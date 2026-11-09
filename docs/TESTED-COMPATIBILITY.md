# Tested compatibility: 2026.11.08.1

Format support and observed behavior are separate claims.

| Layer | Evidence | Limit |
|---|---|---|
| Skill packages | Metadata, local links, notices, hashes and ZIP contents are checked by CI. | The host must support the format and expose the needed capabilities. |
| Python helpers | Windows/Linux, Python 3.10/3.12 CI matrix; regression and integrity tests (182 in this release). Local Windows runs are recorded below. | Passing code tests do not establish legal accuracy. |
| Document templates | All 11 JSON-backed templates were rebuilt on 2026-11-07 after the page-1 clearance spacer was given an exact height; Word 16.0 and its exported PDF place page 1 body text at 2.00 in (3.00 in for the proposed order) and later pages at 0.95 in; page counts unchanged; page 1 of two templates viewed by an AI agent. On 2026-11-08 a second AI reviewer rendered two of them with LibreOffice 26.8.2.2 and measured first glyph boxes at 2.03 in, 3.03 in and 0.98 in, a constant offset from Word's line positions, no clipping. The 2026-10-24 rebuild was independently rendered and measured by a second AI reviewer. All 14 Word assets have a byte-bound review record. | A rendered-page check by AI is not an attorney review and does not establish filing readiness. The three assets outside the rebuild keep their inherited review. See TEMPLATE-QA.md. |
| Claude model behavior | No provider trials recorded for this release. | The optional CLI adapter is tested with simulated subprocess responses only. |
| GPT/OpenAI model behavior | No provider trials recorded for this release. | Codex metadata and prompt exports establish integration format, not answer quality. |
| Other LLMs | Portable prompt inputs and manual result import are available. No provider trials recorded. | No universal compatibility or equivalent-performance claim. |

The 24 scenarios prepare 48 paired trials per repetition. None is marked passed
merely because its fixture exists. There is no published model score, legal-accuracy
score, or attorney approval for this release. Current publication provides tested
helpers and evaluation infrastructure, not a completed cross-model benchmark.

## Record of 2026-11-08 (release 2026.11.08.1)

- **CI.** The validate workflow (Ubuntu and Windows, each on Python 3.10 and 3.12)
  passed in all four jobs at 07d4396 on `main` (run 42541808087), the last change merged
  before this release's pull request, and on each of the four pull requests merged that day
  (18, 19, 20 and 21). Each job ran 182 tests. The release pull request's own runs are listed
  on that pull request.
- **Local Windows run.** On Windows 11 under CPython 3.14.5 (the system interpreter, not the
  3.12 virtual environment of the earlier records), the four validators exited 0 and the suite
  ran 182 tests, OK, with 2 skipped (symbolic links), on the release branch.
- **Document templates.** Not rebuilt; the 2026.11.07.1 bytes are unchanged. On 2026-11-08 a
  second AI reviewer converted 01-motion.docx and 06-proposed-order.docx to PDF with
  LibreOffice 26.8.2.2 (writer_pdf_Export) and measured the first glyph box from the top edge
  with PyMuPDF: 2.034 in on page 1 of the motion, 0.984 in on its page 2, 3.034 in on page 1
  of the proposed order; Century Schoolbook embedded as subsets; page counts 2 and 1; no
  clipping. The 0.034 in difference from Word's 2.00, 0.95 and 3.00 in is the glyph box
  sitting below the line top that Word reports, not a layout change. The remaining twelve
  templates were not rendered outside Word.
- **Source checker.** The rebuilt checker was run once by hand against the real register on
  2026-11-08 before its pull request merged: 21 requests (18 URLs, two robots files, one
  same-host redirect hop) in 86 seconds, no retries, all ten PDF responses accepted by the
  integrity checks, exit 1 from seven changed currency lines (the statutes republication of
  11-4-26), which the register refresh then recorded. The monthly workflow has not yet run on
  the new code.
- **Release assets.** The draft release's nine assets were downloaded before publication and
  every SHA-256 matched the local build from the clean checkout at fd525a8; BUILD.json names
  that commit with `dirty` and `preview` false. The maintainer published on 2026-11-09 00:59 UTC
  (2026-11-08 local). The artifacts of the validate run for the push of fd525a8 to `main`
  (run 42542908238) were then downloaded: the four matrix jobs produced nine files byte-identical
  to one another, but the five ZIPs and SHA256SUMS.txt differed from the published ones, because
  the local build had run under CPython 3.14.5 and its compression library packs differently;
  every ZIP member name, member bytes and date were identical. A rebuild from the same checkout
  under CPython 3.12.10 was byte-identical to all four CI artifact sets, and within the hour the
  maintainer had those six files replace the published ones. The public assets, the 3.12 build and
  the CI artifacts now match byte for byte, and SHA256SUMS.txt verifies against the downloads. The
  copy of this file inside the release says the check had not been made yet, because the file is
  itself an asset; this repository copy records the result.
- **Models and hosts.** No new trial. The 2026-10-24 trigger-activation record stands.

## Record of 2026-11-07 (release 2026.11.07.1)

- **CI.** The validate workflow (Ubuntu and Windows, each on Python 3.10 and 3.12)
  passed in all four jobs at f5fb4ff on `main` (run 40151236293), the last change merged
  before this release's pull request. Each job ran 145 tests. The release pull request's
  own runs are listed on that pull request.
- **Local Windows run.** On Windows 11 under CPython 3.12.10 (the same virtual
  environment as the previous records), the four validators exited 0 and the suite ran
  145 tests, OK, with 2 skipped (symbolic links), on the release branch.
- **Document templates.** Rebuilt with make_templates.py after the builder change; only
  word/header1.xml differs from the 2026.10.24.2 bytes in each of the 11 files. Microsoft
  Word 16.0 reports page 1 body text at 2.00 in from the top edge, 3.00 in for the
  proposed order (the line-break spacer gave 2.31 in and 3.51 in), and later pages at
  0.95 in; page counts unchanged. The Word-exported PDFs of four templates, read with
  PyMuPDF, give the same first-text positions. Page 1 of the proposed order and of the
  motion was viewed by an AI agent. No renderer other than Word was run.
- **Release assets.** Before publication the draft release's assets were downloaded and
  all eight SHA-256 values in SHA256SUMS.txt matched the local build from the clean
  checkout at a58f32e, with SHA256SUMS.txt itself identical; BUILD.json names that commit
  with `dirty` and `preview` false. The artifacts of the validate workflow run for the
  push of a58f32e to `main` (run 42440778709) were downloaded: each of the four matrix
  jobs (Ubuntu and Windows, Python 3.10 and 3.12) produced all nine files byte-identical
  to the release assets. The release was published on 2026-11-08 after the maintainer's
  go-ahead. The copy of this file inside the release says the check had not been made yet,
  because the file is itself an asset; this repository copy records the result.
- **Models and hosts.** No new trial. The 2026-10-24 trigger-activation record stands.

## Record of 2026-10-24 (release 2026.10.24.2)

- **CI.** The validate workflow (Ubuntu and Windows, each on Python 3.10 and 3.12)
  passed in all four jobs at e917cd0 on `main` (run 40149240755), the last change merged
  before this release's pull request. Each job ran 145 tests. The release pull request's
  own runs are listed on that pull request.
- **Local Windows run.** On Windows 11 under CPython 3.12.10 (the same virtual
  environment as the previous record), the four validators exited 0 and the suite ran 145
  tests, OK, with 2 skipped (symbolic links), on the release branch.
- **Release assets.** Before publication the draft release's assets were downloaded and
  all eight SHA-256 values in SHA256SUMS.txt matched the local build from the clean
  checkout at 07ef342, with SHA256SUMS.txt itself identical; BUILD.json names that commit
  with `dirty` and `preview` false. After publication, the artifacts of the validate
  workflow run for the push of 07ef342 to `main` (run 40150567840) were downloaded: each
  of the four matrix jobs (Ubuntu and Windows, Python 3.10 and 3.12) produced all nine
  files byte-identical to the published assets. The copy of this file inside the release
  says the check had not been made yet, because the file is itself an asset; this
  repository copy records the result.
- **Models and hosts.** Trigger-activation rounds 4 to 6 on 2026-10-24, on the same host
  and wrapper as rounds 2 and 3, all on claude-sonnet-5-5. Round 4 repeated the five
  round-3 misses three times each: the three cite-check misses stayed missed (1 hit in 9
  runs), the interpretation miss hit in 2 of 3, the writing miss in 0 of 3. Round 5 ran
  the cite-check and interpretation sets with two candidate descriptions installed: the
  interpretation set passed 20 of 20 (recall 1.00, precision 1.00); cite-check recall was
  0.44 with zero unwanted triggers. Round 6 ran the cite-check set with a second
  candidate: recall 0.33, zero unwanted triggers. The interpretation sentence ships in this
  release; both cite-check candidates were rejected and that description is unchanged.
  One run per query in rounds 5 and 6, three in round 4; a subagent context on one host;
  see evals/triggers/results/2026-10-24-claude-code-subagents.md. No output-quality or
  legal-accuracy trial was run.

## Record of 2026-10-24 (release 2026.10.24.1)

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
