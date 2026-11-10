"""The appellate brief checker: measured passes, measured departures, and refusals to call the unmeasured a pass.

Every brief here is generated filler text. Nothing in it is a real filing or a legal position.
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/wisconsin-legal-writing/scripts/check_appellate_brief.py"
SPEC = importlib.util.spec_from_file_location("check_appellate_brief_test", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def filler(count):
    return " ".join(["synthetic"] * count)


def add(doc, text, *, spacing=1.5, size=None, bold=False, indent=None, align=None):
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.bold = bold or None
    if size:
        run.font.size = Pt(size)
    if spacing is not None:
        paragraph.paragraph_format.line_spacing = spacing
    if indent:
        paragraph.paragraph_format.left_indent = Inches(indent)
    if align:
        paragraph.alignment = align
    return paragraph


def element(tag, **attributes):
    made = OxmlElement(tag)
    for name, value in attributes.items():
        made.set(qn("w:" + name), value)
    return made


def page_field(paragraph, instruction=" PAGE ", simple=False):
    if simple:
        paragraph._p.append(element("w:fldSimple", instr=instruction))
        return
    run = paragraph.add_run()
    run._r.append(element("w:fldChar", fldCharType="begin"))
    text = OxmlElement("w:instrText")
    text.text = instruction
    run._r.append(text)
    run._r.append(element("w:fldChar", fldCharType="end"))


def cite_footnote(paragraph, note_id):
    paragraph.add_run()._r.append(element("w:footnoteReference", id=str(note_id)))


def footnotes_part(notes):
    """notes: {id: (text, half_points, line)}"""
    items = "".join(
        f'<w:footnote w:id="{note_id}"><w:p><w:pPr><w:spacing w:line="{line}" w:lineRule="auto"/></w:pPr><w:r><w:rPr>'
        f'<w:sz w:val="{half_points}"/></w:rPr><w:t>{text}</w:t></w:r></w:p></w:footnote>'
        for note_id, (text, half_points, line) in notes.items())
    return (f'<w:footnotes xmlns:w="{W_NS}"><w:footnote w:type="separator" w:id="0"><w:p><w:r><w:separator/></w:r></w:p>'
            f'</w:footnote>{items}</w:footnotes>')


def brief(path, *, title="BRIEF OF APPELLANT", case=True, argument=300, after=40, footer="center", hooks=None, notes=None):
    """Write a synthetic brief. hooks: {'cover'|'issues'|'argument'|'conclusion'|'end'|'document': callable(doc)}."""
    hooks = hooks or {}
    doc = Document()
    doc.styles["Normal"].font.size = Pt(13)
    doc.styles["Normal"].font.name = "Century Schoolbook"
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.left_margin = section.right_margin = Inches(1.25)
    section.top_margin = section.bottom_margin = Inches(1)
    if footer:
        holder = section.footer.paragraphs[0]
        holder.alignment = WD_ALIGN_PARAGRAPH.CENTER if footer == "center" else WD_ALIGN_PARAGRAPH.LEFT
        page_field(holder)
    for line in ("STATE OF WISCONSIN", "COURT OF APPEALS", "DISTRICT IV", "Alex Example, Plaintiff-Appellant,", title):
        add(doc, line, spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    hooks.get("cover", lambda d: None)(doc)
    add(doc, "TABLE OF CONTENTS", bold=True)
    add(doc, "ARGUMENT\t5", spacing=1.0)
    add(doc, "STATEMENT OF THE ISSUES", bold=True)
    add(doc, "1. Whether the synthetic order should be reversed. " + filler(20))
    hooks.get("issues", lambda d: None)(doc)
    if case:
        add(doc, "STATEMENT OF THE CASE", bold=True)
        add(doc, filler(60))
    add(doc, "ARGUMENT", bold=True)
    add(doc, "I. The synthetic order should be reversed.", bold=True)
    add(doc, filler(argument))
    hooks.get("argument", lambda d: None)(doc)
    add(doc, "CONCLUSION", bold=True)
    add(doc, "For the reasons stated, the synthetic order should be reversed.")
    hooks.get("conclusion", lambda d: None)(doc)
    add(doc, "Dated: November 9, 2026", spacing=1.0)
    add(doc, "Electronically signed by Alex Example", spacing=1.0)
    add(doc, "CERTIFICATION AS TO FORM AND LENGTH: " + filler(after), spacing=1.0)
    hooks.get("end", lambda d: None)(doc)
    hooks.get("document", lambda d: None)(doc)
    doc.save(path)
    if notes:
        with zipfile.ZipFile(path, "a") as archive:
            archive.writestr("word/footnotes.xml", footnotes_part(notes))
    return path


class AppellateCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "brief.docx"

    def run_checker(self, *arguments, path=None):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            try:
                code = checker.main([str(path or self.path), *arguments])
            except SystemExit as stop:
                code = stop.code
        return code, output.getvalue()

    def check(self, expected, *arguments, contains=(), kind="appellant", **options):
        brief(self.path, **options)
        code, output = self.run_checker("--kind", kind, *arguments)
        self.assertEqual(code, expected, output)
        for text in ([contains] if isinstance(contains, str) else contains):
            self.assertIn(text, output)
        if expected == 0:
            self.assertNotIn("DEPARTS", output)
            self.assertNotIn("UNMEASURED", output)
        if expected == 3:
            self.assertNotIn("DEPARTS", output)
            self.assertIn("this is not a pass", output)
        return output

    def test_ordinary_briefs_pass_and_the_scope_is_stated(self):
        output = self.check(0, contains=("measured     page setup", "measured     pagination", "measured     length: at most",
                                         "measured     text form", "not examined blocks 1 to", "Word limit 11000",
                                         "covers only the lines marked measured",
                                         "a self-represented filer must still meet the form and length rules"))
        self.assertNotIn("the filer must certify", output)
        self.check(0, "--no-statement-of-case", kind="respondent", case=False, title="BRIEF OF RESPONDENT")
        self.check(0, kind="respondent", title="BRIEF OF RESPONDENT")
        self.check(0, kind="reply", case=False, title="REPLY BRIEF OF APPELLANT", contains="Word limit 3000")
        self.check(0, kind="nonparty", case=False, title="BRIEF OF NONPARTY", contains="s. 809.19(8)(c)3.")
        self.check(0, title="BRIEF OF PLAINTIFF-APPELLANT-CROSS-RESPONDENT")
        code, output = self.run_checker("--kind", "appellant", path=ROOT / "skills/wisconsin-legal-writing/assets/10-appellate-brief.docx")
        self.assertEqual(code, 0, output)

    def test_missing_or_repeated_section_headings_are_not_a_pass(self):
        self.check(3, kind="respondent", case=False, contains="pass --no-statement-of-case")
        self.check(3, kind="appellant", case=False, contains="no STATEMENT OF THE CASE heading was found")
        self.check(3, "--no-statement-of-case", kind="respondent", contains="a STATEMENT OF THE CASE heading is present")
        self.check(3, title="COMBINED BRIEF OF RESPONDENT AND CROSS-APPELLANT", contains="each part of a combined brief has its own limit")

        def second_part(doc):
            add(doc, "ARGUMENT", bold=True)
            add(doc, filler(12000))
            add(doc, "CONCLUSION", bold=True)
            add(doc, "The synthetic cross-appeal should be granted.")
        self.check(3, hooks={"end": second_part}, contains="found 2 ARGUMENT and 2 CONCLUSION heading(s)")
        self.check(3, hooks={"cover": lambda doc: add(doc, "ARGUMENT")}, contains="a table of contents line without a page number")

    def test_tables_pictures_and_text_boxes_in_the_counted_portions_are_not_a_pass(self):
        def big_table(doc):
            doc.add_table(rows=1, cols=1).cell(0, 0).text = filler(12000)
        output = self.check(3, hooks={"conclusion": big_table}, contains="is a table inside or after the counted portions")
        self.assertNotIn("measured     length", output)
        self.check(0, hooks={"cover": big_table}, contains="including 1 table(s)")
        for tag in ("w:drawing", "w:pict"):
            with self.subTest(tag=tag):
                self.check(3, hooks={"argument": lambda doc, tag=tag: add(doc, "See the figure.").add_run()._r.append(OxmlElement(tag))},
                           contains="words in an image count, s. 809.19(8g)(a)2.")

        def over_and_table(doc):
            add(doc, filler(12000))
            doc.add_table(rows=1, cols=1)
        brief(self.path, hooks={"argument": over_and_table})
        code, output = self.run_checker("--kind", "appellant")
        self.assertEqual(code, 1, output)
        self.assertIn("before anything unmeasured is added", output)

    def test_length_passes_departs_or_is_too_close_to_call(self):
        output = self.check(1, argument=11500, contains="DEPARTS      length: at least")
        self.assertIn("limit 11000 words, Wis. Stat. s. 809.19(8)(c)1.", output)
        self.check(3, argument=10900, contains="this tool's count can differ from a word processor's")
        self.check(3, argument=10400, after=900, contains="depends on where the conclusion ends")
        self.check(1, kind="reply", case=False, argument=3200, contains="limit 3000 words")
        self.check(0, argument=10000, after=40)

    def test_footnotes_count_where_they_are_cited_and_their_form_is_measured(self):
        def count(output):
            return int(re.search(r"length: at most (\d+) words", output).group(1))
        plain = count(self.check(0))
        cited = count(self.check(0, hooks={"argument": lambda doc: cite_footnote(add(doc, "A cited point."), 2)},
                                 notes={2: (filler(500), 22, 240)}))
        self.assertEqual(cited, plain + 3 + 500)
        elsewhere = count(self.check(0, hooks={"issues": lambda doc: cite_footnote(add(doc, "An issue note."), 2)},
                                     notes={2: (filler(500), 22, 240)}))
        self.assertEqual(elsewhere, plain)
        hook = {"argument": lambda doc: cite_footnote(add(doc, "A cited point."), 2)}
        self.check(1, hooks=hook, notes={2: (filler(20), 16, 480)}, contains="footnote 2: 8-point text, under the 11-point minimum")
        self.check(1, hooks=hook, notes={2: (filler(20), 22, 480)}, contains="footnote 2: line spacing of 2 lines, not single-spaced")
        self.check(1, hooks={"issues": lambda doc: cite_footnote(add(doc, "An issue note."), 2)}, notes={2: (filler(20), 16, 240)},
                   contains="footnote 2: 8-point text")
        self.check(3, hooks=hook, contains="footnote 2 is cited but could not be found")

    def test_text_form_in_the_counted_portions(self):
        self.check(1, hooks={"argument": lambda doc: add(doc, filler(30), spacing=1.0)},
                   contains="line spacing of 1 lines, outside 1.15 to 1.5 for body text; s. 809.19(8)(b)3.c.")
        self.check(1, hooks={"argument": lambda doc: add(doc, filler(30), size=12)}, contains="12-point text, under the 13-point minimum")
        self.check(1, hooks={"argument": lambda doc: add(doc, filler(30), spacing=2.0)}, contains="line spacing of 2 lines")
        self.check(0, hooks={"argument": lambda doc: add(doc, filler(30), spacing=1.15)})
        self.check(0, hooks={"argument": lambda doc: add(doc, filler(30), spacing=1.0, size=11, indent=0.5)},
                   contains="1 paragraph(s) passed as block quotes")
        self.check(1, hooks={"argument": lambda doc: add(doc, filler(30), spacing=2.0, size=11, indent=0.5)},
                   contains=("as body text: 11-point text, under the 13-point minimum",
                             "as block quote: line spacing of 2 lines, not single-spaced"))
        self.check(1, hooks={"argument": lambda doc: add(doc, filler(30), spacing=1.0, size=10, indent=0.5)},
                   contains="as block quote: 10-point text, under the 11-point minimum")
        self.check(0, hooks={"argument": lambda doc: add(doc, filler(30), spacing=1.5, indent=0.5)})
        fixed = self.check(3, hooks={"argument": lambda doc: add(doc, filler(30), spacing=Pt(19.5))},
                           contains="line spacing is fixed at 19.5 points")
        self.assertIn("does not judge equivalence", fixed)
        self.check(3, hooks={"argument": lambda doc: add(doc, "A. A single-spaced point heading.", spacing=1.0, bold=True)},
                   contains="does not decide whether they reach headings")
        self.check(0, hooks={"end": lambda doc: add(doc, filler(30), spacing=1.0, size=9)})

    def test_pagination_is_read_from_the_page_field_in_every_footer_word_prints(self):
        def second_centered_line(doc):
            add_line = doc.sections[0].footer.add_paragraph("Synthetic Firm")
            add_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.check(1, footer="left", hooks={"document": second_centered_line},
                   contains="the paragraph holding the PAGE field is not centered")
        self.check(1, footer=None, contains="section 1, default-page footer: there is no footer")

        def even_pages(doc, create):
            doc.settings.odd_and_even_pages_header_footer = True
            if create:
                doc.sections[0].even_page_footer.is_linked_to_previous = False
        self.check(1, hooks={"document": lambda doc: even_pages(doc, True)}, contains="section 1, even-page footer: no PAGE field")
        self.check(1, hooks={"document": lambda doc: even_pages(doc, False)}, contains="section 1, even-page footer: there is no footer")

        def first_page(doc, numbered):
            doc.sections[0].different_first_page_header_footer = True
            holder = doc.sections[0].first_page_footer.paragraphs[0]
            holder.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if numbered:
                page_field(holder)
        self.check(1, hooks={"document": lambda doc: first_page(doc, False)}, contains="section 1, first-page footer: no PAGE field")
        self.check(0, hooks={"document": lambda doc: first_page(doc, True)})

        def second_section(doc, **numbering):
            doc.add_section(WD_SECTION.NEW_PAGE)
            if numbering:
                doc.sections[1]._sectPr.append(element("w:pgNumType", **numbering))
        self.check(0, hooks={"end": second_section})
        self.check(1, hooks={"end": lambda doc: second_section(doc, fmt="lowerRoman")}, contains="section 2: page numbers use the lowerRoman format")
        self.check(1, hooks={"end": lambda doc: second_section(doc, start="1")}, contains="section 2: numbering restarts at 1")
        self.check(3, hooks={"end": lambda doc: second_section(doc, start="7")}, contains="section 2: numbering restarts at 7")
        self.check(1, hooks={"document": lambda doc: doc.sections[0]._sectPr.append(element("w:pgNumType", start="3"))},
                   contains="section 1: numbering starts at 3")

        def replace_footer(doc, build):
            holder = doc.sections[0].footer.paragraphs[0]
            for child in list(holder._p):
                if child.tag != qn("w:pPr"):
                    holder._p.remove(child)
            build(holder)
        self.check(1, hooks={"document": lambda doc: replace_footer(doc, lambda p: page_field(p, " PAGE \\* roman \\* MERGEFORMAT "))},
                   contains="the PAGE field is formatted as roman")
        self.check(0, hooks={"document": lambda doc: replace_footer(doc, lambda p: page_field(p, " PAGE   \\* MERGEFORMAT "))})
        self.check(0, hooks={"document": lambda doc: replace_footer(doc, lambda p: page_field(p, " PAGE ", simple=True))})
        self.check(1, hooks={"document": lambda doc: replace_footer(doc, lambda p: page_field(p, " NUMPAGES "))},
                   contains="default-page footer: no PAGE field")

        def tabbed(holder):
            holder.alignment = WD_ALIGN_PARAGRAPH.LEFT
            holder.add_run("\t")
            page_field(holder)
        self.check(3, hooks={"document": lambda doc: replace_footer(doc, tabbed)}, contains="placed with a tab, not a centered paragraph")

    def test_page_setup_departures(self):
        def margins(doc, **sides):
            for side, inches in sides.items():
                setattr(doc.sections[0], side, Inches(inches))
        self.check(1, hooks={"document": lambda doc: margins(doc, left_margin=1.0)},
                   contains="left margin is 1 inches; s. 809.19(8)(b)3.e. requires at least 1.25")
        self.check(1, hooks={"document": lambda doc: margins(doc, top_margin=0.5)}, contains="top margin is 0.5 inches")
        self.check(1, hooks={"document": lambda doc: margins(doc, page_width=8.27, page_height=11.69)},
                   contains="formatted to fit 8.5 by 11 inch paper")

    def test_tracked_changes_and_endnotes_are_not_a_pass(self):
        self.check(3, hooks={"argument": lambda doc: add(doc, "Inserted text.")._p.append(element("w:ins", id="1"))},
                   contains="the file has tracked changes")
        self.check(3, hooks={"argument": lambda doc: add(doc, "An endnote.").add_run()._r.append(element("w:endnoteReference", id="2"))},
                   contains="the file uses endnotes")

    def test_usage_errors_exit_2(self):
        brief(self.path)
        self.assertEqual(self.run_checker("--kind", "reply", "--no-statement-of-case")[0], 2)
        self.assertEqual(self.run_checker()[0], 2)
        self.assertEqual(self.run_checker("--kind", "amicus")[0], 2)
        pdf = self.path.with_suffix(".pdf")
        pdf.write_bytes(b"%PDF-1.4 synthetic")
        self.assertEqual(self.run_checker("--kind", "appellant", path=pdf)[0], 2)
        fake = self.path.with_name("fake.docx")
        fake.write_text("not a zip", encoding="utf-8")
        code, output = self.run_checker("--kind", "appellant", path=fake)
        self.assertEqual(code, 2, output)
        self.assertIn("not a readable DOCX", output)
        self.assertEqual(self.run_checker("--kind", "appellant", path=self.path.with_name("missing.docx"))[0], 2)

    def test_limits_come_from_the_dated_values_table(self):
        self.assertEqual(checker.wi_values.value_on("appellate_brief_words")["value"], 11000)
        saved = checker.wi_values.VALUES
        self.addCleanup(lambda: setattr(checker.wi_values, "VALUES", saved))
        checker.wi_values.VALUES = tuple({**row, "value": 400} if row["id"] == "appellate_brief_words" else row for row in saved)
        self.check(1, argument=600, contains="limit 400 words")


if __name__ == "__main__":
    unittest.main()
