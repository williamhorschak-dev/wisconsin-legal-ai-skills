#!/usr/bin/env python3
"""Check source responses and recorded currency lines without changing the registry.

Outcomes are ok, changed, refused, and transient. HTTP 404/410 sources are
refused (reason http_404/http_410), not a fifth outcome. Exit precedence is
2 (configuration/report failure), 1 (changed/refused), 3 (transient), 0 (all
required checks completed successfully). An unexpected unconditional 304 is
refused. PDF checks validate response type/completeness only, not content
changes; HTML fingerprints, conditional requests and county loading are absent.

Every network attempt, including robots, redirect hops and one retry per URL,
uses one host scheduler: maximum of 2 seconds, robots Crawl-delay, the legislature
host's 5 seconds, and Retry-After. A 20-second supervised worker bounds the whole
attempt, including DNS and a stalled or slowly streaming body. A 720-second run
budget admits an attempt only with its timeout and 1-second cleanup reserve.
Responses are capped at 16 MB; oversized/incomplete responses are refused.

The JSON retains the original results/currency/problems shape and adds outcomes,
coverage, attempt details and checker_exit.
Summary checked/unchecked count source records: checked requires every required
response/currency check for that record to complete. Required/completed check
counts also appear separately. Link-only success is response_valid, never a PDF
content comparison. Per-source severity is refused > changed > transient > ok;
all component diagnostics remain visible even when one controls the outcome.
This is not legal review and copies legally_reviewed_at into the report only.
"""
import argparse
import base64
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_CEILING
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Optional
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/legal-sources.json"
USER_AGENT = ("wisconsin-legal-ai-skills-source-check/2 "
              "(+https://github.com/williamhorschak-dev/wisconsin-legal-ai-skills; "
              "monthly link and currency-line check)")
TIMEOUT_SECONDS = 20
RUN_BUDGET_SECONDS = 720
CLEANUP_SECONDS = 1
MAX_BODY_BYTES = 16_000_000
PAUSE_SECONDS = 2.0
MAX_REDIRECTS = 5
MEANING = ("Link, response-integrity and currency-line check only. It is not a legal review, "
           "does not establish current law, and never sets legally_reviewed_at.")
SEVERITY = {"ok": 0, "transient": 1, "changed": 2, "refused": 3}
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
    headers: dict = field(default_factory=dict)
    complete: bool = True
    reason: Optional[str] = None


class NoRedirects(urllib.request.HTTPRedirectHandler):
    """The scheduler, never urllib, owns every redirect attempt."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_once(url, method, headers, timeout):
    """Worker-only blocking I/O; the parent enforces an absolute deadline."""
    opener = urllib.request.build_opener(NoRedirects)
    request = urllib.request.Request(url, method=method, headers=headers)
    try:
        try:
            reply = opener.open(request, timeout=timeout)
        except urllib.error.HTTPError as exc:
            reply = exc
        with reply:
            response_headers = dict(reply.headers.items())
            if reply.code != 200:
                return Response(reply.code, final_url=url, headers=response_headers)
            body = reply.read(MAX_BODY_BYTES + 1)
            complete = len(body) <= MAX_BODY_BYTES
            return Response(reply.code, reply.headers.get("Content-Type", ""), body[:MAX_BODY_BYTES],
                            url, reply.headers.get("Last-Modified"), headers=response_headers,
                            complete=complete, reason=None if complete else "body_size_limit")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return Response(None, final_url=url, error=f"{type(exc).__name__}: {reason}",
                        reason="timeout" if isinstance(reason, TimeoutError) else "network_error")
    except Exception as exc:
        # IncompleteRead and malformed HTTP are response failures, not valid bodies.
        return Response(None, final_url=url, error=f"{type(exc).__name__}: {exc}",
                        complete=False, reason="invalid_response")


def urllib_fetch(url, *, method="GET", headers=None, timeout=TIMEOUT_SECONDS):
    """Bound worker execution, DNS, headers and body after process creation."""
    request = json.dumps({"url": url, "method": method, "headers": headers or {}, "timeout": timeout})
    worker = subprocess.Popen([sys.executable, "-I", str(Path(__file__).resolve()), "--fetch-worker"],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True)
    try:
        output, _ = worker.communicate(request, timeout=timeout)
    except subprocess.TimeoutExpired:
        worker.kill()
        try:
            worker.communicate(timeout=CLEANUP_SECONDS)
        except subprocess.TimeoutExpired:
            # The kill has been issued; never wait past the cleanup reserve.
            for pipe in (worker.stdin, worker.stdout, worker.stderr):
                if pipe:
                    pipe.close()
            return Response(None, final_url=url, error="request deadline exceeded; worker cleanup timed out", reason="timeout")
        return Response(None, final_url=url, error="request deadline exceeded", reason="timeout")
    if worker.returncode:
        return Response(None, final_url=url, error="request worker failed", reason="network_error")
    try:
        result = json.loads(output)
        result["body"] = base64.b64decode(result["body"], validate=True)
        return Response(**result)
    except (ValueError, TypeError, KeyError):
        return Response(None, final_url=url, error="invalid request worker response", reason="invalid_response")


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
    match = PUBLISHED.search(line or "")
    if not match:
        return None
    month, day, year = (int(part) for part in match.groups())
    try:
        return date(2000 + year, month, day).isoformat()
    except ValueError:
        return None


def normalized_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def origin(url):
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc.lower()}"


def header(reply, name):
    return next((str(value) for key, value in reply.headers.items() if key.lower() == name.lower()), None)


def integrity_error(reply, expected_pdf=False, allow_empty=False):
    if not reply.complete or len(reply.body) > MAX_BODY_BYTES:
        return reply.reason or "truncated_body"
    length = header(reply, "Content-Length")
    if length is not None:
        if not re.fullmatch(r"[0-9]{1,12}", length) or int(length) != len(reply.body):
            return "content_length_mismatch"
    encoding = header(reply, "Content-Encoding")
    if encoding and encoding.lower() != "identity":
        return "unsupported_content_encoding"
    if expected_pdf:
        if reply.content_type.split(";", 1)[0].strip().lower() != "application/pdf":
            return "unexpected_pdf_type"
        if not reply.body.startswith(b"%PDF-") or not reply.body.rstrip().endswith(b"%%EOF"):
            return "invalid_pdf_body"
    elif not reply.body and not allow_empty:
        return "empty_body"
    return None


def robots_lines(body):
    """Round numeric fractional Crawl-delay up; refuse unrecognized delay syntax."""
    lines = body.decode("utf-8-sig", "replace").splitlines()
    for index, line in enumerate(lines):
        key, separator, value = line.partition(":")
        if separator and key.strip().lower() == "crawl-delay":
            value = value.split("#", 1)[0].strip()
            if len(value) > 40 or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", value):
                raise ValueError("invalid_crawl_delay")
            delay = Decimal(value).to_integral_value(rounding=ROUND_CEILING)
            lines[index] = f"Crawl-delay: {delay}"
    return lines


def result(url, outcome, reason=None, reply=None, **extra):
    record = {"url": url, "outcome": outcome, "reason": reason,
              "status": reply.status if reply else None, "fetched": bool(extra.get("attempts", 0)),
              "comparison": "response_valid" if outcome == "ok" else "not_performed",
              "completed": outcome == "ok", "error": reply.error if reply else None}
    if reply:
        record.update(final_url=reply.final_url or url, content_type=reply.content_type,
                      last_modified_header=reply.last_modified)
    record.update(extra)
    return record


class Checker:
    """One scheduler and retry allowance shared by robots, redirects and sources."""

    def __init__(self, fetch=urllib_fetch, pause=time.sleep, clock=time.monotonic,
                 wall_clock=time.time, budget=RUN_BUDGET_SECONDS):
        self.fetch, self.pause, self.clock, self.wall_clock = fetch, pause, clock, wall_clock
        self.deadline = clock() + budget
        self.robots, self.pages, self.responses = {}, {}, {}
        self.requests, self.attempts = [], {}
        self.last_start, self.delays, self.retry_until = {}, {}, {}

    def _delay(self, url):
        floor = 5.0 if urlsplit(url).hostname == "docs.legis.wisconsin.gov" else PAUSE_SECONDS
        return max(floor, self.delays.get(origin(url), 0))

    def _retry_after(self, reply):
        value = header(reply, "Retry-After")
        if value is None:
            return 0
        if re.fullmatch(r"[0-9]+", value.strip()):
            # Any very large valid delay exceeds this bounded run.
            return float(value.strip()) if len(value.strip()) < 12 else float("inf")
        try:
            stamp = parsedate_to_datetime(value)
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            return max(0.0, stamp.timestamp() - self.wall_clock())
        except (ValueError, TypeError, OverflowError):
            return 0

    def _attempt(self, url):
        host = origin(url)
        now = self.clock()
        ready = max(now, self.last_start.get(host, now - self._delay(url)) + self._delay(url),
                    self.retry_until.get(host, now))
        if ready + TIMEOUT_SECONDS + CLEANUP_SECONDS > self.deadline:
            reason = "retry_after_exceeds_budget" if self.retry_until.get(host, 0) > now else "budget_exhausted"
            return None, reason
        if ready > now:
            self.pause(ready - now)
        if self.clock() + TIMEOUT_SECONDS + CLEANUP_SECONDS > self.deadline:
            return None, "budget_exhausted"
        attempt = self.attempts.get(url, 0) + 1
        self.attempts[url] = attempt
        started = self.clock()
        self.last_start[host] = started
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        self.requests.append({"method": "GET", "url": url, "headers": dict(headers),
                              "start_time": started, "attempt": attempt, "timeout": TIMEOUT_SECONDS})
        try:
            reply = self.fetch(url, method="GET", headers=headers, timeout=TIMEOUT_SECONDS)
        except (TimeoutError, OSError) as exc:
            reply = Response(None, error=str(exc), reason="timeout" if isinstance(exc, TimeoutError) else "network_error")
        wait = self._retry_after(reply)
        if wait:
            self.retry_until[host] = max(self.retry_until.get(host, 0), self.clock() + wait)
        return reply, None

    def _request(self, url):
        if url in self.responses:
            return self.responses[url]
        honored = False
        while self.attempts.get(url, 0) < 2:
            reply, deferred = self._attempt(url)
            if deferred:
                value = (None, "transient", deferred, honored)
                break
            if reply.reason == "invalid_response" or not reply.complete:
                value = (reply, "refused", reply.reason or "truncated_body", honored)
                break
            retryable = reply.status is None or reply.status == 429 or (reply.status is not None and 500 <= reply.status <= 599)
            if not retryable:
                value = (reply, "ok", None, honored)
                break
            reason = reply.reason or (f"http_{reply.status}" if reply.status else "network_error")
            value = (reply, "transient", reason, honored)
            if self.attempts[url] == 2:
                break
            honored = self._retry_after(reply) > 0
        self.responses[url] = value
        return value

    def _chain(self, url, robots=False):
        initial, current, visited = url, url, set()
        while True:
            if current in visited or len(visited) > MAX_REDIRECTS:
                return result(initial, "refused", "redirect_limit", attempts=self.attempts.get(initial, 0)), None
            visited.add(current)
            reply, outcome, reason, honored = self._request(current)
            attempts = sum(self.attempts.get(item, 0) for item in visited)
            record = result(initial, outcome, reason, reply, attempts=attempts, retry_after_honored=honored)
            if outcome != "ok":
                return record, reply
            if reply.final_url and normalized_url(reply.final_url) != current:
                record.update(outcome="refused", reason="transport_followed_redirect", completed=False,
                              comparison="not_performed")
                return record, reply
            if reply.status in (301, 302, 303, 307, 308):
                location = header(reply, "Location") or ""
                try:
                    target = normalized_url(urljoin(current, location))
                    parts = urlsplit(target)
                    if (not parts.hostname or parts.username or parts.password or parts.port not in (None, 443)
                            or any(character.isspace() for character in target)):
                        raise ValueError("invalid redirect URL")
                except ValueError:
                    record.update(outcome="refused", reason="invalid_redirect_location", completed=False,
                                  comparison="not_performed", redirect_target=location, redirect_followed=False)
                    return record, reply
                record.update(redirect_target=target, redirect_followed=False)
                if origin(target) != origin(initial):
                    record.update(outcome="refused", reason="off_host_redirect", completed=False,
                                  comparison="not_performed")
                    return record, reply
                if not header(reply, "Location"):
                    record.update(outcome="refused", reason="missing_redirect_location", completed=False,
                                  comparison="not_performed")
                    return record, reply
                if not robots:
                    allowed, state, robots_outcome = self.allowed(target)
                    if not allowed:
                        record.update(outcome=robots_outcome, reason=state, completed=False, comparison="not_performed")
                        return record, reply
                current = target
                continue
            if reply.status != 200:
                reason = "unexpected_304_without_baseline" if reply.status == 304 else f"http_{reply.status}"
                record.update(outcome="refused", reason=reason, completed=False, comparison="not_performed")
            return record, reply

    def allowed(self, url):
        host = origin(url)
        if host not in self.robots:
            record, reply = self._chain(f"{host}/robots.txt", robots=True)
            parser = urllib.robotparser.RobotFileParser()
            if reply and reply.status in (404, 410):
                parser.allow_all, state, outcome = True, f"HTTP {reply.status}: no robots.txt", "ok"
            elif record["outcome"] == "transient":
                state, outcome = "robots_unavailable", "transient"
                record["underlying_reason"] = record["reason"]
            elif record["outcome"] != "ok":
                state, outcome = (f"robots_http_{reply.status}" if reply and reply.status in (401, 403)
                                  else record["reason"]), "refused"
            else:
                invalid = integrity_error(reply, allow_empty=True)
                mime = reply.content_type.split(";", 1)[0].strip().lower()
                if invalid or mime not in ("text/plain", ""):
                    state, outcome = invalid or "invalid_robots_type", "refused"
                else:
                    try:
                        parser.parse(robots_lines(reply.body))
                        self.delays[host] = parser.crawl_delay(USER_AGENT) or parser.crawl_delay("*") or 0
                        state, outcome = "parsed", "ok"
                    except ValueError:
                        state, outcome = "invalid_crawl_delay", "refused"
            self.robots[host] = (parser, state, outcome, record)
        parser, state, outcome, _ = self.robots[host]
        if outcome != "ok":
            return False, state, outcome
        return (True, state, "ok") if parser.can_fetch(USER_AGENT, url) else (False, "robots_disallow", "refused")

    def page(self, url):
        url = normalized_url(url)
        if url not in self.pages:
            permitted, state, outcome = self.allowed(url)
            if permitted:
                record, reply = self._chain(url)
                if record["outcome"] == "ok":
                    expected_pdf = urlsplit(url).path.lower().endswith(".pdf")
                    invalid = integrity_error(reply, expected_pdf=expected_pdf)
                    if invalid:
                        record.update(outcome="refused", reason=invalid, completed=False, comparison="not_performed")
            else:
                record, reply = result(url, outcome, state, attempts=0), None
                record["robots_detail"] = dict(self.robots[origin(url)][3])
            record.update(robots=state, source_requests=sum(1 for request in self.requests if request["url"] == url))
            self.pages[url] = (record, reply)
        record, reply = self.pages[url]
        return dict(record), reply


def check(data, checker, now=None):
    """Adapt collected responses to the original readable JSON fields, add coverage."""
    now = now or datetime.now(timezone.utc)
    results, problems = [], []
    required_checks = completed_checks = 0
    required_comparisons = completed_comparisons = 0
    for item in data["sources"]:
        entry, _ = checker.page(item["url"])
        primary = dict(entry)
        components = [primary]
        entry["id"] = item["id"]
        currency_url, recorded = item.get("currency_url"), item.get("currency_line")
        if currency_url:
            page, reply = checker.page(currency_url)
            observed = currency_line(reply.body) if page["outcome"] == "ok" else None
            page.update(recorded_currency_line=recorded, observed_currency_line=observed,
                        recorded_page_changed_at=item.get("page_changed_at"),
                        observed_page_changed_at=published_date(observed), currency_changed=None)
            if page["outcome"] == "ok" and recorded is not None:
                changed = recorded != observed
                page.update(currency_changed=changed, outcome="changed" if changed else "ok",
                            comparison="different" if changed else "unchanged",
                            reason=("currency_line_missing" if observed is None else "currency_line_changed") if changed else None)
            if recorded is not None:
                required_comparisons += 1
                completed_comparisons += page["completed"]
            entry["currency"] = page
            components.append(page)
        dominant = max(components, key=lambda component: SEVERITY[component["outcome"]])
        entry.update(outcome=dominant["outcome"], reason=dominant["reason"],
                     comparison=dominant["comparison"], checked=all(component["completed"] for component in components),
                     review_required=any(component["outcome"] == "changed" for component in components),
                     primary=primary)
        entry["legally_reviewed_at"] = item.get("legally_reviewed_at")
        required_checks += len(components)
        completed_checks += sum(component["completed"] for component in components)
        for index, component in enumerate(components):
            if component["outcome"] != "ok":
                label = "currency page " if index else ""
                problems.append(f"{item['id']}: {label}{component['url']} {component['outcome']} "
                                f"({component['reason']}; {component.get('error') or 'no further detail'})")
        results.append(entry)
    summary = {"checked": sum(entry["checked"] for entry in results)}
    summary["unchecked"] = len(results) - summary["checked"]
    summary.update({kind: sum(entry["outcome"] == kind for entry in results)
                    for kind in ("changed", "refused", "transient")})
    exit_code = 1 if summary["changed"] or summary["refused"] else 3 if summary["transient"] else 0
    return {"checked_at": now.isoformat(timespec="seconds"), "meaning": MEANING, "user_agent": USER_AGENT,
            "timeout_seconds": TIMEOUT_SECONDS, "run_budget_seconds": RUN_BUDGET_SECONDS,
            "requests": len(checker.requests), "request_log": checker.requests,
            "required_sources": len(results), "required_checks": required_checks, "completed_checks": completed_checks,
            "required_currency_comparisons": required_comparisons, "completed_currency_comparisons": completed_comparisons,
            "summary": summary, "checker_exit": exit_code, "results": results, "problems": problems}


def load_registry(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, list) or not sources:
        raise ValueError("registry has no sources")
    seen = set()
    for item in sources:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"] or item["id"] in seen:
            raise ValueError("every source needs a unique id")
        seen.add(item["id"])
        for unsupported in ("conditional", "conditional_requests", "baseline", "content_hash", "fingerprint"):
            if unsupported in item or unsupported in data:
                raise ValueError(f"unsupported source-check feature: {unsupported}")
        for key in ("url", "currency_url"):
            value = item.get(key)
            if key == "currency_url" and value is None:
                continue
            parts = urlsplit(value) if isinstance(value, str) else None
            if (not parts or parts.scheme != "https" or not parts.hostname or parts.username or parts.password
                    or parts.port not in (None, 443) or any(character.isspace() for character in value)):
                raise ValueError(f"{item['id']}: {key} must be an HTTPS URL without credentials or a custom port")
        recorded = item.get("currency_line")
        if recorded is not None and (not isinstance(recorded, str) or not item.get("currency_url")):
            raise ValueError(f"{item['id']}: currency_line requires text and a currency_url")
    return data


def render(report):
    lines = [f"Source check {report['checked_at']} ({report['requests']} requests)", report["meaning"], ""]
    for entry in report["results"]:
        reason = f" reason={entry['reason']}" if entry["reason"] else ""
        lines.append(f"{entry['id']}: {entry['outcome'].upper()} status={entry.get('status')} "
                     f"comparison={entry['comparison']}{reason} {entry['url']}")
        for label, component in (("source", entry["primary"]), ("currency", entry.get("currency"))):
            if component is None:
                continue
            lines.append(f"  {label}: {component['outcome'].upper()} reason={component['reason']} "
                         f"attempts={component.get('attempts', 0)} source_requests={component['source_requests']} "
                         f"comparison={component['comparison']} {component['url']}")
            if component.get("redirect_target"):
                lines.append(f"  redirect_target={component['redirect_target']} redirect_followed=false")
            if component.get("robots_detail"):
                detail = component["robots_detail"]
                lines.append(f"  robots: reason={detail['reason']} error={detail.get('error')}")
        currency = entry.get("currency")
        if currency:
            changed = {True: "CHANGED", False: "unchanged", None: "not compared"}[currency["currency_changed"]]
            lines.append(f"  currency line ({changed}): {currency['observed_currency_line']}")
    summary = report["summary"]
    lines.append("Summary: " + " ".join(f"{key}={summary[key]}" for key in ("checked", "unchecked", "changed", "refused", "transient")))
    lines.append(f"Checks: completed={report['completed_checks']} required={report['required_checks']}; "
                 f"currency comparisons: completed={report['completed_currency_comparisons']} "
                 f"required={report['required_currency_comparisons']}; PDF content comparison=not_configured")
    if summary["unchecked"]:
        lines.append("WARNING: incomplete run; unchecked sources remain.")
        if not report["completed_currency_comparisons"]:
            lines.append("WARNING: zero comparisons completed (currency lines); response checks are counted separately.")
    if report["problems"]:
        lines.extend(["Problems:", *(f"  - {problem}" for problem in report["problems"])])
    elif (summary["checked"] == report["required_sources"]
          and report["completed_checks"] == report["required_checks"]):
        lines.append("No problems found.")
    lines.append(f"checker_exit={report['checker_exit']}")
    return "\n".join(lines)


def main(argv=None, fetch=urllib_fetch, pause=time.sleep, clock=time.monotonic, wall_clock=time.time):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", required=True, help="path for the JSON report (parent folders are created)")
    parser.add_argument("--registry", default=str(REGISTRY), help="registry to read (default: docs/legal-sources.json)")
    args = parser.parse_args(argv)
    try:
        report_path, registry_path = Path(args.report).resolve(), Path(args.registry).resolve()
        if report_path == registry_path or (report_path.exists() and registry_path.exists() and report_path.samefile(registry_path)):
            raise ValueError("the report path must not be the registry")
        data = load_registry(registry_path)
    except (OSError, ValueError) as exc:
        print(f"CONFIG_ERROR: registry invalid; no source requests made: {exc}", file=sys.stderr)
        return 2
    report = check(data, Checker(fetch, pause, clock, wall_clock))
    print(render(report))
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    except (OSError, ValueError) as exc:
        print(f"CONFIG_ERROR: cannot write required report: {exc}; checker_exit=2", file=sys.stderr)
        return 2
    return report["checker_exit"]


if __name__ == "__main__":
    if sys.argv[1:] == ["--fetch-worker"]:
        response = asdict(_fetch_once(**json.loads(sys.stdin.read())))
        response["body"] = base64.b64encode(response["body"]).decode("ascii")
        print(json.dumps(response))
    else:
        sys.exit(main())
