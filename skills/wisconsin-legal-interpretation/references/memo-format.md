# Output Format — Memo, Authority Table, Red Team Report

**This file describes the Mode 3 deliverable.** Three artifacts: the memo carries the analysis,
the authority table carries the proof, the red team report carries the attack. They are separate
on purpose — folding the red team into the analysis is how its findings get softened.

**Modes 1 and 2 do not produce these artifacts and should not imitate them.** A Mode 1 lookup
delivers the five items in SKILL.md's Mode 1 list and nothing else. A Mode 2 answer delivers the
sequence, both readings, the prediction, and the compact adversarial check, in prose, with no
files. What all three modes share is the *substance* below: verbatim quotations with pincites,
`[UNVERIFIED]` on anything not retrieved this session, and a confidence that reflects what was
actually verified. **Chat answers get pasted into filings; treat every one as future filing
text.**

---

## 1. The three lenses

The heart of the format. Each lens is labeled and lives in its own section. Never blend them.

**Lens 1 — What the law is (neutral).** Written as though for a judge who will read the same
sources. No characterization, no "clearly," no adjectives doing argumentative work. Where the law
is unsettled, the section says it is unsettled rather than picking a side quietly. If this
section were handed to the opponent, they should find nothing to dispute in its description of
the authorities — only in what follows from them.

**Lens 2 — How each side argues it (advocate, both directions).** Two subsections, each built at
full strength:

- **Our best reading** — the strongest version of the requester's position, with its best
  authority and its most useful text.
- **Their best reading** — the strongest version of the opposing position, written as an
  opponent's counsel would write it, not as a strawman. Give it the space its support needs;
  equal length is not required. If the text or controlling authority forecloses a contrary
  reading, say so rather than inventing a balanced dispute.

Where the requester's position is not yet fixed, or where the work is neutral research with no
side, write both as "Reading A" and "Reading B" and let the prediction lens sort them.

**Lens 3 — How a Wisconsin court likely rules (prediction).** A forecast, stated as a forecast,
with reasons:

- The likely outcome, in a sentence.
- Which lens-2 argument prevails and **why** — which specific feature of the text, the framework,
  or the precedent does the work.
- The **standard of review**, named and quoted, and what it does to the odds.
- Court-specific reality where it is known and relevant: what this forum, this judge, or the
  supreme court's current composition has done with this kind of question. Label it
  `[INFERENCE]` with its inputs named. Never dress up a hunch as authority.
- What would change the prediction: a fact, a document, a decision in a pending case.
- The confidence grade from `red-team.md` §4, and who assigned it.

---

## 2. Memo structure

```markdown
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
citator_notes: <free text; flags and what they mean, or the §3 substitutes actually run>
red_team: <full | compact | none>
fatal_findings: <integer; 0 if the pass found none>
confidence: <HIGH | MODERATE | LOW | UNRESOLVED>
tags: [legal, research, wisconsin]
---

# <Question, as a question>

## Question Presented
One sentence. Names the text, the actor, the conduct, and the date.

## Short Answer
Three sentences at most. The answer, the reason, the confidence grade. A reader who stops
here should not be misled by having stopped here.

## Governing Text
Every operative provision, quoted verbatim in the version in force at the operative date,
with the currency banner and the source file path. This section is text, not argument.

## Lens 1 — What the Law Is
Neutral statement. Runs the canons.md § 8 sequence in its stated order — all intrinsic sources
before the plain-meaning call — showing each step, including the
empty ones.

## Lens 2 — How Each Side Argues It
### Our best reading
### Their best reading

## Lens 3 — How a Wisconsin Court Likely Rules
Prediction, reasons, standard of review, what would change it, confidence.

## Application
Element by element. Each element: the text, quoted; the facts; the fit; what is missing.

## Open Questions and What Would Resolve Them
Specific. "Need the ordinance as adopted 2019-03-12 from the county clerk" beats
"further research needed."

## Authority Table
See §3.

## Red Team Report
See §4. Reproduced in full, unedited.

## Retrieval Record
Every source: file path, origin URL, retrieval date, currency banner, how found.

---
*Analysis, not legal advice. The requester decides. Nothing here substitutes for the
official court record; verify dates and dockets with CCAP or the Clerk of Courts before
relying on them.*
```

---

## 3. Authority table

One row per authority, plus the full classification block from `authority-hierarchy.md` §8 for
anything the argument stands on.

| # | Citation | Cited for | Binding? | Citable? | Vintage OK? | Copy | How found | Evidence |
|---|---|---|---|---|---|---|---|---|
| 1 | Kalal, 2004 WI 58, ¶46 | Context is part of plain meaning | Binding (Wis.) | Published | n/a | `sources/opinions/2004-WI-58 - Kalal.pdf` | search-for-proposition | ¶46, quote at p.19 |

Rules:

- **An empty Evidence cell with a "verified" row is a contradiction.** The evidence cell must
  contain a file and a locator that could only exist if the work happened.
- **Copy to file** — every unpublished Wisconsin opinion (§ 809.23(3)(c)) and every federal
  nonprecedential disposition where the local rule requires it, listed so none is forgotten at
  filing.
- **Vintage OK** — for statutes and rules, whether the version quoted is the version in force at
  the operative date. For cases, whether the text the case construed matches the text in force
  now. Blank is not an answer.
- Anything not retrieved carries `[UNVERIFIED]` in the row and is called out in the Short Answer
  if the conclusion leans on it.

---

## 4. Red team report

Reproduced in the memo **in full and unedited**, as its own section, in this order:

```markdown
## Red Team Report

Run: <independent agent | in-session pass> on <date>
Attacks run: 1-7 <or: which, and why any was skipped>
Checks not run: <named check — named reason>

### Findings
<schema from red-team.md §3, most severe first. "No findings" is a valid result and is
stated with the list of what was checked.>

### Best contrary reading, at full strength
<Attack 4's output, preserved even where it was answered. A reader should be able to see
what the opposition looks like without reconstructing it.>

### Confidence: <GRADE>
<Why this grade and not the one above it.>
```

If a FATAL finding was found and fixed, the report says so and notes that a second pass ran.
Reproduce the corrected finding **unedited**, under a heading that names it as corrected
(“Corrected on the second pass”), and set `fatal_findings: 0` — it is no longer outstanding
— with `fatal_findings_first_pass:` recording that the first pass was not clean. That shape is
what `check_memo.py` recognizes. Use `#` headings throughout: the checker does not read
underlined (Setext) headings as section or block boundaries. Record the correction and the second-pass result outside the
quotation; historical words such as "unresolved" remain unchanged inside it. The linter checks
the declared counts, not whether the correction actually happened. A
clean report on the second pass is not the same artifact as a clean report on the first, and the
reader is entitled to know which one they are reading.

---

## 5. Where files go

- Memo: the matter's working folder, named `Research - <question> - <YYYY-MM-DD>.md`. If a
  private overlay is loaded (`sources.md` § 9) and it names a destination, use that; otherwise
  ask once where the matter's files
  live; if there is nobody to ask, write beside the `sources/` archive and say where you put
  it.
- Sources: the matter's `sources/` tree per `sources.md` § 8. **Source citations are relative to
  the archive root.** The linter rejects traversal, UNC, and system or credential paths outright
  and warns on any other absolute or home-relative path — a transcript of a command actually run
  is the one place an absolute path is defensible, and it still draws the warning.
- Frontmatter: nine mandatory keys, and the linter rejects a memo missing any of them —
  `type`, `status`, `updated`, `operative_date`, `framework_checked`, `citator`, `red_team`,
  `fatal_findings`, `confidence` — plus `citator_date` and `citator_signal` whenever `citator`
  is not `NONE`. The full block is in § 2 above. If an overlay defines additional required keys,
  add them. Metadata in frontmatter, never inline.
- **If an overlay distinguishes a low-sensitivity index tier from a matter tier, a research memo
  is matter-tier content and does not go in the index tier.**

---

## 6. Hand-offs

Every hand-off below is **conditional on the skill existing in this environment**. Check first;
if it is not available, say so and deliver the memo as the finished product rather than promising
a step that will not happen.

- **To a citation-verification skill, if available** — when the memo's authorities will be used
  in anything filed, served, or sent. Use the same archive layout so the second run picks up
  where this one stopped. Say explicitly that the memo's retrieval record is **not** a
  cite-check report; the two do different jobs.
- **To a Wisconsin legal-drafting skill, if available** — when the answer becomes a motion,
  brief, letter, or appellate brief. Carry the verbatim quotations across intact; do not
  re-summarize them into the draft from memory, which is where quote drift starts.
- **When passing material from a private overlay to another agent or skill, prefer the cited
  excerpts** — the quoted passage, file name, and pincite. Broader context requires an authorized
  scope and a task need, subject to host, tool, and confidentiality restrictions (`sources.md` § 9).
- **Back to the requester** — anything marked `[FILL-IN]`, any FATAL finding, any question
  sitting on the practice-of-law line, any authority whose citator status is `NOT RUN`
  (`sources.md` § 4), and the license question in `sources.md` § 2.3 the first time an
  authenticated academic or institutional license is used in a client matter.
