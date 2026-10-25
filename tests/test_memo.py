"""Behavioral regressions for the formal-memo linter; no fixture asserts real law."""

import datetime
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


LINTER = (Path(__file__).resolve().parents[1] / "skills" /
          "wisconsin-legal-interpretation" / "scripts" / "check_memo.py")
DISCLOSURE = "Not Shepardized or KeyCited."


def memo(source="sources/synthetic.md"):
    today = datetime.date.today().isoformat()
    return f"""---
type: research-memo
status: test-fixture
updated: {today}
operative_date: {today}; synthetic test only
framework_checked: {today}; synthetic test only
citator: NONE
citator_notes: No real authorities or citator checks in this synthetic fixture.
red_team: full
fatal_findings: 0
confidence: MODERATE
---
# Synthetic structural test, not legal research

## Question Presented
Does the synthetic condition apply?

## Short Answer
The synthetic condition likely applies. Confidence: MODERATE. {DISCLOSURE}

## Governing Text
> A synthetic condition applies when this test says it does.

Test provision § 900.1.
Source: `{source}`.

## Lens 1
Synthetic text and context support the condition.

## Lens 2
Reading A includes the conduct; Reading B argues the condition is narrower.

## Lens 3
Confidence: MODERATE. A different definition changes the synthetic outcome.

## Application
The synthetic actor satisfies the synthetic condition.

## Authority Table
| # | Citation | Cited for | Binding? | Citable? | Vintage OK? | Copy | How found | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | Test provision § 900.1 | Condition | No | Test only | Synthetic | `{source}` | Generated fixture | § 900.1 |

## Red Team Report
Run: synthetic declarations for testing, not a claim of real legal review.
Attacks run: 1-7, synthetic declaration only.
Checks not run: actual legal research, because this is not a legal memo.
Best contrary reading: a narrower definition could exclude the actor. This report tests the structural threshold and explicitly remains a synthetic fixture.
Confidence: MODERATE.

## Retrieval Record
`{source}` is a generated test file, not a retrieved legal source.
{DISCLOSURE}
"""


class FormalMemoTests(unittest.TestCase):
    def run_memo(self, text, source_name="synthetic.md", create_source=True):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sources = root / "sources"
            sources.mkdir()
            if create_source:
                (sources / source_name).write_text("Synthetic evidence, not law.\n", encoding="utf-8")
            path = root / "memo.md"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(LINTER), str(path), "--formal", "--sources", str(sources)],
                capture_output=True, text=True, encoding="utf-8",
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )

    def assert_clean(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_baseline_is_clean(self):
        self.assert_clean(self.run_memo(memo()))

    def test_utf8_bom_has_same_substantive_result(self):
        self.assert_clean(self.run_memo("\ufeff" + memo()))
        invalid = memo().replace("red_team: full", "red_team: none").replace("MODERATE", "LOW")
        for prefix in ("", "\ufeff"):
            result = self.run_memo(prefix + invalid)
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("red_team: none", result.stdout)

    def test_bom_does_not_hide_missing_frontmatter(self):
        for prefix in ("", "\ufeff"):
            result = self.run_memo(prefix + "# Missing frontmatter\n")
            self.assertEqual(result.returncode, 2, result.stdout)
            self.assertIn("No YAML frontmatter", result.stdout)

    def test_existing_source_with_spaces_is_not_truncated(self):
        name = "Wis-Stat-809.23 (2023-24).md"
        self.assert_clean(self.run_memo(memo("sources/" + name), source_name=name))

    def test_missing_source_with_spaces_is_still_rejected(self):
        result = self.run_memo(memo("sources/Missing Rule.md"), create_source=False)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Referenced source file not found", result.stdout)

    def test_disclosure_in_analysis_cannot_replace_decision_sections(self):
        text = memo().replace(DISCLOSURE, "").replace("## Lens 1\n", "## Lens 1\n" + DISCLOSURE + "\n")
        result = self.run_memo(text)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Short Answer", result.stdout)
        self.assertIn("Retrieval Record", result.stdout)

    def test_each_decision_section_needs_its_own_disclosure(self):
        for section in ("Short Answer", "Retrieval Record"):
            with self.subTest(section=section):
                text = memo()
                start = text.index("## " + section)
                next_heading = text.find("\n## ", start + 3)
                end = len(text) if next_heading == -1 else next_heading
                text = text[:start] + text[start:end].replace(DISCLOSURE, "") + text[end:]
                result = self.run_memo(text)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn(section, result.stdout)

    def test_corrected_finding_preserves_original_unresolved_wording(self):
        text = memo().replace("fatal_findings: 0\n", "fatal_findings: 0\nfatal_findings_first_pass: 1\n")
        text = text.replace("## Retrieval Record", """### Corrected on the second pass
> FINDING 1
> Severity: FATAL
> Claim: The governing source was retrieved.
> Defect: The source could not be found; the provenance issue remains unresolved.
> Fix: Retrieve the source and repeat the quote check.

Correction completed: the missing source was retrieved, compared, and checked again on the second pass. Synthetic history only.

## Retrieval Record""")
        self.assert_clean(self.run_memo(text))

    def test_live_fatal_outside_historical_quote_is_rejected(self):
        text = memo().replace("## Retrieval Record", "Severity: FATAL - missing source.\n\n## Retrieval Record")
        result = self.run_memo(text)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("MISMATCH: fatal_findings", result.stdout)

    def test_high_confidence_without_citator_is_rejected(self):
        result = self.run_memo(memo().replace("MODERATE", "HIGH"))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("citator was not run", result.stdout)

    def test_missing_archive_source_is_rejected(self):
        result = self.run_memo(memo(), create_source=False)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Referenced source file not found", result.stdout)

    def test_skipped_red_team_is_rejected_in_formal_mode(self):
        text = memo().replace("red_team: full", "red_team: none").replace("MODERATE", "LOW")
        text = text.replace("## Red Team Report\n", "## Red Team Report\nRed team not run.\n")
        result = self.run_memo(text)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("red_team: none", result.stdout)

    def high_confidence_memo(self, *lines):
        today = datetime.date.today().isoformat()
        text = memo().replace(
            "citator: NONE\ncitator_notes: No real authorities or citator checks in this synthetic fixture.",
            f"citator: KeyCite\ncitator_date: {today}\ncitator_signal: none\ncitator_notes: synthetic",
        ).replace(DISCLOSURE, "").replace("MODERATE", "HIGH")
        return text.replace("## Application\n", "## Application\n" + "".join(l + "\n" for l in lines))

    def test_high_confidence_control_is_clean(self):
        self.assert_clean(self.run_memo(self.high_confidence_memo()))

    def test_unverified_marker_after_a_negation_word_still_blocks_high_confidence(self):
        for line in ("The 2019 amendment was not retrieved [UNVERIFIED] but the answer relies on it.",
                     "There is no copy of the 2019 amendment [UNVERIFIED]; the answer relies on its text.",
                     "No [UNVERIFIED] marker remains on the first point, but the second is [UNVERIFIED]."):
            with self.subTest(line=line):
                result = self.run_memo(self.high_confidence_memo(line))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("UNVERIFIED", result.stdout)

    def test_marker_exemption_does_not_cross_a_clause_boundary(self):
        for line in ("The statutory cite is [UNVERIFIED]; markers are not optional.",
                     "The lease date is [UNVERIFIED], and the marker is not removed.",
                     "The lease date is [UNVERIFIED]: markers are never optional.",
                     "Is the lease date [UNVERIFIED]? The marker is not removed.",
                     "The rent term was not retrieved; [UNVERIFIED] marker applies.",
                     # Third review: marker prose in the same clause, and a rule-file name on the line.
                     "The instrument is [UNVERIFIED] and the marker is not removed.",
                     "The instrument is [UNVERIFIED] and markers are not optional.",
                     "The instrument is [UNVERIFIED]; memo-format.md requires a warning."):
            with self.subTest(line=line):
                result = self.run_memo(self.high_confidence_memo(line))
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertIn("confidence: HIGH is not available while [UNVERIFIED]", result.stdout)

    def test_sentence_stating_the_marker_rule_is_not_counted(self):
        for line in ("Confidence is HIGH because no [UNVERIFIED] marker remains.",
                     "Zero [UNVERIFIED] markers were applied.",
                     "[UNVERIFIED] markers: none.",
                     "[UNVERIFIED] markers remain: none.",
                     "The [UNVERIFIED] marker no longer applies to any authority.",
                     # Third review: a parenthetical inside the clearance sentence, and a noun use on a rule line.
                     "The [UNVERIFIED] marker, now obsolete, no longer applies.",
                     "memo-format.md requires an [UNVERIFIED] marker on every unretrieved citation."):
            with self.subTest(line=line):
                self.assert_clean(self.run_memo(self.high_confidence_memo(line)))

    def test_report_exemption_ends_at_the_next_peer_heading(self):
        # Third review: a "## Further Analysis" after the report inherited its no-pincite
        # exemption; a "### Corrected" block inside the report must keep it.
        text = memo().replace("## Red Team Report\n", (
            "## Red Team Report\n### Corrected on the second pass\n"
            "> FINDING 1, reproduced from the first pass.\n\n"), 1)
        text = text.replace("## Retrieval Record\n", (
            "## Further Analysis\n"
            "> Jane Q. Example promised to pay rent on the first of each month.\n\n"
            "The synthetic promise supports the condition.\n\n"
            "## Retrieval Record\n"), 1)
        result = self.run_memo(text)
        self.assertEqual(result.returncode, 2, result.stdout)
        body = text.split("\n---", 1)[1].splitlines()
        line = body.index("> Jane Q. Example promised to pay rent on the first of each month.") + 1
        self.assertIn(f"Block quote at line {line} has no pincite", result.stdout)
        quoted = body.index("> FINDING 1, reproduced from the first pass.") + 1
        self.assertNotIn(f"Block quote at line {quoted} has no pincite", result.stdout)

    def test_corrected_heading_without_report_exempts_only_its_own_block(self):
        text = memo()
        start = text.index("## Red Team Report")
        text = text[:start] + text[text.index("## Retrieval Record"):]
        text = text.replace("## Application\n", (
            "## Application\n### Corrected on the second pass\n"
            "> FINDING 1, reproduced from the first pass.\n\n"
            "## Further Analysis\n"
            "> Jane Q. Example promised to pay rent on the first of each month.\n\n"
            "The synthetic promise supports the condition.\n\n"))
        result = self.run_memo(text)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("Missing required section: Red Team Report", result.stdout)
        line = text.split("\n---", 1)[1].splitlines().index(
            "> Jane Q. Example promised to pay rent on the first of each month.") + 1
        self.assertIn(f"Block quote at line {line} has no pincite", result.stdout)
        quoted = text.split("\n---", 1)[1].splitlines().index(
            "> FINDING 1, reproduced from the first pass.") + 1
        self.assertNotIn(f"Block quote at line {quoted} has no pincite", result.stdout)
    def test_memo_that_is_not_utf8_is_an_error_exit_not_a_traceback(self):
        base = memo()
        cases = (("utf-16", base.encode("utf-16")),
                 ("cp1252", base.replace("Synthetic", "Synthetic “quoted”", 1).encode("cp1252")))
        for label, raw in cases:
            with self.subTest(encoding=label), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / "sources").mkdir()
                (root / "sources" / "synthetic.md").write_text("Synthetic evidence, not law.\n", encoding="utf-8")
                path = root / "memo.md"
                path.write_bytes(raw)
                result = subprocess.run(
                    [sys.executable, str(LINTER), str(path), "--formal", "--sources", str(root / "sources")],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                self.assertNotIn("Traceback", result.stderr)
                self.assertIn("cannot read memo", result.stderr)
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
    def test_memo_name_outside_console_code_page_still_prints_the_lint_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            (root / "sources" / "synthetic.md").write_text("Synthetic evidence, not law.\n", encoding="utf-8")
            path = root / "Memo-Łukasz.md"
            path.write_text(memo(), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(LINTER), str(path), "--formal", "--sources", str(root / "sources")],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONIOENCODING": "cp1252"},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Structurally clean", result.stdout)


if __name__ == "__main__":
    unittest.main()
