"""The statute vintage screen and its enforcement in the memo linter; every act and section is invented."""
from datetime import date
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from test_memo import LINTER, memo

SCRIPT = LINTER.with_name("statute_vintage.py")
SPEC = importlib.util.spec_from_file_location("statute_vintage_test", SCRIPT)
vintage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(vintage)

BANNER = ("2023-24 Wisconsin Statutes updated through 2025 Wis. Act 998 and through all Supreme Court Orders filed before and "
          "in effect on November 4, 2026. Published and certified under s. 35.18. Changes effective after November 4, 2026, "
          "are designated by NOTES. (Published 11-4-26)")
PAGE = f"""998.99 HistoryHistory: 1999 a. 1; 2030 a. 7.
999.01999.01 Synthetic section.
999.01(1)(1) A synthetic rule applies where the amount is $15,000 or less.
Effective date noteNOTE: Sub. (1) is shown as amended eff. 1-1-27 by 2025 Wis. Act 999. Prior to 1-1-27 it reads:
Effective date text(1) A synthetic rule applies where the amount is $10,000 or less.
999.01 HistoryHistory: 1975 c. 325; 1983 a. 228; 2021 a. 77; 2025 a. 999; Sup. Ct. Order No. 20-07, 2021 WI 37.
999.02999.02 Another synthetic section.
999.02 HistoryHistory: 2031 a. 5.
{BANNER}
"""
QUIET = f"""999.05999.05 A quiet synthetic section.
999.05 HistoryHistory: 1975 c. 325; 2017 a. 207.
{BANNER}
"""


class StatuteVintageTests(unittest.TestCase):
    def kinds(self, text, on, section):
        return [flag["kind"] for flag in vintage.screen(text, date.fromisoformat(on), section)["flags"]]

    def test_effective_date_note_is_flagged_in_both_directions_with_its_act(self):
        before = vintage.screen(PAGE, date(2026, 11, 9), "999.01")
        self.assertEqual([flag["kind"] for flag in before["flags"]], ["effective_date_note"])
        self.assertEqual(before["flags"][0]["act"], "2025 Wis. Act 999")
        self.assertIn("not yet in effect on the operative date", before["flags"][0]["text"])
        self.assertEqual((before["published"], before["through"], before["last_act"]),
                         ("2026-11-04", "2025 Wis. Act 998", "2025 Wis. Act 999"))
        after = vintage.screen(PAGE, date(2027, 1, 1), "999.01")
        self.assertIn("took effect on or before the operative date", after["flags"][0]["text"])
        self.assertIn("stale_copy", self.kinds(PAGE, "2027-03-01", "999.01"))

    def test_history_is_read_for_the_named_section_only_and_past_dates_flag_later_acts(self):
        past = vintage.screen(PAGE, date(2022, 6, 1), "999.01")
        later = [flag["text"] for flag in past["flags"] if flag["kind"] == "later_amendment"]
        self.assertEqual(len(later), 1, later)
        self.assertIn("2025 Wis. Act 999", later[0])
        self.assertFalse(any("2030" in text or "2031" in text or "Act 77" in text for text in later))
        orders = vintage.screen(PAGE, date(2020, 6, 1), "999.01")
        self.assertTrue(any("Sup. Ct. Order No. 20-07" in flag["text"] for flag in orders["flags"]))
        self.assertEqual(self.kinds(QUIET, "2026-11-09", "999.05"), [])
        self.assertEqual(self.kinds(QUIET, "2010-01-01", "999.05"), ["later_amendment"])

    def test_copies_that_cannot_be_screened_are_flagged_and_other_text_is_ignored(self):
        self.assertIsNone(vintage.screen("Synthetic evidence, not law.", date(2026, 11, 9)))
        no_banner = QUIET.replace(BANNER, "")
        self.assertEqual(self.kinds(no_banner, "2026-11-09", "999.05"), ["no_currency_line"])
        no_history = "999.07999.07 Synthetic.\n" + BANNER
        self.assertEqual(self.kinds(no_history, "2026-11-09", "999.07"), ["no_history_note"])
        html = "<html><body><div>999.05 HistoryHistory: 2017 a. 207.</div><p>" + BANNER + "</p></body></html>"
        self.assertEqual(self.kinds(html, "2026-11-09", "999.05"), [])

    def test_command_line_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "Wis-Stat-999.01.md"
            copy.write_text(PAGE, encoding="utf-8")
            run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                               encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            flagged = run(str(copy), "--section", "999.01", "--operative-date", "2026-11-09")
            self.assertEqual(flagged.returncode, 1, flagged.stderr)
            self.assertIn("FLAG  an effective-date note", flagged.stdout)
            self.assertIn("Read the act.", flagged.stdout)
            quiet = Path(folder) / "quiet.md"
            quiet.write_text(QUIET, encoding="utf-8")
            self.assertEqual(run(str(quiet), "--section", "999.05", "--operative-date", "2026-11-09").returncode, 0)
            other = Path(folder) / "notes.md"
            other.write_text("Synthetic notes.", encoding="utf-8")
            self.assertEqual(run(str(other), "--operative-date", "2026-11-09").returncode, 2)
            self.assertEqual(run(str(copy), "--operative-date", "soon").returncode, 2)


class MemoVintageEnforcementTests(unittest.TestCase):
    NAME = "Wis-Stat-999.01 (synthetic).md"

    def lint(self, text, page=PAGE):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            (root / "sources" / self.NAME).write_text(page, encoding="utf-8")
            path = root / "memo.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, str(LINTER), str(path), "--formal", "--sources", str(root / "sources")],
                                  capture_output=True, text=True, encoding="utf-8",
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_memo_citing_a_flagged_copy_must_mention_the_act(self):
        silent = self.lint(memo("sources/" + self.NAME))
        self.assertEqual(silent.returncode, 2, silent.stdout)
        self.assertIn("Statute vintage", silent.stdout)
        self.assertIn("never mentions 2025 Wis. Act 999", silent.stdout)
        addressed = memo("sources/" + self.NAME).replace(
            "The synthetic actor satisfies the synthetic condition.",
            "The synthetic actor satisfies the synthetic condition. 2025 Wis. Act 999 is not yet in effect on the operative "
            "date, so the earlier text applies.")
        fixed = self.lint(addressed)
        self.assertEqual(fixed.returncode, 0, fixed.stdout)
        self.assertIn("which the memo mentions", fixed.stdout)

    def test_unflagged_and_non_statute_sources_do_not_change_the_result(self):
        quiet = self.lint(memo("sources/" + self.NAME), page=QUIET.replace("999.05", "999.01"))
        self.assertEqual(quiet.returncode, 0, quiet.stdout)
        plain = self.lint(memo("sources/" + self.NAME), page="Synthetic evidence, not law.\n")
        self.assertEqual(plain.returncode, 0, plain.stdout)


if __name__ == "__main__":
    unittest.main()
