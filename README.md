# Wisconsin Legal AI Skills

[![Validate skills](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/github/license/williamhorschak-dev/wisconsin-legal-ai-skills)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/williamhorschak-dev/wisconsin-legal-ai-skills?sort=date)](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/releases/latest)

> **General information and software tools; no legal services.** William Horschak
> is **not a licensed attorney**. This project does not provide legal advice or
> representation from the maintainer. Using it or contacting him about it does not
> by itself create an attorney-client relationship. Do not submit confidential or
> case-specific information in public issues or pull requests.
> Read the [legal notice and support boundaries](LEGAL_NOTICE.md).

Support here is limited to software use, reproducible defects, general
documentation corrections, and feature suggestions. The maintainer does not choose
claims or remedies, calculate your deadlines, review your filings, or advise you
whether to file, settle, or appeal. Ask a lawyer licensed in the relevant place.

## What this is

Three skills for AI assistants that work on Wisconsin court matters, plus five
prompt exports for chat applications. A skill is a folder with a `SKILL.md`
file (the Agent Skills format), reference files, and in some cases small Python
tools and Word templates.

The skills are instructions and helper tools. They do not contain a legal
database, do not look anything up by themselves, and do not run a citator such as
KeyCite or Shepard's. Your assistant and its tools have to supply source access.

**Audience.** The references are written around a self-represented civil litigant
in La Crosse and Trempealeau Counties, which they call a default in places, and
include a paralegal memo convention. Attorneys and paralegals may also use the
verification tools. Check the rules of your own county and judge.

**Not for** advice on your own case, deadline calculations you will rely on,
or deciding that a document is ready to file. A passing test, lint, or build
never establishes that.

## The three skills

- **Citation check:** [cite-check](skills/cite-check/SKILL.md) checks citations,
  quotations, pincites, and the propositions they support against sources the session
  can read.
- **Wisconsin filings:** [wisconsin-legal-writing](skills/wisconsin-legal-writing/SKILL.md)
  drafts and reviews Wisconsin circuit court and Court of Appeals papers.
- **Wisconsin statutory interpretation:**
  [wisconsin-legal-interpretation](skills/wisconsin-legal-interpretation/SKILL.md) looks up
  what a Wisconsin provision said on a given date and analyzes contested readings under
  Wisconsin's own method.

| Skill | Use it to | It does not | Bundled tools |
|---|---|---|---|
| [cite-check](skills/cite-check/SKILL.md) | Check that citations, quotations, pincites, and the propositions they support match sources you or the assistant can read. | Run a citator. Treat a failed search as proof a case does not exist. | `cite_check.py`: an evidence log tied to SHA-256 hashes of the draft and sources, a text-quotation matcher, and a report generator. Python 3.10 and 3.12 tested in CI; 3.14.5 run in the 2026-10-11 assessment and again on 2026-10-13; other versions untested. Standard library only. |
| [wisconsin-legal-writing](skills/wisconsin-legal-writing/SKILL.md) | Draft or review Wisconsin circuit court and Court of Appeals papers: motions, briefs, discovery responses, declarations, proposed orders, letters, research memos. | File, serve, sign, or confirm a paper meets today's rules. The builder makes circuit-court captions only. | `build_filing.py` (DOCX from a JSON spec), 11 JSON specifications, 14 Word templates. Python 3.10 and 3.12 tested in CI; 3.14.5 run in the 2026-10-11 assessment and again on 2026-10-13; other versions untested. Needs `python-docx`. |
| [wisconsin-legal-interpretation](skills/wisconsin-legal-interpretation/SKILL.md) | Look up what a Wisconsin provision said on a given date, analyze a contested reading with Wisconsin's own method, or produce a formal research memo. | Compute deadlines. Retrieve law without source access. | `check_memo.py`: a structural linter for formal memos, and a memo template. Python 3.10 and 3.12 tested in CI; 3.14.5 run in the 2026-10-11 assessment and again on 2026-10-13; other versions untested. Standard library only. |

## Set up

Everything below was run on Windows with the files from release
`v2026.09.20.2` unless the text says otherwise. Hosts differ; see "What has and has
not been tested".

**1. Download.** From the [latest release](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/releases/latest),
put `SHA256SUMS.txt` and the files you want in a new empty folder.

| File | Use |
|---|---|
| `cite-check.zip`, `wisconsin-legal-writing.zip`, `wisconsin-legal-interpretation.zip` | One skill each. For Claude Code, Codex, and other Agent Skills hosts. |
| `prompt-packs.zip` | Five prompt files for chat applications. |
| `evaluation-suite.zip` | 24 synthetic test scenarios, for people who want to test a model themselves. |
| `BUILD.json`, `RELEASE-NOTES.md`, `TESTED-COMPATIBILITY.md` | Build record, release notes, and the testing record. |

**2. Check the download.** Windows PowerShell, in the folder with the files:

```powershell
Get-Content SHA256SUMS.txt | ForEach-Object {
  $hash, $name = $_ -split '\s+', 2
  if (Test-Path $name) {
    $ok = (Get-FileHash $name -Algorithm SHA256).Hash.ToLower() -eq $hash
    "{0}  {1}" -f ($(if ($ok) {'OK'} else {'MISMATCH'})), $name
  }
}
```

macOS or Linux: `sha256sum -c SHA256SUMS.txt` (it expects every listed file to be in the folder).
A checksum shows the file matches the published one. It does not show the content is correct.

**3. Install a skill.** Extract the ZIP into your host's skills folder. Each ZIP
has one top-level folder, so extract into the skills folder itself.

| Host | Project folder | Personal folder |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.agents/skills/` |

Windows PowerShell, from your project folder (replace the path to the ZIPs):

```powershell
New-Item -ItemType Directory -Force .claude\skills | Out-Null
Expand-Archive C:\path\to\cite-check.zip -DestinationPath .claude\skills
Expand-Archive C:\path\to\wisconsin-legal-writing.zip -DestinationPath .claude\skills
Expand-Archive C:\path\to\wisconsin-legal-interpretation.zip -DestinationPath .claude\skills
```

macOS or Linux: `mkdir -p .claude/skills && unzip /path/to/cite-check.zip -d .claude/skills`.
(`unzip` was run on Windows Git Bash for `cite-check.zip` only. Use `.agents/skills`
for Codex.)

`Expand-Archive` stops with an error if the skill folder already exists, which
protects your edits. Adding `-Force` overwrites local changes without warning.

**4. Check the installed skill.** Each skill folder carries `MANIFEST.sha256`.
From inside one skill folder, `sha256sum -c MANIFEST.sha256` works, or in PowerShell:

```powershell
Get-Content MANIFEST.sha256 | ForEach-Object {
  $hash, $path = $_ -split '  ', 2
  if ((Get-FileHash $path -Algorithm SHA256).Hash.ToLower() -ne $hash) { "MISMATCH $path" }
}
```

No output means every file matches. The repository's own `scripts/skill_tools.py` and
`tests/` are not in the ZIPs, so the commands in "For maintainers" below do not
run in an installed copy.

**5. Use it.** Ask for the task in plain words, or name the skill: `/cite-check`
in Claude Code, `$cite-check` in Codex. The project has not recorded a test that
either host finds and starts the skill; the folder layout follows each product's
documentation as of 2026-09-20.

Other hosts:

- **Claude web or desktop upload:** use one skill ZIP with your account's skill upload.
  Not tested by this project.
- **ChatGPT or another chat application:** open `prompt-packs.zip` and give the model
  one profile file plus your task. `citation-audit.md` checks citations in a draft you
  supply; `draft-review.md` reviews or edits a Wisconsin filing; `interpretation-lookup.md`
  answers what a provision says; `interpretation-analysis.md` handles a contested
  reading; `formal-memo.md` produces a full memo. The files are about 49,000 to
  147,000 characters, and some products limit instruction or upload size; that has not
  been tested. If the host has no file access or Python execution, the bundled scripts cannot
  run, so checks that need a script should be reported as not run.

**6. Build a Word template (writing skill).** Needs Python and `python-docx`:

```sh
python -m pip install -r .claude/skills/wisconsin-legal-writing/requirements.txt
python .claude/skills/wisconsin-legal-writing/scripts/build_filing.py .claude/skills/wisconsin-legal-writing/assets/01-motion.json --draft -o motion-draft.docx
```

Use `.agents/skills` in place of `.claude/skills` for Codex. `--draft` allows
unfilled placeholders; without it the builder refuses bracketed text and runs of
underscores. It will not overwrite an existing file unless you add `--overwrite`.
Python 3.10 and 3.12 are what CI tests. Python 3.14.5 ran these tools in a
2026-10-11 check, with a deprecation warning from `cite_check.py` that this release
removes, and ran the test suite again on 2026-10-13; later versions are not part of CI.

## Try one example

These are the repository's own invented examples. Nothing in them is Wisconsin law.
The "expected shape" is taken from each skill's completed example file; it is what a
good answer looks like, not a recorded model run.

**cite-check.** Say:

> Use cite-check. Check the quotation and proposition against the supplied page.
> No browser, citator, file archive, or Python is available.
> Draft: Fictional Workshop Rule 4 says, "A signed request may be accepted."
> Therefore every signed request must be accepted.
> Page: Fictional Workshop Rule 4: "A signed request may be accepted." This rule
> governs only the fictional workshop exercise.

Expected shape: the quotation matches; the proposition does not, because permission
to accept is not a duty to accept every request; a supported replacement sentence;
a plain statement that authenticity, version, and later treatment were not checked
and that no citator ran. See [the full example](skills/cite-check/references/synthetic-example.md).

**wisconsin-legal-writing.** Say:

> Use wisconsin-legal-writing. Add paragraph breaks only. Preserve every word and the
> signer. Do not research or revise substance. Text: "I request a copy of the attached
> schedule. The copy will help me check the dates. Alex Example, self-represented."

Expected shape: the same three sentences on separate lines, the signer line unchanged,
and a note that no legal review, source check, or signing happened. See
[the full example](skills/wisconsin-legal-writing/references/synthetic-example.md).
To see the template builder work, run step 6 above and open `motion-draft.docx`;
you will find a captioned motion filled with placeholders and example text.

**wisconsin-legal-interpretation.** Say:

> Use wisconsin-legal-interpretation. What did Fictional Workshop Rule 2 say on March 1,
> 2022? A short lookup is enough. Use only these versions. Version A, effective
> January 1, 2021 through December 31, 2022: "Members may request a paper copy."
> Version B, effective January 1, 2023: "Members may request an electronic copy."

Expected shape: a quick lookup, not a memo; Version A identified as operative for that
date and quoted; the source named as the supplied text, not independently retrieved.
See [the full example](skills/wisconsin-legal-interpretation/references/synthetic-example.md).

## What has and has not been tested

| Claim | Status |
|---|---|
| The skill packages pass the repository's checks (metadata, links, legal notice, checksums) | Run by CI on every push to `main`. |
| The Python tools have a regression test suite | 145 tests. CI ran all 145 on Ubuntu and Windows with Python 3.10 and 3.12 at commit 327038f (run 40146193402), the last change merged before the version bump for this release. |
| Release files can be rebuilt from the tagged commit | For release 2026.10.24.1, each of the four CI jobs (Ubuntu and Windows, Python 3.10 and 3.12; run 40146773285 at the tagged commit) produced assets byte-identical to the published ones, checked 2026-10-24. For release 2026.09.20.2, a rebuild on CPython 3.12 on 2026-10-11 matched every published asset byte for byte; a rebuild on 3.14 had identical contents but different ZIP bytes, because the compression library differs. No independent rebuild of release 2026.10.13.1 was recorded. |
| Word templates build and render | The 11 JSON-backed templates rebuild in tests. On 2026-10-24 all 11 were rebuilt with a corrected later-page margin, rendered in Word 16.0 and viewed by an AI lane, and independently rebuilt, rendered and measured by a second AI reviewer. No attorney reviewed them. See [TEMPLATE-QA.md](docs/TEMPLATE-QA.md). |
| Any model follows these skills | **No trial recorded by the project.** As of 2026-10-12, the project's release record (see below) lists no model or host trial. The 24-scenario [evaluation suite](evals/README.md) and its harness have no recorded results. A separate exploratory evaluation is summarized after this table; it is not a certification. |
| Claude Code, Codex, Claude upload, or ChatGPT find and use the skills | **One run recorded, 2026-10-24.** Claude Code desktop subagents on claude-haiku-5-5, 60 trigger queries, one run each: no unwanted activation on any near-miss or cross-skill query, but the skills loaded for only 1 of 9, 3 of 9 and 3 of 9 should-trigger queries. See [the record](evals/triggers/results/2026-10-24-claude-code-haiku-subagents.md). Codex, Claude upload and ChatGPT: not tested; layouts follow vendor documentation. |
| The legal statements are correct and current | **Not established.** There has been no attorney review. See "Keeping it current". |

The full record is in [TESTED-COMPATIBILITY.md](docs/TESTED-COMPATIBILITY.md).

**Exploratory model evaluation, 2026-10-11 (repetition 1 only).** An AI-assisted
assessment ran 12 fresh test cases, built on Wisconsin law or synthetic fixtures, that are not in
the repository's 24-scenario suite. Each was answered by a new Claude Code session
reporting the model `claude-sonnet-5-5`, once with no skill (A) and once with the text of release
2026.09.20.2 supplied in the prompt (B). Two AI scorers, the second added on 2026-10-12,
each rated all 24 responses from 0 to 3 for task completion against sealed expected answers
without seeing the other's scores. They gave the same primary score to 23 of the 24 responses.
The pooled mean was 2.04 without the skill and 2.58 with it; B scored higher in 6 cases,
equal in 6, and lower in none, and neither scorer recorded a material legal error, an
invented authority or check, or a failure to resist an injected instruction in either
condition. The protocol's improvement verdict is provisional because the second repetition
was not run, and one response that the scorers rated 2 points apart on a secondary
dimension has not been reconciled. The limits are large: one repetition, one model, AI
scorers only, no attorney review, isolation and tool limits enforced by instruction rather
than by the host, and the skill text pasted in rather than installed, so the result says
nothing about whether any host finds or starts a skill, or about the bundled scripts. Both
scorers identified the condition of all 24 responses, so the scoring was effectively
unblinded. Read it as an exploratory measurement of task completion, not as evidence that
the legal content is correct. It was run on release 2026.09.20.2, not on this release.

## Known limits of the bundled tools (release 2026.10.24.1)

These describe the files in release 2026.10.24.1. Defects of release 2026.10.13.1
corrected in it, all found by a third independent AI review: a verbatim pass recorded by
hand or through the record command was not checked against the cited locator; a
remembered source could pass checks other than verbatim; an exact match in a version not
in force passed without warning; mistyped locator markers silently turned a marked file
into a whole-file comparison; the memo linter exempted live `[UNVERIFIED]` markers beside
marker prose and let a section after the Red Team Report inherit its no-pincite exemption;
pages 2 and later of built documents had a 0.5 inch top margin; and the page-1 stamp
clearance could be switched off.

- The evidence log is an ordinary file. The tool detects a changed draft or source. It
  does not detect log lines that were deleted or written by hand. `RECORDED PASS` means
  a reviewer entered passing records; it is not an independent certification.
- The builder's non-draft check catches bracketed text and runs of underscores. It does
  not catch `TBD`, `XXXX`, `<DATE>`, or `{...}`.
- In two templates a section symbol can be separated from its number by a line break,
  and the appellate template's top margin differs from the margin table in `appellate.md`.
- The subsequent history of cited authorities was not checked exhaustively against public
  sources where only the original opinion was read.
- Two items in the procedure references remain marked [VERIFY]: how 2025 Wis. Act 105
  applies to a claim made before January 1, 2027 in an action commenced after it, and the
  signing date of the 2025 La Crosse County local rules.
- Version detection in the citation tool is phrase matching on the reviewer's own
  annotation; it has no model of which text is in force on a given date.

## Keeping it current

Wisconsin law changes by Act, court order, and decision. Statements stored in the
reference files carry the date they were checked and can be out of date. The
[source register](docs/legal-sources.json) lists eleven topics, what was checked, and
when; six records are inherited from an earlier review and three are pending, and it does
not yet cover every chapter the skills discuss or watch for enacted changes with later
effective dates.

An AI-assisted accuracy check of the stored legal references on 2026-10-11 (not a legal
review and not by an attorney) found stored statements that needed correction, including
judicial substitution timing and public-records remedy subsections. Release 2026.10.13.1
contains the corrections, and release 2026.10.24.1 adds reporter citations and a restored
local-rule attribution found by a third review. AI reviewers checked them against public
sources; no attorney has reviewed them. Each one is listed with its source in
[LEGAL-TEXT-CHANGES-2026-10.md](docs/LEGAL-TEXT-CHANGES-2026-10.md). The check also
found that the Wisconsin Supreme Court had accepted review of whether to modify the
*Kalal* interpretive framework in *Abby Windows, LLC v. Labor & Industry Review
Commission*, No. 2024AP1013, and that the case is scheduled
for oral argument on November 10, 2026. Monetary limits in the references, including the
small-claims limit, are affected by 2025 Wis. Act 105, which takes effect on
January 1, 2027 (Act section 5). The small-claims passage now carries a dated note about
it. Do not rely on any amount, deadline, or rule in a reference file without
reading the current primary text and its effective-date note.

## Contribute

Issues are welcome for reproducible software defects, general documentation
corrections, and feature suggestions. Use fictional names and synthetic data. For a
correction to a general legal reference, name the passage and link the official public
source. Do not post case files, personal details, privileged material, or financial
records, and do not ask for advice about a matter. See
[CONTRIBUTING.md](CONTRIBUTING.md). Security reports go through GitHub's private vulnerability reporting under the Security tab (confirmed enabled 2026-10-13); see [SECURITY.md](SECURITY.md).

## For maintainers

From a clone of this repository (these files are not in the skill ZIPs):

```sh
python -m pip install -r requirements-dev.txt
python scripts/skill_tools.py validate
python -m unittest discover -s tests -v
python scripts/skill_tools.py package --out dist/skills
```

Choose a new package output directory. After reviewed changes to a skill, refresh
manifests with `python scripts/skill_tools.py manifest`. The queries in `evals/triggers/`
and `scripts/trigger_eval.py` test whether each skill's description triggers, as
described in [evals/README.md](evals/README.md), and no trigger results have been
recorded. A small fixed query set does not show that a skill triggers reliably on any
host or model. See [AGENTS.md](AGENTS.md),
[RELEASING.md](docs/RELEASING.md), [PORTABILITY.md](docs/PORTABILITY.md), and the
[September 20, 2026 assessment](docs/ASSESSMENT-2026-09-20.md), which records that
day's corrections and is a dated, non-attorney record whose test counts are out of date.

`python -I scripts/check_sources.py --report <path>` requests each URL in the
[source register](docs/legal-sources.json) once, honoring robots.txt, writes a JSON report,
and exits 1 if a URL is unreachable or a recorded currency line has changed; it never edits
the register or its `legally_reviewed_at` field. The
[Check sources workflow](.github/workflows/check-sources.yml) runs it monthly and on manual
dispatch and uploads the report as an artifact without committing anything.

## Author and license

William Horschak is a nonlawyer software maintainer in Wisconsin, with a background
in operations management. He publishes these tools and general reference materials;
he does not provide legal services through this project.

- [Website](https://www.williamhorschak.com)
- [LinkedIn](https://www.linkedin.com/in/williamhorschak)
- [GitHub](https://github.com/williamhorschak-dev)

To cite this software, use the "Cite this repository" link on the GitHub page
([CITATION.cff](CITATION.cff)).

Licensed under [MIT](LICENSE). Each skill ZIP also includes the license and the
[legal notice](LEGAL_NOTICE.md).
