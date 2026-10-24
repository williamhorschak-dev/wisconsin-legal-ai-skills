# How Wisconsin sources behave

This file describes how the public Wisconsin source sites display text, dates and
status, and where those displays mislead a reader or an agent. It says nothing about
what any provision means or whether it is in force. Each entry was checked against
the live page on the date given; sites change, so treat a dated entry as a
description of what was seen then, not a promise about today. All examples use
placeholders such as `{chapter}` and invented values.

Method for the checks: one request per page, after reading the host's robots.txt.
Pages were read through a fetch tool that returns a summary of the page text, or
through one scripted GET with a descriptive User-Agent and a 10-second timeout.

Each entry has four parts: what you see, why it misleads, what to do, and the date
it was checked.

## docs.legis.wisconsin.gov (statutes)

### 1. The currency line

- **What you see.** Statute pages carry one line that names the biennial edition
  (for example "2099-00 Wisconsin Statutes"), says the text is updated through a
  named Act and through court and board orders filed before and in effect on a
  stated date, says changes effective after that date are marked by NOTES, and
  ends with a publication stamp such as "(Published 1-2-99)". In the page source
  the line sits in a separate block near the end of the HTML, so a text extract
  can show it after the section text rather than above it.
- **Why it misleads.** The edition label names the last printed biennial volume,
  not the version you are reading; the site revises the text continuously between
  printings. The stamp is a publication date for the online text, not an effective
  date for any provision.
- **What to do.** Copy the whole line verbatim into the source header
  (`updated_through:`), keep the publication stamp with it, and read the NOTES on
  the section before quoting. Never infer currency from the edition label alone.
- **Checked:** 2026-10-13, on a section page and a chapter page.

### 2. Two versions of the same unit (amendments not yet in effect)

- **What you see.** When a unit has been amended, or repealed and recreated, with a
  later effective date, the page publishes both versions with a NOTE. Each NOTE on
  the page checked was worded in the pattern "Par. (x) is shown as amended eff.
  {date} by {year} Wis. Act {n}. Prior to {date} it reads:" and the earlier version
  followed it. The site's help page says one version appears in regular type and the
  other in smaller bold type, and that the note and the superseded text are removed
  once the effective date passes.
- **Why it misleads.** In that pattern the text printed first, in the ordinary
  position of the section, is the version that takes effect later. An agent that
  reads the first block of text as the current text quotes language that is not yet
  in effect. A text extract also loses the type styling, and the help page does not
  say which version gets which typeface.
- **What to do.** Search every quoted unit for a NOTE before quoting. When one is
  present, record both versions, the effective date the note states, and the Act it
  names; pick the version for the operative date of the question; then read the
  amending Act's effective-date provision. Rely on the note's wording, not the
  typeface. Quote the text in force on the target date: for a date before the
  effective date the note states, that is the earlier version printed after the
  words "Prior to {date} it reads:", not the first block on the page. Say which
  version you quoted and why.
- **Checked:** 2026-10-13 (help page "About the statutes", and a section page that
  showed two such notes).

### 3. Permalinks and the JSON suffix

- **What you see.** The help page on linking gives permanent links in the form
  `https://docs.legis.wisconsin.gov/document/statutes/{section}`. Requesting that
  form redirects to a longer path of the form
  `/statutes/statutes/{chapter}/{subchapter}/{number}`, where the subchapter is a
  lowercase roman numeral. The machine-readable-data help page says every page on the
  site is also available as JSON by appending `.json`; a request for
  `/document/statutes/{section}.json` redirected to the long path with `.json` and
  returned `application/json` holding the section's path, name, citation keys, a
  `biennium` value and the text.
- **Why it misleads.** The long path encodes a subchapter that cannot be derived
  from the section number, so a hand-built long link breaks easily. The same help
  page says the URL structure may change without notice and states no licensing or
  rate terms. The JSON `biennium` value seen did not match the edition named in the
  currency line; what that field means was not determined.
- **What to do.** Cite and store the `/document/statutes/{section}` form. Use JSON
  only as a convenience for reading text, take the currency line from the HTML page,
  and do not treat the JSON `biennium` field as a currency statement.
- **Checked:** 2026-10-13.

### 4. Tables that appear only in the chapter PDF

- **What you see.** The help page "About the statutes" says certain tables and maps
  that are part of the printed statutes appear only in the PDF format, and names the
  s. 20.005 schedules as missing from the HTML. Section pages link a chapter PDF of
  the form `/document/statutes/{chapter}.pdf`.
- **Why it misleads.** An HTML page or its JSON can look complete while a table that
  belongs to the text is absent, and nothing on the section page flags the gap.
- **What to do.** When a provision refers to a table, schedule or map, open the
  chapter PDF and record that the PDF was the copy read.
- **Checked:** 2026-10-13.

### 5. Annotations are editorial aids, not statute text

- **What you see.** Statute pages show annotations directly after the affected
  sections: section histories, cross-references, interpretive notes and notes about court decisions.
  The help page says the Legislative Reference Bureau prepares them under
  s. 35.18 (4), and says the case annotations help readers find case law but are not
  definitive statements of the law or a substitute for reading the cases. Case links
  in the annotations go to Google Scholar.
- **Why it misleads.** Annotations sit on the same page as the statute, so a text
  extract can blend them into the quoted text. A one-line case note is a finding aid
  written by an editor, and the linked copy is an unofficial third-party copy.
- **What to do.** Quote only the statute text as statute. Use a case annotation to
  locate a decision, then read the decision itself from wicourts.gov or another copy
  named in the source ladder. Never quote annotation text as if it were the statute.
- **Checked:** 2026-10-13.

## wicourts.gov

### 6. Opinion URL forms and what the list pages show

- **What you see.** Supreme Court opinions released since September 1995 are listed
  through `/supreme/scopin.jsp?begin_date=MM/DD/YYYY&end_date=MM/DD/YYYY&SortBy=date`
  and Court of Appeals opinions through
  `/other/appeals/caopin.jsp?begin_date=...&end_date=...&SortBy=date`. Each listed
  document opens at `/sc/opinion/DisplayDocument.pdf?content=pdf&seqNo={n}` or
  `/ca/opinion/DisplayDocument.pdf?content=pdf&seqNo={n}`. The lists show a release
  date, case number, caption and PDF link. In one list two case numbers pointed to
  the same `seqNo`. The Court of Appeals list says published opinions are subject to
  further editing and modification. The Supreme Court opinions page footer read
  "Updated: May 2, 2024" while the linked list held releases from September 2026.
- **Why it misleads.** `seqNo` is a document number, not a case number, and one PDF
  can serve several consolidated case numbers. The list pages give no public-domain
  citation. A PDF saved on release day may differ from the final edited text. The
  footer date says nothing about how recent the list is.
- **What to do.** Record the case number, release date and full `seqNo` URL for each
  opinion used, take the citation and paragraph numbers from the document itself,
  and note whether the copy is a release-day slip. Ignore footer dates as currency
  evidence.
- **Checked:** 2026-10-13.

### 7. The pending-cases table describes its own coverage

- **What you see.** The Supreme Court pending-cases page says its table lists the
  cases the court has accepted for review, with issues, background, oral argument
  date, mandate and Court of Appeals citation, and that it is updated regularly. The
  table itself is a released document; the latest release shown was dated
  Oct 05, 2026, while the page footer read "Updated: February 13, 2022".
- **Why it misleads.** The table covers accepted cases only. A case missing from it
  may still have a petition for review waiting for action, and a case listed there
  shows nothing about later events after the release date. The footer date is not
  the table's date.
- **What to do.** Treat the table as a list of accepted cases as of its release date,
  record that date, and check the WSCCA docket for the case's actual status.
- **Checked:** 2026-10-13.

### 8. Supreme Court Rules pages give release dates, not effective dates

- **What you see.** The SCR page lists chapters with a column labeled "Release
  date" and says the rules are updated as the court approves changes. Chapter PDFs
  open at `/sc/scrule/DisplayDocument.pdf?content=pdf&seqNo={n}`. The newest release
  listed was dated Mar 24, 2026, later than the page footer "Updated: January 6,
  2026". Orders amending rules are in a separate Orders section.
- **Why it misleads.** A release date is when the court system posted the chapter,
  not when any rule in it took effect, and the footer date is older than the list.
- **What to do.** Record the chapter's release date as a release date. For the date a
  rule took effect, find and read the order that adopted it and its stated
  effective date.
- **Checked:** 2026-10-13.

### 9. Rule-petition pages show filings, not outcomes, unless an order is listed

- **What you see.** The pending rule-petitions index lists petitions by number with
  no status column. Each petition page has sections for the petition and supporting
  papers, the next scheduled event, court orders and communications, past hearings,
  and responses. On one page checked, a petitioner's letter titled as withdrawing the
  petition appeared under responses while the court orders section was empty.
- **Why it misleads.** A filed paper, including a request to withdraw, is not a
  disposition. An earlier check found a search summary that still called a petition
  pending after its page had changed.
- **What to do.** Report what is filed and what the court has ordered as separate
  facts. Describe a petition as decided, dismissed or withdrawn only when an order
  saying so appears in the court orders section, and give the order's date. Read the
  petition page itself, not a summary.
- **Checked:** 2026-10-13.

### 10. Automated access: wicourts.gov has no robots.txt

- **What you see.** A request for `https://www.wicourts.gov/robots.txt` returned
  HTTP 404, and the pages above answered normal requests. The site disclaimer says
  its information should not be cited as an official or authoritative source and
  should be independently verified; it says nothing about automated access.
- **Why it misleads.** The absence of a robots file allows polite fetching, but it is
  not a license to reuse content and does not make the site's copy official.
- **What to do.** Fetch lightly (one request per page, a descriptive User-Agent) and
  keep recording each copy's origin and retrieval date. Do not describe a wicourts
  page or PDF as the official record on the strength of a successful fetch.
- **Checked:** 2026-10-13.

## Other sources

### 11. County local rules are hosted by the State Bar

- **What you see.** The directory of circuit court local rules that searches return
  first is the State Bar of Wisconsin's Circuit Court Rules directory on wisbar.org, which
  lists county rule sets with a date and, for some counties, later directives or
  orders as separate entries. The State Bar's Terms of Use, as indexed by a search
  engine, prohibit scraping and bots, and prohibit linking to the site without the
  Bar's express written permission.
- **Why it misleads.** The listing date is not an effective date, a base rule set can
  be older than directives that must be read with it, and the host is a private
  association whose terms restrict automated access and linking even though the
  rules are court documents.
- **What to do.** Do not fetch, bundle or link wisbar.org copies. Ask the user for the
  current local rules and any directives from the county's clerk of circuit court or
  the county's own court web page, cite that source, and record the date shown on the
  copy. Say when no copy was available.
- **Checked:** 2026-10-13, through search-engine results only. wisbar.org itself was
  not fetched, because its terms restrict automated clients; an assessment on
  2026-10-12 read the terms page and the directory.

### 12. Jury instructions moved to the State Law Library in 2021

- **What you see.** The Wisconsin State Law Library hosts the current civil, criminal
  and children's jury instructions at `https://wilawlibrary.gov/jury/`, with paths
  `/jury/civil/`, `/jury/criminal/` and `/jury/children/`. The library's blog
  announced the hosting on January 26, 2021, as a joint effort with the University of
  Wisconsin Law School and the court system's Office of Judicial Education. The
  jury page says it publishes only current instructions, posts a filing release on
  each set's updates page, and keeps archived compilations on the Wisconsin Digital
  Archive. Its robots.txt allows `/jury/`.
- **Why it misleads.** Links and citations made before 2021 may point to print sets
  or other locations. Because the site holds only current instructions, the page for an
  instruction does not show the version that applied on an earlier date.
- **What to do.** Link the wilawlibrary.gov page, record the instruction's revision
  date shown on it, and use the archived compilation when an earlier version is
  needed.
- **Checked:** 2026-10-13.

### 13. CourtListener and static.case.law refuse automated clients

- **What you see.** A scripted request for `https://www.courtlistener.com/robots.txt`
  returned HTTP 403. `https://static.case.law/robots.txt` returned
  `User-agent: *` and `Disallow: /`.
- **Why it misleads.** Both hold useful opinion text, so an agent may assume it can
  fetch them. A robots file that is refused
  (401 or 403) is treated by standard robots parsers as disallowing everything, and
  `Disallow: /` excludes the whole host.
- **What to do.** Do not script requests to either host. For Wisconsin opinions use
  wicourts.gov; use CourtListener only through a human session or a separately
  authorized API arrangement whose terms have been read (they were not read for this
  file); use copies the user supplies for anything else.
- **Checked:** 2026-10-13.
