#!/usr/bin/env python3
"""Record citation evidence and generate a hash-bound completeness report.

This tool does not discover citations, evaluate holdings, or run a citator.
Only plain-text quote matching is automated. Other results are reviewer attestations.
Requires Python 3.10+; standard library only. Run --help for commands.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def inventory_digest(inv):
    """Bind the evidence to inventory meaning, independent of JSON indentation."""
    payload = json.dumps(inv, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_path(root, name):
    """Reject absolute paths, traversal, Windows device/ADS names and escaped links."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("source file must be a non-empty relative POSIX path")
    relative = Path(name)
    if relative.is_absolute() or PureWindowsPath(name).is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe source path: {name}")
    if any(PureWindowsPath(part).is_reserved() for part in relative.parts):
        raise ValueError(f"reserved source path: {name}")
    root = Path(root).resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError(f"source is not a file inside the archive: {name}")
    return candidate


def required_checks(use):
    if use["kind"] == "record":
        checks = {"record", "pincite", "format"}
    else:
        checks = {"citation", "pincite", "treatment", "proposition", "format"}
    if use.get("quote"):
        checks.add("verbatim")
    return checks


def inventory(path, document):
    data = load_json(path)
    if not isinstance(data, dict) or data.get("document_sha256") != digest(document):
        raise ValueError("document hash differs from inventory; create a new run for the revised draft")
    uses = data.get("uses")
    if not isinstance(uses, list) or not uses:
        raise ValueError("inventory must include at least one citation use")
    ids = set()
    for use in uses:
        if not isinstance(use, dict) or any(not isinstance(use.get(k), str) or not use[k].strip() for k in ("id", "citation", "proposition", "kind")):
            raise ValueError("each use needs non-empty id, citation, proposition and kind strings")
        if use["id"] in ids:
            raise ValueError(f"duplicate citation use: {use['id']}")
        if use["kind"] not in {"case", "statute", "regulation", "rule", "record"}:
            raise ValueError(f"unsupported kind: {use['kind']}")
        if "quote" in use and (not isinstance(use["quote"], str) or not normalized(use["quote"])):
            raise ValueError("quote must contain non-empty text after normalization; omit it when there is no quote")
        ids.add(use["id"])
    return data


def normalized(text):
    # Preserve dashes, word boundaries and punctuation. Dehyphenation, OCR repairs,
    # omissions and bracketed alterations require visual/manual review.
    translation = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\ufb01": "fi", "\ufb02": "fl", "\u00ad": ""})
    return re.sub(r"\s+", " ", text.translate(translation)).strip()


def quote_in_text(quote, text):
    """Normalized match that does not start or end inside a word or number.

    "30 days after entry" must not match "130 days after entry"."""
    needle = normalized(quote)
    prefix = r"(?<!\w)" if re.match(r"\w", needle) else ""
    suffix = r"(?!\w)" if re.search(r"\w$", needle) else ""
    return re.search(prefix + re.escape(needle) + suffix, normalized(text)) is not None


def validate_entry(entry, inv, root):
    if not isinstance(entry, dict):
        raise ValueError("each evidence entry must be a JSON object")
    if entry.get("document_sha256") != inv["document_sha256"]:
        raise ValueError("evidence belongs to another draft")
    if entry.get("inventory_sha256") != inventory_digest(inv):
        raise ValueError("evidence belongs to another inventory; create a new run after inventory changes")
    use = next((u for u in inv["uses"] if u["id"] == entry.get("use")), None)
    if use is None or entry.get("check") not in required_checks(use):
        raise ValueError("evidence names an unknown use or inapplicable check")
    if entry.get("result") not in {"pass", "fail", "unverified", "caution"}:
        raise ValueError("result must be pass, fail, unverified or caution")
    if not isinstance(entry.get("note"), str) or not entry["note"].strip():
        raise ValueError("every check needs a note describing what was reviewed or what blocked it")
    if "provenance" in entry:
        provenance = entry["provenance"]
        if not isinstance(provenance, dict) or any(not isinstance(provenance.get(k), str) or not provenance[k].strip()
                for k in ("origin", "retrieved_at", "version", "extraction_method")):
            raise ValueError("provenance needs origin, retrieved_at, version and extraction_method strings")
        try:
            retrieved = datetime.fromisoformat(provenance["retrieved_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("provenance retrieved_at must be an ISO-8601 timestamp") from exc
        if retrieved.tzinfo is None:
            raise ValueError("provenance retrieved_at needs a timezone")
        if "original_file" in provenance or "original_sha256" in provenance:
            original = source_path(root, provenance.get("original_file"))
            if provenance.get("original_sha256") != digest(original):
                raise ValueError("provenance original source hash differs")
    if entry["result"] == "pass":
        if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("file", "sha256", "locator", "matched")):
            raise ValueError("passing checks need file, sha256, locator and matched source evidence")
        if entry["check"] == "treatment" and use["kind"] == "case" and (not isinstance(entry.get("citator"), str) or not entry["citator"].strip()):
            raise ValueError("case treatment cannot pass without a named citator; use caution for a free-source screen")
    if entry.get("file"):
        path = source_path(root, entry["file"])
        if entry.get("sha256") != digest(path):
            raise ValueError(f"source hash differs: {entry['file']}")
    elif entry.get("sha256"):
        raise ValueError("source hash without a source file")
    if entry.get("method") == "exact-text":
        path = source_path(root, entry["file"])
        if entry["check"] != "verbatim" or path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("exact-text only supports verbatim checks against .txt/.md sources")
        found = quote_in_text(use["quote"], path.read_text(encoding="utf-8-sig"))
        if entry["result"] != ("pass" if found else "fail") or entry.get("matched") != (use["quote"] if found else ""):
            raise ValueError("exact-text result does not match the archived text")
    elif entry["check"] == "verbatim" and entry["result"] == "pass" and Path(entry["file"]).suffix.lower() in {".txt", ".md"}:
        # A manual pass may not assert a quotation that the readable archived text lacks.
        if not quote_in_text(use["quote"], source_path(root, entry["file"]).read_text(encoding="utf-8-sig")):
            raise ValueError("verbatim pass refused: the quotation is not in the archived text; use the quote command, or record fail, caution or unverified")
    return use


def read_log(path, inv, root):
    if not Path(path).exists():
        return []
    entries, seen = [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            validate_entry(entry, inv, root)
        except (ValueError, OSError) as exc:
            raise ValueError(f"log line {number}: {exc}") from exc
        key = (entry["use"], entry["check"])
        if key in seen:
            raise ValueError(f"duplicate evidence for {key}; start a new run for corrections")
        seen.add(key)
        entries.append(entry)
    return entries


def append_entry(log, entry, inv, root):
    if not isinstance(entry, dict):
        raise ValueError("each evidence entry must be a JSON object")
    entry = dict(entry)
    entry.setdefault("inventory_sha256", inventory_digest(inv))
    entries = read_log(log, inv, root)
    validate_entry(entry, inv, root)
    if any((e["use"], e["check"]) == (entry["use"], entry["check"]) for e in entries):
        raise ValueError("check already recorded; preserve this log and start a new run for corrections")
    entry = dict(entry, recorded_at=datetime.now(timezone.utc).isoformat())
    # One writer per log. Preserve every prior byte, including an unterminated
    # final record accepted by read_log; separate it before appending another.
    with Path(log).open("ab+") as stream:
        stream.seek(0, 2)
        if stream.tell():
            stream.seek(-1, 2)
            if stream.read(1) not in (b"\n", b"\r"):
                stream.write(b"\n")
        stream.write((json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8"))


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def report(inv, entries):
    rows, incomplete = [], False
    for use in inv["uses"]:
        checks = {e["check"]: e for e in entries if e["use"] == use["id"]}
        missing = required_checks(use) - checks.keys()
        failed = [k for k, e in checks.items() if e["result"] == "fail"]
        unresolved = [k for k, e in checks.items() if e["result"] in {"unverified", "caution"}]
        status = "FLAGGED" if failed else "UNVERIFIED" if missing or unresolved else "RECORDED PASS"
        incomplete |= status != "RECORDED PASS"
        detail = []
        for name in sorted(required_checks(use)):
            entry = checks.get(name)
            if entry is None:
                detail.append(f"{name}: missing")
            else:
                evidence = f"{entry.get('file', 'no copy')} @ {entry.get('locator', 'no locator')}"
                if name == "verbatim":
                    if entry.get("method") == "exact-text":
                        evidence += ", text compared by the tool"
                    elif entry["result"] == "pass" and Path(entry.get("file") or "").suffix.lower() in {".txt", ".md"}:
                        evidence += ", reviewer attestation; the tool confirmed the quotation appears in the archived text, nothing more"
                    else:
                        evidence += ", reviewer attestation, not compared by the tool"
                detail.append(f"{name}: {entry['result']} ({evidence}); {entry['note']}")
        rows.append("| " + " | ".join(map(cell, [use["id"], use["citation"], use["proposition"], status, "; ".join(detail)])) + " |")
    text = "\n".join([
        "# Citation evidence report", "", f"Document SHA-256: `{inv['document_sha256']}`",
        f"Inventory SHA-256 (canonical JSON): `{inventory_digest(inv)}`", "",
        "RECORDED PASS means every required check has a passing evidence record. It is not an independent finding of legal accuracy, good-law status, or filing readiness. Citation inventory completeness and manual judgments require review. Exact text matching does not verify attribution, pagination, or proposition support. The evidence log is an ordinary local file: this tool detects a changed draft, source or inventory, but not a deleted, inserted or hand-edited log line.", "",
        "| Use | Citation | Proposition | Status | Checks and evidence |", "|---|---|---|---|---|", *rows, "",
        "## Evidence records", "",
        "The records below preserve source hashes, locators, matched text, methods, and reviewer notes. Corrected drafts require a new inventory and log; prior runs remain unchanged.", "", "```json", json.dumps(entries, indent=2, ensure_ascii=False), "```", ""
    ])
    return text, incomplete


def main():
    # A path or name outside the console code page must not turn finished work into a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("record", "quote", "report"))
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--entry", type=Path, help="JSON evidence for record")
    parser.add_argument("--use", help="inventory use id for quote")
    parser.add_argument("--file", help="archive-relative .txt/.md source for quote")
    parser.add_argument("--locator", help="source locator; independently verify the pincite")
    parser.add_argument("--out", type=Path, help="new Markdown report path; never overwritten")
    args = parser.parse_args()
    try:
        inv = inventory(args.inventory, args.document)
        if args.command == "record":
            if not args.entry:
                parser.error("record requires --entry")
            entry = load_json(args.entry)
            if not isinstance(entry, dict):
                raise ValueError("entry must be a JSON object")
            entry.setdefault("document_sha256", inv["document_sha256"])
            append_entry(args.log, entry, inv, args.sources)
        elif args.command == "quote":
            if not all((args.use, args.file, args.locator)):
                parser.error("quote requires --use, --file and --locator")
            use = next((u for u in inv["uses"] if u["id"] == args.use), None)
            if not use or not use.get("quote"):
                raise ValueError("use must have a non-empty quote in the inventory")
            path = source_path(args.sources, args.file)
            if path.suffix.lower() not in {".txt", ".md"}:
                raise ValueError("quote requires a UTF-8 text source; archive/examine the original PDF separately")
            found = quote_in_text(use["quote"], path.read_text(encoding="utf-8-sig"))
            append_entry(args.log, {"document_sha256": inv["document_sha256"], "use": args.use,
                "check": "verbatim", "result": "pass" if found else "fail", "method": "exact-text",
                "file": args.file, "sha256": digest(path), "locator": args.locator,
                "matched": use["quote"] if found else "", "note": "Full-text substring match only; locator and attribution need separate review."}, inv, args.sources)
        else:
            if not args.out or args.out.suffix.lower() != ".md":
                parser.error("report requires --out with a new .md path")
            entries = read_log(args.log, inv, args.sources)
            text, incomplete = report(inv, entries)
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            print(args.out)
            return 1 if incomplete else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"cite_check: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
