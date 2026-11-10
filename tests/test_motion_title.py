"""Motion titles in the filing builder: one supported title form checked against the reviewer's statements.

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
NOTICE = ("The builder has not verified party status, the completeness of that list, legal adequacy of the description, or "
          "whether the document is the motion rather than a separate hearing notice.")


def motion(title, movers=("Plaintiff",), relief="to Compel", **extra):
    spec = filing()
    spec["title"] = title
    spec["motion"] = {"moving_parties": list(movers), "relief": relief, **extra}
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

    def test_supported_titles_build_and_every_success_says_what_was_not_verified(self):
        passing = [
            motion("Plaintiff's Motion to Compel"),
            motion("PLAINTIFF'S MOTION TO COMPEL"),
            motion("Plaintiff’s Renewed Motion to Compel"),
            motion("Plaintiff's Motion: Dismissal", relief="Dismissal"),
            motion("Motion of Alex Example to Compel", movers=("Alex Example",)),
            motion("Motion of Plaintiff Alex Example to Compel", movers=("Plaintiff",)),
            motion("Motion of Plaintiff Alex Example to Compel", movers=("Plaintiff Alex Example",)),
            motion("Plaintiff's Notice of Motion and Motion to Compel"),
            motion("Defendant's Motion for Protective Order", movers=("Defendant",), relief="for Protective Order"),
            motion("Plaintiff's Motion to Strike Defendant's Declaration", relief="to Strike Defendant's Declaration"),
            motion("Joint Motion of Plaintiff and Defendant to Extend Time", movers=("Plaintiff", "Defendant"),
                   relief="to Extend Time"),
            motion("Plaintiff's and Defendant's Stipulated Motion to Extend Time", movers=("Plaintiff", "Taylor Example"),
                   relief="to Extend Time"),
            motion("Plaintiff's Stipulated Motion to Extend Time", relief="to Extend Time"),
            motion("Plaintiff's Agreed Motion to Extend Time", relief="to Extend Time"),
            motion("Non-Party Acme Records, Inc.'s Motion to Quash Subpoena", movers=("Non-Party Acme Records, Inc.",),
                   relief="to Quash Subpoena", outside_caption=["Non-Party Acme Records, Inc."]),
        ]
        for spec in passing:
            for draft in (False, True):
                with self.subTest(title=spec["title"], draft=draft):
                    output = self.passes(spec, draft=draft)
                    self.assertIn("Motion title checked against the reviewer's list of distinct moving parties", output)
        typed = motion("Plaintiff's Notice of Motion to Compel")
        typed["document_type"] = "motion"
        self.passes(typed)
        self.assertNotIn("Motion title checked", self.builds(filing()))

    def test_accented_and_non_latin_names_are_matched_as_written(self):
        for name in ("José Example", "Zoë Müller-Example", "Мария Пример", "山田 太郎"):
            with self.subTest(name=name):
                spec = motion(f"Motion of {name} to Compel", movers=(name,))
                spec["first_party"]["name"] = name
                spec["signature"]["name"] = name
                self.passes(spec)
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
        absent = motion("Plaintiff's Motion to Compel")
        del absent["motion"]["relief"]
        self.refused(absent, "motion.relief must briefly describe")
        request = motion("Request for Relief", relief="Relief")
        request["document_type"] = "motion"
        message = self.refused(request, "motion.relief must briefly describe")
        self.assertIn("the title does not name moving party 'Plaintiff'", message)

    def test_movers_must_be_distinct_parties_named_in_the_title_and_the_title_holds_nothing_else(self):
        self.refused(motion("Stranger's Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Stranger's Motion to Compel", movers=("Stranger",)),
                     "'Stranger' is not the name or designation of a party in this spec")
        self.refused(motion("Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Plaintiff's Motion to Compel", movers=()), "motion.moving_parties must name each party")
        absent = motion("Plaintiff's Motion to Compel")
        del absent["motion"]["moving_parties"]
        self.refused(absent, "motion.moving_parties must name each party")
        self.refused(motion("Plaintiff's Motion to Compel", movers=("Plaintiff", "Defendant")),
                     "the title does not name moving party 'Defendant'")
        self.refused(motion("Plaintiffs' Motion to Compel"), "the title does not name moving party 'Plaintiff'")
        # a second mover in the title that the fields omit
        for title in ("Plaintiff's and Stranger's Motion to Compel", "Motion of Plaintiff and Defendant to Compel",
                      "Plaintiff's Motion to Compel, Joined by Acme Records"):
            with self.subTest(extra=title):
                message = self.refused(motion(title), "the title has words that are not a declared mover")
                self.assertIn("add that party to motion.moving_parties", message)
        # the same party listed twice, under one name or two
        for movers in (("Plaintiff", "Plaintiff"), ("Plaintiff", "Alex Example"), ("Alex Example", "Plaintiff Alex Example")):
            with self.subTest(duplicate=movers):
                self.refused(motion("Plaintiff's Joint Motion to Compel", movers=movers),
                             "motion.moving_parties lists the same party twice")
        self.refused(motion("Joint Motion to Compel", movers=("Plaintiff", "Defendant")),
                     "the title does not name moving party 'Plaintiff'")
        self.refused(motion("Plaintiff's Joint Motion to Compel"), "names fewer than two distinct parties")
        outside = motion("Stranger's Motion to Compel", movers=("Stranger",), outside_caption=["Stranger"])
        self.passes(outside)

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
        self.passes(named)

    def test_a_notice_must_say_whether_it_is_the_motion(self):
        for title in ("Notice of Motion Hearing", "Notice of Hearing", "Notice of Motion", "Plaintiff's Notice of Hearing"):
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                message = self.refused(spec, "document_type does not say whether this document is the written motion")
                self.assertIn("s. 802.01(2)(a)", message)
                self.assertIn("document_type does not say", self.builds(spec, draft=True))
                spec["document_type"] = "notice"
                output = self.builds(spec)
                self.assertNotIn("Motion title checked", output)
                spec["document_type"] = "motion"
                self.refused(spec, "a written motion needs a motion object")

    def test_contradictions_and_wrong_types_are_refused_in_every_mode(self):
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
                for wrong in ("Plaintiff", False, 0, "", {}, None, [1], [None]):
                    bad = motion("Plaintiff's Motion to Compel")
                    bad["motion"]["moving_parties"] = wrong
                    self.refused(bad, "motion.moving_parties must be a list of strings", draft=draft)
                    bad = motion("Plaintiff's Motion to Compel", outside_caption=wrong)
                    self.refused(bad, "motion.outside_caption must be a list of strings", draft=draft)
                for wrong in (7, False, None, [], {}):
                    self.refused(motion("Plaintiff's Motion to Compel", relief=wrong), "motion.relief must be a string", draft=draft)
                for wrong in (["Plaintiff"], "Plaintiff", False, 0, ""):
                    bad = filing()
                    bad["title"], bad["motion"] = "Plaintiff's Motion to Compel", wrong
                    self.refused(bad, "motion must be an object", draft=draft)
        self.passes(motion("Plaintiff's Motion to Compel", outside_caption=[]))

    def test_other_documents_that_mention_a_motion_are_not_checked(self):
        titles = ("Defendant's Brief in Support of Motion to Dismiss", "Plaintiff's Response to Defendant's Motion to Compel",
                  "Withdrawal of Plaintiff's Motion to Compel", "Plaintiff's Reply in Support of Motion to Compel",
                  "Synthetic motion for testing", "Answer to Complaint")
        for title in titles:
            with self.subTest(title=title):
                spec = filing()
                spec["title"] = title
                self.assertEqual(self.builds(spec), "")
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
        checked = refused_before = newly_refused = 0
        for first, second, lead, kind, typed, draft in itertools.product(names, names[:3], leads, kinds, (None, "brief"), (False, True)):
            spec = filing()
            spec["first_party"]["name"], spec["second_party"]["name"] = first, second
            spec["title"] = lead + kind
            if typed:
                spec["document_type"] = typed
            before = frozen_refuses(spec["title"])
            now = builder._is_complaint_or_summons(spec)
            checked += 1
            refused_before += before
            newly_refused += now and not before
            if before:
                self.assertTrue(now, f"merged guard refused {spec['title']!r} for parties {first!r}, {second!r}")
        self.assertGreater(refused_before, 1000)
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
                self.assertNotIn("words that are not a declared mover", warning)
        example = json.loads(json.dumps(builder.EXAMPLE))
        self.assertEqual(example["motion"], {"moving_parties": ["Plaintiff"], "relief": "to Compel"})
        self.assertNotIn("draft motion", self.builds(example, draft=True))


if __name__ == "__main__":
    unittest.main()
