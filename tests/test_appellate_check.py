"""The appellate brief checker measures synthetic DOCX files against s. 809.19(8); no real brief is used."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wisconsin-legal-writing/scripts/check_appellate_brief.py"
SPEC = importlib.util.spec_from_file_location("appellate_check_test", SCRIPT)
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
TEMPLATE = ROOT / "skills/wisconsin-legal-writing/assets/10-appellate-brief.docx"


def page_field(footer, centered=True):
    paragraph = footer.paragraphs[0]
    if centered:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), " PAGE ")
    paragraph._p.append(field)


def brief(path, *, words=600, size=13, spacing=1.5, side=1.25, top=1.0, footer=True, centered=True,
          headings=("STATEMENT OF THE CASE", "ARGUMENT", "CONCLUSION"), quote_size=11):
    document = Document()
    document.styles["Normal"].font.size = Pt(size)
    section = document.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.left_margin = section.right_margin = Inches(side)
    section.top_margin, section.bottom_margin = Inches(top), Inches(1.0)
    if footer:
        page_field(section.footer, centered)
    document.add_paragraph("BRIEF OF APPELLANT")
    document.add_paragraph("STATEMENT OF THE ISSUES")
    document.add_paragraph("Synthetic issue text that is outside the counted portions. " * 30)
    per_part = max(words // max(len(headings), 1), 45)
    for heading in headings:
        document.add_paragraph(heading)
        body = document.add_paragraph("synthetic " * per_part)
        body.paragraph_format.line_spacing = spacing
    quote = document.add_paragraph("A synthetic block quotation that is indented on both sides.")
    quote.paragraph_format.left_indent = quote.paragraph_format.right_indent = Inches(0.5)
    quote.runs[0].font.size = Pt(quote_size)
    document.add_paragraph("Dated: January 2, 2026")
    document.add_paragraph("CERTIFICATION AS TO FORM AND LENGTH: synthetic text that is never counted. " * 50)
    document.save(path)
    return path


class AppellateBriefCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "brief.docx"

    def problems(self, kind="appellant", **changes):
        return check.measure(brief(self.path, **changes), kind)[0]

    def test_conforming_brief_has_no_problems_and_counts_only_the_counted_portions(self):
        problems, facts = check.measure(brief(self.path), "appellant")
        self.assertEqual(problems, [])
        counted = next(line for line in facts if line.startswith("counted portions"))
        self.assertIn("s. 809.19(1)(d), (e) and (f)", counted)
        self.assertIn("limit 11000", counted)
        words = int(counted.split(" hold ")[1].split(" words")[0])
        self.assertLess(words, 700)
        self.assertGreater(words, 590)

    def test_each_form_departure_is_reported_with_its_subsection(self):
        cases = {
            "side margin": (dict(side=1.0), "minimum 1.25", "809.19(8)(b)3.e."),
            "top margin": (dict(top=0.5), "top and bottom margin settings are 0.5", "809.19(8)(b)3.e."),
            "body size": (dict(size=12), "12 pt in body text", "809.19(8)(b)3.c."),
            "quote size": (dict(quote_size=10), "10 pt in block quote", "809.19(8)(b)3.c."),
            "spacing": (dict(spacing=2.0), "2 lines in", "809.19(8)(b)3.c."),
            "no page number": (dict(footer=False), "has no page-number field", "809.19(8)(bm)"),
            "page number not centered": (dict(centered=False), "not centered", "809.19(8)(bm)"),
            "no headings": (dict(headings=("ARGUMENT",)), "could not be located", "809.19(8)(c)1."),
        }
        for name, (changes, text, subsection) in cases.items():
            with self.subTest(departure=name):
                joined = " | ".join(self.problems(**changes))
                self.assertIn(text, joined)
                self.assertIn(subsection, joined)

    def test_length_limits_follow_the_kind_of_brief(self):
        self.assertEqual(self.problems(words=10800), [])
        over = " | ".join(self.problems(words=11400))
        self.assertIn("limit 11000 for a appellant brief", over)
        self.assertIn("809.19(8)(c)1.", over)
        reply = " | ".join(self.problems("reply", words=4800, headings=("ARGUMENT", "CONCLUSION")))
        self.assertIn("limit 3000 for a reply brief", reply)
        self.assertIn("809.19(8)(c)2.", reply)
        self.assertEqual(self.problems("reply", words=2400, headings=("ARGUMENT", "CONCLUSION")), [])
        facts = check.measure(brief(self.path, words=900), "reply")[1]
        self.assertTrue(any("s. 809.19(1)(e) and (f)" in line for line in facts), facts)

    def test_shipped_appellate_template_passes_and_command_line_exit_codes(self):
        self.assertEqual(check.measure(TEMPLATE, "appellant")[0], [])
        run = lambda *args: subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                                           encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        good = run(str(brief(self.path)), "--kind", "appellant")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("0 item(s) depart", good.stdout)
        self.assertIn("certification under s. 809.19(8g)(a) is the filer's own statement", good.stdout)
        bad = run(str(brief(self.path, top=0.5)), "--kind", "appellant")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("CHECK section 1: top and bottom margin settings", bad.stdout)
        self.assertEqual(run(str(self.path.with_suffix(".txt")), "--kind", "appellant").returncode, 2)


if __name__ == "__main__":
    unittest.main()
