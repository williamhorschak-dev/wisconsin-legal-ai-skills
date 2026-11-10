"""The dated values table and its check of fixed reference statements.

The reference files are copied to a temporary folder before any edit. Edited numbers are test inputs, not law.
"""
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


class DatedValuesTests(unittest.TestCase):
    def setUp(self):
        self.saved = values.VALUES
        self.addCleanup(lambda: setattr(values, "VALUES", self.saved))
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        shutil.copytree(SKILL / "references", self.root / "references")

    def with_value(self, value_id, new):
        values.VALUES = tuple({**row, "value": new} if row["id"] == value_id else row for row in self.saved)

    def rewrite(self, name, old, new):
        path = self.root / "references" / name
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(old), 1, (name, old))
        path.write_text(text.replace(old, new), encoding="utf-8")

    def check(self, on=None):
        return values.check_references(self.root, on)

    # ---- the table

    def test_table_is_well_formed_and_every_row_names_its_source_and_conditions(self):
        self.assertEqual(values.table_problems(), [])
        for row in values.VALUES:
            with self.subTest(value=row["id"]):
                self.assertTrue(row["source"].startswith("https://docs.legis.wisconsin.gov/document/statutes/"))
                self.assertEqual((row["published"], row["checked"]), ("2026-11-04", "2026-11-09"))
                self.assertTrue(row["note"])
        self.assertEqual(len(values.VALUES), 25)
        managed = {value_id for _, _, template, _ in values.MANAGED_STATEMENTS for ids, _ in values._slots(template) for value_id in ids}
        self.assertEqual(managed | {"unpublished_opinion_persuasive_from", "protected_information_from"},
                         {row["id"] for row in values.VALUES})

    def test_dates_before_the_verified_range_are_refused_not_answered(self):
        for early in ("1900-01-01", "2016-07-01", "2026-11-03"):
            with self.subTest(on=early):
                with self.assertRaises(values.UnsupportedDate):
                    values.value_on("small_claims_other_civil_amount", early)
                with self.assertRaises(values.UnsupportedDate):
                    values.check_references(on=early)
        self.assertEqual(values.value_on("small_claims_other_civil_amount", values.SUPPORTED_FROM)["value"], 10000)
        self.assertEqual(values.value_on("appellate_brief_words")["value"], 11000)
        with self.assertRaises(KeyError):
            values.value_on("no_such_value")

    def test_basis_separates_publication_from_retrieval_and_claims_no_survey_of_later_law(self):
        at_publication = values.basis("2026-11-04")
        self.assertEqual(at_publication, "the statutes published for 2026-11-04, read on 2026-11-09")
        for later in ("2026-11-05", "2026-11-09", "2027-06-01"):
            with self.subTest(on=later):
                text = values.basis(later)
                self.assertIn("published for 2026-11-04, read on 2026-11-09", text)
                self.assertIn("applies that publication's schedule only", text)
                self.assertIn("changes absent from it are not covered", text)
                self.assertNotIn("enacted by then", text)
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("not that none was enacted", source)
        self.assertNotIn("no later change was enacted when", source)

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

    # ---- the check of managed statements

    def test_reference_files_agree_with_the_table_before_and_after_the_change(self):
        for on in (None, "2026-12-31", "2027-01-01", "2028-06-01"):
            with self.subTest(on=on):
                self.assertEqual(values.check_references(on=on), ([], []))

    def test_changing_only_the_table_is_a_disagreement_and_changing_the_reference_restores_agreement(self):
        self.assertEqual(self.check(), ([], []))
        self.with_value("appellate_brief_words", 12000)
        disagreements, unmeasured = self.check()
        self.assertEqual(unmeasured, [])
        self.assertEqual(len(disagreements), 1, disagreements)
        self.assertIn("DISAGREES: states 11,000 for appellate_brief_words; the table has 12000 words", disagreements[0])
        self.rewrite("appellate.md", "**11,000 words**", "**12,000 words**")
        self.assertEqual(self.check(), ([], []))

    def test_a_wrong_number_in_a_managed_statement_is_a_disagreement_on_the_statements_own_date(self):
        self.rewrite("practice-areas.md", "**$5,000** limit for third-party complaints", "**$7,500** limit for third-party complaints")
        disagreements, unmeasured = self.check("2027-03-01")
        self.assertEqual((len(disagreements), unmeasured), (1, []))
        self.assertIn("DISAGREES: states 7,500 for small_claims_tort_amount", disagreements[0])
        self.rewrite("practice-areas.md", "raises both amounts to $15,000 effective January 1, 2027",
                     "raises both amounts to $10,000 effective January 1, 2027")
        disagreements, _ = self.check("2026-11-09")
        dated = [line for line in disagreements if "as of 2027-01-01, the date the statement speaks of" in line]
        self.assertEqual(len(dated), 2, disagreements)
        self.assertTrue(any("small_claims_replevin_value" in line for line in dated))

    def test_an_old_fragment_left_beside_a_changed_number_cannot_pass(self):
        # the three attacks of the second review: a moved number, a hidden old fragment, a second statement
        attacks = {
            "moved number": ("appellate.md", "**minimum 13 point**", "minimum 14 point; the prior wording was **minimum 13 point**"),
            "hidden old fragment": ("appellate.md", "**minimum 13 point**", "minimum 14 point <!-- **minimum 13 point** -->"),
            "trailing text in the cell": ("appellate.md", "**minimum 13 point** |", "**minimum 13 point** (14 for headings) |"),
            "comment inside a sentence": ("circuit-court.md", "- Service by mail: **+3 days**.",
                                          "- Service by mail: **+3 days**<!-- formerly +5 days -->."),
        }
        for label, (name, old, new) in attacks.items():
            with self.subTest(attack=label):
                shutil.rmtree(self.root / "references")
                shutil.copytree(SKILL / "references", self.root / "references")
                self.rewrite(name, old, new)
                disagreements, unmeasured = self.check()
                self.assertEqual(disagreements, [])
                self.assertEqual(len(unmeasured), 1, unmeasured)
                self.assertIn("UNMEASURED: it is not in its reviewed form", unmeasured[0])

    def test_a_second_copy_of_a_managed_statement_cannot_hide_behind_the_first(self):
        path = self.root / "references" / "circuit-court.md"
        original = path.read_text(encoding="utf-8")
        for label, addition in (("contradictory partial copy", "\n- **When the period is less than 12 days, different rules apply.**\n"),
                                ("exact second copy", "\n- Service by mail: **+3 days**.\n"),
                                ("second copy with another number", "\n- Service by mail: **+5 days**.\n")):
            with self.subTest(duplicate=label):
                path.write_text(original + addition, encoding="utf-8")
                disagreements, unmeasured = self.check()
                self.assertEqual(disagreements, [])
                self.assertEqual(len(unmeasured), 1, unmeasured)
                self.assertIn("its opening words occur 2 times, not once", unmeasured[0])

    def test_a_reworded_statement_is_unmeasured_and_unmanaged_prose_is_outside_the_check(self):
        self.rewrite("appellate.md", "**minimum 13 point**", "**at least 13 points**")
        disagreements, unmeasured = self.check()
        self.assertEqual((disagreements, len(unmeasured)), ([], 1))
        path = self.root / "references" / "appellate.md"
        path.write_text(path.read_text(encoding="utf-8").replace("**at least 13 points**", "**minimum 13 point**")
                        + "\nA reply brief may contain 4,000 words.\n", encoding="utf-8")
        self.assertEqual(self.check(), ([], []))

    def test_command_line_exit_codes_and_the_stated_scope(self):
        def run(*args, script=SCRIPT):
            return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, encoding="utf-8",
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        listing = run("--on", "2027-01-02")
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertIn("small_claims_other_civil_amount: 15000 dollars", listing.stdout)
        self.assertIn("applies that publication's schedule only", listing.stdout)
        self.assertEqual(run().returncode, 0)
        for flags in (("--check-references",), ("--check-references", "--on", "2027-01-01")):
            checked = run(*flags)
            self.assertEqual(checked.returncode, 0, checked.stdout)
            self.assertIn("0 disagreement(s) and 0 unmeasured statement(s)", checked.stdout)
            self.assertIn("23 numeric fields in 16 uniquely identified, fixed reference statements", checked.stdout)
            self.assertIn("Other prose, governing-law selection and later legal changes are outside the check", checked.stdout)
        for flags in (("--on", "1900-01-01"), ("--check-references", "--on", "2026-11-03")):
            early = run(*flags)
            self.assertEqual(early.returncode, 2, early.stdout)
            self.assertIn("the first date this table was verified for", early.stderr)
        self.assertEqual(run("--on", "not-a-date").returncode, 2)
        # exit 1 for a disagreement and exit 3 for an unmeasured statement, from a copy of the skill
        copy = self.root / "skill"
        shutil.copytree(SKILL / "scripts", copy / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(SKILL / "references", copy / "references")
        target = copy / "references" / "appellate.md"
        text = target.read_text(encoding="utf-8")
        target.write_text(text.replace("**minimum 13 point**", "**minimum 14 point**"), encoding="utf-8")
        wrong = run("--check-references", script=copy / "scripts" / "wi_values.py")
        self.assertEqual(wrong.returncode, 1, wrong.stdout)
        self.assertIn("DISAGREES: states 14 for appellate_body_point_min", wrong.stdout)
        target.write_text(text.replace("**minimum 13 point**", "**at least 13 points**"), encoding="utf-8")
        reworded = run("--check-references", script=copy / "scripts" / "wi_values.py")
        self.assertEqual(reworded.returncode, 3, reworded.stdout)
        self.assertIn("UNMEASURED", reworded.stdout)


if __name__ == "__main__":
    unittest.main()
