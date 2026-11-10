"""Unsworn declarations in the filing builder: structured closing, refusals and contradictions. Invented facts only."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from docx import Document

from test_builder import SCRIPT, builder, filing

ASSETS = SCRIPT.parents[1] / "assets"
SENTENCE = "I declare under penalty of false swearing under the law of Wisconsin that the foregoing is true and correct."


def declaration(**fields):
    spec = filing()
    spec["title"] = "Declaration of Alex Example in Support of Plaintiff's Motion to Compel"
    spec["document_type"] = "declaration"
    spec["body"] = [
        {"type": "p", "text": "I, Alex Example, state the following under Wis. Stat. § 887.015:"},
        {"type": "num", "text": "1. I am the plaintiff in this synthetic action and make this declaration on personal knowledge."},
    ]
    spec["declaration"] = {"use": "sworn_declaration_substitute", "signed_on": "2026-11-09", "location": "Anytown",
                           "state_or_country": "Wisconsin", **fields}
    return spec


class DeclarationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "review.docx"

    def build(self, spec, **options):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            builder.build(spec, self.output, overwrite=True, **options)
        return [p.text for p in Document(self.output).paragraphs if p.text.strip()], errors.getvalue()

    def refused(self, spec, expected, **options):
        self.output.unlink(missing_ok=True)
        with self.assertRaises(ValueError) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                builder.build(spec, self.output, **options)
        self.assertIn(expected, str(caught.exception))
        self.assertFalse(self.output.exists())
        return str(caught.exception)

    def test_builder_prints_the_statutory_closing_once_after_the_facts_and_before_the_signature(self):
        lines, _ = self.build(declaration())
        self.assertEqual(lines.count(SENTENCE), 1)
        execution = "Signed on the 9th day of November, 2026, at Anytown, Wisconsin."
        self.assertEqual(lines.count(execution), 1)
        facts = next(i for i, line in enumerate(lines) if line.startswith("1. I am the plaintiff"))
        signature = next(i for i, line in enumerate(lines) if line.endswith("Alex Example") and i > facts)
        self.assertLess(facts, lines.index(SENTENCE))
        self.assertEqual(lines.index(execution), lines.index(SENTENCE) + 1)
        self.assertLess(lines.index(execution), signature)
        abroad, _ = self.build(declaration(signed_on="2027-03-01", location="Paris", state_or_country="France"))
        self.assertIn("Signed on the 1st day of March, 2027, at Paris, France.", abroad)
        self.assertEqual([builder._ordinal(day) for day in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 30, 31)],
                         ["1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "30th", "31st"])

    def test_final_build_needs_a_full_date_a_location_and_a_state_or_country(self):
        incomplete = [
            ({"signed_on": "2026"}, "declaration.signed_on must be the full date"),
            ({"signed_on": "2026-11-9"}, "declaration.signed_on must be the full date"),
            ({"signed_on": "November 9, 2026"}, "declaration.signed_on must be the full date"),
            ({"signed_on": "2026-02-30"}, "declaration.signed_on must be the full date"),
            ({"signed_on": None}, "declaration.signed_on must be the full date"),
            ({"state_or_country": None}, "declaration.state_or_country must be the state or country"),
            ({"state_or_country": "  "}, "declaration.state_or_country must be the state or country"),
            ({"location": ""}, "declaration.location must be the city or other location"),
            ({"use": None}, 'declaration.use must be "sworn_declaration_substitute"'),
            ({"use": "court_filing"}, 'declaration.use must be "sworn_declaration_substitute"'),
        ]
        for fields, expected in incomplete:
            with self.subTest(fields=fields):
                message = self.refused(declaration(**fields), expected)
                self.assertIn("declaration is incomplete", message)
                lines, warning = self.build(declaration(**fields), draft=True)
                self.assertIn("warning: draft declaration is incomplete", warning)
                self.assertIn(expected, warning)
                self.assertEqual(lines.count(SENTENCE), 1)
        blank, _ = self.build(declaration(signed_on=None, location=None, state_or_country=None), draft=True)
        self.assertIn("Signed on the ____ day of __________, [YEAR], at [CITY OR OTHER LOCATION], [STATE OR COUNTRY].", blank)

    def test_excluded_uses_are_refused_in_every_mode_and_a_mention_is_not_a_use(self):
        named = {"deposition": "(4)(b)1.", "oath_of_office": "(4)(b)2.", "oath_before_specified_official": "(4)(b)3.",
                 "recorded_under_706_or_140": "(4)(b)4.", "oath_under_853_04": "(4)(b)5."}
        self.assertEqual(set(named), set(builder.DECLARATION_EXCLUDED_USES))
        for use, pinpoint in named.items():
            for draft in (False, True):
                with self.subTest(use=use, draft=draft):
                    message = self.refused(declaration(use=use), "Wis. Stat. s. 887.015 does not apply to", draft=draft)
                    self.assertIn(pinpoint, message)
        spec = declaration()
        spec["body"].append({"type": "num", "text": "2. At my deposition on March 3, 2026, I produced the synthetic lease, "
                                                    "which was later recorded with the register of deeds."})
        lines, _ = self.build(spec)
        self.assertEqual(lines.count(SENTENCE), 1)

    def test_other_closing_wording_is_refused_as_unsupported_not_declared_invalid(self):
        own = ("I declare under penalty of false swearing under the laws of Wisconsin that the foregoing is true and correct.",
               "Pursuant to Wis. Stat. § 887.015, I declare the following to be true under penalty of false swearing under "
               "the law of Wisconsin.",
               SENTENCE,
               "I certify under penalty of perjury that the foregoing is true.",
               "Signed on November 9, 2026, at Anytown, Wisconsin.",
               "Executed on the 9th day of November, 2026.",
               "Dated this 9th day of November, 2026.")
        for text in own:
            for draft in (False, True):
                with self.subTest(text=text, draft=draft):
                    spec = declaration()
                    spec["body"].append({"type": "p", "text": text})
                    message = self.refused(spec, "body[2] carries its own declaration or execution wording", draft=draft)
                    self.assertIn("does not judge whether other wording conforms", message)
                    self.assertNotIn("invalid", message)
        spec = declaration()
        spec["body"] += [
            {"type": "num", "text": "2. I signed the synthetic lease on March 3, 2026."},
            {"type": "num", "text": "3. The federal form I received says it is signed under penalty of perjury."},
            {"type": "num", "text": "4. The notice is dated this year and was executed on paper."},
        ]
        lines, _ = self.build(spec)
        self.assertEqual(lines.count(SENTENCE), 1)

    def test_contradictory_specs_are_refused_before_any_signature_shortcut(self):
        for draft in (False, True):
            with self.subTest(draft=draft):
                typed = declaration()
                typed["document_type"] = "motion"
                self.refused(typed, "the title opens as a declaration but document_type is 'motion'", draft=draft)
                order = declaration()
                order["proposed_order"], order["signature"] = True, None
                self.refused(order, "a declaration cannot be a proposed order", draft=draft)
                in_body = declaration()
                in_body["signature_in_body"], in_body["signature"] = True, None
                self.refused(in_body, "a declaration cannot be a proposed order or carry signature_in_body", draft=draft)
                untitled = declaration()
                untitled["title"] = "Statement of Alex Example"
                self.refused(untitled, "the title does not say Declaration", draft=draft)
                stray = filing()
                stray["declaration"] = declaration()["declaration"]
                self.refused(stray, "the title does not say Declaration", draft=draft)
                stray["document_type"] = "motion"
                self.refused(stray, "a declaration object is given but document_type is 'motion'", draft=draft)
                for title in ("Declaration of Alex Example", "Alex Example's Declaration in Support of Motion to Compel",
                              "SECOND SUPPLEMENTAL DECLARATION OF ALEX EXAMPLE", "Unsworn Declaration of Alex Example"):
                    bare = filing()
                    bare["title"] = title
                    self.refused(bare, "a declaration needs a declaration object", draft=draft)
                extra = declaration(sworn="yes")
                self.refused(extra, "declaration has unknown key(s): 'sworn'", draft=draft)
                self.refused(declaration(signed_on=20261109), "declaration.signed_on must be a string or null", draft=draft)

    def test_other_documents_that_mention_a_declaration_still_build_without_the_closing(self):
        for title in ("Plaintiff's Motion to Strike Defendant's Declaration", "Brief in Opposition to the Declaration of Taylor Example",
                      "Defendant's Response to Plaintiff's Declaration"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                lines, _ = self.build(spec)
                self.assertNotIn(SENTENCE, lines)
        order = filing()
        order["title"] = "Order Granting Motion to Strike the Declaration of Taylor Example"
        order["proposed_order"], order["signature"] = True, None
        lines, _ = self.build(order)
        self.assertNotIn(SENTENCE, lines)
        affidavit = json.loads((ASSETS / "05b-affidavit.json").read_text(encoding="utf-8-sig"))
        lines, _ = self.build(affidavit, draft=True)
        self.assertNotIn(SENTENCE, lines)

    def test_template_spec_builds_to_the_same_text_as_the_reviewed_template(self):
        spec = json.loads((ASSETS / "05-declaration.json").read_text(encoding="utf-8-sig"))
        self.assertEqual(spec["document_type"], "declaration")
        self.assertFalse(any("penalty of false swearing" in block.get("text", "") for block in spec["body"]))
        lines, warning = self.build(spec, draft=True)
        self.assertIn("warning: draft declaration is incomplete", warning)
        reviewed = [p.text for p in Document(ASSETS / "05-declaration.docx").paragraphs if p.text.strip()]
        self.assertEqual(lines, reviewed)
        self.assertEqual(lines.count(SENTENCE), 1)
        self.output.unlink()
        with self.assertRaisesRegex(ValueError, "placeholder markers need review"):
            builder.build(spec, self.output)


if __name__ == "__main__":
    unittest.main()
