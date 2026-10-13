"""Test trigger-evaluation scoring with fake predictions; no model or network is involved."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import trigger_eval

CC, INT, WL = "cite-check", "wisconsin-legal-interpretation", "wisconsin-legal-writing"


def run_main(*argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(sys, "argv", ["trigger_eval.py", *argv]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = trigger_eval.main()
        except SystemExit as exc:  # argparse errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def perfect_runs(item, name, runs=3):
    """What a host that routed every query correctly would report."""
    triggered = [name] if item["should_trigger"] else ([item["expected_skill"]] if item["expected_skill"] else [])
    return [list(triggered) for _ in range(runs)]


class TriggerEvalTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sets = trigger_eval.load_queries()

    def predictions(self, mutate=None, runs=3, **extra):
        entries = [{"skill": name, "query": item["query"], "runs": perfect_runs(item, name, runs)}
                   for name, items in self.sets.items() for item in items]
        if mutate:
            mutate({(e["skill"], e["query"]): e for e in entries})
        return {"schema_version": 1, "host": "fake host", "model": "fake model", "predictions": entries, **extra}

    def write(self, data, name="predictions.json"):
        path = self.root / name
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return str(path)

    def query(self, name, split=None, **match):
        return next(i for i in self.sets[name] if (split is None or i["split"] == split)
                    and all(i[k] == v for k, v in match.items()))

    # --- the committed query files ---

    def test_committed_query_files_match_the_documented_shape(self):
        self.assertEqual(set(self.sets), {CC, INT, WL})
        everything = []
        for name, items in self.sets.items():
            self.assertEqual(len(items), 20)
            counts = {c: sum(1 for i in items if i["category"] == c) for c in trigger_eval.CATEGORIES}
            self.assertEqual(counts, {"positive": 9, "near-miss": 6, "cross-skill": 5})
            self.assertEqual(sum(1 for i in items if i["split"] == "train"), 12)
            for split in trigger_eval.SPLITS:
                part = [i for i in items if i["split"] == split]
                self.assertTrue(any(i["should_trigger"] for i in part) and any(not i["should_trigger"] for i in part))
                self.assertTrue(any(i["category"] == "cross-skill" for i in part))
            self.assertEqual({i["expected_skill"] for i in items if i["category"] == "cross-skill"} & {name}, set())
            everything += [i["query"] for i in items]
        self.assertEqual(len(everything), len(set(everything)))

    def test_queries_avoid_em_and_en_dashes(self):
        for items in self.sets.values():
            for item in items:
                self.assertNotRegex(item["query"], "[–—]")

    def test_validate_command_succeeds(self):
        code, out, _ = run_main("validate")
        self.assertEqual(code, 0)
        self.assertIn("no models were run", out)

    def test_query_file_mutations_are_rejected(self):
        original = ROOT / "evals/triggers"
        mutations = {
            "missing key": lambda items: items[0].pop("split"),
            "extra key": lambda items: items[0].__setitem__("note", "x"),
            "string should_trigger": lambda items: items[0].__setitem__("should_trigger", "true"),
            "empty query": lambda items: items[0].__setitem__("query", "  "),
            "bad category": lambda items: items[0].__setitem__("category", "other"),
            "bad split": lambda items: items[0].__setitem__("split", "test"),
            "unknown expected skill": lambda items: items[0].__setitem__("expected_skill", "no-such-skill"),
            "positive naming another skill": lambda items: next(i for i in items if i["category"] == "positive").__setitem__("expected_skill", INT),
            "near-miss that should trigger": lambda items: next(i for i in items if i["category"] == "near-miss").__setitem__("should_trigger", True),
            "cross-skill naming itself": lambda items: next(i for i in items if i["category"] == "cross-skill").__setitem__("expected_skill", CC),
            "duplicate query": lambda items: items[1].__setitem__("query", items[0]["query"]),
            "not a list": lambda items: items.clear(),
        }
        for label, mutate in mutations.items():
            with self.subTest(label):
                copy = self.root / label.replace(" ", "-")
                shutil.copytree(original, copy)
                path = copy / CC / trigger_eval.QUERY_FILE
                items = json.loads(path.read_text(encoding="utf-8"))
                mutate(items)
                path.write_text(json.dumps(items), encoding="utf-8")
                with self.assertRaises(ValueError):
                    trigger_eval.load_queries(copy)

    def test_a_split_with_only_one_label_is_rejected(self):
        copy = self.root / "one-label"
        shutil.copytree(ROOT / "evals/triggers", copy)
        path = copy / CC / trigger_eval.QUERY_FILE
        items = json.loads(path.read_text(encoding="utf-8"))
        for item in items:
            if item["split"] == "validation" and item["should_trigger"]:
                item.update(should_trigger=False, category="near-miss", expected_skill=None)
        path.write_text(json.dumps(items), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "both should-trigger and should-not-trigger"):
            trigger_eval.load_queries(copy)

    # --- offline scoring ---

    def test_perfect_predictions_pass_and_report_is_written(self):
        report = self.root / "report.json"
        code, out, _ = run_main("score", "--predictions", self.write(self.predictions()), "--report", str(report))
        self.assertEqual(code, 0, out)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(data["passed"])
        self.assertEqual(data["mode"], "offline-predictions")
        self.assertEqual(data["threshold"], 0.5)
        self.assertEqual(data["run_metadata"]["model"], "fake model")
        self.assertIn("does not establish general reliability", data["scope"])
        for name in self.sets:
            stats = data["skills"][name]["splits"]["all"]
            self.assertEqual((stats["precision"], stats["recall"], stats["pass_rate"]), (1.0, 1.0, 1.0))
            self.assertEqual(stats["cross_skill_routed_to_expected"], 5)
            self.assertEqual(set(data["skills"][name]["splits"]), {"all", "train", "validation"})
        self.assertIn("PASS", out)
        # An existing report is never overwritten.
        code, _, err = run_main("score", "--predictions", self.write(self.predictions()), "--report", str(report))
        self.assertEqual(code, 2)
        self.assertIn("trigger_eval:", err)

    def test_precision_recall_and_failures_are_counted_per_skill(self):
        missed = self.query(CC, "train", category="positive")
        unwanted = self.query(CC, "validation", category="near-miss")

        def mutate(entries):
            entries[(CC, missed["query"])]["runs"] = [[], [], []]
            entries[(CC, unwanted["query"])]["runs"] = [[CC], [CC], [CC]]
        report = self.root / "report.json"
        code, out, _ = run_main("score", "--predictions", self.write(self.predictions(mutate)),
                                "--report", str(report), "--skill", CC)
        self.assertEqual(code, 1)
        stats = json.loads(report.read_text(encoding="utf-8"))["skills"][CC]["splits"]
        self.assertEqual((stats["all"]["true_positives"], stats["all"]["false_negatives"],
                          stats["all"]["false_positives"], stats["all"]["true_negatives"]), (8, 1, 1, 10))
        self.assertAlmostEqual(stats["all"]["precision"], 8 / 9, places=3)
        self.assertAlmostEqual(stats["all"]["recall"], 8 / 9, places=3)
        self.assertEqual(stats["train"]["false_negatives"], 1)
        self.assertEqual(stats["validation"]["false_positives"], 1)
        self.assertIn("missed trigger", out)
        self.assertIn("unwanted trigger", out)
        self.assertIn("FAIL", out)

    def test_threshold_is_strict_in_both_directions(self):
        positive = self.query(WL, category="positive")
        negative = self.query(WL, category="near-miss")
        cases = [  # (runs reported for the skill, positive passes, negative passes)
            ([[WL], [WL], []], True, False),     # 2 of 3 = 0.67
            ([[WL], [], []], False, True),       # 1 of 3 = 0.33
            ([[WL], [WL], [], []], False, False),  # 2 of 4 = 0.5 exactly: a tie fails both ways
        ]
        for runs, positive_passes, negative_passes in cases:
            with self.subTest(runs=runs):
                row_p = trigger_eval.score_skill(WL, [positive], {positive["query"]: runs}, 0.5, 1.0, "all")["queries"][0]
                row_n = trigger_eval.score_skill(WL, [negative], {negative["query"]: runs}, 0.5, 1.0, "all")["queries"][0]
                self.assertEqual((row_p["passed"], row_n["passed"]), (positive_passes, negative_passes))
        tied = trigger_eval.score_skill(WL, [positive], {positive["query"]: cases[2][0]}, 0.5, 1.0, "all")
        self.assertEqual(tied["splits"]["all"]["ties_at_threshold"], 1)

    def test_threshold_option_changes_the_outcome(self):
        positive = self.query(CC, category="positive")

        def mutate(entries):
            entries[(CC, positive["query"])]["runs"] = [[CC], [CC], [], [], []]  # rate 0.4
        path = self.write(self.predictions(mutate, runs=5))
        self.assertEqual(run_main("score", "--predictions", path, "--skill", CC)[0], 1)
        self.assertEqual(run_main("score", "--predictions", path, "--skill", CC, "--threshold", "0.3")[0], 0)
        self.assertEqual(run_main("score", "--predictions", path, "--skill", CC, "--min-pass-rate", "0.9")[0], 0)

    def test_cross_skill_routing_is_reported_separately_from_pass(self):
        cross = self.query(INT, category="cross-skill")

        def mutate(entries):
            entries[(INT, cross["query"])]["runs"] = [[], [], []]  # nothing triggered: passes for INT, but not routed
        report = self.root / "report.json"
        code, _, _ = run_main("score", "--predictions", self.write(self.predictions(mutate)),
                              "--report", str(report), "--skill", INT)
        self.assertEqual(code, 0)
        stats = json.loads(report.read_text(encoding="utf-8"))["skills"][INT]["splits"]["all"]
        self.assertEqual((stats["cross_skill_routed_to_expected"], stats["cross_skill_total"]), (4, 5))

    def test_split_option_scores_only_that_split(self):
        wrong = self.query(CC, "train", category="positive")

        def mutate(entries):
            entries[(CC, wrong["query"])]["runs"] = [[], [], []]
        path = self.write(self.predictions(mutate))
        self.assertEqual(run_main("score", "--predictions", path, "--skill", CC, "--split", "train")[0], 1)
        code, out, _ = run_main("score", "--predictions", path, "--skill", CC, "--split", "validation")
        self.assertEqual(code, 0)
        self.assertNotIn(" train ", out)

    def test_even_run_counts_warn(self):
        report = self.root / "report.json"
        run_main("score", "--predictions", self.write(self.predictions(runs=2)), "--report", str(report))
        warnings = json.loads(report.read_text(encoding="utf-8"))["warnings"]
        self.assertTrue(any("even number of runs" in w for w in warnings))

    # --- malformed or incomplete predictions ---

    def test_malformed_predictions_exit_2_with_a_message(self):
        first = next(iter(self.sets[CC]))
        broken = {
            "not json": "{ this is not json",
            "wrong schema version": {**self.predictions(), "schema_version": 2},
            "unknown top-level key": {**self.predictions(), "extra": 1},
            "predictions not a list": {"schema_version": 1, "predictions": {}},
            "entry missing runs": {"schema_version": 1, "predictions": [{"skill": CC, "query": first["query"]}]},
            "unknown skill set": {"schema_version": 1, "predictions": [{"skill": "other", "query": first["query"], "runs": [[]]}]},
            "query not in set": {"schema_version": 1, "predictions": [{"skill": CC, "query": "not a real query", "runs": [[]]}]},
            "run is a string": {"schema_version": 1, "predictions": [{"skill": CC, "query": first["query"], "runs": ["cite-check"]}]},
            "run holds a non-string": {"schema_version": 1, "predictions": [{"skill": CC, "query": first["query"], "runs": [[1]]}]},
            "empty runs": {"schema_version": 1, "predictions": [{"skill": CC, "query": first["query"], "runs": []}]},
            "too few queries": {"schema_version": 1, "predictions": [{"skill": CC, "query": first["query"], "runs": [[CC]]}]},
        }
        for label, data in broken.items():
            with self.subTest(label):
                code, out, err = run_main("score", "--predictions", self.write(data))
                self.assertEqual(code, 2)
                self.assertTrue(err.startswith("trigger_eval:"))
                self.assertNotIn("PASS", out)

    def test_duplicate_prediction_and_missing_file_exit_2(self):
        data = self.predictions()
        data["predictions"].append(dict(data["predictions"][0]))
        self.assertEqual(run_main("score", "--predictions", self.write(data))[0], 2)
        self.assertEqual(run_main("score", "--predictions", str(self.root / "absent.json"))[0], 2)

    def test_incomplete_predictions_never_pass(self):
        data = self.predictions()
        data["predictions"] = [e for e in data["predictions"] if e["skill"] != WL]
        code, _, err = run_main("score", "--predictions", self.write(data))
        self.assertEqual(code, 2)
        self.assertIn(WL, err)
        # Limiting to the skills that were actually predicted is explicit, not silent.
        self.assertEqual(run_main("score", "--predictions", self.write(data), "--skill", CC, "--skill", INT)[0], 0)

    def test_bad_options_exit_2(self):
        path = self.write(self.predictions())
        self.assertEqual(run_main("score", "--predictions", path, "--threshold", "1.5")[0], 2)
        self.assertEqual(run_main("score", "--predictions", path, "--skill", "nope")[0], 2)

    # --- command mode, with a local stand-in for a host ---

    STUB = ("import sys, json; q = sys.stdin.read().lower() if len(sys.argv) < 2 else sys.argv[1].lower(); "
            "hits = ['cite-check'] if ('verify' in q or 'check' in q) else []; print(json.dumps(hits))")

    def config(self, command, **extra):
        return self.write({"command": command, "runs": 1, **extra}, "config.json")

    def test_command_mode_runs_the_supplied_command_per_query(self):
        report = self.root / "report.json"
        saved = self.root / "saved.json"
        code, out, _ = run_main("run", "--config", self.config([sys.executable, "-c", self.STUB], host="stub", model="stub-model"),
                                "--skill", CC, "--split", "validation", "--report", str(report),
                                "--save-predictions", str(saved), "--min-pass-rate", "0")
        self.assertEqual(code, 0, out)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(data["mode"], "command")
        self.assertEqual(data["run_metadata"]["model"], "stub-model")
        self.assertEqual(len(data["skills"][CC]["queries"]), 8)
        self.assertTrue(all(r["runs"] == 1 for r in data["skills"][CC]["queries"]))
        # The saved predictions file can be re-scored offline to the same result.
        rescored = self.root / "rescored.json"
        code, _, _ = run_main("score", "--predictions", str(saved), "--skill", CC, "--split", "validation",
                              "--report", str(rescored), "--min-pass-rate", "0")
        self.assertEqual(code, 0)
        again = json.loads(rescored.read_text(encoding="utf-8"))
        self.assertEqual(again["skills"][CC]["splits"]["all"], data["skills"][CC]["splits"]["all"])

    def test_command_mode_substitutes_the_query_placeholder(self):
        config = self.config([sys.executable, "-c", self.STUB, "{query}"])
        code, _, _ = run_main("run", "--config", config, "--skill", CC, "--split", "validation", "--min-pass-rate", "0")
        self.assertEqual(code, 0)

    def test_command_failures_exit_2(self):
        cases = {
            "non-zero exit": [sys.executable, "-c", "import sys; sys.exit(3)"],
            "not json": [sys.executable, "-c", "print('cite-check')"],
            "wrong json shape": [sys.executable, "-c", "print('{\"a\": 1}')"],
            "missing program": [str(self.root / "no-such-program")],
        }
        for label, command in cases.items():
            with self.subTest(label):
                code, _, err = run_main("run", "--config", self.config(command), "--skill", CC, "--split", "validation")
                self.assertEqual(code, 2)
                self.assertTrue(err.startswith("trigger_eval:"))

    def test_command_output_object_form_is_accepted(self):
        self.assertEqual(trigger_eval.parse_triggered('{"triggered": ["cite-check", "cite-check"]}'), ["cite-check"])
        self.assertEqual(trigger_eval.parse_triggered("[]"), [])

    def test_bad_config_exits_2(self):
        for label, data in {"no command": {}, "empty command": {"command": []}, "string command": {"command": "python x.py"},
                            "bad runs": {"command": ["x"], "runs": 0}, "unknown key": {"command": ["x"], "shell": True},
                            "bad timeout": {"command": ["x"], "timeout_seconds": 0}}.items():
            with self.subTest(label):
                self.assertEqual(run_main("run", "--config", self.write(data, "bad.json"))[0], 2)

    def test_script_makes_no_network_calls(self):
        source = (ROOT / "scripts/trigger_eval.py").read_text(encoding="utf-8")
        for module in ("socket", "urllib", "http", "requests", "ssl", "ftplib", "smtplib"):
            self.assertNotRegex(source, rf"^\s*(import|from)\s+{module}\b")


if __name__ == "__main__":
    unittest.main()
