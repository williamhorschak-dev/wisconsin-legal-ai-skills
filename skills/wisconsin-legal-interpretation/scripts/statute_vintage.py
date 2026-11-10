#!/usr/bin/env python3
"""Screen an archived Wisconsin statute page against an operative date.

    python statute_vintage.py "sources/statutes/Wis-Stat-799.01.md" --section 799.01 --operative-date 2026-12-01

The legislature's published statutes carry three dated signals this script reads from
a saved copy of a section page (text, Markdown or HTML from docs.legis.wisconsin.gov):

  the currency line   "2023-24 Wisconsin Statutes updated through 2025 Wis. Act 247 ...
                       (Published 11-4-26)", which also says changes effective after that
                       date are designated by NOTES;
  effective-date notes "NOTE: Par. (c) is shown as amended eff. 1-1-27 by 2025 Wis. Act
                       105. Prior to 1-1-27 it reads: ...";
  the History note    "History: 1975 c. 325; ... 2025 a. 105.", listing the acts and
                       Supreme Court orders that created or amended the section.

It flags a copy whose text may not be the text in force on the operative date:

  an effective-date note, in either direction (the page shows the future text and prints
  the earlier text after the note);
  an operative date before the copy was published, when the History note lists an act or
  court order from the operative year or later;
  a copy published more than 45 days before the operative date;
  a copy with no currency line or no History note, which cannot be screened.

Exit 0 when nothing is flagged, 1 when something is, 2 for a usage error. A clean screen is
not a finding that the text was in force: History notes are editorial, initial-applicability
and nonstatutory provisions are not shown in them, and this script reads one saved copy.
It never fetches anything. Standard library only.
"""
import argparse
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

CURRENCY = re.compile(r"(\d{4}-\d{2}) Wisconsin Statutes updated through ((?:19|20)\d{2} Wis\. Act \d+)"
                      r".{0,400}?\(Published (\d{1,2})-(\d{1,2})-(\d{2})\)", re.DOTALL)
EFFECTIVE_NOTE = re.compile(r"NOTE:\s*([^\n]*?\beff(?:ective)?\.?\s*(\d{1,2})-(\d{1,2})-(\d{2,4})\b[^\n]*)")
ACT_IN_NOTE = re.compile(r"((?:19|20)\d{2}) Wis\. Act (\d+)")
HISTORY = re.compile(r"History:\s*([^\n]+)")
HISTORY_ACT = re.compile(r"\b((?:19|20)\d{2}) a\. (\d+)")
HISTORY_CHAPTER = re.compile(r"\b((?:19|20)\d{2}) c\. (\d+)")
HISTORY_ORDER = re.compile(r"Sup\. Ct\. Order(?: No\.)? (\d{2})-(\d+[A-Z]?)")
SECTION_LEAD = re.compile(r"^\s*(\d{1,3}\.\d{1,4})(?!\d)")
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
    return re.sub(r"\n\s*\n+", "\n", raw)


def _year(two_or_four):
    value = int(two_or_four)
    return value if value > 99 else (2000 + value if value <= 69 else 1900 + value)


def section_text(text, section):
    """Lines belonging to the section: a line that opens with a section number sets the owner."""
    kept, owner, seen = [], None, False
    for line in text.split("\n"):
        lead = SECTION_LEAD.match(line)
        if lead:
            owner = lead.group(1)
        if owner == section:
            kept.append(line)
            seen = True
    return ("\n".join(kept), True) if seen else (text, False)


def screen(raw, operative, section=None):
    """Return None when the text shows no statute signals, else a dict with flags and notes."""
    text = plain_text(raw)
    currency = CURRENCY.search(text)
    scoped, located = section_text(text, section) if section else (text, True)
    history = HISTORY.search(scoped)
    notes_found = list(EFFECTIVE_NOTE.finditer(scoped))
    if not currency and not history and not notes_found:
        return None
    result = {"section": section, "operative_date": operative.isoformat(), "flags": [], "notes": [],
              "published": None, "through": None}
    flag = lambda kind, act, message: result["flags"].append({"kind": kind, "act": act, "text": message})
    if section and not located:
        result["notes"].append(f"no line opening with {section} was found; the whole copy was screened")
    published = None
    if currency:
        published = date(_year(currency.group(5)), int(currency.group(3)), int(currency.group(4)))
        result["published"], result["through"] = published.isoformat(), currency.group(2)
    else:
        flag("no_currency_line", None, "the copy has no currency line, so its publication date is unknown")
    for match in notes_found:
        effective = date(_year(match.group(4)), int(match.group(2)), int(match.group(3)))
        act = ACT_IN_NOTE.search(match.group(1))
        label = f"{act.group(1)} Wis. Act {act.group(2)}" if act else None
        when = ("is not yet in effect on the operative date; the text in force is the earlier text printed after the note"
                if operative < effective else
                "took effect on or before the operative date; the text in force is the amended text, not the earlier text "
                "printed after the note")
        quoted = " ".join(match.group(1).split())[:90]
        flag("effective_date_note", label, f"an effective-date note (\"{quoted}\"): an amendment effective "
             f"{effective.isoformat()}" + (f" by {label}" if label else "") + f" {when}")
    if not history:
        flag("no_history_note", None, "no History note was found for the section, so later amendments cannot be screened")
    else:
        acts = [(int(year), f"{year} Wis. Act {number}") for year, number in HISTORY_ACT.findall(history.group(1))]
        acts += [(int(year), f"chapter {number}, Laws of {year}") for year, number in HISTORY_CHAPTER.findall(history.group(1))]
        orders = [(_year(year), f"Sup. Ct. Order No. {year}-{number}") for year, number in HISTORY_ORDER.findall(history.group(1))]
        result["last_act"] = max(acts)[1] if acts else None
        if published and operative < published:
            for year, label in sorted(acts + orders):
                if year >= operative.year:
                    flag("later_amendment", label if "Wis. Act" in label else None,
                         f"the History note lists {label}; the copy was published {published.isoformat()}, after the "
                         "operative date, so its text may include that change and may not be the text in force on the "
                         "operative date")
    if published and (operative - published).days > STALE_AFTER_DAYS:
        flag("stale_copy", None, f"the copy was published {published.isoformat()}, {(operative - published).days} days before "
             "the operative date; later acts and orders are not in it")
    elif published and operative > published:
        result["notes"].append(f"the copy was published {published.isoformat()}; changes after that date are not in it")
    return result


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("copy", type=Path, help="saved section page (.txt, .md, .html)")
    parser.add_argument("--operative-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--section", help="section number, for example 799.01, when the copy holds several sections")
    args = parser.parse_args(argv)
    try:
        operative = date.fromisoformat(args.operative_date)
        raw = args.copy.read_text(encoding="utf-8-sig")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"statute_vintage: {exc}\n")
    result = screen(raw, operative, args.section)
    if result is None:
        parser.exit(2, "statute_vintage: no currency line, History note or effective-date note was found; this does not look "
                       "like a saved Wisconsin statute page\n")
    print(f"Section {args.section or '(whole copy)'}; operative date {result['operative_date']}; copy published "
          f"{result['published'] or 'unknown'}" + (f", updated through {result['through']}" if result["through"] else "")
          + (f"; last act in the History note: {result['last_act']}" if result.get("last_act") else ""))
    for item in result["notes"]:
        print("note  " + item)
    for item in result["flags"]:
        print("FLAG  " + item["text"])
    print(f"{len(result['flags'])} flag(s). A clean screen does not establish the text in force on the operative date: History "
          "notes are editorial and do not show initial-applicability or nonstatutory provisions. Read the act.")
    return 1 if result["flags"] else 0


if __name__ == "__main__":
    sys.exit(main())
