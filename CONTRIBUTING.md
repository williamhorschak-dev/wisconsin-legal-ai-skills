# Contribution and support guidelines

Read the [legal notice](LEGAL_NOTICE.md) before opening an issue or pull request.
William Horschak is a nonlawyer publishing software tools and general information;
this project does not accept legal clients or provide individual legal services.

Use issues for reproducible software defects, general documentation corrections,
and feature suggestions. Use fictional names and synthetic data. For a correction
to a general legal reference, identify the passage and link the official public
source; do not submit an actual case for review. Say when you read the source and
what date the text takes effect. A statute page can display amended text before the
amendment takes effect, so read any effective-date note on the page and the
amending Act's effective-date section.

Do not request selection of claims or remedies, personal deadline calculations,
review of a proposed filing, or advice about litigation, settlement, or an appeal.
Do not provide individualized legal advice to others through project channels.
Direct requests for personal legal assistance to qualified counsel.

Issues and pull requests are public. Do not post case files, personal identifying
details, privileged communications, financial records, or credentials. If sensitive
material has already been posted, do not quote or repost it. Removal from the
project cannot guarantee removal of copies already made elsewhere.

Keep changes focused and follow [AGENTS.md](AGENTS.md) for validation. Keep the root
legal notice and the three standalone skill copies identical; packages and prompt
exports must include it. Refresh manifests after reviewing skill changes. The
notice explains scope and does not add conditions to the MIT license.

## Working on the repository

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
described in [evals/README.md](evals/README.md); recorded results are under
[evals/triggers/results](evals/triggers/results/). A small fixed query set does not show
that a skill triggers reliably on any host or model. See [AGENTS.md](AGENTS.md),
[RELEASING.md](docs/RELEASING.md), [PORTABILITY.md](docs/PORTABILITY.md), and the
[September 20, 2026 assessment](docs/ASSESSMENT-2026-09-20.md), which records that
day's corrections and is a dated, non-attorney record whose test counts are out of date.

`python -I scripts/check_sources.py --report <path>` requests each URL in the
[source register](docs/legal-sources.json) once, honoring robots.txt, writes a JSON report,
and exits 1 if a URL is unreachable or a recorded currency line has changed; it never edits
the register or its `legally_reviewed_at` field. The
[Check sources workflow](.github/workflows/check-sources.yml) runs it monthly and on manual
dispatch and uploads the report as an artifact without committing anything.
