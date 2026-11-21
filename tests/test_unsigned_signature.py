"""An explicitly unsigned Word file: blank signature line, typed identification kept, no statement of signing.

These checks read the saved DOCX. They do not render it and do not decide how a document must be signed.
Invented facts only.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from docx import Document

from test_builder import SCRIPT, builder, filing
from test_declaration import declaration


RULE = "_" * 30
EXPECTED_NOTICE = "note: signature.unsigned is true. The generated signature line is blank."


def attorney():
    spec = filing()
    spec["signature"] = {
        "style": "attorney", "date": "January 2, 2026", "firm": "Synthetic Firm", "name": "Alex Example",
        "bar_no": "0000000", "for_party": "Attorney for synthetic plaintiff",
        "address": "1 Synthetic Way", "city_state_zip": "Anytown, Wisconsin 54000",
        "phone": "555-0100", "email": "test@example.invalid",
    }
    return spec


class UnsignedSignatureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "review.docx"

    def build(self, spec, **options):
        notes = io.StringIO()
        with contextlib.redirect_stderr(notes):
            builder.build(spec, self.output, overwrite=True, **options)
        return Document(self.output).paragraphs, notes.getvalue()

    def assert_says_nobody_signed(self, paragraphs, notes):
        with zipfile.ZipFile(self.output) as archive:
            saved = "".join(archive.read(name).decode("utf-8") for name in archive.namelist() if name.endswith(".xml"))
        self.assertNotIn("lectronically", saved)
        self.assertNotIn("signed by", saved.lower())
        self.assertEqual(sum(RULE in paragraph.text for paragraph in paragraphs), 1)
        self.assertIn(EXPECTED_NOTICE, notes.splitlines())

    def test_self_represented_block_keeps_the_typed_lines_under_a_blank_rule(self):
        for draft in (True, False):
            with self.subTest(draft=draft):
                spec = filing()
                spec["signature"]["unsigned"] = True
                paragraphs, notes = self.build(spec, draft=draft)
                self.assertEqual([paragraph.text for paragraph in paragraphs[-6:]], [
                    "Dated: January 2, 2026\t" + RULE, "Alex Example", "Plaintiff, pro se",
                    "1 Synthetic Way", "555-0100", "alex@example.invalid"])
                self.assertFalse(any(run.italic for run in paragraphs[-6].runs))
                self.assert_says_nobody_signed(paragraphs, notes)

    def test_attorney_block_keeps_the_typed_lines_under_a_blank_rule(self):
        for draft in (True, False):
            with self.subTest(draft=draft):
                spec = attorney()
                spec["signature"]["unsigned"] = True
                paragraphs, notes = self.build(spec, draft=draft)
                self.assertEqual([paragraph.text for paragraph in paragraphs[-14:]], [
                    "January 2, 2026", "Respectfully submitted,", "", "SYNTHETIC FIRM", "", RULE, "Alex Example",
                    "State Bar No. 0000000", "Attorney for synthetic plaintiff", "", "1 Synthetic Way",
                    "Anytown, Wisconsin 54000", "555-0100", "test@example.invalid"])
                self.assertFalse(any(run.italic for run in paragraphs[-9].runs))
                self.assert_says_nobody_signed(paragraphs, notes)

    def test_without_the_statement_the_electronic_line_is_unchanged(self):
        for make in (filing, attorney):
            for change in ({}, {"unsigned": False}):
                with self.subTest(style=make.__name__, change=change):
                    spec = make()
                    spec["signature"].update(change)
                    paragraphs, notes = self.build(spec)
                    signed = [paragraph for paragraph in paragraphs if "Electronically signed by Alex Example" in paragraph.text]
                    self.assertEqual(len(signed), 1)
                    self.assertTrue(signed[0].runs[-1].italic)
                    self.assertFalse(any(RULE in paragraph.text for paragraph in paragraphs))
                    self.assertNotIn("unsigned", notes)

    def test_only_true_or_false_is_a_statement(self):
        for value in (None, "true", "yes", 1, 0, [], {}):
            for draft in (True, False):
                with self.subTest(value=value, draft=draft):
                    spec = filing()
                    spec["signature"]["unsigned"] = value
                    with self.assertRaisesRegex(ValueError, "signature.unsigned must be true or false"):
                        builder.build(spec, self.output, draft=draft)
                    self.assertFalse(self.output.exists())

    def test_unsigned_declaration_cannot_state_a_day_of_signing(self):
        dated = declaration()
        dated["signature"]["unsigned"] = True
        for draft in (True, False):
            with self.subTest(draft=draft):
                with self.assertRaisesRegex(ValueError, "contradictory spec: signature.unsigned is true"):
                    builder.build(dated, self.output, draft=draft)
                self.assertFalse(self.output.exists())
        for raw, refusal in ((None, "declaration is incomplete"), ("[SIGNING DATE]", "placeholder markers")):
            with self.subTest(signed_on=raw):
                blank = declaration(signed_on=raw)
                blank["signature"]["unsigned"] = True
                with self.assertRaisesRegex(ValueError, refusal):
                    builder.build(blank, self.output)
                paragraphs, notes = self.build(blank, draft=True)
                text = "\n".join(paragraph.text for paragraph in paragraphs)
                self.assertIn("Signed on the ____ day of __________, [YEAR], at Anytown, Wisconsin.", text)
                self.assertEqual(text.count("Signed on"), 1)
                self.assert_says_nobody_signed(paragraphs, notes)

    def test_blank_signature_line_preserves_supplied_body_text(self):
        spec = filing()
        statement = "I signed this document."
        spec["body"] = [{"type": "p", "text": statement}]
        spec["signature"]["unsigned"] = True
        paragraphs, notes = self.build(spec, draft=True)
        self.assertIn(statement, [p.text for p in paragraphs])
        self.assertTrue(any(RULE in p.text for p in paragraphs))
        self.assertIn(EXPECTED_NOTICE, notes.splitlines())

    def test_command_line_reports_the_blank_line_and_a_proposed_order_ignores_the_key(self):
        source = Path(self.temporary.name) / "spec.json"

        def run(spec, *options):
            source.write_text(json.dumps(spec), encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPT), str(source), "-o", str(self.output), "--overwrite", *options],
                capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})

        spec = filing()
        spec["signature"]["unsigned"] = True
        result = run(spec, "--draft")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(EXPECTED_NOTICE, result.stderr.splitlines())
        self.assertIn(RULE, "\n".join(paragraph.text for paragraph in Document(self.output).paragraphs))

        spec["signature"]["unsigned"] = "true"
        refused = run(spec, "--draft")
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn("signature.unsigned must be true or false", refused.stderr)
        self.assertNotIn("Traceback", refused.stderr)

        order = filing()
        order["proposed_order"] = True
        order["signature"]["unsigned"] = True
        order["body"] = [{"type": "ordered", "text": "Synthetic ordered paragraph."}]
        result = run(order)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(EXPECTED_NOTICE, result.stderr)
        self.assertNotIn(RULE, "\n".join(paragraph.text for paragraph in Document(self.output).paragraphs))


if __name__ == "__main__":
    unittest.main()
