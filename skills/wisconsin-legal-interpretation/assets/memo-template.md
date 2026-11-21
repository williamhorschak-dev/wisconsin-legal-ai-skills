---
type: research-memo
status: draft
matter: <matter name / case number>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
operative_date: <date whose law governs, and why>
framework_checked: <YYYY-MM-DD — what was checked live today, and what was found>
citator: <KeyCite | Shepards | NONE>
citator_date: <YYYY-MM-DD — required unless citator is NONE>
citator_signal: <none | yellow | red | other — required unless citator is NONE>
citator_notes: <free text; the flags and what they mean, or the §3 substitutes actually run>
red_team: <full | compact | none>
fatal_findings: <integer; FATAL findings still OUTSTANDING — 0 if none>
# fatal_findings_first_pass: <optional integer; FATAL findings the first pass found and you fixed>
confidence: <HIGH | MODERATE | LOW | UNRESOLVED>
tags: [legal, research, wisconsin]
---

# <Question, stated as a question>

## Question Presented

<One sentence. Name the text, the actor, the conduct, and the date.>

## Short Answer

<Three sentences at most: the answer, the reason, the confidence grade. A reader who stops here
must not be misled by having stopped here.>

## Governing Text

### <Wis. Stat. § X.XX (YYYY-YY)>

> <verbatim text of the operative provision>

§ 990.001(6).   <-- a real pincite goes on its own line BELOW the quotation, not only in the
heading. Every block quotation needs one within four lines of its end, and the heading above it
does not count. Administrative Code form works too: § DHS 134.31(3)(g).

Source: `sources/statutes/<file>` · Retrieved <date> · Currency banner: "<verbatim banner>"
Version in force on <operative date>: <yes / differs how>

### <Next provision>

> <verbatim>

§ 802.09(3).   <-- and again here: one pincite per block quotation.

## Lens 1 — What the Law Is

*Neutral. No characterization. Run the sequence in `canons.md` § 8 in its stated order and show
each step, including the ones that came out empty. **The plain-meaning call comes after all the
intrinsic sources, not before them** — that ordering is the point of the sequence, not a detail
of it.*

**Stage A — intrinsic sources, all of them, before any plain-meaning call**

1. **Text**, in the version in force at the operative date.
2. **Definitions** — section, chapter, § 990.01, common usage, technical meaning; follow any
   cross-reference into a borrowed chapter and run this step again there.
3. **Structure and related statutes**, and any textually manifest purpose.
4. **Statutory history** — how the text itself has changed. (Intrinsic. Not legislative history.)
5. **Construction statutes** — § 990.001, read with its introductory clause first,
   and chapter-specific enacted construction directives within their stated scope.
   An enacted liberal-construction directive is statutory text; consider it here.
6. **Intrinsic (textual) canons** — whole-text, surplusage, *noscitur*, *ejusdem generis*,
   *expressio unius*, absurdity avoidance. **These need no ambiguity finding.**
7. **Binding construction of the same words**, run through `authority-hierarchy.md`.

**Stage B — the plain-meaning call, made on the whole of Stage A**

8. **Plain meaning?** State what made it plain. If plain, ordinarily go to Application;
   identify any optional use of extrinsic sources solely to confirm that reading.
9. **If ambiguous** — the two or more senses, and who reasonably holds each.

**Stage C — resolve remaining ambiguity; extrinsic confirmation is a separate use**

10. **Substantive canons** — lenity (grievous ambiguity only), avoidance, and generic
    judge-made remedial or liberal-construction maxims, subject to governing Wisconsin
    decisions. Enacted construction directives belong in Stage A. For retroactivity,
    follow the separate analysis in `canons.md` § 3.2 and § 2.4.
11. **Extrinsic sources** — legislative history, drafting records, LRB analyses, Council
    notes: use to resolve ambiguity, or identify their limited use to confirm an already
    established plain reading. Do not use them to manufacture ambiguity.

## Lens 2 — How Each Side Argues It

### Our best reading

<Strongest version of the requester's position — or Reading A, if the work is neutral — with its best text and authority.>

### Their best reading

<Strongest supported opposing position. Do not invent a dispute or force equal length; explain
when controlling text or authority forecloses the alternative.>

## Lens 3 — How a Wisconsin Court Likely Rules

- **Likely outcome:**
- **Which argument prevails, and why:**
- **Standard of review:** <named, quoted, with authority> — <what it does to the odds>
- **Forum-specific considerations:** `[INFERENCE]` <with inputs named>
- **What would change this:**
- **Confidence:** <grade, assigned by the red team>

## Application

| Element | Text (quoted) | Facts | Fit | Missing |
|---|---|---|---|---|
| | | | | |

## Open Questions and What Would Resolve Them

- <Specific. Name the document, the source, and the cost.>

## Authority Table

<!-- For How found, use the values in references/authority-hierarchy.md §8. -->

| # | Citation | Cited for | Binding? | Citable? | Vintage OK? | Copy | How found | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |

## Red Team Report

Run: <independent agent | in-session pass> on <date>
Attacks run: <which of 1-7 were attempted; do not write "1-7" unless all seven were>
Checks not run: <name each check that did not run and why — an unrun check is never a passed
check. Write "none" only if that is true.>

### Findings

<Schema from `red-team.md` §3, most severe first. "No findings" is valid and is stated with the
list of what was checked.>

### Best contrary reading, at full strength

<Attack 4's output, preserved even where it was answered.>

### Confidence: <GRADE>

<Why this grade and not the one above it.>

## Retrieval Record

| Source file | Origin URL | Retrieved | Currency banner | How found |
|---|---|---|---|---|
| | | | | |

---

*Analysis, not legal advice. The requester decides. Nothing here substitutes for the official court
record; verify dates and dockets with CCAP or the Clerk of Courts before relying on them.*
