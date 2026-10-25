# Source Ladder — Where to Get Primary Sources

Work down each ladder in order; stop at the first source that yields a usable copy — full
text, plus the pagination scheme any pincite check needs, plus the correct **version
vintage** for statutes and regulations. Record origin URL and retrieval date for every
file. When two copies disagree, the more official controls and the disagreement goes in
the report.

**URL rot rule:** if a ladder URL 404s or redirects, navigate from the site's root —
prefer another official or reliable primary-text source when needed; the ladder is not exhaustive — and record the
changed URL in the report.

This skill's default practice area is Wisconsin state courts plus the federal courts sitting in Wisconsin
(W.D. Wis., 7th Circuit). Those ladders come first; the general principles cover
everything else.

## Official sources vs. verification copies

- **Official**: the courts' own sites (wicourts.gov, WSCCA, supremecourt.gov,
  ca7.uscourts.gov), docs.legis.wisconsin.gov, govinfo.gov, uscode.house.gov, PACER.
- **Acceptable verification copies (unofficial reprints of primary text)**:
  CourtListener/RECAP, Justia, Cornell LII (locator-grade), Lexis/Westlaw
  (editorially reliable, still unofficial for most reporters).

The eCFR is maintained by the Office of the Federal Register and GPO but is an
unofficial editorial compilation, distinct from a third-party reprint.

Either kind can verify a check; the report records which copy verified what. When a check
is outcome-determinative or copies disagree, escalate to the official version.

## Quick map

| Authority | First stop | Watch for |
|---|---|---|
| Wis. Supreme Ct. / Ct. App. opinions | wicourts.gov opinions pages; WSCCA | official PDFs carry the ¶ numbers |
| Wisconsin appellate briefs | WSCCA briefs / document search | coverage starts ~July 1, 2009; see limits below |
| Wisconsin circuit dockets | WCCA (aka CCAP) | docket facts, not document text |
| Wisconsin circuit filings | matter's case-file archive; eFiling; Clerk | WCCA rarely has the PDF |
| Wisconsin statutes / rules / admin code | docs.legis.wisconsin.gov | capture the currency banner + NOTES |
| U.S. Supreme Court | supremecourt.gov; CourtListener; Justia | slip → preliminary print → bound; pagination shifts |
| Federal cts. of appeals / district | CourtListener (MCP if connected); govinfo USCOURTS | USCOURTS = slip pagination only |
| Federal briefs / filings | RECAP via CourtListener; PACER | PACER discipline below |
| U.S. Code | uscode.house.gov; govinfo | positive-law caveat below |
| C.F.R. / Fed. Reg. | govinfo (annual editions); eCFR point-in-time | verify coverage and the operative date |
| Paywalled-only needs | Nexis Uni (Lexis) → Westlaw | license warning below |

## Wisconsin

### Appellate opinions

1. **wicourts.gov** — Supreme Court at `wicourts.gov/opinions/supreme.jsp`, Court of
   Appeals at `wicourts.gov/opinions/appeals.jsp`. Official slip PDFs with the paragraph
   numbers Wisconsin pincites use — the verification copy of choice.
2. **WSCCA** (`wscca.wicourts.gov`) — appellate docket history, opinions, briefs; also
   where the live status of a pending appeal is verified.
3. **CourtListener / Justia** — usable text mirrors of published Wisconsin opinions for
   verbatim checks; prefer the official PDF when a ¶ pincite must be verified.
4. **Nexis Uni / Westlaw** — pre-public-domain-era cases where only reporter star paging
   (`Wis. 2d` / `N.W.2d`) can verify a pincite.

### Appellate briefs

**WSCCA's brief collection has edges — know them before hunting:**

- eFiled briefs from filings **on or after July 1, 2009** (plus scanned briefs from cases
  decided after that point) are there as free PDFs.
- Generally **not** there: appendices, petitions for review, briefs in confidential case
  types, and sealed or restricted documents.
- Pre-2009 briefs (roughly Nov. 1992 – June 2009): the **UW Law Library's Wisconsin
  Briefs collection**; older still, or anything missing: the **Wisconsin State Law
  Library** (`wilawlibrary.gov`) document services or the Clerk of the appellate courts.

### Circuit court records

- **WCCA / CCAP** (`wcca.wicourts.gov`) — party names, docket entries, charges,
  dispositions, deadlines. **Most filed documents are not downloadable here.** WCCA
  verifies *docket facts* — what was filed, when, current status — not document text.
- Filings themselves: the matter's own case-file archive first (the user's own archive of
  filed PDFs), then the eFiling portal for the user's cases, then the Clerk of Courts (fees;
  certified copies also originate there).
- A saved WCCA screen capture (URL + date, into `sources/`) is fine as *the run's working
  verification of a docket fact*. It is **not** proof of the record for a court — WCCA is
  not the official record; the clerk's file is. Anything a judge must rely on comes from
  the clerk, certified when required.

### Statutes, rules, administrative code

- **docs.legis.wisconsin.gov** — official. Statutes, court rules (including ch. 809
  appellate procedure), administrative code, session laws (Wisconsin Acts), and archives
  of prior biennial editions.
- **Currency is continuous, not biennial.** Wisconsin statutes change by Act throughout
  the biennium; the printed biennial volume is an *edition*, not a version. The site
  states what the text is "updated through" — **copy that banner verbatim into the
  `.md` header** (`updated_through:`), and read the section's **NOTES**: a NOTE can flag
  an amendment the base text does not yet show.
- For how these sites display currency lines, versions not yet in effect, permalinks,
  release dates and access limits, read [source-behavior.md](source-behavior.md) in
  this skill's references folder (a copy of the interpretation skill's file).
- **Vintage rule** (it governs): when the draft concerns past conduct,
  acquire and cite the version **in force at the operative time**, from the archived
  editions, and say so in the report. The archived copy in `sources/statutes/` must *be*
  that vintage; the citation's date parenthetical (see `references/bluebook.md`) must
  match the archived copy.
- Copy the full section — history notes included — never a fragment.
- SCR (Supreme Court Rules) and Wisconsin Jury Instructions: via wicourts.gov and the
  State Law Library.

## Federal

### Opinions

1. **CourtListener** (`courtlistener.com`) — first stop, especially with a CourtListener
   MCP connected: `search` to find the case, `read_document` for text. Note:
   `extract_citations` / `analyze_citations` belong to the *inventory and existence
   check* (see `references/verification.md`), not to good-law screening. Many copies
   carry star pagination usable for pincites.
2. **govinfo.gov USCOURTS** — authenticated PDFs of federal opinions, but: **selected
   courts, roughly 2004 forward, not comprehensive — and slip pagination only, so it
   cannot verify an `F.3d` / `F. Supp. 3d` reporter pincite.** Use it for text; use a
   star-paged copy for reporter pincites.
3. **supremecourt.gov** — slip opinions. The sequence is slip opinion → preliminary
   print → bound U.S. Reports volume, and pagination can shift between stages; record
   which stage verified the pincite. A case without final U.S. Reports pagination is
   pincited to the slip opinion (`603 U.S. ___, ___ (2024) (slip op., at 12)`) — never
   an invented page number.
4. **Justia** — clean HTML; its U.S. Supreme Court pages preserve U.S. Reports
   pagination.
5. **ca7.uscourts.gov** — 7th Circuit opinions and oral-argument audio.
6. **Nexis Uni / Westlaw** — when only reporter star paging can verify the pincite, or
   coverage runs out.

### Briefs, dockets, filings

- **RECAP (via CourtListener)** — free mirror of PACER documents; check it first, always.
- **PACER** — discipline, because fees are real and a pro se user pays them personally:
  - As a **party**, the user gets one free look at each document in the user's own cases when
    the NEF/NDA email arrives — those downloads should come from the user's own saved copies first.
  - Fees: per-page with a per-document cap (search results are *not* capped), and a
    quarterly waiver threshold under which fees are forgiven — verify current amounts at
    pacer.uscourts.gov before spending.
  - **No PACER purchase without per-document approval from the user**; log every purchase
    and its fee in the report. After a purchase, the RECAP browser extension (if
    installed) contributes the document back to the free mirror.

### Statutes, regulations, rules

- **uscode.house.gov** (OLRC) — the U.S. Code. **Positive-law caveat: titles not enacted
  into positive law — including Title 15, where the FDCPA lives — are only *prima facie*
  evidence of the law; the Statutes at Large control if they differ.** When exact
  statutory wording is load-bearing or contested, verify against the Statutes at Large
  on govinfo (for the FDCPA: Pub. L. 95-109, 91 Stat. 874, as amended). Capture the
  site's "current through Pub. L. …" banner into the `.md` header.
- **govinfo.gov** — U.S. Code editions, Statutes at Large, C.F.R. **annual editions**
  (the path to any *historical* C.F.R. version), Federal Register.
- **eCFR** (`ecfr.gov`) — an unofficial, continuously updated compilation with a
  point-in-time system generally covering dates from January 3, 2017 onward. Use the
  selected-date view for historical research within its coverage, record that date,
  and inspect source notes and Federal Register amendments/effective dates. For older
  dates or an official edition, use govinfo annual CFR editions and intervening rules.
  The annual edition's revision date may differ from the event date.
  Source: [OFR point-in-time guide](https://www.ecfr.gov/reader-aids/using-ecfr/ecfr-changes-through-time),
  checked September 20, 2026.
- **Cornell LII** — locator-grade; verify anything load-bearing on an official copy.
- Federal rules (FRCP / FRAP / FRE): current official PDFs via uscourts.gov.

## Nexis Uni and Westlaw — the authenticated tier

Use when free primary sources cannot supply the text, pagination, or citator a check
needs. Mechanics of the login handoff are in SKILL.md; two things live here:

**Access terms.** Check the actual vendor and institutional terms applicable to the
account and task. Academic services differ in permitted uses; this repository cannot
determine a particular subscription's license. Reuse an authorized logged-in session;
if the permitted use is uncertain, identify the uncertainty and use public sources for
work that can proceed. Do not treat user consent as a license the account does not have.
Do not buy access, bulk-export, or change account settings without authorization.

For a citator check, record the signal, relevant negative treatment, search date, and
whether that treatment affects the proposition at issue. A signal alone is not a
holding analysis. Stop on an access challenge and let the user handle authentication.

## What is never a primary source

Headnotes, syllabi, key numbers, editor's summaries, annotations, A.L.R. write-ups,
Wikipedia, blog posts, practice guides, law-review descriptions, Google snippets,
AI-generated summaries (including this AI's own memory), and citation strings copied from
other briefs. Any of these may *locate* authority; none of them *is* authority. Even the
Supreme Court's own syllabus is "no part of the opinion of the Court." *United States v.
Detroit Timber & Lumber Co.*, 200 U.S. 321, 337 (1906) — and per this skill's own rules,
verify that citation against a downloaded copy before repeating it in a filing.

## Metadata header for `.md` source copies

```yaml
---
authority: Harlow v. Fitzgerald
citation: 457 U.S. 800 (1982)
source: CourtListener            # who supplied this copy
url: https://www.courtlistener.com/opinion/...
retrieved: 2026-08-22
pagination: star pages preserved as [*805] markers   # or "none — pincites unverifiable from this copy"
updated_through: ""              # statutes/regs: the site's currency banner, verbatim
vintage: current                 # or the operative-time version this copy represents
---
```

The `pagination` and `updated_through` fields are required honesty: a copy's limitations
are data the checks depend on.
