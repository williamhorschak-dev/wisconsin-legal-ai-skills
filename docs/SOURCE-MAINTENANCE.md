# Maintaining legal references

[legal-sources.json](legal-sources.json) starts with frequently used procedural
rules, interpretation guidance, and publication boundaries. It is not an inventory
of every authority mentioned in the skills. Add a record when materially changing
an uncovered legal proposition.

Each record identifies the proposition, official source URL, operative-version
description, review scope/date, review basis, affected files, and review interval.
`focused_primary_check` means the identified passage was read for that limited
purpose. `inherited_review` carries forward a documented earlier review without
pretending a new one occurred. `needs_primary_review` records an actual gap.
Neither a date nor an accessible URL establishes current law or subsequent treatment.

```sh
python scripts/source_registry.py validate
python scripts/source_registry.py due --as-of 2026-09-20
```

`validate` checks record structure and file references, without network requests.
`due` returns `1` when review is due or pending, `0` when no reminder is due, and
`2` for invalid data. These are maintenance reminders, not legal-currency verdicts.
Review before releases and when an amendment, court order, or reported defect
affects an entry; intervals are upper bounds for routine reminders, not safe
reliance periods.

Each record also carries three dates that answer different questions.
`retrieved_at` is the day a maintainer last fetched the URL and saw it answer.
`page_changed_at` is the publication date shown in the currency line of the page at
`currency_url`, or null when no line is recorded. `legally_reviewed_at` stays null until a
qualified reviewer checks the proposition against the law; no script sets it.
`currency_line` holds the line last seen at `currency_url`.

```sh
python -I scripts/check_sources.py --report source-check/report.json
```

The check reads each host's robots.txt, requests every distinct URL once with a
10-second timeout and a descriptive User-Agent, and prints and saves a report. It exits
`1` when a URL is unreachable or refused by robots.txt, or when a recorded currency line
changed or disappeared, `0` otherwise, and `2` for an unreadable register. It never
writes the register; after reading a report, a maintainer updates `retrieved_at`,
`page_changed_at` and `currency_line` by hand. A changed currency line is a prompt to
review the affected files, not evidence that any proposition changed, and an unchanged
line is not evidence that none did. The `Check sources` workflow runs the check monthly
and on manual dispatch and uploads the report as an artifact; it has read-only
repository permission and commits nothing. No third-party notification is enabled.

For each review, retrieve the official text, establish the applicable version and
effective date, read the proposition in context, and inspect subsequent history
or treatment appropriate to the proposed claim. Record what actually happened,
including retrieval failure or absent citator coverage. Review every affected file
and its examples/templates together. Update the date only after the described
review, then refresh skill manifests and run validation.

Keep a private matter's source archive separate. The citation helper's optional
structured provenance records origin, retrieval timestamp, operative version,
extraction method, and an original-file/hash link. That is evidence for a specific
run, not content for the public register. Do not publish private or licensed source
archives as maintenance examples.
