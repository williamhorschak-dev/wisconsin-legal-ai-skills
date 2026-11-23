# Set up and first examples

Installation steps for the hosts listed below, the download and install checks, the builder command, and one short
invented example for each skill. The [README](../README.md) carries the short version.

## Set up

For dated operating system, host and release checks, see [TESTED-COMPATIBILITY.md](TESTED-COMPATIBILITY.md).

**1. Download.** From the [latest release](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/releases/latest),
put `SHA256SUMS.txt` and the files you want in a new empty folder. The examples use a
folder named `wi-release` inside Downloads. Keep the original filenames.

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

**3. Verify and install the ZIP.** Use **By hand** below for a release download. The examples
install `cite-check` for one Claude Code project. For another skill, substitute its exact ZIP
and folder name. For another host or a personal install, use the folder from step 2.

**By hand.** Open the new download folder. On Windows, open PowerShell in that folder and
run **Other downloads** below. Continue only after you see `OK  cite-check.zip` for your
chosen ZIP and the check finishes without an error. On macOS, run `shasum -a 256 cite-check.zip`;
on Linux, run `sha256sum cite-check.zip`. Check for exactly one line for that filename in
`SHA256SUMS.txt` and compare all 64 hash characters, ignoring case. Stop if anything differs.

1. Extract the checked ZIP into a **new** folder named `wi-unpacked` in the download folder,
   if it is on the installation drive. Otherwise create the new folder on the project's drive,
   outside the host, and edit the source path below to match. On Windows, right-click the ZIP, choose **Extract All**,
   and enter that folder as the destination. Open the extracted `cite-check` folder and confirm
   it contains `SKILL.md`. Keep downloads and extraction outside any host's skills folder.
2. On Windows, open your **project** folder in File Explorer. Type `powershell` in its address
   bar and press Enter. Check the displayed folder before pasting the whole block below.
   If it is wrong, run `Set-Location -LiteralPath 'C:\path to your project'` with your actual
   project path and confirm it with `Get-Location`. If you
   used another download location, edit the first path. The move stops if the destination exists.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $source = "$HOME/Downloads/wi-release/wi-unpacked/cite-check"
    $root = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.claude/skills')
    if (-not [IO.File]::Exists([IO.Path]::Combine($source, 'SKILL.md'))) { throw "Missing extracted SKILL.md." }
    $null = [IO.Directory]::CreateDirectory($root)
    [IO.Directory]::Move($source, [IO.Path]::Combine($root, 'cite-check'))
    "Installed cite-check in $root"
}
```

3. On macOS or Linux, create the skills folder from step 2 if needed. In the file manager,
   move the whole extracted skill folder into it only if that name is free. Cancel any merge
   or replacement prompt. To compare versions on any system, keep the new folder outside the
   host, alongside your existing work. Use ordinary local directories that you control throughout.

**Optional PowerShell installer.** If you already have a reviewed repository checkout and your
organization permits running its script, you can use [the installer](../scripts/install_release_skill.ps1)
instead of the by-hand steps. It is unsigned and the release checksums cover the ZIPs and records.
Read the script at the revision you intend to run. From the project folder, in your current
PowerShell window, replace the example checkout path and run:

```powershell
& "$HOME/wisconsin-legal-ai-skills/scripts/install_release_skill.ps1" -Archive "$HOME/Downloads/wi-release/cite-check.zip" -SkillsDirectory ".claude/skills"
```

On a Windows client, the default Restricted policy permits individual commands and refuses
script files. Under RemoteSigned, an unsigned script marked as downloaded from the internet
can also be refused. Keep your existing policy. If it blocks the script, use the by-hand steps
where your organization permits them. If a standard command is missing, open PowerShell from
Start or ask your administrator. The installer verifies one staged copy of the ZIP against
the one matching release checksum, then moves the extracted skill into a free destination.

**Other downloads.** The installer takes only the three skill ZIPs. To check every file you
downloaded against the published list, paste this into PowerShell in the download folder.
Commands pasted into the window are not script files, so the default policy does not stop them.

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $seen = @{}
    $checked = 0
    $folder = (Get-Location).ProviderPath
    foreach ($line in Get-Content -LiteralPath ([IO.Path]::Combine($folder, 'SHA256SUMS.txt'))) {
        if ($line -cnotmatch '^([0-9A-Fa-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)$') { throw "Invalid checksum line." }
        $hash, $name = $Matches[1], $Matches[2]
        if ($seen.ContainsKey($name)) { throw "Duplicate checksum for $name." }
        $seen[$name] = $true
        $file = [IO.Path]::Combine($folder, $name)
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { "SKIPPED  $name"; continue }
        if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $hash) { throw "MISMATCH  $name" }
        "OK  $name"
        $checked++
    }
    if ($checked -eq 0) { throw "No listed downloads found. Open the folder containing the release files." }
}
```

An optional file you did not download is marked SKIPPED. A missing list, an empty selection,
a duplicate entry or a mismatch stops the check. For every file you intend to use, look for
its exact name on an OK line and make sure the block finished without an error. On Linux, run
`sha256sum -c SHA256SUMS.txt`. On macOS, run `shasum -a 256 -c SHA256SUMS.txt`. Both expect
every listed file to be in the folder. A checksum shows the file matches the published one. It
does not show the content is correct.

**4. Check an installed copy.** Open the individual skill folder. Its `MANIFEST.sha256` lists
the files shipped with it. Run `shasum -a 256 -c MANIFEST.sha256` on macOS or
`sha256sum -c MANIFEST.sha256` on Linux. In PowerShell, run the following from that folder.

```powershell
$folder = (Get-Location).ProviderPath
$records = @(Get-Content -LiteralPath ([IO.Path]::Combine($folder, 'MANIFEST.sha256')) -ErrorAction Stop)
if ($records.Count -eq 0) { throw "Empty skill manifest." }
foreach ($record in $records) {
    if ($record -cnotmatch '^([0-9a-f]{64})  (.+)$') { throw "Invalid manifest line." }
    $expected, $file = $Matches[1], $Matches[2]
    if ((Get-FileHash -LiteralPath ([IO.Path]::Combine($folder, $file)) -Algorithm SHA256 -ErrorAction Stop).Hash -ne $expected) {
        throw "Checksum mismatch for $file"
    }
}
"Verified $($records.Count) listed files."
```

This checks only the files listed in the local manifest. Added personal files are outside the
check. To compare with the published files, start with a separately verified release ZIP.
The repository's own `scripts/skill_tools.py` and `tests/` are not in the ZIPs, so the maintainer
commands in [CONTRIBUTING.md](../CONTRIBUTING.md) do not run in an installed copy.

**5. Use it.** Ask for the task in plain words, or name the skill: `/cite-check`
in Claude Code, `$cite-check` in Codex. On one Windows host, Claude Code desktop subagents
selected skills from an earlier release in the [October trials](../evals/triggers/results/2026-10-24-claude-code-subagents.md).
A [November probe](../evals/triggers/results/2026-11-10-listing-probe.md) found duplicate listings and
entries shown by name only. Discovery on a clean installation of this release and in Codex remains unmeasured.

Other hosts:

- **Claude web or desktop upload:** use one skill ZIP with your account's skill upload.
  Not tested by this project.
- **ChatGPT or another chat application:** open `prompt-packs.zip` and give the model
  one profile file plus your task. `citation-audit.md` checks citations in a draft you
  supply; `draft-review.md` reviews or edits a Wisconsin filing; `interpretation-lookup.md`
  answers what a provision says; `interpretation-analysis.md` handles a contested
  reading; `formal-memo.md` produces a full memo. In release 2026.11.21.1, the five profiles
  range from about 54,000 to 149,000 characters. Some products limit instruction or upload size; that has not
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

Expected shape: the two sentences and the original signer on separate lines,
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
