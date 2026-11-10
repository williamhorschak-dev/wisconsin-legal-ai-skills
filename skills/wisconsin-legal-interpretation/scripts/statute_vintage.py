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

It flags a copy that may not show the text in force on the operative date:

  an effective-date NOTE for the section, in either direction;
  an operative date before the copy was published, when the History note lists an act or
  a Supreme Court order dated in the operative year or later, or an order whose year the
  note does not show;
  a copy published more than 45 days before the operative date (a screening interval this
  project chose, not a legal safe harbor);
  a copy with no currency line, no History note, or no line for the requested section.

Exit 0 when nothing is flagged, 1 when something is, 2 for a usage error or a file with
none of the signals. A flag is a reason to read the amending act; a clean screen is not a
finding that the text was in force. History notes are editorial, a Supreme Court order's
number is its docket number and not its date, initial-applicability and nonstatutory
provisions do not appear in the notes, and this script reads one saved copy in the layout
the legislature's site publishes. Text extracted from the chapter PDFs is not parsed
reliably and is flagged as unscreenable. It never fetches anything. Standard library only.
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
HISTORY_ACT = re.compile(r"\b((?:19|20)\d{2}) a\. (\d+)")
HISTORY_CHAPTER = re.compile(r"\b((?:18|19|20)\d{2}) c\. (\d+)")
# An order entry runs to the next semicolon or the next order; its year is the public domain
# citation or a parenthetical year inside the entry, never the docket prefix of "No. 20-07"
# (the published note for s. 809.23 lists "No. 08-02, 2009 WI 2").
HISTORY_ORDER = re.compile(r"Sup\. Ct\. Order(?: No\. (\d{2}-\d+[A-Z]?))?((?:(?!Sup\. Ct\. Order)[^;])*)")
ORDER_YEAR = re.compile(r"\b((?:19|20)\d{2}) WI \d+|\(((?:19|20)\d{2})\)")
# An order with no docket number is identified by where it is printed: "83 Wis. 2d xiii".
ORDER_REPORTER = re.compile(r"\b(\d{1,3} Wis\. 2d [ivxlcdm]+)\b")
# The site prints the number twice on a section's title line ("799.01799.01 Applicability"),
# so the doubled form is tried first; "1.011.01" is section 1.01, not 1.011.
SECTION_LEAD = re.compile(r"^\s*(?:(\d{1,3}\.\d{1,4})\1|(\d{1,3}\.\d{1,4}))(?!\d)")
BLOCK_END = re.compile(r"^\s*(?:\d{1,3}\.\d{1,4}(?!\d)|Effective date|Cross-reference|NOTE:|Annotation|Note\b)")
STALE_AFTER_DAYS = 45


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
    """The History note, joined across wrapped lines, or None."""
    start = HISTORY_START.search(text)
    if not start:
        return None
    lines = text[start.end():].split("\n")
    block = [lines[0]]
    for line in lines[1:]:
        if block[-1].rstrip().endswith(".") or not line.strip() or BLOCK_END.match(line):
            break
        block.append(line)
    return " ".join(part.strip() for part in block)


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
              "published": None, "through": None, "last_act": None}

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
        acts, orders = [], []
    else:
        acts = [(int(year), f"{year} Wis. Act {number}") for year, number in HISTORY_ACT.findall(history)]
        acts += [(int(year), f"chapter {number}, Laws of {year}") for year, number in HISTORY_CHAPTER.findall(history)]
        orders = []
        for number, rest in HISTORY_ORDER.findall(history):
            found = ORDER_YEAR.search(rest)
            year = int(found.group(1) or found.group(2)) if found else None
            printed = ORDER_REPORTER.search(rest)
            where = f" No. {number}" if number else (f", {printed.group(1)}" if printed else "")
            orders.append((year, "Sup. Ct. Order" + where + (f" ({year})" if year else "")))
        dated = [item for item in acts if item[0]]
        result["last_act"] = max(dated)[1] if dated else None
        if published and operative < published:
            for year, label in sorted(acts):
                if year >= operative.year:
                    flag("later_amendment", label,
                         f"the History note lists {label}; the copy was published {published.isoformat()}, after the "
                         "operative date, so it may include that change and may not show the text in force on the operative date")
            for year, label in orders:
                if year is None:
                    flag("undated_order", label, f"the History note lists {label} without a year this script can read; an order's "
                         "number is its docket number, not its date, so find when it was adopted and took effect")
                elif year >= operative.year:
                    flag("later_amendment", label, f"the History note lists {label}; the copy was published "
                         f"{published.isoformat()}, after the operative date, so it may include that change. The year shown is "
                         "the order's, not its effective date")
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
          + (f"; latest act in the History note: {result['last_act']}" if result.get("last_act") else ""))
    for item in result["notes"]:
        print("note  " + item)
    for item in result["flags"]:
        print("FLAG  " + item["text"])
    print(f"{len(result['flags'])} flag(s). A flag is a reason to read the amending act. A clean screen does not establish the text "
          "in force on the operative date: History notes are editorial and do not show initial-applicability or nonstatutory "
          "provisions.")
    return 1 if result["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
