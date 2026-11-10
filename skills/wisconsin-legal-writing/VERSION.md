# wisconsin-legal-writing

## 2026.11.10.3

- `SKILL.md`: a new section, "Check for a standard court form first", Wis. Stat. § 807.001,
  and `references/court-forms.md`. Instruction text; the builder does not enforce it.
- `references/local-rules.md` and `references/local-rules/counties.json`: an index of where
  five counties were found posting local rules on 2026-11-10, with the other 67 counties
  marked not yet indexed. No rule text.
- `references/standards-of-review.md`: the dated *Kalal* status passage, rechecked 2026-11-10.
- No script, template or input contract changed. Listed in
  docs/LEGAL-TEXT-CHANGES-2026-11.md with sources; no second AI review; not attorney-reviewed.

## 2026.11.10.2

- **Input contract change.** A final build of a motion needs `"document_type": "motion"` or a
  title that opens as a motion, a `motion` object (`movers` by party reference, `qualifier`,
  `relief`, optional `with_notice`), and a title that matches one the builder generates from
  those fields, Wis. Stat. § 802.01(2)(d). See docs/RELEASE-NOTES.md for the migration and the
  limits. It is one supported title form, not a check of statutory compliance.
- A supplied non-null `document_type` must be a nonempty string, for every document. A final
  build whose title is recognized as a notice of motion or hearing must say what it is.
- The complaint and summons refusal recognizes more party-name forms and refuses everything
  it refused before.
- `references/captions.md`: the motion fields. Listed in docs/LEGAL-TEXT-CHANGES-2026-11.md
  with its source and the AI checks; not attorney-reviewed. No template changed.

## 2026.11.10.1

- **Input contract change.** A declaration specification needs `"document_type": "declaration"`
  and a `declaration` object (`use`, `purpose`, `signed_on`, `location`, `state_or_country`,
  `body_reviewed`, optional `not_closings`), and must not type its own closing. The builder
  prints the declaration sentence and execution line of the form in Wis. Stat. § 887.015(6)
  and, on success, says what was not verified. See docs/RELEASE-NOTES.md for the migration.
- `build_filing.py`: a final build is refused on a protected-information number pattern,
  § 801.19 (`--protected-info-reviewed` after checking a match); on a county that is not one
  of the 72 in § 752.11(1) (`--district COUNTY` prints the district); and, in every mode, on a
  complaint or summons, §§ 802.04(1) and 801.09(1).
- `assets/05-declaration.json` and `.docx`: order and wording of the statutory form.
  `assets/10-appellate-brief.docx`: top margin 1 inch, § 809.19(8)(b)3.e. Both rendered in
  Word and recorded in docs/TEMPLATE-QA.md. No other template changed.
- `scripts/wi_values.py`, new: a lookup of dated numbers transcribed from the statutes
  published for 2026-11-04. It does not check the reference files.
- `references/circuit-court.md`, `captions.md`, `checklists.md`: passages on § 801.19, the
  county table, the complaint caption and the declaration fields. Each is listed in
  docs/LEGAL-TEXT-CHANGES-2026-11.md with its source and both AI checks; not attorney-reviewed.

## 2026.11.08.1

- `build_filing.py`: the final-mode placeholder screen now also refuses nonempty single-line
  angle and curly tokens, whole-word TBD, TBA and TK in any case, and whole-word runs of two
  or more X, and lists every offending token with its spec path before any output file is
  opened. A number mask ending in four digits (XXXX1234, XXX-XX-1234 and grouped forms) is
  exempt from the X rule; the exemption is an engineering choice, not a redaction check.
  Draft mode is unchanged. No template was rebuilt; package members are byte-identical.
- `references/voice.md`, section 2: the dated status of Rule Petition 26-02 (proposed SCR
  chapter on generative AI in court proceedings) now records the court's order of October 15,
  2026 granting the motion to withdraw and dismissing the petition, which does not adopt the
  proposed rules, and names petition 26-06 (filed September 28, 2026) as listed but not yet
  scheduled for hearing as checked November 8, 2026. Source-checked by two AI reviewers of
  different model families; not attorney-reviewed; listed in docs/LEGAL-TEXT-CHANGES-2026-11.md.
- SKILL.md and the README describe the wider placeholder screen.

## 2026.11.07.1

- `build_filing.py`: the page-1 clearance band is one header paragraph of exact height
  (2.5 inches for a proposed order, 1.5 inches otherwise, after the 0.5 inch header
  distance) instead of a stack of line breaks whose height depended on the renderer.
  Page 1 body text now starts at exactly 3.0 inches on a proposed order and 2.0 inches
  on other documents; later pages unchanged at 0.95 inch. All 11 JSON-backed templates
  rebuilt; only their header part changed; measured in Word 16.0 and its exported PDF on
  2026-11-07; not attorney-reviewed.
- captions.md and circuit-court.md describe the exact-height band.

## 2026.10.24.2

- Version number only. No file in the skill changed.

## 2026.10.24.1

- `build_filing.py`: pages 2 and later keep the 0.95 inch top margin (the earlier
  release set 0.5 inch); page 1 clearance unchanged; the clearance can no longer be
  switched off after a filed declaration built with it off had the clerk's stamp over
  the county name. All 11 JSON-backed templates rebuilt, rendered in Word 16.0 and
  viewed on 2026-10-24 by an AI lane and independently by a second AI reviewer; not
  attorney-reviewed. 08-motion-for-reconsideration is now 3 pages.
- captions.md records where the court's header and FILED stamp land, measured on two
  October 2026 filings, and says the builder emits the three-rule caption only.
- References: Teff and Koepsell's reporter citations filled from public opinions; the
  La Crosse approval sentence restored from the county clerk's signature page (the
  handwritten day still [VERIFY]); proposed-order margin sentence; appellate.md
  attributes the half-inch top margin to the technical requirements page. Each change is
  listed with its source in docs/LEGAL-TEXT-CHANGES-2026-10.md; source-checked by AI
  review, not attorney-reviewed.
- Compatibility frontmatter added to SKILL.md.

## 2026.10.13.1

- Corrected procedure references found in the 2026-10-11 assessment: small-claims
  amount limits and 2025 Wis. Act 105, judge substitution timing, the two
  frivolous-claim cost procedures, public-records remedies, the status of the
  Herrmann opinion, the reply-brief appendix, the appendix certification excerpt,
  block-quote and footnote spacing, appellate e-filing registration, the eFiling
  filing-day rule, the discovery exclusion in s. 802.05(5), Rule Petition 26-02
  status, and a dated Kalal status note. Each change is listed with its source in the
  repository file docs/LEGAL-TEXT-CHANGES-2026-10.md. They were source-checked by two
  AI reviewers and have not been reviewed by an attorney.
- `assets/10-appellate-brief.docx`: the appendix certification now carries the full
  form of s. 809.19(8g)(b)1., with the cross-reference "s. 809.23(3)(a) or (b)",
  copied from the statute on 2026-10-13. The text was read back; the pages were not
  rendered. The other 13 Word templates are unchanged.
- The worked example and a caption sample use a `[CASE NO.]` placeholder. The La
  Crosse County local-rules note no longer names who approved the rules and marks
  that question [VERIFY].
- `build_filing.py` and `make_templates.py` no longer fail when console output
  contains characters outside the console code page.

## 2026.09.20.2

- Added a completed fictional formatting example preserving words and actual signer.
- Added repository regression coverage for all 11 JSON-backed templates and a
  content-bound record for the inherited visual review of all 14 Word assets.
- Document content and layout are unchanged in this release.

## 2026.09.20.1

- Added a standalone publisher notice identifying the maintainer as a nonlawyer,
  the absence of legal services through the project, and public support boundaries.
- Corrected UPL guidance so actual work and supervision control; removed an
  unsupported enforcement claim and reliance on an unverified secondary guideline.
- Templates and document layout are unchanged by this publication-scope update.

## 2026.09.20

- Corrected appellate routing and deadline guidance, discovery objections and
  response periods, summary-judgment evidence instructions, signature rules, and
  affidavit/declaration distinctions using current primary sources.
- Separated legal requirements from editable typography and voice preferences;
  made court, county, actual signer, supervision, privilege, and verification status
  explicit rather than assumed.
- Added Codex metadata and capability-aware instructions for other LLM hosts.
- Hardened the circuit-court builder: explicit draft mode, input validation,
  overwrite protection, and rejection of appellate use. Added regression coverage.
- Regenerated 11 specification-based templates and revised the three manual Word
  templates. Inspected all 14 rendered documents, including affidavit execution,
  appellate-cover pagination, attorney signatures, headings, and memorandum legends.
- Added a standalone license, pinned builder dependency, portable checksums, and
  repository-wide validation/packaging commands.

These changes do not certify completed documents for filing. Read the repository's
assessment and current official sources for the scope and limits of verification.

## Earlier caption revision

The builder omits the branch line by default and accepts but ignores the legacy
`branch` key. That is a formatting preference: preserve any branch information
required by an applicable form, local rule, or court order. The La Crosse judge
roster remains practice-reference material and must be checked before use.
