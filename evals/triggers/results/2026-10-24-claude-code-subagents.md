# Trigger evaluation record: 2026-10-24, Claude Code desktop subagents, haiku and sonnet

First recorded runs of the 60 trigger queries on a host that logs skill activation: one run
per query on claude-haiku-5-5 (round 2) and one on claude-sonnet-5-5 (round 3), same
wrapper, same host configuration. Not the three runs the protocol asks for. Read them as
first measurements, not as reliability figures.

## Setup

- Host: Claude Code desktop app 2.1.272 on Windows 11. Each query ran in a fresh
  general-purpose subagent started with the Agent tool; the subagent's transcript records
  every tool call, and a `Skill` tool call naming one of the three skills (or the
  `anthropic-skills:` plugin copy of it, which was also installed on this host) counts as
  that skill being loaded. Installed skills: release 2026.10.24.1.
- Models: claude-haiku-5-5 (round 2) and claude-sonnet-5-5 (round 3), as recorded in every transcript.
- Prompt wrapper (round 2): "Respond to the following user message as you normally would,
  using whichever of your tools and skills you would normally use for it. Do not run shell
  commands, do not create or edit files, do not browse the web, do not spawn agents. Keep the
  reply under 150 words." followed by the query verbatim. The wrapper names no skill.
- A first round with a wrapper that said "Reply in text only" produced zero skill calls in
  60 runs: the model read it as a ban on all tools, including `Skill`. That round is kept as
  `r1-predictions.json` and `r1-report.json` and is not a measurement of the descriptions.
- Scoring: `python scripts/trigger_eval.py score --predictions r2-predictions.json`, default
  threshold 0.5 and pass rate 1.0.

## Result, round 2 (claude-haiku-5-5, one run per query)

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

## Result, round 3 (claude-sonnet-5-5, one run per query, same wrapper)

| Skill | Split | Pass | Precision | Recall | False positives | Missed triggers | Cross-skill routed to expected |
|---|---|---|---|---|---|---|---|
| cite-check | all | 17/20 | 1.00 | 0.67 | 0 | 3 | 4/5 |
| wisconsin-legal-interpretation | all | 19/20 | 1.00 | 0.89 | 0 | 1 | 5/5 |
| wisconsin-legal-writing | all | 19/20 | 1.00 | 0.89 | 0 | 1 | 4/5 |

OVERALL FAIL under the every-query rule, by five missed triggers. Again no near-miss or
cross-skill query triggered the skill under test. 36 skill calls in 60 runs, every one on a
query where a repository skill belonged; 13 of 15 cross-skill queries went to the expected
skill (the two exceptions went to no skill).

Missed triggers, round 3: cite-check on the record-index references, the Kessler pincite
and the six-case string cite; interpretation on the unpublished-opinion citability
question; writing on the short letter to the judge. Every other should-trigger query loaded
its skill.

Nine of the thirty-six calls went to the `anthropic-skills:` plugin copy of the writing skill.

## What this does and does not show

- On this host, with either model, the descriptions did not cause unwanted activation on
  any of the 18 near-miss or 15 cross-skill queries (120 runs, zero false positives).
- Recall depends heavily on the model. Haiku loaded the right skill for 7 of 27
  should-trigger queries; Sonnet for 22 of 27 with the same wrapper and the same
  descriptions. The remaining Sonnet misses cluster on short, informal citation requests
  and on one letter-drafting request.
- One run per query per model. The protocol's three runs were not made; single runs are
  sensitive to sampling, and the main session model and the command-line runner have not
  been exercised.
- Some skill calls went to the `anthropic-skills:` plugin copy of the writing skill rather
  than the installed one (4 of 15 in round 2, 9 of 36 in round 3). Which copy loads is a
  host decision; the count treats them as the same skill.
- Nothing here measures output quality or legal accuracy.

Files: `r1-predictions.json`, `r1-report.json` (invalid wrapper, kept for the record),
`r2-predictions.json`, `r2-report.json` (haiku), `r3-predictions.json`, `r3-report.json` (sonnet).
