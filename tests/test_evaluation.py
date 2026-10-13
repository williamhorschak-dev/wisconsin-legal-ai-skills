"""Test evaluation integrity; these tests do not stand in for model trials."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evaluate
import source_registry


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.run = self.root / "run"

    def prepare(self):
        return evaluate.prepare(self.run, ["C03"])

    def test_validate_rejects_malformed_rubric_criteria_with_exit_2(self):
        data = evaluate.read_json(evaluate.SUITE)
        mutations = {
            "missing critical": lambda c: c["rubric"][0].pop("critical"),
            "string critical": lambda c: c["rubric"][0].__setitem__("critical", "yes"),
            "empty criterion": lambda c: c["rubric"][0].__setitem__("criterion", "  "),
            "missing id": lambda c: c["rubric"][0].pop("id"),
            "string rubric": lambda c: c.__setitem__("rubric", "not a list"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as folder:
                fresh = json.loads(json.dumps(data))
                mutate(fresh["cases"][2])
                suite = Path(folder) / "cases.json"
                suite.write_text(json.dumps(fresh), encoding="utf-8")
                with mock.patch.object(evaluate, "SUITE", suite),                         mock.patch.object(sys, "argv", ["evaluate.py", "validate"]),                         mock.patch.object(sys, "stderr"):
                    self.assertEqual(evaluate.main(), 2)

    def collect(self, plan):
        response = self.root / "response.txt"
        response.write_text("Synthetic harness fixture, not a model response.\n", encoding="utf-8")
        for trial in plan["trials"]:
            evaluate.import_response(self.run, trial["id"], response, "unit-test fixture", "no-model")

    def test_prepared_trials_are_paired_and_hide_scoring_criteria(self):
        plan = self.prepare()
        self.assertEqual([t["condition"] for t in plan["trials"]], ["baseline", "with-skills"])
        baseline = evaluate.read_json(self.run / plan["trials"][0]["input"])
        treatment = evaluate.read_json(self.run / plan["trials"][1]["input"])
        self.assertEqual(baseline["system"], treatment["system"])
        self.assertIn(baseline["user"], treatment["user"])
        for trial in plan["trials"]:
            prompt = evaluate.read_json(self.run / trial["input"])["user"]
            self.assertNotIn(trial["rubric"][0]["criterion"], prompt)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_unrun_or_unreviewed_trials_never_pass(self):
        plan = self.prepare()
        pending = self.root / "pending.json"
        evaluate.review_template(self.run, pending)
        self.assertEqual(evaluate.summarize(self.run, pending)["counts"]["not_assessed"], 2)
        self.collect(plan)
        reviews = self.root / "reviews.json"
        evaluate.review_template(self.run, reviews)
        self.assertNotEqual(evaluate.summarize(self.run, reviews)["gate"], "pass")

    def test_changed_inputs_and_responses_invalidate_results(self):
        plan = self.prepare()
        self.collect(plan)
        reviews = self.root / "reviews.json"
        evaluate.review_template(self.run, reviews)
        result_path = self.run / f"{plan['trials'][0]['id']}.result.json"
        result = evaluate.read_json(result_path)
        result["response"] = "Changed response"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "response changed"):
            evaluate.summarize(self.run, reviews)
        input_path = self.run / plan["trials"][0]["input"]
        input_path.write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "input changed"):
            evaluate.checked_plan(self.run)

    def test_baseline_failure_does_not_mask_a_passing_treatment_or_vice_versa(self):
        plan = self.prepare()
        self.collect(plan)
        path = self.root / "reviews.json"
        evaluate.review_template(self.run, path)
        review = evaluate.read_json(path)
        review.update(reviewer="test fixture", method="unit test only; not legal review")
        for trial in review["trials"]:
            for criterion in trial["criteria"]:
                criterion.update(verdict="fail" if "baseline" in trial["id"] else "pass", evidence="Synthetic test assertion only.")
        path.write_text(json.dumps(review), encoding="utf-8")
        self.assertEqual(evaluate.summarize(self.run, path)["gate"], "pass")
        review["trials"][1]["criteria"][0]["verdict"] = "fail"
        # The original rubric, not editable review metadata, controls criticality.
        review["trials"][1]["criteria"][0]["critical"] = False
        path.write_text(json.dumps(review), encoding="utf-8")
        result = evaluate.summarize(self.run, path)
        self.assertNotEqual(result["gate"], "pass")
        self.assertIn("C03-with-skills-1/attribution", result["critical_failures"])

    def test_missing_response_cannot_receive_a_fabricated_pass(self):
        self.prepare()
        path = self.root / "reviews.json"
        evaluate.review_template(self.run, path)
        review = evaluate.read_json(path)
        review.update(reviewer="fixture", method="fixture")
        review["trials"][0]["criteria"][0].update(verdict="pass", evidence="Invented")
        path.write_text(json.dumps(review), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "never collected"):
            evaluate.summarize(self.run, path)

    def test_all_suite_profiles_and_fixtures_resolve(self):
        self.assertEqual(len(evaluate.load_suite()["cases"]), 24)
        with self.assertRaises(ValueError):
            evaluate.prepare(self.run, ["missing"])
        self.assertFalse(self.run.exists())

    def test_collector_disables_tools_and_records_reported_model(self):
        import subprocess
        self.prepare()
        output = json.dumps({"is_error": False, "result": "Synthetic response only", "modelUsage": {"fixture-model": {}}, "subtype": "success"})
        completed = subprocess.CompletedProcess([], 0, output, "")
        with mock.patch.object(evaluate.subprocess, "check_output", return_value="fixture CLI"), mock.patch.object(evaluate.subprocess, "run", return_value=completed) as run:
            results = evaluate.collect_claude(self.run)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["models"], ["fixture-model"])
        for call in run.call_args_list:
            command = call.args[0]
            self.assertIn("--safe-mode", command)
            self.assertIn("--no-session-persistence", command)
            self.assertEqual(command[command.index("--tools") + 1], "")
            self.assertFalse(call.kwargs["shell"])

    def test_provider_failure_stops_and_cannot_silently_resume(self):
        import subprocess
        self.prepare()
        completed = subprocess.CompletedProcess([], 1, json.dumps({"is_error": True, "result": "Synthetic provider failure"}), "")
        with mock.patch.object(evaluate.subprocess, "check_output", return_value="fixture CLI"), mock.patch.object(evaluate.subprocess, "run", return_value=completed) as run:
            with self.assertRaisesRegex(ValueError, "stopped"):
                evaluate.collect_claude(self.run)
            self.assertEqual(run.call_count, 1)
            with self.assertRaisesRegex(ValueError, "cannot resume"):
                evaluate.collect_claude(self.run)
            self.assertEqual(run.call_count, 1)


class RegistryTests(unittest.TestCase):
    def test_due_boundary_and_unreviewed_record_are_explicit(self):
        from datetime import date
        data = {"sources": [{"id": "one", "status": "focused_primary_check", "last_reviewed": "2026-01-01",
                             "review_interval_days": 30, "url": "https://example.invalid", "affected_files": []}]}
        self.assertEqual(source_registry.due_sources(data, date(2026, 1, 30)), [])
        self.assertEqual(len(source_registry.due_sources(data, date(2026, 1, 31))), 1)
        data["sources"][0].update(status="needs_primary_review", last_reviewed=None)
        self.assertEqual(source_registry.due_sources(data, date(2026, 1, 1))[0]["review_due"], None)


if __name__ == "__main__":
    unittest.main()
