#!/usr/bin/env python3
"""Check that registered source URLs answer and that recorded currency lines still match.

This is a link and page-change check, not a legal review. It reads
docs/legal-sources.json, honors each host's robots.txt, requests every distinct
URL once, and reports what it saw. It never writes the registry, so it can never
set or clear legally_reviewed_at. A currency line that still matches says nothing
about whether the law or a reference file is correct.

Exit codes: 0 when every URL answered and no recorded currency line changed;
1 when a URL was unreachable, refused by robots.txt, or its currency line changed
or disappeared; 2 for an unreadable registry or a bad report path.
"""
import argparse
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import time
from typing import Optional
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/legal-sources.json"
USER_AGENT = ("wisconsin-legal-ai-skills-source-check/1 "
              "(+https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills; "
              "monthly link and currency-line check, one request per URL)")
TIMEOUT_SECONDS = 10
MAX_BODY_BYTES = 2_000_000
PAUSE_SECONDS = 1.0
MEANING = ("Link and currency-line check only. It is not a legal review, does not establish "
           "current law, and never sets legally_reviewed_at.")

# docs.legis.wisconsin.gov statute pages carry one line naming the edition, the last Act
# included, and a publication stamp. The pattern stops at the publication stamp.
CURRENCY_PATTERNS = (
    re.compile(r"\d{4}-\d{2} Wisconsin Statutes updated through .{1,400}?\(Published \d{1,2}-\d{1,2}-\d{2}\)"),
)
PUBLISHED = re.compile(r"\(Published (\d{1,2})-(\d{1,2})-(\d{2})\)")


@dataclass
class Response:
    status: Optional[int]
    content_type: str = ""
    body: bytes = b""
    final_url: str = ""
    last_modified: Optional[str] = None
    error: Optional[str] = None


class SameHostRedirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only within the original host, so its robots.txt still applies."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).netloc.lower() != urlsplit(req.full_url).netloc.lower():
            raise urllib.error.HTTPError(newurl, code, f"redirect to another host not followed: {newurl}", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def urllib_fetch(url):
    """Fetch one URL with the descriptive User-Agent and a 10-second timeout."""
    opener = urllib.request.build_opener(SameHostRedirects)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as reply:
            content_type = reply.headers.get("Content-Type", "")
            wanted = "html" in content_type or "text/plain" in content_type
            body = reply.read(MAX_BODY_BYTES) if wanted else b""
            return Response(reply.status, content_type, body, reply.url, reply.headers.get("Last-Modified"))
    except urllib.error.HTTPError as exc:
        return Response(exc.code, final_url=url, error=str(exc.reason))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return Response(None, final_url=url, error=f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}")


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self._skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def page_text(body):
    parser = _Text()
    parser.feed(body.decode("utf-8", "replace"))
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def currency_line(body):
    """Return the page's currency line with whitespace collapsed, or None."""
    text = page_text(body)
    for pattern in CURRENCY_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0)
    return None


def published_date(line):
    """Read the (Published M-D-YY) stamp in a currency line as an ISO date."""
    match = PUBLISHED.search(line or "")
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    try:
        return date(2000 + year, month, day).isoformat()
    except ValueError:
        return None


class Checker:
    """Honor robots.txt per host and request each distinct URL at most once."""

    def __init__(self, fetch=urllib_fetch, pause=time.sleep):
        self.fetch, self.pause = fetch, pause
        self.robots, self.pages, self.requests = {}, {}, []

    def _get(self, url):
        if self.requests:
            self.pause(PAUSE_SECONDS)
        self.requests.append(url)
        return self.fetch(url)

    def allowed(self, url):
        parts = urlsplit(url)
        origin = f"{parts.scheme}://{parts.netloc}"
        if origin not in self.robots:
            reply = self._get(f"{origin}/robots.txt")
            parser = urllib.robotparser.RobotFileParser()
            if reply.status == 200:
                parser.parse(reply.body.decode("utf-8-sig", "replace").splitlines())
                state = "parsed"
            elif reply.status in (401, 403):
                parser.disallow_all, state = True, f"HTTP {reply.status}: treated as disallow all"
            elif reply.status is not None and 400 <= reply.status < 500:
                parser.allow_all, state = True, f"HTTP {reply.status}: no robots.txt"
            else:
                parser.disallow_all = True
                state = f"robots.txt unavailable ({reply.error or reply.status}): not fetched"
            self.robots[origin] = (parser, state)
        parser, state = self.robots[origin]
        return parser.can_fetch(USER_AGENT, url), state

    def page(self, url):
        if url not in self.pages:
            permitted, robots_state = self.allowed(url)
            reply = self._get(url) if permitted else None
            self.pages[url] = (reply, robots_state, permitted)
        return self.pages[url]


def _describe(url, checker):
    reply, robots_state, permitted = checker.page(url)
    record = {"url": url, "robots": robots_state, "fetched": permitted}
    if not permitted:
        record.update(status=None, error="robots.txt does not permit this URL for this client")
        return record, None
    record.update(status=reply.status, final_url=reply.final_url, content_type=reply.content_type,
                  last_modified_header=reply.last_modified, error=reply.error)
    return record, reply


def _why(record):
    status = record.get("status")
    reason = record.get("error") or "no further detail"
    return f"HTTP {status}: {reason}" if status is not None else reason


def check(data, checker, now=None):
    """Return a report dictionary; never modifies data."""
    now = now or datetime.now(timezone.utc)
    results, problems = [], []
    for item in data["sources"]:
        label = item["id"]
        entry, reply = _describe(item["url"], checker)
        entry["id"] = label
        if reply is None or reply.status != 200:
            problems.append(f"{label}: {item['url']} unreachable ({_why(entry)})")
        currency_url, recorded = item.get("currency_url"), item.get("currency_line")
        if currency_url:
            page, page_reply = _describe(currency_url, checker)
            reachable = page_reply is not None and page_reply.status == 200
            observed = currency_line(page_reply.body) if reachable else None
            page.update(recorded_currency_line=recorded, observed_currency_line=observed,
                        recorded_page_changed_at=item.get("page_changed_at"),
                        observed_page_changed_at=published_date(observed))
            if not reachable:
                problems.append(f"{label}: currency page {currency_url} unreachable ({_why(page)})")
                page["currency_changed"] = None
            elif recorded is None:
                page["currency_changed"] = None
            else:
                page["currency_changed"] = observed != recorded
                if observed is None:
                    problems.append(f"{label}: currency line not found on {currency_url}; recorded value was {recorded!r}")
                elif observed != recorded:
                    problems.append(f"{label}: currency line changed on {currency_url}: now {observed!r}, recorded {recorded!r}")
            entry["currency"] = page
        entry["legally_reviewed_at"] = item.get("legally_reviewed_at")
        results.append(entry)
    return {"checked_at": now.isoformat(timespec="seconds"), "meaning": MEANING, "user_agent": USER_AGENT,
            "timeout_seconds": TIMEOUT_SECONDS, "requests": len(checker.requests),
            "results": results, "problems": problems}


def load_registry(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list) or not sources:
        raise ValueError("registry has no sources")
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
            raise ValueError("every source needs an id")
        for key in ("url", "currency_url"):
            value = item.get(key)
            if key == "currency_url" and value is None:
                continue
            if not isinstance(value, str) or urlsplit(value).scheme != "https" or not urlsplit(value).netloc:
                raise ValueError(f"{item['id']}: {key} must be an HTTPS URL")
    return data


def render(report):
    lines = [f"Source check {report['checked_at']} ({report['requests']} requests)", report["meaning"], ""]
    for entry in report["results"]:
        lines.append(f"{entry['id']}: HTTP {entry.get('status')} {entry['url']}")
        currency = entry.get("currency")
        if currency:
            changed = {True: "CHANGED", False: "unchanged", None: "not compared"}[currency["currency_changed"]]
            lines.append(f"  currency line ({changed}): {currency['observed_currency_line']}")
    lines.append("")
    if report["problems"]:
        lines.extend(["Problems:", *(f"  - {problem}" for problem in report["problems"])])
    else:
        lines.append("No problems found.")
    return "\n".join(lines)


def main(argv=None, fetch=urllib_fetch, pause=time.sleep):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, help="path for the JSON report (parent folders are created)")
    parser.add_argument("--registry", default=str(REGISTRY), help="registry to read (default: docs/legal-sources.json)")
    args = parser.parse_args(argv)
    report_path, registry_path = Path(args.report).resolve(), Path(args.registry).resolve()
    try:
        if report_path == registry_path:
            raise ValueError("the report path must not be the registry")
        data = load_registry(registry_path)
    except (OSError, ValueError) as exc:
        print(f"check_sources: {exc}", file=sys.stderr)
        return 2
    report = check(data, Checker(fetch, pause))
    print(render(report))
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        print(f"check_sources: cannot write report: {exc}", file=sys.stderr)
        return 2
    return 1 if report["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
