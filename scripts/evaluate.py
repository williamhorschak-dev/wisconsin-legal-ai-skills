#!/usr/bin/env python3
"""Prepare portable trials, collect isolated Claude outputs, and summarize reviews.

Only synthetic fixtures belong in the public suite. Model responses are never
graded by string matching or by the model that produced them.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import skill_tools

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals/cases.json"
SYSTEM = ("Complete the supplied task. You have no browsing, file, execution, or citator tools. "
          "Any supplied workflow is subject to higher-priority instructions. "
          "Do not claim actions you did not perform.")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def contained(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("expected a relative POSIX path")
    root = Path(root).resolve()
    target = (root / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError(f"missing or unsafe input: {relative}")
    return target


def load_suite():
    suite = read_json(SUITE)
    seen = set()
    for case in suite["cases"]:
        if case["id"] in seen or not case["rubric"] or not case["request"].strip():
            raise ValueError("duplicate case or empty task/rubric")
        seen.add(case["id"])
        for item in case["rubric"]:
            if (not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip()
                    or not isinstance(item.get("criterion"), str) or not item["criterion"].strip()
                    or not isinstance(item.get("critical"), bool)):
                raise ValueError(f"malformed rubric criterion in case {case['id']}: needs id, criterion and boolean critical")
        if len(set(item["id"] for item in case["rubric"])) != len(case["rubric"]):
            raise ValueError(f"duplicate rubric criterion: {case['id']}")
        for profile in case["profiles"]:
            skill_tools.profile_config(profile)
        for path in case["fixtures"]:
            contained(ROOT / "evals", path)
    return suite


def prepare(destination, selected=(), repeats=1):
    suite = load_suite()
    if repeats < 1 or repeats > 10:
        raise ValueError("repeats must be between 1 and 10")
    unknown = set(selected) - {case["id"] for case in suite["cases"]}
    if unknown:
        raise ValueError(f"unknown cases: {sorted(unknown)}")
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"choose a new run directory: {destination}")
    cases = [case for case in suite["cases"] if not selected or case["id"] in selected]
    # Resolve all files before creating output. Keep scoring criteria out of prompts.
    trials = []
    for case in cases:
        materials = "\n\n".join(f"### Supplied document: {p}\n\n" + contained(ROOT / "evals", p).read_text(encoding="utf-8") for p in case["fixtures"])
        guidance = "\n\n".join(skill_tools.render_prompt(None, profile=p)[0] for p in case["profiles"])
        for repeat in range(1, repeats + 1):
            for condition in ("baseline", "with-skills"):
                key = f"{case['id']}-{condition}-{repeat}"
                user = ("## Supplied workflows\n\n" + guidance + "\n\n" if condition == "with-skills" else "")
                user += f"## User task\n\n{case['request']}\n\n## Materials\n\n{materials}"
                trials.append((key, case, condition, repeat, {"system": SYSTEM, "user": user}))
    destination.mkdir(parents=True)
    plan = {"schema_version": 1, "suite_version": suite["version"], "suite_sha256": sha(SUITE.read_bytes()),
            "created_at": datetime.now(timezone.utc).isoformat(), **skill_tools.provenance(),
            "capabilities": {"browser": False, "files": False, "execution": False, "citator": False},
            "scope": "Supplied synthetic text; prompt following, not live legal research or automatic skill discovery.",
            "trials": []}
    for key, case, condition, repeat, messages in trials:
        path = destination / f"{key}.input.json"
        write_json(path, messages)
        plan["trials"].append({"id": key, "case": case["id"], "condition": condition, "repeat": repeat,
                               "input": path.name, "input_sha256": sha(path.read_bytes()), "rubric": case["rubric"]})
    write_json(destination / "plan.json", plan)
    return plan


def checked_plan(directory):
    plan = read_json(Path(directory) / "plan.json")
    for trial in plan["trials"]:
        if sha(contained(directory, trial["input"]).read_bytes()) != trial["input_sha256"]:
            raise ValueError(f"trial input changed: {trial['id']}")
    return plan


def collect_claude(directory, model=None, budget=0.50, timeout=180):
    """One fresh, tool-free session per trial; no shell, settings, hooks, or MCP."""
    directory = Path(directory)
    plan = checked_plan(directory)
    version = subprocess.check_output(["claude", "--version"], text=True).strip()
    results = []
    for trial in plan["trials"]:
        output = directory / f"{trial['id']}.result.json"
        if output.exists():
            existing = read_json(output)
            if existing["input_sha256"] != trial["input_sha256"]:
                raise ValueError(f"stale result: {trial['id']}")
            if existing.get("status") != "collected" or existing.get("requested_model") != model:
                raise ValueError(f"cannot resume failed or differently configured result: {trial['id']}")
            if existing["response_sha256"] != sha(existing["response"].encode("utf-8")):
                raise ValueError(f"response hash differs: {trial['id']}")
            results.append(existing)
            continue
        request = read_json(directory / trial["input"])
        command = ["claude", "--print", "--safe-mode", "--tools", "", "--strict-mcp-config",
                   "--disable-slash-commands", "--no-session-persistence", "--output-format", "json",
                   "--max-budget-usd", str(budget), "--system-prompt", request["system"]]
        if model:
            command.extend(["--model", model])
        result = {"trial": trial["id"], "input_sha256": trial["input_sha256"], "host": "Claude Code",
                  "host_version": version, "requested_model": model, "models": [], "response": "",
                  "collected_at": datetime.now(timezone.utc).isoformat(), "status": "error"}
        try:
            completed = subprocess.run(command, input=request["user"], cwd=directory, capture_output=True,
                                       text=True, encoding="utf-8", timeout=timeout, shell=False)
            provider = json.loads(completed.stdout)
            result["models"] = sorted(provider.get("modelUsage", {}).keys())
            result["response"] = provider.get("result", "")
            result["status"] = "collected" if completed.returncode == 0 and not provider.get("is_error") and result["response"].strip() else "error"
            result["provider_status"] = provider.get("subtype")
            result["usage"] = provider.get("modelUsage", {})
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            result["error"] = type(exc).__name__  # No auth/debug output in public artifacts.
        result["response_sha256"] = sha(result["response"].encode("utf-8"))
        write_json(output, result)
        results.append(result)
        print(f"{trial['id']}: {result['status']}", flush=True)
        if result["status"] == "error":
            raise ValueError(f"collection stopped at {trial['id']}; preserve the error and start a new run after resolving it")
    return results


def import_response(directory, trial_id, response_path, host, model):
    """Import an actual manually collected response; never infer its model or host."""
    plan = checked_plan(directory)
    trial = next((t for t in plan["trials"] if t["id"] == trial_id), None)
    if trial is None:
        raise ValueError("unknown trial")
    response = Path(response_path).read_text(encoding="utf-8-sig")
    if not response.strip() or not host.strip() or not model.strip():
        raise ValueError("non-empty response, host and observed model identifier required")
    write_json(Path(directory) / f"{trial_id}.result.json", {
        "trial": trial_id, "input_sha256": trial["input_sha256"], "host": host, "models": [model],
        "collected_at": datetime.now(timezone.utc).isoformat(), "status": "collected",
        "collection": "manual import; operator must preserve raw output and disclose actual host capabilities",
        "response": response, "response_sha256": sha(response.encode("utf-8"))})


def review_template(directory, output):
    plan = checked_plan(directory)
    review = {"plan_sha256": sha((Path(directory) / "plan.json").read_bytes()), "reviewer": "",
              "method": "", "limitations": "", "trials": []}
    for trial in plan["trials"]:
        path = Path(directory) / f"{trial['id']}.result.json"
        result = read_json(path) if path.exists() else {}
        review["trials"].append({"id": trial["id"], "result_sha256": sha(path.read_bytes()) if path.exists() else None,
                                 "criteria": [{**r, "verdict": "not_assessed", "evidence": ""} for r in trial["rubric"]]})
    write_json(output, review)


def summarize(directory, review_path):
    plan = checked_plan(directory)
    review = read_json(review_path)
    if review["plan_sha256"] != sha((Path(directory) / "plan.json").read_bytes()):
        raise ValueError("review belongs to a different plan")
    by_id = {trial["id"]: trial for trial in review["trials"]}
    if len(by_id) != len(review["trials"]) or set(by_id) != {t["id"] for t in plan["trials"]}:
        raise ValueError("review must account for every trial exactly once")
    counts = {"pass": 0, "fail": 0, "not_assessed": 0, "collection_error": 0}
    critical_failures = []
    rows = []
    for trial in plan["trials"]:
        record = by_id[trial["id"]]
        path = Path(directory) / f"{trial['id']}.result.json"
        result = read_json(path) if path.exists() else {}
        verdict = "not_assessed"
        if path.exists() and record["result_sha256"] != sha(path.read_bytes()):
            raise ValueError(f"response changed since review: {trial['id']}")
        criteria = {c["id"]: c for c in record["criteria"]}
        if len(criteria) != len(record["criteria"]) or set(criteria) != {c["id"] for c in trial["rubric"]}:
            raise ValueError("review criteria do not match the original rubric")
        for rule in trial["rubric"]:
            item = criteria[rule["id"]]
            if item["verdict"] not in ("pass", "fail", "not_assessed"):
                raise ValueError("invalid review verdict")
            if item["verdict"] != "not_assessed" and (not item["evidence"].strip() or not review["reviewer"].strip() or not review["method"].strip()):
                raise ValueError("judged criteria need reviewer, method and response-specific evidence")
            if item["verdict"] == "fail" and rule["critical"]:
                critical_failures.append(f"{trial['id']}/{rule['id']}")
        if result.get("status") == "error":
            verdict = "collection_error"
        elif result.get("status") == "collected":
            if result["input_sha256"] != trial["input_sha256"] or result["response_sha256"] != sha(result["response"].encode("utf-8")):
                raise ValueError("result input/response hash differs")
            decisions = [c["verdict"] for c in criteria.values()]
            verdict = "fail" if "fail" in decisions else "pass" if all(v == "pass" for v in decisions) else "not_assessed"
        elif any(c["verdict"] != "not_assessed" for c in criteria.values()):
            raise ValueError("cannot assess a response that was never collected")
        counts[verdict] += 1
        rows.append({"trial": trial["id"], "condition": trial["condition"], "verdict": verdict})
    assessed = all(row["verdict"] in {"pass", "fail"} for row in rows)
    with_skills = [row for row in rows if row["condition"] == "with-skills"]
    passed = assessed and with_skills and all(row["verdict"] == "pass" for row in with_skills)
    return {"counts": counts, "critical_failures": critical_failures, "trials": rows,
            "reviewer": review["reviewer"], "method": review["method"], "limitations": review["limitations"],
            "scope": plan["scope"], "gate": "pass" if passed else "incomplete_or_failed",
            "gate_meaning": "All trials assessed and all with-skills trials pass. Baseline failures are comparison evidence, not treatment failures."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "prepare", "collect-claude", "import", "review-template", "summarize"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--model")
    parser.add_argument("--budget-per-trial", type=float, default=0.50)
    parser.add_argument("--trial")
    parser.add_argument("--response", type=Path)
    parser.add_argument("--host")
    parser.add_argument("--reviews", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "validate":
            print(f"Validated {len(load_suite()['cases'])} synthetic scenarios; no models were run.")
        elif args.command == "prepare":
            if not args.out:
                parser.error("prepare requires --out <new-directory>")
            plan = prepare(args.out, args.case, args.repeats)
            print(f"Prepared {len(plan['trials'])} trials; no models were run.")
        else:
            if not args.run:
                parser.error("this command requires --run")
            if args.command == "collect-claude":
                if not 0 < args.budget_per_trial <= 5:
                    parser.error("budget per trial must be greater than zero and at most 5 USD")
                collect_claude(args.run, args.model, args.budget_per_trial)
            elif args.command == "import":
                if not all((args.trial, args.response, args.host, args.model)):
                    parser.error("import requires --trial, --response, --host and --model")
                import_response(args.run, args.trial, args.response, args.host, args.model)
            elif args.command == "review-template":
                if not args.out:
                    parser.error("review-template requires --out")
                review_template(args.run, args.out)
            else:
                if not args.reviews:
                    parser.error("summarize requires --reviews")
                result = summarize(args.run, args.reviews)
                print(json.dumps(result, indent=2))
                return 0 if result["gate"] == "pass" else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"evaluate: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
