#!/usr/bin/env python3
"""Validate the county local-rules index and render its Markdown table.

The index records where a county was found posting circuit court local rules on a stated
date. It holds no rule text and makes no statement about what any rule requires. This
script reads two local files and never opens a network connection.

  python scripts/local_rules.py validate
  python scripts/local_rules.py render            # writes the Markdown reference
  python scripts/local_rules.py render --check    # exit 1 if the committed Markdown differs
"""
import argparse
from datetime import date
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/wisconsin-legal-writing"
INDEX = SKILL / "references/local-rules/counties.json"
MARKDOWN = SKILL / "references/local-rules.md"

REVIEW_LABEL = "SOURCE-CHECKED BY AI REVIEW, NOT ATTORNEY-REVIEWED"
COVERAGE = ("rules_posted", "other_documents_only", "none_found", "not_checked")
ACCESS = ("ok", "blocked_by_robots", "http_error", "redirected_off_host", "timeout", "not_attempted")
KINDS = ("rules", "directive_or_order", "judge_practice", "form", "listing_page")
FORMATS = ("pdf_text", "pdf_scan", "html")
HOST_CLASSES = ("county", "court", "outside")
COURT_HOSTS = ("www.wicourts.gov", "wicourts.gov")
# The maintainer's decision of 2026-11-08 allows one read each of one outside-host document
# for these two counties. No other county may record verified metadata from an outside host.
OUTSIDE_HOST_EXCEPTIONS = ("Adams", "Vilas")
TOP_KEYS = {"schema_version", "review_label", "scope", "clerk_directory", "counties"}
DIRECTORY_KEYS = {"url", "page_updated_as_printed", "read_on"}
COUNTY_KEYS = {"county", "coverage", "access", "checked_on", "sites_checked", "county_hosts", "clerk_website",
               "note", "documents", "digest", "legally_reviewed_at"}
DOCUMENT_KEYS = {"link_text", "title_as_printed", "kind", "url", "host", "host_class", "format", "printed_dates",
                 "page_count", "sha256", "last_modified_header", "checked_on", "check_method", "metadata_verified"}
SHA = re.compile(r"[0-9a-f]{64}\Z")


def county_names():
    """The 72 county names, read from the builder's table of Wis. Stat. s. 752.11(1)."""
    spec = importlib.util.spec_from_file_location("build_filing_for_counties", SKILL / "scripts/build_filing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(name for names in module.COURT_OF_APPEALS_DISTRICTS.values() for name in names)


def _https(url):
    parts = urlsplit(url) if isinstance(url, str) else None
    return bool(parts and parts.scheme == "https" and parts.netloc)


def _host(url):
    return urlsplit(url).netloc.lower()


def _forbidden(host):
    return host == "wisbar.org" or host.endswith(".wisbar.org")


def _iso(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate(data, names=None):
    """Return a list of problems; an empty list means the index satisfies every rule."""
    errors = []
    names = county_names() if names is None else names
    if not isinstance(data, dict) or set(data) != TOP_KEYS:
        return [f"top level must have exactly the keys {sorted(TOP_KEYS)}"]
    if data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if data["review_label"] != REVIEW_LABEL:
        errors.append("review_label must be the fixed label")
    if not isinstance(data["scope"], str) or not data["scope"].strip():
        errors.append("scope must be a non-empty string")
    directory = data["clerk_directory"]
    if not isinstance(directory, dict) or set(directory) != DIRECTORY_KEYS:
        errors.append(f"clerk_directory must have exactly the keys {sorted(DIRECTORY_KEYS)}")
    else:
        if not _https(directory["url"]) or _host(directory["url"]) not in COURT_HOSTS:
            errors.append("clerk_directory.url must be an https wicourts.gov address")
        if not _iso(directory["read_on"]):
            errors.append("clerk_directory.read_on must be a date as YYYY-MM-DD")
        if not isinstance(directory["page_updated_as_printed"], str) or not directory["page_updated_as_printed"].strip():
            errors.append("clerk_directory.page_updated_as_printed must be the page's own date text")
    counties = data["counties"]
    if not isinstance(counties, list):
        return errors + ["counties must be a list"]
    listed = [c.get("county") if isinstance(c, dict) else None for c in counties]
    if listed != names:
        errors.append("counties must be exactly the 72 county names of Wis. Stat. s. 752.11(1), once each, in alphabetical order")
    for record in counties:
        label = record.get("county", "<missing>") if isinstance(record, dict) else "<not an object>"
        if not isinstance(record, dict) or set(record) != COUNTY_KEYS:
            errors.append(f"{label}: expected exactly the keys {sorted(COUNTY_KEYS)}")
            continue
        errors += _validate_county(label, record)
    return errors


def _validate_county(label, record):
    errors = []
    coverage, access = record["coverage"], record["access"]
    if coverage not in COVERAGE:
        errors.append(f"{label}: coverage must be one of {list(COVERAGE)}")
    if access not in ACCESS:
        errors.append(f"{label}: access must be one of {list(ACCESS)}")
    if record["digest"] != "":
        errors.append(f"{label}: digest is reserved and must stay empty; the index holds no rule text or summary")
    if record["legally_reviewed_at"] is not None:
        errors.append(f"{label}: legally_reviewed_at must be null; no qualified legal review is recorded")
    for key in ("sites_checked", "county_hosts", "documents"):
        if not isinstance(record[key], list):
            errors.append(f"{label}: {key} must be a list")
            return errors
    if not isinstance(record["note"], str):
        errors.append(f"{label}: note must be a string")
    website = record["clerk_website"]
    if website is not None:
        # Copied exactly as the state clerk contact page lists it, which for some counties is plain http.
        parts = urlsplit(website) if isinstance(website, str) else None
        if not parts or parts.scheme not in ("http", "https") or not parts.netloc or _forbidden(parts.netloc.lower()):
            errors.append(f"{label}: clerk_website must be null or the web address the state directory lists, never wisbar.org")
    for url in record["sites_checked"]:
        if not _https(url) or _forbidden(_host(url)):
            errors.append(f"{label}: sites_checked entries must be https addresses, never wisbar.org")
    for host in record["county_hosts"]:
        if not isinstance(host, str) or host != host.lower() or "/" in host or _forbidden(host) or host in COURT_HOSTS:
            errors.append(f"{label}: county_hosts entries must be lower-case host names of the county's own sites")
    untouched = coverage == "not_checked" and access == "not_attempted"
    if untouched:
        if record["checked_on"] is not None or record["sites_checked"] or record["documents"] or record["county_hosts"]:
            errors.append(f"{label}: a county that was not checked carries no date, sites, hosts or documents")
        return errors
    if access == "not_attempted":
        errors.append(f"{label}: a county with a coverage finding needs the access outcome of the attempt")
    if not _iso(record["checked_on"]):
        errors.append(f"{label}: checked_on must be a date as YYYY-MM-DD once a check was attempted")
    if not record["sites_checked"]:
        errors.append(f"{label}: sites_checked must name the pages requested")
    if coverage == "not_checked":
        if access == "ok":
            errors.append(f"{label}: a completed check must record what it found, not not_checked")
        if record["documents"]:
            errors.append(f"{label}: an incomplete check records no documents")
        if not record["note"].strip():
            errors.append(f"{label}: an incomplete check needs a note saying what happened")
        return errors
    if access != "ok":
        errors.append(f"{label}: a coverage finding needs access ok; record an incomplete check as not_checked")
    if coverage == "none_found" and record["documents"]:
        errors.append(f"{label}: none_found records no documents")
    if coverage in ("rules_posted", "other_documents_only") and not record["documents"]:
        errors.append(f"{label}: {coverage} needs at least one document")
    kinds = [d.get("kind") for d in record["documents"] if isinstance(d, dict)]
    if coverage == "rules_posted" and "rules" not in kinds:
        errors.append(f"{label}: rules_posted needs a document of kind rules")
    if coverage == "other_documents_only" and "rules" in kinds:
        errors.append(f"{label}: other_documents_only cannot hold a document of kind rules")
    for index, document in enumerate(record["documents"]):
        errors += _validate_document(f"{label} document {index + 1}", record, document)
    return errors


def _validate_document(label, record, document):
    errors = []
    if not isinstance(document, dict) or set(document) != DOCUMENT_KEYS:
        return [f"{label}: expected exactly the keys {sorted(DOCUMENT_KEYS)}"]
    if document["kind"] not in KINDS:
        errors.append(f"{label}: kind must be one of {list(KINDS)}")
    if not isinstance(document["link_text"], str) or not document["link_text"].strip():
        errors.append(f"{label}: link_text must be the link's words on the listing page")
    if not _https(document["url"]):
        return errors + [f"{label}: url must be an https address"]
    host = _host(document["url"])
    if _forbidden(host):
        errors.append(f"{label}: wisbar.org copies are never indexed")
    if document["host"] != host:
        errors.append(f"{label}: host must be the url's own host, {host}")
    expected = "court" if host in COURT_HOSTS else "county" if host in record["county_hosts"] else "outside"
    if document["host_class"] != expected:
        errors.append(f"{label}: host_class must be {expected} for {host}")
    verified = document["metadata_verified"]
    if not isinstance(verified, bool):
        errors.append(f"{label}: metadata_verified must be true or false")
        return errors
    if expected == "outside" and verified and record["county"] not in OUTSIDE_HOST_EXCEPTIONS:
        errors.append(f"{label}: metadata from an outside host is unverified except for the two approved documents")
    facts = ("title_as_printed", "format", "sha256", "checked_on", "check_method")
    if not verified:
        filled = [k for k in facts + ("page_count", "last_modified_header") if document[k] is not None] + (["printed_dates"] if document["printed_dates"] else [])
        if filled:
            errors.append(f"{label}: an unverified document records only its link; remove {filled}")
        return errors
    if document["format"] not in FORMATS:
        errors.append(f"{label}: format must be one of {list(FORMATS)}")
    if not isinstance(document["sha256"], str) or not SHA.match(document["sha256"]):
        errors.append(f"{label}: sha256 must be 64 lower-case hex digits of the response body")
    if not _iso(document["checked_on"]):
        errors.append(f"{label}: checked_on must be a date as YYYY-MM-DD")
    for key in ("title_as_printed", "check_method"):
        if not isinstance(document[key], str) or not document[key].strip():
            errors.append(f"{label}: {key} must be a non-empty string")
    pages = document["page_count"]
    if document["format"] == "html":
        if pages is not None:
            errors.append(f"{label}: an HTML page has no page count")
    elif not isinstance(pages, int) or isinstance(pages, bool) or pages < 1:
        errors.append(f"{label}: a PDF needs its page count")
    dates = document["printed_dates"]
    if not isinstance(dates, list) or any(not isinstance(d, dict) or set(d) != {"label", "as_printed"}
                                          or not all(isinstance(v, str) and v.strip() for v in d.values()) for d in dates):
        errors.append(f"{label}: printed_dates must be a list of label and as_printed pairs copied from the document")
    return errors


def _cell(text):
    return text.replace("|", "\\|").replace("\n", " ")


def _status(record):
    coverage, access, on = record["coverage"], record["access"], record["checked_on"]
    if coverage == "not_checked" and access == "not_attempted":
        return "Not yet indexed."
    if coverage == "not_checked":
        return f"Check incomplete on {on} ({access.replace('_', ' ')}). The index cannot say what this county posts."
    if coverage == "none_found":
        return f"No in-scope copy found in the government sources checked as of {on}."
    if coverage == "rules_posted":
        if not any(d["kind"] == "rules" and d["metadata_verified"] for d in record["documents"]):
            return f"A link to a rules document was found on {on}; the document was not read."
        return f"Rules found posted on {on}."
    return f"Other court documents found posted on {on}; no rules document found."


def _document_lines(document):
    if not document["metadata_verified"]:
        return [f"- **{_cell(document['link_text'])}** (link text on the county's page; {document['kind'].replace('_', ' ')}). "
                f"<{document['url']}>. Host: `{document['host']}`, which is not a county or court site. "
                "Title, date, length and contents were not read."]
    dates = "; ".join(f"{d['label']}: {d['as_printed']}" for d in document["printed_dates"]) or "no date printed"
    length = "HTML page" if document["format"] == "html" else f"{document['page_count']} pages, {'scanned image, no text layer' if document['format'] == 'pdf_scan' else 'text PDF'}"
    return [f"- **{_cell(document['title_as_printed'])}** ({document['kind'].replace('_', ' ')}; link text \"{_cell(document['link_text'])}\"). "
            f"<{document['url']}>. Printed dates: {dates}. {length}. Read {document['checked_on']}; "
            f"SHA-256 of that response `{document['sha256'][:16]}`."]


USAGE = """# County local rules: where they were found posted

<!-- Generated by scripts/local_rules.py from references/local-rules/counties.json. Do not edit by hand. -->

{label}. This is an index of locations. It holds no rule text and says nothing about what any
rule requires. It is a snapshot taken on the dates shown; a county may have posted a newer
copy since. The list covers the counties checked so far and is never complete coverage.

## How to use it

1. Give the county's status and its check date first, exactly as the table states them.
2. **Not yet indexed:** say so, give no date, and point to the clerk's website in the table
   or to the state court system's clerk directory.
3. **Check incomplete:** say the check of the named site was incomplete on that date and why,
   and that the index cannot say what the site posts.
4. **No in-scope copy found:** say that as of the date no copy was found on the government
   pages checked. Never say the county has no local rules. Tell the user to ask the Clerk of
   Circuit Court for the current local rules, any directives or administrative orders, and the
   assigned judge's procedures.
5. **A link found but not read:** give the link and its host, and say that the title, date and
   contents were not read. Do not describe the document.
6. **Rules found posted:** give each document's title as printed, its printed dates with their
   labels, its format and its address. If the session can open the address, read the document
   before saying anything a rule requires, and mark what you say `[LOCAL RULE]`. If it cannot,
   say the document was not read.
7. In every case add the check the other references already require: the scheduling order
   and any standing order of the assigned judge.
8. Never offer a copy from wisbar.org.

Clerk websites in the table are the addresses the state court system's
[clerk contact page]({directory}) listed when it was read on {read_on} (that page printed
"Updated: {updated}"). They were not opened for this index unless the county was checked.
"""


def render(data):
    lines = [USAGE.format(label=data["review_label"].capitalize().replace("ai review", "AI review"),
                          directory=data["clerk_directory"]["url"], read_on=data["clerk_directory"]["read_on"],
                          updated=data["clerk_directory"]["page_updated_as_printed"]).rstrip("\n"), "",
             "## Counties", "", "| County | Status | Clerk's website |", "|---|---|---|"]
    for record in data["counties"]:
        site = f"<{record['clerk_website']}>" if record["clerk_website"] else "not listed"
        lines.append(f"| {record['county']} | {_cell(_status(record))} | {site} |")
    detailed = [r for r in data["counties"] if not (r["coverage"] == "not_checked" and r["access"] == "not_attempted")]
    if detailed:
        lines += ["", "## What each check found", ""]
    for record in detailed:
        lines += [f"### {record['county']} County", "", _status(record), ""]
        lines.append("Pages requested: " + ", ".join(f"<{u}>" for u in record["sites_checked"]) + ".")
        if record["note"].strip():
            lines += ["", record["note"].strip()]
        if record["documents"]:
            lines.append("")
            for document in record["documents"]:
                lines += _document_lines(document)
        lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("validate", "render"))
    parser.add_argument("--check", action="store_true", help="with render: compare with the committed Markdown")
    args = parser.parse_args()
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"local_rules: cannot read the index: {exc}", file=sys.stderr)
        return 2
    errors = validate(data)
    if errors:
        print("\n".join(f"local_rules: {e}" for e in errors), file=sys.stderr)
        return 2
    if args.command == "validate":
        checked = sum(1 for c in data["counties"] if c["checked_on"])
        print(f"Validated {len(data['counties'])} county records ({checked} with a check attempted); no rule text is held and no law was checked.")
        return 0
    text = render(data)
    if args.check:
        if not MARKDOWN.is_file() or MARKDOWN.read_text(encoding="utf-8") != text:
            print("local_rules: references/local-rules.md differs from the rendering; run render", file=sys.stderr)
            return 1
        print("The committed Markdown matches the index.")
        return 0
    MARKDOWN.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {MARKDOWN.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
