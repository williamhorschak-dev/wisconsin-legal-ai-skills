#!/usr/bin/env python3
"""Validate the federal source survey register; never certify law.

The register records which official federal pages and documents were fetched on a stated
day, what each printed about its own date, how much of it was read, and the SHA-256 of the
response. It holds no rule text and no statement of law. This script reads one local file
and never opens a network connection.

  python scripts/federal_sources.py validate
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "docs/federal-sources.json"

TOP_KEYS = {"schema_version", "scope", "method", "permitted_hosts", "hosts", "sources", "not_reached"}
HOST_KEYS = {"host", "robots_url", "robots_status", "robots_sha256", "crawl_delay_seconds", "retrieved_at_utc", "note"}
SOURCE_KEYS = {"id", "issuer", "title", "title_source", "url", "format", "pages", "date_printed", "date_kind",
               "retrieved_at_utc", "bytes", "sha256", "read_extent", "note", "recheck_trigger", "legally_reviewed_at"}
NOT_REACHED_KEYS = {"url", "reason", "note"}

ISSUERS = ("U.S. Courts", "U.S. Code (GPO)", "7th Cir.", "E.D. Wis.", "W.D. Wis.")
TITLE_SOURCES = ("face", "link_label", "descriptive")
FORMATS = ("html", "pdf")
DATE_KINDS = ("edition", "effective", "amendment", "revision", "entry", "update_notice", "projection", "none_printed")
READ_EXTENTS = ("full", "part", "keyword", "links", "date_only", "not_read")
REASONS = ("http_404", "redirect_to_http", "script_redirect", "robots_disallow")
# A robots request answered 404 means the host has no robots file; any other answer but 200 is not a reading.
ROBOTS_STATUSES = (200, 404)

SHA = re.compile(r"[0-9a-f]{64}\Z")
SOURCE_ID = re.compile(r"S-[0-9]{2,3}\Z")
STAMP = "%Y-%m-%dT%H:%M:%SZ"
MAX_TITLE, MAX_NOTE = 300, 400
# Paid databases and bar association copies are never sources here, and nothing read on one is recorded here.
FORBIDDEN_WORDS = ("westlaw", "keycite", "lexis", "wisbar")
DASHES = ("\u2013", "\u2014")


def permitted(host):
    """uscourts.gov and its subdomains, uscode.house.gov, govinfo.gov and www.govinfo.gov."""
    host = (host or "").lower()
    return (host == "uscourts.gov" or host.endswith(".uscourts.gov")
            or host in ("uscode.house.gov", "govinfo.gov", "www.govinfo.gov"))


def _official(url):
    """An https address on a permitted host, with no user name, password or port."""
    if not isinstance(url, str):
        return False
    try:
        parts = urlsplit(url)
        return parts.scheme == "https" and parts.netloc == (parts.hostname or "") and permitted(parts.hostname)
    except ValueError:
        return False


def _stamp(value):
    if not isinstance(value, str):
        return False
    try:
        datetime.strptime(value, STAMP)
        return True
    except ValueError:
        return False


def _text(value, limit, *, empty_ok=False):
    return isinstance(value, str) and len(value) <= limit and (empty_ok or bool(value.strip())) and value == value.strip()


def _whole(value, low):
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _keys(label, record, expected, errors):
    if not isinstance(record, dict):
        errors.append(f"{label}: must be an object")
        return False
    missing, extra = sorted(expected - set(record)), sorted(set(record) - expected)
    if missing:
        errors.append(f"{label}: missing key(s): {', '.join(missing)}")
    if extra:
        # A new field needs a schema change and a review; this is what keeps rule text out of the file.
        errors.append(f"{label}: unknown key(s): {', '.join(extra)}")
    return not missing and not extra


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def validate(data):
    """Return a list of problems; an empty list means the file obeys the register's rules, not that any law is current."""
    errors = []
    if not _keys("register", data, TOP_KEYS, errors):
        return errors
    if data["schema_version"] != 1 or isinstance(data["schema_version"], bool):
        errors.append("register: schema_version must be 1")
    for key in ("scope", "method", "permitted_hosts"):
        if not _text(data[key], 1000):
            errors.append(f"register: {key} must be text")
    for key in ("hosts", "sources", "not_reached"):
        if not isinstance(data[key], list):
            errors.append(f"register: {key} must be a list")
            return errors
    if not data["sources"]:
        errors.append("register: no sources")

    for text in _strings(data):
        low = text.lower()
        for word in FORBIDDEN_WORDS:
            if word in low:
                errors.append(f"register: the word {word!r} may not appear anywhere in this file")
        if any(dash in text for dash in DASHES):
            errors.append(f"register: an en dash or em dash appears in {text[:40]!r}")

    robots_read = set()
    for position, host in enumerate(data["hosts"]):
        label = f"hosts[{position}]"
        if not _keys(label, host, HOST_KEYS, errors):
            continue
        name = host["host"]
        label = f"host {name!r}"
        if not isinstance(name, str) or not permitted(name) or name != name.lower():
            errors.append(f"{label}: not a permitted host")
            continue
        if name in robots_read:
            errors.append(f"{label}: listed twice")
        if host["robots_url"] != f"https://{name}/robots.txt":
            errors.append(f"{label}: robots_url must be https://{name}/robots.txt")
        status = host["robots_status"]
        if isinstance(status, bool) or status not in ROBOTS_STATUSES:
            errors.append(f"{label}: robots_status must be 200, or 404 for a host with no robots file")
        elif (status == 200) != (isinstance(host["robots_sha256"], str) and bool(SHA.match(host["robots_sha256"]))):
            errors.append(f"{label}: robots_sha256 is the hash of a robots file that was read, and null when there is none")
        else:
            robots_read.add(name)
        delay = host["crawl_delay_seconds"]
        if delay is not None and (isinstance(delay, bool) or not isinstance(delay, (int, float)) or not 0 < delay <= 120):
            errors.append(f"{label}: crawl_delay_seconds must be null or a number of seconds up to 120")
        if not _stamp(host["retrieved_at_utc"]):
            errors.append(f"{label}: retrieved_at_utc must look like 2026-11-14T02:20:13Z")
        if not _text(host["note"], MAX_NOTE, empty_ok=True):
            errors.append(f"{label}: note must be text of at most {MAX_NOTE} characters")

    ids, urls = set(), set()
    for position, source in enumerate(data["sources"]):
        label = f"sources[{position}]"
        if not _keys(label, source, SOURCE_KEYS, errors):
            continue
        label = str(source["id"])
        if not isinstance(source["id"], str) or not SOURCE_ID.match(source["id"]):
            errors.append(f"{label}: id must look like S-09")
        if source["id"] in ids:
            errors.append(f"{label}: duplicate id")
        ids.add(source["id"])
        if not _official(source["url"]):
            errors.append(f"{label}: url must be an https address on a permitted host")
        else:
            if source["url"] in urls:
                errors.append(f"{label}: duplicate url")
            urls.add(source["url"])
            if urlsplit(source["url"]).hostname not in robots_read:
                errors.append(f"{label}: no robots reading is recorded for its host")
        if source["issuer"] not in ISSUERS:
            errors.append(f"{label}: issuer must be one of {', '.join(ISSUERS)}")
        if not _text(source["title"], MAX_TITLE):
            errors.append(f"{label}: title must be text of at most {MAX_TITLE} characters")
        if source["title_source"] not in TITLE_SOURCES:
            errors.append(f"{label}: title_source must be one of {', '.join(TITLE_SOURCES)}")
        if source["format"] not in FORMATS:
            errors.append(f"{label}: format must be html or pdf")
        elif (source["format"] == "pdf") != _whole(source["pages"], 1) or (source["format"] == "html" and source["pages"] is not None):
            errors.append(f"{label}: pages is a page count for a pdf and null for html")
        kind, printed = source["date_kind"], source["date_printed"]
        if kind not in DATE_KINDS:
            errors.append(f"{label}: date_kind must be one of {', '.join(DATE_KINDS)}")
        elif (kind == "none_printed") != (printed is None):
            errors.append(f"{label}: date_printed is null exactly when date_kind is none_printed")
        elif printed is not None and not _text(printed, 120):
            errors.append(f"{label}: date_printed must be the date text as printed, at most 120 characters")
        if not _stamp(source["retrieved_at_utc"]):
            errors.append(f"{label}: retrieved_at_utc must look like 2026-11-14T02:20:13Z")
        if not _whole(source["bytes"], 1):
            errors.append(f"{label}: bytes must be a positive whole number")
        if not isinstance(source["sha256"], str) or not SHA.match(source["sha256"]):
            errors.append(f"{label}: sha256 must be 64 lowercase hexadecimal characters")
        if source["read_extent"] not in READ_EXTENTS:
            errors.append(f"{label}: read_extent must be one of {', '.join(READ_EXTENTS)}")
        if not _text(source["note"], MAX_NOTE, empty_ok=True):
            errors.append(f"{label}: note must be text of at most {MAX_NOTE} characters")
        if source["recheck_trigger"] is not None and not _text(source["recheck_trigger"], 200):
            errors.append(f"{label}: recheck_trigger must be null or text of at most 200 characters")
        if source["legally_reviewed_at"] is not None:
            errors.append(f"{label}: legally_reviewed_at stays null in this file; a reviewed proposition is recorded in "
                          "docs/legal-sources.json by a qualified reviewer, never here and never by a script")

    for position, item in enumerate(data["not_reached"]):
        label = f"not_reached[{position}]"
        if not _keys(label, item, NOT_REACHED_KEYS, errors):
            continue
        if not _official(item["url"]):
            errors.append(f"{label}: url must be an https address on a permitted host")
        elif item["url"] in urls:
            errors.append(f"{label}: {item['url']} is also listed as a source")
        if item["reason"] not in REASONS:
            errors.append(f"{label}: reason must be one of {', '.join(REASONS)}")
        if not _text(item["note"], MAX_NOTE):
            errors.append(f"{label}: note must be text of at most {MAX_NOTE} characters")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--register", default=str(REGISTER), help="register to read (default: docs/federal-sources.json)")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.register).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"federal_sources: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print("federal_sources: " + "\n".join(errors), file=sys.stderr)
        return 2
    print(f"Validated {len(data['sources'])} federal source records on {len(data['hosts'])} hosts; "
          "no address was requested and legal currency was not checked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
