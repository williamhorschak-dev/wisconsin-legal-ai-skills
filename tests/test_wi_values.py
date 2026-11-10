"""The dated values lookup: its bounded date range, its source basis and its structure."""
from datetime import date
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wisconsin-legal-writing/scripts/wi_values.py"
SPEC = importlib.util.spec_from_file_location("wi_values_test", SCRIPT)
values = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(values)


class DatedValuesTests(unittest.TestCase):
    def setUp(self):
        self.saved = values.VALUES
        self.addCleanup(lambda: setattr(values, "VALUES", self.saved))

    def test_table_is_well_formed_and_every_row_names_its_source_and_conditions(self):
        self.assertEqual(values.table_problems(), [])
        for row in values.VALUES:
            with self.subTest(value=row["id"]):
                self.assertTrue(row["source"].startswith("https://docs.legis.wisconsin.gov/document/statutes/"))
                self.assertEqual((row["published"], row["checked"]), ("2026-11-04", "2026-11-09"))
                self.assertIn(row["unit"], values.UNITS)
                self.assertTrue(row["note"])
        self.assertEqual(len(values.VALUES), 25)
        self.assertEqual(len({row["id"] for row in values.VALUES}), 23)

    def test_dates_before_the_verified_range_are_refused_not_answered(self):
        for early in ("1900-01-01", "2016-07-01", "2026-11-03"):
            with self.subTest(on=early):
                with self.assertRaises(values.UnsupportedDate):
                    values.value_on("small_claims_other_civil_amount", early)
                with self.assertRaises(values.UnsupportedDate):
                    values.basis(early)
        self.assertEqual(values.value_on("small_claims_other_civil_amount", values.SUPPORTED_FROM)["value"], 10000)
        self.assertEqual(values.value_on("appellate_brief_words")["value"], 11000)
        with self.assertRaises(KeyError):
            values.value_on("no_such_value")

    def test_basis_separates_publication_from_retrieval_and_claims_no_survey_of_later_law(self):
        self.assertEqual(values.basis("2026-11-04"), "the statutes published for 2026-11-04, read on 2026-11-09")
        for later in ("2026-11-05", "2026-11-09", "2027-06-01"):
            with self.subTest(on=later):
                text = values.basis(later)
                self.assertIn("published for 2026-11-04, read on 2026-11-09", text)
                self.assertIn("applies that publication's schedule only", text)
                self.assertIn("changes absent from it are not covered", text)
                self.assertNotIn("enacted by then", text)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("not that none was enacted", source)
        self.assertIn("This is a lookup, not a check", source)
        self.assertNotIn("check-references", source)

    def test_small_claims_amounts_change_on_january_1_2027(self):
        for value_id in ("small_claims_other_civil_amount", "small_claims_replevin_value"):
            with self.subTest(value=value_id):
                self.assertEqual(values.value_on(value_id, "2026-12-31")["value"], 10000)
                later = values.value_on(value_id, date(2027, 1, 1))
                self.assertEqual(later["value"], 15000)
                self.assertIn("2025 Wis. Act 105", later["authority"])
                self.assertIn("initial-applicability provision", later["note"])
        self.assertEqual(values.value_on("small_claims_tort_amount", "2027-06-01")["value"], 5000)

    def test_malformed_tables_are_reported(self):
        gap = [dict(row) for row in self.saved]
        next(row for row in gap if row["value"] == 15000)["effective_from"] = "2027-01-03"
        values.VALUES = tuple(gap)
        self.assertTrue(any("not contiguous at 2026-12-31" in line for line in values.table_problems()))
        closed = [dict(row) for row in self.saved]
        next(row for row in closed if row["id"] == "motion_notice_days")["effective_until"] = "2030-01-01"
        values.VALUES = tuple(closed)
        self.assertIn("motion_notice_days: the last row must be open-ended", values.table_problems())
        unnoted = [dict(row) for row in self.saved]
        unnoted[0]["note"] = ""
        values.VALUES = tuple(unnoted)
        self.assertTrue(any("has no note stating its conditions" in line for line in values.table_problems()))

    def test_appeal_period_notes_state_the_trigger_in_each_row(self):
        with_notice = values.value_on("appeal_days_with_notice_of_entry")["note"]
        for phrase in ("Runs from entry of a final judgment or order", "within 21 days after entry of the final judgment or order",
                       "s. 806.06(5)", "a notice given later is not", "exceptions in s. 808.04", "s. 809.50"):
            self.assertIn(phrase, with_notice)
        self.assertIn("entry of a final judgment or order", values.value_on("appeal_days_without_notice_of_entry")["note"])
        interval = values.value_on("notice_of_entry_days")["note"]
        for phrase in ("not an independent deadline or a duty to give notice", "within 21 days after entry of the final judgment or order",
                       "from 90 to 45 days", "exceptions in s. 808.04"):
            self.assertIn(phrase, interval)
        self.assertIn("not this number or fewer", values.value_on("short_period_threshold_days")["note"])
        self.assertIn("only to the portions in s. 809.19(1)(d), (e) and (f)", values.value_on("appellate_brief_pages_monospaced")["note"])

    def test_command_line_prints_values_and_refuses_unsupported_dates(self):
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        listing = run("--on", "2027-01-02")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("small_claims_other_civil_amount: 15000 dollars", listing.stdout)
        self.assertIn("applies that publication's schedule only", listing.stdout)
        self.assertIn("This is a lookup; it does not check the reference files", listing.stdout)
        self.assertEqual(run().returncode, 0)
        early = run("--on", "1900-01-01")
        self.assertEqual(early.returncode, 2, early.stdout)
        self.assertIn("the first date this table was verified for", early.stderr)
        self.assertEqual(run("--on", "not-a-date").returncode, 2)
        self.assertEqual(run("--check-references").returncode, 2)


if __name__ == "__main__":
    unittest.main()
