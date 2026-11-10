#!/usr/bin/env python3
"""Dated Wisconsin numbers that this skill's reference files repeat, with a consistency check.

    python wi_values.py                     # values on today's date
    python wi_values.py --on 2027-01-02     # values on a date in the supported range
    python wi_values.py --check-references  # exit 1 if a reference file disagrees

Each value names its authority, the official page it was read from and the day it was
read. The table is bounded. It begins on SUPPORTED_FROM, the date the pages read say their
text was in effect, and it refuses any earlier date: the pages do not establish what the
number was before then, and this is not a historical-law database. For a later date it
reports the law as it stood when read on CHECKED, including amendments then enacted with a
later effective date. An act passed after CHECKED is not in it.

--check-references reads the number out of each listed sentence in the reference files
and compares it with the table. A sentence that speaks as of a stated date ("Before
January 1, 2027 ...") is compared with the table on that date, so accurate dated history
never becomes a disagreement. A sentence in the present tense is compared with the table
on the date given. A listed sentence that cannot be found is reported too, because the
number in it can no longer be confirmed.

This is a table of numbers read from published text by an AI reviewer. It is not legal
advice, it does not decide which rule governs a matter, and which actions or claims a
changed amount first applies to is outside it. Standard library only.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path
import re
import sys

SKILL = Path(__file__).resolve().parents[1]
LEGIS = "https://docs.legis.wisconsin.gov/document/statutes/"
CHECKED = "2026-11-09"
# The pages read on CHECKED carry "updated through 2025 Wis. Act 247 and through all Supreme
# Court Orders ... filed before and in effect on November 4, 2026 ... (Published 11-4-26)".
SUPPORTED_FROM = "2026-11-04"
ACT_105 = ("Which actions and claims the new amount first applies to is governed by 2025 Wis. Act 105's "
           "initial-applicability provision, not by this table.")
UNITS = {"dollars", "words", "pages", "points", "lines", "inches", "days", "date"}

# (id, value, unit, authority, effective_from, effective_until, source page, note)
# Dates are inclusive ISO dates. effective_from None means from SUPPORTED_FROM; effective_until
# None means no later change was enacted when the table was read.
_ROWS = (
    ("small_claims_other_civil_amount", 10000, "dollars", "Wis. Stat. s. 799.01(1)(d)", None, "2026-12-31", "799.01",
     "Other civil actions of the kinds listed in par. (d) 1. to 3. The published page shows $15,000 with a NOTE that "
     "par. (d) (intro.) is shown as amended eff. 1-1-27 by 2025 Wis. Act 105 and reads $10,000 before then."),
    ("small_claims_other_civil_amount", 15000, "dollars", "Wis. Stat. s. 799.01(1)(d), as amended by 2025 Wis. Act 105",
     "2027-01-01", None, "799.01", "Other civil actions of the kinds listed in par. (d) 1. to 3. " + ACT_105),
    ("small_claims_replevin_value", 10000, "dollars", "Wis. Stat. s. 799.01(1)(c)", None, "2026-12-31", "799.01",
     "Value of the property claimed in a replevin action under ss. 810.01 to 810.13; sub. (1) (intro.) states exceptions. "
     "The published page shows $15,000 with a NOTE that par. (c) is shown as amended eff. 1-1-27 by 2025 Wis. Act 105 and "
     "reads $10,000 before then."),
    ("small_claims_replevin_value", 15000, "dollars", "Wis. Stat. s. 799.01(1)(c), as amended by 2025 Wis. Act 105",
     "2027-01-01", None, "799.01",
     "Value of the property claimed in a replevin action under ss. 810.01 to 810.13; sub. (1) (intro.) states exceptions. "
     + ACT_105),
    ("small_claims_tort_amount", 5000, "dollars", "Wis. Stat. s. 799.01(1)(cr)", None, None, "799.01",
     "Only the category in par. (cr): third-party complaints, personal injury claims and actions based in tort. Not a "
     "limit on every small claim."),
    ("appellate_brief_words", 11000, "words", "Wis. Stat. s. 809.19(8)(c)1.", None, None, "809.19(8)",
     "A party's brief under s. 809.19(1), (5) or (6)(a), (b) or (c), or a guardian ad litem's under (6m): the portions "
     "referred to in s. 809.19(1)(d), (e) and (f), in a proportional serif font."),
    ("appellate_reply_brief_words", 3000, "words", "Wis. Stat. s. 809.19(8)(c)2.", None, None, "809.19(8)",
     "A reply brief under s. 809.19(4) or (6)(d): the portions referred to in s. 809.19(1)(e) and (f), in a proportional "
     "serif font."),
    ("appellate_nonparty_brief_words", 3000, "words", "Wis. Stat. s. 809.19(8)(c)3.", None, None, "809.19(8)",
     "A brief under s. 809.19(7): the portions referred to in s. 809.19(1)(e) and (f), in a proportional serif font."),
    ("appellate_brief_pages_monospaced", 50, "pages", "Wis. Stat. s. 809.19(8)(c)1.", None, None, "809.19(8)",
     "Monospaced font or handwriting only; not a page limit for a brief in a proportional serif font."),
    ("appellate_reply_brief_pages_monospaced", 13, "pages", "Wis. Stat. s. 809.19(8)(c)2.", None, None, "809.19(8)",
     "Monospaced font or handwriting only; not a page limit for a brief in a proportional serif font."),
    ("appellate_body_point_min", 13, "points", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)",
     "Minimum for body text in a proportional serif font."),
    ("appellate_quote_footnote_point", 11, "points", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)",
     "Block quotes and footnotes in a proportional serif font, which must also be single-spaced."),
    ("appellate_line_spacing_min", 1.15, "lines", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)",
     "Body text in a proportional serif font; an equivalent line spacing is allowed."),
    ("appellate_line_spacing_max", 1.5, "lines", "Wis. Stat. s. 809.19(8)(b)3.c.", None, None, "809.19(8)",
     "Body text in a proportional serif font; an equivalent line spacing is allowed."),
    ("appellate_side_margin_min", 1.25, "inches", "Wis. Stat. s. 809.19(8)(b)3.e.", None, None, "809.19(8)",
     "Minimum on the right and left sides."),
    ("appellate_top_bottom_margin_min", 1.0, "inches", "Wis. Stat. s. 809.19(8)(b)3.e.", None, None, "809.19(8)",
     "Minimum on the top and bottom."),
    ("motion_notice_days", 5, "days", "Wis. Stat. s. 801.15(4)", None, None, "801.15",
     "A written motion, other than one which may be heard ex parte, and notice of its hearing: served not later than this "
     "many days before the time specified for the hearing, unless a different period is fixed by statute or by order of "
     "the court."),
    ("short_period_threshold_days", 11, "days", "Wis. Stat. s. 801.15(1)(b)", None, None, "801.15",
     "When the period is less than this number (not this number or fewer), Saturdays, Sundays and holidays are excluded "
     "in the computation."),
    ("service_by_mail_added_days", 3, "days", "Wis. Stat. s. 801.15(5)(a)", None, None, "801.15",
     "Added to a prescribed period that runs from service of a notice or other paper on the party, when it is served by "
     "mail. How the addition combines with the other counting rules is not decided here."),
    ("late_electronic_service_added_days", 1, "days", "Wis. Stat. s. 801.15(5)(b)", None, None, "801.15",
     "Added to a prescribed period that runs from service, when service is by facsimile transmission, electronic mail or "
     "the electronic filing system under s. 801.18 and the transmission is completed between 5 p.m. and midnight."),
    ("appeal_days_with_notice_of_entry", 45, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "Runs from entry of a final judgment or order. The statute gives this period only if written notice of the entry is "
     "given within 21 days of the final judgment or order as provided in s. 806.06(5); a notice given later is not treated "
     "here as meeting that condition. Subject to the exceptions in s. 808.04 and as otherwise expressly provided by law. "
     "Review of a nonfinal judgment or order is under s. 809.50."),
    ("appeal_days_without_notice_of_entry", 90, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "Runs from entry of a final judgment or order, if the notice described for the 45-day period is not given. Subject to "
     "the exceptions in s. 808.04 and as otherwise expressly provided by law. Review of a nonfinal judgment or order is "
     "under s. 809.50."),
    ("notice_of_entry_days", 21, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "Not a deadline of its own and not a duty to give notice: the interval within which written notice of entry must be "
     "given, as provided in s. 806.06(5), for the 45-day period to apply in place of the 90-day period."),
    ("unpublished_opinion_persuasive_from", "2009-07-01", "date", "Wis. Stat. s. 809.23(3)(b)", None, None, "809.23",
     "An unpublished opinion issued on or after this date that is authored by a member of a three-judge panel or by a "
     "single judge under s. 752.31(2) may be cited for its persuasive value. A per curiam opinion, memorandum opinion, "
     "summary disposition order or other order is not an authored opinion."),
    ("protected_information_from", "2016-07-01", "date", "Wis. Stat. s. 801.19(2)(a)", None, None, "801.19",
     "On or after this date no party may submit protected information in a document filed in an action or proceeding in "
     "circuit court except in the manner s. 801.19 provides."),
)
VALUES = tuple(dict(zip(("id", "value", "unit", "authority", "effective_from", "effective_until", "source", "note"), row),
                    checked=CHECKED) for row in _ROWS)
for _value in VALUES:
    _value["source"] = LEGIS + _value["source"]

# Sentences in the reference files that state a table value: (value id, file under the skill,
# pattern whose group "v" captures the number as written, as_of). as_of is the date the sentence
# itself speaks of, or None for a present-tense sentence, which is compared on the date asked.
REFERENCE_STATEMENTS = (
    ("small_claims_other_civil_amount", "references/practice-areas.md",
     r"Before January 1, 2027, § 799\.01\(1\)\(d\) sets a\s+\$(?P<v>[\d,]+)\s+limit", "2026-12-31"),
    ("small_claims_replevin_value", "references/practice-areas.md",
     r"§ 799\.01\(1\)\(c\) sets a\s+\$(?P<v>[\d,]+)\s+property-value\s+limit", "2026-12-31"),
    ("small_claims_other_civil_amount", "references/practice-areas.md",
     r"raises both amounts to\s+\$(?P<v>[\d,]+)\s+effective\s+January 1, 2027", "2027-01-01"),
    ("small_claims_replevin_value", "references/practice-areas.md",
     r"raises both amounts to\s+\$(?P<v>[\d,]+)\s+effective\s+January 1, 2027", "2027-01-01"),
    ("small_claims_tort_amount", "references/practice-areas.md",
     r"\*\*\$(?P<v>[\d,]+)\*\*\s+limit for third-party complaints", None),
    ("appellate_brief_words", "references/appellate.md",
     r"\| Appellant, respondent, guardian ad litem \| \d+ pages \| \*\*(?P<v>[\d,]+) words\*\*", None),
    ("appellate_brief_pages_monospaced", "references/appellate.md",
     r"\| Appellant, respondent, guardian ad litem \| (?P<v>\d+) pages \|", None),
    ("appellate_reply_brief_words", "references/appellate.md", r"\| Reply \| \d+ pages \| \*\*(?P<v>[\d,]+) words\*\*", None),
    ("appellate_reply_brief_pages_monospaced", "references/appellate.md", r"\| Reply \| (?P<v>\d+) pages \|", None),
    ("appellate_nonparty_brief_words", "references/appellate.md",
     r"\| Nonparty \(amicus\) \| \d+ pages \| \*\*(?P<v>[\d,]+) words\*\*", None),
    ("appellate_body_point_min", "references/appellate.md", r"\*\*minimum (?P<v>\d+) point\*\*", None),
    ("appellate_quote_footnote_point", "references/appellate.md",
     r"block quotes and footnotes \| \*\*(?P<v>\d+) point\*\*", None),
    ("appellate_line_spacing_min", "references/appellate.md", r"between \*\*(?P<v>[\d.]+) and [\d.]+\*\*", None),
    ("appellate_line_spacing_max", "references/appellate.md", r"between \*\*[\d.]+ and (?P<v>[\d.]+)\*\*", None),
    ("appellate_side_margin_min", "references/appellate.md",
     r"Left and right margins \| minimum \*\*(?P<v>[\d.]+)″\*\*", None),
    ("appellate_top_bottom_margin_min", "references/appellate.md",
     r"Top and bottom margins \| minimum \*\*(?P<v>[\d.]+)″\*\*", None),
    ("motion_notice_days", "references/circuit-court.md", r"\*\*not later than (?P<v>\d+) days before\*\*", None),
    ("short_period_threshold_days", "references/circuit-court.md", r"When the period is less than (?P<v>\d+) days", None),
    ("service_by_mail_added_days", "references/circuit-court.md", r"Service by mail: \*\*\+(?P<v>\d+) days\*\*", None),
    ("late_electronic_service_added_days", "references/circuit-court.md",
     r"completed \*\*after 5 p\.m\.\*\*: \*\*\+(?P<v>\d+) day\*\*", None),
    ("appeal_days_without_notice_of_entry", "references/appellate.md",
     r"\*\*The ordinary civil clock, § 808\.04\(1\)\.\*\* (?P<v>\d+) days after entry", None),
    ("appeal_days_with_notice_of_entry", "references/appellate.md",
     r"\*\*(?P<v>\d+)\s+days\*\* if written notice of entry was given", None),
    ("notice_of_entry_days", "references/appellate.md",
     r"if written notice of entry was given within (?P<v>\d+) days after entry", None),
)


class UnsupportedDate(ValueError):
    """The date is before the range the table was verified for."""


def _day(text):
    return date.fromisoformat(text) if isinstance(text, str) else text


def _supported(on):
    on = _day(on) if on else date.today()
    if on < _day(SUPPORTED_FROM):
        raise UnsupportedDate(f"{on.isoformat()} is before {SUPPORTED_FROM}, the first date this table was verified for; "
                              "it does not report earlier law")
    return on


def basis(on=None):
    """One sentence saying what a value reported for the date rests on."""
    on = _supported(on)
    if on <= _day(CHECKED):
        return f"the statutes as published for {SUPPORTED_FROM} and read on {CHECKED}"
    return (f"the law as read on {CHECKED}, including amendments enacted by then with a later effective date; an act passed "
            f"after {CHECKED} is not in this table")


def value_on(value_id, on=None):
    """The one row for value_id on the date. KeyError for an unknown id, UnsupportedDate before the range."""
    on = _supported(on)
    rows = [row for row in VALUES if row["id"] == value_id]
    if not rows:
        raise KeyError(f"{value_id}: no such value")
    start = _day(SUPPORTED_FROM)
    live = [row for row in rows if _day(row["effective_from"] or start) <= on
            and (row["effective_until"] is None or on <= _day(row["effective_until"]))]
    if len(live) != 1:
        raise LookupError(f"{value_id}: {len(live)} rows cover {on.isoformat()}; the table is malformed")
    return live[0]


def table_problems():
    """Structural problems: each id must cover every date from SUPPORTED_FROM on exactly once."""
    problems = []
    start = _day(SUPPORTED_FROM)
    if _day(CHECKED) < start:
        problems.append("CHECKED is before SUPPORTED_FROM")
    for value_id in dict.fromkeys(row["id"] for row in VALUES):
        rows = [row for row in VALUES if row["id"] == value_id]
        for row in rows:
            if row["unit"] not in UNITS:
                problems.append(f"{value_id}: unknown unit {row['unit']!r}")
            if not row["authority"].startswith(("Wis. Stat. s. ", "SCR ")):
                problems.append(f"{value_id}: authority must name a statute or rule")
            if not row["note"]:
                problems.append(f"{value_id}: a row has no note stating its conditions")
        rows.sort(key=lambda row: _day(row["effective_from"] or start))
        if rows[0]["effective_from"] is not None:
            problems.append(f"{value_id}: the first row must begin at the start of the supported range")
        if rows[-1]["effective_until"] is not None:
            problems.append(f"{value_id}: the last row must be open-ended")
        for earlier, later in zip(rows, rows[1:]):
            if earlier["effective_until"] is None or later["effective_from"] is None:
                problems.append(f"{value_id}: only the first row may omit a start and only the last an end")
            elif _day(later["effective_from"]) != _day(earlier["effective_until"]) + timedelta(days=1):
                problems.append(f"{value_id}: rows are not contiguous at {earlier['effective_until']}")
            elif _day(earlier["effective_until"]) < start:
                problems.append(f"{value_id}: a row ends before the supported range begins")
    known = {row["id"] for row in VALUES}
    for value_id, name, pattern, as_of in REFERENCE_STATEMENTS:
        if value_id not in known:
            problems.append(f"reference statement names unknown value {value_id}")
        if "(?P<v>" not in pattern:
            problems.append(f"reference statement for {value_id} captures no number")
        if as_of is not None and _day(as_of) < start:
            problems.append(f"reference statement for {value_id} speaks of {as_of}, before the supported range")
    return problems


def _number(text):
    text = text.replace(",", "")
    return float(text) if "." in text else int(text)


def reference_problems(root=SKILL, on=None):
    """Listed reference sentences whose number differs from the table, or that cannot be found."""
    on = _supported(on)
    problems, texts = [], {}
    for value_id, name, pattern, as_of in REFERENCE_STATEMENTS:
        if name not in texts:
            texts[name] = (Path(root) / name).read_text(encoding="utf-8")
        when = _day(as_of) if as_of else on
        row = value_on(value_id, when)
        dated = f"as of {as_of}, the date the sentence speaks of" if as_of else f"on {on.isoformat()}"
        found = re.search(pattern, texts[name])
        if not found:
            problems.append(f"{name}: NOT FOUND: the sentence that states {value_id} ({row['authority']}) was not found, so "
                            f"its number cannot be confirmed. Restore the sentence or update the pattern /{pattern}/.")
        elif _number(found.group("v")) != row["value"]:
            problems.append(f"{name}: DISAGREES: states {found.group('v')} for {value_id}; the table has {row['value']} "
                            f"{row['unit']} {dated} ({row['authority']}).")
    return problems


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--on", help=f"date as YYYY-MM-DD, {SUPPORTED_FROM} or later (default: today)")
    parser.add_argument("--check-references", action="store_true", help="compare the reference files with the table")
    args = parser.parse_args(argv)
    try:
        on = _supported(date.fromisoformat(args.on) if args.on else None)
    except UnsupportedDate as exc:
        parser.exit(2, f"wi_values: {exc}\n")
    except ValueError:
        parser.error("--on must be a date as YYYY-MM-DD")
    problems = table_problems()
    for line in problems:
        print("table problem: " + line, file=sys.stderr)
    if problems:
        return 1
    if args.check_references:
        problems = reference_problems(SKILL, on)
        for line in problems:
            print(line)
        print(f"{len(problems)} problem(s) across {len(REFERENCE_STATEMENTS)} reference sentences on {on.isoformat()}. "
              f"Basis: {basis(on)}. This check compares numbers; it does not review the law.")
        return 1 if problems else 0
    print(f"Values on {on.isoformat()}. Basis: {basis(on)}. Not legal advice.")
    for value_id in dict.fromkeys(row["id"] for row in VALUES):
        row = value_on(value_id, on)
        print(f"  {value_id}: {row['value']} {row['unit']}  [{row['authority']}]  {row['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
