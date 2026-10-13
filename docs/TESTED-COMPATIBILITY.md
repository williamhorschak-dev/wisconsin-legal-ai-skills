# Tested compatibility: 2026.10.13.1

Format support and observed behavior are separate claims.

| Layer | Evidence | Limit |
|---|---|---|
| Skill packages | Metadata, local links, notices, hashes and ZIP contents are checked by CI. | The host must support the format and expose the needed capabilities. |
| Python helpers | Windows/Linux, Python 3.10/3.12 CI matrix; regression and integrity tests (132 in this release). Local Windows runs on CPython 3.12.10 and 3.14.5 are recorded below. | Passing code tests do not establish legal accuracy. |
| Document templates | All 11 JSON-backed templates are rebuilt; all 14 Word assets have a byte-bound review record. | Structural/text checks do not render pages. The existing visual review is inherited; the appendix certification in `10-appellate-brief.docx` was edited as text on 2026-10-13 and not rendered. See TEMPLATE-QA.md. |
| Claude model behavior | No provider trials recorded for this release. | The optional CLI adapter is tested with simulated subprocess responses only. |
| GPT/OpenAI model behavior | No provider trials recorded for this release. | Codex metadata and prompt exports establish integration format, not answer quality. |
| Other LLMs | Portable prompt inputs and manual result import are available. No provider trials recorded. | No universal compatibility or equivalent-performance claim. |

The 24 scenarios prepare 48 paired trials per repetition. None is marked passed
merely because its fixture exists. There is no published model score, legal-accuracy
score, or attorney approval for this release. Current publication provides tested
helpers and evaluation infrastructure, not a completed cross-model benchmark.

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
