"""The dated values table: its bounded date range, its structure, and agreement with the reference files."""
from datetime import date
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/wisconsin-legal-writing"
SCRIPT = SKILL / "scripts/wi_values.py"
SPEC = importlib.util.spec_from_file_location("wi_values_test", SCRIPT)
values = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(values)


def copy_of_references(folder):
    shutil.copytree(SKILL / "references", Path(folder) / "references")
    return Path(folder)


def rewrite(root, name, old, new):
    path = root / "references" / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (name, old, text.count(old))
    path.write_text(text.replace(old, new), encoding="utf-8")


class DatedValuesTests(unittest.TestCase):
    def setUp(self):
        self.saved = values.VALUES
        self.addCleanup(lambda: setattr(values, "VALUES", self.saved))

    def with_value(self, value_id, new):
        values.VALUES = tuple({**row, "value": new} if row["id"] == value_id else row for row in self.saved)

    def test_table_is_well_formed_and_every_row_names_its_source_and_conditions(self):
        self.assertEqual(values.table_problems(), [])
        for row in values.VALUES:
            with self.subTest(value=row["id"]):
                self.assertTrue(row["source"].startswith("https://docs.legis.wisconsin.gov/document/statutes/"))
                self.assertEqual(row["checked"], values.CHECKED)
                self.assertTrue(row["note"])
        self.assertEqual(len(values.VALUES), 25)
        self.assertEqual({item[0] for item in values.REFERENCE_STATEMENTS} | {"unpublished_opinion_persuasive_from",
                         "protected_information_from"}, {row["id"] for row in values.VALUES})

    def test_dates_before_the_verified_range_are_refused_not_answered(self):
        for early in ("1900-01-01", "2016-07-01", "2026-11-03"):
            with self.subTest(on=early):
                with self.assertRaises(values.UnsupportedDate):
                    values.value_on("small_claims_other_civil_amount", early)
                with self.assertRaises(values.UnsupportedDate):
                    values.reference_problems(on=early)
        self.assertEqual(values.value_on("small_claims_other_civil_amount", values.SUPPORTED_FROM)["value"], 10000)
        self.assertEqual(values.value_on("appellate_brief_words")["value"], 11000)
        with self.assertRaises(KeyError):
            values.value_on("no_such_value")
        self.assertIn("published for 2026-11-04", values.basis("2026-11-09"))
        self.assertIn("an act passed after 2026-11-09 is not in this table", values.basis("2027-06-01"))

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

    def test_appeal_period_notes_state_trigger_condition_and_exceptions(self):
        with_notice = values.value_on("appeal_days_with_notice_of_entry")["note"]
        for phrase in ("entry of a final judgment or order", "within 21 days", "s. 806.06(5)", "a notice given later is not",
                       "exceptions in s. 808.04", "s. 809.50"):
            self.assertIn(phrase, with_notice)
        self.assertIn("entry of a final judgment or order", values.value_on("appeal_days_without_notice_of_entry")["note"])
        self.assertIn("Not a deadline of its own", values.value_on("notice_of_entry_days")["note"])
        self.assertIn("not this number or fewer", values.value_on("short_period_threshold_days")["note"])

    def test_reference_files_agree_with_the_table_before_and_after_the_change(self):
        for on in (None, "2026-12-31", "2027-01-01", "2028-06-01"):
            with self.subTest(on=on):
                self.assertEqual(values.reference_problems(on=on), [])

    def test_changing_only_the_table_creates_a_mismatch_and_changing_the_reference_restores_agreement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = copy_of_references(folder)
            self.assertEqual(values.reference_problems(root), [])
            self.with_value("appellate_brief_words", 12000)
            problems = values.reference_problems(root)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("DISAGREES: states 11,000 for appellate_brief_words; the table has 12000 words", problems[0])
            rewrite(root, "appellate.md", "**11,000 words**", "**12,000 words**")
            self.assertEqual(values.reference_problems(root), [])

    def test_wrong_present_tense_number_fails_and_accurate_dated_history_does_not(self):
        with tempfile.TemporaryDirectory() as folder:
            root = copy_of_references(folder)
            rewrite(root, "practice-areas.md", "**$5,000** limit for third-party complaints",
                    "**$7,500** limit for third-party complaints")
            wrong = values.reference_problems(root, on="2027-03-01")
            self.assertEqual(len(wrong), 1, wrong)
            self.assertIn("DISAGREES: states 7,500 for small_claims_tort_amount", wrong[0])
        with tempfile.TemporaryDirectory() as folder:
            root = copy_of_references(folder)
            rewrite(root, "practice-areas.md", "raises both amounts to $15,000 effective January 1, 2027",
                    "raises both amounts to $10,000 effective January 1, 2027")
            wrong = values.reference_problems(root, on="2026-11-09")
            self.assertEqual(len(wrong), 2, wrong)
            self.assertTrue(all("as of 2027-01-01, the date the sentence speaks of" in line for line in wrong))
        with tempfile.TemporaryDirectory() as folder:
            root = copy_of_references(folder)
            rewrite(root, "circuit-court.md", "Service by mail: **+3 days**.", "Service by mail adds time.")
            missing = values.reference_problems(root)
            self.assertEqual(len(missing), 1, missing)
            self.assertIn("NOT FOUND: the sentence that states service_by_mail_added_days", missing[0])

    def test_command_line_prints_values_and_refuses_unsupported_dates(self):
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        listing = run("--on", "2027-01-02")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("small_claims_other_civil_amount: 15000 dollars", listing.stdout)
        self.assertIn("an act passed after 2026-11-09 is not in this table", listing.stdout)
        self.assertEqual(run().returncode, 0)
        for flags in (("--check-references",), ("--check-references", "--on", "2027-01-01")):
            checked = run(*flags)
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertIn("0 problem(s) across 23 reference sentences", checked.stdout)
        for flags in (("--on", "1900-01-01"), ("--check-references", "--on", "2026-11-03")):
            early = run(*flags)
            self.assertEqual(early.returncode, 2, early.stdout)
            self.assertIn("the first date this table was verified for", early.stderr)
        self.assertEqual(run("--on", "not-a-date").returncode, 2)


if __name__ == "__main__":
    unittest.main()
