# 2026.10.24.1

Fixes from a third independent AI review (two passes on the 2026.10.13.1 bundle by a
Google model and a third pass on the pull request by a Codex model), and a file-stamp
placement fix the maintainer reported from two filed documents. The legal-text rows were
source-checked by AI review against public sources. No attorney reviewed any of it; the
maintainer is not a lawyer; LEGAL_NOTICE.md applies.

## cite-check

- A verbatim pass against a .txt or .md source, whether recorded by the quote command,
  written by hand, or found in the log when the report runs, must sit in the segment
  marked for the cited locator; a cited locator that matches no marker is refused. The
  earlier release checked only the quote command's own entries.
- No check of any type can pass from remembered text. The earlier release refused only a
  remembered verbatim pass.
- An exact match in a file whose version line says the text is not in force or is a prior
  version is recorded as caution with the reason. A legacy exact-text record without a
  label gets the same rule. The phrase check ignores spacing and is documented as phrase
  matching, not an operative-date model.
- The report says when the tool did not read a file: "archived file present and its hash
  matched when this report ran; contents not compared by the tool".
- Marker lines are parsed with optional spacing and any case, a line that starts like a
  marker but does not parse is refused, spacing inside a locator is ignored, and a
  quotation longer than its segment is classified instead of raising an error.
- references/source-behavior.md now ships inside the skill as a byte-identical copy of the
  interpretation skill's file; compatibility frontmatter added; the description says what
  the skill is not for; evidence-tool.md documents the Markdown, parent-segment and
  version-phrase limits; PORTABILITY.md covers hosts whose code sandbox has no network.

## wisconsin-legal-writing

- Pages 2 and later keep the documented 0.95 inch top margin. The earlier release set
  them to 0.5 inch, under the court's header band. Page 1 clearance is unchanged. All 11
  JSON-backed templates were rebuilt, rendered in Word 16.0 and viewed by an AI lane, and
  independently rebuilt, rendered and measured by the third reviewer; the review record
  says so and claims no attorney review. 08-motion-for-reconsideration is now 3 pages.
- The page-1 stamp clearance can no longer be switched off. A filed declaration built with
  it off had the clerk's FILED stamp printed over the county name of its caption.
  captions.md records where the court's header and stamp land, measured on two October
  2026 circuit court filings, with the technical requirements and statutes quoted.
- captions.md and worked-example.md say the builder emits the three-rule caption only;
  the attorney-table caption is a manual step.
- References: Teff and Koepsell's reporter citations filled from public opinions; the
  La Crosse approval sentence restored from the county clerk's signature page, with the
  handwritten day still marked [VERIFY]; the proposed-order sentence separates the
  half-inch header band from the builder's 0.95 inch margin; appellate.md attributes the
  half-inch top margin to the appellate technical requirements page rather than to
  s. 809.801(8)(h), which gives the 2 by 2 inch square only; the Koepsell's source note
  cites the published Bauer v. Wisconsin Energy Corp., 2022 WI 11. Each change is in
  docs/LEGAL-TEXT-CHANGES-2026-10.md with its source.

## wisconsin-legal-interpretation

- check_memo.py counts an [UNVERIFIED] marker unless the token is used as a noun in a
  statement about the marker ("no [UNVERIFIED] marker remains", "[UNVERIFIED] markers:
  none"). A live marker beside marker prose, a rule-file name or clause punctuation is
  counted; a parenthetical inside a clearance sentence is not a false error. The Red Team
  Report's no-pincite exemption ends at the next heading of its own level, and a corrected
  block in a memo without a report exempts only itself.
- Guarnero reporter citation filled; source-behavior.md entry 2 states the "Prior to
  [date] it reads:" rule in words; SKILL.md says Mode 1 quick lookups are in scope;
  memo-format.md says headings are # headings; compatibility frontmatter added.

## Repository

- Tests 132 to 145; the CI matrix is unchanged (Ubuntu and Windows, Python 3.10 and 3.12).
- Reviewer claims checked against public sources and not adopted: a La Crosse rule
  renumbering (the official PDF, page 8, numbers settlement authority 505, continuances
  507 and the consumer credit checklist 508, as the references have them), a wrong N.W.2d
  page for Teff, and a wicourts link for State v. Johnson that opened a different case.
- The assessment's public record of all three reviews is kept outside the repository by
  the maintainer; docs/reviews holds nothing new in this release.

## Known issues carried forward

- Subsequent history of cited authorities was not exhaustively checked against public
  sources.
- The Kalal status sentence must be rechecked after 2026-11-10; the small-claims passage
  must be re-edited on 2027-01-01.
- The evidence log does not detect deleted lines. Hand-edited pass lines are now
  re-checked against the archive when the report runs.
- Version detection in cite_check.py is phrase matching on the reviewer's annotation; it
  has no operative-date model, and a phrase outside its list is not recognised.
- The trigger queries have never been run on a host that records skill activation.
- Two items remain marked [VERIFY]: how 2025 Wis. Act 105 applies to a claim made before
  January 1, 2027 in an action commenced after it, and the signing date of the 2025
  La Crosse County local rules.

The three skills remain independently usable. These changes do not certify legal
accuracy, filing readiness, or the permissibility of a particular legal-service
deployment.

# 2026.10.13.1

Corrections from an AI-assisted assessment run on 2026-10-11, with the legal-text
corrections source-checked by two AI reviewers on 2026-10-12 and 2026-10-13. No
attorney reviewed any of it; the maintainer is not a lawyer; LEGAL_NOTICE.md applies.

## Wisconsin procedure references corrected (all three skills)

- Small claims: the § 799.01(1)(c) and (d) limits are $10,000 until 2027-01-01 and
  $15,000 from that date under 2025 Wis. Act 105, with its initial-applicability
  rule quoted; the categories in (a), (am), (b) and (cm) and the $5,000 category
  (cr) are stated with their own conditions; covered Consumer Act replevin proceeds
  under ch. 799 regardless of the value of the goods (§ 425.205(1)). The earlier
  text gave the wrong pinpoint and a wrong replevin rule.
- Judge substitution: § 801.58(1) timing restated from the statute, including its
  60-day limits, and from State v. Matthews, 2021 WI 42 (the preliminary
  contested matter condition turns on the judge in fact hearing a substantive issue
  going to the merits); small-claims timing under § 799.205(1) and (4) stated with
  its own post-appeal trigger.
- Frivolous-claim costs: § 895.044(2) and § 802.05(3)(a)1 described as separate
  procedures; the "21-day gift" wording removed.
- Public records: § 19.37 remedies each carry their statutory condition (mandamus;
  fees and minimum damages for prevailing requesters in § 19.35(1)(a) actions, with
  the committed-or-incarcerated exception; actual damages in § 19.35(1)(am) actions
  only where the authority acted in a willful or intentional manner; punitive
  damages; forfeiture enforced by the attorney general or a district attorney). The
  earlier text swapped two subsections.
- Kalal status: a dated sentence drawn from SEIU Healthcare Wisconsin v. WERC,
  2025 WI 29 (unanimous opinion applied Kalal; four justices joined a separate
  writing) and the clerk's pending-case table (Abby Windows v. LIRC scheduled for
  argument 2026-11-10), with an instruction to check the case's status before
  relying on the framework.
- Tetra Tech ¶ 108 cited as majority text and ¶ 78 as lead-opinion reasoning;
  Herrmann labelled a lead opinion with Miller v. Carroll, 2020 WI 56, ¶¶ 23-24 as
  the later majority standard; chapter 227 scope kept separate from municipal
  certiorari (Grycowski, 2021 WI App 7).
- Appellate: reply-brief appendix rule; the § 809.19(8g)(b)1 certification with the
  correct "809.23(3)(a) or (b)" cross-reference (an abridged excerpt in the
  reference file, the full form in the hand-maintained DOCX template); single
  spacing for proportional-serif block quotes and footnotes; and the § 809.801(3)(a)
  to (c) e-filing categories.
- Smaller: SCR 80.02(1) scope (cite-check); petition 26-02 status as checked
  2026-10-12 (withdrawal letter on the docket, no order); § 801.18(4)(am)
  filing-day rule; § 802.05(5) discovery exclusion; Secord reporter citation;
  § 809.23 permalink; additions on League of Women Voters v. Evers and on
  State v. Jensen and Mitchell v. Buesgen; a [SKILL RULE] marker that separates
  project policy from law; [CASE NO.] placeholders in the worked example and a
  caption sample.
- Three items are marked [VERIFY] in the procedure references: how Act 105 applies
  to a claim made before 2027-01-01 in an action commenced after it; who approved
  the 2025 La Crosse County local rules; and the signing date of those rules, which
  was already marked. The provenance of the worked example is left to the
  maintainer in a source comment, and subsequent history was not checked
  exhaustively for authorities where only the original opinion was read.
- Every change is listed with its old text, new text, source and pinpoint in
  docs/LEGAL-TEXT-CHANGES-2026-10.md.

## cite-check

- A manual verbatim pass is refused when the quotation is absent from a text
  source; quote matching requires word boundaries ("30 days" no longer matches
  "130 days"); the report distinguishes tool-compared, tool-confirmed-present and
  reviewer-attested records; the evidence log is described as an ordinary local
  file.
- Quote labels VERIFIED, QUOTE_ALTERED (with a word diff), MISATTRIBUTED (exact
  text found elsewhere in the run's archive, including a not-yet-in-force amended
  version) and UNRESOLVED; only VERIFIED supports a pass.
- Provenance per evidence entry (retrieved this session, user supplied,
  remembered; a remembered verbatim pass is refused) and a per-source,
  per-authority "Sources reachable" table.
- A deprecated path call replaced ahead of Python 3.15.

## wisconsin-legal-writing

- The appendix certification in 10-appellate-brief.docx now carries the full
  § 809.19(8g)(b)1 form, copied from the statute on 2026-10-13. The text was read
  back with python-docx; the pages were not rendered. The other 13 Word templates
  are unchanged.
- build_filing.py and make_templates.py tolerate console output characters outside
  the console code page.

## wisconsin-legal-interpretation

- check_memo.py no longer exempts an [UNVERIFIED] marker because a negation word is
  nearby; a non-UTF-8 memo exits 2 with a message.
- New references/source-behavior.md: 13 observed behaviours of
  docs.legis.wisconsin.gov, wicourts.gov and related sites that mislead automated
  readers, each dated.

## Repository

- Freshness fields in docs/legal-sources.json and scripts/check_sources.py with a
  monthly, report-only workflow. The register now has 11 records, two of them new
  and pending primary review.
- Trigger evaluations: 20 hand-written queries per skill and an offline scorer; no
  results recorded yet.
- evaluate.py rejects malformed rubric items; build_release.py packages the
  evaluation suite from Git's file list, so ignored files are not shipped; stdout
  tolerates non-console characters.
- README rewritten against the assessment's evidence; CITATION.cff; technical issue
  template; CONTRIBUTING revised; two skill descriptions tightened; README names
  GitHub private vulnerability reporting as the security channel.
- Tests 67 to 132. The CI matrix is unchanged (Ubuntu and Windows, Python 3.10 and
  3.12); CI now also runs the trigger-query validator.

## Evaluation (exploratory)

12 fresh cases (Wisconsin law or synthetic fixtures, not the repository's
24-scenario suite), one repetition, answered by one model with no skill (A) and with
the 2026.09.20.2 skill text pasted in (B), 24 responses in all. Two AI scorers rated
each response against a sealed oracle with condition labels hidden: agreement on
the primary score in 23 of 24 responses; pooled supported task completion (0 to 3)
2.04 without the skill and 2.58 with it; no protocol-critical errors in either
condition. Blinding failed on content: both scorers identified the condition of all
24 responses. One response differs between the scorers by 2 points on a secondary
dimension and has not been reconciled. This is not a legal-accuracy measurement
and was not run on this release.

## Known issues carried forward

- Subsequent history of cited authorities was not exhaustively checked against
  public sources.
- The Kalal status sentence must be rechecked after 2026-11-10; the small-claims
  passage must be re-edited on 2027-01-01.
- The evidence log does not detect deleted or hand-edited lines.

The three skills remain independently usable. These changes do not certify legal
accuracy, filing readiness, or the permissibility of a particular legal-service
deployment.

# 2026.09.20.2

- Preserve valid citation logs that end without a newline; add original-source
  provenance fields without invalidating legacy records.
- Accept UTF-8 memo files with a byte-order mark while retaining structural checks.
- Align interpretation templates and references on enacted construction directives
  and extrinsic confirmation. Historical date and analytical depth are now separate.
- Add five named prompt profiles, exact included-file hashes, version/commit
  provenance, and a completed synthetic example for each skill.
- Add 24 synthetic model-evaluation scenarios, paired baseline/skill inputs,
  raw-response collection/import, and hash-bound review summaries.
- Add legal-source maintenance records and review reminders; distinguish inherited
  checks from newly reviewed passages and pending work.
- Rebuild all 11 JSON templates in regression tests and bind all 14 existing Word
  assets to their inherited visual-review record. Document the rendering procedure.
- Publish complete release assets with checksums and upload CI build artifacts.

The three skills remain independently usable. No Word template content or layout
was changed in this release. Model-provider evaluations are **not yet run**; see
TESTED-COMPATIBILITY.md. These changes do not certify legal accuracy, filing
readiness, or the permissibility of a particular legal-service deployment.
