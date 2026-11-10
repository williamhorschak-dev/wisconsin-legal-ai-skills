"""The statute vintage screen and its enforcement in the memo linter; every act, order and section is invented."""
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
999.01 HistoryHistory: 1975 c. 325; 1983 a. 228; 2021 a. 77; 2025 a. 999.
999.02999.02 Another synthetic section.
999.02 HistoryHistory: 2031 a. 5.
{BANNER}
"""
QUIET = f"""999.05999.05 A quiet synthetic section.
999.05 HistoryHistory: 1975 c. 325; 2017 a. 207.
{BANNER}
"""
ORDERS = f"""999.07999.07 A synthetic rule of procedure.
999.07 HistoryHistory: Sup. Ct. Order, 83 Wis. 2d xiii (1978); 1991 a. 189, Sup. Ct. Order No. 96-10, 208 Wis. 2d xiii (1997), Sup. Ct. Order No. 18-03, 2020 WI 12, 390 Wis. 2d xv; Sup. Ct. Order No. 20-07, 2021 WI 37, 397 Wis. 2d xiii.
{BANNER}
"""


def kinds(text, on, section):
    return [flag["kind"] for flag in vintage.screen(text, date.fromisoformat(on), section)["flags"]]


class StatuteVintageTests(unittest.TestCase):
    def test_effective_date_note_is_flagged_on_both_sides_without_declaring_the_text_in_force(self):
        before = vintage.screen(PAGE, date(2026, 11, 9), "999.01")
        self.assertEqual([flag["kind"] for flag in before["flags"]], ["effective_date_note"])
        self.assertEqual(before["flags"][0]["identity"], "2025 Wis. Act 999")
        self.assertIn("the operative date is before the stated effective date 2027-01-01", before["flags"][0]["text"])
        self.assertIn("check the amending act and any other amendment", before["flags"][0]["text"])
        self.assertNotIn("text in force is", before["flags"][0]["text"])
        self.assertEqual((before["published"], before["through"], before["last_act"]),
                         ("2026-11-04", "2025 Wis. Act 998", "2025 Wis. Act 999"))
        after = vintage.screen(PAGE, date(2027, 1, 1), "999.01")
        self.assertIn("on or after the stated effective date", after["flags"][0]["text"])
        stale = vintage.screen(PAGE, date(2027, 3, 1), "999.01")
        self.assertIn("stale_copy", [flag["kind"] for flag in stale["flags"]])
        self.assertIn("not a legal safe harbor", [flag["text"] for flag in stale["flags"] if flag["kind"] == "stale_copy"][0])

    def test_history_is_read_for_the_named_section_only_and_wrapping_does_not_hide_an_act(self):
        past = vintage.screen(PAGE, date(2022, 6, 1), "999.01")
        later = [flag["text"] for flag in past["flags"] if flag["kind"] == "later_amendment"]
        self.assertEqual(len(later), 1, later)
        self.assertIn("2025 Wis. Act 999", later[0])
        self.assertFalse(any("2030" in text or "2031" in text or "Act 77" in text for text in later))
        self.assertEqual(kinds(QUIET, "2026-11-09", "999.05"), [])
        self.assertEqual(kinds(QUIET, "2010-01-01", "999.05"), ["later_amendment"])
        wrapped = "999.09999.09 Synthetic.\n999.09 HistoryHistory: 1999 a. 1;\n2025 a. 999.\n999.10999.10 Next.\n999.10 HistoryHistory: 2031 a. 5.\n" + BANNER
        flags = vintage.screen(wrapped, date(2024, 6, 1), "999.09")["flags"]
        self.assertEqual([flag["identity"] for flag in flags], ["2025 Wis. Act 999"])

    def test_supreme_court_orders_are_dated_by_their_citation_not_their_docket_number(self):
        at_2021 = vintage.screen(ORDERS, date(2021, 1, 1), "999.07")["flags"]
        self.assertEqual([flag["identity"] for flag in at_2021], ["Sup. Ct. Order No. 20-07 (2021)"])
        self.assertIn("not its effective date", at_2021[0]["text"])
        at_2019 = [flag["identity"] for flag in vintage.screen(ORDERS, date(2019, 6, 1), "999.07")["flags"]]
        self.assertEqual(at_2019, ["Sup. Ct. Order No. 18-03 (2020)", "Sup. Ct. Order No. 20-07 (2021)"])
        at_2018 = [flag["identity"] for flag in vintage.screen(ORDERS, date(2018, 6, 1), "999.07")["flags"]]
        self.assertIn("Sup. Ct. Order No. 18-03 (2020)", at_2018)
        undated = ORDERS.replace("Sup. Ct. Order, 83 Wis. 2d xiii (1978)", "Sup. Ct. Order, 92 Wis. 2d xiii")
        flags = vintage.screen(undated, date(2022, 1, 1), "999.07")["flags"]
        self.assertEqual([(flag["kind"], flag["identity"]) for flag in flags],
                         [("undated_order", "Sup. Ct. Order, 92 Wis. 2d xiii")])
        self.assertIn("docket number, not its date", flags[0]["text"])
        early = vintage.screen(ORDERS, date(1978, 6, 1), "999.07")["flags"]
        self.assertEqual([flag["identity"] for flag in early][:3],
                         ["1991 Wis. Act 189", "Sup. Ct. Order, 83 Wis. 2d xiii (1978)", "Sup. Ct. Order No. 96-10 (1997)"])
        chapter = vintage.screen(PAGE, date(1975, 6, 1), "999.01")["flags"]
        self.assertEqual(chapter[1]["identity"], "chapter 325, Laws of 1975")
        self.assertEqual(kinds(ORDERS, "2026-11-09", "999.07"), [])

    def test_absent_section_and_unscreenable_copies_are_flagged_and_other_text_is_ignored(self):
        self.assertIsNone(vintage.screen("Synthetic evidence, not law.", date(2026, 11, 9), "999.01"))
        absent = vintage.screen(QUIET.replace("2017 a. 207", "2031 a. 5"), date(2026, 11, 9), "999.01")
        self.assertEqual([flag["kind"] for flag in absent["flags"]], ["section_not_found"])
        self.assertEqual(kinds(QUIET.replace(BANNER, ""), "2026-11-09", "999.05"), ["no_currency_line"])
        self.assertEqual(kinds("999.07999.07 Synthetic.\n" + BANNER, "2026-11-09", "999.07"), ["no_history_note"])
        html = "<html><body><div>999.05999.05 Quiet.</div><div>999.05 HistoryHistory: 2017 a. 207.</div><p>" + BANNER + "</p></body></html>"
        self.assertEqual(kinds(html, "2026-11-09", "999.05"), [])

    def test_command_line_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "Wis-Stat-999.01.md"
            copy.write_text(PAGE, encoding="utf-8")
            run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                               encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            flagged = run(str(copy), "--section", "999.01", "--operative-date", "2026-11-09")
            self.assertEqual(flagged.returncode, 1, flagged.stderr)
            self.assertIn("FLAG  an effective-date NOTE", flagged.stdout)
            self.assertEqual(run(str(copy), "--section", "999.03", "--operative-date", "2026-11-09").returncode, 1)
            quiet = Path(folder) / "quiet.md"
            quiet.write_text(QUIET, encoding="utf-8")
            self.assertEqual(run(str(quiet), "--section", "999.05", "--operative-date", "2026-11-09").returncode, 0)
            other = Path(folder) / "notes.md"
            other.write_text("Synthetic notes.", encoding="utf-8")
            self.assertEqual(run(str(other), "--section", "999.01", "--operative-date", "2026-11-09").returncode, 2)
            self.assertEqual(run(str(copy), "--section", "999.01", "--operative-date", "soon").returncode, 2)
            self.assertEqual(run(str(copy), "--operative-date", "2026-11-09").returncode, 2)


class MemoVintageEnforcementTests(unittest.TestCase):
    NAME = "Wis-Stat-999.01 (synthetic).md"

    def lint(self, text, page=PAGE, name=None, raw=None):
        name = name or self.NAME
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            if raw is not None:
                (root / "sources" / name).write_bytes(raw)
            else:
                (root / "sources" / name).write_text(page, encoding="utf-8")
            path = root / "memo.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, str(LINTER), str(path), "--formal", "--sources", str(root / "sources")],
                                  capture_output=True, text=True, encoding="utf-8",
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def with_row(self, addition):
        base = memo("sources/" + self.NAME)
        row = f"| 1 | Test provision § 900.1 | Condition | No | Test only | Synthetic | `sources/{self.NAME}` | Generated fixture | § 900.1 |"
        self.assertIn(row, base)
        return base.replace(row, row.replace("| Synthetic |", f"| {addition} |"))

    def test_flagged_act_must_be_named_in_full_beside_the_source(self):
        silent = self.lint(memo("sources/" + self.NAME))
        self.assertEqual(silent.returncode, 2, silent.stdout)
        self.assertIn("Name 2025 Wis. Act 999 in visible text", silent.stdout)
        acknowledged = self.lint(self.with_row("Earlier text applies; 2025 Wis. Act 999 takes effect 2027-01-01"))
        self.assertEqual(acknowledged.returncode, 0, acknowledged.stdout)
        self.assertIn("Whether the memo resolves it correctly is not checked", acknowledged.stdout)

    def test_wrong_year_hidden_comment_or_distant_mention_does_not_acknowledge(self):
        cases = {
            "wrong year": self.with_row("See 1999 Wis. Act 999"),
            "number only": self.with_row("See Act 999"),
            "hidden comment": self.with_row("Synthetic <!-- 2025 Wis. Act 999 -->"),
            "elsewhere in the memo": memo("sources/" + self.NAME).replace(
                "The synthetic actor satisfies the synthetic condition.",
                "The synthetic actor satisfies the synthetic condition. 2025 Wis. Act 999 is not yet in effect."),
        }
        for name, text in cases.items():
            with self.subTest(case=name):
                result = self.lint(text)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("Name 2025 Wis. Act 999 in visible text", result.stdout)

    def test_order_flags_and_unscreenable_statute_copies_are_not_silent(self):
        past = self.with_row("Synthetic").replace("operative_date: " + date.today().isoformat(), "operative_date: 2021-01-01")
        orders = ORDERS.replace("999.07", "999.01")
        result = self.lint(past, page=orders)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Name Sup. Ct. Order No. 20-07 (2021) in visible text", result.stdout)
        named = self.lint(past.replace("| Synthetic |", "| Sup. Ct. Order No. 20-07 changed this rule in 2021 |"), page=orders)
        self.assertEqual(named.returncode, 0, named.stdout)
        undated = orders.replace("Sup. Ct. Order, 83 Wis. 2d xiii (1978)", "Sup. Ct. Order, 92 Wis. 2d xiii")
        result = self.lint(past.replace("| Synthetic |", "| Sup. Ct. Order No. 20-07 changed this rule in 2021 |"), page=undated)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Name Sup. Ct. Order, 92 Wis. 2d xiii in visible text", result.stdout)
        both = self.lint(past.replace("| Synthetic |", "| Sup. Ct. Order No. 20-07 (2021); the order at 92 Wis. 2d xiii predates the operative date |"), page=undated)
        self.assertEqual(both.returncode, 0, both.stdout)
        for label, kwargs in (("no signals", dict(page="Synthetic evidence, not law.\n")),
                              ("invalid encoding", dict(raw=b"\xff\xfe\x00bad")),
                              ("oversized", dict(raw=b"x" * 5_000_001))):
            with self.subTest(unscreenable=label):
                result = self.lint(memo("sources/" + self.NAME), **kwargs)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("is cited as a statute copy but could not be screened", result.stdout)
        plain = "synthetic notes.md"
        ordinary = self.lint(memo("sources/" + plain), page="Synthetic evidence, not law.\n", name=plain)
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout)
        quiet = self.lint(memo("sources/" + self.NAME), page=QUIET.replace("999.05", "999.01"))
        self.assertEqual(quiet.returncode, 0, quiet.stdout)


if __name__ == "__main__":
    unittest.main()
