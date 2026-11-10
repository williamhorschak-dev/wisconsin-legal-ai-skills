#!/usr/bin/env python3
"""Dated Wisconsin numbers that this skill's tools and reference files repeat.

Each value names its authority, the period it applies to, the official page it was read
from and the day it was read. The other scripts take their numbers from here, and
--check-references fails when a reference file states a number this table says is not
the one in force on the chosen date. That turns a scheduled change, such as the
small-claims amounts that change on January 1, 2027 under 2025 Wis. Act 105, into a
failing check on that date instead of a stale sentence.

    python wi_values.py                     # values in force today
    python wi_values.py --on 2027-01-02     # values in force on a date
    python wi_values.py --check-references  # exit 1 if a reference file disagrees

This is a table of numbers read from published text by an AI reviewer. It is not legal
advice, it does not decide which rule governs a matter, and an initial-applicability
question (for example which claims a changed amount reaches) is outside it. Standard
library only.
"""
import argparse
from datetime import date
from pathlib import Path
import re
import sys

SKILL = Path(__file__).resolve().parents[1]
LEGIS = "https://docs.legis.wisconsin.gov/document/statutes/"
CHECKED = "2026-11-09"

# (id, value, unit, authority, effective_from, effective_until, source, note)
# effective_from/effective_until are inclusive ISO dates or None for open-ended.
_ROWS = (
    ("small_claims_other_civil_amount", 10000, "dollars", "Wis. Stat. s. 799.01(1)(d)", None, "2026-12-31", "799.01",
     "Published text shows $15,000 with a note that par. (d) (intro.) is amended eff. 1-1-27 by 2025 Wis. Act 105 and reads $10,000 before then."),
    ("small_claims_other_civil_amount", 15000, "dollars", "Wis. Stat. s. 799.01(1)(d), as amended by 2025 Wis. Act 105", "2027-01-01", None, "799.01",
     "Which actions and claims the new amount first applies to is governed by Act 105's initial-applicability provision, not by this table."),
    ("small_claims_replevin_value", 10000, "dollars", "Wis. Stat. s. 799.01(1)(c)", None, "2026-12-31", "799.01",
     "Published text shows $15,000 with a note that par. (c) is amended eff. 1-1-27 by 2025 Wis. Act 105 and reads $10,000 before then."),
    ("small_claims_replevin_value", 15000, "dollars", "Wis. Stat. s. 799.01(1)(c), as amended by 2025 Wis. Act 105", "2027-01-01", None, "799.01", ""),
    ("small_claims_tort_amount", 5000, "dollars", "Wis. Stat. s. 799.01(1)(cr)", None, None, "799.01",
     "Third-party complaints, personal injury claims and actions based in tort."),
    ("appellate_brief_words", 11000, "words", "Wis. Stat. s. 809.19(8)(c)1.", None, None, "809.19(8)",
     "Portions referred to in s. 809.19(1)(d), (e) and (f); proportional serif font."),
    ("appellate_reply_brief_words", 3000, "words", "Wis. Stat. s. 809.19(8)(c)2.", None, None, "809.19(8)",
     "Portions referred to in s. 809.19(1)(e) and (f); proportional serif font."),
    ("appellate_nonparty_brief_words", 3000, "words", "Wis. Stat. s. 809.19(8)(c)3.", None, None, "809.19(8)", ""),
    ("appellate_brief_pages_monospaced", 50, "pages", "Wis. Stat. s. 809.19(8)(c)1.", None, None, "809.19(8)", "Monospaced font or handwriting."),
    ("appellate_reply_brief_pages_monospaced", 13, "pages", "Wis. Stat. s. 809.19(8)(c)2.", None, None, "809.19(8)", "Monospaced font or handwriting."),
    ("appellate_body_point_min", 13, "points", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)", "Proportional serif body text."),
    ("appellate_quote_footnote_point", 11, "points", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)", "Block quotes and footnotes."),
    ("appellate_line_spacing_min", 1.15, "lines", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)", "Body text; or an equivalent line spacing."),
    ("appellate_line_spacing_max", 1.5, "lines", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)", "Body text; or an equivalent line spacing."),
    ("appellate_side_margin_min", 1.25, "inches", "Wis. Stat. s. 809.19(8)(b)3.e.", None, None, "809.19(8)", "Right and left sides."),
    ("appellate_top_bottom_margin_min", 1.0, "inches", "Wis. Stat. s. 809.19(8)(b)3.e.", None, None, "809.19(8)", ""),
    ("motion_notice_days", 5, "days", "Wis. Stat. s. 801.15(4)", None, None, "801.15",
     "Unless a different period is fixed by statute or by order of the court."),
    ("short_period_threshold_days", 11, "days", "Wis. Stat. s. 801.15(1)(b)", None, None, "801.15",
     "When the period is less than this, Saturdays, Sundays and holidays are excluded."),
    ("service_by_mail_added_days", 3, "days", "Wis. Stat. s. 801.15(5)(a)", None, None, "801.15", "Period running from service of a notice or paper."),
    ("late_electronic_service_added_days", 1, "days", "Wis. Stat. s. 801.15(5)(b)", None, None, "801.15",
     "Facsimile, electronic mail or the electronic filing system, completed between 5 p.m. and midnight."),
    ("appeal_days_with_notice_of_entry", 45, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "If written notice of entry is given within 21 days as provided in s. 806.06(5); exceptions in s. 808.04 and elsewhere."),
    ("appeal_days_without_notice_of_entry", 90, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04", "Exceptions in s. 808.04 and elsewhere."),
    ("notice_of_entry_days", 21, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04", ""),
    ("unpublished_opinion_persuasive_from", "2009-07-01", "date", "Wis. Stat. s. 809.23(3)(b)", None, None, "809.23", "Authored opinions only."),
    ("protected_information_from", "2016-07-01", "date", "Wis. Stat. s. 801.19(2)(a)", None, None, "801.19", ""),
)
VALUES = tuple(dict(zip(("id", "value", "unit", "authority", "effective_from", "effective_until", "source", "note"), row),
                    checked=CHECKED) for row in _ROWS)
for _value in VALUES:
    _value["source"] = LEGIS + _value["source"]

# Reference statements tied to a value: (value id, file under the skill, pattern, kind, from, until).
# "require" patterns must be present while the period is current; "forbid" patterns must be gone.
REFERENCE_STATEMENTS = (
    ("small_claims_other_civil_amount", "references/practice-areas.md",
     r"Before January 1, 2027, § 799\.01\(1\)\(d\) sets a\s+\$10,000 limit", "require", None, "2026-12-31"),
    ("small_claims_other_civil_amount", "references/practice-areas.md",
     r"Before January 1, 2027, § 799\.01\(1\)\(d\) sets a\s+\$10,000 limit", "forbid", "2027-01-01", None),
    ("small_claims_other_civil_amount", "references/practice-areas.md", r"\$15,000", "require", "2027-01-01", None),
    ("small_claims_tort_amount", "references/practice-areas.md", r"\*\*\$5,000\*\*\s+limit for third-party complaints", "require", None, None),
    ("appellate_brief_words", "references/appellate.md", r"\*\*11,000 words\*\*", "require", None, None),
    ("appellate_reply_brief_words", "references/appellate.md", r"Reply \| 13 pages \| \*\*3,000 words\*\*", "require", None, None),
    ("appellate_body_point_min", "references/appellate.md", r"\*\*minimum 13 point\*\*", "require", None, None),
    ("appellate_side_margin_min", "references/appellate.md", r"minimum \*\*1\.25", "require", None, None),
    ("appellate_line_spacing_min", "references/appellate.md", r"between \*\*1\.15 and 1\.5\*\*", "require", None, None),
    ("motion_notice_days", "references/circuit-court.md", r"not later than 5 days before", "require", None, None),
    ("short_period_threshold_days", "references/circuit-court.md", r"period is less than 11 days", "require", None, None),
    ("service_by_mail_added_days", "references/circuit-court.md", r"Service by mail: \*\*\+3 days\*\*", "require", None, None),
    ("appeal_days_with_notice_of_entry", "references/appellate.md", r"\*\*45\s+days\*\*", "require", None, None),
)


def _day(text):
    return date.fromisoformat(text) if isinstance(text, str) else text


def _in_period(start, end, on):
    return (start is None or _day(start) <= on) and (end is None or on <= _day(end))


def value_on(value_id, on=None):
    """Return the one row for value_id in force on the date; raise if none or several."""
    on = _day(on) if on else date.today()
    rows = [row for row in VALUES if row["id"] == value_id and _in_period(row["effective_from"], row["effective_until"], on)]
    if len(rows) != 1:
        raise KeyError(f"{value_id}: {len(rows)} values in force on {on.isoformat()}")
    return rows[0]


def table_problems():
    """Structural problems in the table itself: bad dates, overlapping or missing periods."""
    problems = []
    for value_id in sorted({row["id"] for row in VALUES}):
        rows = [row for row in VALUES if row["id"] == value_id]
        edges = set()
        for row in rows:
            start, end = row["effective_from"], row["effective_until"]
            if start and end and _day(start) > _day(end):
                problems.append(f"{value_id}: period ends before it starts")
            edges.update(day for day in (start, end) if day)
            if not row["authority"].startswith(("Wis. Stat. s. ", "SCR ")):
                problems.append(f"{value_id}: authority must name a statute or rule")
        probes = [date(2000, 1, 1), date(2100, 1, 1)] + [_day(edge) for edge in edges]
        probes += [date.fromordinal(day.toordinal() + 1) for day in probes[2:]]
        for probe in probes:
            count = sum(_in_period(row["effective_from"], row["effective_until"], probe) for row in rows)
            if count != 1:
                problems.append(f"{value_id}: {count} values in force on {probe.isoformat()}")
    return problems


def reference_problems(root=SKILL, on=None):
    """Reference statements that disagree with the table on the date."""
    on = _day(on) if on else date.today()
    problems = []
    for value_id, name, pattern, kind, start, end in REFERENCE_STATEMENTS:
        if not _in_period(start, end, on):
            continue
        text = (Path(root) / name).read_text(encoding="utf-8")
        found = re.search(pattern, text) is not None
        row = value_on(value_id, on)
        if kind == "require" and not found:
            problems.append(f"{name}: expected a statement matching /{pattern}/ for {value_id} = {row['value']} {row['unit']} "
                            f"({row['authority']}) on {on.isoformat()}")
        if kind == "forbid" and found:
            problems.append(f"{name}: still states /{pattern}/, which is out of date on {on.isoformat()}: {value_id} is "
                            f"{row['value']} {row['unit']} ({row['authority']})")
    return problems


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--on", help="date as YYYY-MM-DD (default: today)")
    parser.add_argument("--check-references", action="store_true", help="compare the reference files with the table")
    args = parser.parse_args(argv)
    try:
        on = date.fromisoformat(args.on) if args.on else date.today()
    except ValueError:
        parser.error("--on must be a date as YYYY-MM-DD")
    problems = table_problems()
    if args.check_references:
        problems += reference_problems(SKILL, on)
        for line in problems:
            print(line)
        print(f"{len(problems)} problem(s) on {on.isoformat()}. Values were read from the published statutes on {CHECKED}; "
              "this check compares text, it does not review the law.")
        return 1 if problems else 0
    for line in problems:
        print("table problem: " + line, file=sys.stderr)
    print(f"Values in force on {on.isoformat()} (read {CHECKED}; not legal advice):")
    for value_id in dict.fromkeys(row["id"] for row in VALUES):
        row = value_on(value_id, on)
        print(f"  {value_id}: {row['value']} {row['unit']}  [{row['authority']}]" + (f"  {row['note']}" if row["note"] else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
