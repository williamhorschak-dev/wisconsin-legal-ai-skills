# wisconsin-legal-writing

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
