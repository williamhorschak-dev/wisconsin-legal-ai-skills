"""Regression checks from the second review of the federal source register (findings R64-01 to R64-07)."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from test_federal_sources import fs, synthetic_register

# What each of these saved responses prints, checked by eye against the kept body with this hash.
FACE_ORACLE = [
    ("S-21", "7225b63872ec3187a342a92bad2c855c5adeaecf834092806aa66f3f4815c721", {"date_printed": "last amended in 2025", "date_kind": "amendment"}),
    ("S-24", "6874a45535211871084e312d5820bdfddfc66676a7c15dcbef57f77db83709db", {"title": "Pro Se Frequently Asked Questions"}),
    ("S-32", "ef691e74e19099530a7c9f03ca579fdc5873faef97450a15a59218cc5cd0b811", {"date_printed": "became effective December 1, 2025", "date_kind": "effective"}),
    ("S-40", "696184b7941a8681e8d164efe0f70a43f79c037ef2a01ba97f7dcb3831076310", {"title": "All Forms"}),
    ("S-41", "02f34b98ef6cbe3587b48e0ee24996a92c6b83a6c106955f7390dc38d4b3c68f", {"title": "All Forms"}),
    ("S-48", "51726fd2dac1b42fa8943d0ee0755b2a5acddc4b0e030a405f33a41af9c61628", {"title": "Local Rules General, Civil, and Criminal"}),
    ("S-49", "a538634232b7809314ff7baa9c1947dad3931c8dac4782083eddc2de74880ff9", {"date_kind": "unlabeled_mark"}),
    ("S-50", "bd8705fc038d87e4fe222a7ea2e4324222c9430e2373fce56826bd2dfa2f8baf", {"date_printed": "DECEMBER 1, 2025"}),
    ("S-56", "a6f417607a71c05a3a54df68a43ec67e691dcf276c46a415e78038ae4f9305f4", {"date_printed": "DECEMBER 1, 2025"}),
    ("S-64", "53ce0e33f484f309c92c788cb6289edeb5d3ec71789779db330a1bd943a36852", {"date_printed": "[drafted 5/7/24]", "date_kind": "drafted"}),
    ("S-67", "31a68db82b2179cd4188cc97a191bfc1cb99cdc58e22c2c776c9b3566a44d142", {"date_printed": "Entered this 4th day of October, 2007."}),
    ("S-69", "2a9a81ce084be3a8b0ebb4ba8590ee8a71322d2798a97a8c36e50d6851d43ff8", {"date_printed": "Entered February 2, 2024.", "date_kind": "entry"}),
    ("S-70", "f101465183738c09888201d2f27402e2fcc1e20d327fad980ffc9cd1614c9da5", {"date_printed": "Entered this 10th day of MAY, 2018.", "date_kind": "entry"}),
    ("S-77", "d9684d35d10cdfb677a76ba2dbea87a3f735ed3b19347ceeddcf01f15f1848d5", {"date_printed": "this 26th day of September, 2025.", "date_kind": "order_date"}),
]


def run_validate(text):
    """Exit code and standard output of the command on a register file holding exactly this text."""
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "register.json"
        path.write_text(text, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = fs.main(["validate", "--register", str(path)])
        return code, out.getvalue()


def refused(change):
    data = synthetic_register()
    change(data)
    return bool(fs.validate(data))


class TimingAndCounts(unittest.TestCase):  # R64-01
    def test_source_hosts_are_counted_apart_from_robots_readings(self):
        data = synthetic_register()
        data["sources"] = data["sources"][:1]
        code, out = run_validate(json.dumps(data))
        self.assertEqual(code, 0)
        self.assertIn("1 source hosts; 2 host readings", out)

    def test_the_method_discloses_the_recorded_circuit_interval(self):
        register = json.loads(fs.REGISTER.read_text(encoding="utf-8"))
        robots = {host["host"]: host["retrieved_at_utc"] for host in register["hosts"]}
        home = next(source for source in register["sources"] if source["id"] == "S-08")
        self.assertEqual((robots["www.ca7.uscourts.gov"], home["retrieved_at_utc"]),
                         ("2026-11-14T02:02:25Z", "2026-11-14T02:02:28Z"))
        self.assertIn("three seconds", register["method"])
        self.assertIn("did not apply the Seventh Circuit's 10 second delay", register["method"])


class FaceRecords(unittest.TestCase):  # R64-02
    def test_transcriptions_for_the_inspected_bodies(self):
        register = json.loads(fs.REGISTER.read_text(encoding="utf-8"))
        by_id = {source["id"]: source for source in register["sources"]}
        for source_id, digest, expected in FACE_ORACLE:
            with self.subTest(source=source_id):
                self.assertEqual(by_id[source_id]["sha256"], digest, "a new body needs its face read again")
                for name, value in expected.items():
                    self.assertEqual(by_id[source_id][name], value)

    def test_the_new_date_kinds_are_accepted_and_used(self):
        register = json.loads(fs.REGISTER.read_text(encoding="utf-8"))
        used = {source["date_kind"] for source in register["sources"]}
        self.assertTrue({"drafted", "order_date", "unlabeled_mark"} <= used)
        self.assertTrue(used <= set(fs.DATE_KINDS))


class DuplicateMembers(unittest.TestCase):  # R64-03
    def test_a_repeated_json_member_is_refused_at_any_depth(self):
        raw = json.dumps(synthetic_register())
        for key, value in (("schema_version", 1), ("pages", 12), ("legally_reviewed_at", None)):
            single = json.dumps(key) + ": " + json.dumps(value)
            with self.subTest(key=key):
                self.assertIn(single, raw)
                self.assertEqual(run_validate(raw.replace(single, single + ", " + single, 1))[0], 2)

    def test_a_review_date_cannot_hide_behind_a_later_null(self):
        raw = json.dumps(synthetic_register())
        single = '"legally_reviewed_at": null'
        self.assertEqual(run_validate(raw.replace(single, '"legally_reviewed_at": "2026-11-13", ' + single, 1))[0], 2)

    def test_nonstandard_number_constants_are_refused(self):
        raw = json.dumps(synthetic_register())
        for constant in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(constant=constant):
                changed = raw.replace('"crawl_delay_seconds": 10', '"crawl_delay_seconds": ' + constant, 1)
                self.assertNotEqual(changed, raw)
                self.assertEqual(run_validate(changed)[0], 2)


class Addresses(unittest.TestCase):  # R64-04
    def test_an_address_has_one_plain_spelling(self):
        base = "https://www.example.uscourts.gov"
        for tail in ("/a b", "/a\\b", "/a#", "/a#section", "/a\tb", "/a\nb", "/a%", "/a%zz", "/a?", "", "/a "):
            with self.subTest(tail=tail):
                self.assertFalse(fs._official(base + tail))
        self.assertFalse(fs._official(" " + base + "/a"))
        self.assertTrue(fs._official(base + "/"))
        self.assertTrue(fs._official(base + "/a%20b?x=1&y=2"))

    def test_a_host_is_made_of_valid_lower_case_labels(self):
        for name in (".uscourts.gov", "a_b.uscourts.gov", "-a.uscourts.gov", "a..uscourts.gov", "WWW.uscourts.gov",
                     "www.uscourts.gov.", "x" * 64 + ".uscourts.gov", None, 7):
            with self.subTest(name=name):
                self.assertFalse(fs.permitted(name))
        self.assertTrue(fs.permitted("www.wied.uscourts.gov"))


class RobotsAgreement(unittest.TestCase):  # R64-05
    def test_a_host_with_no_robots_file_has_no_hash_and_no_delay(self):
        for field, value in (("robots_sha256", ""), ("robots_sha256", 7), ("robots_sha256", []), ("crawl_delay_seconds", 10)):
            with self.subTest(field=field, value=value):
                self.assertTrue(refused(lambda d: d["hosts"][1].update({field: value})))

    def test_a_robots_status_is_a_whole_number(self):
        self.assertTrue(refused(lambda d: d["hosts"][0].update({"robots_status": 200.0})))

    def test_a_missed_address_needs_a_matching_robots_reading(self):
        # A robots refusal on a host recorded as having no robots file, and a host with no reading at all.
        for url in ("https://www.govinfo.gov/missing", "https://new.uscourts.gov/missing"):
            with self.subTest(url=url):
                self.assertTrue(refused(lambda d: d["not_reached"][0].update({"url": url})))
        self.assertTrue(refused(lambda d: d["not_reached"].append(dict(d["not_reached"][0]))))

    def test_a_source_does_not_come_before_its_robots_reading(self):
        self.assertTrue(refused(lambda d: d["sources"][0].update({"retrieved_at_utc": "2001-01-01T00:00:00Z"})))


class IdsAndTimes(unittest.TestCase):  # R64-06
    def test_a_bad_id_is_refused_without_a_traceback(self):
        for bad in ([], {}, "S-001", "S-00", "S-9", "s-09"):
            with self.subTest(bad=bad):
                self.assertTrue(refused(lambda d: d["sources"][0].update({"id": bad})))

    def test_a_retrieval_time_is_a_past_instant_in_one_spelling(self):
        for value in ("2999-01-01T00:00:00Z", "2001-1-2T0:0:0Z", "2026-02-30T00:00:00Z"):
            with self.subTest(value=value):
                self.assertFalse(fs._stamp(value))
        self.assertTrue(fs._stamp("2000-02-29T00:00:00Z"))

    def test_the_schema_version_is_the_whole_number_one(self):
        for value in (1.0, True, "1"):
            with self.subTest(value=value):
                self.assertTrue(refused(lambda d: d.update({"schema_version": value})))


class Strings(unittest.TestCase):  # R64-07, adopted in part
    def test_decoded_strings_are_ascii(self):
        self.assertTrue(refused(lambda d: d["sources"][0].update({"note": "A title with \u200bformatting."})))
        escaped = json.dumps(synthetic_register()).replace("Example Local Rules", "Example \\u2011 Rules")
        self.assertEqual(run_validate(escaped)[0], 2)

    def test_a_name_is_matched_after_one_level_of_percent_decoding(self):
        with mock.patch.object(fs, "FORBIDDEN_WORDS", ("sample",)):
            self.assertTrue(refused(lambda d: d["sources"][0].update({"note": "A %73ample label"})))
            self.assertTrue(refused(lambda d: d["sources"][0].update({"note": "A SampleNext label"})))
            self.assertFalse(refused(lambda d: d["sources"][0].update({"note": "A harmless label"})))

    def test_ordinary_words_that_contain_or_span_a_name_are_not_refused(self):
        # Not adopted from the review: removing white space before matching. It refuses each of these.
        for note in ("Order signed by Judge Alexis Example.", "Midwest Law Library hours.", "A complex issue."):
            with self.subTest(note=note):
                self.assertFalse(refused(lambda d: d["sources"][0].update({"note": note})))


if __name__ == "__main__":
    unittest.main()
