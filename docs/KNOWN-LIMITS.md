# Known limits of the bundled tools (release 2026.11.10.2)

What the bundled tools do not do, and which earlier defects each release corrected. Update the heading and the
first paragraph at every release. The [README](../README.md) carries a short summary.

These describe the files in release 2026.11.10.2. Release 2026.11.10.2 adds one change: the builder generates the supported titles of a motion from the reviewer's statements of who moves and what is sought, and refuses a final build whose title is not one of them (this changes the motion input contract; see the release notes). Release 2026.11.10.1, published the same day, added seven changes that enforce Wisconsin rules in the tools: a protected-information screen, a county check, a refusal of complaints and summonses, a generated declaration closing (which changes the declaration input contract; see the release notes), a corrected appellate template margin, an unpublished-opinion citation check, and a lookup table of dated values. Six further checks were built, reviewed and not shipped because they could not be made exact; the release notes list them. Release 2026.11.08.1 widened the builder's placeholder screen, rebuilds the source checker so that temporary failures, refusals and changed sources are reported apart, refreshes the source register and updates one dated passage on the AI rule petitions. Release 2026.11.07.1 corrected one layout defect of
the two 2026.10.24 releases: the page-1 clearance band was built from line breaks, so its
height depended on the renderer and a proposed order's gap came out well over 3 inches.
Defects of release 2026.10.13.1 corrected in 2026.10.24.1, all found by a third
independent AI review: a verbatim pass recorded by
hand or through the record command was not checked against the cited locator; a
remembered source could pass checks other than verbatim; an exact match in a version not
in force passed without warning; mistyped locator markers silently turned a marked file
into a whole-file comparison; the memo linter exempted live `[UNVERIFIED]` markers beside
marker prose and let a section after the Red Team Report inherit its no-pincite exemption;
pages 2 and later of built documents had a 0.5 inch top margin; and the page-1 stamp
clearance could be switched off.

- The evidence log is an ordinary file. The tool detects a changed draft or source. It
  does not detect log lines that were deleted or written by hand. `RECORDED PASS` means
  a reviewer entered passing records; it is not an independent certification.
- The builder's non-draft screen catches square-bracketed text, nonempty single-line
  angle/curly tokens, two or more underscores, and case-insensitive whole-word
  `TBD`/`TBA`/`TK` and X runs of two or more. X masks ending in four visible digits
  are allowed, with whitespace, period or common dash separators. It does not infer
  missing facts, catch every placeholder spelling, or perform semantic validation.
- The builder's protected-information screen matches number patterns for the five
  categories in Wis. Stat. § 801.19(1)(a) in the spec text only. It cannot see exhibits,
  does not recognise every account, license or passport format, and can match numbers
  that are not protected information. It is not a redaction check.
- The builder generates one declaration closing, the form in Wis. Stat. § 887.015(6), from the
  reviewer's statements of use, purpose, signing date and place. It does not verify that a
  law permits a sworn declaration for the purpose, that the use is not excluded, that the
  body holds no other closing, or that anyone signed. Its screen for possible closing
  wording can miss a closing and can match an ordinary fact. Other wording is refused as
  unsupported by the tool, not as legally defective.
- The builder generates one supported form of motion title, under Wis. Stat. § 802.01(2)(d),
  from the reviewer's party references, qualifier and relief description. Other lawful
  titles are refused as unsupported. It recognises a motion by English title words, so a
  motion under a title it does not know is not checked unless the specification says it is
  a motion. The same title wording can arise from different facts. It does not verify who
  the parties are, whether the list of movers is complete, or whether the description is
  legally adequate.
- The builder refuses a complaint or a summons by the opening words of the title or the
  declared type. A complaint under an unusual title is not recognised. The county check
  knows the 72 county names; it does not decide venue or where an appeal is heard.
- The county local-rules index (`references/local-rules.md`) records where five counties were
  checked on one day and what each posted document printed about itself. It holds no rule
  text, does not say what any rule requires, does not confirm that a posted set is complete
  or current, and does not notice when a county replaces a file. Sixty-seven counties are
  not yet indexed. One check was incomplete and one linked document was not read.
- The unpublished-opinion check in the citation tool applies Wis. Stat. § 809.23(3) to
  facts the reviewer records. It does not read the opinion and does not find unpublished
  opinions the inventory fails to mark.
- In two templates a section symbol can be separated from its number by a line break.
- The subsequent history of cited authorities was not checked exhaustively against public
  sources where only the original opinion was read.
- `wi_values.py` is a lookup transcribed from the statutes published for the date it
  records and read on a later date it also records. It refuses earlier dates. A later-date
  answer applies that publication's schedule only, not a survey of what was enacted
  afterwards. It does not check that the reference files state the same numbers, and it
  does not decide which rule governs or which claims a changed amount first applies to.
- Two items in the procedure references remain marked [VERIFY]: how 2025 Wis. Act 105
  applies to a claim made before January 1, 2027 in an action commenced after it, and the
  signing date of the 2025 La Crosse County local rules.
- Version detection in the citation tool is phrase matching on the reviewer's own
  annotation; it has no model of which text is in force on a given date.

## Keeping it current

Wisconsin law changes by Act, court order, and decision. Statements stored in the
reference files carry the date they were checked and can be out of date. The
[source register](legal-sources.json) lists twelve topics, what was checked, and
when; six records are inherited from an earlier review, four are pending primary review and two are
focused checks, and it does not yet cover every chapter the skills discuss or watch for enacted changes with later
effective dates.

An AI-assisted accuracy check of the stored legal references on 2026-10-11 (not a legal
review and not by an attorney) found stored statements that needed correction, including
judicial substitution timing and public-records remedy subsections. Release 2026.10.13.1
contains the corrections, and release 2026.10.24.1 adds reporter citations and a restored
local-rule attribution found by a third review. AI reviewers checked them against public
sources; no attorney has reviewed them. Each one is listed with its source in
[LEGAL-TEXT-CHANGES-2026-10.md](LEGAL-TEXT-CHANGES-2026-10.md). The check also
found that the Wisconsin Supreme Court had accepted review of whether to modify the
*Kalal* interpretive framework in *Abby Windows, LLC v. Labor & Industry Review
Commission*, No. 2024AP1013, and that the case is scheduled
for oral argument on November 10, 2026. Monetary limits in the references, including the
small-claims limit, are affected by 2025 Wis. Act 105, which takes effect on
January 1, 2027 (Act section 5). The small-claims passage now carries a dated note about
it. Do not rely on any amount, deadline, or rule in a reference file without
reading the current primary text and its effective-date note.
