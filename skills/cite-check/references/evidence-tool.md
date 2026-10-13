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

```sh
python <skill-dir>/scripts/cite_check.py record --inventory inventory.json --document draft.docx --sources sources --log checks.jsonl --entry entry.json
```

For a straightforward quote in a UTF-8 `.txt` or `.md` source, the tool can perform
conservative substring matching. It normalizes whitespace, curly quotation marks,
fi/fl ligatures and soft hyphens. It does not drop words, infer omissions, dehyphenate
line endings, remove headers, or resolve attribution. Intentional alterations and OCR
need manual comparison against the original and a documented manual `verbatim` check.

```sh
python <skill-dir>/scripts/cite_check.py quote --inventory inventory.json --document draft.docx --sources sources --log checks.jsonl --use use-1 --file opinions/source.txt --locator "paragraph 12"
```

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
