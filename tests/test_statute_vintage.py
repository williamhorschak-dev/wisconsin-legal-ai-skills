"""The statute vintage screen and its enforcement in the memo linter.

Synthetic provisions use illustrative citation forms; they do not establish the content or legal effect of any
real act or order.
"""
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


def page(history, section="999.07"):
    return f"{section}{section} A synthetic rule of procedure.\n{section} HistoryHistory: {history}\n{BANNER}\n"


def flags(text, on, section="999.07"):
    return vintage.screen(text, date.fromisoformat(on), section)["flags"]


def named(text, on, section="999.07"):
    return [flag["identity"] for flag in flags(text, on, section)]


def kinds(text, on, section="999.07"):
    return [flag["kind"] for flag in flags(text, on, section)]


class HistoryGrammarTests(unittest.TestCase):
    def test_every_number_of_a_grouped_entry_is_read_and_section_suffixes_are_not_acts(self):
        entries, complete = vintage.parse_history("1975 c. 325, 365, 422; 1979 c. 32 ss. 66, 92 (16); 1987 a. 208, 378, 403; "
                                                  "2005 a. 443, s. 265; 1983 a. 30 ss. 4 to 11, 14; 2013 a. 20 ss. 2365m, 9448; "
                                                  "Stats. 1979 s. 999.01; 2025 a.998,999.")
        self.assertTrue(complete)
        self.assertEqual([entry["identity"] for entry in entries], [
            "chapter 325, Laws of 1975", "chapter 365, Laws of 1975", "chapter 422, Laws of 1975", "chapter 32, Laws of 1979",
            "1987 Wis. Act 208", "1987 Wis. Act 378", "1987 Wis. Act 403", "2005 Wis. Act 443", "1983 Wis. Act 30",
            "2013 Wis. Act 20", "Stats. 1979 s. 999.01", "2025 Wis. Act 998", "2025 Wis. Act 999"])
        self.assertNotIn("unread", {entry["kind"] for entry in entries})

    def test_supreme_court_orders_in_every_published_shape(self):
        shapes = {
            "Sup. Ct. Order, 83 Wis. 2d xiii (1978)": [("Sup. Ct. Order, 83 Wis. 2d xiii", 1978, None)],
            "Sup Ct. Order, 130 Wis. 2d xi (1986)": [("Sup. Ct. Order, 130 Wis. 2d xi", 1986, None)],
            "Sup. Ct. Order, 67 Wis. 2d 585, 776 (1975)": [("Sup. Ct. Order, 67 Wis. 2d 585, 776", 1975, None)],
            "Sup. Ct. Order, 67 Wis. 2d 585, 597 (1975), 758": [("Sup. Ct. Order, 67 Wis. 2d 585, 597, 758", 1975, None)],
            "Sup. Ct. Order, 171 Wis. 2d xiii, xvii, xxxvii (1992)": [("Sup. Ct. Order, 171 Wis. 2d xiii, xvii, xxxvii", 1992, None)],
            "Sup. Ct. Order, 92 Wis. 2d xiii": [("Sup. Ct. Order, 92 Wis. 2d xiii", None, None)],
            "Sup. Ct. Order No. 96-10, 208 Wis. 2d xiii (1997)": [("Sup. Ct. Order No. 96-10", 1997, None)],
            "Sup. Ct. Order No. 18-03, 2020 WI 12, 390 Wis. 2d xv": [("Sup. Ct. Order No. 18-03", 2020, None)],
            "Sup. Ct. Order No. 17-05, 2017 WI 95, filed 11-9-17, eff. 7-1-18": [("Sup. Ct. Order No. 17-05", 2017, date(2018, 7, 1))],
            "Sup. Ct. Order No. 10-01 and Sup. Ct. Order No. 10-02, 2010 WI 42, 323 Wis. 2d xxiii":
                [("Sup. Ct. Order No. 10-01", 2010, None), ("Sup. Ct. Order No. 10-02", 2010, None)],
            "Sup. Ct. Order, 2001 WI 135": [("Sup. Ct. Order, 2001 WI 135", 2001, None)],
        }
        for text, expected in shapes.items():
            with self.subTest(order=text):
                entries, _ = vintage.parse_history(text + ".")
                self.assertEqual([(e["identity"], e["year"], e["effective"]) for e in entries], expected)
                self.assertEqual({e["kind"] for e in entries}, {"order"})
        mixed, _ = vintage.parse_history("1991 a. 189, Sup. Ct. Order No. 96-10, 208 Wis. 2d xiii (1997), Sup. Ct. Order No. 01-04, "
                                         "2001 WI 135, 248 Wis. 2d xvii; Sup. Ct. Order No. 08-02, 2009 WI 2, 311 Wis. 2d xxv.")
        self.assertEqual([(e["identity"], e["year"]) for e in mixed], [
            ("1991 Wis. Act 189", 1991), ("Sup. Ct. Order No. 96-10", 1997), ("Sup. Ct. Order No. 01-04", 2001),
            ("Sup. Ct. Order No. 08-02", 2009)])

    def test_an_entry_that_fits_no_form_is_kept_word_for_word_and_a_cut_off_note_is_noticed(self):
        entries, complete = vintage.parse_history("1999 a. 1; s. 13.92 (2) (i); Sup. Ct. Order (1975); corrected by revisor; 2001 a. 16.")
        self.assertTrue(complete)
        self.assertEqual([(e["kind"], e["identity"]) for e in entries], [
            ("act", "1999 Wis. Act 1"), ("unread", "s. 13.92 (2) (i)"), ("unread", "Sup. Ct. Order (1975)"),
            ("unread", "corrected by revisor"), ("act", "2001 Wis. Act 16")])
        for cut in ("1999 a. 1; 2025 a", "1999 a. 1; 2025 a. 999;", "1999 a. 1; Stats. 1979 s"):
            with self.subTest(cut=cut):
                self.assertFalse(vintage.parse_history(cut)[1])

    def test_a_note_wrapped_at_any_word_reads_the_same_or_is_flagged(self):
        history = ("1975 c. 325, 365; 1987 a. 208, 378; Sup. Ct. Order, 67 Wis. 2d 585, 776 (1975); Sup Ct. Order No. 20-07, "
                   "2021 WI 37, 397 Wis. 2d xiii; Stats. 1979 s. 999.07; 2025 a. 998, 999.")
        whole = named(page(history), "1974-06-01")
        self.assertEqual(len(whole), 9)
        words = history.split(" ")
        for cut in range(1, len(words)):
            wrapped = " ".join(words[:cut]) + "\n" + " ".join(words[cut:])
            with self.subTest(wrap_before=words[cut]):
                result = flags(page(wrapped), "1974-06-01")
                if [flag["identity"] for flag in result] != whole:
                    # the only wrap that changes the reading puts a section number at the start of a line
                    self.assertEqual(words[cut], "999.07;")
                    self.assertIn("unread_history_entry", [flag["kind"] for flag in result])
        following = page(history) + "999.07 AnnotationA synthetic annotation mentions 2031 a. 5.\n999.08999.08 Next.\n999.08 HistoryHistory: 2032 a. 6.\n"
        self.assertEqual(named(following, "1974-06-01"), whole)


class StatuteVintageTests(unittest.TestCase):
    def test_effective_date_note_is_flagged_on_both_sides_without_declaring_the_text_in_force(self):
        before = vintage.screen(PAGE, date(2026, 11, 9), "999.01")
        self.assertEqual([flag["kind"] for flag in before["flags"]], ["effective_date_note"])
        self.assertEqual(before["flags"][0]["identity"], "2025 Wis. Act 999")
        self.assertIn("the operative date is before the stated effective date 2027-01-01", before["flags"][0]["text"])
        self.assertIn("check the amending act and any other amendment", before["flags"][0]["text"])
        self.assertNotIn("text in force is", before["flags"][0]["text"])
        self.assertEqual((before["published"], before["through"], before["last_act"], before["entries"]),
                         ("2026-11-04", "2025 Wis. Act 998", "2025 Wis. Act 999", 4))
        after = vintage.screen(PAGE, date(2027, 1, 1), "999.01")
        self.assertIn("on or after the stated effective date", after["flags"][0]["text"])
        stale = vintage.screen(PAGE, date(2027, 3, 1), "999.01")
        self.assertIn("not a legal safe harbor", [flag["text"] for flag in stale["flags"] if flag["kind"] == "stale_copy"][0])

    def test_history_is_read_for_the_named_section_only(self):
        past = [flag for flag in flags(PAGE, "2022-06-01", "999.01") if flag["kind"] == "later_amendment"]
        self.assertEqual([flag["identity"] for flag in past], ["2021 Wis. Act 77", "2025 Wis. Act 999"])
        self.assertFalse(any("2030" in flag["text"] or "2031" in flag["text"] for flag in past))
        self.assertIsNone(vintage.screen("Synthetic evidence, not law.", date(2026, 11, 9), "999.01"))
        self.assertEqual(kinds(PAGE, "2026-11-09", "999.03"), ["section_not_found"])
        self.assertEqual(kinds(page("2017 a. 207.").replace(BANNER, ""), "2026-11-09"), ["no_currency_line"])
        self.assertEqual(kinds("999.07999.07 Synthetic.\n" + BANNER, "2026-11-09"), ["no_history_note"])
        html = "<html><body><div>999.07999.07 Quiet.</div><div>999.07 HistoryHistory: 2017 a. 207.</div><p>" + BANNER + "</p></body></html>"
        self.assertEqual(kinds(html, "2026-11-09"), [])

    def test_grouped_acts_and_both_order_spellings_are_flagged_one_by_one(self):
        self.assertEqual(named(page("1999 a. 1; 2025 a. 998, 999."), "2025-06-01"), ["2025 Wis. Act 998", "2025 Wis. Act 999"])
        self.assertEqual(named(page("1975 c. 998, 999."), "1975-06-01"), ["chapter 998, Laws of 1975", "chapter 999, Laws of 1975"])
        self.assertEqual(named(page("Sup Ct. Order No. 20-07, 2021 WI 37."), "2020-06-01"), ["Sup. Ct. Order No. 20-07"])
        self.assertEqual(named(page("Sup. Ct. Order, 67 Wis. 2d 585, 776 (1975)."), "1974-06-01"),
                         ["Sup. Ct. Order, 67 Wis. 2d 585, 776"])

    def test_orders_are_dated_by_their_citation_or_stated_effective_date_never_by_docket_number(self):
        orders = page("Sup. Ct. Order, 83 Wis. 2d xiii (1978); Sup. Ct. Order No. 18-03, 2020 WI 12, 390 Wis. 2d xv; "
                      "Sup. Ct. Order No. 20-07, 2021 WI 37, 397 Wis. 2d xiii.")
        at_2021 = flags(orders, "2021-01-01")
        self.assertEqual([flag["identity"] for flag in at_2021], ["Sup. Ct. Order No. 18-03", "Sup. Ct. Order No. 20-07"])
        self.assertIn("the year appearing in the order's citation; it does not establish the order's adoption date or effective date",
                      at_2021[1]["text"])
        self.assertEqual(named(orders, "2026-11-09"), [])
        undated = flags(page("Sup. Ct. Order, 92 Wis. 2d xiii; 1999 a. 1."), "2022-01-01")
        self.assertEqual([(flag["kind"], flag["identity"]) for flag in undated], [("undated_entry", "Sup. Ct. Order, 92 Wis. 2d xiii")])
        dated = page("Sup. Ct. Order No. 17-05, 2017 WI 95, filed 11-9-17, eff. 7-1-18.")
        self.assertEqual(named(dated, "2018-03-01"), ["Sup. Ct. Order No. 17-05"])
        self.assertIn("with an effective date of 2018-07-01, after the operative date", flags(dated, "2018-03-01")[0]["text"])
        self.assertEqual(named(dated, "2018-07-01"), [])
        self.assertEqual(named(dated, "2019-03-01"), [])

    def test_an_entry_dated_the_year_before_the_operative_year_is_flagged_and_the_limit_is_stated(self):
        delayed = page("2024 a. 50; 2025 a. 105.")
        self.assertEqual(named(delayed, "2026-06-01"), ["2025 Wis. Act 105"])
        self.assertEqual(named(delayed, "2025-06-01"), ["2024 Wis. Act 50", "2025 Wis. Act 105"])
        self.assertEqual(kinds(delayed, "2027-06-01"), ["stale_copy"])
        self.assertEqual(vintage.LOOK_BACK_YEARS, 1)
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "Wis-Stat-999.07.md"
            copy.write_text(delayed, encoding="utf-8")
            clean = subprocess.run([sys.executable, str(SCRIPT), str(copy), "--section", "999.07", "--operative-date", "2026-11-09"],
                                   capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(clean.returncode, 0, clean.stdout)
        self.assertIn("an entry dated more than 1 year before the operative year is assumed to have taken effect by then, which "
                      "this script does not check", clean.stdout)
        self.assertIn("2 History entries read", clean.stdout)

    def test_unread_entries_and_cut_off_notes_are_flagged_only_when_the_history_decides_the_result(self):
        odd = page("1999 a. 1; s. 13.92 (2) (i); 2001 a. 16.")
        result = flags(odd, "2010-06-01")
        self.assertEqual([(flag["kind"], flag["identity"]) for flag in result], [("unread_history_entry", "s. 13.92 (2) (i)")])
        self.assertIn("an entry this script cannot read", result[0]["text"])
        self.assertEqual(kinds(odd, "2026-11-09"), [])
        cut = page("1999 a. 1; 2025 a")
        self.assertEqual(kinds(cut, "2010-06-01"), ["history_incomplete", "unread_history_entry"])
        self.assertEqual(kinds(cut, "2026-11-09"), [])

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
            quiet.write_text(page("1975 c. 325; 2017 a. 207."), encoding="utf-8")
            self.assertEqual(run(str(quiet), "--section", "999.07", "--operative-date", "2026-11-09").returncode, 0)
            other = Path(folder) / "notes.md"
            other.write_text("Synthetic notes.", encoding="utf-8")
            self.assertEqual(run(str(other), "--section", "999.01", "--operative-date", "2026-11-09").returncode, 2)
            self.assertEqual(run(str(copy), "--section", "999.01", "--operative-date", "soon").returncode, 2)
            self.assertEqual(run(str(copy), "--operative-date", "2026-11-09").returncode, 2)


class MemoVintageEnforcementTests(unittest.TestCase):
    NAME = "Wis-Stat-999.01 (synthetic).md"
    ANCHOR = "is a generated test file, not a retrieved legal source."

    def lint(self, text, page_text=PAGE, name=None, raw=None):
        name = name or self.NAME
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            if raw is not None:
                (root / "sources" / name).write_bytes(raw)
            else:
                (root / "sources" / name).write_text(page_text, encoding="utf-8")
            path = root / "memo.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run([sys.executable, str(LINTER), str(path), "--formal", "--sources", str(root / "sources")],
                                  capture_output=True, text=True, encoding="utf-8",
                                  env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def with_lines(self, *lines, operative=None):
        base = memo("sources/" + self.NAME)
        self.assertEqual(base.count(self.ANCHOR), 1)
        text = base.replace(self.ANCHOR, self.ANCHOR + "\n\n" + "\n".join(lines) + "\n")
        if operative:
            today = "operative_date: " + date.today().isoformat()
            self.assertIn(today, text)
            text = text.replace(today, "operative_date: " + operative)
        return text

    def ack(self, identity, name=None, note="the earlier text applies on the operative date"):
        return f"Vintage acknowledgement: {name or self.NAME} | {identity} | {note}"

    def test_a_flagged_act_needs_a_plain_text_acknowledgement_line_naming_the_source_and_the_act(self):
        silent = self.lint(memo("sources/" + self.NAME))
        self.assertEqual(silent.returncode, 2, silent.stdout)
        self.assertIn(f"Vintage acknowledgement: {self.NAME} | 2025 Wis. Act 999 | <what the memo does about it>", silent.stdout)
        for line in (self.ack("2025 Wis. Act 999"), "- " + self.ack("2025 Wis. Act 999")):
            done = self.lint(self.with_lines(line))
            self.assertEqual(done.returncode, 0, done.stdout)
            self.assertIn("occur together in a plain-text acknowledgement line", done.stdout)
            self.assertIn("it does not establish that the source version or the legal analysis is correct", done.stdout)

    def test_what_does_not_acknowledge(self):
        row = f"| 9 | {self.NAME} | 2025 Wis. Act 999 | acknowledged in a table |"
        cases = {
            "wrong year": self.ack("1999 Wis. Act 999"),
            "number only": self.ack("Act 999"),
            "longer number": self.ack("2025 Wis. Act 9990"),
            "another source": self.ack("2025 Wis. Act 999", name="Wis-Stat-999.02 (synthetic).md"),
            "no source": "Vintage acknowledgement: 2025 Wis. Act 999 applies later",
            "table row": row,
            "ordinary sentence": f"The copy {self.NAME} shows 2025 Wis. Act 999, which is not yet in effect.",
            "html comment": "<!-- " + self.ack("2025 Wis. Act 999") + " -->",
        }
        for label, line in cases.items():
            with self.subTest(case=label):
                result = self.lint(self.with_lines(line))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("| 2025 Wis. Act 999 | <what the memo does about it>", result.stdout)
        hidden = {
            "link title": f'Vintage acknowledgement: {self.NAME} | [explanation](https://example.invalid "2025 Wis. Act 999")',
            "link text": f"Vintage acknowledgement: {self.NAME} | [2025 Wis. Act 999](https://example.invalid)",
            "hidden span": f'Vintage acknowledgement: {self.NAME} | <span hidden>2025 Wis. Act 999</span>',
        }
        for label, line in hidden.items():
            with self.subTest(hidden=label):
                result = self.lint(self.with_lines(line))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("line must be plain text: no links, images or HTML", result.stdout)
                self.assertIn("| 2025 Wis. Act 999 | <what the memo does about it>", result.stdout)

    def test_each_member_of_a_group_and_each_order_needs_its_own_identity(self):
        grouped = page("1999 a. 1; 2025 a. 998, 999.", "999.01")
        one = self.lint(self.with_lines(self.ack("2025 Wis. Act 998"), operative="2025-06-01"), page_text=grouped)
        self.assertEqual(one.returncode, 2, one.stdout)
        self.assertIn("| 2025 Wis. Act 999 | <what the memo does about it>", one.stdout)
        both = self.lint(self.with_lines(self.ack("2025 Wis. Act 998"), self.ack("2025 Wis. Act 999"), operative="2025-06-01"),
                         page_text=grouped)
        self.assertEqual(both.returncode, 0, both.stdout)
        numeric = page("Sup. Ct. Order, 67 Wis. 2d 585, 776 (1975).", "999.01")
        for label, line in (("bare words", self.ack("Supreme Court Order")), ("generic", self.ack("Sup. Ct. Order")),
                            ("another page", self.ack("Sup. Ct. Order, 67 Wis. 2d 585, 598")),
                            ("another volume", self.ack("Sup. Ct. Order, 68 Wis. 2d 585, 776")),
                            ("year only", self.ack("Sup. Ct. Order (1975)"))):
            with self.subTest(order=label):
                result = self.lint(self.with_lines(line, operative="1974-06-01"), page_text=numeric)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("| Sup. Ct. Order, 67 Wis. 2d 585, 776 | <what the memo does about it>", result.stdout)
        exact = self.lint(self.with_lines(self.ack("Sup. Ct. Order, 67 Wis. 2d 585, 776"), operative="1974-06-01"), page_text=numeric)
        self.assertEqual(exact.returncode, 0, exact.stdout)
        odd = page("1999 a. 1; s. 13.92 (2) (i).", "999.01")
        unread = self.lint(self.with_lines("A synthetic note.", operative="2010-06-01"), page_text=odd)
        self.assertEqual(unread.returncode, 2, unread.stdout)
        self.assertIn("an entry this script cannot read", unread.stdout)
        read = self.lint(self.with_lines(self.ack("s. 13.92 (2) (i)", note="read; a revisor's correction"), operative="2010-06-01"),
                         page_text=odd)
        self.assertEqual(read.returncode, 0, read.stdout)

    def test_unscreenable_and_cut_off_statute_copies_are_not_silent_and_other_sources_are_ignored(self):
        for label, kwargs in (("no signals", dict(page_text="Synthetic evidence, not law.\n")),
                              ("invalid encoding", dict(raw=b"\xff\xfe\x00bad")),
                              ("oversized", dict(raw=b"x" * 5_000_001))):
            with self.subTest(unscreenable=label):
                result = self.lint(memo("sources/" + self.NAME), **kwargs)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn("is cited as a statute copy but could not be screened", result.stdout)
        cut = self.lint(self.with_lines("A synthetic note.", operative="2010-06-01"), page_text=page("1999 a. 1; 2001 a. 16", "999.01"))
        self.assertEqual(cut.returncode, 1, cut.stdout)
        self.assertIn("the History note does not end with a period", cut.stdout)
        plain = "synthetic notes.md"
        ordinary = self.lint(memo("sources/" + plain), page_text="Synthetic evidence, not law.\n", name=plain)
        self.assertEqual(ordinary.returncode, 0, ordinary.stdout)
        quiet = self.lint(memo("sources/" + self.NAME), page_text=page("1975 c. 325; 2017 a. 207.", "999.01"))
        self.assertEqual(quiet.returncode, 0, quiet.stdout)


if __name__ == "__main__":
    unittest.main()
