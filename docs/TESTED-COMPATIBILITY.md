# Tested compatibility: 2026.10.24.1

Format support and observed behavior are separate claims.

| Layer | Evidence | Limit |
|---|---|---|
| Skill packages | Metadata, local links, notices, hashes and ZIP contents are checked by CI. | The host must support the format and expose the needed capabilities. |
| Python helpers | Windows/Linux, Python 3.10/3.12 CI matrix; regression and integrity tests (145 in this release). Local Windows runs are recorded below. | Passing code tests do not establish legal accuracy. |
| Document templates | All 11 JSON-backed templates were rebuilt on 2026-10-24, rendered in Word 16.0 and viewed by an AI lane, and independently rebuilt, rendered and measured by a second AI reviewer the same day; all 14 Word assets have a byte-bound review record. | A rendered-page check by AI is not an attorney review and does not establish filing readiness. The three assets outside the rebuild keep their inherited review. See TEMPLATE-QA.md. |
| Claude model behavior | No provider trials recorded for this release. | The optional CLI adapter is tested with simulated subprocess responses only. |
| GPT/OpenAI model behavior | No provider trials recorded for this release. | Codex metadata and prompt exports establish integration format, not answer quality. |
| Other LLMs | Portable prompt inputs and manual result import are available. No provider trials recorded. | No universal compatibility or equivalent-performance claim. |

The 24 scenarios prepare 48 paired trials per repetition. None is marked passed
merely because its fixture exists. There is no published model score, legal-accuracy
score, or attorney approval for this release. Current publication provides tested
helpers and evaluation infrastructure, not a completed cross-model benchmark.

## Record of 2026-10-24

- **CI.** The validate workflow (Ubuntu and Windows, each on Python 3.10 and 3.12)
  passed in all four jobs at 327038f on `main` (run 40146193402), the merge of pull
  request 8, and at that pull request's last two commits, e493335 (run 40144698014)
  and edca691 (run 40145939490). Each job ran 145 tests. The version-bump pull
  request's own runs are listed on that pull request.
- **Local Windows runs.** On Windows 11 under CPython 3.12.10 (a virtual environment
  with python-docx 1.2.0 and PyYAML), the four validators (`skill_tools.py`,
  `evaluate.py`, `trigger_eval.py` and `source_registry.py`, each with `validate`)
  exited 0, and the suite ran 145 tests, OK, with 2 skipped. The skipped tests create
  symbolic links, which needs a Windows privilege the account did not hold; the Ubuntu
  jobs run them.
- **Independent reviewer run.** A Codex-model reviewer ran the same five commands on
  Windows 11 under CPython 3.12.14 at 3a705a7 and reported the same validator results
  and 141 tests, OK, 2 skipped (before the four tests added afterwards). It also ran 29
  synthetic citation-check scenarios and 20 memo fixtures; the defects it found are
  fixed in e493335.
- **Release assets.** Before publication the draft release's assets were downloaded and
  all eight SHA-256 values in SHA256SUMS.txt matched the local build from the clean
  checkout at 4d9f296; BUILD.json names that commit with `dirty` and `preview` false.
  After publication, the artifacts of the validate workflow run for the push of 4d9f296
  to `main` (run 40146773285) were downloaded: each of the four matrix jobs (Ubuntu and
  Windows, Python 3.10 and 3.12) produced all nine files byte-identical to the published
  assets. That is an independent rebuild on GitHub's runners. The copy of this file
  inside the release says the check had not been made yet, because the file is itself
  an asset; this repository copy records the result.
- **Models and hosts.** Two trigger-activation runs on 2026-10-24, after publication: the
  60 trigger queries, one run each, in fresh Claude Code desktop (2.1.272) subagents with
  the release's skills installed, once on claude-haiku-5-5 and once on claude-sonnet-5-5.
  No near-miss or cross-skill query triggered the skill under test in either run
  (precision 1.00 for all three skills). Recall on haiku was 0.11, 0.33 and 0.33; on
  sonnet 0.67, 0.89 and 0.89 (cite-check, interpretation, writing). Both fail the
  protocol's every-query rule. One run per query per model, a subagent context: see
  evals/triggers/results/2026-10-24-claude-code-subagents.md. No output-quality or
  legal-accuracy trial was run.

## Record of 2026-10-13

- **CI.** The validate workflow (Ubuntu and Windows, each on Python 3.10 and 3.12)
  passed in all four jobs at each commit merged to `main` for this release: 65d863b
  (run 38417720687), c2c08b9 (run 38417813926), 085bd09 (run 38419216434) and
  c9f04e7 (run 38420064917). At c9f04e7 each job ran 132 tests with no failures and
  no skips. The release pull request's own runs are listed on that pull request.
- **Local Windows runs.** On Windows 11, on the release branch with
  `PYTHONIOENCODING=utf-8`, under CPython 3.12.10 and CPython 3.14.5: the four
  validators (`skill_tools.py`, `evaluate.py`, `trigger_eval.py` and
  `source_registry.py`, each with `validate`) exited 0, and the suite ran 132 tests,
  OK, with 2 skipped. The skipped tests create symbolic links, which needs a Windows
  privilege the account did not hold.
- **Release assets.** Not checked when this record was written. RELEASING.md
  requires the draft release's assets to match the local build by SHA-256 before
  publication; its result is not recorded in this file, which is itself one of the
  assets. No independent byte-for-byte rebuild of these assets is recorded here.
- **Models and hosts.** None run on this release.

Record future model/host versions, capabilities, dates, raw outputs, baseline
comparison, rubric decisions, repetitions, and remaining failures before changing
this table. Do not translate a later finite test pass into a guarantee of error-free
behavior. See [evaluation protocol](../evals/README.md) and
[GitHub validation runs](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/actions/workflows/validate.yml).
