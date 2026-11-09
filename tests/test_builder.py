"""Exercise filing-builder behavior using invented parties and temporary outputs.

These checks inspect DOCX content/structure, not rendered layout or legal validity.
"""

import importlib.util
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from docx import Document


SCRIPT = (Path(__file__).resolve().parents[1] / "skills" /
          "wisconsin-legal-writing" / "scripts" / "build_filing.py")
MODULE_SPEC = importlib.util.spec_from_file_location("filing_builder_test", SCRIPT)
builder = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(builder)


def filing():
    return {
        "county": "Synthetic",
        "case_no": "TEST-1",
        "title": "Synthetic motion for testing",
        "first_party": {"name": "Alex Example", "designation": "Plaintiff"},
        "second_party": {"name": "Taylor Example", "designation": "Defendant"},
        "body": [{"type": "p", "text": "This is a synthetic request, not legal advice."}],
        "signature": {
            "name": "Alex Example", "role": "Plaintiff, pro se",
            "address": "1 Synthetic Way", "phone": "555-0100",
            "email": "alex@example.invalid", "date": "January 2, 2026",
        },
    }


class FilingBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "review.docx"

    def cli(self, spec, *options):
        source = self.root / "spec.json"
        source.write_text(json.dumps(spec), encoding="utf-8-sig")
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "-o", str(self.output), *options],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def text(self):
        return "\n".join(p.text for p in Document(self.output).paragraphs)

    def test_complete_spec_builds_without_draft_and_preserves_supplied_text(self):
        spec = filing()
        self.assertEqual(builder.build(spec, self.output), self.output)
        text = self.text()
        self.assertIn(spec["body"][0]["text"], text)
        self.assertIn("ALEX EXAMPLE,", text)
        self.assertIn("Case No. TEST-1", text)
        self.assertIn("Electronically signed by Alex Example", text)
        self.assertIn("alex@example.invalid", text)
        section = Document(self.output).sections[0]
        self.assertAlmostEqual(section.page_width.inches, 8.5)
        self.assertAlmostEqual(section.page_height.inches, 11)

    def test_cli_accepts_utf8_bom_and_discloses_remaining_review(self):
        result = self.cli(filing())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.output.is_file())
        self.assertIn("review", result.stderr.lower())
        self.assertIn("layout", result.stderr.lower())

    def test_existing_output_is_preserved_until_overwrite_is_explicit(self):
        original = b"Existing user document must survive."
        self.output.write_bytes(original)
        with self.assertRaises(FileExistsError):
            builder.build(filing(), self.output)
        self.assertEqual(self.output.read_bytes(), original)
        builder.build(filing(), self.output, overwrite=True)
        self.assertIn("synthetic request", self.text())

    def test_invalid_input_preserves_existing_output_even_with_overwrite(self):
        original = b"Existing output."
        self.output.write_bytes(original)
        for changes in (
            {"body": []}, {"body": [{"type": "unknown", "text": "Test"}]},
            {"signature": None}, {"appellate": True}, {"line_spacing": float("nan")},
            {"line_spacing": True}, {"font": "Imaginary Font"},
        ):
            with self.subTest(changes=changes):
                spec = filing()
                spec.update(changes)
                with self.assertRaises(ValueError):
                    builder.build(spec, self.output, overwrite=True)
                self.assertEqual(self.output.read_bytes(), original)

    def test_placeholders_need_draft_and_remain_visible_in_draft(self):
        spec = filing()
        spec["body"][0]["text"] = "On [DATE], see (Doc. __:__)."
        spec["signature"].pop("phone")
        with self.assertRaises(ValueError):
            builder.build(spec, self.output)
        self.assertFalse(self.output.exists())
        builder.build(spec, self.output, draft=True)
        self.assertIn("On [DATE], see (Doc. __:__).", self.text())

    def test_each_placeholder_form_requires_draft_and_remains_visible(self):
        for token in (
            "[DATE]", "__", "____", "<DATE>", "<date to supply>",
            "{...}", "{date to supply}", "TBD", "TBA", "TK", "tbd", "tba", "tk",
            "XX", "XXXX", "xx", "xXx",
        ):
            with self.subTest(token=token):
                spec = filing()
                spec["body"][0]["text"] = f"Synthetic input: {token}."
                with self.assertRaises(ValueError) as caught:
                    builder.build(spec, self.output, overwrite=True)
                self.assertIn(f"body[0].text: {json.dumps(token)}", str(caught.exception))
                builder.build(spec, self.output, draft=True, overwrite=True)
                self.assertIn(spec["body"][0]["text"], self.text())

    def test_placeholder_error_lists_every_token_and_unambiguous_spec_path(self):
        spec = filing()
        spec["title"] = "<TITLE>"
        spec["body"][0]["text"] = "TBD, TBA; TK. XXXX [DATE] __ {time} TBD"
        spec["signature"]["date"] = "<DATE>"
        spec["metadata"] = {"nested": ["TBA", {"key.with[punctuation]": "{...}"}]}
        original = b"Existing document must survive placeholder refusal."
        self.output.write_bytes(original)
        result = self.cli(spec, "--overwrite")
        self.assertEqual(result.returncode, 2, result.stderr)
        expected = ['title: "<TITLE>"']
        expected.extend(f"body[0].text: {json.dumps(token)}" for token in (
            "TBD", "TBA", "TK", "XXXX", "[DATE]", "__", "{time}", "TBD",
        ))
        expected.extend([
            'signature.date: "<DATE>"', 'metadata.nested[0]: "TBA"',
            'metadata.nested[1]["key.with[punctuation]"]: "{...}"',
        ])
        self.assertEqual(result.stderr.splitlines()[1:], expected)
        self.assertIn("--draft", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.output.read_bytes(), original)

    def test_ordinary_words_and_four_digit_number_masks_build_without_draft(self):
        for text in (
            "Ordinary text, next, Exhibit, textbook, Next and exhibit remain intact.",
            "Literal tokens X, x, TK421, XTBD, TBAx and unfilled are outside the screen.",
            "Synthetic number XXXX1234.",
            "Synthetic number XXX-XX-1234.",
            "Synthetic number XXXX XXXX XXXX 1234.",
            "Synthetic number xxxx-xxxx-1234.",
            "Synthetic number XX.XX.1234.",
            "Synthetic number XX\tXX\t1234.",
            "Synthetic number XXX\u00a0XX\u00a01234.",
            "Synthetic number XXX\u2011XX\u20111234.",
            "Synthetic number XXX\u2012XX\u20121234.",
            "Synthetic number XXX\u2013XX\u20131234.",
            "Synthetic number XXX\u2212XX\u22121234.",
            "Literal empty pairs <> and {} remain outside the screen.",
            "Literal multiline pairs <first\nsecond> and {first\nsecond} remain outside the screen.",
        ):
            with self.subTest(text=text):
                spec = filing()
                spec["body"][0]["text"] = text
                builder.build(spec, self.output, overwrite=True)
                self.assertIn(text, self.text())

    def test_number_mask_exception_does_not_hide_other_placeholders(self):
        spec = filing()
        spec["body"][0]["text"] = "XXXX 1234; TBD; XXXX 123; XXXX 12345; <XXXX 1234>; Chapter XX."
        with self.assertRaises(ValueError) as caught:
            builder.build(spec, self.output)
        self.assertEqual(str(caught.exception).splitlines()[1:], [
            'body[0].text: "TBD"', 'body[0].text: "XXXX"',
            'body[0].text: "XXXX"', 'body[0].text: "<XXXX 1234>"', 'body[0].text: "XX"',
        ])
        self.assertFalse(self.output.exists())

    def test_brackets_in_synthetic_statutory_quote_still_require_draft(self):
        spec = filing()
        spec["body"] = [{
            "type": "quote",
            "text": 'Fictional statute: "The [requesting] party may obtain a copy."',
        }]
        with self.assertRaisesRegex(ValueError, "intentional legal brackets"):
            builder.build(spec, self.output)
        self.assertFalse(self.output.exists())
        builder.build(spec, self.output, draft=True)
        self.assertIn(spec["body"][0]["text"], self.text())

    def test_protected_information_patterns_refuse_final_build_without_echoing_the_number(self):
        cases = {
            "Her social security number is 123-45-6789.": "social security number",
            "SSN 123456789 appears on the form.": "social security number",
            "The employer's EIN is 12-3456789.": "employer or taxpayer identification number",
            "Taxpayer identification 987654321 was used.": "employer or taxpayer identification number",
            "Funds left account number 0001234567890 that day.": "financial account number",
            "Routing 123456789 was printed on the check.": "financial account number",
            "He paid with 4111 1111 1111 1111 at the counter.": "financial account number",
            "Her driver license number is E123-4567-8901-23.": "driver license number",
            "Passport number C12345678 was presented.": "passport number",
        }
        for text, category in cases.items():
            with self.subTest(category=category, text=text):
                spec = filing()
                spec["body"][0]["text"] = text
                with self.assertRaises(ValueError) as caught:
                    builder.build(spec, self.output)
                message = str(caught.exception)
                self.assertIn("801.19(2)(c)", message)
                self.assertIn(f"body[0].text: {category} pattern", message)
                for digits in re.findall(r"\d{4,}", text):
                    self.assertNotIn(digits, message)
                self.assertFalse(self.output.exists())

    def test_protected_information_screen_passes_masks_dates_phones_and_case_numbers(self):
        for text in (
            "The account ending in 1234 and SSN XXX-XX-6789 are masked.",
            "The account was opened on 2025-01-15 and closed 2025-03-01.",
            "Call the account manager at 608-555-0100 or (608) 555-0100.",
            "Case No. 2025-CV-000123 and 2025CV000123; zip 54000-1234; Doc. 12 at 3.",
            "Her driver license was suspended on 2025-01-15 for 90 days.",
            "The passport application was filed in 2024 at 123 Main Street.",
            "Invoice 1234 5678 9012 3456 is not a card number under the checksum test.",
            "Wis. Stat. s. 801.19(1)(a) lists five kinds of numbers; damages were $12,500,000.",
        ):
            with self.subTest(text=text):
                spec = filing()
                spec["body"][0]["text"] = text
                builder.build(spec, self.output, overwrite=True)
                self.assertIn(text, self.text())

    def test_protected_information_draft_warns_and_reviewed_flag_builds(self):
        spec = filing()
        spec["signature"]["address"] = "1 Synthetic Way; SSN 123-45-6789"
        refused = self.cli(spec)
        self.assertEqual(refused.returncode, 2, refused.stderr)
        self.assertIn("signature.address: social security number pattern (11 characters, not shown)", refused.stderr)
        self.assertNotIn("6789", refused.stderr)
        self.assertFalse(self.output.exists())
        draft = self.cli(spec, "--draft")
        self.assertEqual(draft.returncode, 0, draft.stderr)
        self.assertIn("warning: possible protected information", draft.stderr)
        self.assertNotIn("6789", draft.stderr)
        reviewed = self.cli(spec, "--protected-info-reviewed", "--overwrite")
        self.assertEqual(reviewed.returncode, 0, reviewed.stderr)
        self.assertNotIn("protected information", reviewed.stderr)

    def declaration(self):
        spec = filing()
        spec["title"] = "Declaration of Alex Example in Support of Synthetic Motion"
        spec["body"] = [
            {"type": "num", "text": "1. I am the plaintiff and make this declaration on personal knowledge."},
            {"type": "p", "text": "I declare under penalty of false swearing under the law of Wisconsin "
                                    "that the foregoing is true and correct."},
            {"type": "p", "text": "Signed on the 2nd day of January, 2026, at Anytown, Wisconsin."},
        ]
        return spec

    def test_declaration_in_statutory_form_builds_and_other_documents_are_not_checked(self):
        builder.build(self.declaration(), self.output)
        self.assertIn("under penalty of false swearing under the law of Wisconsin", self.text())
        motion = filing()
        motion["title"] = "Plaintiff's Motion for Declaratory Relief"
        builder.build(motion, self.output, overwrite=True)
        affidavit = self.declaration()
        affidavit["document_type"] = "motion"
        affidavit["body"] = affidavit["body"][:1]
        builder.build(affidavit, self.output, overwrite=True)

    def test_declaration_missing_statutory_elements_is_refused_and_draft_warns(self):
        cases = {
            "phrase": (lambda body: body.pop(1), "false swearing under the law of Wisconsin"),
            "execution": (lambda body: body.pop(2), "lacks an execution line"),
            "year": (lambda body: body.__setitem__(2, {"type": "p", "text": "Signed on January 2 at Anytown, Wisconsin."}),
                     "states no year"),
        }
        for name, (change, expected) in cases.items():
            with self.subTest(missing=name):
                spec = self.declaration()
                change(spec["body"])
                with self.assertRaises(ValueError) as caught:
                    builder.build(spec, self.output)
                self.assertIn("887.015(6)", str(caught.exception))
                self.assertIn(expected, str(caught.exception))
                self.assertFalse(self.output.exists())
                result = self.cli(spec, "--draft", "--overwrite")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("warning: declaration form", result.stderr)
                self.output.unlink()
        typed = self.declaration()
        typed["title"] = "Statement of Alex Example"
        typed["document_type"] = "declaration"
        typed["body"].pop(1)
        with self.assertRaisesRegex(ValueError, "887.015"):
            builder.build(typed, self.output)

    def test_declaration_notes_excluded_uses_and_place_without_state(self):
        spec = self.declaration()
        spec["title"] = "Declaration of Alex Example for Recording with the Register of Deeds"
        spec["body"][2]["text"] = "Signed on January 2, 2026, at Anytown."
        result = self.cli(spec)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("note: declaration: the text mentions a declaration to be recorded", result.stderr)
        self.assertIn("887.015(4)(b)4.", result.stderr)
        self.assertIn("place has no comma", result.stderr)

    def test_complaint_and_summons_titles_are_refused_in_every_mode(self):
        for title in ("Complaint", "Summons and Complaint", "Amended Complaint for Damages",
                      "VERIFIED COMPLAINT", "Third-Party Complaint", "Summons"):
            for draft in (False, True):
                with self.subTest(title=title, draft=draft):
                    spec = filing()
                    spec["title"] = title
                    with self.assertRaises(ValueError) as caught:
                        builder.build(spec, self.output, draft=draft)
                    self.assertIn("802.04(1)", str(caught.exception))
                    self.assertIn("case classification type and code", str(caught.exception))
                    self.assertFalse(self.output.exists())
        typed = filing()
        typed["document_type"] = "complaint"
        with self.assertRaisesRegex(ValueError, "801.09"):
            builder.build(typed, self.output)
        for title in ("Defendant's Answer to Complaint", "Plaintiff's Motion to Amend Complaint",
                      "Defendant's Brief in Support of Motion to Dismiss the Complaint"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                builder.build(spec, self.output, overwrite=True)

    def test_motion_title_must_name_the_party_and_describe_the_relief(self):
        bad = {
            "Motion to Compel Discovery": "the name of the party seeking",
            "Notice of Motion and Motion for Summary Judgment": "the name of the party seeking",
            "Renewed Motion to Dismiss": "the name of the party seeking",
            "Plaintiff's Motion": "a brief description",
            "Motion": "the name of the party seeking the order or relief and a brief description",
        }
        for title, expected in bad.items():
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                with self.assertRaises(ValueError) as caught:
                    builder.build(spec, self.output)
                self.assertIn("802.01(2)(d)", str(caught.exception))
                self.assertIn(expected, str(caught.exception))
                result = self.cli(spec, "--draft", "--overwrite")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("warning: motion title", result.stderr)
                self.output.unlink()
        for title in ("Plaintiff's Motion to Compel Discovery", "Defendants' Motion for Summary Judgment",
                      "Motion of Plaintiff to Enlarge Time", "Motion by Taylor Example to Dismiss",
                      "Joint Motion to Amend the Scheduling Order", "Stipulated Motion for a Protective Order",
                      "Plaintiff's Notice of Motion and Motion to Compel",
                      "Plaintiff's Brief in Support of Motion to Compel", "Order Granting Motion to Compel"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                builder.build(spec, self.output, overwrite=True)

    def test_generated_non_draft_does_not_invent_blank_attorney_date(self):
        spec = filing()
        spec["signature"] = {
            "style": "attorney", "firm": "Synthetic Firm", "name": "Alex Example",
            "bar_no": "0000000", "for_party": "Attorney for synthetic plaintiff",
            "address": "1 Synthetic Way", "phone": "555-0100", "email": "test@example.invalid",
        }
        try:
            builder.build(spec, self.output)
        except ValueError as exc:
            # Requiring the missing date is also a truthful, supported outcome.
            self.assertIn("date", str(exc).lower())
        else:
            self.assertNotIn("____", self.text())

    def test_malformed_scalar_fields_are_cli_errors_without_tracebacks(self):
        for changes in (
            {"county": 7}, {"title": 7}, {"case_no": 7},
            {"first_party": {"name": 7, "designation": "Plaintiff"}},
        ):
            with self.subTest(changes=changes):
                spec = filing()
                spec.update(changes)
                result = self.cli(spec, "--draft")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn("Traceback", result.stderr)
                self.assertFalse(self.output.exists())

    def test_proposed_order_allows_no_signature_and_does_not_add_one(self):
        spec = filing()
        spec["proposed_order"] = True
        spec["signature"] = None
        spec["body"] = [{"type": "ordered", "text": "Synthetic ordered paragraph."}]
        builder.build(spec, self.output)
        self.assertIn("Synthetic ordered paragraph.", self.text())
        self.assertNotIn("Electronically signed", self.text())

    def test_saved_xml_keeps_top_margin_on_every_page_and_spacer_on_page_one(self):
        # 1368 twips = 0.95 in on every page. Page 1 clearance comes from a
        # first-page header that starts 720 twips (0.5 in) from the top edge and
        # holds one empty paragraph of exact height: 2160 twips (1.5 in) for a
        # 2 in band, 3600 twips (2.5 in) for a proposed order's 3 in band. An
        # exact line rule, not a stack of line breaks, so the height does not
        # depend on the renderer's line metrics. Pages 2 and later have no
        # header, so their body text starts at the 0.95 in margin.
        cases = (({}, 2160), ({"proposed_order": True, "signature": None}, 3600),
                 ({"stamp_clearance": True}, 2160))
        for changes, twips in cases:
            with self.subTest(changes=changes):
                spec = {**filing(), **changes, "case_no": "2025CV000123"}
                builder.build(spec, self.output, overwrite=True)
                with zipfile.ZipFile(self.output) as archive:
                    document = archive.read("word/document.xml").decode("utf-8")
                    headers = [n for n in archive.namelist() if n.startswith("word/header")]
                    header = archive.read(headers[0]).decode("utf-8") if headers else ""
                self.assertRegex(document, r'<w:pgMar [^>]*w:top="1368"')
                self.assertRegex(document, r'<w:pgMar [^>]*w:header="720"')
                self.assertNotIn('w:type="default"', document)
                self.assertIn("<w:titlePg/>", document)
                self.assertIn('<w:headerReference w:type="first"', document)
                self.assertEqual(len(headers), 1)
                spacing = re.search(r"<w:spacing [^>]*/>", header)
                self.assertIsNotNone(spacing, header)
                self.assertIn(f'w:line="{twips}"', spacing.group(0))
                self.assertIn('w:lineRule="exact"', spacing.group(0))
                self.assertNotIn("<w:br/>", header)
                self.assertEqual(header.count("<w:p>") + header.count("<w:p "), 1)

    def test_stamp_clearance_cannot_be_switched_off(self):
        # A filed declaration built with the switch off had the clerk's FILED stamp
        # (0.27 to 1.19 in from the top, 6.7 to 8.0 in from the left) printed over
        # the county name of a caption that started at the 0.95 in margin.
        spec = {**filing(), "stamp_clearance": False, "case_no": "2025CV000123"}
        with self.assertRaisesRegex(ValueError, "stamp_clearance: false is not supported"):
            builder.build(spec, self.output, overwrite=True)
        self.assertFalse(self.output.exists())

    def test_legal_omissions_and_literal_asterisks_survive_emphasis(self):
        spec = filing()
        spec["body"][0]["text"] = r"*Synthetic Case*; **emphasis**; 5 * 3; * * *; \*literal\*; __."
        builder.build(spec, self.output, draft=True)
        body = next(p for p in Document(self.output).paragraphs if "Synthetic Case" in p.text)
        self.assertEqual(body.text, "Synthetic Case; emphasis; 5 * 3; * * *; *literal*; __.")
        self.assertTrue(any(run.italic and run.text == "Synthetic Case" for run in body.runs))
        self.assertTrue(any(run.bold and run.text == "emphasis" for run in body.runs))

    def test_non_docx_output_is_refused(self):
        with self.assertRaisesRegex(ValueError, "docx"):
            builder.build(filing(), self.root / "review.pdf")
        self.assertFalse((self.root / "review.pdf").exists())

    def test_output_symlink_never_overwrites_its_target(self):
        target = self.root / "existing.docx"
        target.write_bytes(b"Original linked document")
        try:
            self.output.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            builder.build(filing(), self.output, overwrite=True, draft=True)
        self.assertEqual(target.read_bytes(), b"Original linked document")

    def test_output_name_outside_console_code_page_does_not_turn_success_into_failure(self):
        # A Windows process with piped output uses cp1252; U+0141 is not in it.
        self.output = self.root / "Brief-Łukasz.docx"
        source = self.root / "spec.json"
        source.write_text(json.dumps(filing()), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(source), "-o", str(self.output)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        self.assertEqual((result.returncode, self.output.exists()), (0, True), result.stderr)

    def test_make_templates_survives_output_directory_outside_console_code_page(self):
        script = SCRIPT.with_name("make_templates.py")
        target = self.root / "out-Łukasz"
        result = subprocess.run(
            [sys.executable, str(script), "--out-dir", str(target)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(list(target.glob("*.docx")))

    def test_readme_build_command_runs_as_written(self):
        repo = SCRIPT.parents[3]
        # The README shows the command as run from an installed copy under .claude/skills/;
        # the same files sit under skills/ in this repository.
        prefix = "python .claude/skills/wisconsin-legal-writing/scripts/build_filing.py"
        commands = [line.strip().replace(".claude/skills/", "skills/")
                    for line in (repo / "README.md").read_text(encoding="utf-8").splitlines()
                    if line.strip().startswith(prefix)]
        self.assertTrue(commands, "README no longer shows a build_filing.py command")
        for command in commands:
            with self.subTest(command=command):
                argv = [str(self.root / "motion-draft.docx") if a == "motion-draft.docx" else a
                        for a in command.split()[1:]]
                result = subprocess.run([sys.executable, *argv], cwd=repo, capture_output=True, text=True,
                                        encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((self.root / "motion-draft.docx").exists())
                (self.root / "motion-draft.docx").unlink()


if __name__ == "__main__":
    unittest.main()
