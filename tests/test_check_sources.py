"""Test the source link and currency-line checker with a fake fetcher; no network access."""
import copy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_sources
import source_registry

# Synthetic page in the shape of a statute page: the currency line is split across spans.
LINE = ("2099-00 Wisconsin Statutes updated through 2099 Wis. Act 1 and through all Supreme Court Orders "
        "filed before and in effect on January 2, 2099. Published and certified under s. 0.00. "
        "Changes effective after January 2, 2099, are designated by NOTES. (Published 1-2-99)")
PAGE = ("<html><head><script>var x = 'updated through nothing';</script></head><body><p>Synthetic text.</p>"
        "<div id='frame'><span>2099-00 Wisconsin Statutes updated </span><span>through 2099 Wis. Act 1 and through "
        "all Supreme Court Orders\n filed before and in effect on January 2, 2099.</span><span>  Published and "
        "<a href='/c'>certified</a> under s. 0.00.  Changes effective after January 2, 2099, are designated by "
        "NOTES.</span> <span>(Published 1-2-99)</span></div></body></html>").encode()
CHANGED = PAGE.replace(b"Act 1 and", b"Act 2 and")


def registry():
    return {"schema_version": 1, "sources": [
        {"id": "pdf-one", "url": "https://statutes.example.test/ch/1.pdf", "currency_url": "https://statutes.example.test/ch/1",
         "currency_line": LINE, "retrieved_at": "2099-01-01", "page_changed_at": "2099-01-02", "legally_reviewed_at": None},
        {"id": "pdf-two", "url": "https://statutes.example.test/ch/2.pdf", "currency_url": "https://statutes.example.test/ch/1",
         "currency_line": LINE, "retrieved_at": "2099-01-01", "page_changed_at": "2099-01-02", "legally_reviewed_at": "2099-01-01"},
        {"id": "court-pdf", "url": "https://court.example.test/doc.pdf", "currency_url": None, "currency_line": None,
         "retrieved_at": None, "page_changed_at": None, "legally_reviewed_at": None},
    ]}


class FakeFetcher:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, url):
        self.calls.append(url)
        return self.pages.get(url, check_sources.Response(404, final_url=url, error="Not Found"))


def ok(url, body=b"", content_type="application/pdf"):
    return check_sources.Response(200, content_type, body, url)


def healthy_pages(**overrides):
    pages = {
        "https://statutes.example.test/robots.txt": ok("https://statutes.example.test/robots.txt",
                                                       b"\xef\xbb\xbfUser-agent: *\nDisallow: /feed/\n", "text/plain"),
        "https://statutes.example.test/ch/1.pdf": ok("https://statutes.example.test/ch/1.pdf"),
        "https://statutes.example.test/ch/2.pdf": ok("https://statutes.example.test/ch/2.pdf"),
        "https://statutes.example.test/ch/1": ok("https://statutes.example.test/ch/1", PAGE, "text/html"),
        "https://court.example.test/doc.pdf": ok("https://court.example.test/doc.pdf"),
    }
    pages.update(overrides)
    return pages


class CheckSourcesTests(unittest.TestCase):
    def run_check(self, pages, data=None):
        fetcher = FakeFetcher(pages)
        report = check_sources.check(data or registry(), check_sources.Checker(fetcher, pause=lambda _: None),
                                     now=datetime(2099, 1, 3, tzinfo=timezone.utc))
        return report, fetcher

    def test_currency_line_is_read_from_split_markup_and_ignores_scripts(self):
        self.assertEqual(check_sources.currency_line(PAGE), LINE)
        self.assertIsNone(check_sources.currency_line(b"<p>No stamp here.</p>"))
        self.assertEqual(check_sources.published_date(LINE), "2099-01-02")
        self.assertIsNone(check_sources.published_date("(Published 13-40-99)"))

    def test_healthy_registry_passes_and_each_url_is_requested_once(self):
        report, fetcher = self.run_check(healthy_pages())
        self.assertEqual(report["problems"], [])
        self.assertEqual(len(fetcher.calls), len(set(fetcher.calls)))
        self.assertEqual(fetcher.calls.count("https://statutes.example.test/ch/1"), 1)
        self.assertIn("https://court.example.test/robots.txt", fetcher.calls)
        first = report["results"][0]
        self.assertFalse(first["currency"]["currency_changed"])
        self.assertEqual(first["currency"]["observed_page_changed_at"], "2099-01-02")
        self.assertIn("not a legal review", report["meaning"])

    def test_changed_or_missing_currency_line_is_a_problem(self):
        report, _ = self.run_check(healthy_pages(**{"https://statutes.example.test/ch/1": ok(
            "https://statutes.example.test/ch/1", CHANGED, "text/html")}))
        self.assertTrue(report["results"][0]["currency"]["currency_changed"])
        self.assertEqual(len([p for p in report["problems"] if "currency line changed" in p]), 2)
        report, _ = self.run_check(healthy_pages(**{"https://statutes.example.test/ch/1": ok(
            "https://statutes.example.test/ch/1", b"<p>redesigned</p>", "text/html")}))
        self.assertTrue(any("currency line not found" in p for p in report["problems"]))

    def test_unreachable_url_is_a_problem(self):
        pages = healthy_pages()
        del pages["https://court.example.test/doc.pdf"]
        pages["https://statutes.example.test/ch/2.pdf"] = check_sources.Response(None, error="TimeoutError: timed out")
        report, _ = self.run_check(pages)
        self.assertTrue(any(p.startswith("court-pdf:") and "404" in p for p in report["problems"]))
        self.assertTrue(any(p.startswith("pdf-two:") and "timed out" in p for p in report["problems"]))

    def test_robots_rules_are_honored_before_any_page_request(self):
        pages = healthy_pages(**{"https://statutes.example.test/robots.txt": ok(
            "https://statutes.example.test/robots.txt", b"User-agent: *\nDisallow: /ch/\n", "text/plain")})
        report, fetcher = self.run_check(pages)
        self.assertNotIn("https://statutes.example.test/ch/1.pdf", fetcher.calls)
        self.assertNotIn("https://statutes.example.test/ch/1", fetcher.calls)
        self.assertFalse(report["results"][0]["fetched"])
        self.assertTrue(any("robots.txt does not permit" in p for p in report["problems"]))

    def test_forbidden_or_failing_robots_file_means_no_fetch(self):
        for status in (403, 503, None):
            pages = healthy_pages(**{"https://court.example.test/robots.txt": check_sources.Response(status, error="refused")})
            report, fetcher = self.run_check(pages)
            self.assertNotIn("https://court.example.test/doc.pdf", fetcher.calls, status)
            self.assertTrue(any(p.startswith("court-pdf:") for p in report["problems"]), status)

    def test_missing_robots_file_allows_fetching(self):
        report, fetcher = self.run_check(healthy_pages())
        self.assertIn("https://court.example.test/doc.pdf", fetcher.calls)
        self.assertEqual(report["results"][2]["robots"], "HTTP 404: no robots.txt")

    def test_cross_host_redirect_is_not_followed(self):
        handler = check_sources.SameHostRedirects()
        request = urllib.request.Request("https://statutes.example.test/a")
        with self.assertRaises(urllib.error.HTTPError):
            handler.redirect_request(request, io.BytesIO(), 302, "Found", {}, "https://elsewhere.example.test/b")
        same = handler.redirect_request(request, io.BytesIO(), 302, "Found", {}, "https://statutes.example.test/b")
        self.assertEqual(same.full_url, "https://statutes.example.test/b")

    def test_main_writes_report_exit_codes_and_never_touches_registry(self):
        with tempfile.TemporaryDirectory() as folder:
            registry_path, report_path = Path(folder) / "sources.json", Path(folder) / "out" / "report.json"
            registry_path.write_text(json.dumps(registry(), indent=2), encoding="utf-8")
            before = registry_path.read_bytes()
            out = io.StringIO()
            with redirect_stdout(out):
                code = check_sources.main(["--report", str(report_path), "--registry", str(registry_path)],
                                          fetch=FakeFetcher(healthy_pages()), pause=lambda _: None)
            self.assertEqual(code, 0)
            self.assertIn("No problems found.", out.getvalue())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual([r["legally_reviewed_at"] for r in report["results"]], [None, "2099-01-01", None])
            with redirect_stdout(io.StringIO()):
                code = check_sources.main(["--report", str(report_path), "--registry", str(registry_path)],
                                          fetch=FakeFetcher(healthy_pages(**{"https://statutes.example.test/ch/1": ok(
                                              "https://statutes.example.test/ch/1", CHANGED, "text/html")})),
                                          pause=lambda _: None)
            self.assertEqual(code, 1)
            self.assertEqual(registry_path.read_bytes(), before)
            with redirect_stderr(io.StringIO()):
                self.assertEqual(check_sources.main(["--report", str(registry_path), "--registry", str(registry_path)],
                                                    fetch=FakeFetcher({})), 2)
                registry_path.write_text("{not json", encoding="utf-8")
                self.assertEqual(check_sources.main(["--report", str(report_path), "--registry", str(registry_path)],
                                                    fetch=FakeFetcher({})), 2)

    def test_registry_rejects_non_https_currency_url(self):
        data = registry()
        data["sources"][0]["currency_url"] = "http://statutes.example.test/ch/1"
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "sources.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                check_sources.load_registry(path)

    def test_bundled_registry_loads_and_records_freshness_fields(self):
        data = check_sources.load_registry(check_sources.REGISTRY)
        self.assertEqual(source_registry.validate(data), [])
        for item in data["sources"]:
            for key in ("retrieved_at", "page_changed_at", "legally_reviewed_at", "currency_url", "currency_line"):
                self.assertIn(key, item)
        self.assertIn("never set by a script", data["freshness_fields"])

    def test_registry_validation_checks_freshness_fields(self):
        data = json.loads(source_registry.REGISTRY.read_text(encoding="utf-8"))
        broken = copy.deepcopy(data)
        broken["sources"][0].pop("legally_reviewed_at")
        broken["sources"][1]["retrieved_at"] = "13 October"
        broken["sources"][2]["currency_url"] = "ftp://statutes.example.test/"
        broken["sources"][3]["currency_url"], broken["sources"][3]["currency_line"] = None, "orphan line"
        errors = "\n".join(source_registry.validate(broken))
        for expected in ("missing legally_reviewed_at", "retrieved_at must be an ISO date", "currency_url must be an HTTPS",
                         "currency_line must be text"):
            self.assertIn(expected, errors)


if __name__ == "__main__":
    unittest.main()
