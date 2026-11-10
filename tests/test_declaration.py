"""Unsworn declarations in the filing builder: generated closing, reviewer statements, refusals. Invented facts only."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document

from test_builder import SCRIPT, builder, filing

ASSETS = SCRIPT.parents[1] / "assets"
SENTENCE = "I declare under penalty of false swearing under the law of Wisconsin that the foregoing is true and correct."
NOTICE = ("Applicability, exclusion status, body closing review, and actual execution have not been independently verified. "
          "Recheck these statements before reuse for another purpose.")


def declaration(**fields):
    spec = filing()
    spec["title"] = "Declaration of Alex Example in Support of Plaintiff's Motion to Compel"
    spec["document_type"] = "declaration"
    spec["body"] = [
        {"type": "p", "text": "I, Alex Example, state the following under Wis. Stat. § 887.015:"},
        {"type": "num", "text": "1. I am the plaintiff in this synthetic action and make this declaration on personal knowledge."},
    ]
    spec["declaration"] = {"use": "sworn_declaration_substitute", "purpose": "in support of the synthetic motion to compel",
                           "signed_on": "2026-11-09", "location": "Anytown", "state_or_country": "Wisconsin",
                           "body_reviewed": True, **fields}
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

    def test_final_build_needs_every_reviewer_statement_and_a_draft_warns(self):
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
            ({"purpose": None}, "declaration.purpose must name the intended current use"),
            ({"purpose": "   "}, "declaration.purpose must name the intended current use"),
            ({"body_reviewed": False}, "declaration.body_reviewed must be true"),
        ]
        for fields, expected in incomplete:
            with self.subTest(fields=fields):
                message = self.refused(declaration(**fields), expected)
                self.assertIn("declaration is incomplete", message)
                lines, warning = self.build(declaration(**fields), draft=True)
                self.assertIn("warning: draft declaration is incomplete", warning)
                self.assertIn(expected, warning)
                self.assertEqual(lines.count(SENTENCE), 1)
        unstated = declaration()
        del unstated["declaration"]["body_reviewed"]
        self.refused(unstated, "declaration.body_reviewed must be true")
        blank, _ = self.build(declaration(signed_on=None, location=None, state_or_country=None), draft=True)
        self.assertIn("Signed on the ____ day of __________, [YEAR], at [CITY OR OTHER LOCATION], [STATE OR COUNTRY].", blank)

    def test_every_successful_build_says_what_was_not_verified(self):
        _, notice = self.build(declaration())
        self.assertIn("generated from the reviewer's stated current use (in support of the synthetic motion to compel)", notice)
        self.assertIn(NOTICE, notice)
        self.assertNotIn("cannot", notice)
        service = declaration(purpose="proof of service of the synthetic motion")
        service["title"] = "Declaration of Service"
        self.assertIn(NOTICE, self.build(service)[1])
        reused = declaration()
        reused["title"] = "Declaration for Recording under Section 706.06"
        self.assertIn(NOTICE, self.build(reused)[1])
        self.assertIn("stated current use (none stated)", self.build(declaration(purpose=None), draft=True)[1])
        self.assertNotIn("Declaration form generated", self.build(filing())[1])
        source = Path(self.temporary.name) / "spec.json"
        source.write_text(json.dumps(declaration()), encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), str(source), "-o", str(self.output), "--overwrite"],
                                capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(NOTICE, result.stderr)

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

    def test_possible_closing_wording_is_put_to_the_reviewer_and_never_called_a_finding(self):
        possible = ("I declare under penalty of false swearing under the laws of Wisconsin that the foregoing is true and correct.",
                    "Pursuant to Wis. Stat. § 887.015, I declare the following to be true under penalty of false swearing under "
                    "the law of Wisconsin.",
                    "Under penalty of false swearing, I declare that the foregoing is true and correct.",
                    "I certify under penalty of perjury that the foregoing is true.",
                    "I, Alex Example, hereby swear that the statements above are true.",
                    "Signed on November 9, 2026, at Anytown, Wisconsin.",
                    "This concludes my statement. Signed on November 9, 2026, at Anytown, Wisconsin.",
                    "Executed on the 9th day of November, 2026.",
                    "Dated this 9th day of November, 2026.",
                    "Dated this week, the synthetic lease bears a new address.",
                    "3. The federal form I received says it is signed under penalty of perjury.")
        for text in possible:
            for draft in (False, True):
                with self.subTest(text=text, draft=draft):
                    spec = declaration()
                    spec["body"].append({"type": "p", "text": text})
                    message = self.refused(spec, "possible closing wording in the body:\nbody[2] ", draft=draft)
                    self.assertIn("A match is a question for the reviewer, not a finding", message)
                    self.assertIn("does not judge whether other wording conforms", message)
                    self.assertNotIn("invalid", message)
                    self.assertNotIn("carries its own", message)
                    spec["declaration"]["not_closings"] = [2]
                    lines, _ = self.build(spec, draft=draft)
                    self.assertEqual(lines.count(text), 1)
        for text in (SENTENCE, "5. " + SENTENCE.upper(), SENTENCE.replace(" under the law", "  under the law")):
            for draft in (False, True):
                with self.subTest(repeated=text, draft=draft):
                    spec = declaration(not_closings=[2])
                    spec["body"].append({"type": "p", "text": text})
                    message = self.refused(spec, "body[2]: this block's raw text contains the complete sentence reserved for "
                                           "the builder-generated closing", draft=draft)
                    self.assertIn("not_closings cannot override this raw-text restriction", message)
                    self.assertNotIn("twice", message)
        for draft in (False, True):
            with self.subTest(unprinted_block=True, draft=draft):
                spec = declaration()
                spec["body"].append({"type": "blank", "text": SENTENCE})
                message = self.refused(spec, "raw text contains the complete sentence reserved", draft=draft)
                self.assertNotIn("twice", message)
            with self.subTest(formatted_word=True, draft=draft):
                # The comparison is of raw text: inline markup makes this an ordinary screen match the reviewer resolves.
                spec = declaration()
                spec["body"].append({"type": "p", "text": SENTENCE.replace("Wisconsin", "**Wisconsin**")})
                self.refused(spec, "possible closing wording in the body:\nbody[2] ", draft=draft)
                spec["declaration"]["not_closings"] = [2]
                self.assertIn(NOTICE, self.build(spec, draft=draft)[1])
        spec = declaration()
        spec["body"] += [
            {"type": "num", "text": "2. I signed the synthetic lease on March 3, 2026."},
            {"type": "num", "text": "3. Attached as Exhibit A is a true and correct copy of the lease, which I received by mail."},
            {"type": "num", "text": "4. The notice is dated this year and was executed on paper."},
        ]
        lines, _ = self.build(spec)
        self.assertEqual(lines.count(SENTENCE), 1)

    def test_the_list_of_reviewed_blocks_must_match_the_screen_and_be_well_formed(self):
        for draft in (False, True):
            with self.subTest(draft=draft):
                self.refused(declaration(not_closings=[1]), "declaration.not_closings lists body[1], which the closing screen "
                             "does not match", draft=draft)
                self.refused(declaration(not_closings=[9]), "declaration.not_closings lists body[9]", draft=draft)
                for wrong in ("2", 2, {"2": True}, [True], ["2"], None):
                    self.refused(declaration(not_closings=wrong), "declaration.not_closings must be a list of body block numbers",
                                 draft=draft)
                for wrong in ("true", 1, 0, None, []):
                    self.refused(declaration(body_reviewed=wrong), "declaration.body_reviewed must be true or false", draft=draft)
        self.build(declaration(not_closings=[]))

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
                spec["body"].append({"type": "p", "text": "The declaration says it was signed under penalty of false swearing."})
                if title.startswith("Plaintiff's Motion"):
                    spec["motion"] = {"movers": ["first_party"], "relief": "to Strike Defendant's Declaration"}
                lines, notice = self.build(spec)
                self.assertNotIn(SENTENCE, lines)
                self.assertNotIn("Declaration form generated", notice)
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
        self.assertIs(spec["declaration"]["body_reviewed"], False)
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
