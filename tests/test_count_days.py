"""The s. 801.15 day counter: holiday rules, counting, and the cases it refuses. Dates only; no matter facts."""
from datetime import date
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wisconsin-legal-writing/scripts/count_days.py"
SPEC = importlib.util.spec_from_file_location("count_days_test", SCRIPT)
counter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(counter)
D = date.fromisoformat


class HolidayRuleTests(unittest.TestCase):
    def test_holidays_for_the_verified_years_follow_the_statutory_rules(self):
        expected = {
            2026: ["2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19", "2026-07-04",
                   "2026-08-11", "2026-09-07", "2026-10-12", "2026-11-03", "2026-11-11", "2026-11-26", "2026-12-24",
                   "2026-12-25", "2026-12-31"],
            2027: ["2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-19", "2027-07-04",
                   "2027-07-05", "2027-09-06", "2027-10-11", "2027-11-11", "2027-11-25", "2027-12-24", "2027-12-25",
                   "2027-12-31"],
        }
        for year, days in expected.items():
            with self.subTest(year=year):
                self.assertEqual(sorted(day.isoformat() for day in counter.holidays(year)), days)
        names = counter.holidays(2026)
        self.assertIn("s. 801.15(1)(a)", names[D("2026-04-03")][0])
        self.assertIn("s. 5.02(12s)", names[D("2026-08-11")][0])
        self.assertIn("s. 5.02(5)", names[D("2026-11-03")][0])
        self.assertEqual(names[D("2026-12-24")], ["December 24, s. 230.35(4)(a)"])
        self.assertEqual(len(counter.holidays(2027)[D("2027-07-05")]), 2)
        self.assertEqual(counter.VERIFIED_YEARS, (2026, 2027))


class CountingTests(unittest.TestCase):
    def test_short_period_excludes_weekends_and_holidays_and_long_period_does_not(self):
        short = counter.compute(D("2026-11-09"), 5, "after", closures_stated=True)
        self.assertEqual(short["act_by"], D("2026-11-17"))
        labels = dict(short["readings"][0][2])
        self.assertIn("not counted", labels[D("2026-11-09")])
        self.assertIn("November 11, s. 995.20", labels[D("2026-11-11")])
        self.assertIn("Saturday", labels[D("2026-11-14")])
        self.assertEqual(labels[D("2026-11-17")], "day 5")
        election = counter.compute(D("2026-10-29"), 5, "after", closures_stated=True)
        self.assertEqual(election["act_by"], D("2026-11-06"))
        ten = counter.compute(D("2026-11-09"), 10, "after", closures_stated=True)
        self.assertEqual(ten["act_by"], D("2026-11-24"))
        eleven = counter.compute(D("2026-11-09"), 11, "after", closures_stated=True)
        self.assertEqual(eleven["act_by"], D("2026-11-20"))

    def test_last_day_on_a_closed_day_reports_both_neighbours_and_uses_the_earlier(self):
        result = counter.compute(D("2026-11-09"), 20, "after", closures_stated=True)
        self.assertEqual(result["computed"], D("2026-11-29"))
        self.assertEqual((result["act_by"], result["next_open"]), (D("2026-11-27"), D("2026-11-30")))
        self.assertIn("does not say in terms what follows", " ".join(result["notes"]))
        closed = counter.compute(D("2026-11-09"), 20, "after", clerk_closed={D("2026-11-27")})
        self.assertEqual(closed["act_by"], D("2026-11-25"))

    def test_last_day_on_a_holiday_is_refused_until_the_closure_is_stated(self):
        with self.assertRaisesRegex(counter.Refused, "2026-11-11.*--clerk-closed 2026-11-11 or --clerk-open 2026-11-11"):
            counter.compute(D("2026-10-28"), 14, "after", clerk_closed={D("2026-12-01")})
        self.assertEqual(counter.compute(D("2026-10-28"), 14, "after", clerk_open={D("2026-11-11")})["act_by"], D("2026-11-11"))
        closed = counter.compute(D("2026-10-28"), 14, "after", clerk_closed={D("2026-11-11")})
        self.assertEqual((closed["act_by"], closed["next_open"]), (D("2026-11-10"), D("2026-11-12")))
        stated = counter.compute(D("2026-10-28"), 14, "after", closures_stated=True)
        self.assertEqual(stated["act_by"], D("2026-11-11"))
        self.assertIn("treated as open", " ".join(stated["notes"]))

    def test_service_additions_show_both_readings_and_use_the_earlier_date(self):
        same = counter.compute(D("2026-11-09"), 5, "after", "mail", closures_stated=True)
        self.assertEqual(len(same["readings"]), 2)
        self.assertEqual({reading[1] for reading in same["readings"]}, {D("2026-11-20")})
        differ = counter.compute(D("2026-11-09"), 8, "after", "mail", closures_stated=True)
        self.assertEqual(sorted(reading[1] for reading in differ["readings"]), [D("2026-11-20"), D("2026-11-23")])
        self.assertEqual(differ["act_by"], D("2026-11-20"))
        self.assertIn("the earlier date is used", " ".join(differ["notes"]))
        late = counter.compute(D("2026-11-09"), 20, "after", "late-electronic", closures_stated=True)
        self.assertEqual(late["computed"], D("2026-11-30"))

    def test_counting_back_from_a_hearing_and_the_combinations_that_are_refused(self):
        back = counter.compute(D("2026-11-20"), 5, "before", closures_stated=True)
        self.assertEqual(back["act_by"], D("2026-11-13"))
        with self.assertRaisesRegex(counter.Refused, "counted back from a hearing"):
            counter.compute(D("2026-11-20"), 5, "before", "mail", closures_stated=True)
        with self.assertRaisesRegex(counter.Refused, "clerk of courts office is closed"):
            counter.compute(D("2026-11-09"), 5, "after")
        with self.assertRaisesRegex(counter.Refused, "outside the years"):
            counter.compute(D("2027-12-28"), 5, "after", closures_stated=True)
        with self.assertRaises(ValueError):
            counter.compute(D("2026-11-09"), 0, "after", closures_stated=True)

    def test_command_line_shows_the_work_and_exit_codes_follow_refusals(self):
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        done = run("--event", "2026-11-09", "--days", "5", "--direction", "after", "--no-other-closures")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("2026-11-11 Wed  excluded (holiday: November 11, s. 995.20)", done.stdout)
        self.assertIn("Act on or before: Tuesday 2026-11-17", done.stdout)
        self.assertIn("does not decide whether s. 801.15 governs this deadline", done.stdout)
        refused = run("--event", "2026-11-09", "--days", "5", "--direction", "after")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("NOT COMPUTED", refused.stdout)
        self.assertEqual(run("--days", "5").returncode, 2)
        listing = run("--holidays", "2026")
        self.assertEqual(listing.returncode, 0)
        self.assertIn("2026-04-03 Friday    Good Friday", listing.stdout)
        self.assertEqual(run("--holidays", "2030").returncode, 1)


if __name__ == "__main__":
    unittest.main()
