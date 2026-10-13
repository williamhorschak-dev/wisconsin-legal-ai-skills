# Sources — Acquisition, Ladder, and the Ways It Fails

The prime rule of this skill is that nothing is law until it has been retrieved. That makes
acquisition the load-bearing step, and acquisition is where runs quietly break. This file is the
ladder, the access protocols, the citator rule, and a catalogue of failure modes to expect.

**Capability neutrality.** This skill runs in more than one environment. Nothing here assumes a
particular assistant, tool name, model, or operating system. Where a capability is named, it is
named as a *class* — "a full-text case retrieval tool," "a page-fetching tool," "a local shell" —
and the run is expected to check what actually exists before relying on it. If a class of
capability is absent, say so and fall back down the ladder. Never simulate a capability you do
not have.

---

## 1. The ladder

Climb from the top. Stop at the first rung that produces the actual text with reliable
pagination. Record which rung produced it.

**Rung 1 — Official Wisconsin government sources.** These are the citable, authoritative text.

| Material | Source |
|---|---|
| Wisconsin Statutes and Annotations | `docs.legis.wisconsin.gov/statutes/statutes/<ch>/<sec>` |
| Wisconsin Administrative Code | `docs.legis.wisconsin.gov/code/admin_code/...` |
| Wisconsin Acts (session laws) | `docs.legis.wisconsin.gov/<year>/related/acts/...` |
| Bill drafting files, LRB analyses, Legislative Council notes | `docs.legis.wisconsin.gov` bill history pages |
| Wisconsin Attorney General opinions | `docs.legis.wisconsin.gov/misc/oag/` |
| Supreme Court and Court of Appeals opinions | `wicourts.gov/sc/opinion/...`, `wicourts.gov/ca/opinion/...`; older opinions by case number, e.g. `wicourts.gov/sc/opinions/02/pdf/02-2490.pdf` |
| Appellate docket, briefs, filings | WSCCA — `wscca.wicourts.gov` |
| Circuit court dockets | CCAP / Wisconsin Circuit Court Access — `wcca.wicourts.gov` |
| Supreme Court Rules, court forms, eFiling technical requirements | `wicourts.gov` |
| County / municipal ordinances | The municipality's own site first; third-party code publishers second, and only with a currency date |

**A local convenience copy of frequently used chapters**, if the user keeps one, does not
change the ladder: it is faster than a fresh fetch for *finding* a provision, but the live
docs.legis page is still what gets quoted and cited, per Rule 1 of this skill.

**Rung 2 — Free primary aggregators.** Use for full text when an official source is unreachable,
and to search across opinions.

- **A full-text case-law retrieval capability**, if the environment has one — an API client or
  connector for a free case-law corpus (CourtListener and the Caselaw Access Project are the usual
  ones) is the best free way to pull paragraph-level text without a summarization cap, and to run
  a literal phrase search inside a known opinion. Check whether such a capability exists before
  planning a run around it; if it does, note any rate limit it reports and budget accordingly.
- **Justia** (`law.justia.com/codes/wisconsin/...`) — reliable, fetchable statutory text. **Not
  official**: use it to read and to draft, then confirm the operative language against
  docs.legis before it enters a filing, and never take its currency on faith.
  **For a past-date question, this is also the free route to a prior edition:** the year-scoped
  pattern `law.justia.com/codes/wisconsin/<year>/chapter-<N>/section-<N-N>/` returns that year's
  edition, and a superseded page carries a banner saying a newer version exists — capture that
  banner verbatim in the source file header, because it is what dates the text. An edition is
  still not a version (see `canons.md` § 2.4); confirm against the amending Act.
- Google Scholar, casetext mirrors, vLex previews — last resort, and never as the cited source.

**Rung 3 — Authenticated databases.** Whatever the user actually has. See §2.

**Rung 4 — Secondary.** Wisconsin Practice Series, State Bar CLE books, *Wisconsin Lawyer*,
WisBar, law reviews, practitioner blogs. Useful to **find** authority and to understand a
landscape. Never cited as the authority for a proposition, and never quoted in place of the text
it describes. A secondary source that says a statute means X is a lead, not a holding.

---

## 2. Authenticated databases

### 2.1 Availability

Do not assume any authenticated database is available, and do not assume any is not. **In Mode 2
or Mode 3, ask once at the start of a run that needs one** which of Westlaw, Lexis / Nexis Uni,
Fastcase / vLex, or a bar-association research benefit the user can reach today. Record the
answer for the run and do not re-ask within the same matter.

**Never ask in Mode 1.** A quick lookup has one answer and opening it with a database interview
is the failure the mode exists to prevent. If a Mode 1 lookup turns out to need a citator, that
is itself a reason to escalate and say so.

**If there is nobody to ask** — a scheduled run, a subagent, any unattended context — do not
block and do not guess upward. Proceed as though no authenticated database is available, run the
§ 3 substitutes, record `citator: NONE`, apply the § 4 confidence cap, and say in the output
that the database question could not be put to anyone. That is a complete, honest run. Waiting on
an unanswerable question is not.

Availability changes — a student subscription starts or lapses, a firm adds or drops a plan. This
file therefore states no availability dates and no subscription facts. Anything of that kind
belongs in the private overlay described in §9, or in the answer to the question above.

### 2.2 The login protocol — non-negotiable

1. Navigate the browser to the sign-in page and **stop**.
2. Ask the user to complete the login personally, including any institutional SSO and any
   two-factor step.
3. **Never** ask for, accept, read, store, or type credentials or one-time codes, even if
   offered. If credentials appear in the conversation, do not use them; ask the user to log in at
   the browser.
4. After the user confirms, work at a human pace. Search, open, Shepardize or KeyCite, download
   what the question needs. No bulk downloading, no settings changes, no saved searches, no
   crawling.
5. On any CAPTCHA, unusual-activity interstitial, or rate-limit notice: **stop and hand the
   browser back.** Never solve, bypass, or retry through one.

### 2.3 The license question

Academic and student database licenses are commonly limited to academic use, and using one for
commercial or client legal work may violate the subscription agreement. **This is the user's call
to make, not the skill's.** Before the first use of an academic or institutional license in a
billable or client matter, raise it once, in one sentence, and let the user decide. Do not raise
it again in the same matter, and do not use it as a reason to refuse research the user has asked
for.

### 2.4 What the authenticated databases are actually for

Not "better search." Specifically:

- **Citator** — Shepard's or KeyCite. There is no free equivalent that reliably surfaces negative
  history, and "no negative history found" from a free source is not a citator result. See §4.
- **Unpublished and unreported decisions** not on free sources.
- **Superseded statutory text** — the version in force on a past date, which docs.legis exposes
  only awkwardly.
- **Wisconsin-specific secondary sources** to find authority faster.

---

## 3. Checking good law without a citator

When no citator is available, run these and say in the memo that this is what was run:

1. **Cited-by search.** Search a case-law corpus for the citation, sorted by date, to see what
   has cited it since. Read the most recent citing cases for treatment.
2. **Statutory vintage comparison.** Pull the statutory text the case construed and the text in
   force at your operative date and diff them. A case construing repealed or amended language is
   the most common form of silently-dead authority, and no citator flag is needed to catch it.
3. **Supreme court check.** For a published court of appeals decision, check whether the supreme
   court has granted review, withdrawn language, or decided a case in tension — remembering
   *Cook*: only the supreme court can withdraw the language.
4. **Legislative override check.** Search the Acts for amendments to the construed section after
   the decision date.

Recorded in the memo's frontmatter as `citator: NONE` with the substitutes named in
`citator_notes:` — for example `cited-by, vintage comparison, and review check run 2026-01-15`.
That is an honest record. "Still good law" with nothing behind it is not.

---

## 4. The citator rule for outcome-determinative work

**When an authority is outcome-determinative for anything that will be filed, served, sent to a
client, or relied on to meet a deadline, current negative treatment must be checked through an
authorized citator — or the absence of that check must be disclosed on the face of the work and
the stated confidence capped accordingly.**

An authority is outcome-determinative when the conclusion changes if that authority is bad law.
If you are unsure whether it is, treat it as if it is.

**The claim is recorded as fields, not as a sentence.** A free-text citator line cannot be
checked, and a linter that tries to check one by pattern-matching prose both misses the evasions
and accuses honest authors. So the memo declares four things in its frontmatter, three of them
constrained tokens the linter validates, and puts every word of narrative in the fourth:

```yaml
citator: KeyCite            # exactly one of: KeyCite | Shepards | NONE
citator_date: YYYY-MM-DD    # a real ISO date, not in the future; required unless NONE
citator_signal: none        # none | yellow | red | other; required unless NONE
citator_notes: >-           # free text, never parsed — flags, what they mean, substitutes run
  Clean on all five authorities; one yellow flag on a case not relied on.
```

The red team's two fields work the same way:

```yaml
red_team: full              # full | compact | none — nothing else, no commentary
fatal_findings: 0           # plain integer: FATAL findings still OUTSTANDING
fatal_findings_first_pass: 1  # optional; FATAL findings the first pass found and you fixed
```

A FATAL finding that was found and corrected is **no longer outstanding**, so `fatal_findings`
is 0 and `fatal_findings_first_pass` records that the first pass was not clean. Reproduce the
corrected finding unedited under a heading naming it as corrected — "Corrected on the second
pass" — which is what tells both the reader and the linter which artifact they are holding.

No commentary belongs in `citator:` itself. "KeyCite not run", "Shepard's-equivalent",
"KeyCite (0 results, account lapsed)" are all rejected — write `citator: NONE` and explain in
`citator_notes:`.

Three permissible outcomes, and no fourth:

| Outcome | Fields | Confidence cap |
|---|---|---|
| Citator run, clean | `citator: KeyCite\|Shepards` + `citator_date` + `citator_signal: none` | none — normal calibration |
| Citator run, flagged | same, with `citator_signal: yellow\|red\|other`, and the flag discussed in the memo | a **red** signal cannot carry `confidence: HIGH` — resolve the flag first; yellow can, if the memo says why it does not bite |
| No citator available | `citator: NONE` + `citator_notes` naming the § 3 substitutes actually performed, **and the words "not Shepardized or KeyCited" in the memo's own voice** | **cap at "likely"** — never "settled," "clearly," or "will"; the linter refuses `confidence: HIGH` |

Rules that follow from it:

- **The disclosure is not a footnote.** It appears in both the **Short Answer** and the
  **Retrieval Record**. Formal lint checks those sections separately; a disclosure elsewhere
  does not satisfy either placement requirement.
- **A free-source result is not a citator result.** A cited-by list, an absence of later
  citations, and a search that returned nothing are §3 substitutes. Reporting any of them as a
  citator check is a FATAL defect.
- **The cap is on the stated confidence, not on the analysis.** Do the full analysis; state the
  conclusion at the confidence the verification actually supports.
- **A stale check ages into a missing one.** `check_memo.py` warns at six months, and refuses
  `confidence: HIGH` on a citator result more than a year old — a year-old result and no result
  are the same fact about negative treatment since. Re-run it
  sooner than that on a fast-moving question, on one where a petition for review is pending, or
  wherever an intervening decision is plausible — and if it is not re-run, say in the memo how
  old the check is rather than letting the date sit unremarked in a field.
- **Keep status truthful.** The user may request a draft without a citator. Disclose that
  omission and its effect on confidence; do not call the result a completed formal pass.

---

## 5. Wisconsin legislative history — where it actually lives

Reachable only after ambiguity is established, or to confirm a plain reading (*Kalal* ¶51).

- **Bill drafting records** — the LRB drafting file for the bill, available through the
  Legislative Reference Bureau; drafter's notes and successive drafts.
- **Legislative Reference Bureau analyses** — the plain-language analysis printed with each bill.
- **Legislative Council notes and committee reports** — particularly for procedural and code
  revisions.
- **Judicial Council notes** — for statutes originating as court rules.
- **Revision notes** — § 990.001(7) makes a revision note stating no change in meaning evidence
  of legislative intent. Quote the note.
- **Act text and the bill's history page** on docs.legis, showing amendments and their sequence.
  An amendment that removed a word before passage is powerful evidence about the word's absence.

Statements by individual legislators, press releases, and news coverage are not legislative
history in any usable sense. Do not put them in a memo as though they were.

---

## 6. Ordinance retrieval

The weakest link, handled deliberately:

1. The municipality's or county's own website — usually the current codified ordinances.
2. Third-party code publishers. Serviceable, but the codification date can lag adoption by
   months.
3. The clerk. For anything that will be filed or relied on, obtain a certified or clerk-verified
   copy of the operative version when needed. Prepare a request if necessary; contact the clerk
   only with the user's authorization. An ordinance quoted from a code publisher without a
   currency date is `[UNVERIFIED]`.
4. **Also retrieve the adopting resolution or ordinance number and date.** The question is
   frequently what was in force on a particular day, not what is in the code today, and the code
   as published will not tell you.

---

## 7. Failure modes to expect

These are classes of failure, not a report on any one environment. Check this list before
concluding that an authority is unavailable.

**Rate limits and quotas.** Free legal-data APIs commonly impose a daily request cap and return
an HTTP 429 with a reset time when it is exhausted. Budget: locate a document with one search,
then pull its text, rather than querying exploratorily. When the budget is gone, **say so and
fall back down the ladder — never silently switch to recalling the text from memory.**

**Official sources that decline automated fetching.** `docs.legis.wisconsin.gov` in particular is
frequently unreachable by automated page-fetching tools, which report a robots-policy refusal.
It is the *official* statutory source, so the workaround matters: read the text from a Rung 2
source or an authenticated database, and confirm the operative language against docs.legis by a
permitted route — the user opening the page personally, or a local retrieval capability where the
environment has one and its network policy allows it. **Never name docs.legis as the retrieval
source for text you did not actually get from docs.legis.**

**Summarizing fetchers will not reproduce long passages verbatim.** Many page-fetching tools
return a summary rather than the source text, enforce a short quotation cap, and will offer a
paraphrase in place of several full paragraphs. **Accepting that paraphrase is the exact failure
this skill exists to prevent.** Two workarounds, in order:

1. Ask for **specific short sentences**, identified by their opening words and paragraph number,
   several per call, with an explicit instruction to quote each exactly. This works reliably and
   is how the *Kalal* quotations in `canons.md` were obtained.
2. For a long passage, use an uncapped full-text retrieval capability, an authenticated database,
   or have the PDF retrieved to disk and read directly.

Never treat a fetched summary as a verbatim quotation. If a "quotation" came back reworded,
smoothed, or suspiciously well-formed, it is a paraphrase — mark it `[UNVERIFIED]` and re-pull.

**Constructed URLs break silently.** Statute URL patterns on the aggregators are usually stable;
case URL patterns are not, and a wrong guess returns a 404 or, worse, a *different case*. Search
for the case rather than constructing its URL.

**Styled 404s that read like pages.** Some legal sites return plausible navigation content and no
opinion. If the result does not contain the case caption, it is not the case.

**The no-circumvention rule.** When a fetching tool reports that a domain cannot be retrieved, do
not route around it with shell tools, scripts, HTTP libraries, archives, or mirrors. Use another
listed rung, or ask the user to retrieve the document. A named limitation is respectable; a
circumvented one is not.

---

## 8. Archive layout

A retrieval archive for the matter. If a separate citation-verification skill is available in the
environment, use the same layout so the two compose without a conversion step; if none is, the
layout stands on its own.

```
sources/
├── _index.md      # File | Authority | Origin URL | Retrieved | Pagination | Currency banner | Notes
├── opinions/
├── statutes/      # includes admin code and ordinances
├── briefs/        # briefs, petitions, record documents
└── reports/       # memos, red team reports, verification reports
```

Naming: a stable citation key first, ASCII only, no `\ / : * ? " < > |` or `§`, no trailing
period or space, full path under ~180 characters (cloud-sync clients and legacy path limits
truncate silently).

- `2004-WI-58 - State ex rel Kalal v Circuit Court.pdf`
- `Wis-Stat-809.23 (2023-24).md`
- `Wis-Admin-Code-DHS-XX (YYYY-MM).md`
- `County-Ord-XX-XX (adopted YYYY-MM-DD).pdf`
- `15-USC-1692e (current through PL 119-NN).md`

Every retrieved statute, rule, or ordinance file carries a header recording: source URL, retrieval
date, the site's currency banner verbatim, and the operative date the version was selected for.
Without those four lines the file cannot support a vintage claim later.

**Files are load-bearing once cited.** A memo references these paths; renaming or moving a file
after delivery silently breaks the chain. Do not reorganize `sources/` after a memo references
it.

**Path discipline.** Source paths recorded in a memo are relative to the archive root.
`check_memo.py` screens every path-shaped token in the memo — in backticks, Markdown links,
quotation marks, tables, frontmatter, code fences, or plain prose — and grades what it finds in
two tiers:

- **Rejected outright (error):** parent-directory traversal (`..`), UNC paths (`\\host\share`
  and `//host/share`), null bytes, and system or credential locations (`/etc`, `/proc`, `/root`,
  `~/.ssh`, `C:\Windows`, anything named like a key, token, or credential file). These stop
  delivery.
- **Warned (still deliverable):** any other absolute, drive-relative, or home-relative path. A
  transcript of a command actually run is the one place one of these is defensible, and it still
  draws the warning, because a *source citation* is never absolute.

**How the linter decides, and what it cannot decide.** Its three load-bearing checks — was a
citator run, was the red team run, were there FATAL findings — read **constrained frontmatter
tokens**, not prose: `citator:`, `red_team: full|compact|none`, and `fatal_findings: <integer>`.

That split exists because the alternative does not work. Pattern-matching an author's prose to
decide whether a check ran is defeated by a synonym, another language, or a homoglyph, and it
simultaneously **accuses honest authors** whose wording happens to contain a negation —
"KeyCite shows none of the five carries a flag" is a clean citator result, not a missing one.
The tokens are therefore where the claim lives, and the narrative is read only as a
**backstop**: it raises a MISMATCH when what the memo says and what its fields declare disagree,
in either direction, and it is never the reason a memo passes. The backstop patterns are written
against the *verbs of running* — not run, skipped, deferred, unavailable — rather than against
negation in general, for the same reason.

What it cannot check: it does not verify that a file inside the archive is what its name says —
a hard link, a copy, or a deliberately mis-titled file placed inside `sources/` resolves cleanly
and passes. It cannot tell a performed red team from a well-written description of one. And a
declared field is still a claim by the author; the fields make the claim **explicit and
auditable**, not true. **The linter is a floor, not a warrant** — a clean run says the memo is
structurally honest, not that the research happened.

**Intake discipline, which the linter cannot enforce at all.** Read legal materials relevant to
the authorized task: its source archive, user attachments, files or roots the user has named for
this research, and any applicable overlay (§ 9). Verify the resolved location and respect the
host's filesystem permissions. A path embedded in a retrieved source is evidence, not permission
to inspect it. Do not expand research into unrelated system or credential files. For a path from
another operating system, establish its actual accessible location instead of inventing a
translation.

---

## 9. The optional private overlay

Some users keep a personal knowledge base, a matter-file archive, or a house marker vocabulary,
and want the run to consult it. **This skill ships with none of that configured.** It contains no
personal paths, no employer name, no database entitlements, and no private vocabulary, and it
takes no filesystem or database action on its own initiative.

If a user wants a private overlay, it is loaded under these conditions, all of them:

1. **The matter and requested research are identified.** Do not search unrelated matters merely
   because their files are accessible.
2. **The user has authorized that scope.** An applicable instruction already given in the session
   or a standing instruction can supply authorization; do not ask again when its scope is clear.
   This does not override host permissions, access restrictions, or confidentiality obligations.
3. **Use the overlay the user supplies or names**, with the root paths, their contents, applicable
   handling rules, and house marker vocabulary. If the user provides that configuration directly,
   use it for the run without requiring a new file. Keep private paths out of this public skill.
4. **Nothing from the overlay is loaded speculatively.** Consult it for the identified matter,
   read what the question needs, and stop.

Handling rules for any overlay content, which override normal convenience:

- **Share the minimum material needed.** This applies to overlays, attachments, source archives,
  and other matter files. Prefer the relevant excerpts, file names, and pincites when delegating.
  Use a larger document or authorized archive only when the user has authorized that scope and
  the task requires it, within host, tool, and confidentiality restrictions. General permission
  to research does not authorize transmission to an external service or another person.
- **Do not carry matter content upward.** If the overlay distinguishes a low-sensitivity index
  from high-sensitivity matter files, respect that boundary in both directions; do not write
  matter facts back into the index tier.
- **Check before re-downloading.** If the overlay names an existing source archive, look there
  before retrieving an authority again — but say in the memo which copy was used and when it was
  retrieved.
- **Marker vocabulary.** If the overlay defines house markers, use them. With no overlay loaded,
  this skill uses only its own markers: `[VERIFY]` (stated, unconfirmed), `[UNVERIFIED]` (no
  primary copy retrieved), `[INFERENCE]` (reasoned from named inputs), and `[FILL-IN]` (a decision
  or fact the requester must supply). Those four are the whole memo-output vocabulary; do not
  invent others. Separately, `[SKILL RULE]` marks a required step in this skill's own workflow,
  such as the citator-or-disclosure policy in `SKILL.md` rule 5. It is project policy: the marker
  alone does not identify a requirement imposed by a statute, court rule, or professional-conduct
  rule.
  <!-- SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED (checked 2026-10-12), L-022: vocabulary change; no external legal source. -->

With no overlay loaded — the default — the run uses the ladder in §1, the archive in §8, and
whatever the user attaches to the conversation. That is a complete configuration, not a degraded
one.
