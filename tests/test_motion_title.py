"""Motion titles in the filing builder: titles are generated from the reviewer's fields and compared whole.

Invented parties only. The complaint corpus test freezes the recognizer merged in pull request 37 so that a
later change to the shared title helpers cannot allow a complaint title that recognizer refused.
"""
import contextlib
import io
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest

from test_builder import SCRIPT, builder, filing

ASSETS = SCRIPT.parents[1] / "assets"
RULE = "Wis. Stat. s. 802.01(2)(d) requires the caption of every written motion"
NOTICE = ("This is not a check of statutory compliance; party status, completeness, legal adequacy and document "
          "classification remain unverified.")
NOT_GENERATED = "the title is not one the builder generates from the motion object"


def motion(title, movers=("first_party",), relief="to Compel", **extra):
    spec = filing()   # first party Alex Example, Plaintiff; second party Taylor Example, Defendant
    spec["title"] = title
    spec["motion"] = {"movers": list(movers), "relief": relief, **extra}
    return spec


# ---- the complaint recognizer as merged in pull request 37 (commit 3a7a3d7), frozen here on purpose
_Q = (r"(?:verified|amended|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th)|"
      r"supplemental|class\s+action|third[- ]party|corrected|restated|proposed|consolidated)")
_FROZEN_TITLE = re.compile(r"^\W*(?:" + _Q + r"\s+)*(?:summons|complaint)\b", re.IGNORECASE)
_FROZEN_POSSESSIVE = re.compile(r"(?:'s|s'|’s|s’)$")
_FROZEN_WORD = re.compile(r"^(?:answer|motion|brief|response|reply|opposition|notice|order|memorandum|declaration|"
                          r"affidavit|objection|stipulation|to|in|of|for|and)$", re.IGNORECASE)


def frozen_refuses(title):
    if _FROZEN_TITLE.search(title):
        return True
    words = title.split()
    for index, word in enumerate(words[:6]):
        if _FROZEN_WORD.match(word.strip(".,:;")):
            return False
        if _FROZEN_POSSESSIVE.search(word.rstrip(".,:;")):
            return bool(_FROZEN_TITLE.search(" ".join(words[index + 1:])))
    return False


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

    def passes(self, spec, **options):
        output = self.builds(spec, **options)
        self.assertNotIn("warning", output)
        self.assertIn(NOTICE, output)
        return output

    def refused(self, spec, expected, **options):
        self.output.unlink(missing_ok=True)
        with self.assertRaises(ValueError) as caught:
            with contextlib.redirect_stderr(io.StringIO()):
                builder.build(spec, self.output, **options)
        self.assertIn(expected, str(caught.exception))
        self.assertFalse(self.output.exists())
        return str(caught.exception)

    def test_each_generated_title_builds_and_says_what_was_not_verified(self):
        both = ("first_party", "second_party")
        passing = [
            motion("Plaintiff's Motion to Compel"),
            motion("PLAINTIFF’S   MOTION TO COMPEL"),
            motion("Motion of Plaintiff to Compel"),
            motion("Alex Example's Motion to Compel"),
            motion("Motion of Alex Example to Compel"),
            motion("Plaintiff Alex Example's Motion to Compel"),
            motion("Motion of Plaintiff Alex Example to Compel"),
            motion("Defendant's Motion for Protective Order", movers=("second_party",), relief="for Protective Order"),
            motion("Plaintiff's Motion to Strike Defendant's Declaration", relief="to Strike Defendant's Declaration"),
            motion("Plaintiff's Motion in Limine to Exclude Synthetic Evidence", relief="in Limine to Exclude Synthetic Evidence"),
            motion("Plaintiff's Renewed Motion to Compel", qualifier="renewed"),
            motion("Ex Parte Motion of Plaintiff to Compel", qualifier="ex_parte"),
            motion("Plaintiff's Stipulated Motion to Extend Time", relief="to Extend Time", qualifier="stipulated"),
            motion("Plaintiff's Notice of Motion and Motion to Compel", with_notice=True),
            motion("Amended Notice of Motion and Motion of Plaintiff to Compel", with_notice=True, qualifier="amended"),
            motion("Plaintiff's and Defendant's Joint Motion to Extend Time", movers=both, relief="to Extend Time", qualifier="joint"),
            motion("Joint Motion of Plaintiff and Defendant to Extend Time", movers=both, relief="to Extend Time", qualifier="joint"),
            motion("Plaintiff's and Defendant's Motion to Extend Time", movers=both, relief="to Extend Time"),
            motion("Acme Records, Inc.'s Motion to Quash Subpoena", movers=({"name": "Acme Records, Inc."},), relief="to Quash Subpoena"),
            motion("Non-Party Acme Records, Inc.'s Motion to Quash Subpoena",
                   movers=({"name": "Acme Records, Inc.", "designation": "Non-Party"},), relief="to Quash Subpoena"),
            motion("Motion of Alex Example, Taylor Example and Acme Records, Inc. to Stay",
                   movers=("first_party", "second_party", {"name": "Acme Records, Inc."}), relief="to Stay"),
        ]
        for spec in passing:
            for draft in (False, True):
                with self.subTest(title=spec["title"], draft=draft):
                    output = self.passes(spec, draft=draft)
                    self.assertIn("one supported motion title generated from the reviewer's party references", output)
        self.assertEqual(set(builder.MOTION_QUALIFIERS), {"amended", "renewed", "emergency", "expedited", "unopposed", "stipulated",
                                                          "agreed", "joint", "ex_parte", "supplemental"})
        for qualifier, word in builder.MOTION_QUALIFIERS.items():
            movers = ("first_party", "second_party") if qualifier == "joint" else ("first_party",)
            lead = "Plaintiff's and Defendant's" if qualifier == "joint" else "Plaintiff's"
            self.passes(motion(f"{lead} {word} Motion to Compel", movers=movers, qualifier=qualifier))
        self.assertNotIn("supported motion title", self.builds(filing()))

    def test_a_title_the_fields_do_not_generate_is_refused_and_the_generated_titles_are_listed(self):
        cases = [
            motion("Motion to Compel"),
            motion("Plaintiff's Motion to Compel Discovery"),
            motion("Plaintiff's Motion to Compel, Joined by Acme Records"),
            motion("Plaintiff's and Defendant's Motion to Compel"),
            motion("Defendant's Motion to Compel"),
            motion("Plaintiffs' Motion to Compel"),
            motion("Plaintiff's Renewed Motion to Compel"),
            motion("Plaintiff's Motion to Compel", qualifier="renewed"),
            motion("Plaintiff's Notice of Motion and Motion to Compel"),
            motion("Plaintiff's Motion: Compel"),
            motion("Stranger's Motion to Compel"),
        ]
        for spec in cases:
            with self.subTest(title=spec["title"], fields=spec["motion"]):
                message = self.refused(spec, NOT_GENERATED)
                self.assertIn(RULE, message)
                self.assertIn("Other titles may be lawful; this tool supports these", message)
                self.assertIn("Plaintiff's ", message)
                drafted = self.builds(spec, draft=True)
                self.assertIn("warning: draft motion: " + RULE, drafted)
                self.assertNotIn("supported motion title generated", drafted)
        mixed = motion("Motion of Plaintiff, Defendant and Acme Records, Inc. to Stay",
                       movers=("first_party", "second_party", {"name": "Acme Records, Inc."}), relief="to Stay")
        self.assertIn("      Motion of Alex Example, Taylor Example and Acme Records, Inc. to Stay", self.refused(mixed, NOT_GENERATED))
        listed = self.refused(motion("Motion to Compel"), NOT_GENERATED)
        for title in ("Plaintiff's Motion to Compel", "Motion of Plaintiff to Compel", "Plaintiff Alex Example's Motion to Compel",
                      "Motion of Plaintiff Alex Example to Compel", "Alex Example's Motion to Compel", "Motion of Alex Example to Compel"):
            self.assertIn("      " + title, listed)

    def test_the_title_is_never_read_for_roles(self):
        # the attacks of the third review: a party named for a boilerplate word, a mover named only in the relief,
        # a person named Joint, and designations shared by both parties
        parte = motion("Plaintiff's and Parte's Motion to Compel")
        parte["second_party"]["name"] = "Parte"
        self.refused(parte, NOT_GENERATED)
        by = motion("Plaintiff's Motion to Compel by By")
        by["second_party"]["name"] = "By"
        self.refused(by, NOT_GENERATED)
        self.refused(motion("Motion to Strike Plaintiff's Declaration", relief="to Strike Plaintiff's Declaration"), NOT_GENERATED)
        self.passes(motion("Plaintiff's Motion to Strike Plaintiff's Declaration", relief="to Strike Plaintiff's Declaration"))
        joint = motion("Joint's Motion to Compel")
        joint["first_party"]["name"], joint["signature"]["name"] = "Joint", "Joint"
        self.passes(joint)
        self.passes({**joint, "title": "Motion of Joint to Compel"})
        for mover, other in (("first_party", "second_party"), ("second_party", "first_party")):
            with self.subTest(shared_designation=mover):
                shared = motion("Petitioner's Motion to Compel", movers=(mover,))
                shared["first_party"]["designation"] = shared["second_party"]["designation"] = "Petitioner"
                message = self.refused(shared, NOT_GENERATED)
                self.assertNotIn("      Petitioner's Motion to Compel", message)
                name = shared[mover]["name"]
                self.assertIn(f"      Petitioner {name}'s Motion to Compel", message)
                self.assertNotIn(shared[other]["name"], message)
                shared["title"] = f"Petitioner {name}'s Motion to Compel"
                self.passes(shared)
        collision = motion("Petitioner Respondent's and Respondent Taylor Example's Motion to Compel", movers=("first_party", "second_party"))
        collision["first_party"].update(name="Respondent", designation="Petitioner")
        collision["second_party"]["designation"] = "Respondent"
        collision["signature"]["name"] = "Respondent"
        self.passes(collision)

    def test_documented_limits_one_title_can_come_from_different_fields(self):
        # The second review's collisions. Each title is a candidate for the fields supplied, so each builds with the
        # conditional notice. The title cannot be read back into its fields, and the tool does not claim it can.
        alone = motion("Motion of Plaintiff and Defendant to Compel")
        alone["first_party"]["name"] = alone["signature"]["name"] = "Plaintiff and Defendant"
        both = motion("Motion of Plaintiff and Defendant to Compel", movers=("first_party", "second_party"))
        both["first_party"]["name"] = both["signature"]["name"] = "Plaintiff and Defendant"
        of_name = motion("Motion of Alex of Morgan to Compel")
        of_name["first_party"]["name"] = of_name["signature"]["name"] = "Alex of Morgan"
        of_relief = motion("Motion of Alex to Compel".replace("Alex to", "Alex of Morgan to"), relief="of Morgan to Compel")
        of_relief["first_party"]["name"] = of_relief["signature"]["name"] = "Alex"
        for spec in (alone, both, of_name, of_relief):
            for draft in (False, True):
                with self.subTest(fields=spec["motion"], name=spec["first_party"]["name"], draft=draft):
                    self.passes(spec, draft=draft)
            extra = {**spec, "title": spec["title"] + " and for Sanctions"}
            self.refused(extra, NOT_GENERATED)
        # An outside mover's name is not printed by the caption; a designation-only title omits it. Disclosed, not decided.
        outside = motion("Intervenor's Motion to Compel", movers=({"name": "Casey Example", "designation": "Intervenor"},))
        self.passes(outside)
        from docx import Document
        printed = "\n".join(paragraph.text for paragraph in Document(self.output).paragraphs)
        self.assertNotIn("CASEY EXAMPLE", printed.upper())
        named = {**outside, "title": "Intervenor Casey Example's Motion to Compel"}
        self.passes(named)
        self.assertIn("CASEY EXAMPLE", "\n".join(paragraph.text for paragraph in Document(self.output).paragraphs).upper())

    def test_normalisation_is_exactly_case_whitespace_and_one_apostrophe_pair(self):
        self.passes(motion("plaintiff\u2019s   motion\tto  compel"))
        self.passes(motion("Plaintiff's Motion to Compel Discovery", relief="  to Compel\n Discovery "))
        for mark in ("\u2018", "\u02bc", "\uff07", "`"):
            with self.subTest(apostrophe=repr(mark)):
                self.refused(motion(f"Plaintiff{mark}s Motion to Compel"), NOT_GENERATED)
        self.refused(motion("Plaintiff's Motion to Compel."), NOT_GENERATED)
        self.passes(motion("Plaintiff's Motion to Compel.", relief="to Compel."))
        many = motion("placeholder", movers=tuple({"name": f"Party{number} Jones"} for number in range(5)))
        message = self.refused(many, NOT_GENERATED)
        self.assertEqual(message.count("\n      "), 8)
        self.assertGreater(len(builder._motion_titles(many, many["motion"])[0]), 8)

    def test_names_are_used_as_written(self):
        for name in ("José Example", "Zoë Müller-Example", "Мария Пример", "山田 太郎", "Acme+ (Holdings) Co.", "Chris Jones"):
            with self.subTest(name=name):
                spec = motion(f"Motion of {name} to Compel")
                spec["first_party"]["name"] = name
                spec["signature"]["name"] = name
                self.passes(spec)
                spec["title"] = f"{name}'s Motion to Compel"
                self.passes(spec)
                spec["title"] = f"Motion of {name[:-1]} to Compel"
                self.refused(spec, NOT_GENERATED)
        jones = motion("Chris Jones' Motion to Compel")
        jones["first_party"]["name"] = jones["signature"]["name"] = "Chris Jones"
        self.passes(jones)
        example = motion("Alex Example' Motion to Compel")
        self.refused(example, NOT_GENERATED)

    def test_incomplete_statements_are_refused_in_a_final_build_and_warned_in_a_draft(self):
        cases = [
            (motion("Plaintiff's Motion to Compel", movers=()), "motion.movers must list each party seeking the order or relief"),
            (motion("Plaintiff's Motion to Compel", relief=""), "motion.relief must briefly describe"),
            (motion("Plaintiff's Motion to Compel", relief=" ... "), "motion.relief must briefly describe"),
            (motion("Plaintiff's Motion to Compel", movers=("first_party", "first_party")), "motion.movers lists 'Alex Example' twice"),
            (motion("Plaintiff's Motion to Compel", movers=("Plaintiff",)), "'Plaintiff' is not \"first_party\" or \"second_party\""),
            (motion("Plaintiff's Motion to Compel", movers=({"name": "Alex Example"},)), "'Alex Example' is a party in the caption"),
            (motion("Plaintiff's Motion to Compel", movers=({"name": "  "},)), "a mover outside the caption needs a name"),
            (motion("Acme's Motion to Compel", movers=({"name": "Acme"}, {"name": "ACME"})), "motion.movers lists 'ACME' twice"),
            (motion("Plaintiff's Joint Motion to Compel", qualifier="joint"), "lists fewer than two distinct movers"),
        ]
        for spec, expected in cases:
            with self.subTest(expected=expected):
                message = self.refused(spec, expected)
                self.assertIn(RULE, message)
                self.assertIn(expected, self.builds(spec, draft=True))
        for key in ("movers", "relief"):
            absent = motion("Plaintiff's Motion to Compel")
            del absent["motion"][key]
            self.refused(absent, f"motion.{key} must")
        for title in ("Plaintiff's Motion to Compel", "Motion to Compel", "Notice of Motion and Motion to Compel",
                      "Plaintiff Alex Example's Emergency Motion to Compel", "Plaintiff's and Defendant's Joint Motion to Stay"):
            with self.subTest(no_object=title):
                spec = filing()
                spec["title"] = title
                self.refused(spec, "a written motion needs a motion object")
                self.assertIn("a written motion needs a motion object", self.builds(spec, draft=True))
        typed = filing()
        typed["document_type"] = "motion"
        self.refused(typed, "a written motion needs a motion object")

    def test_a_notice_must_say_whether_it_is_the_motion_and_document_type_must_be_text(self):
        for title in ("Notice of Motion Hearing", "Notice of Hearing", "Notice of Motion", "Plaintiff's Notice of Hearing"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                message = self.refused(spec, "document_type does not say whether this document is the written motion")
                self.assertIn("s. 802.01(2)(a)", message)
                self.assertIn("document_type does not say", self.builds(spec, draft=True))
                spec["document_type"] = None
                self.refused(spec, "document_type does not say whether")
                spec["document_type"] = "notice"
                self.assertNotIn("supported motion title", self.builds(spec))
                spec["document_type"] = "motion"
                self.refused(spec, "a written motion needs a motion object")
                for wrong in (False, True, 0, 1, "", "  ", [], {}, ["motion"]):
                    for draft in (False, True):
                        spec["document_type"] = wrong
                        self.refused(spec, "document_type must be a non-empty string, or be left out", draft=draft)
        other = filing()
        other["document_type"] = 0
        self.refused(other, "document_type must be a non-empty string")
        # absent and null are the same thing: unspecified
        for title, expected in (("Plaintiff's Motion to Compel", "a written motion needs a motion object"),
                                ("Notice of Hearing", "document_type does not say whether")):
            absent, null = filing(), filing()
            absent["title"] = null["title"] = title
            null["document_type"] = None
            self.assertEqual(self.refused(absent, expected), self.refused(null, expected))
        untitled = filing()
        untitled["document_type"] = None
        self.assertEqual(self.builds(untitled), "")

    def test_contradictions_and_wrong_types_are_refused_in_every_mode(self):
        good = "Plaintiff's Motion to Compel"
        for draft in (False, True):
            with self.subTest(draft=draft):
                typed = motion(good)
                typed["document_type"] = "brief"
                self.refused(typed, "a motion object is given but document_type is 'brief'", draft=draft)
                titled = filing()
                titled["title"], titled["document_type"] = good, "brief"
                self.refused(titled, "the title opens as a motion but document_type is 'brief'", draft=draft)
                order = motion(good)
                order["proposed_order"], order["signature"] = True, None
                self.refused(order, "a motion cannot be a proposed order", draft=draft)
                self.refused(motion(good, granted=True), "motion has unknown key(s): 'granted'", draft=draft)
                self.refused(motion(good, moving_parties=["Plaintiff"]), "motion has unknown key(s): 'moving_parties'", draft=draft)
                for wrong in ("first_party", False, 0, "", {}, None, [1], [None], [["first_party"]], [{"designation": "Non-Party"}],
                              [{"name": 7}], [{"name": "Acme", "role": "mover"}], [{"name": "Acme", "designation": None}]):
                    bad = motion(good)
                    bad["motion"]["movers"] = wrong
                    self.refused(bad, "motion.movers must be a list whose items are", draft=draft)
                for wrong in (7, False, None, [], {}):
                    self.refused(motion(good, relief=wrong), "motion.relief must be a string", draft=draft)
                for wrong in ("true", 1, 0, None, []):
                    self.refused(motion(good, with_notice=wrong), "motion.with_notice must be true or false", draft=draft)
                for wrong in ("Renewed", "joint motion", "in_limine", "", 0, False, True, ["joint"]):
                    self.refused(motion(good, qualifier=wrong), "motion.qualifier must be null or one of:", draft=draft)
                for wrong in (["first_party"], "first_party", False, 0, ""):
                    bad = filing()
                    bad["title"], bad["motion"] = good, wrong
                    self.refused(bad, "motion must be an object", draft=draft)
        self.passes(motion(good, qualifier=None, with_notice=False))

    def test_documents_the_recogniser_does_not_treat_as_motions(self):
        titles = ("Defendant's Brief in Support of Motion to Dismiss", "Plaintiff's Response to Defendant's Motion to Compel",
                  "Withdrawal of Plaintiff's Motion to Compel", "Plaintiff's Reply in Support of Motion to Compel",
                  "Synthetic motion for testing", "Answer to Complaint",
                  # stated limits: these may be motions, and are checked only when document_type or a motion object says so
                  "Cross-Motion for Summary Judgment", "Plaintiff's Cross-Motion for Summary Judgment", "Aviso de Audiencia",
                  "Amended Notice of Hearing", "Application for an Order Compelling Discovery")
        for title in titles:
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                self.assertEqual(self.builds(spec), "")
        typed = filing()
        typed["title"], typed["document_type"] = "Cross-Motion for Summary Judgment", "motion"
        self.refused(typed, "a written motion needs a motion object")
        typed["motion"] = {"movers": ["first_party"], "relief": "for Summary Judgment"}
        self.refused(typed, NOT_GENERATED)
        order = filing()
        order["title"] = "Order Granting Plaintiff's Motion to Compel"
        order["proposed_order"], order["signature"] = True, None
        self.assertEqual(self.builds(order), "")

    def test_every_complaint_title_the_merged_guard_refused_is_still_refused(self):
        names = ("Alex Example", "Jane Q. Example", "Jones", "Smith & Jones", "State of Anystate", "Acme Records, Inc.")
        leads = ("", "Plaintiff's ", "Plaintiffs' ", "Plaintiff Jane Q. Example's ", "Smith & Jones's ", "Smith & Jones' ",
                 "Defendant’s ", "State of Anystate's ", "Plaintiff's and Defendant's ", "Answer to ", "Withdrawal of ",
                 "Summary of Plaintiff's ", "Exhibits to Plaintiff's ")
        kinds = ("Complaint", "Summons", "Summons and Complaint", "Amended Complaint for Damages", "Fourth Amended Complaint",
                 "Third-Party Complaint", "VERIFIED COMPLAINT", "Counterclaim", "Motion to Amend Complaint")
        refused_before = newly_refused = 0
        for first, second, lead, kind, typed in itertools.product(names, names[:3], leads, kinds, (None, "brief")):
            spec = filing()
            spec["first_party"]["name"], spec["second_party"]["name"] = first, second
            spec["title"] = lead + kind
            if typed:
                spec["document_type"] = typed
            before = frozen_refuses(spec["title"])
            now = builder._is_complaint_or_summons(spec)
            refused_before += before
            newly_refused += now and not before
            if before:
                self.assertTrue(now, f"merged guard refused {spec['title']!r} for parties {first!r}, {second!r}")
        self.assertGreater(refused_before, 500)
        self.assertGreater(newly_refused, 0)
        for first, title in (("Jane Q. Example", "Smith & Jones's Complaint"), ("Smith & Jones", "Smith & Jones' Complaint"),
                             ("State of Anystate", "State of Anystate's Complaint"), ("Alex Example", "Plaintiff's and Defendant's Complaint")):
            for typed, draft in itertools.product((None, "brief"), (False, True)):
                with self.subTest(title=title, typed=typed, draft=draft):
                    spec = filing()
                    spec["first_party"]["name"], spec["title"] = first, title
                    if typed:
                        spec["document_type"] = typed
                    self.refused(spec, "does not produce a complaint or a summons", draft=draft)
        for title in ("Answer to Complaint", "Summary of Plaintiff's Complaint", "Exhibits to Plaintiff's Complaint"):
            spec = filing()
            spec["title"] = title
            self.assertEqual(self.builds(spec), "")

    def test_bundled_motion_specs_and_the_example_generate_their_own_titles(self):
        for stem in ("01-motion", "07-motion-to-enlarge-time", "08-motion-for-reconsideration", "11-motion-attorney-signed",
                     "12-motion-to-compel"):
            with self.subTest(template=stem):
                spec = json.loads((ASSETS / f"{stem}.json").read_text(encoding="utf-8-sig"))
                self.assertEqual(spec["document_type"], "motion")
                titles, problems = builder._motion_titles(spec, spec["motion"])
                self.assertEqual(problems, [])
                self.assertEqual(titles[0], spec["title"])
                self.assertNotIn("draft motion", self.builds(spec, draft=True))
        example = json.loads(json.dumps(builder.EXAMPLE))
        self.assertEqual(example["motion"], {"movers": ["first_party"], "qualifier": None, "relief": "to Compel"})
        self.assertNotIn("draft motion", self.builds(example, draft=True))


if __name__ == "__main__":
    unittest.main()
