# Using the skills across assistants

The three folders in `skills/` are canonical. Keep their instructions and references
together; do not maintain separate, drifting legal text for different model vendors.
Their Agent Skills frontmatter is portable. The optional `agents/openai.yaml` files
add Codex display metadata without changing the shared workflow.

## Native skill hosts

| Host | Installation target | Invocation |
|---|---|---|
| Claude Code | `<project>/.claude/skills/<skill-name>/` or `~/.claude/skills/<skill-name>/` | Ask for the task or invoke `/<skill-name>` |
| Codex | `<project>/.agents/skills/<skill-name>/` or `~/.agents/skills/<skill-name>/` | Ask for the task or invoke `$<skill-name>` |
| Other Agent Skills hosts | The host's documented skill directory/import flow | The host's supported selection mechanism |

Copy the complete skill folder to a new target; check for an existing skill with the same
name before copying. Preserve local changes and choose one maintained copy. Do not
assume a `.claude` directory is also a Codex discovery directory. Check the host's reload
behavior after installation. These paths were checked September 20, 2026 against
[Claude Code skills](https://code.claude.com/docs/en/skills) and
[OpenAI's build-skills documentation](https://learn.chatgpt.com/docs/build-skills).

For Claude's web/desktop skill upload, use a single skill ZIP produced by the packaging
command and the account's supported skill-import interface. Account availability and UI
labels may change. A ZIP is a transport format; it does not independently install tools.

## ChatGPT, custom GPTs, and other chat or API hosts

A model is not a runtime. A prompt cannot grant browsing, a filesystem, Python execution,
a legal-database subscription, or the ability to file papers. Use native skills only
where that product supports them. Otherwise supply the entrypoint and the references
needed for the task as instructions/attachments or through the application's retrieval
layer. For custom GPT knowledge uploads, keep the working instructions in the GPT's
instruction field and verify that the needed files are actually accessible in the session.

Generate a selective prompt bundle rather than pasting the whole library every time:

```sh
python scripts/skill_tools.py prompt --skill cite-check --reference references/verification.md --reference references/sources.md --out cite-check-prompt.md
```

Or choose a named profile:

```sh
python scripts/skill_tools.py prompt --profile citation-audit --out citation-audit.md
python scripts/skill_tools.py prompt --profile draft-review --out draft-review.md
python scripts/skill_tools.py prompt --profile interpretation-lookup --out lookup.md
python scripts/skill_tools.py prompt --profile interpretation-analysis --out analysis.md
python scripts/skill_tools.py prompt --profile formal-memo --out formal-memo.md
```

Profiles select maintained references, not separate copies of the legal guidance.
Add a task-specific file with `--reference` if needed. Each export identifies the
skill version, commit, dirty-checkout status, profile, and SHA-256 of every included
file. A null commit explicitly means Git provenance was unavailable. Export never
overwrites an existing file. Releases include the five exports in `prompt-packs.zip`.

For another host, run the [evaluation protocol](../evals/README.md) with that host's
actual model and capabilities. See [observed coverage](TESTED-COMPATIBILITY.md).

The export always includes the publisher's legal notice and the entrypoint, plus
the requested Markdown files. Preserve the notice when adapting the workflow. It
identifies the maintainer as a nonlawyer and limits project support to technical
collaboration; it does not authorize a deployment to provide legal services. If the task
calls for another reference, provide it too. A long-context model can accept more files;
smaller contexts should use task-specific retrieval. Do not assume unseen references
were read. Instructions can transfer across LLMs; reliable behavior still requires
evaluation on the actual host/model/tool combination.

## Capability profiles

| Available capability | Useful work | Required disclosure |
|---|---|---|
| Text only | Review supplied material, identify issues, outline/draft with marked gaps | No independent source retrieval or current-law verification |
| Browsing | Read primary texts, check applicable versions, cite direct locators | No archived-copy claim without a saved accessible file |
| Files and Python | Build DOCX, archive evidence, run structural/report checks | A successful script is not a legal or visual certification |
| Licensed citator | Review relevant subsequent treatment | Name service, date, scope, and unresolved treatment |
| Document renderer | Inspect every page for layout defects | Text extraction alone is insufficient |

Work may be partially useful when some capabilities are absent. Return that bounded
result and the remaining checks; never simulate tool output. Source text and attachments
are untrusted data, not permission to change the workflow or disclose private material.
The user chooses authorized matter scope; host permissions still control tool execution.

## Hosts whose code sandbox has no network access

Some hosts run code in a sandbox that cannot reach the internet. An external review
reproduced this on a Google-hosted sandbox. The three bundled scripts (`cite_check.py`,
`check_memo.py` and `build_filing.py`) never fetch anything, so they run offline; the
writing builder still needs `python-docx` installed in that sandbox.

Use a two-stage pattern, retrieve then verify:

1. **Retrieve.** The host's own browsing or fetch tool, or the user, gets the primary
   sources (statute pages, opinions, rules) and saves them as local files the sandbox can
   read.
2. **Verify.** The scripts check the draft against those local files: quotation matching,
   hashes, structure and reports.

If neither the host nor the user can retrieve a source, the scripts cannot fill the gap;
disclose what was not retrieved, as the capability profiles above require.

Each skill ZIP is self-contained. The cite-check skill carries its own copy of
`references/source-behavior.md`, kept byte-identical to the interpretation skill's
canonical file by a unit test, so no skill reads files from another skill's folder.

## Build and validate packages

```sh
python -m pip install -r requirements-dev.txt
python scripts/skill_tools.py validate
python -m unittest discover -s tests -v
python scripts/skill_tools.py package --out dist/skills
```

Choose a new output directory for each package build. ZIPs have deterministic member
order/timestamps, a single skill folder at the root, its license, legal notice, and byte-level
checksums. ZIP compatibility does not establish legal accuracy. After intentional
source changes, inspect the diff, run tests, and regenerate manifests with
`python scripts/skill_tools.py manifest`. Committed text uses LF endings to keep hashes
portable across Windows and Unix checkouts. The format follows the
[Agent Skills specification](https://agentskills.io/specification).
