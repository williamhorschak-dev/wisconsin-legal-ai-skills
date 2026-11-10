# Set up and first examples

The full installation steps for every host, the download and install checks, the builder command, and one short
invented example for each skill. The [README](../README.md) carries the short version.

## Set up

Everything below was run on Windows with the files from release
`v2026.09.20.2` unless the text says otherwise. Hosts differ; see [TESTED-COMPATIBILITY.md](TESTED-COMPATIBILITY.md).

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
`tests/` are not in the ZIPs, so the maintainer commands in [CONTRIBUTING.md](../CONTRIBUTING.md) do not
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
unfilled placeholders. Without it the builder reports each token and spec path for
square-bracketed text, nonempty single-line angle/curly tokens, two or more
underscores, whole-word `TBD`/`TBA`/`TK`, and whole-word runs of two or more Xs
(case-insensitive). X masks ending in four visible digits are allowed, including
whitespace, period or common dash separators. Intentional matches, including
bracketed quotations and literal X runs, need `--draft`. This is a conservative
screen, not semantic validation or a redaction check. It will not overwrite an
existing file unless you add `--overwrite`.
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
and that no citator ran. See [the full example](../skills/cite-check/references/synthetic-example.md).

**wisconsin-legal-writing.** Say:

> Use wisconsin-legal-writing. Add paragraph breaks only. Preserve every word and the
> signer. Do not research or revise substance. Text: "I request a copy of the attached
> schedule. The copy will help me check the dates. Alex Example, self-represented."

Expected shape: the same three sentences on separate lines, the signer line unchanged,
and a note that no legal review, source check, or signing happened. See
[the full example](../skills/wisconsin-legal-writing/references/synthetic-example.md).
To see the template builder work, run step 6 above and open `motion-draft.docx`;
you will find a captioned motion filled with placeholders and example text.

**wisconsin-legal-interpretation.** Say:

> Use wisconsin-legal-interpretation. What did Fictional Workshop Rule 2 say on March 1,
> 2022? A short lookup is enough. Use only these versions. Version A, effective
> January 1, 2021 through December 31, 2022: "Members may request a paper copy."
> Version B, effective January 1, 2023: "Members may request an electronic copy."

Expected shape: a quick lookup, not a memo; Version A identified as operative for that
date and quoted; the source named as the supplied text, not independently retrieved.
See [the full example](../skills/wisconsin-legal-interpretation/references/synthetic-example.md).
