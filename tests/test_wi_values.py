"""The dated values table: structure, date lookups, and agreement with the reference files."""
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
    def test_table_has_one_value_per_id_on_every_date_and_names_its_source(self):
        self.assertEqual(values.table_problems(), [])
        for row in values.VALUES:
            with self.subTest(value=row["id"]):
                self.assertTrue(row["source"].startswith("https://docs.legis.wisconsin.gov/document/statutes/"))
                self.assertRegex(row["checked"], r"^\d{4}-\d{2}-\d{2}$")
                self.assertIn(row["unit"], {"dollars", "words", "pages", "points", "lines", "inches", "days", "date"})

    def test_small_claims_amounts_change_on_january_1_2027(self):
        for value_id in ("small_claims_other_civil_amount", "small_claims_replevin_value"):
            with self.subTest(value=value_id):
                self.assertEqual(values.value_on(value_id, "2026-12-31")["value"], 10000)
                self.assertEqual(values.value_on(value_id, date(2027, 1, 1))["value"], 15000)
                self.assertIn("2025 Wis. Act 105", values.value_on(value_id, "2027-06-01")["authority"])
        self.assertEqual(values.value_on("small_claims_tort_amount", "2027-06-01")["value"], 5000)
        self.assertEqual(values.value_on("appellate_brief_words")["value"], 11000)
        with self.assertRaises(KeyError):
            values.value_on("no_such_value")

    def test_reference_files_agree_with_the_table_today(self):
        self.assertEqual(values.reference_problems(), [])

    def test_stale_small_claims_sentence_fails_the_check_from_the_effective_date(self):
        before = values.reference_problems(on="2026-12-31")
        after = values.reference_problems(on="2027-01-01")
        self.assertEqual(before, [])
        self.assertTrue(any("practice-areas.md" in line and "out of date on 2027-01-01" in line for line in after), after)

    def test_command_line_prints_values_and_exit_code_follows_the_check(self):
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        listing = run("--on", "2027-01-02")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("small_claims_other_civil_amount: 15000 dollars", listing.stdout)
        self.assertEqual(run("--check-references", "--on", "2026-11-09").returncode, 0)
        stale = run("--check-references", "--on", "2027-01-01")
        self.assertEqual(stale.returncode, 1)
        self.assertIn("out of date on 2027-01-01", stale.stdout)
        self.assertEqual(run("--on", "not-a-date").returncode, 2)


if __name__ == "__main__":
    unittest.main()
