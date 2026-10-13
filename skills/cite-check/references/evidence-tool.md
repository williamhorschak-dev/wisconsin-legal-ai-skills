# Evidence tool

Run `scripts/cite_check.py` from the installed skill directory with Python 3.10+.
It needs no third-party packages. Use absolute paths or resolve paths from the current
working directory; source `file` values are relative to `--sources`.

## Prepare the inventory

Save a JSON inventory after manually checking that every citation use is included.
Compute `document_sha256` from the exact input document's bytes (for example with
Python's `hashlib.sha256(Path(path).read_bytes()).hexdigest()`). Synthetic example:

```json
{
  "document_sha256": "<actual 64-character SHA-256>",
  "uses": [
    {
      "id": "use-1",
      "citation": "<actual citation>",
      "kind": "case",
      "proposition": "<what this use asserts>",
      "quote": "<exact quotation in the draft, or omit this field>"
    }
  ]
}
```

Kinds: `case`, `statute`, `regulation`, `rule`, `record`. For authorities the required
checks are `citation`, `pincite`, `treatment`, `proposition`, and `format`; for records,
`record`, `pincite`, and `format`. A non-empty quote adds `verbatim`. Record separate
uses for different propositions, locators, and short forms. Omit `quote` when there is
no quotation; an empty or normalization-only quotation is invalid. Omitting a use or quote
from the inventory cannot be detected automatically; review the inventory itself.

## Record evidence

Create `entry.json` with `use`, `check`, `result` (`pass`, `fail`, `unverified`, or
`caution`), and a specific `note`. For a passing check also supply `file`, `sha256`,
`locator`, and `matched` source text. Case `treatment` passes require a named `citator`
and a note explaining the signal, relevant treatment, and review date. The software
cannot confirm the truth of that attestation. With only free-source screening use
`caution`, not `pass`.

New records should include structured `provenance` rather than keeping the source
origin and version only in notes. Existing records without it remain readable:

```json
{
  "provenance": {
    "origin": "https://official.example.invalid/source.pdf",
    "retrieved_at": "2026-09-20T14:30:00-05:00",
    "version": "The edition/effective period actually read; state uncertainty",
    "extraction_method": "PDF text extraction; page images separately compared",
    "original_file": "opinions/source.pdf",
    "original_sha256": "<actual SHA-256 of the archived original>"
  }
}
```

Use the actual URL or identify a supplied document in `origin`. Record the actual
retrieval time with timezone. `original_file` and `original_sha256` are optional
together, and bind an extraction to an original inside the archive. The helper
validates their hash and the field structure; it cannot authenticate a URL,
determine the operative legal version, or prove that a visual comparison occurred.
For native text with no separate original, omit both original fields and describe
the method accurately. Keep this evidence private to the authorized matter.

Add `provenance_origin` to each new entry: `retrieved_this_session`, `user_supplied`,
or `remembered` (recalled without the source in front of the reviewer). Records without
it remain readable and are reported as `provenance not recorded`. The tool refuses a
verbatim `pass` whose origin is `remembered`. An entry may also carry `source_status`
with `source`, `reason`, and `status` (`reachable`, `unreachable`, or `not_attempted`);
a check cannot pass from a source that was not reached.

```sh
python <skill-dir>/scripts/cite_check.py record --inventory inventory.json --document draft.docx --sources sources --log checks.jsonl --entry entry.json
```

For a straightforward quote in a UTF-8 `.txt` or `.md` source, the tool can perform
conservative substring matching. It normalizes whitespace, curly quotation marks,
fi/fl ligatures and soft hyphens. It does not drop words, infer omissions, dehyphenate
line endings, remove headers, or resolve attribution. Intentional alterations and OCR
need manual comparison against the original and a documented manual `verbatim` check.

```sh
python <skill-dir>/scripts/cite_check.py quote --inventory inventory.json --document draft.docx --sources sources --log checks.jsonl --use use-1 --file opinions/source.txt --locator "paragraph 12" --provenance-origin retrieved_this_session
```

The quote command records one label with the entry:

| Label | Meaning | Result |
|---|---|---|
| `VERIFIED` | Exact text found in the compared text | `pass` |
| `QUOTE_ALTERED` | No exact match; a passage at least 70 percent similar by words is in the compared text. The report shows a `[-draft only-]{+source only+}` diff | `fail` |
| `MISATTRIBUTED` | Exact text is elsewhere in this run's archived `.txt`/`.md` sources, not in the compared text; `found_in` names each place | `fail` |
| `UNRESOLVED` | Not found | `fail` |

Without markers the whole file is compared and the locator is not checked. To compare
the cited locator, mark the extraction: a line `[locator: s. 999.01]` starts a segment
that runs to the next locator line, and the locator `s. 999.01(2)` uses that segment. One
`[version: ...]` line names the dated text a file holds; archive each version in its own
file. A verbatim entry against a file with a version line must repeat it in
`version_compared`; the quote command does this. Marker lines are reviewer annotations,
are not matched, and do not establish which version was in force on the operative date.

PDFs and other files are listed as not searched for `MISATTRIBUTED`. When no other
archived text can be searched, the label falls back to `UNRESOLVED` with a note. Manual
verbatim entries may record a `label`: `VERIFIED` only with `pass`, `UNRESOLVED` with
`fail`, `caution`, or `unverified`, and the others with `fail` or `caution`. A manual
`MISATTRIBUTED` needs `found_in`; `QUOTE_ALTERED` needs the source wording in `matched`.
Older records without a label are reported as `quote label not recorded`.

The provided locator still needs a separate `pincite` check. Preserve extraction
provenance to the original PDF in the source index; a match in an unchecked extraction
does not verify the original image. Manual checks must explain what was compared.

## Generate the report

```sh
python <skill-dir>/scripts/cite_check.py report --inventory inventory.json --document draft.docx --sources sources --log checks.jsonl --out report.md
```

Exit status: `0` all required evidence records pass, `1` a report was written with
missing/flagged/caution checks, `2` malformed or stale evidence, unsafe/missing source,
or another execution error. An absent log produces an entirely unverified report;
it cannot silently pass. Reports never overwrite existing files.

Add `--sources-status sources-status.json` to include the reachability you recorded:

```json
{"sources": [{"source": "<site, connector or service>", "status": "unreachable",
  "reason": "<what happened and when>", "uses": ["use-2"]}]}
```

The report's "Sources reachable" block lists each source with its status, reason, and
affected uses, then archived files and `source_status` entries from the log, then any use
with no recorded source. The tool contacts no source and never prints a run-wide verdict.

The log is an ordinary local file, not a signed or append-only record. The helper detects a
changed draft, source or inventory, but it does not detect a deleted, inserted or hand-edited
log line. Treat `RECORDED PASS` as a summary of what the log says, and keep the log under
the same control as the draft.

The report preserves evidence records verbatim as JSON and gives per-use coverage.
The helper rechecks draft/source hashes and a canonical-JSON inventory hash on every
operation. It binds a new entry to the current inventory and rejects any supplied hash
that disagrees. Editing a citation, proposition, quote, or other inventory content
invalidates the old log even when the draft bytes stay the same. JSON indentation and
object-key order do not change this hash. Logs allow one record per
use/check and one writer per run. Preserve the old run and start new inventory/log/report
files after correcting evidence or changing a draft or inventory; do not append a contradictory pass
to bury an earlier failure. A completed report is a review aid, not permission to file.
