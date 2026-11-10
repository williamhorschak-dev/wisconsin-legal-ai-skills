#!/usr/bin/env python3
"""Screen a saved Wisconsin statute section page against an operative date.

    python statute_vintage.py "sources/statutes/Wis-Stat-799.01.md" --section 799.01 --operative-date 2026-12-01

It reads three dated signals from a saved copy of a section page from
docs.legis.wisconsin.gov (text, Markdown or saved HTML):

  the currency line   "2023-24 Wisconsin Statutes updated through 2025 Wis. Act 247 ...
                       (Published 11-4-26)", which also says changes effective after that
                       date are designated by NOTES;
  effective-date NOTEs "NOTE: Par. (c) is shown as amended eff. 1-1-27 by 2025 Wis. Act 105.
                       Prior to 1-1-27 it reads: ...";
  the History note    "History: 1975 c. 325; ... 2025 a. 105; Sup. Ct. Order No. 20-07,
                       2021 WI 37, ...", listing acts and Supreme Court orders.

The History note is read whole or not at all. Every entry must fit a form this script
knows: an act or chapter law with each of its numbers ("1987 a. 208, 378, 403"), with or
without a section suffix; a Supreme Court order with its number, public domain citation,
reporter citation, parenthetical year, and filed and effective dates, in the combinations
the published notes use; a renumbering ("Stats. 1979 s. 799.01"). An entry that fits none
of them is reported word for word and flagged. Nothing is skipped in silence.

It flags a copy that may not show the text in force on the operative date:

  an effective-date NOTE for the section, in either direction;
  when the operative date is before the copy was published, each History entry that is
  dated in the year before the operative year or later, or whose note gives an effective
  date after the operative date; each entry with no year; and each entry it cannot read;
  a copy published more than 45 days before the operative date;
  a copy with no currency line, no History note, a History note that looks cut off, or no
  line for the requested section.

Two of those numbers are this project's screening choices, not law: the 45 days, and the
one-year look-back. An act or order can take effect in a later year than the year it is
dated, so an entry dated the year before the operative year is flagged too. A longer delay
is not detected. The year shown for an order is the year appearing in its citation; it
does not establish the order's adoption date or effective date.

Exit 0 when nothing is flagged, 1 when something is, 2 for a usage error or a file with
none of the signals. A flag is a reason to read the amending act; a clean screen is not a
finding that the text was in force. History notes are editorial, initial-applicability and
nonstatutory provisions do not appear in them, and this script reads one saved copy in the
layout the legislature's site publishes. Text extracted from the chapter PDFs is not parsed
reliably. It never fetches anything. Standard library only.
"""
import argparse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

CURRENCY = re.compile(r"(\d{4}-\d{2}) Wisconsin Statutes updated through ((?:19|20)\d{2} Wis\. Act \d+)"
                      r".{0,400}?\(Published (\d{1,2})-(\d{1,2})-(\d{2})\)", re.DOTALL)
EFFECTIVE_NOTE = re.compile(r"NOTE:\s*((?:(?!\n\s*\n)[\s\S]){0,300}?\beff(?:ective)?\.?\s*(\d{1,2})-(\d{1,2})-(\d{2,4})\b[^\n]*)")
ACT_IN_NOTE = re.compile(r"((?:19|20)\d{2}) Wis\. Act (\d+)")
HISTORY_START = re.compile(r"History:\s*")
# The site prints the number twice on a section's title line ("799.01799.01 Applicability"),
# so the doubled form is tried first; "1.011.01" is section 1.01, not 1.011.
SECTION_LEAD = re.compile(r"^\s*(?:(\d{1,3}\.\d{1,4})\1|(\d{1,3}\.\d{1,4}))(?!\d)")
# A line that cannot be a continuation of a wrapped History note.
BLOCK_END = re.compile(r"^\s*(?:\d{1,3}\.\d{1,4}(?!\d)|Effective date|Cross[- ][Rr]eference|NOTE:|Note:|Annotation|"
                       r"\d{4}-\d{2} Wisconsin Statutes updated)")
STALE_AFTER_DAYS = 45
LOOK_BACK_YEARS = 1

# ---- the History grammar. Each entry must match one of these in full.
_YEAR = r"(?:18|19|20)\d{2}"
_LOCATOR = r"(?:[ivxlcdm]+|R?\d+)"
_ORDER_WORDS = r"Sup\.? Ct\.? Order"
_ORDER_NUMBER = r"\d{2}-\d{1,3}[A-Z]?"
_SHORT_DATE = r"\d{1,2}-\d{1,2}-\d{2}"
ACT_ENTRY = re.compile(rf"(?P<year>{_YEAR}) (?P<kind>[ac])\.\s*(?P<numbers>\d+(?:,\s*\d+)*)(?:,?\s+ss?\.\s*[0-9a-z ,.()]+)?")
ORDER_ENTRY = re.compile(
    rf"{_ORDER_WORDS}(?: No\. (?P<number>{_ORDER_NUMBER}))?(?P<joined>(?: and {_ORDER_WORDS} No\. {_ORDER_NUMBER})*)"
    rf"(?:, (?P<public>(?:19|20)\d{{2}} WI \d+))?"
    rf"(?:, (?P<reporter>\d{{1,3}} Wis\. ?2d {_LOCATOR}(?:, {_LOCATOR})*))?"
    rf"(?: \((?P<parenthetical>{_YEAR})\))?"
    rf"(?:, (?P<trailing>{_LOCATOR}(?:, {_LOCATOR})*))?"
    rf"(?:, filed (?P<filed>{_SHORT_DATE}))?(?:, eff\. (?P<effective>{_SHORT_DATE}))?")
RENUMBERING_ENTRY = re.compile(rf"Stats\. (?P<year>{_YEAR}) s\. \d{{1,3}}\.\d{{1,4}}")
_SPLIT_BEFORE = re.compile(rf",\s*(?=(?:{_ORDER_WORDS}\b|{_YEAR} [ac]\.))")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("div", "p", "br", "tr", "li", "table"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def plain_text(raw):
    """Text of a saved page; HTML is reduced to lines, other text is returned as it is."""
    if re.search(r"<(?:html|body|div|p)\b", raw, re.IGNORECASE):
        parser = _Text()
        parser.feed(raw)
        raw = "".join(parser.parts)
    raw = re.sub(r"[ \t\xa0]+", " ", raw)
    return re.sub(r"\n\s*\n+", "\n\n", raw)


def _year(two_or_four):
    value = int(two_or_four)
    return value if value > 99 else (2000 + value if value <= 69 else 1900 + value)


def _short_date(text):
    month, day, year = text.split("-")
    try:
        return date(_year(year), int(month), int(day))
    except ValueError:
        return None


def section_text(text, section):
    """Lines belonging to the section, or None when no line opens with its number."""
    kept, owner = [], None
    for line in text.split("\n"):
        lead = SECTION_LEAD.match(line)
        if lead:
            owner = lead.group(1) or lead.group(2)
        if owner == section:
            kept.append(line)
    return "\n".join(kept) if kept else None


def history_block(text):
    """The History note with its wrapped lines joined, or None. It ends at a blank line or a line that opens something else."""
    start = HISTORY_START.search(text)
    if not start:
        return None
    lines = text[start.end():].split("\n")
    block = [lines[0]]
    for line in lines[1:]:
        if not line.strip() or BLOCK_END.match(line):
            break
        block.append(line)
    return " ".join(" ".join(block).split())


def parse_history(block):
    """Read every entry of a History note.

    Returns (entries, complete). Each entry is a dict with 'identity' (the exact words a memo uses to
    name it), 'year' (int or None), 'effective' (date or None) and 'kind': 'act', 'chapter', 'order',
    'renumbering' or 'unread'. complete is False when the note does not end with a period, which is
    how a cut-off copy shows.
    """
    text = block.strip()
    complete = text.endswith(".")
    text = _SPLIT_BEFORE.sub("; ", text.rstrip(". "))
    entries = []
    for piece in (part.strip().rstrip(".").strip() for part in text.split(";")):
        if not piece:
            continue
        act, order, renumbering = ACT_ENTRY.fullmatch(piece), ORDER_ENTRY.fullmatch(piece), RENUMBERING_ENTRY.fullmatch(piece)
        if act:
            year = int(act.group("year"))
            for number in re.findall(r"\d+", act.group("numbers")):
                identity = f"{year} Wis. Act {number}" if act.group("kind") == "a" else f"chapter {number}, Laws of {year}"
                entries.append({"identity": identity, "year": year, "effective": None,
                                "kind": "act" if act.group("kind") == "a" else "chapter"})
        elif order and (order.group("number") or order.group("public") or order.group("reporter")):
            effective = _short_date(order.group("effective")) if order.group("effective") else None
            shown = order.group("public") or order.group("parenthetical")
            year = int(shown[:4]) if shown else (_short_date(order.group("filed")).year if order.group("filed")
                                                 and _short_date(order.group("filed")) else None)
            numbers = ([order.group("number")] if order.group("number") else []) + re.findall(
                rf"No\. ({_ORDER_NUMBER})", order.group("joined") or "")
            if numbers:
                identities = [f"Sup. Ct. Order No. {number}" for number in numbers]
            elif order.group("public"):
                identities = [f"Sup. Ct. Order, {order.group('public')}"]
            else:
                printed = re.sub(r"Wis\. ?2d", "Wis. 2d", order.group("reporter"))
                identities = ["Sup. Ct. Order, " + printed + (", " + order.group("trailing") if order.group("trailing") else "")]
            for identity in identities:
                entries.append({"identity": identity, "year": year, "effective": effective, "kind": "order"})
        elif renumbering:
            entries.append({"identity": piece, "year": int(renumbering.group("year")), "effective": None, "kind": "renumbering"})
        else:
            entries.append({"identity": piece, "year": None, "effective": None, "kind": "unread"})
    return entries, complete


def screen(raw, operative, section=None):
    """Return None when the text shows no statute signals, else a dict with flags and notes."""
    text = plain_text(raw)
    currency = CURRENCY.search(text)
    scoped = section_text(text, section) if section else text
    located = scoped is not None
    history = history_block(scoped) if located else None
    notes_found = list(EFFECTIVE_NOTE.finditer(scoped)) if located else []
    if not currency and history_block(text) is None and not EFFECTIVE_NOTE.search(text):
        return None
    result = {"section": section, "operative_date": operative.isoformat(), "flags": [], "notes": [],
              "published": None, "through": None, "last_act": None, "entries": 0}

    def flag(kind, identity, message):
        result["flags"].append({"kind": kind, "identity": identity, "text": message})

    published = None
    if currency:
        published = date(_year(currency.group(5)), int(currency.group(3)), int(currency.group(4)))
        result["published"], result["through"] = published.isoformat(), currency.group(2)
    else:
        flag("no_currency_line", None, "the copy has no currency line, so its publication date is unknown")
    if not located:
        flag("section_not_found", None, f"no line of the copy opens with {section}, so the section was not screened; save the "
             "page for that section, or check the number")
        return result
    for match in notes_found:
        effective = date(_year(match.group(4)), int(match.group(2)), int(match.group(3)))
        act = ACT_IN_NOTE.search(match.group(1))
        label = f"{act.group(1)} Wis. Act {act.group(2)}" if act else None
        side = "before" if operative < effective else "on or after"
        quoted = " ".join(match.group(1).split())[:90]
        flag("effective_date_note", label, f"an effective-date NOTE (\"{quoted}\"): the operative date is {side} the stated "
             f"effective date {effective.isoformat()}" + (f" of {label}" if label else "") + ". The NOTE points to the version "
             "displayed on that side of the date; check the amending act and any other amendment before identifying the text in force")
    if history is None:
        flag("no_history_note", None, "no History note was found for the section, so later amendments cannot be screened "
             "(text extracted from a chapter PDF is not parsed reliably)")
    else:
        entries, complete = parse_history(history)
        result["entries"] = len(entries)
        acts = [(entry["year"], entry["identity"]) for entry in entries if entry["kind"] == "act"]
        result["last_act"] = max(acts)[1] if acts else None
        if published and operative < published:
            lead = f"the copy was published {published.isoformat()}, after the operative date"
            if not complete:
                flag("history_incomplete", None, "the History note does not end with a period, so it may be cut off and later "
                     "entries may be missing; save the section page again")
            for entry in entries:
                identity = entry["identity"]
                if entry["kind"] == "unread":
                    flag("unread_history_entry", identity, f"the History note has an entry this script cannot read, \"{identity}\"; "
                         f"it may be an amendment, and {lead}")
                elif entry["effective"] is not None:
                    if entry["effective"] > operative:
                        flag("later_amendment", identity, f"the History note lists {identity} with an effective date of "
                             f"{entry['effective'].isoformat()}, after the operative date; {lead}, so it may include that change")
                elif entry["year"] is None:
                    flag("undated_entry", identity, f"the History note lists {identity} without a year this script can read; an "
                         "order's number is its docket number, not its date, so find when it was adopted and took effect")
                elif entry["year"] >= operative.year - LOOK_BACK_YEARS:
                    caution = (" The year shown is the year appearing in the order's citation; it does not establish the order's "
                               "adoption date or effective date." if entry["kind"] == "order" else "")
                    flag("later_amendment", identity, f"the History note lists {identity} ({entry['year']}); {lead}, so it may "
                         "include that change and may not show the text in force on the operative date." + caution)
    if published and (operative - published).days > STALE_AFTER_DAYS:
        flag("stale_copy", None, f"the copy was published {published.isoformat()}, {(operative - published).days} days before "
             f"the operative date; later acts and orders are not in it ({STALE_AFTER_DAYS} days is this project's screening "
             "interval, not a legal safe harbor)")
    elif published and operative > published:
        result["notes"].append(f"the copy was published {published.isoformat()}; changes after that date are not in it")
    return result


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("copy", type=Path, help="saved section page (.txt, .md, .html)")
    parser.add_argument("--operative-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--section", required=True, help="section number, for example 799.01")
    args = parser.parse_args(argv)
    try:
        operative = date.fromisoformat(args.operative_date)
        raw = args.copy.read_text(encoding="utf-8-sig")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"statute_vintage: {exc}\n")
    result = screen(raw, operative, args.section)
    if result is None:
        parser.exit(2, "statute_vintage: no currency line, History note or effective-date NOTE was found; this does not look "
                       "like a saved Wisconsin statute page\n")
    print(f"Section {args.section}; operative date {result['operative_date']}; copy published "
          f"{result['published'] or 'unknown'}" + (f", updated through {result['through']}" if result["through"] else "")
          + f"; {result['entries']} History entries read"
          + (f"; latest act in the History note: {result['last_act']}" if result.get("last_act") else ""))
    for item in result["notes"]:
        print("note  " + item)
    for item in result["flags"]:
        print("FLAG  " + item["text"])
    print(f"{len(result['flags'])} flag(s). A flag is a reason to read the amending act. A clean screen does not establish the text "
          "in force on the operative date: History notes are editorial and do not show initial-applicability or nonstatutory "
          f"provisions, and an entry dated more than {LOOK_BACK_YEARS} year before the operative year is assumed to have taken "
          "effect by then, which this script does not check.")
    return 1 if result["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
