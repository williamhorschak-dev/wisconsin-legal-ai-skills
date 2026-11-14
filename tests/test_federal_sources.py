"""The federal source survey register: the committed file obeys its rules, and the rules refuse what they should."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import federal_sources as fs  # noqa: E402

SHA = "a" * 64
STAMP = "2026-11-14T02:20:13Z"


def synthetic_register():
    """A two-host register built from invented documents on permitted hosts."""
    return {
        "schema_version": 1,
        "scope": "Synthetic register for tests.",
        "method": "No request was made.",
        "permitted_hosts": "Permitted hosts only.",
        "hosts": [
            {"host": "www.example.uscourts.gov", "robots_url": "https://www.example.uscourts.gov/robots.txt",
             "robots_status": 200, "robots_sha256": SHA, "crawl_delay_seconds": 10, "retrieved_at_utc": STAMP, "note": ""},
            {"host": "www.govinfo.gov", "robots_url": "https://www.govinfo.gov/robots.txt", "robots_status": 404,
             "robots_sha256": None, "crawl_delay_seconds": None, "retrieved_at_utc": STAMP, "note": "No robots file."},
        ],
        "sources": [
            {"id": "S-01", "issuer": "E.D. Wis.", "title": "Example Local Rules", "title_source": "face",
             "url": "https://www.example.uscourts.gov/rules.pdf", "format": "pdf", "pages": 12,
             "date_printed": "Effective January 1, 2026", "date_kind": "effective", "retrieved_at_utc": STAMP,
             "bytes": 1024, "sha256": SHA, "read_extent": "full", "note": "", "recheck_trigger": "The response hash changes.",
             "legally_reviewed_at": None},
            {"id": "S-02", "issuer": "U.S. Code (GPO)", "title": "Sec. 1 - Example", "title_source": "face",
             "url": "https://www.govinfo.gov/content/example.htm", "format": "html", "pages": None, "date_printed": None,
             "date_kind": "none_printed", "retrieved_at_utc": STAMP, "bytes": 2048, "sha256": "b" * 64,
             "read_extent": "part", "note": "First section read.", "recheck_trigger": None, "legally_reviewed_at": None},
        ],
        "not_reached": [
            {"url": "https://www.example.uscourts.gov/assets/handbook.pdf", "reason": "robots_disallow",
             "note": "Not requested."},
        ],
    }


def problems(change):
    data = synthetic_register()
    change(data)
    return "\n".join(fs.validate(data))


class CommittedRegister(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(fs.REGISTER.read_text(encoding="utf-8"))

    def test_the_committed_register_obeys_its_own_rules(self):
        self.assertEqual(fs.validate(self.data), [])

    def test_every_source_was_fetched_from_a_host_whose_robots_file_was_requested(self):
        hosts = {host["host"] for host in self.data["hosts"]}
        for source in self.data["sources"]:
            self.assertIn(source["url"].split("/")[2], hosts, source["id"])

    def test_no_record_carries_a_legal_review_date(self):
        self.assertTrue(all(source["legally_reviewed_at"] is None for source in self.data["sources"]))

    def test_the_file_is_plain_ascii_text(self):
        fs.REGISTER.read_text(encoding="utf-8").encode("ascii")


class Rules(unittest.TestCase):
    def test_the_synthetic_register_is_valid(self):
        self.assertEqual(fs.validate(synthetic_register()), [])

    def test_an_unknown_field_is_refused_so_rule_text_cannot_be_added(self):
        for key in ("proposition", "text", "digest", "summary"):
            with self.subTest(key=key):
                self.assertIn(f"unknown key(s): {key}", problems(lambda d: d["sources"][0].update({key: "A rule says so."})))
        self.assertIn("unknown key(s): rules", problems(lambda d: d.update({"rules": []})))

    def test_a_missing_field_is_refused(self):
        self.assertIn("missing key(s): sha256", problems(lambda d: d["sources"][0].pop("sha256")))
        self.assertIn("missing key(s): not_reached", problems(lambda d: d.pop("not_reached")))

    def test_only_permitted_https_hosts_are_accepted(self):
        for url in ("https://www.law.example.edu/rules.pdf", "http://www.example.uscourts.gov/rules.pdf",
                    "https://uscourts.gov.example.com/rules.pdf", "https://user@www.example.uscourts.gov/rules.pdf",
                    "https://www.example.uscourts.gov:8443/rules.pdf", "https://notuscourts.gov/rules.pdf", "", None):
            with self.subTest(url=url):
                self.assertIn("S-01: url must be an https address on a permitted host",
                              problems(lambda d: d["sources"][0].update({"url": url})))
        self.assertIn("not a permitted host", problems(lambda d: d["hosts"][0].update({"host": "www.example.org"})))
        self.assertIn("not_reached[0]: url must be an https address on a permitted host",
                      problems(lambda d: d["not_reached"][0].update({"url": "https://www.example.org/a.pdf"})))

    def test_a_source_needs_a_recorded_robots_reading_for_its_host(self):
        self.assertIn("S-01: no robots reading is recorded for its host", problems(lambda d: d["hosts"].pop(0)))
        self.assertIn("S-01: no robots reading is recorded for its host",
                      problems(lambda d: d["hosts"][0].update({"robots_status": 503})))
        self.assertIn("robots_status must be 200, or 404", problems(lambda d: d["hosts"][0].update({"robots_status": 403})))

    def test_a_robots_hash_goes_with_a_robots_file_that_was_read(self):
        message = "robots_sha256 is the hash of a robots file that was read"
        self.assertIn(message, problems(lambda d: d["hosts"][0].update({"robots_sha256": None})))
        self.assertIn(message, problems(lambda d: d["hosts"][1].update({"robots_sha256": SHA})))
        self.assertIn("robots_url must be", problems(lambda d: d["hosts"][0].update({"robots_url": "https://www.govinfo.gov/robots.txt"})))
        self.assertIn("listed twice", problems(lambda d: d["hosts"].append(copy.deepcopy(d["hosts"][0]))))
        self.assertIn("crawl_delay_seconds", problems(lambda d: d["hosts"][0].update({"crawl_delay_seconds": "10"})))

    def test_hashes_ids_and_addresses_are_exact_and_unique(self):
        for sha in ("A" * 64, "a" * 63, "g" * 64, None, "a" * 64 + "\n"):
            with self.subTest(sha=sha):
                self.assertIn("S-01: sha256 must be 64 lowercase hexadecimal characters",
                              problems(lambda d: d["sources"][0].update({"sha256": sha})))
        self.assertIn("duplicate id", problems(lambda d: d["sources"][1].update({"id": "S-01"})))
        self.assertIn("id must look like S-09", problems(lambda d: d["sources"][0].update({"id": "ed-rules"})))
        self.assertIn("duplicate url", problems(lambda d: d["sources"].append(dict(d["sources"][0], id="S-03"))))
        self.assertIn("is also listed as a source",
                      problems(lambda d: d["not_reached"][0].update({"url": d["sources"][0]["url"]})))

    def test_a_printed_date_and_its_kind_agree(self):
        message = "date_printed is null exactly when date_kind is none_printed"
        self.assertIn(message, problems(lambda d: d["sources"][0].update({"date_printed": None})))
        self.assertIn(message, problems(lambda d: d["sources"][1].update({"date_printed": "January 1, 2026"})))
        self.assertIn("date_kind must be one of", problems(lambda d: d["sources"][0].update({"date_kind": "current"})))

    def test_pages_belong_to_pdf_records_only(self):
        message = "pages is a page count for a pdf and null for html"
        self.assertIn(message, problems(lambda d: d["sources"][0].update({"pages": None})))
        self.assertIn(message, problems(lambda d: d["sources"][0].update({"pages": 0})))
        self.assertIn(message, problems(lambda d: d["sources"][0].update({"pages": True})))
        self.assertIn(message, problems(lambda d: d["sources"][1].update({"pages": 3})))

    def test_enumerated_fields_and_plain_values_are_checked(self):
        self.assertIn("issuer must be one of", problems(lambda d: d["sources"][0].update({"issuer": "A law school"})))
        self.assertIn("title_source must be one of", problems(lambda d: d["sources"][0].update({"title_source": "memory"})))
        self.assertIn("read_extent must be one of", problems(lambda d: d["sources"][0].update({"read_extent": "skimmed"})))
        self.assertIn("format must be html or pdf", problems(lambda d: d["sources"][0].update({"format": "docx"})))
        self.assertIn("reason must be one of", problems(lambda d: d["not_reached"][0].update({"reason": "too slow"})))
        self.assertIn("bytes must be a positive whole number", problems(lambda d: d["sources"][0].update({"bytes": 0})))
        self.assertIn("retrieved_at_utc must look like", problems(lambda d: d["sources"][0].update({"retrieved_at_utc": "2026-11-13"})))
        self.assertIn("title must be text", problems(lambda d: d["sources"][0].update({"title": " "})))
        self.assertIn("note must be text of at most 400", problems(lambda d: d["sources"][0].update({"note": "x" * 401})))
        self.assertIn("schema_version must be 1", problems(lambda d: d.update({"schema_version": 2})))
        self.assertIn("register: no sources", problems(lambda d: d.update({"sources": []})))

    def test_a_legal_review_date_is_refused_in_every_form(self):
        for value in ("2026-11-13", True, 0, ""):
            with self.subTest(value=value):
                self.assertIn("legally_reviewed_at stays null in this file",
                              problems(lambda d: d["sources"][0].update({"legally_reviewed_at": value})))

    def test_paid_database_and_bar_names_are_refused_anywhere(self):
        for word in ("Westlaw", "KEYCITE", "wisbar.org", "LexisNexis"):
            with self.subTest(word=word):
                self.assertIn("may not appear anywhere in this file",
                              problems(lambda d: d["sources"][0].update({"note": f"Also seen on {word}."})))
        self.assertIn("may not appear anywhere in this file",
                      problems(lambda d: d["not_reached"][0].update({"note": "Read on westlaw instead."})))

    def test_en_and_em_dashes_are_refused(self):
        for dash in ("\u2013", "\u2014"):
            with self.subTest(dash=dash):
                self.assertIn("an en dash or em dash appears", problems(lambda d: d["sources"][0].update({"title": f"Rules {dash} Civil"})))


class CommandLine(unittest.TestCase):
    def run_main(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fs.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_validate_exits_zero_and_says_what_it_did_not_check(self):
        code, out, err = self.run_main("validate")
        self.assertEqual((code, err), (0, ""))
        self.assertIn("no address was requested and legal currency was not checked", out)

    def test_an_invalid_or_unreadable_register_exits_two(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "register.json"
            broken = synthetic_register()
            broken["sources"][0]["legally_reviewed_at"] = "2026-11-13"
            path.write_text(json.dumps(broken), encoding="utf-8")
            code, out, err = self.run_main("validate", "--register", str(path))
            self.assertEqual((code, out), (2, ""))
            self.assertIn("legally_reviewed_at stays null", err)
            path.write_text("{not json", encoding="utf-8")
            self.assertEqual(self.run_main("validate", "--register", str(path))[0], 2)
            self.assertEqual(self.run_main("validate", "--register", str(Path(folder) / "absent.json"))[0], 2)


if __name__ == "__main__":
    unittest.main()
