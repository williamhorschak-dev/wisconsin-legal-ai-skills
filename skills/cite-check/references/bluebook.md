# Output Formatting — The Bluebook Layer

Verified is not the same as correctly formatted. This file governs how citations *look*
in the output. Default style: **Bluebook practitioner conventions (the B "Bluepages"
rules)**, yielding to the forum's own citation rule wherever one exists. SCR 80.02(1)
governs the citation of published court of appeals and supreme court opinions in the
table of cases in a brief and the initial citation in a memorandum or other document
filed with the court of appeals or the supreme court. Outside that express scope,
this skill recommends the public-domain form as a drafting default (project policy,
not a statewide rule), subject to any applicable rule or court order. Formatting failures are
`FLAG: FORMAT` in the report: they never block a substantive `VERIFIED`, and they never
ship silently.
<!-- DRAFT FOR LEGAL REVIEW (2026-10-12), L-007: SCR 80.02(1), https://www.wicourts.gov/sc/rules/chap80.pdf, read 2026-10-12. The drafting default outside that scope is project policy. -->

A humility note, in the spirit of the rest of this skill: this file states the
conventions at the confidence they deserve from a style memory. Where a formatting
question is contested, unusual, or load-bearing (a local rule dictates format), check the
current Bluebook or the forum's rule during the run — the forum's rule always wins.

## Italics

- **Italicize case names** — full cites, short forms (*Harlow*), and *id.* (including
  the period). Underlining is the accepted equivalent in court documents: use whichever
  the draft already uses, and never mix the two in one document.
- Italicize procedural phrases: *In re*, *Ex parte*, *ex rel.*, *et al.* when part of
  the name as cited.
- Italicize signals in citation sentences: *See*, *See also*, *Cf.*, *E.g.*,
  *Accord*, *Contra*, *But see*.
- Do **not** italicize the rest of the citation: reporter, volume, pages, court, year,
  statutory material.

## Case citations and years

**Every full case citation carries the decision year — except where the citation format
already encodes it.**

- U.S. Supreme Court: *Harlow v. Fitzgerald*, 457 U.S. 800, 818 (1982) — no court
  abbreviation; the reporter implies it.
- Federal courts of appeals: *Caption*, 897 F.3d 847, 852 (7th Cir. 2018).
- Federal district: *Caption*, 500 F. Supp. 3d 800, 805 (W.D. Wis. 2020).
- Wisconsin, public-domain era (2000–): `20XX WI NN` (Supreme Court) or `20XX WI App NN`
  (Court of Appeals), then ¶ pincite, then parallel cites:
  *Caption*, 20XX WI App NN, ¶ NN, VVV Wis. 2d PPP, NNN N.W.2d PPP.
  **The year and court are already the first two elements — do not append a duplicate
  (Wis. Ct. App. 20XX) parenthetical.** (The patterns here are deliberately synthetic
  placeholders; build from the real cite, and note the Supreme Court form has no "App.")
- Wisconsin, pre-public-domain: *Caption*, VVV Wis. 2d PPP, PPP, NNN N.W.2d PPP (Ct.
  App. 19XX) / (19XX) for the Supreme Court — year required.
- Unpublished Wisconsin (when citable at all — see `references/verification.md`):
  *Caption*, No. 20XXAPXXXX, unpublished slip op. (Wis. Ct. App. Mon. D, 20XX) — full
  date, never an invented public-domain number.
- Recent U.S. Supreme Court without final pagination: *Caption*, 60X U.S. ___, ___
  (20XX) (slip op., at NN).

**Subsequent history** is appended when the convention requires it (*aff'd*, *rev'd*,
*cert. denied* per current Bluebook practice) and must match what Check 4's screen
actually found.

## Statutes and regulations — the vintage parenthetical

**The governing principle: when the work concerns past events,
go by the law of that time — and make the citation say so.** The date parenthetical must
match the *archived copy's* vintage (`vintage:` / `updated_through:` in the file header),
never a guess.

- Wisconsin: cite the edition retrieved and relevant to the event. For example,
  Wis. Stat. § 425.109 (2023–24); do not assume that edition is current in a later run.
- Wisconsin historical: cite and archive the edition in force at the operative time —
  Wis. Stat. § 425.109 (2019–20) for 2020 conduct — and flag in the report that a
  non-current vintage is being relied on and why.
- Amended language: where the cited language changed between the operative time and now,
  say so in text or parenthetical ((amended 20XX)); the history notes in the archived
  copy are the evidence.
- Federal statutes: 15 U.S.C. § 1692e for current law (edition year optional under
  modern practice); relying on a *past* version requires the vintage — the U.S.C.
  edition/supplement of that time, or the Statutes at Large (91 Stat. 874 form) — and
  remember Title 15's positive-law caveat in `references/sources.md`.
- Regulations: 12 C.F.R. § 1006.34 (2024) — year of the annual edition when citing
  historical text; current text may omit the year where the context is clearly current
  law.
- Wisconsin session laws: 20XX Wis. Act NN; federal: Pub. L. No. 119-NN, 139 Stat. NNN.

## Short forms

- **`id.`** — only when the immediately preceding citation contains a single authority;
  *id.* alone for the same locator, *id.* at 819 (or *id.*, ¶ 24) for a different one.
  Capitalized (*Id.*) at the start of a citation sentence.
- **Case short form** — *Harlow*, 457 U.S. at 818; Wisconsin public-domain: *Caption*,
  20XX WI App NN, ¶ 25. Use a distinctive party name (not a common litigant like
  *State* or *United States*).
- **Statute short form** — § 425.109 after a full cite, where the chapter is unambiguous.
- **`supra`** is for secondary materials and briefs, not cases or statutes.
- Every short form still resolves to its antecedent and carries its own pincite check —
  formatting correctness does not exempt it from `references/verification.md`.

## Quoting chains and parentheticals

- Preserve `(quoting *Original*, cite)` / `(citing …)` chains per Check 1's attribution
  rule; the chain is part of the citation and gets verified like the rest.
- Explanatory parentheticals: present participle, no closing period inside unless the
  parenthetical quotes a full sentence ("holding that …") — and whatever a parenthetical
  *asserts* about the case is a proposition for Check 5.
- *(emphasis added)*, *(cleaned up)*, *(alteration in original)* follow Check 1's rules;
  the format layer only ensures they are present, placed after the pincite, and
  italicized per convention.

## Record cites

Follow the forum's rule (Wisconsin appellate: the form required by the current Rules of
Appellate Procedure — verify during an appellate run; federal district: the judge's
standing order often controls). Be consistent within a document; Check 6 verifies the
substance.
