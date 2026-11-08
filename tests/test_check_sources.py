"""Offline fixtures: fake clock and transport, no live requests."""
import copy
from datetime import datetime, timezone
from email.utils import format_datetime
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import Mock, patch
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_sources as cs
import source_registry

LINE = "2099-00 Wisconsin Statutes updated through 2099 Wis. Act 1 (Published 1-2-99)"
PAGE = b"<html><script>ignore me</script><span>2099-00 Wisconsin Statutes updated </span><span>through 2099 Wis. Act 1 (Published 1-2-99)</span></html>"
CHANGED = PAGE.replace(b"Act 1", b"Act 2")
URL = "https://court.example.test/rules.pdf"
CURRENCY = "https://court.example.test/currency"
ROBOTS = "https://court.example.test/robots.txt"


def generated_pdf():
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 100 100] >>"]
    body, offsets = b"%PDF-1.4\n", []
    for index, obj in enumerate(objects, 1):
        offsets.append(len(body))
        body += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(body)
    body += b"xref\n0 4\n0000000000 65535 f \n"
    body += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets)
    return body + f"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()


PDF = generated_pdf()


def ok(url=URL, body=PDF, content_type="application/pdf", **kwargs):
    return cs.Response(200, content_type, body, url, **kwargs)


def registry(url=URL, currency=False):
    item = {"id": "example-source", "url": url, "legally_reviewed_at": "2099-01-01"}
    if currency:
        item.update(currency_url=CURRENCY, currency_line=LINE, page_changed_at="2099-01-02")
    return {"sources": [item]}


class FakeClock:
    def __init__(self):
        self.seconds, self.sleeps = 0.0, []
        self.epoch = datetime(2099, 1, 3, tzinfo=timezone.utc).timestamp()

    def __call__(self):
        return self.seconds

    def wall(self):
        return self.epoch + self.seconds

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.seconds += seconds


class FakeTransport:
    def __init__(self, clock, pages=None):
        self.clock, self.pages, self.calls, self.counts = clock, pages or {}, [], {}

    def __call__(self, url, *, method, headers, timeout):
        attempt = self.counts.get(url, 0) + 1
        self.counts[url] = attempt
        self.calls.append({"method": method, "url": url, "headers": dict(headers),
                           "start_time": self.clock(), "attempt": attempt, "timeout": timeout})
        value = self.pages.get(url)
        if value is None:
            value = cs.Response(404, final_url=url) if url.endswith("/robots.txt") else ok(url)
        if isinstance(value, list):
            value = value[min(attempt - 1, len(value) - 1)]
        if isinstance(value, tuple):
            value, duration = value
            self.clock.seconds += duration
        if isinstance(value, Exception):
            raise value
        return copy.deepcopy(value)


class CheckSourcesTests(unittest.TestCase):
    def run_check(self, pages=None, data=None, budget=cs.RUN_BUDGET_SECONDS):
        clock = FakeClock()
        transport = FakeTransport(clock, pages)
        checker = cs.Checker(transport, clock.sleep, clock, clock.wall, budget)
        report = cs.check(data or registry(), checker, datetime(2099, 1, 3, tzinfo=timezone.utc))
        self.assertEqual(transport.calls, checker.requests)
        self.assertTrue(all(count <= 2 for count in transport.counts.values()))
        self.assertTrue(all(entry["outcome"] in cs.SEVERITY for entry in report["results"]))
        return report, transport, clock

    def test_currency_markup_and_dates(self):
        self.assertEqual(cs.currency_line(PAGE), LINE)
        self.assertIsNone(cs.currency_line(b"<p>No stamp.</p>"))
        self.assertEqual(cs.published_date(LINE), "2099-01-02")
        self.assertIsNone(cs.published_date("(Published 13-40-99)"))

    def test_ok_response_is_not_claimed_to_compare_pdf_content(self):
        report, transport, _ = self.run_check()
        self.assertEqual(report["checker_exit"], 0)
        self.assertEqual(report["summary"], dict(checked=1, unchecked=0, changed=0, refused=0, transient=0))
        self.assertEqual(report["results"][0]["comparison"], "response_valid")
        self.assertIn("No problems found.", cs.render(report))
        self.assertEqual(transport.counts[URL], 1)
        self.assertEqual(transport.calls[1]["start_time"], 2)

    def test_shared_currency_page_is_deduplicated_with_separate_baselines(self):
        data = registry(currency=True)
        data["sources"].append(dict(data["sources"][0], id="second-source", currency_line=LINE.replace("Act 1", "Act 2")))
        report, transport, _ = self.run_check({CURRENCY: ok(CURRENCY, PAGE, "text/html")}, data)
        self.assertEqual([row["outcome"] for row in report["results"]], ["ok", "changed"])
        self.assertEqual(transport.counts[CURRENCY], 1)
        self.assertEqual(report["completed_checks"], 4)
        self.assertEqual(report["results"][0]["currency"]["comparison"], "unchanged")
        self.assertEqual(report["results"][0]["currency"]["observed_page_changed_at"], "2099-01-02")

    def test_changed_and_missing_currency_lines(self):
        for body, reason in ((CHANGED, "currency_line_changed"), (b"<p>redesigned</p>", "currency_line_missing")):
            with self.subTest(reason=reason):
                report, _, _ = self.run_check({CURRENCY: ok(CURRENCY, body, "text/html")}, registry(currency=True))
                self.assertEqual(report["checker_exit"], 1)
                self.assertEqual(report["summary"]["checked"], 1)
                self.assertEqual(report["summary"]["changed"], 1)
                self.assertEqual(report["results"][0]["reason"], reason)
                self.assertTrue(report["results"][0]["review_required"])

    def test_timeout_retried_once_with_twenty_second_deadline(self):
        report, transport, clock = self.run_check({URL: (TimeoutError("timed out"), 20)})
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(report["results"][0]["reason"], "timeout")
        self.assertEqual(transport.counts[URL], 2)
        self.assertEqual([call["timeout"] for call in transport.calls], [20, 20, 20])
        self.assertEqual([call["start_time"] for call in transport.calls], [0, 2, 22])
        self.assertEqual(clock(), 42)
        self.assertIn("zero comparisons completed", cs.render(report))
        self.assertNotIn("No problems found", cs.render(report))

    def test_retry_after_seconds_and_http_date_honored(self):
        stamp = format_datetime(datetime.fromtimestamp(FakeClock().epoch + 9, timezone.utc), usegmt=True)
        for value in ("7", stamp):
            with self.subTest(value=value):
                report, transport, _ = self.run_check({URL: cs.Response(429, headers={"Retry-After": value})})
                self.assertEqual(report["checker_exit"], 3)
                self.assertEqual([call["start_time"] for call in transport.calls], [0, 2, 9])
                self.assertTrue(report["results"][0]["retry_after_honored"])

    def test_retry_after_retry_can_succeed(self):
        report, transport, _ = self.run_check({URL: [cs.Response(429, headers={"Retry-After": "7"}), ok()]})
        self.assertEqual(report["checker_exit"], 0)
        self.assertEqual(transport.calls[-1]["start_time"], 9)

    def test_retry_after_larger_than_budget_defers_retry(self):
        report, transport, clock = self.run_check({URL: cs.Response(429, headers={"Retry-After": "1000"})})
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(report["results"][0]["reason"], "retry_after_exceeds_budget")
        self.assertEqual(transport.counts[URL], 1)
        self.assertEqual(clock(), 2)

    def test_final_retry_after_paces_next_same_host_url(self):
        second = "https://court.example.test/next.pdf"
        data = registry()
        data["sources"].append({"id": "next-source", "url": second})
        report, transport, _ = self.run_check({URL: cs.Response(429, headers={"Retry-After": "7"})}, data)
        self.assertEqual(transport.calls[-1]["url"], second)
        self.assertEqual(transport.calls[-1]["start_time"], 16)
        self.assertEqual(report["summary"]["checked"], 1)

    def test_robots429_retries_or_defers_without_source_fetch(self):
        for value, count in (("7", 2), ("1000", 1)):
            report, transport, _ = self.run_check({ROBOTS: cs.Response(429, headers={"Retry-After": value})})
            self.assertEqual(report["checker_exit"], 3)
            self.assertEqual(transport.counts[ROBOTS], count)
            self.assertNotIn(URL, transport.counts)
            self.assertEqual(report["results"][0]["reason"], "robots_unavailable")
            if count == 1:
                self.assertIn("retry_after_exceeds_budget", cs.render(report))

    def test_http403_and_gone_are_refused_without_retry(self):
        for status in (403, 404, 410):
            report, transport, _ = self.run_check({URL: cs.Response(status)})
            self.assertEqual(report["checker_exit"], 1)
            self.assertEqual(report["results"][0]["outcome"], "refused")
            self.assertEqual(report["results"][0]["reason"], f"http_{status}")
            self.assertEqual(transport.counts[URL], 1)

    def test_robots401_and403_refuse_without_source_fetch(self):
        for status in (401, 403):
            report, transport, _ = self.run_check({ROBOTS: cs.Response(status)})
            self.assertEqual(report["checker_exit"], 1)
            self.assertEqual(report["results"][0]["reason"], f"robots_http_{status}")
            self.assertNotIn(URL, transport.counts)

    def test_robots_disallow_keeps_other_hosts_running(self):
        other = "https://other.example.test/rules.pdf"
        data = registry()
        data["sources"].append({"id": "other-source", "url": other})
        report, transport, _ = self.run_check({ROBOTS: ok(ROBOTS, b"User-agent: *\nDisallow: /\n", "text/plain")}, data)
        self.assertNotIn(URL, transport.counts)
        self.assertIn(other, transport.counts)
        self.assertEqual(report["results"][0]["reason"], "robots_disallow")
        self.assertEqual(report["summary"]["checked"], 1)

    def test_robots_unavailable_is_transient(self):
        for reply in (cs.Response(503), TimeoutError("timed out")):
            report, transport, _ = self.run_check({ROBOTS: reply})
            self.assertEqual(report["checker_exit"], 3)
            self.assertEqual(transport.counts[ROBOTS], 2)
            self.assertNotIn(URL, transport.counts)
            self.assertEqual(report["results"][0]["reason"], "robots_unavailable")

    def test_robots404_410_and_empty_file_allow_fetch(self):
        for reply in (cs.Response(404), cs.Response(410), ok(ROBOTS, b"", "text/plain")):
            report, transport, _ = self.run_check({ROBOTS: reply})
            self.assertEqual(report["checker_exit"], 0)
            self.assertEqual(transport.counts[URL], 1)

    def test_off_host_redirect_target_is_never_requested(self):
        target = "https://other.example.test/rules.pdf"
        report, transport, _ = self.run_check({URL: cs.Response(302, headers={"Location": target})})
        self.assertEqual(report["checker_exit"], 1)
        self.assertEqual(report["results"][0]["reason"], "off_host_redirect")
        self.assertEqual(report["results"][0]["redirect_target"], target)
        self.assertFalse(report["results"][0]["redirect_followed"])
        self.assertEqual(set(transport.counts), {ROBOTS, URL})

    def test_same_host_redirect_uses_scheduler_and_checks_robots(self):
        target = "https://court.example.test/new.pdf"
        pages = {ROBOTS: ok(ROBOTS, b"User-agent: *\nCrawl-delay: 10\nDisallow: /private\n", "text/plain"),
                 URL: cs.Response(302, headers={"Location": "/new.pdf"})}
        report, transport, _ = self.run_check(pages)
        self.assertEqual(report["checker_exit"], 0)
        self.assertEqual([call["start_time"] for call in transport.calls], [0, 10, 20])
        self.assertEqual(transport.calls[-1]["url"], target)
        pages[URL] = cs.Response(302, headers={"Location": "/private.pdf"})
        report, transport, _ = self.run_check(pages)
        self.assertEqual(report["checker_exit"], 1)
        self.assertEqual(len(transport.calls), 2)

    def test_redirect_cycle_is_refused_without_third_attempt(self):
        target = "https://court.example.test/new.pdf"
        report, transport, _ = self.run_check({URL: cs.Response(302, headers={"Location": target}),
                                             target: cs.Response(302, headers={"Location": URL})})
        self.assertEqual(report["results"][0]["reason"], "redirect_limit")
        self.assertEqual(transport.counts[URL], 1)

    def test_malformed_redirect_is_refused(self):
        report, _, _ = self.run_check({URL: cs.Response(302, headers={"Location": "https://["})})
        self.assertEqual(report["results"][0]["reason"], "invalid_redirect_location")
        self.assertEqual(report["checker_exit"], 1)

    def test_transport_must_not_follow_redirects(self):
        handler = cs.NoRedirects()
        request = urllib.request.Request(URL)
        for target in (CURRENCY, "https://other.example.test/rules.pdf"):
            self.assertIsNone(handler.redirect_request(request, io.BytesIO(), 302, "Found", {}, target))
        report, transport, _ = self.run_check({URL: ok(CURRENCY)})
        self.assertEqual(report["results"][0]["reason"], "transport_followed_redirect")
        self.assertEqual(transport.counts[URL], 1)

    def test_unexpected304_is_refused_without_retry_or_conditional_headers(self):
        report, transport, _ = self.run_check({URL: cs.Response(304)})
        self.assertEqual(report["results"][0]["reason"], "unexpected_304_without_baseline")
        self.assertEqual(report["checker_exit"], 1)
        self.assertEqual(transport.counts[URL], 1)
        self.assertFalse(any(key.lower().startswith("if-") for call in transport.calls for key in call["headers"]))

    def test_html_denial_page_instead_of_pdf_is_refused(self):
        report, _, _ = self.run_check({URL: ok(URL, b"<html>sign in</html>", "text/html")})
        self.assertEqual(report["results"][0]["reason"], "unexpected_pdf_type")
        self.assertEqual(report["summary"]["unchecked"], 1)
        self.assertEqual(report["checker_exit"], 1)

    def test_cap_length_mismatch_and_pdf_truncation_are_refused(self):
        cases = [ok(complete=False, reason="body_size_limit"), ok(headers={"Content-Length": str(len(PDF) + 1)}),
                 ok(body=PDF[:-10]), ok(body=b"<html>denied</html>"), ok(headers={"Content-Length": "invalid"})]
        for response in cases:
            with self.subTest(reason=response.reason):
                report, transport, _ = self.run_check({URL: response})
                self.assertEqual(report["checker_exit"], 1)
                self.assertEqual(report["summary"]["unchecked"], 1)
                self.assertEqual(transport.counts[URL], 1)

    def test_malformed_numeric_headers_do_not_abort_the_run(self):
        for value in ("\u00b2", "9" * 5000):
            report, _, _ = self.run_check({URL: ok(headers={"Content-Length": value})})
            self.assertEqual(report["results"][0]["reason"], "content_length_mismatch")
        report, transport, _ = self.run_check({URL: cs.Response(429, headers={"Retry-After": "\u00b2"})})
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(transport.counts[URL], 2)
        report, transport, _ = self.run_check({URL: cs.Response(429, headers={"Retry-After": "9" * 5000})})
        self.assertEqual(report["results"][0]["reason"], "retry_after_exceeds_budget")
        self.assertEqual(transport.counts[URL], 1)

    def test_fractional_crawl_delay_is_rounded_up_and_invalid_delay_refuses(self):
        report, transport, _ = self.run_check({ROBOTS: ok(ROBOTS, b"User-agent: *\nCrawl-delay: 10.5\n", "text/plain")})
        self.assertEqual(report["checker_exit"], 0)
        self.assertEqual(transport.calls[1]["start_time"], 11)
        report, transport, _ = self.run_check({ROBOTS: ok(ROBOTS, b"User-agent: *\nCrawl-delay: unknown\n", "text/plain")})
        self.assertEqual(report["results"][0]["reason"], "invalid_crawl_delay")
        self.assertNotIn(URL, transport.counts)

    def test_comparison_counts_do_not_count_pdf_availability(self):
        report, _, _ = self.run_check()
        self.assertEqual(report["completed_checks"], 1)
        self.assertEqual(report["completed_currency_comparisons"], 0)
        self.assertEqual(report["required_currency_comparisons"], 0)
        report, _, _ = self.run_check({CURRENCY: ok(CURRENCY, PAGE, "text/html")}, registry(currency=True))
        self.assertEqual(report["completed_checks"], 2)
        self.assertEqual(report["completed_currency_comparisons"], 1)
        self.assertEqual(report["required_currency_comparisons"], 1)

    def test_maximum_default_floor_crawl_and_retry_after_pacing(self):
        for host, crawl, expected in (("court.example.test", 0, 2),
                                      ("docs.legis.wisconsin.gov", 0, 5),
                                      ("docs.legis.wisconsin.gov", 10, 10)):
            with self.subTest(host=host, crawl=crawl):
                source, robots = f"https://{host}/rules.pdf", f"https://{host}/robots.txt"
                pages = {robots: ok(robots, f"User-agent: *\nCrawl-delay: {crawl}\n".encode(), "text/plain"),
                         source: [cs.Response(429, headers={"Retry-After": "7"}), ok(source)]}
                report, transport, _ = self.run_check(pages, registry(source))
                self.assertEqual(report["checker_exit"], 0)
                self.assertEqual(transport.calls[1]["start_time"], expected)
                self.assertEqual(transport.calls[2]["start_time"], expected + max(expected, 7))

    def test_budget_reserves_timeout_and_cleanup_before_first_attempt(self):
        report, transport, clock = self.run_check(budget=20)
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(report["summary"]["checked"], 0)
        self.assertEqual(transport.calls, [])
        self.assertEqual(clock(), 0)
        self.assertIn("budget_exhausted", cs.render(report))

    def test_budget_can_expire_between_robots_and_first_source(self):
        report, transport, clock = self.run_check(budget=21)
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(transport.counts, {ROBOTS: 1})
        self.assertEqual(report["results"][0]["reason"], "budget_exhausted")
        self.assertLessEqual(clock(), 21)

    def test_mixed_rows_one_through_four(self):
        cases = [(["ok", "transient"], 3, [1, 1, 0, 0, 1]),
                 (["changed", "transient"], 1, [1, 1, 1, 0, 1]),
                 (["refused", "transient"], 1, [0, 2, 0, 1, 1]),
                 (["ok", "changed", "refused", "transient"], 1, [2, 2, 1, 1, 1])]
        for kinds, expected_exit, counts in cases:
            with self.subTest(kinds=kinds):
                data, pages = {"sources": []}, {}
                for index, kind in enumerate(kinds):
                    url = f"https://fixture{index}.example.test/rules.pdf"
                    item = {"id": f"source-{index}", "url": url}
                    if kind == "changed":
                        currency = url.replace("rules.pdf", "currency")
                        item.update(currency_url=currency, currency_line=LINE)
                        pages[currency] = ok(currency, CHANGED, "text/html")
                    elif kind == "refused":
                        pages[url] = cs.Response(403)
                    elif kind == "transient":
                        pages[url] = TimeoutError("timed out")
                    data["sources"].append(item)
                report, _, _ = self.run_check(pages, data)
                self.assertEqual(report["checker_exit"], expected_exit)
                self.assertEqual(list(report["summary"].values()), counts)
                for item in data["sources"]:
                    self.assertIn(item["id"] + ":", cs.render(report))
                self.assertIn("WARNING: incomplete", cs.render(report))

    def test_mixed_row_six_adapts_deferred_conditional_mode(self):
        # Conditional 304 success is out of scope; use unconditional response success.
        data = registry()
        second = "https://other.example.test/rules.pdf"
        data["sources"].append({"id": "unexpected-source", "url": second})
        report, _, _ = self.run_check({second: cs.Response(304)}, data)
        self.assertEqual(report["checker_exit"], 1)
        self.assertEqual(report["summary"], dict(checked=1, unchecked=1, changed=0, refused=1, transient=0))

    def test_mixed_row_seven_all_hosts_timeout(self):
        data = registry()
        data["sources"].append({"id": "other-source", "url": "https://other.example.test/rules.pdf"})
        report, _, _ = self.run_check({ROBOTS: TimeoutError(), "https://other.example.test/robots.txt": TimeoutError()}, data)
        self.assertEqual(report["checker_exit"], 3)
        self.assertEqual(report["summary"]["checked"], 0)
        self.assertIn("zero comparisons completed", cs.render(report))

    def test_changed_currency_and_source_timeout_preserve_both_diagnostics(self):
        report, _, _ = self.run_check({URL: TimeoutError("timed out"), CURRENCY: ok(CURRENCY, CHANGED, "text/html")},
                                      registry(currency=True))
        self.assertEqual(report["results"][0]["outcome"], "changed")
        self.assertFalse(report["results"][0]["checked"])
        self.assertEqual(report["checker_exit"], 1)
        self.assertIn("timeout", cs.render(report))
        self.assertIn("currency_line_changed", cs.render(report))

    def test_november03_shaped_synthetic_failures_exit_one(self):
        data, pages = {"sources": []}, {}
        for index in range(11):
            url = f"https://synthetic.example.test/source{index}.pdf"
            item = {"id": f"synthetic-{index}", "url": url}
            if index < 6:
                pages[url] = (TimeoutError("timed out"), 20)
            if index < 7:
                currency = f"https://synthetic.example.test/currency{index}"
                item.update(currency_url=currency, currency_line=LINE)
                pages[currency] = (OSError("[Errno 111] Connection refused") if index < 5
                                   else ok(currency, CHANGED, "text/html"))
            data["sources"].append(item)
        report, _, _ = self.run_check(pages, data)
        self.assertEqual(report["checker_exit"], 1)
        self.assertEqual(report["summary"], dict(checked=5, unchecked=6, changed=2, refused=0, transient=5))
        self.assertEqual(sum(row["primary"]["reason"] == "timeout" for row in report["results"]), 6)
        self.assertEqual(sum(row.get("currency", {}).get("reason") == "network_error" for row in report["results"]), 5)
        self.assertEqual(len(report["problems"]), 13)

    def run_main(self, data=None, pages=None, report_write_failure=False):
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "sources.json", Path(folder) / "report.json"
            source.write_text(json.dumps(data or registry()), encoding="utf-8")
            before = source.read_bytes()
            if report_write_failure:
                output.mkdir()
            clock = FakeClock()
            transport = FakeTransport(clock, pages)
            stdout, stderr = io.StringIO(), io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = cs.main(["--registry", str(source), "--report", str(output)],
                               transport, clock.sleep, clock, clock.wall)
            self.assertEqual(before, source.read_bytes())
            report = json.loads(output.read_text()) if output.is_file() else None
            return code, stdout.getvalue(), stderr.getvalue(), report, transport

    def test_main_compatibility_and_no_registry_or_review_date_writes(self):
        code, stdout, stderr, report, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(stderr, "")
        self.assertIn("No problems found", stdout)
        self.assertEqual(report["results"][0]["legally_reviewed_at"], "2099-01-01")
        for key in ("checked_at", "meaning", "user_agent", "timeout_seconds", "requests", "results", "problems"):
            self.assertIn(key, report)
        for key in ("url", "robots", "fetched", "status", "final_url", "content_type", "last_modified_header", "error"):
            self.assertIn(key, report["results"][0])

    def test_main_exit_three_for_transient_only(self):
        code, _, _, report, _ = self.run_main(pages={URL: TimeoutError()})
        self.assertEqual(code, 3)
        self.assertEqual(report["checker_exit"], 3)

    def test_mixed_row_five_write_failure_overrides_changed_result(self):
        code, stdout, stderr, report, _ = self.run_main(registry(currency=True),
                                                      {CURRENCY: ok(CURRENCY, CHANGED, "text/html")}, True)
        self.assertEqual(code, 2)
        self.assertIsNone(report)
        self.assertIn("CHANGED", stdout)
        self.assertIn("CONFIG_ERROR: cannot write required report", stderr)
        self.assertIn("checker_exit=2", stderr)

    def test_configuration_errors_prevent_all_requests(self):
        cases = ["{not json", json.dumps({"sources": []}), json.dumps(registry("http://court.example.test/rules.pdf")),
                 json.dumps(registry("https://court.example.test:bad/rules.pdf")), json.dumps(dict(registry(), conditional=True))]
        with tempfile.TemporaryDirectory() as folder:
            source, output = Path(folder) / "sources.json", Path(folder) / "report.json"
            for text in cases:
                source.write_text(text, encoding="utf-8")
                transport, stderr = Mock(), io.StringIO()
                with redirect_stderr(stderr):
                    self.assertEqual(cs.main(["--registry", str(source), "--report", str(output)], fetch=transport), 2)
                transport.assert_not_called()
                self.assertIn("CONFIG_ERROR: registry invalid; no source requests made", stderr.getvalue())
            source.write_text(json.dumps(registry()))
            with redirect_stderr(io.StringIO()):
                self.assertEqual(cs.main(["--registry", str(source), "--report", str(source)], fetch=transport), 2)
            transport.assert_not_called()

    def test_path_resolution_error_is_configuration_error(self):
        transport = Mock()
        with patch.object(Path, "resolve", side_effect=OSError("invalid path")), redirect_stderr(io.StringIO()):
            self.assertEqual(cs.main(["--registry", "a", "--report", "b"], fetch=transport), 2)
        transport.assert_not_called()

    def test_non_https_currency_rejected_before_requests(self):
        data = registry(currency=True)
        data["sources"][0]["currency_url"] = "http://court.example.test/currency"
        code, _, stderr, _, transport = self.run_main(data)
        self.assertEqual(code, 2)
        self.assertIn("HTTPS", stderr)
        self.assertEqual(transport.calls, [])

    def test_bundled_registry_and_freshness_validation(self):
        data = cs.load_registry(cs.REGISTRY)
        self.assertEqual(source_registry.validate(data), [])
        for item in data["sources"]:
            for key in ("retrieved_at", "page_changed_at", "legally_reviewed_at", "currency_url", "currency_line"):
                self.assertIn(key, item)
        broken = copy.deepcopy(data)
        broken["sources"][0].pop("legally_reviewed_at")
        broken["sources"][1]["retrieved_at"] = "13 October"
        broken["sources"][2]["currency_url"] = "ftp://statutes.example.test/"
        broken["sources"][3]["currency_url"], broken["sources"][3]["currency_line"] = None, "orphan line"
        errors = "\n".join(source_registry.validate(broken))
        for expected in ("missing legally_reviewed_at", "retrieved_at must be an ISO date", "currency_url must be an HTTPS",
                         "currency_line must be text"):
            self.assertIn(expected, errors)

    def test_supervisor_kills_and_reaps_at_absolute_timeout(self):
        worker = Mock()
        worker.communicate.side_effect = [subprocess.TimeoutExpired("worker", 20), ("", "")]
        with patch.object(cs.subprocess, "Popen", return_value=worker) as popen:
            reply = cs.urllib_fetch(URL)
        self.assertEqual(reply.reason, "timeout")
        worker.kill.assert_called_once_with()
        self.assertEqual(worker.communicate.call_args_list[0].kwargs["timeout"], 20)
        self.assertEqual(worker.communicate.call_args_list[1].kwargs["timeout"], 1)
        self.assertEqual(popen.call_args.args[0][-1], "--fetch-worker")

    def test_cleanup_timeout_is_bounded_transient(self):
        worker = Mock()
        worker.communicate.side_effect = subprocess.TimeoutExpired("worker", 1)
        with patch.object(cs.subprocess, "Popen", return_value=worker):
            reply = cs.urllib_fetch(URL)
        self.assertEqual(reply.reason, "timeout")
        self.assertIn("cleanup", reply.error)

    def test_worker_caps_body_without_network(self):
        reply = Mock()
        reply.code, reply.headers = 200, {"Content-Type": "application/pdf"}
        reply.read.return_value = PDF
        reply.__enter__ = Mock(return_value=reply)
        reply.__exit__ = Mock(return_value=False)
        opener = Mock()
        opener.open.return_value = reply
        with patch.object(cs.urllib.request, "build_opener", return_value=opener), patch.object(cs, "MAX_BODY_BYTES", 10):
            result = cs._fetch_once(URL, "GET", {"User-Agent": cs.USER_AGENT}, 20)
        reply.read.assert_called_once_with(11)
        self.assertFalse(result.complete)
        self.assertEqual(result.reason, "body_size_limit")
        self.assertEqual(len(result.body), 10)


if __name__ == "__main__":
    unittest.main()
