"""Motion titles in the filing builder: the reviewer's moving-party and relief fields checked against the title."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from test_builder import SCRIPT, builder, filing

ASSETS = SCRIPT.parents[1] / "assets"
RULE = "Wis. Stat. s. 802.01(2)(d) requires the caption of every written motion"


def motion(title, movers=("Plaintiff",), relief="to Compel", **extra):
    spec = filing()
    spec["title"] = title
    spec["motion"] = {"moving_parties": list(movers), "relief": relief, **extra}
    return spec


class MotionTitleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "review.docx"

    def builds(self, spec, **options):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            builder.build(spec, self.output, overwrite=True, **options)
        return errors.getvalue()

    def refused(self, spec, expected, **options):
        self.output.unlink(missing_ok=True)
        with self.assertRaises(ValueError) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                builder.build(spec, self.output, **options)
        self.assertIn(expected, str(caught.exception))
        self.assertFalse(self.output.exists())
        return str(caught.exception)

    def test_titles_that_name_the_mover_and_describe_the_relief_build(self):
        passing = [
            motion("Plaintiff's Motion to Compel"),
            motion("PLAINTIFF'S MOTION TO COMPEL"),
            motion("Plaintiff’s Renewed Motion to Compel"),
            motion("Plaintiff's Motion: Dismissal", relief="Dismissal"),
            motion("Motion of Alex Example to Compel", movers=("Alex Example",)),
            motion("Motion of Plaintiff Alex Example to Compel", movers=("Plaintiff",)),
            motion("Plaintiff's Notice of Motion and Motion to Compel"),
            motion("Defendant's Motion for Protective Order", movers=("Defendant",), relief="for Protective Order"),
            motion("Joint Motion of Plaintiff and Defendant to Extend Time", movers=("Plaintiff", "Defendant"),
                   relief="to Extend Time"),
            motion("Plaintiff's and Defendant's Stipulated Motion to Extend Time", movers=("Plaintiff", "Taylor Example"),
                   relief="to Extend Time"),
            motion("Non-Party Acme Records, Inc.'s Motion to Quash Subpoena", movers=("Acme Records, Inc.",),
                   relief="to Quash Subpoena", outside_caption=["Acme Records, Inc."]),
        ]
        for spec in passing:
            with self.subTest(title=spec["title"]):
                self.assertEqual(self.builds(spec), "")
        typed = motion("Request for Enlargement of Time by Plaintiff", relief="Enlargement of Time")
        typed["document_type"] = "motion"
        self.assertEqual(self.builds(typed), "")

    def test_accented_and_non_latin_names_are_matched_as_written(self):
        for name in ("José Example", "Zoë Müller-Example", "Мария Пример", "山田 太郎"):
            with self.subTest(name=name):
                spec = motion(f"Motion of {name} to Compel", movers=(name,))
                spec["first_party"]["name"] = name
                spec["signature"]["name"] = name
                self.assertEqual(self.builds(spec), "")
                spec["motion"]["moving_parties"] = [name[:-1]]
                self.refused(spec, "is not the name or designation of a party in this spec")

    def test_titles_without_a_relief_description_are_refused(self):
        cases = [
            (motion("Motion of Plaintiff", relief=""), "motion.relief must briefly describe"),
            (motion("Motion of Plaintiff", relief="Motion"), "motion.relief must briefly describe"),
            (motion("Motion of Plaintiff", relief="of Plaintiff"), "motion.relief must briefly describe"),
            (motion("Plaintiff's Notice of Motion and Motion", relief="Notice of Motion and Motion"),
             "motion.relief must briefly describe"),
            (motion("Plaintiff's Notice of Motion and Motion", relief="Plaintiff's"), "motion.relief must briefly describe"),
            (motion("Plaintiff's Motion for an Order", relief="for an Order"), "motion.relief must briefly describe"),
            (motion("Plaintiff's Motion", relief="to Compel"), "the title does not contain the relief description 'to Compel'"),
            (motion("Plaintiff's Motion to Compel", relief="to Dismiss"),
             "the title does not contain the relief description 'to Dismiss'"),
        ]
        for spec, expected in cases:
            with self.subTest(title=spec["title"], relief=spec["motion"]["relief"]):
                message = self.refused(spec, expected)
                self.assertIn(RULE, message)
                self.assertIn("warning: draft motion: " + RULE, self.builds(spec, draft=True))
        request = motion("Request for Relief", relief="Relief")
        request["document_type"] = "motion"
        message = self.refused(request, "motion.relief must briefly describe")
        self.assertIn("the title does not name moving party 'Plaintiff'", message)

    def test_movers_must_be_parties_and_must_be_named_in_the_title(self):
        self.refused(motion("Stranger's Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Stranger's Motion to Compel", movers=("Stranger",)),
                     "'Stranger' is not the name or designation of a party in this spec")
        self.refused(motion("Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Plaintiff's Motion to Compel", movers=()), "motion.moving_parties must name each party")
        self.refused(motion("Plaintiff's Motion to Compel", movers=("Plaintiff", "Defendant")),
                     "the title does not name moving party 'Defendant'")
        self.refused(motion("Plaintiffs' Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Joint Motion to Compel", movers=("Plaintiff", "Defendant")),
                     "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Plaintiff's Joint Motion to Compel"), "names fewer than two parties")
        self.refused(motion("Stipulated Motion of Plaintiff to Extend Time", relief="to Extend Time"),
                     "names fewer than two parties")
        outside = motion("Stranger's Motion to Compel", movers=("Stranger",), outside_caption=["Stranger"])
        self.assertEqual(self.builds(outside), "")

    def test_a_motion_without_the_fields_is_refused_and_a_draft_warns(self):
        for title in ("Plaintiff's Motion to Compel", "Motion to Compel", "Notice of Motion and Motion to Compel",
                      "Plaintiff Alex Example's Emergency Motion to Compel", "Plaintiff's and Defendant's Joint Motion to Stay"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                self.refused(spec, "a written motion needs a motion object")
                self.assertIn("a written motion needs a motion object", self.builds(spec, draft=True))
        typed = filing()
        typed["document_type"] = "motion"
        self.refused(typed, "a written motion needs a motion object")
        named = filing()
        named["first_party"]["name"] = "State of Anystate"
        named["title"] = "State of Anystate's Motion to Dismiss"
        self.refused(named, "a written motion needs a motion object")
        named["motion"] = {"moving_parties": ["State of Anystate"], "relief": "to Dismiss"}
        self.assertEqual(self.builds(named), "")

    def test_contradictions_and_malformed_fields_are_refused_in_every_mode(self):
        for draft in (False, True):
            with self.subTest(draft=draft):
                typed = motion("Plaintiff's Motion to Compel")
                typed["document_type"] = "brief"
                self.refused(typed, "a motion object is given but document_type is 'brief'", draft=draft)
                titled = filing()
                titled["title"], titled["document_type"] = "Plaintiff's Motion to Compel", "brief"
                self.refused(titled, "the title opens as a motion but document_type is 'brief'", draft=draft)
                order = motion("Plaintiff's Motion to Compel")
                order["proposed_order"], order["signature"] = True, None
                self.refused(order, "a motion cannot be a proposed order", draft=draft)
                self.refused(motion("Plaintiff's Motion to Compel", granted=True), "motion has unknown key(s): 'granted'", draft=draft)
                bad = motion("Plaintiff's Motion to Compel")
                bad["motion"]["moving_parties"] = "Plaintiff"
                self.refused(bad, "motion.moving_parties must be a list of strings", draft=draft)
                bad = motion("Plaintiff's Motion to Compel", relief=7)
                self.refused(bad, "motion.relief must be a string", draft=draft)
                bad = filing()
                bad["title"], bad["motion"] = "Plaintiff's Motion to Compel", ["Plaintiff"]
                self.refused(bad, "motion must be an object", draft=draft)

    def test_other_documents_that_mention_a_motion_are_not_checked(self):
        titles = ("Notice of Motion Hearing", "Notice of Hearing", "Defendant's Brief in Support of Motion to Dismiss",
                  "Plaintiff's Response to Defendant's Motion to Compel", "Withdrawal of Plaintiff's Motion to Compel",
                  "Plaintiff's Reply in Support of Motion to Compel", "Synthetic motion for testing")
        for title in titles:
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                self.assertEqual(self.builds(spec), "")
        order = filing()
        order["title"] = "Order Granting Plaintiff's Motion to Compel"
        order["proposed_order"], order["signature"] = True, None
        self.assertEqual(self.builds(order), "")

    def test_bundled_motion_specs_and_the_example_carry_the_fields(self):
        for stem in ("01-motion", "07-motion-to-enlarge-time", "08-motion-for-reconsideration", "11-motion-attorney-signed",
                     "12-motion-to-compel"):
            with self.subTest(template=stem):
                spec = json.loads((ASSETS / f"{stem}.json").read_text(encoding="utf-8-sig"))
                self.assertEqual(spec["document_type"], "motion")
                self.assertTrue(spec["motion"]["moving_parties"])
                self.assertIn(spec["motion"]["relief"].casefold(), spec["title"].casefold())
                warning = self.builds(spec, draft=True)
                self.assertNotIn("a written motion needs a motion object", warning)
                self.assertNotIn("does not name moving party", warning)
        example = json.loads(json.dumps(builder.EXAMPLE))
        self.assertEqual(example["motion"], {"moving_parties": ["Plaintiff"], "relief": "to Compel"})
        self.assertNotIn("draft motion", self.builds(example, draft=True))


if __name__ == "__main__":
    unittest.main()
