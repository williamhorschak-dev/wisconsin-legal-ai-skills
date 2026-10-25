# Trigger evaluation record: 2026-10-24, Claude Code desktop subagents, claude-haiku-5-5

First recorded run of the 60 trigger queries on a host that logs skill activation. It is
one run per query, not the three the protocol asks for, on one model and one host
configuration. Read it as a first measurement, not as a reliability figure.

## Setup

- Host: Claude Code desktop app 2.1.272 on Windows 11. Each query ran in a fresh
  general-purpose subagent started with the Agent tool; the subagent's transcript records
  every tool call, and a `Skill` tool call naming one of the three skills (or the
  `anthropic-skills:` plugin copy of it, which was also installed on this host) counts as
  that skill being loaded. Installed skills: release 2026.10.24.1.
- Model: claude-haiku-5-5, as recorded in every transcript.
- Prompt wrapper (round 2): "Respond to the following user message as you normally would,
  using whichever of your tools and skills you would normally use for it. Do not run shell
  commands, do not create or edit files, do not browse the web, do not spawn agents. Keep the
  reply under 150 words." followed by the query verbatim. The wrapper names no skill.
- A first round with a wrapper that said "Reply in text only" produced zero skill calls in
  60 runs: the model read it as a ban on all tools, including `Skill`. That round is kept as
  `r1-predictions.json` and `r1-report.json` and is not a measurement of the descriptions.
- Scoring: `python scripts/trigger_eval.py score --predictions r2-predictions.json`, default
  threshold 0.5 and pass rate 1.0.

## Result (round 2, one run per query)

| Skill | Split | Pass | Precision | Recall | False positives | Missed triggers | Cross-skill routed to expected |
|---|---|---|---|---|---|---|---|
| cite-check | all | 12/20 | 1.00 | 0.11 | 0 | 8 | 3/5 |
| wisconsin-legal-interpretation | all | 14/20 | 1.00 | 0.33 | 0 | 6 | 3/5 |
| wisconsin-legal-writing | all | 14/20 | 1.00 | 0.33 | 0 | 6 | 2/5 |

OVERALL FAIL under the protocol's every-query rule. No near-miss or cross-skill query
triggered the skill under test (precision 1.00 for all three). The failures are all missed
triggers: the subagent answered should-trigger queries directly, usually saying it could not
verify sources in a text-only run, instead of loading the skill.

Missed triggers, cite-check (8 of 9 should-trigger queries): Hollis good-law check;
record-index references; Kessler pincite; majority-versus-dissent quotation; table of
authorities audit; Brandt and Pell existence check; Fenwick quote; six-case string cite.
The one hit was the brief with a sources folder.

Missed triggers, interpretation (6 of 9): "shall" in Wisconsin versus federal courts;
small-claims statute as of June 2016; research memo on a 2023 amendment; unpublished
opinion citability; agency deference; Wis. Stat. 227.10(2m) text. Hits: lease versus
statute notice phrases; ordinance "person"; constitution text and history.

Missed triggers, writing (6 of 9): motion-to-compel review by path; caption and signature
block fix; substitution of judge request; letter to the judge; outline to brief; proposed
order from a PDF. Hits: declaration for a client; discovery responses; motion to extend time.

Cross-skill routing that worked: statute-text questions placed in the cite-check set went to
the interpretation skill (3 of 3); citation checks in the interpretation set went to
cite-check (1 of 2); drafting requests in the interpretation set went to the writing skill
(2 of 2); the citation check in the writing set went to cite-check (1 of 2); interpretation
questions in the writing set went to the interpretation skill (1 of 2).

## What this does and does not show

- On this host and model, the descriptions did not cause unwanted activation on any of the
  18 near-miss or 15 cross-skill queries.
- They under-triggered badly on the positive queries, especially for cite-check. Whether the
  cause is the description text, the subagent context (a long tool list and a wrapper that
  forbade browsing and files), or the model, this run cannot say; the same queries have not
  been run against the main session model or through the command-line runner.
- One run per query. The protocol's three runs were not made; a single Haiku run is
  sensitive to sampling.
- Four of the fifteen skill calls went to the `anthropic-skills:` plugin copy of the writing
  skill rather than the installed one. Which copy loads is a host decision; the count treats
  them as the same skill.
- Nothing here measures output quality or legal accuracy.

Files: `r1-predictions.json`, `r1-report.json` (invalid wrapper, kept for the record),
`r2-predictions.json`, `r2-report.json` (this result).
