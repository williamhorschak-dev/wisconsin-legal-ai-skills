# Wisconsin Legal AI Skills

> **General information and software tools; no legal services.** William Horschak
> is **not a licensed attorney**. This project does not provide legal advice or
> representation from the maintainer. Using it or contacting him about it does not
> by itself create an attorney-client relationship. Do not submit confidential or
> case-specific information in public issues or pull requests.
> Read the [legal notice and support boundaries](LEGAL_NOTICE.md).

Reusable workflows for Wisconsin legal research, citation verification, and legal
drafting. Originally developed for Claude, the same skill folders now support
Claude Code, Codex, other Agent Skills hosts, and selective prompt use in ChatGPT
or other LLM applications. Tool availability determines what each host can do.

Each folder contains a `SKILL.md` entrypoint, focused references, and any scripts
or templates it needs. The legal text has one maintained source; vendor-specific
metadata does not create a second version of the law.

Repository: [williamhorschak-dev/wisconsin-legal-ai-skills](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills).

## Skills

| Skill | Purpose | Included tools |
|---|---|---|
| [cite-check](skills/cite-check/SKILL.md) | Inventory citation uses; check quotations, pincites, treatment, proposition support, form, and record references against actual sources. | An evidence log tied by SHA-256 to the draft, sources and inventory (an ordinary file; deleted or hand-edited lines are not detected), text-quotation matcher, and report generator. A report records documented checks; it cannot perform legal judgment or a citator search itself. |
| [wisconsin-legal-writing](skills/wisconsin-legal-writing/SKILL.md) | Draft and review Wisconsin filings, correspondence, discovery responses, and research memoranda using the actual court, posture, and signer. | A **circuit-court** DOCX builder, 11 JSON specifications, and 14 Word templates. The appellate brief, letter, and memorandum templates are maintained separately. |
| [wisconsin-legal-interpretation](skills/wisconsin-legal-interpretation/SKILL.md) | Apply Wisconsin's interpretive method, distinguish binding and persuasive authority, and test contested readings. | Three work modes, a formal-memo template, and a structural linter. A passing lint result does not establish legal accuracy. |

The [September 20, 2026 assessment](docs/ASSESSMENT-2026-09-20.md) explains the
substantive corrections, implementation changes, validation, and remaining limits.

## Install or adapt

Start with the [latest release](https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills/releases/latest).
It includes three complete skill ZIPs, five task-specific prompt exports, the
synthetic evaluation suite, checksums, and the tested compatibility record.

| Your setup | Start here |
|---|---|
| Claude Code or Codex | Extract each desired skill ZIP and copy its complete folder to the installation path below. |
| ChatGPT or another chat application | Open `prompt-packs.zip`, choose one task profile, and provide that Markdown file as instructions/context along with the actual task. |
| Another LLM application or local model | Use the same skill folders or prompt profiles; test the actual host and tools with the [evaluation protocol](evals/README.md). |

Copy a **complete skill folder** to a new installation target after checking for
an existing copy and local changes:

| Host | Project installation | Personal installation |
|---|---|---|
| Claude Code | `.claude/skills/<skill-name>/` | `~/.claude/skills/<skill-name>/` |
| Codex | `.agents/skills/<skill-name>/` | `~/.agents/skills/<skill-name>/` |

Ask for the task, or invoke `/<skill-name>` in Claude Code or `$<skill-name>` in
Codex. The optional `agents/openai.yaml` files supply Codex display metadata.

For Claude skill upload, use one packaged skill ZIP and the account's supported
import flow. For ChatGPT, custom GPTs, and other chat/API hosts, supply the
entrypoint and task-relevant references as instructions, attachments, or retrieved
context. This does not create browsing, Python, storage, or database access.
See [portability and capability profiles](docs/PORTABILITY.md) for exact boundaries
and prompt-export instructions.

For a first example, see the completed fictional [citation check](skills/cite-check/references/synthetic-example.md),
[formatting request](skills/wisconsin-legal-writing/references/synthetic-example.md), or
[historical lookup](skills/wisconsin-legal-interpretation/references/synthetic-example.md).
These demonstrate the workflow without implying that invented materials are law.

## Local tools and validation

Use **Python 3.10 or later**. The filing builder requires `python-docx`; metadata
validation requires `PyYAML`. The citation tool and memo linter use the standard
library. From the repository root:

```sh
python -m pip install -r requirements-dev.txt
python scripts/skill_tools.py validate
python -m unittest discover -s tests -v
python scripts/skill_tools.py package --out dist/skills
```

Choose a new package output directory. Each deterministic ZIP contains one complete
skill folder, its MIT license, legal notice, and a checksum manifest. CI runs the checks on
Windows and Linux with Python 3.10 and 3.12.

Build a fill-in circuit-court template with explicit draft mode:

```sh
python skills/wisconsin-legal-writing/scripts/build_filing.py skills/wisconsin-legal-writing/assets/01-motion.json -o motion-draft.docx --draft
```

Existing output files are preserved unless `--overwrite` is explicitly supplied.
Draft mode permits unresolved placeholders. Without it, the builder performs
additional input checks, but neither mode certifies a document for filing. Inspect
the rendered pages, governing requirements, factual support, and actual signatures.
Appellate output must use the separate appellate template and current Rule 809.19.

See the [citation tool guide](skills/cite-check/references/evidence-tool.md) for
evidence-log commands, and the [interpretation README](skills/wisconsin-legal-interpretation/README.md)
for formal-memo validation.

## Verification and maintenance

Read the [tested compatibility record](docs/TESTED-COMPATIBILITY.md) before treating
format compatibility as evidence of model performance. The [24-scenario suite](evals/README.md)
supports paired baseline/skill trials and hash-bound reviews; unrun or unreviewed
trials cannot pass. Model calls are opt-in and are not run by ordinary CI.

The [source register](docs/legal-sources.json) tracks review scope and affected files.
Its [maintenance procedure](docs/SOURCE-MAINTENANCE.md) distinguishes new checks,
inherited reviews, and pending work. [Template QA](docs/TEMPLATE-QA.md) separates
the automatic rebuild checks from rendered-page review. See the
[release procedure](docs/RELEASING.md) and [current release notes](docs/RELEASE-NOTES.md).

Skill text is a research aid, not retrieved authority. Verify the controlling
version, court, jurisdiction, primary text, and relevant subsequent treatment when
using it. Record the checks actually performed. Identify missing source access or
citator coverage explicitly; never infer a completed check from a template, an
LLM's confidence, or a successful script.

Court rules and orders control over typography preferences. Preserve the user's
actual facts, role, voice, and authorized scope. A drafting request does not itself
direct filing or service. Keep private matter files and credentials out of this
public repository.

After reviewed changes, refresh manifests with
`python scripts/skill_tools.py manifest`, then rerun validation and relevant tests.
Rebuild and visually inspect affected Word templates after specification or layout
changes. Recheck current primary law before revising legal guidance. These aids do
not replace matter-specific legal review or any professional review required by law.

## Author and license

William Horschak is a nonlawyer software maintainer in Wisconsin, with a background
in operations management. He publishes these tools and general reference materials;
he does not provide legal services through this project.

- [Website](https://www.williamhorschak.com)
- [LinkedIn](https://www.linkedin.com/in/williamhorschak)
- [GitHub](https://github.com/williamhorschak-dev)

Technical bug reports, general documentation corrections, and feature suggestions
are welcome through repository issues. Do not request advice about an individual
matter or submit confidential information. See [contribution and support guidelines](CONTRIBUTING.md).
Licensed under [MIT](LICENSE); each distributable skill also includes the license
and [legal notice](LEGAL_NOTICE.md).
