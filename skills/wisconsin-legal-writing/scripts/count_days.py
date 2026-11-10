#!/usr/bin/env python3
"""Count a period of days under Wis. Stat. s. 801.15(1) and show every step.

    python count_days.py --event 2026-11-09 --days 20 --direction after --no-other-closures
    python count_days.py --event 2026-11-09 --days 5 --direction after --service mail --no-other-closures
    python count_days.py --event 2026-11-20 --days 5 --direction before --no-other-closures
    python count_days.py --holidays 2026

What it applies, each read from the published statutes on the date in wi_values.py:

  s. 801.15(1)(b)  the day of the act, event or default is not counted; the last day is
                   included unless it is a day the clerk of courts office is closed; when
                   the period is less than 11 days, Saturdays, Sundays and holidays are
                   excluded from the count.
  s. 801.15(1)(a)  "holiday" is a s. 230.35(4)(a) holiday or a statewide legal holiday under
                   s. 995.20, and a full day on Good Friday.
  s. 801.15(5)     3 days are added for service by mail, and 1 day for service by facsimile,
                   electronic mail or the electronic filing system completed between 5 p.m.
                   and midnight, when the period runs from service of a notice or paper.

What it refuses to do, because the statute's text does not settle it or the facts are not
in the command:

  It will not give a date when the last day falls on a holiday unless you say whether the
  clerk's office is closed that day (--clerk-closed DATE or --clerk-open DATE). Statewide
  legal holidays include election days on which a clerk's office may be open.
  When the last day is a closed day it reports the next open day and the last open day
  before it; s. 801.15(1)(b) says the closed day is not included and does not say in terms
  what follows.
  When a service addition changes the answer depending on whether the added days are
  counted before or after the short-period rule, it shows both and gives the earlier date.
  It does not combine a service addition with a period counted back from a hearing.
  It handles only the years whose holiday rules were read (VERIFIED_YEARS).

It does not decide whether s. 801.15 governs a deadline, whether a different period is fixed
by statute or order, when an event occurred, or when service was complete. A date printed
here is arithmetic on the inputs, not a deadline determination and not legal advice.
Exit 0 when a date is computed, 1 when it is refused, 2 for a usage error.
"""
import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wi_values  # noqa: E402

# The holiday rules below were read on wi_values.CHECKED from ss. 230.35(4)(a), 995.20 and
# 5.02(5) and (12s). Re-read those sections before adding a year.
VERIFIED_YEARS = (2026, 2027)
STATE = "s. 230.35(4)(a)"
LEGAL = "s. 995.20"


def _nth(year, month, weekday, n):
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last(year, month, weekday):
    day = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return day - timedelta(days=(day.weekday() - weekday) % 7)


def _easter(year):
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    m = (32 + 2 * e + 2 * i - h - k) % 7
    n = (a + 11 * h + 19 * m) // 433
    month = (h + m - 7 * n + 90) // 25
    return date(year, month, (h + m - 7 * n + 33 * month + 19) % 32)


def holidays(year):
    """Holidays under s. 801.15(1)(a) for a year: {date: [name and authority, ...]}."""
    found = {}

    def add(day, name, authority):
        found.setdefault(day, []).append(f"{name}, {authority}")

    fixed = lambda month, day: date(year, month, day)
    both = STATE + " and " + LEGAL
    add(fixed(1, 1), "January 1", both)
    add(_nth(year, 1, 0, 3), "the 3rd Monday in January", both)
    add(_nth(year, 2, 0, 3), "the 3rd Monday in February", LEGAL)
    add(_last(year, 5, 0), "the last Monday in May", both)
    add(fixed(6, 19), "June 19", LEGAL)
    add(fixed(7, 4), "July 4", both)
    add(_nth(year, 9, 0, 1), "the 1st Monday in September", both)
    add(_nth(year, 10, 0, 2), "the 2nd Monday in October", LEGAL)
    add(fixed(11, 11), "November 11", LEGAL)
    add(_nth(year, 11, 3, 4), "the 4th Thursday in November", both)
    add(fixed(12, 24), "December 24", STATE)
    add(fixed(12, 25), "December 25", both)
    add(fixed(12, 31), "December 31", STATE)
    if year % 2 == 0:
        add(_nth(year, 8, 1, 2), "the partisan primary (2nd Tuesday in August, s. 5.02(12s))", LEGAL)
        first_monday = _nth(year, 11, 0, 1)
        add(first_monday + timedelta(days=1), "the general election (Tuesday after the first Monday in November, s. 5.02(5))", LEGAL)
    for day, labels in list(found.items()):
        if day.weekday() != 6:
            continue
        if any(LEGAL in label for label in labels):
            add(day + timedelta(days=1), f"the Monday after a legal holiday that falls on Sunday ({day.isoformat()})", LEGAL)
        if day in (fixed(1, 1), fixed(7, 4), fixed(12, 25)):
            add(day + timedelta(days=1), f"the day following a Sunday holiday ({day.isoformat()})", "s. 230.35(4)(a)10.")
    add(_easter(year) - timedelta(days=2), "Good Friday", "s. 801.15(1)(a)")
    return found


class Refused(Exception):
    """The inputs do not allow a date to be stated."""


def _holiday(day):
    if day.year not in VERIFIED_YEARS:
        raise Refused(f"{day.isoformat()} is outside the years whose holiday rules were read ({', '.join(map(str, VERIFIED_YEARS))}); "
                      "re-read ss. 230.35(4)(a), 995.20 and 5.02 and extend VERIFIED_YEARS before counting there")
    return holidays(day.year).get(day)


def _skip_reason(day):
    if day.weekday() == 5:
        return "Saturday"
    if day.weekday() == 6:
        return "Sunday"
    names = _holiday(day)
    return "holiday: " + "; ".join(names) if names else None


def _walk(event, count, step, short):
    """Count `count` days from the event; return (last day, rows of (day, label))."""
    rows, day, counted = [(event, "day of the act or event: not counted, s. 801.15(1)(b)")], event, 0
    while counted < count:
        day += timedelta(days=step)
        reason = _skip_reason(day) if short else None
        if not short:
            _holiday(day)  # still enforces the verified years
        if reason:
            rows.append((day, f"excluded ({reason}), period under 11 days, s. 801.15(1)(b)"))
        else:
            counted += 1
            rows.append((day, f"day {counted}"))
    return day, rows


def compute(event, days, direction, service="none", clerk_closed=(), clerk_open=(), closures_stated=False):
    """Return a dict with the reading(s), rows and the stated result; raise Refused when no date can be given."""
    threshold = wi_values.value_on("short_period_threshold_days", event)["value"]
    added = {"none": 0, "mail": wi_values.value_on("service_by_mail_added_days", event)["value"],
             "late-electronic": wi_values.value_on("late_electronic_service_added_days", event)["value"]}[service]
    if days < 1:
        raise ValueError("--days must be at least 1")
    if direction == "before" and added:
        raise Refused("a service addition under s. 801.15(5) is not combined here with a period counted back from a hearing; how "
                      "the two interact is a question of case law (see references/circuit-court.md section 6)")
    if not closures_stated and not clerk_closed and not clerk_open:
        raise Refused("say which days the clerk of courts office is closed besides Saturdays and Sundays (--clerk-closed DATE ...), "
                      "or state that there are none in the period (--no-other-closures); s. 801.15(1)(b) makes the last day depend "
                      "on it")
    step = 1 if direction == "after" else -1
    readings = []
    if added:
        total = days + added
        last, rows = _walk(event, total, step, total < threshold)
        readings.append((f"{days} days plus {added} under s. 801.15(5) counted as one period of {total} days"
                         + (" (under 11, so Saturdays, Sundays and holidays are excluded)" if total < threshold else ""), last, rows))
        base, rows = _walk(event, days, step, days < threshold)
        tail = []
        last = base
        for index in range(added):
            last += timedelta(days=1)
            _holiday(last)
            tail.append((last, f"added day {index + 1}, s. 801.15(5)"))
        readings.append((f"{days} days counted first" + (" (under 11, so Saturdays, Sundays and holidays are excluded)" if days < threshold else "")
                         + f", then {added} calendar day(s) added under s. 801.15(5)", last, rows + tail))
    else:
        last, rows = _walk(event, days, step, days < threshold)
        readings.append((f"{days} days" + (" (under 11, so Saturdays, Sundays and holidays are excluded)" if days < threshold else ""), last, rows))
    distinct = sorted({reading[1] for reading in readings})
    chosen = distinct[0]
    result = {"readings": readings, "computed": chosen, "notes": [], "direction": direction}
    if len(distinct) > 1:
        result["notes"].append(f"the two ways of applying the s. 801.15(5) addition give {distinct[0].isoformat()} and "
                               f"{distinct[1].isoformat()}; the statute's text does not say which is right, so the earlier date is used")
    if direction == "before":
        result["act_by"] = chosen
        result["notes"].append("this is the latest day that is the stated number of days before the event; if you cannot serve or act "
                               "on that day by your method, do it earlier")
        return result

    def status(day):
        if day in clerk_closed:
            return "closed"
        if day in clerk_open:
            return "open"
        if day.weekday() >= 5:
            return "closed"
        if _holiday(day) and closures_stated:
            stated = (f"{day.isoformat()} is a holiday under s. 801.15(1)(a) (" + "; ".join(_holiday(day)) + "); you stated the "
                      "clerk of courts office has no closures besides weekends, so it is treated as open. Confirm that with the clerk")
            if stated not in result["notes"]:
                result["notes"].append(stated)
            return "open"
        return "unknown" if _holiday(day) else "open"

    state = status(chosen)
    if state == "unknown":
        raise Refused(f"the last day computed is {chosen.strftime('%A')} {chosen.isoformat()}, a holiday under s. 801.15(1)(a) ("
                      + "; ".join(_holiday(chosen)) + "). It is included unless the clerk of courts office is closed that day. Ask the "
                      f"clerk, then rerun with --clerk-closed {chosen.isoformat()} or --clerk-open {chosen.isoformat()}")
    if state == "open":
        result["act_by"] = chosen
        return result
    after, before = chosen, chosen
    while status(after) != "open":
        after += timedelta(days=1)
        if status(after) == "unknown":
            raise Refused(f"the last day computed, {chosen.isoformat()}, is a day the clerk's office is closed, and the next day, "
                          f"{after.isoformat()}, is a holiday (" + "; ".join(_holiday(after)) + "); say whether the office is closed "
                          f"that day with --clerk-closed {after.isoformat()} or --clerk-open {after.isoformat()}")
    while status(before) != "open":
        before -= timedelta(days=1)
    result.update(act_by=before, next_open=after)
    result["notes"].append(f"the last day computed, {chosen.strftime('%A')} {chosen.isoformat()}, is a day the clerk of courts office is "
                           "closed, so s. 801.15(1)(b) does not include it. The statute does not say in terms what follows. The next day "
                           f"the office is open on these inputs is {after.strftime('%A')} {after.isoformat()}; the last open day before "
                           f"the computed day is {before.strftime('%A')} {before.isoformat()}, and acting by then avoids the question")
    return result


def _dates(values, parser):
    try:
        return {date.fromisoformat(value) for value in values or ()}
    except ValueError:
        parser.error("dates must be YYYY-MM-DD")


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--event", help="day of the act, event or default, or the hearing date for --direction before (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="the period in days")
    parser.add_argument("--direction", choices=("after", "before"))
    parser.add_argument("--service", choices=("none", "mail", "late-electronic"), default="none",
                        help="how the notice or paper that starts the period was served, s. 801.15(5)")
    parser.add_argument("--clerk-closed", nargs="*", metavar="DATE", help="days the clerk of courts office is closed, besides weekends")
    parser.add_argument("--clerk-open", nargs="*", metavar="DATE", help="holidays on which the clerk of courts office is open")
    parser.add_argument("--no-other-closures", action="store_true", help="state that the office has no closures in the period besides weekends")
    parser.add_argument("--holidays", type=int, metavar="YEAR", help="list the s. 801.15(1)(a) holidays for a year and exit")
    args = parser.parse_args(argv)
    if args.holidays:
        if args.holidays not in VERIFIED_YEARS:
            parser.exit(1, f"count_days: holiday rules were read for {', '.join(map(str, VERIFIED_YEARS))} only\n")
        for day, names in sorted(holidays(args.holidays).items()):
            print(f"{day.isoformat()} {day.strftime('%A'):9s} " + "; ".join(names))
        return 0
    if not (args.event and args.days and args.direction):
        parser.error("give --event, --days and --direction, or --holidays YEAR")
    try:
        event = date.fromisoformat(args.event)
    except ValueError:
        parser.error("--event must be YYYY-MM-DD")
    try:
        result = compute(event, args.days, args.direction, args.service, _dates(args.clerk_closed, parser),
                         _dates(args.clerk_open, parser), args.no_other_closures)
    except ValueError as exc:
        parser.error(str(exc))
    except Refused as exc:
        print(f"NOT COMPUTED: {exc}.")
        return 1
    for label, last, rows in result["readings"]:
        print(f"Reading: {label}")
        for day, text in rows:
            print(f"  {day.isoformat()} {day.strftime('%a')}  {text}")
        print(f"  = {last.strftime('%A')} {last.isoformat()}")
    for item in result["notes"]:
        print("Note: " + item + ".")
    verb = "Latest day to act before the event" if result["direction"] == "before" else "Act on or before"
    print(f"{verb}: {result['act_by'].strftime('%A')} {result['act_by'].isoformat()}")
    print("This is arithmetic under s. 801.15(1) on the dates and facts you gave. It does not decide whether s. 801.15 governs this "
          "deadline, whether a statute or order fixes a different period, when the event occurred or when service was complete. "
          "Check the governing rule and any order, and confirm closures with the clerk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
