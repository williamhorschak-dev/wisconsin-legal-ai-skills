#!/usr/bin/env python3
"""Score whether each skill's description triggers on a fixed set of labeled queries.

Queries live in evals/triggers/<skill>/eval_queries.json. This script never calls a
network API or a model itself. It either (a) scores a static predictions file that an
operator collected elsewhere (`score`), or (b) runs a command the operator supplies, once
per query and run, and reads which skills that command says were triggered (`run`).
A passing score describes only these queries on the host and model that produced the
predictions. It is not a measure of general reliability or of legal accuracy.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import skill_tools

ROOT = Path(__file__).resolve().parents[1]
TRIGGERS = ROOT / "evals/triggers"
QUERY_FILE = "eval_queries.json"
CATEGORIES = ("positive", "near-miss", "cross-skill")
SPLITS = ("train", "validation")
VERDICT_SPLITS = ("all",) + SPLITS
QUERY_KEYS = {"query", "should_trigger", "expected_skill", "category", "split"}
DEFAULT_THRESHOLD = 0.5
MAX_RUNS = 25
SCOPE = ("Trigger rates for a small fixed query set on one host and model. This does not establish general "
         "reliability, other hosts or models, output quality, or legal accuracy.")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def skill_names():
    return [folder.name for folder in skill_tools.folders()]


def normalize(text):
    return re.sub(r"\s+", " ", text).strip().casefold()


def load_queries(root=None, names=None):
    """Return {skill: [query, ...]} after checking every file against the documented schema."""
    root = Path(TRIGGERS if root is None else root)
    names = list(names) if names is not None else skill_names()
    sets, seen = {}, {}
    for name in names:
        path = root / name / QUERY_FILE
        if not path.is_file():
            raise ValueError(f"missing query file: {path}")
        items = read_json(path)
        if not isinstance(items, list) or not items:
            raise ValueError(f"{name}: {QUERY_FILE} must be a non-empty JSON array")
        for index, item in enumerate(items):
            label = f"{name} query {index}"
            if not isinstance(item, dict) or set(item) != QUERY_KEYS:
                raise ValueError(f"{label}: expected exactly the keys {sorted(QUERY_KEYS)}")
            if not isinstance(item["query"], str) or not item["query"].strip():
                raise ValueError(f"{label}: query must be a non-empty string")
            if not isinstance(item["should_trigger"], bool):
                raise ValueError(f"{label}: should_trigger must be true or false")
            expected = item["expected_skill"]
            if expected is not None and expected not in names:
                raise ValueError(f"{label}: expected_skill must be null or one of {names}")
            if item["category"] not in CATEGORIES:
                raise ValueError(f"{label}: category must be one of {list(CATEGORIES)}")
            if item["split"] not in SPLITS:
                raise ValueError(f"{label}: split must be one of {list(SPLITS)}")
            category = item["category"]
            if category == "positive" and not (item["should_trigger"] and expected == name):
                raise ValueError(f"{label}: a positive must have should_trigger true and expected_skill {name}")
            if category == "near-miss" and (item["should_trigger"] or expected is not None):
                raise ValueError(f"{label}: a near-miss must have should_trigger false and expected_skill null")
            if category == "cross-skill" and (item["should_trigger"] or expected in (None, name)):
                raise ValueError(f"{label}: a cross-skill query must have should_trigger false and another skill expected")
            key = normalize(item["query"])
            if key in seen:
                raise ValueError(f"{label}: duplicate of {seen[key]}; queries must be unique across all skills")
            seen[key] = label
        for split in SPLITS:
            members = [item for item in items if item["split"] == split]
            if not any(i["should_trigger"] for i in members) or all(i["should_trigger"] for i in members):
                raise ValueError(f"{name}: the {split} split needs both should-trigger and should-not-trigger queries")
        sets[name] = items
    return sets


def trigger_rate(skill, runs):
    return sum(1 for run in runs if skill in run) / len(runs)


def passes(should_trigger, rate, threshold):
    """Strict, as the guidance words it: above the threshold, or below it. A tie fails either way."""
    return rate > threshold if should_trigger else rate < threshold


def ratio(numerator, denominator):
    return round(numerator / denominator, 4) if denominator else None


def summarize_rows(rows):
    tp = sum(1 for r in rows if r["should_trigger"] and r["passed"])
    fn = sum(1 for r in rows if r["should_trigger"] and not r["passed"])
    fp = sum(1 for r in rows if not r["should_trigger"] and not r["passed"])
    tn = sum(1 for r in rows if not r["should_trigger"] and r["passed"])
    cross = [r for r in rows if r["category"] == "cross-skill"]
    return {"queries": len(rows), "passed": sum(1 for r in rows if r["passed"]),
            "pass_rate": ratio(sum(1 for r in rows if r["passed"]), len(rows)),
            "true_positives": tp, "false_negatives": fn, "false_positives": fp, "true_negatives": tn,
            "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn),
            "ties_at_threshold": sum(1 for r in rows if r["trigger_rate"] == r["threshold"]),
            "cross_skill_routed_to_expected": sum(1 for r in cross if r["expected_skill_rate"] > r["threshold"]),
            "cross_skill_total": len(cross)}


def score_skill(name, items, observed, threshold, min_pass_rate, split):
    """observed maps query text to a list of runs; each run is the list of skills triggered."""
    rows = []
    for index, item in enumerate(items):
        if split != "all" and item["split"] != split:
            continue
        runs = observed[item["query"]]
        rate = trigger_rate(name, runs)
        seen = sorted({skill for run in runs for skill in run})
        expected = item["expected_skill"]
        rows.append({"index": index, "query": item["query"], "split": item["split"], "category": item["category"],
                     "should_trigger": item["should_trigger"], "expected_skill": expected, "runs": len(runs),
                     "triggers": sum(1 for run in runs if name in run), "trigger_rate": round(rate, 4),
                     "threshold": threshold, "passed": passes(item["should_trigger"], rate, threshold),
                     "expected_skill_rate": round(trigger_rate(expected, runs), 4) if expected else None,
                     "skills_triggered": {skill: round(trigger_rate(skill, runs), 4) for skill in seen}})
    splits = {label: summarize_rows([r for r in rows if label == "all" or r["split"] == label])
              for label in VERDICT_SPLITS if any(label == "all" or r["split"] == label for r in rows)}
    overall = splits["all"]
    return {"passed": overall["pass_rate"] is not None and overall["pass_rate"] >= min_pass_rate,
            "splits": splits, "queries": rows}


def build_report(sets, observed, threshold, min_pass_rate, split, mode, metadata, selected):
    warnings = []
    if any(len(runs) % 2 == 0 for per in observed.values() for runs in per.values()):
        warnings.append("Some queries have an even number of runs; a trigger rate equal to the threshold fails both ways. Use an odd count such as 3.")
    if any(len(runs) < 3 for per in observed.values() for runs in per.values()):
        warnings.append("Some queries have fewer than 3 runs; single runs are sensitive to model nondeterminism.")
    skills = {name: score_skill(name, sets[name], observed[name], threshold, min_pass_rate, split) for name in selected}
    return {"schema_version": 1, "tool": "scripts/trigger_eval.py", "mode": mode,
            "generated_at": datetime.now(timezone.utc).isoformat(), **skill_tools.provenance(),
            "threshold": threshold, "threshold_rule": "should-trigger passes above the threshold; should-not-trigger passes below it",
            "min_pass_rate": min_pass_rate, "verdict_split": split,
            "queries_content_sha256": {name: sha(json.dumps(sets[name], sort_keys=True).encode("utf-8")) for name in selected},
            "run_metadata": {**metadata, "note": "Supplied by the operator and not verified by this script."},
            "scope": SCOPE, "warnings": warnings, "skills": skills,
            "passed": all(entry["passed"] for entry in skills.values())}


def load_predictions(path, sets, selected, split="all"):
    data = read_json(path)
    allowed = {"schema_version", "host", "model", "collected", "predictions"}
    if not isinstance(data, dict) or set(data) - allowed or data.get("schema_version") != 1:
        raise ValueError("predictions file must be an object with schema_version 1 and keys " + ", ".join(sorted(allowed)))
    metadata = {}
    for key in ("host", "model", "collected"):
        if key in data:
            if not isinstance(data[key], str) or not data[key].strip():
                raise ValueError(f"{key} must be a non-empty string when present")
            metadata[key] = data[key]
    entries = data.get("predictions")
    if not isinstance(entries, list):
        raise ValueError("predictions must be an array")
    observed = {name: {} for name in sets}
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict) or set(entry) != {"skill", "query", "runs"}:
            raise ValueError(f"prediction {position}: expected exactly skill, query and runs")
        if entry["skill"] not in sets:
            raise ValueError(f"prediction {position}: unknown skill set {entry['skill']!r}")
        known = {item["query"] for item in sets[entry["skill"]]}
        if entry["query"] not in known:
            raise ValueError(f"prediction {position}: query is not in the {entry['skill']} set (copy it exactly)")
        if entry["query"] in observed[entry["skill"]]:
            raise ValueError(f"prediction {position}: duplicate query in the {entry['skill']} set")
        runs = entry["runs"]
        if not isinstance(runs, list) or not 1 <= len(runs) <= MAX_RUNS:
            raise ValueError(f"prediction {position}: runs must be a list of 1 to {MAX_RUNS} runs")
        clean = []
        for run in runs:
            if not isinstance(run, list) or any(not isinstance(s, str) or not s.strip() for s in run):
                raise ValueError(f"prediction {position}: each run must be a list of skill-name strings (empty if none triggered)")
            clean.append(sorted(set(run)))
        observed[entry["skill"]][entry["query"]] = clean
    for name in selected:
        needed = [i["query"] for i in sets[name] if split == "all" or i["split"] == split]
        missing = [q for q in needed if q not in observed[name]]
        if missing:
            raise ValueError(f"{name}: {len(missing)} of {len(needed)} queries have no prediction; first missing: {missing[0][:70]!r}")
    return observed, metadata


def load_config(path):
    config = read_json(path)
    allowed = {"command", "runs", "timeout_seconds", "host", "model"}
    if not isinstance(config, dict) or set(config) - allowed:
        raise ValueError("config must be an object with keys " + ", ".join(sorted(allowed)))
    command = config.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(a, str) or not a for a in command):
        raise ValueError("config command must be a non-empty list of strings (it is run without a shell)")
    runs = config.get("runs", 3)
    if isinstance(runs, bool) or not isinstance(runs, int) or not 1 <= runs <= 10:
        raise ValueError("config runs must be an integer from 1 to 10")
    timeout = config.get("timeout_seconds", 120)
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 1 <= timeout <= 600:
        raise ValueError("config timeout_seconds must be a number from 1 to 600")
    metadata = {}
    for key in ("host", "model"):
        if key in config:
            if not isinstance(config[key], str) or not config[key].strip():
                raise ValueError(f"config {key} must be a non-empty string when present")
            metadata[key] = config[key]
    return {"command": command, "runs": runs, "timeout": timeout}, metadata


def parse_triggered(stdout):
    """The command prints a JSON array of skill names, or an object with a `triggered` array."""
    try:
        value = json.loads(stdout)
    except ValueError as exc:
        raise ValueError("command output was not JSON; print an array of triggered skill names, [] for none") from exc
    if isinstance(value, dict) and set(value) == {"triggered"}:
        value = value["triggered"]
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        raise ValueError("command output must be a JSON array of skill-name strings or {\"triggered\": [...]}")
    return sorted(set(value))


def run_command(config, query):
    """One invocation. {query} in an argument is replaced; otherwise the query is sent on stdin."""
    by_argument = any("{query}" in arg for arg in config["command"])
    args = [arg.replace("{query}", query) for arg in config["command"]]
    try:
        completed = subprocess.run(args, input=None if by_argument else query, stdin=subprocess.DEVNULL if by_argument else None,
                                   capture_output=True, text=True, encoding="utf-8", timeout=config["timeout"], shell=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError(f"command timed out after {config['timeout']} seconds") from exc
    except OSError as exc:
        raise ValueError(f"could not start the command: {type(exc).__name__}") from exc
    if completed.returncode != 0:
        raise ValueError(f"command exited with status {completed.returncode}; see its own logs")
    return parse_triggered(completed.stdout)


def collect(sets, config, selected, split):
    observed = {name: {} for name in sets}
    for name in selected:
        todo = [item for item in sets[name] if split == "all" or item["split"] == split]
        for number, item in enumerate(todo, 1):
            observed[name][item["query"]] = [run_command(config, item["query"]) for _ in range(config["runs"])]
            print(f"{name}: {number}/{len(todo)} queries run", file=sys.stderr, flush=True)
    return observed


def write_new_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def fmt(value):
    return "n/a" if value is None else f"{value:.2f}"


def print_summary(report):
    print(f"Trigger rate threshold {report['threshold']} ({report['threshold_rule']}); "
          f"pass needs pass rate >= {report['min_pass_rate']} on split '{report['verdict_split']}'.")
    for name, entry in report["skills"].items():
        for label, stats in entry["splits"].items():
            print(f"{name:34} {label:10} pass {stats['passed']}/{stats['queries']} ({fmt(stats['pass_rate'])})  "
                  f"precision {fmt(stats['precision'])}  recall {fmt(stats['recall'])}  "
                  f"fp {stats['false_positives']}  fn {stats['false_negatives']}  "
                  f"routed {stats['cross_skill_routed_to_expected']}/{stats['cross_skill_total']}")
        print(f"{name:34} {'RESULT':10} {'PASS' if entry['passed'] else 'FAIL'}")
        for row in entry["queries"]:
            if not row["passed"]:
                kind = "missed trigger" if row["should_trigger"] else "unwanted trigger"
                print(f"    {kind} ({row['split']}, rate {row['trigger_rate']}): {row['query'][:70]}")
    for warning in report["warnings"]:
        print(f"warning: {warning}")
    print(report["scope"])
    print("OVERALL " + ("PASS" if report["passed"] else "FAIL"))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="check the query files; no scoring, no model calls")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    common.add_argument("--min-pass-rate", type=float, default=1.0,
                        help="fraction of queries that must pass for a skill to pass (default 1.0)")
    common.add_argument("--split", choices=VERDICT_SPLITS, default="all")
    common.add_argument("--skill", action="append", default=[], help="limit to this skill (repeatable)")
    common.add_argument("--report", type=Path, help="write a JSON report to this new file")
    score = commands.add_parser("score", parents=[common], help="score a static predictions file; no model or network")
    score.add_argument("--predictions", type=Path, required=True)
    run = commands.add_parser("run", parents=[common], help="run an operator-supplied command per query")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--save-predictions", type=Path, help="also save the collected runs as a predictions file")
    args = parser.parse_args()
    try:
        sets = load_queries()
        if args.command == "validate":
            for name, items in sets.items():
                counts = {c: sum(1 for i in items if i["category"] == c) for c in CATEGORIES}
                print(f"{name}: {len(items)} queries ({counts['positive']} positive, {counts['near-miss']} near-miss, "
                      f"{counts['cross-skill']} cross-skill); train {sum(1 for i in items if i['split'] == 'train')}, "
                      f"validation {sum(1 for i in items if i['split'] == 'validation')}")
            print("Validated trigger queries; no models were run.")
            return 0
        if not 0 < args.threshold < 1 or not 0 <= args.min_pass_rate <= 1:
            parser.error("threshold must be between 0 and 1 (exclusive); min-pass-rate between 0 and 1")
        unknown = set(args.skill) - set(sets)
        if unknown:
            parser.error(f"unknown skills: {sorted(unknown)}")
        selected = [name for name in sets if not args.skill or name in args.skill]
        if args.command == "score":
            observed, metadata = load_predictions(args.predictions, sets, selected, args.split)
            mode = "offline-predictions"
        else:
            config, metadata = load_config(args.config)
            observed = collect(sets, config, selected, args.split)
            mode = "command"
            if args.save_predictions:
                write_new_json(args.save_predictions, {
                    "schema_version": 1, **metadata,
                    "collected": datetime.now(timezone.utc).date().isoformat(),
                    "predictions": [{"skill": name, "query": q, "runs": runs}
                                    for name in selected for q, runs in observed[name].items()]})
        report = build_report(sets, observed, args.threshold, args.min_pass_rate, args.split, mode, metadata, selected)
        if args.report:
            write_new_json(args.report, report)
        print_summary(report)
        return 0 if report["passed"] else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"trigger_eval: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
