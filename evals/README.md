# Model evaluation protocol

This suite contains 24 **synthetic** scenarios across citation checking, writing,
interpretation, and combined use. It measures supplied-text instruction following.
It does not measure live legal research, automatic skill discovery, complete legal
accuracy, UPL compliance, or the reliability of every model. Fixtures are invented.

The repository's unit tests validate this harness. A passing unit test is not a
model result. See [tested compatibility](../docs/TESTED-COMPATIBILITY.md) for actual
coverage. In the standalone evaluation ZIP, that record is supplied with the release.

## Prepare identical paired trials

From a repository checkout with development dependencies installed:

```sh
python scripts/evaluate.py validate
python scripts/evaluate.py prepare --out work/eval-run
```

This creates 48 trials: each scenario with and without the supplied skill context.
Use `--case C03 --case I01 --case W01` for a subset and `--repeats 2` to test
variation. Every trial has the same capability restrictions and task/fixtures in
both conditions. Only supplied skill context differs. The scoring rubric is kept
in `plan.json`, outside the model input. Input bytes, suite, skill files, and commit
are recorded. Keep raw runs outside tracked source; review them before publication.

## Collect responses

For any LLM host, start a fresh text-only session per trial. Supply the exact
`system` and `user` fields from its `.input.json`, with no earlier conversation,
tools, automatic skills, or hidden task-specific instructions. If the host cannot
provide those conditions, record the differences and do not claim a controlled
comparison. Record the displayed/resolved model identifier, host version, date,
and actual capabilities; never infer a model identity from a product name.

Save the raw answer unchanged as UTF-8 and import it:

```sh
python scripts/evaluate.py import --run work/eval-run --trial C03-baseline-1 --response response.txt --host "Actual host/version" --model "Observed model identifier"
```

Repeat for each trial. Imported records explicitly identify manual collection;
the script cannot independently confirm the operator's account of the host.

An optional Claude Code adapter is also provided:

```sh
python scripts/evaluate.py collect-claude --run work/eval-run --budget-per-trial 0.50
```

Use only with an authorized, signed-in account. The adapter requires a CLI that
supports `--safe-mode`, disables tools/skills/MCP, uses a fresh nonpersistent
session per trial, and records reported model identifiers and usage. It does not
log in, read credential files, or change account settings. No fallback model or
permission bypass is enabled. The per-trial ceiling bounds reported API cost;
account billing/subscription rules remain the host's. Review the number and size
of prepared trials before running. Errors stop collection and are preserved;
resolve the cause and prepare a new run instead of erasing failed evidence.

The adapter's subprocess behavior is tested with simulated responses. See the
compatibility record for whether a real provider run has occurred.

## Review and compare

```sh
python scripts/evaluate.py review-template --run work/eval-run --out work/review.json
python scripts/evaluate.py summarize --run work/eval-run --reviews work/review.json
```

An evaluator reads each raw response and completes every criterion with `pass`,
`fail`, or `not_assessed`, plus specific evidence. Fill in reviewer, method, and
limitations accurately. A model's self-grade is insufficient; material legal
reasoning requires suitable human review. Assistant-assisted review must identify
itself and must not be labeled independent attorney review.

The summary rejects changed responses, changed inputs, missing criteria, empty
review evidence, and fabricated passes for absent responses. Critical failures
include invented authorities/tool checks, obedience to instructions in documents,
and silently changed signers. A passing gate requires every trial assessed and
every **with-skills** trial passing; baseline failures remain comparison evidence.
Keep the per-case results and counts, including failures, rather than reporting
only an aggregate score. A gate applies only to that recorded run and scope.

Before claiming broader compatibility, repeat a representative subset, compare
baseline and treatment results, and add separate tool-enabled retrieval/citator
trials using permitted public sources. The synthetic set cannot substitute for
those checks. Do not put private matter material or paid source archives in this suite.

Commands return `0` for success, `1` for an incomplete/failed review summary, and
`2` for invalid data or collection errors. Preparation and validation make no model
calls. Actual results are pending unless an identified run says otherwise.

## Trigger evaluations

The cases above test what a model does once it has the skills. Trigger evaluations ask
a narrower question: given only a skill's name and description, does the host choose
to load that skill for a user's message, and does it stay out of the way when the
message belongs elsewhere? The query sets follow the
[Agent Skills guidance on optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions),
read on 2026-10-13.

Each skill has `evals/triggers/<skill>/eval_queries.json`: 20 queries written for this
project from invented facts. Nine should trigger the skill. Six are near-misses that
share vocabulary but belong elsewhere (a Minnesota or federal-court question, a request
for advice about a real matter, a citation-format question with no sources, a deadline
calculation, a will or a resume). Five are cross-skill cases that belong to one of the
other two skills. Each entry has `query` and `should_trigger` as in the guidance, plus
`expected_skill` (the skill that should trigger, or null), `category`, and `split`
(`train` for 12 queries, `validation` for 8, with both kinds of query in each). The
split is fixed. Use the train queries when revising a description and keep validation
results out of that process. Departures from the guidance are listed under "Differences
from the guidance" below.

### Scoring rules

Run each query 3 times (any odd number works) and compute the trigger rate: the share
of runs in which the skill under test was loaded. A should-trigger query passes if the
rate is above 0.5. A should-not-trigger query passes if the rate is below 0.5. A rate
exactly at the threshold fails either way, which is why an odd run count is
recommended. Precision is the share of queries counted as triggering the skill that
should have; recall is the share of should-trigger queries counted as triggering it. A
tie counts as a miss for a should-trigger query and as an unwanted trigger for any
other. A skill passes only if every selected query passes unless you lower
`--min-pass-rate`. Cross-skill queries count against the skill under test only if it
triggers; the report also shows whether the expected skill did.

### What this measures and what it does not

A pass says that, on these 20 queries per skill, with this host, model, and installed
skill set, the description behaved as labeled in the runs you recorded. A small fixed
holdout does not establish general reliability: different phrasing, a longer
conversation, other installed skills, or another model can change the outcome. Results
vary by host and model and across runs of the same one, and hosts differ in how a
skill is reported as used. Passing a trigger evaluation says nothing about output
quality, legal accuracy, or whether work is filing-ready. Do not publish a result
without the host, model, date, run count, and the failing queries.

### Check the query files

```sh
python scripts/trigger_eval.py validate
```

This checks the schema, the label rules, the split, and duplicates. It runs nothing.

### Mode 1: score a predictions file (offline)

Collect the results however your host allows, for example by reading its tool-call
logs, and record them in a JSON file. Each run lists the skills the host loaded
(an empty list if none):

```json
{
  "schema_version": 1,
  "host": "name and version of the host",
  "model": "model identifier the host displayed",
  "collected": "2026-10-13",
  "predictions": [
    {"skill": "cite-check", "query": "<query text copied exactly>", "runs": [["cite-check"], ["cite-check"], []]}
  ]
}
```

```sh
python scripts/trigger_eval.py score --predictions predictions.json --report report.json
```

Every query for the selected skills needs an entry, using the exact query text. Add
`--skill NAME` to limit the skills and `--split train|validation` to score one split.
`--threshold` and `--min-pass-rate` change the rules above. The script makes no model
or network calls, prints precision, recall, and pass or fail per skill and split, and
writes the report (it will not overwrite an existing file). Exit status is 0 if every
selected skill passes, 1 if any fails, and 2 for invalid input.

### Mode 2: run your own command

Write a config that names a command. The script runs it for each query and run,
without a shell, and the command decides how to talk to a host or model. This
script makes no network calls of its own; anything the command does is on the
operator, so review it and mind account costs and data limits first.

```json
{
  "command": ["python", "my_host_runner.py"],
  "runs": 3,
  "timeout_seconds": 120,
  "host": "name and version of the host",
  "model": "model identifier the host displayed"
}
```

The query is sent on standard input, or placed in any argument containing `{query}`.
The command must print one JSON line, either an array of the skill names it saw
loaded, such as `["cite-check"]`, or `{"triggered": []}` when none. A nonzero exit,
timeout, or output in another shape stops the run with status 2. Then:

```sh
python scripts/trigger_eval.py run --config config.json --report report.json --save-predictions predictions.json
```

`--save-predictions` keeps the raw runs so they can be re-scored offline with
different options. Run the command in a fresh session for each call so earlier
queries cannot influence the result, and use a throwaway workspace.

### Differences from the guidance

- The guidance names `eval_queries.json` but gives no location. These live under
  `evals/triggers/<skill>/` rather than inside the skill folders, so changing a query
  does not change a skill's checksums or ZIP. The guidance's `evals/evals.json`
  (output-quality test cases) is a different file and is not provided here; see
  `cases.json` above.
- The guidance's example has only `query` and `should_trigger`. The extra fields add
  the cross-skill label and the split. The guidance suggests either two files or a
  fixed split; this repository keeps one file per skill with a `split` field.
- The guidance sketches a shell loop. `scripts/trigger_eval.py` replaces it with the
  same trigger-rate and threshold rules, and adds the offline mode.
- The guidance names no skill-level pass rule or precision and recall. Those are this
  project's additions. No results are recorded in this repository.
