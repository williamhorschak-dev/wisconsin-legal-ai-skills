# wisconsin-legal-interpretation

William Horschak is not a licensed attorney. This is a published research tool;
the maintainer does not offer legal services through this project.
Read the [legal notice and public support boundaries](LEGAL_NOTICE.md).

A skill that replaces an assistant's default, nationally-averaged legal reasoning with
Wisconsin's actual interpretive framework, and refuses to let a proposition of law out the door
without the words it rests on.

It ships with no personal paths, no employer information, and no database entitlements. Anything
of that kind belongs in an optional private overlay the user supplies for an identified matter
(`references/sources.md` § 9).

## What it changes

| Default behavior | With this skill |
|---|---|
| Paraphrases what a statute "basically says" | Quotes the operative language verbatim, with a pincite and a retrieved copy on disk |
| Reasons from purpose, then finds text to fit | Runs the sequence *SEIU* states: every intrinsic source first — text, definitions, structure, statutory history, construction statutes, intrinsic canons, binding construction — **then** the plain-meaning call, and only then ambiguity, substantive canons, and extrinsic sources |
| Treats the newest case as the strongest | Applies *Cook v. Cook*: the court of appeals cannot overrule itself, so conflicting published decisions are both live |
| Treats the Seventh Circuit as controlling | Persuasive only in Wisconsin state courts, and says so |
| Defers to reasonable agency readings | On ch. 227 judicial review, Wis. Stat. § 227.57(11): no deference to the agency's interpretation of law, by statute; municipal certiorari review has its own standards (*Grycowski*, 2021 WI App 7, ¶ 30 & n.2) |
| Cites any case it finds | Runs the § 809.23(3) citability screen and tracks the copy-filing duty |
| Delivers the analysis | Delivers the analysis, an authority table backed by an archive, and an adversarial red team report |
| Reviews when asked | Red-teams every contested answer and every memo, unasked — compact in Mode 2, all seven attacks in Mode 3 — and discloses when a pass was skipped |

**Status as checked October 12, 2026.** In *SEIU Healthcare Wisconsin v. WERC*, 2025 WI 29,
the majority opinion for a unanimous Court applied *Kalal* (cover; ¶¶ 9-12), while Justice
Dallet's concurrence, joined by three other justices (four of seven), proposed a broader,
holistic approach (cover; ¶ 65). The clerk's Table of Pending Cases (p. 9) lists *Abby
Windows, LLC v. LIRC*, No. 2024AP1013, accepted 06/16/2026, with oral argument scheduled for
November 10, 2026 on whether to revisit and modify the *Kalal* framework. Apply *Kalal* as
explained in *SEIU* unless later controlling authority changes it, and check the case's
current status before relying on that framework.
<!-- DRAFT FOR LEGAL REVIEW (2026-10-12), L-008 and K-1: one identical dated status sentence in canons.md section 1.6, standards-of-review.md and the interpretation README. Sources: SEIU, 2025 WI 29, cover, ¶¶ 9-12, ¶ 65 (https://www.wicourts.gov/sc/order/DisplayDocImage.pdf?docId=977376); Clerk's Table of Pending Cases, p. 9, No. 2024AP1013 (https://www.wicourts.gov/sc/SCCASES.pdf), both read 2026-10-12. No citator content. Recheck on 2026-11-10 and on decision. -->
<!-- DRAFT FOR LEGAL REVIEW (2026-10-12), L-016 (table row on agency readings): Wis. Stat. § 227.57(11), https://docs.legis.wisconsin.gov/document/statutes/227.57; Grycowski v. Milwaukee Employees' Retirement System/Annuity and Pension Board, 2021 WI App 7, ¶ 30 and n.2, https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=317184; read 2026-10-12. -->

## Contents

```
wisconsin-legal-interpretation/
├── SKILL.md                        the router, three modes, and the five rules
├── references/
│   ├── canons.md                   Kalal, ch. 990, canons, admin rules, constitution,
│   │                               ordinances, federal interplay, the staged sequence
│   ├── authority-hierarchy.md      what binds, what persuades, what may not be cited
│   ├── sources.md                  source ladder, database login protocol, the citator
│   │                               rule, failure modes, the optional private overlay
│   ├── red-team.md                 the seven attacks, severities, confidence grades
│   └── memo-format.md              three-lens memo, authority table, red team report
├── assets/
│   ├── memo-template.md            blank memo
│   └── example-memo.md             format specimen (unverified sources, labeled)
└── scripts/
    └── check_memo.py               structural lint, run before delivering
```

## Three lenses

Every substantive answer separates what the law **is** (neutral), how each **side** argues it
(both at full strength), and how a Wisconsin court likely **rules** (predicted, with a confidence
grade the red team assigns). Blending them is how motivated reasoning gets into a memo without
anyone noticing.

## Three operating modes

Most questions do not need a memo. **Mode 1 (quick lookup)** is the default: current text,
operative quotation, citation, direct source link, date verified. **Mode 2 (contested
interpretation)** runs the Wisconsin sequence, both good-faith readings, a prediction, and a
compact adversarial check. **Mode 3 (formal memo)** runs the full apparatus, and only when it is
asked for. SKILL.md states the triggers.

## Database access and the citator rule

The skill assumes no database. Use an available, authorized session; ask about access only
when needed information cannot be inferred from the current environment. The user handles
credentials, one-time codes, and challenges. Respect actual subscription terms without
inventing a universal academic-license restriction. If source retrieval or a citator is
unavailable, identify that limitation and provide only the supported, bounded analysis.

**For outcome-determinative work, negative treatment is checked through an authorized citator, or
the memo says on its face that the authority was not Shepardized or KeyCited and the stated
confidence is capped.** There is no third option, the disclosure is not a footnote, and a
free-source cited-by search is not a citator result.

`check_memo.py` enforces this on **constrained frontmatter fields**, not on prose —
`citator: KeyCite|Shepards|NONE` with a date and a signal, `red_team: full|compact|none`,
`fatal_findings: <integer>` — with all narrative in `citator_notes:`, which the linter never
parses. The memo's own words are read only as a backstop, to raise a MISMATCH when the narrative
and the fields disagree. `references/sources.md` § 8 explains why the split is drawn there.

## Optional companions

Both are **conditional** — the skill checks whether they exist before offering a hand-off, and
neither is required:

- **A citation-verification skill** — formal verification and archiving before filing. Uses the
  same `sources/` layout, so the two compose without conversion.
- **A Wisconsin legal-drafting skill** — turns the answer into the filing. Verbatim quotations
  cross over intact rather than being re-summarized from memory.

## Live currency warning

The Wisconsin interpretive framework is itself contested: a petition to revisit and modify it has
been before the Wisconsin Supreme Court, and *SEIU* and *Brekke* have already refined how the
sequence is stated. **This file states no docket status and no expected decision date, because
either would be stale by the time it mattered.** Any run touching interpretive method checks the
current status of the framework cases at the start and records the date of that check in the
`framework_checked` field.

## Verification

The quotations in the reference files were transcribed from primary sources (wicourts.gov for
the opinions; Justia for statutory text, flagged for confirmation against docs.legis before
filing) during the run that built this skill. Items that were **not** independently retrieved
carry an inline `[UNVERIFIED]` marker — but the absence of a marker records that one build, not
today's law. **A skill file is not a retrieved primary source.** Re-pull before any quotation
appears in an output as law; `red-team.md` scores a value copied from a skill file as a failed
check.

`assets/example-memo.md` is a **format specimen**: its source paths are notional, no citator was
run against its authorities, and it says so at the top. Do not treat it as verified research.

`scripts/check_memo.py` needs Python 3.10 or later and only the standard library. Run it when
the host can execute Python; otherwise disclose that structural lint was not run. For a
completed Mode 3 memo, use `--formal --sources <archive>` to check source-path existence and
containment. An intentionally incomplete draft must identify its gaps. The linter screens
recognized cited-path forms including backticks,
links, quotes, tables, code fences, frontmatter, bare prose, and non-web URI schemes — rejecting
traversal, UNC, and system or credential locations outright and warning on other absolute paths, and it resolves archive paths
through symlinks before checking containment. Markdown and prose parsing is heuristic, not
exhaustive. **It is a floor, not a warrant.** A clean run says the checked sections are present,
recognized quotations carry pincites, cited paths resolve when an archive is supplied, and
the frontmatter's claims do not contradict the
memo's own text. It does not say the citator ran, the red team ran, or the law is right — those
are the author's claims, in fields the tool can only check for consistency. Never the last check
before a filing.
