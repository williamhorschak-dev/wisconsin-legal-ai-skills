# Legal skills repository assessment and improvements

Reviewed September 20, 2026. Baseline: the original 65-file skill library, archived by the maintainer before this repository was recreated with a fresh history.

## Overall assessment

This is a substantial legal-workflow library with useful source discipline, Wisconsin-specific reasoning, realistic drafting material, and a valuable distinction between legal analysis and document production. It deserves continued development. The original version should not have been treated as a reliable filing-production system unchanged: several procedural instructions were wrong or too broad, some promised verification had no executable implementation, and the builder could overwrite an existing document.

The revised version is a stronger candidate for supervised research and drafting. The important work was correcting shared legal guidance and making verification claims accurate. Adding a GPT label alone would have carried the original defects into another product.

Claude and Codex can now use the same canonical skill folders. Other LLM applications can use selective prompt exports and task-specific references. This is **instruction and packaging portability**, not a claim that every LLM or product was tested, and it does not extend Wisconsin legal guidance to other jurisdictions.

## Scope and method

- Reviewed the three skills, their instructions and references, original Python helpers, 11 JSON specifications, and all 14 Word templates. The baseline repository contains 65 tracked files.
- Independently reviewed the writing guidance, interpretation guidance/linter, and helper behavior. Used synthetic fixtures and realistic instruction-following walkthroughs, without real matter data.
- Checked the consequential legal corrections against official Wisconsin statutes, opinions, court rules, and filing instructions. Sources and exact limits appear below.
- Added and ran regression tests, metadata/link/license/checksum validation, packaging checks, and static security review. Rendered all 14 Word templates through Microsoft Word and visually inspected their 32 pages; revised affected pages after finding defects.
- Reviewed changes in a separate checkout. This assessment does not report filing, service, legal-database access, or a production deployment.

The full law library was read for consistency and risk, but this was **not** a complete citator audit of every authority, verification of every historical quotation, or review of every county rule and judge-specific order.

## Strengths preserved

1. **Evidence before confidence.** Primary-source copies, exact operative text, pincites, actual treatment checks, and explicit uncertainty are sound foundations.
2. **Wisconsin-specific method.** The interpretation skill uses Wisconsin authority and distinguishes neutral analysis, competing arguments, and a prediction.
3. **Useful separation of tasks.** Citation checking, legal interpretation, and drafting remain separate skills with conditional handoffs. A simple lookup need not become a formal memorandum.
4. **Practical document coverage.** The templates and references cover motions, responses, discovery, affidavits/declarations, proposed orders, letters, appellate briefs, and memoranda.
5. **Attention to the signer.** The revised instructions preserve supplied facts, authorized scope, actual role, and the user's voice while retaining a coherent default style.

## Confirmed legal-content findings

P1 denotes a material risk of giving the wrong procedural or legal direction. P2 denotes a consequential qualification, unsupported assurance, or execution risk. P3 denotes maintenance or usability. Priorities describe the original defect; the corrections below are implemented.

### Wisconsin legal writing

Paths in this table are under `skills/wisconsin-legal-writing/`.

| Priority | Original issue | Implemented correction | Source |
|---|---|---|---|
| P1 | `references/appellate.md` and `checklists.md` routed initiating appellate documents incorrectly and omitted the self-represented docketing-statement exemption. | Route the notice, required docketing statement, and transcript statement through the circuit-court workflow; check track, service, fee, and transmission obligations. | [Rules 809.10–.11](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf); [official eFiling FAQ](https://www.wicourts.gov/ecourts/efileappellate/faq.htm) |
| P1 | `circuit-court.md` gave a 14-day cross-appeal period and the wrong subdivision. | Use the later of the otherwise applicable appeal period or 30 days after notice of appeal is filed, under Rule 809.10(2)(b). | [Chapter 809](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf) |
| P1 | `appellate.md` treated essentially all other appellate deadlines as extendable. | Identify nonextendable reconsideration and petition-for-review deadlines and track-specific exceptions under Rule 809.82(2); account for timely reconsideration when applicable. | [Chapter 809](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf) |
| P1 | Discovery references and templates required a protective-order motion whenever a party objected rather than answered. | Distinguish timely specific objections expressly permitted by §§804.08/.09 from total failure to answer or object under §804.12(4). Update the response and motion-to-compel specifications. | [Chapter 804](https://docs.legis.wisconsin.gov/statutes/statutes/804.pdf) |
| P1 | `responding.md` used literal day-31/day-46 admissions language, limited the defendant's 45-day protection to requests accompanying a summons, and oversimplified answer periods. | Calculate the actual adjusted deadline; preserve the summons-service protection; distinguish answer-period categories and the applicable discovery stay. | [Chapters 801](https://docs.legis.wisconsin.gov/statutes/statutes/801.pdf), [802](https://docs.legis.wisconsin.gov/statutes/statutes/802.pdf), and [804](https://docs.legis.wisconsin.gov/statutes/statutes/804.pdf) |
| P2 | Service additions were stated without consistently identifying the event that starts the deadline. | Require the trigger, method/time of service, counting rule, holidays, and controlling order. Preserve the correct mailed-motion-notice rule; do not add service days to an entry-based appeal clock merely because a notice was mailed. | [§801.15](https://docs.legis.wisconsin.gov/statutes/statutes/801.pdf); [*Strook*, 2009 WI App 31, ¶26 n.8](https://www.wicourts.gov/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo=35567) |
| P2 | Paper signatures and electronic signatures were conflated; discovery guidance assumed two different signers even for one self-represented respondent. | Distinguish paper and eFiled signature requirements and use the actual answerer, party, entity representative, or attorney required for the document. | [§801.18](https://docs.legis.wisconsin.gov/statutes/statutes/801.pdf); [§802.05](https://docs.legis.wisconsin.gov/statutes/statutes/802.pdf); [§804.08](https://docs.legis.wisconsin.gov/statutes/statutes/804.pdf) |
| P2 | Summary-judgment instructions imported an obsolete sworn/certified-copy requirement and over-required one evidence form. | Explain the permitted evidentiary materials, movant's burden, papers already of record, and §802.08(4) relief when facts cannot yet be presented. | [§802.08](https://docs.legis.wisconsin.gov/statutes/statutes/802.pdf) |
| P2 | The reconsideration specification implied a one-year deadline for every §806.07 ground. | Distinguish the reasonable-time requirement, the one-year limit for (1)(a)/(c), and §805.16 for (1)(b). | [§806.07](https://docs.legis.wisconsin.gov/statutes/statutes/806.pdf) |
| P2 | A generic affidavit was offered for every procedure excluded from the declaration statute. Its affiant signature followed the jurat and venue followed the litigation county. | Explain specialized execution requirements; move affiant execution before the jurat; use the actual place of execution. | [§887.015](https://docs.legis.wisconsin.gov/statutes/statutes/887.pdf) |
| P2 | The appellate brief skeleton omitted requirements in Rule 809.19(1)(g)–(i). | Add protected-identity conventions, signatures, actual lawyer-drafting-assistance disclosure, and party-name usage. AI assistance alone is not lawyer assistance. | [Rule 809.19](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf) |
| P2 | Exact caption geometry, no-branch formatting, font, italics, and some voice formulas were treated as universal legal requirements. | Label preferences as defaults; preserve compliant alternatives and any governing court form, rule, or order. Distinguish circuit practice from appellate requirements. | [§802.04](https://docs.legis.wisconsin.gov/statutes/statutes/802.pdf); [Rule 809.19](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf) |
| P2 | An arbitrary argument limit, preservation shorthand, and a claim that circuit courts never review decisions could distort the analysis. | Preserve necessary alternative and developed preservation arguments; recognize circuit judicial review and applicable standards. | [Rule 809.19(2)(a)](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf); reviewed drafting instructions |
| P2 | Memo text implied privilege, attorney supervision, or completed adversarial verification without establishing those facts. | Make legends conditional, identify the actual role and audience, and state only checks performed. Correct the Word template and repeated-page headers. | [SCR ch.23](https://www.wicourts.gov/sc/scrule/DisplayDocument.pdf?content=pdf&seqNo=692090); [SCR 20:5.3](https://www.wicourts.gov/sc/scrule/DisplayDocument.pdf?content=pdf&seqNo=1121033); original template text |
| P3 | The jury-instruction route pointed to a nonexistent section. | Add a current official-catalog route and instruction-specific checks; distinguish Civil 2418A from 2418B. | [Official civil jury instructions](https://wilawlibrary.gov/jury/civil/) |
| P3 | Templates silently assumed La Crosse County, fixed signing years, or a particular party role. | Use explicit county/year/placeholders and actual-role instructions; remove fictional street details from the manual templates. | Inspection of all JSON and DOCX assets |

**Deadline calibration:** the original eight-day mailed-motion-notice rule was not itself wrong. *Strook* applies the mail addition and short-period counting exclusions. The correction avoids turning that rule into eight calendar days or making service additions universal.

The independent writing review also completed 12 manual walkthroughs: appeal initiation, cross-appeal, reconsideration enlargement, admissions received after summons, pro se interrogatory objections, privilege objections versus total nonresponse, mailed hearing notice, summary-judgment evidence, specialized affidavit procedures, another county/party role, a memo without attorney review, and an AI-assisted appellate brief. These were instruction evaluations against primary sources, not separate Claude/GPT product benchmarks.

### Wisconsin legal interpretation

Paths in this table are under `skills/wisconsin-legal-interpretation/`.

| Priority | Original issue | Implemented correction | Source |
|---|---|---|---|
| P1 | `authority-hierarchy.md` applied Wisconsin's unpublished Court of Appeals restriction to unpublished federal opinions. | Separate the source jurisdiction and governing citation rule; do not suppress potentially usable persuasive federal or out-of-state authority. | [*Predick*, 2003 WI App 46, ¶12 n.7](https://www.wicourts.gov/html/ca/02/02-0503.htm) |
| P1 | Agency-authority guidance suggested a broad grant was necessarily inadequate under §227.10(2m). | Explain that an explicit grant can be broad; distinguish explicit authority from narrowly specific authority. | [*Clean Wisconsin*, 2021 WI 71, ¶¶24–25](https://www.wicourts.gov/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo=386188) |
| P2 | Unpublished-opinion guidance treated per curiam exclusion as an inference and misstated the July 1, 2009 boundary. | State the express exclusions and “on or after” boundary; remove a fabricated interpretive dispute from the example memo. | [Rule adoption order 08-02](https://www.wicourts.gov/sc/rulhear/DisplayDocument.pdf?content=pdf&seqNo=35116); [current chapter 809](https://docs.legis.wisconsin.gov/statutes/statutes/809.pdf) |
| P2 | A fragmented-opinion discussion generalized one case's disposition. | Read the actual mandate and proposition-specific votes; narrow the *Lynch* example and retain an explicit unverified marker for other unverified discussion. | [*Lynch*, 2016 WI 66, opening mandate/n.1](https://www.wicourts.gov/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo=171644) |
| P2 | Enacted construction directives appeared both among intrinsic sources and among rules deferred until ambiguity. | Treat an enacted directive as intrinsic text within its scope; distinguish generic remedial maxims and verify their actual use under controlling Wisconsin authority. | [*SEIU*, 2025 WI 29, ¶¶8, 10–12](https://www.wicourts.gov/sc/order/DisplayDocImage.pdf?docId=977376) |
| P2 | Blanket overlay instructions could override current user authorization; unavailable tools could become a reason to withhold useful bounded work. | Honor actual authorization, relevance, confidentiality, and host permissions. Provide accurately labeled partial work without claiming unavailable verification. | Instruction consistency review |
| P3 | Equal-length opposing arguments encouraged artificial balance. | Require the strongest supported alternative, without inventing a dispute or imposing equal length. | Instruction/example consistency review |

The review also verified the specific *Brekke*, 2026 WI 29, ¶20 passage against the [official opinion](https://www.wicourts.gov/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo=1143901). This is passage verification, not a complete treatment audit. The current procedural status of *Abby Windows* remains a fresh-check item; a historical grant is not labeled as a current docket status.

## Software, evidence, and security improvements

| Area | Original problem or gap | Implemented behavior |
|---|---|---|
| Citation verification | Instructions required a script-generated log/report, but the repository supplied no citation-checking script. | New standard-library helper inventories declared citation uses, appends evidence records to an ordinary local log (deleted or hand-edited lines are not detected), conservatively matches straightforward text quotations, and generates per-use reports. Manual inventory and legal judgment remain necessary. |
| Evidence integrity | A polished report could obscure missing or stale support. | Bind evidence to draft/source SHA-256 hashes and the canonical-JSON inventory hash, recheck them, reject duplicate checks, and require evidence text/locator/source for passes. Changing an inventory cannot reuse an old log. Reject quotations that normalize to empty text. Missing logs or checks remain unverified. A completed report says `RECORDED PASS`, accurately describing attestations. |
| Source confinement | New tooling needed safe archive paths. | Reject traversal, absolute/device paths, and symlink escapes; use source-root-relative paths. Preserve reports rather than overwrite them. Document a single writer per evidence-log run. |
| Citator claims | A name or an LLM assertion could be mistaken for an actual check. | Require a nonempty named service for a case-treatment pass, and explain that the program cannot authenticate the attestation. Free cited-by searches remain cautionary evidence, not a substitute citator result. |
| Filing output | Builder overwrote existing files and accepted an appellate court label when the appellate flag was omitted. | Explicit output path, exclusive creation by default, intentional `--overwrite`, and circuit-court-only enforcement. Serialize before creating the output file. |
| Builder validation | Invalid types could crash late; incomplete specs were presented too confidently. | Validate caption/body/signer types, booleans and spacing; distinguish `--draft`; reject unresolved placeholders for ordinary builds; require actual supplied execution details. The checks are conservative, not a complete legal validator. |
| Template execution | Affidavit placement, an overlong appellate cover, a broken attorney signature line, and orphan headings impaired usability. | Rebuild the 11 JSON-backed templates, revise the three manual templates, keep headings with their content, fit the appellate cover to one page, and repair signature/jurat placement. |
| Memo linter | Source filenames with spaces produced false missing-file errors. | Separate safety-screen fragments from complete existence-check candidates; retain path-containment checks. |
| Memo linter | No-citator disclosure elsewhere in the body passed formal lint without disclosure in the decision sections. | Require disclosure in both the Short Answer and Retrieval Record for the relevant formal case. |
| Memo linter | A corrected historical FATAL quotation containing “unresolved” was treated as a live unresolved failure. | Preserve the required historical quote and check the current correction narrative separately. Live unresolved FATAL findings still fail. |
| Maintainability | Duplicated legal exposition, a writing entrypoint over 500 lines, missing standalone licenses, and no regression suite/CI. | Shorter routed entrypoints, per-skill MIT licenses and metadata, 45 regression tests (the count when this row was written; later releases add tests), maintenance instructions, and a Windows/Linux Python 3.10/3.12 CI matrix. |
| Packaging | No shared build/validation/export process; cross-platform ordering and line endings could invalidate hashes. | Validate frontmatter, local links, licenses and manifests; fixed POSIX-string ordering, LF source/license bytes, fixed ZIP metadata, and complete skill packages. Selective prompt exports preserve one source of legal text. |

The source ladder now distinguishes the officially maintained eCFR from a third-party reproduction and allows its available point-in-time history, while identifying when another official publication is required. See the [eCFR historical guide](https://www.ecfr.gov/reader-aids/using-ecfr/ecfr-changes-through-time) and [National Archives explanation](https://www.archives.gov/federal-register/tutorial/text). Database access instructions respect actual entitlements and existing authorized sessions rather than assuming a product-specific tool or blanket license restriction.

The static skill-security scan found no critical finding. Its one high-severity match was a false positive: a `sys.exit` error string explains how to install the declared dependency; the builder does not execute package installation. Manual review found no runtime credential collection or network/exfiltration routine in the production helpers. DOCX inspection found no macros, embedded executable objects, or external relationships in the reviewed templates. This is not a vulnerability-database audit or a guarantee against malicious inputs.

## Portability assessment

| Target | Delivered support | Practical limit |
|---|---|---|
| Claude Code | Native skill-folder layout and documented `.claude/skills` installation. | Actual tool access and permissions depend on the host. |
| Claude skill upload | One complete ZIP per skill. | Account/import support must be available; uploading text does not install a Python runtime. |
| Codex | Native `.agents/skills` layout, valid shared frontmatter, optional `agents/openai.yaml` display metadata and `$skill-name` invocation. | Installation must preserve any existing skill of the same name. |
| ChatGPT/custom GPTs | Selective Markdown prompt exports; instructions for supplying entrypoints and needed references. | Instruction fields, attached knowledge, browsing, and code execution differ by product/account. Unseen references cannot be assumed read. |
| Other LLM/API applications | Vendor-neutral workflow, explicit capability fallback, selectable references and scripts. | The application must provide retrieval, tools and storage. Model behavior still needs evaluation on that deployment. |

Paths and format were checked against [Claude's official skills documentation](https://code.claude.com/docs/en/skills), [OpenAI's build-skills documentation](https://learn.chatgpt.com/docs/build-skills), and the [Agent Skills specification](https://agentskills.io/specification). Full installation/export commands and the capability matrix are in [PORTABILITY.md](PORTABILITY.md).

No extra vendor-specific legal copies are needed. Keep one canonical skill per workflow, then adapt only the host metadata or execution layer. If an existing installation contains another Wisconsin drafting or artifact skill, select the intended role explicitly and resolve trigger overlap before activating duplicates.

## Validation results and interpretation

The release-candidate checks are reproducible from the repository root:

```sh
python -m pip install -r requirements-dev.txt
python scripts/skill_tools.py validate
python -m unittest discover -s tests -v
python scripts/skill_tools.py package --out dist/skills
```

- **45 automated tests:** filing-builder input/output behavior; citation evidence, draft/source/inventory hashing, normalized-empty quotations, incompleteness and path safety; formal-memo regressions; complete, deterministic packaging and selective exports. On the local Windows runtime, two symlink tests require a privilege unavailable to that process and are reported as skips; hosted CI exercises those cases.
- **Memo regression evidence:** the 10-test memo suite exposed five failing assertions before fixes and passed after fixes. Valid source paths with spaces and corrected historical findings now pass; missing archives, inappropriate high confidence, omitted disclosure and live FATAL findings remain rejected.
- **All 14 Word templates / 32 pages:** visually inspected after rendering. The canonical LibreOffice renderer was unavailable on this machine, so a hidden Microsoft Word instance exported PDFs for inspection. No claim is made about every renderer or a court's acceptance of completed documents.
- **Metadata/package checks:** each skill's entrypoint, optional Codex metadata, local links, independent license and exact file hashes are checked. Packages preserve all references, assets and scripts. A manifest detects changed bytes; it is not a cryptographic publisher signature.
- **CI:** the added workflow runs the same validation, tests and package build on Windows and Linux with Python 3.10/3.12. The pull request's current checks are the authoritative record of hosted run status.

The local Python runtime was CPython 3.12.14 with `python-docx` 1.2.0 and PyYAML 6.0.3. Dependency versions are declared and pinned for this build. Existing outputs, stale evidence, source escapes, and accidental appellate use have explicit regression coverage.

## Publication-scope update

The maintainer confirmed that he is a nonlawyer publishing tools only. Added a
prominent no-legal-services notice, standalone notices in all three skills,
technical-only issue guidance, and notice retention in packages and prompt
exports. Corrected UPL wording that could overstate the effect of labels or
supervision. Two additional packaging/export regressions bring the suite to
47 tests at that point in the 2026-09-20 assessment; later releases add tests. See [the source review and limits](PUBLICATION-SCOPE-2026-09-20.md).
These changes do not constitute a professional opinion that all uses comply with
UPL rules. Earlier template and source checks above retain their stated scope.

## Remaining limits and next maintenance priorities

1. **Complete the legal checks for the actual matter.** No source archive or automated test establishes that every reference remains current. Recheck statutes, treatment, local rules, standing orders, deadlines and the record for the work being delivered. No KeyCite or Shepard's review was performed for this repository assessment.
2. **Treat labels as claims requiring evidence.** Citation inventory coverage is manually reviewed. Source matching does not prove proposition support, and a structural memo linter cannot establish that research or adversarial review occurred. An actor can supply an inaccurate attestation; these tools do not solve that trust problem.
3. **Evaluate each intended LLM deployment.** Before routine reliance, use representative tasks with known expected sources, citation traps, missing tools, altered drafts, malicious instructions inside source material, and actual document rendering. This review did not run end-to-end tasks inside every named product or measure model accuracy rates.
4. **Keep rendered templates tied to their sources.** Eleven templates are rebuildable from JSON; the letter, appellate brief and memo are separately maintained Word assets. Update and inspect affected assets together. Real names, long captions and completed text can change pagination.
5. **Refresh law deliberately.** The official statutory PDFs checked in this review carry the publication currency “updated through 2025 Wis. Act 247 and orders effective September 4, 2026.” That source date does not certify every development after September 4. The focused Trempealeau rule check and La Crosse source discovery do not constitute a complete current local-rule audit.
6. **Keep the library focused.** Preserve the current three-workflow separation; avoid auto-installing overlapping skills, loading the entire legal library into every prompt, or adding more mandatory gates unrelated to the user's task. Expand to other jurisdictions only with separately sourced jurisdiction-specific references and evaluations.

The resulting repository is more usable, testable and portable, with concrete defects repaired. Its appropriate role is an evidence-conscious research and drafting aid whose legal conclusions and finished documents receive the checks required by the actual task.
