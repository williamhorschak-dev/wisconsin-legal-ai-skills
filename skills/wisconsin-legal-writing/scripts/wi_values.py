#!/usr/bin/env python3
"""Dated Wisconsin numbers that this skill's reference files repeat, with a check of fixed statements.

    python wi_values.py                     # values on today's date
    python wi_values.py --on 2027-01-02     # values on a date in the supported range
    python wi_values.py --check-references  # compare the managed reference statements

The table transcribes the statutes published for November 4, 2026 (PUBLISHED), read on
November 9, 2026 (CHECKED), including the scheduled changes identified on those pages. Each
value names its authority, its conditions and the page it was read from. The table begins on
PUBLISHED and refuses any earlier date: the pages do not establish what a number was before
then, and this is not a historical-law database. A later-date answer applies that saved
publication's schedule only. Enactments, orders or other changes absent from that publication
are not covered, and an open-ended row means no later change was recorded from those
sources, not that none was enacted.

--check-references compares the numeric fields in uniquely identified, fixed reference
statements with the table. Each managed statement is a full sentence or table row with typed
number slots. A statement that speaks as of a stated date is compared with the table on that
date, so accurate dated history never becomes a disagreement. Exit 0 when every managed
statement was found once in its reviewed form and every number agrees; exit 1 when a number
disagrees; exit 3 when nothing disagrees but a statement was reworded, duplicated, or carries
extra or hidden text, so its number could not be measured. Other prose, the choice of
governing law and later legal changes are outside the check: a number stated in a sentence
this file does not manage is not examined.

This is a transcription made by an AI reviewer. It is not legal advice, it does not decide
which rule governs a matter, and which actions or claims a changed amount first applies to is
outside it. Standard library only.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path
import re
import sys

SKILL = Path(__file__).resolve().parents[1]
LEGIS = "https://docs.legis.wisconsin.gov/document/statutes/"
# The pages carry "updated through 2025 Wis. Act 247 and through all Supreme Court Orders ... filed
# before and in effect on November 4, 2026 ... (Published 11-4-26)". PUBLISHED is that date. CHECKED
# is the day the pages were retrieved and read; it is not a survey of everything enacted by then.
PUBLISHED = "2026-11-04"
CHECKED = "2026-11-09"
SUPPORTED_FROM = PUBLISHED
ACT_105 = ("Which actions and claims the new amount first applies to is governed by 2025 Wis. Act 105's "
           "initial-applicability provision, not by this table.")
UNITS = {"dollars", "words", "pages", "points", "lines", "inches", "days", "date"}

# (id, value, unit, authority, effective_from, effective_until, source page, note)
# Dates are inclusive ISO dates. effective_from None means from SUPPORTED_FROM; effective_until
# None means no later change was recorded from the pages read, not that none was enacted.
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
     "For the brief types in s. 809.19(8)(c)1., this page limit applies only to the portions in s. 809.19(1)(d), (e) and "
     "(f), using monospaced font or handwriting."),
    ("appellate_reply_brief_pages_monospaced", 13, "pages", "Wis. Stat. s. 809.19(8)(c)2.", None, None, "809.19(8)",
     "For a reply under s. 809.19(4) or (6)(d), this page limit applies only to the portions in s. 809.19(1)(e) and (f), "
     "using monospaced font or handwriting."),
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
     "given within 21 days after entry of the final judgment or order, as provided in s. 806.06(5); a notice given later "
     "is not treated here as meeting that condition. Subject to the exceptions in s. 808.04 and as otherwise expressly "
     "provided by law. Review of a nonfinal judgment or order is under s. 809.50."),
    ("appeal_days_without_notice_of_entry", 90, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "Runs from entry of a final judgment or order, if the notice described for the 45-day period is not given. Subject to "
     "the exceptions in s. 808.04 and as otherwise expressly provided by law. Review of a nonfinal judgment or order is "
     "under s. 809.50."),
    ("notice_of_entry_days", 21, "days", "Wis. Stat. s. 808.04(1)", None, None, "808.04",
     "This is not an independent deadline or a duty to give notice. Under s. 808.04(1), qualifying written notice must be "
     "given within 21 days after entry of the final judgment or order, as provided in s. 806.06(5), to shorten the "
     "ordinary appeal period from 90 to 45 days. The exceptions in s. 808.04 and other express law still apply."),
    ("unpublished_opinion_persuasive_from", "2009-07-01", "date", "Wis. Stat. s. 809.23(3)(b)", None, None, "809.23",
     "An unpublished opinion issued on or after this date that is authored by a member of a three-judge panel or by a "
     "single judge under s. 752.31(2) may be cited for its persuasive value. A per curiam opinion, memorandum opinion, "
     "summary disposition order or other order is not an authored opinion."),
    ("protected_information_from", "2016-07-01", "date", "Wis. Stat. s. 801.19(2)(a)", None, None, "801.19",
     "On or after this date no party may submit protected information in a document filed in an action or proceeding in "
     "circuit court except in the manner s. 801.19 provides."),
)
VALUES = tuple(dict(zip(("id", "value", "unit", "authority", "effective_from", "effective_until", "source", "note"), row),
                    checked=CHECKED, published=PUBLISHED) for row in _ROWS)
for _value in VALUES:
    _value["source"] = LEGIS + _value["source"]

# Managed statements: (file under the skill, anchor, template, whole_line).
# The anchor is a phrase that must occur exactly once in the file, so a second copy of the statement
# cannot hide. The template is the reviewed statement in full, from its first word to its last, with
# a slot for each number: {value_id} is compared on the date asked, {value_id@YYYY-MM-DD} on the date
# the statement itself speaks of, and {first_id+second_id} where one written number states two values.
# A single space in a template matches any run of whitespace; a whole_line template must be the
# entire line.
MANAGED_STATEMENTS = (
    ("references/practice-areas.md", "Before January 1, 2027, § 799.01(1)(d) sets a",
     "Before January 1, 2027, § 799.01(1)(d) sets a ${small_claims_other_civil_amount@2026-12-31} limit for the civil actions "
     "specified there, and § 799.01(1)(c) sets a ${small_claims_replevin_value@2026-12-31} property-value limit for the "
     "replevin actions specified there.", False),
    ("references/practice-areas.md", "raises both amounts to",
     "2025 Wis. Act 105, §§ 2, 3 and 5, raises both amounts to "
     "${small_claims_other_civil_amount+small_claims_replevin_value@2027-01-01} effective January 1, 2027,", False),
    ("references/practice-areas.md", "limit for third-party complaints, personal injury claims, and actions",
     "The **${small_claims_tort_amount}** limit for third-party complaints, personal injury claims, and actions based in "
     "tort, § 799.01(1)(cr), is unchanged by Act 105.", False),
    ("references/appellate.md", "| Proportional serif, body |",
     "| Proportional serif, body | **minimum {appellate_body_point_min} point** |", True),
    ("references/appellate.md", "| Proportional serif, block quotes and footnotes |",
     "| Proportional serif, block quotes and footnotes | **{appellate_quote_footnote_point} point**, single-spaced, "
     "§ 809.19(8)(b)3.c |", True),
    ("references/appellate.md", "| Line spacing, proportional serif |",
     "| Line spacing, proportional serif | between **{appellate_line_spacing_min} and {appellate_line_spacing_max}** |", True),
    ("references/appellate.md", "| Left and right margins |",
     "| Left and right margins | minimum **{appellate_side_margin_min}″** |", True),
    ("references/appellate.md", "| Top and bottom margins |",
     "| Top and bottom margins | minimum **{appellate_top_bottom_margin_min}″** |", True),
    ("references/appellate.md", "| Appellant, respondent, guardian ad litem |",
     "| Appellant, respondent, guardian ad litem | {appellate_brief_pages_monospaced} pages | **{appellate_brief_words} "
     "words** |", True),
    ("references/appellate.md", "| Reply |",
     "| Reply | {appellate_reply_brief_pages_monospaced} pages | **{appellate_reply_brief_words} words** |", True),
    ("references/appellate.md", "| Nonparty (amicus) |",
     "| Nonparty (amicus) | 13 pages | **{appellate_nonparty_brief_words} words** |", True),
    ("references/appellate.md", "**The ordinary civil clock, § 808.04(1).**",
     "**The ordinary civil clock, § 808.04(1).** {appeal_days_without_notice_of_entry} days after entry of the judgment or "
     "order; **{appeal_days_with_notice_of_entry} days** if written notice of entry was given within {notice_of_entry_days} "
     "days after entry (§ 806.06(5)).", False),
    ("references/circuit-court.md", "**Timing, Wis. Stat. § 801.15(4).**",
     "**Timing, Wis. Stat. § 801.15(4).** A written motion and the notice of hearing must be served **not later than "
     "{motion_notice_days} days before** the hearing.", False),
    ("references/circuit-court.md", "- **When the period is less than",
     "- **When the period is less than {short_period_threshold_days} days, Saturdays, Sundays, and legal holidays are "
     "excluded from the count.**", False),
    ("references/circuit-court.md", "- Service by mail:",
     "- Service by mail: **+{service_by_mail_added_days} days**.", True),
    ("references/circuit-court.md", "- Service by fax, email, or the eFiling system completed",
     "- Service by fax, email, or the eFiling system completed **after 5 p.m.**: **+{late_electronic_service_added_days} "
     "day**.", True),
)
_SLOT = re.compile(r"\{([a-z_+]+)(?:@(\d{4}-\d{2}-\d{2}))?\}")
_NUMBER = r"[0-9][0-9,]*(?:\.[0-9]+)?"


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
    source = f"the statutes published for {PUBLISHED}, read on {CHECKED}"
    if on <= _day(PUBLISHED):
        return source
    return (source + ", including the scheduled changes identified on those pages; a later-date answer applies that "
            "publication's schedule only, and enactments, orders or other changes absent from it are not covered")


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


def _slots(template):
    """[(value ids stated by one written number, as_of or None)] in template order."""
    return [(match.group(1).split("+"), match.group(2)) for match in _SLOT.finditer(template)]


def table_problems():
    """Structural problems: each id must cover every date from SUPPORTED_FROM on exactly once."""
    problems = []
    start = _day(SUPPORTED_FROM)
    if _day(CHECKED) < _day(PUBLISHED):
        problems.append("CHECKED is before PUBLISHED")
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
    known = {row["id"]: row["unit"] for row in VALUES}
    for name, anchor, template, whole_line in MANAGED_STATEMENTS:
        if not _slots(template):
            problems.append(f"managed statement {anchor!r} has no number slot")
        if anchor not in template:
            problems.append(f"managed statement {anchor!r}: the anchor is not part of its template")
        for value_ids, as_of in _slots(template):
            for value_id in value_ids:
                if value_id not in known:
                    problems.append(f"managed statement {anchor!r} names unknown value {value_id}")
                elif known[value_id] == "date":
                    problems.append(f"managed statement {anchor!r}: {value_id} is a date, which the check does not compare")
            if as_of is not None and _day(as_of) < start:
                problems.append(f"managed statement {anchor!r} speaks of {as_of}, before the supported range")
    return problems


def _pattern(text, whole_line=False):
    """Regex for literal template text; a single space matches any whitespace run (within the line for whole_line)."""
    gap = r"[ \t]+" if whole_line else r"\s+"
    parts, position = [], 0
    for index, match in enumerate(_SLOT.finditer(text)):
        parts.append(gap.join(re.escape(piece) for piece in text[position:match.start()].split(" ")))
        parts.append(f"(?P<s{index}>{_NUMBER})")
        position = match.end()
    parts.append(gap.join(re.escape(piece) for piece in text[position:].split(" ")))
    body = "".join(parts)
    return re.compile(r"^[ \t]*" + body + r"[ \t]*$" if whole_line else body, re.MULTILINE)


def _number(text):
    text = text.replace(",", "")
    return float(text) if "." in text else int(text)


def check_references(root=SKILL, on=None):
    """Return (disagreements, unmeasured) for the managed statements on the date."""
    on = _supported(on)
    disagreements, unmeasured, texts = [], [], {}
    for name, anchor, template, whole_line in MANAGED_STATEMENTS:
        if name not in texts:
            texts[name] = (Path(root) / name).read_text(encoding="utf-8")
        label = f"{name}: statement \"{anchor}\""
        anchors = len(_pattern(anchor).findall(texts[name]))
        found = list(_pattern(template, whole_line).finditer(texts[name]))
        if anchors != 1 or len(found) != 1:
            why = (f"its opening words occur {anchors} times, not once" if anchors != 1 else
                   "it is not in its reviewed form (reworded, or carrying extra or hidden text)" if not found else
                   f"it occurs {len(found)} times")
            unmeasured.append(f"{label}: UNMEASURED: {why}. Restore the reviewed statement, or review the change and update "
                              "its template in wi_values.py.")
            continue
        for index, (value_ids, as_of) in enumerate(_slots(template)):
            written = found[0].group(f"s{index}")
            for value_id in value_ids:
                row = value_on(value_id, _day(as_of) if as_of else on)
                if _number(written) != row["value"]:
                    dated = f"as of {as_of}, the date the statement speaks of" if as_of else f"on {on.isoformat()}"
                    disagreements.append(f"{label}: DISAGREES: states {written} for {value_id}; the table has "
                                         f"{row['value']} {row['unit']} {dated} ({row['authority']}).")
    return disagreements, unmeasured


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--on", help=f"date as YYYY-MM-DD, {SUPPORTED_FROM} or later (default: today)")
    parser.add_argument("--check-references", action="store_true", help="compare the managed reference statements with the table")
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
        disagreements, unmeasured = check_references(SKILL, on)
        for line in disagreements + unmeasured:
            print(line)
        fields = sum(len(value_ids) for _, _, template, _ in MANAGED_STATEMENTS for value_ids, _ in _slots(template))
        print(f"{len(disagreements)} disagreement(s) and {len(unmeasured)} unmeasured statement(s) on {on.isoformat()}, across "
              f"{fields} numeric fields in {len(MANAGED_STATEMENTS)} uniquely identified, fixed reference statements. Basis: "
              f"{basis(on)}. Other prose, governing-law selection and later legal changes are outside the check.")
        return 1 if disagreements else 3 if unmeasured else 0
    print(f"Values on {on.isoformat()}. Basis: {basis(on)}. Not legal advice.")
    for value_id in dict.fromkeys(row["id"] for row in VALUES):
        row = value_on(value_id, on)
        print(f"  {value_id}: {row['value']} {row['unit']}  [{row['authority']}]  {row['note']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
