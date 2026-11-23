# Set up and first examples

The full installation steps for every host, the download and install checks, the builder command, and one short
invented example for each skill. The [README](../README.md) carries the short version.

## Set up

For dated operating system, host and release checks, see [TESTED-COMPATIBILITY.md](TESTED-COMPATIBILITY.md).

**1. Download.** From the [latest release](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/releases/latest),
put `SHA256SUMS.txt` and the files you want in a new empty folder.

| File | Use |
|---|---|
| `cite-check.zip`, `wisconsin-legal-writing.zip`, `wisconsin-legal-interpretation.zip` | One skill each. For Claude Code, Codex, and other Agent Skills hosts. |
| `prompt-packs.zip` | Five prompt files for chat applications. |
| `evaluation-suite.zip` | 24 synthetic test scenarios, for people who want to test a model themselves. |
| `BUILD.json`, `RELEASE-NOTES.md`, `TESTED-COMPATIBILITY.md` | Build record, release notes, and the testing record. |

**2. Choose an installation folder.** For a single project, start in the project's root.
For a personal installation, use the personal folder in this table. Install one skill at a time.

| Host | Project folder | Personal folder |
|---|---|---|
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Codex | `.agents/skills/` | `~/.agents/skills/` |

**3. Verify and install the ZIP.** Save [the PowerShell installer](../scripts/install_release_skill.ps1)
using GitHub's **Download raw file** button, or use it from a clone. It is a short script. Read it
before you run it. If you saved the script and release files in your Downloads folder, run this
from your project in PowerShell on Windows.

```powershell
powershell -ExecutionPolicy Bypass -File "$HOME/Downloads/install_release_skill.ps1" -Archive "$HOME/Downloads/cite-check.zip" -SkillsDirectory ".claude/skills"
```

Windows does not start a downloaded script file unless it is told to. This form allows that one
run and changes no setting on the computer. Calling the script directly stops with "running
scripts is disabled on this system" on a Windows computer where no script policy has been set.
If your computer is not allowed to run script files at all, use the steps under **By hand**
below. Under PowerShell 7 on another system, start the script with `pwsh -File` and the same two
options. The project's tests run it that way on Linux.

The installer requires exactly one checksum for the chosen ZIP in the release's
`SHA256SUMS.txt`. It checks the copy it will unpack and moves the complete skill into
place. Success names the ZIP and its destination. On a repeat install it stops. To compare an
upgrade with your existing copy, point `-SkillsDirectory` at a separate folder outside your
host. You can then decide which personal edits to keep.

**By hand.** From the download folder, run `shasum -a 256 cite-check.zip` on
macOS or `sha256sum cite-check.zip` on Linux. In PowerShell on Windows, paste
`(Get-FileHash cite-check.zip -Algorithm SHA256).Hash`. It prints the hash in capital letters, so
compare without regard to case. Find the one line ending in two spaces and
`cite-check.zip` in the published checksum list. Continue only if the file exists, the entry
appears exactly once and all 64 characters of the two hashes agree. Unpack into a new,
empty folder outside the host. In PowerShell that is
`Expand-Archive cite-check.zip -DestinationPath` followed by the new folder's name. If the host already has a folder named `cite-check`, keep
the unpacked copy separate. Otherwise move just the unpacked `cite-check` folder into the
host's skills folder. Substitute the appropriate filename and folder for either other skill.

**Other downloads.** The installer takes only the three skill ZIPs. To check every file you
downloaded against the published list, paste this into PowerShell in the download folder.
Commands pasted into the window are not script files, so the default policy does not stop them.

```powershell
Get-Content SHA256SUMS.txt | ForEach-Object {
  $hash, $name = $_ -split '\s+', 2
  if (Test-Path $name) {
    $ok = (Get-FileHash $name -Algorithm SHA256).Hash.ToLower() -eq $hash
    "{0}  {1}" -f ($(if ($ok) {'OK'} else {'MISMATCH'})), $name
  }
}
```

It prints one line for each listed file that is in the folder. On Linux, run
`sha256sum -c SHA256SUMS.txt`. On macOS, run `shasum -a 256 -c SHA256SUMS.txt`. Both expect
every listed file to be in the folder. A checksum shows the file matches the published one. It
does not show the content is correct.

**4. Check an installed copy.** Open the individual skill folder. Its `MANIFEST.sha256` lists
the files shipped with it. Run `shasum -a 256 -c MANIFEST.sha256` on macOS or
`sha256sum -c MANIFEST.sha256` on Linux. In PowerShell, run the following from that folder.

```powershell
$records = @(Get-Content -LiteralPath MANIFEST.sha256 -ErrorAction Stop)
if ($records.Count -eq 0) { throw "Empty skill manifest." }
foreach ($record in $records) {
    if ($record -cnotmatch '^([0-9a-f]{64})  (.+)$') { throw "Invalid manifest line." }
    $expected, $file = $Matches[1], $Matches[2]
    if ((Get-FileHash -LiteralPath $file -Algorithm SHA256 -ErrorAction Stop).Hash -ne $expected) {
        throw "Checksum mismatch for $file"
    }
}
"Verified $($records.Count) listed files."
```

The repository's own `scripts/skill_tools.py` and `tests/` are not in the ZIPs, so the maintainer
commands in [CONTRIBUTING.md](../CONTRIBUTING.md) do not run in an installed copy.

**5. Use it.** Ask for the task in plain words, or name the skill: `/cite-check`
in Claude Code, `$cite-check` in Codex. On one Windows host, Claude Code desktop subagents
selected skills from an earlier release in the [October trials](../evals/triggers/results/2026-10-24-claude-code-subagents.md).
A [November probe](../evals/triggers/results/2026-11-10-listing-probe.md) found duplicate listings and
missing or incomplete descriptions. Discovery on a clean installation of this release and in Codex remains unmeasured.

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
