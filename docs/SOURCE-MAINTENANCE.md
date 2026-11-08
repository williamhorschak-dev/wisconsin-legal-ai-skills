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

The checker reports exactly one outcome per source, with every underlying source
and currency-page diagnostic retained:

| Outcome | Meaning | Exit when controlling |
| --- | --- | --- |
| `ok` | Every configured response check and recorded currency comparison completed successfully. | 0 |
| `changed` | A recorded currency line changed or disappeared. | 1 |
| `refused` | Robots disallow or 401/403, HTTP refusal, off-host/invalid redirect, an invalid/incomplete response, or an unexpected 304. Source 404/410 is `refused` with reason `http_404`/`http_410`. | 1 |
| `transient` | Timeout, connection failure, 429, server 5xx, unavailable robots or exhausted budget. | 3 |

Invalid configuration or inability to write the required report exits 2. Mixed
exit precedence is `2 > 1 > 3 > 0`. Within a source, outcome precedence is
`refused > changed > transient > ok`; a changed currency line can therefore
control exit 1 while that source's primary URL timed out. Both diagnostics stay
visible. Robots 404/410 means no robots file and permits the source check; robots
429 never does. Explicit refusals and invalid responses are not retried.

Each distinct URL is cached, with at most two attempts, including robots and
redirect targets. All attempts use one scheduler and a descriptive User-Agent.
Same-host redirect targets must also pass robots rules. Off-host redirects are
not followed. Request start times on each host are at least the maximum of 2
seconds, robots Crawl-delay, and 5 seconds for docs.legis.wisconsin.gov apart.
Numeric fractional Crawl-delay is conservatively rounded up to a whole second;
unrecognized delay syntax refuses the host instead of silently dropping its delay.
Retry-After seconds or HTTP dates also delay the next request to that host,
including a different URL after the final retry. At most five redirect hops are
followed. Oversized Retry-After waits are recorded as deferred, without sleeping
past the run budget.

A supervised worker bounds the entire request at 20 seconds, including DNS,
headers and streaming body reads. The parent drains the worker output while
waiting, kills a timed-out worker and reserves one second to reap it. A cleanup
timeout is reported as transient without another blocking wait. The 720-second
run budget admits an attempt only if the host wait plus its 21-second reservation
fits. This leaves 180 seconds inside the workflow's existing 15-minute limit for
setup, report generation and artifact upload. A run cannot guarantee checking
every source when servers are slow. At the current registry size, 11 records
reference 18 distinct URLs on two hosts, or 20 URLs with robots. Two 20-second
attempts per URL alone would take 800 seconds; adding conservative cleanup and
5-second pacing reservations gives `40 * (20 + 1 + 5) = 1040` seconds before
extra Crawl-delay, Retry-After or redirects. The 720-second cap therefore stops
collection and reports remaining checks as transient, rather than claiming that
worst case fits. Redirect attempts consume the same cap and per-URL limit.

Complete bodies are capped at 16 MB. Expected PDFs must have PDF content type,
a PDF header and a final EOF marker; declared lengths must match. These are
response-integrity checks, not a full PDF parser, a content hash comparison or a
substantive review. Link-only success is reported as `comparison=response_valid`.
The current registry has no PDF comparison baselines. Only recorded currency
lines have `unchanged`/`different` comparisons. HTML fingerprints, PDF content
comparison, conditional requests and county-index loading are not implemented;
recognized future-mode configuration is rejected, and unconditional 304 is refused.

`Summary: checked= unchecked= changed= refused= transient=` counts source records.
A record is checked only when all its configured response/currency checks
completed, including a completed comparison that found a change. Separate
required/completed response-check and currency-comparison counts prevent treating
PDF availability as unchanged content. Incomplete runs warn about unchecked
records, with a zero-comparisons warning when no currency comparisons completed.
`No problems found` appears only if all required checks completed successfully.

The JSON preserves the original top-level `results`, `problems`, request count,
response metadata and nested `currency` fields. It adds each outcome and reason,
the original primary result, coverage counters, the full attempt log and
`checker_exit`. Shared currency responses are fetched once but compared separately
against every record's stored line. The checker never writes the registry and
only copies `legally_reviewed_at` into the report; it does not use that date to
decide an outcome. After reading a report, a maintainer updates retrieval and
currency metadata by hand. A changed currency line prompts review; it does not
establish that a legal proposition changed or remained correct.

The monthly/manual `Check sources` workflow captures the actual exit, fails on
1 or 2 and unexpected exits, warns on 3, and always attempts report upload. It
keeps read-only repository permission and commits nothing. No third-party
notification is enabled.

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
