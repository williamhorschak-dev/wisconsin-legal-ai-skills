"""The county local-rules index: the committed file obeys its rules, and the rules refuse what they should."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import local_rules  # noqa: E402

SHA = "a" * 64


def verified_document(url="https://county.example/rules.pdf"):
    return {"link_text": "Local Court Rules", "title_as_printed": "LOCAL COURT RULES", "kind": "rules", "url": url,
            "host": url.split("/")[2], "host_class": "county", "format": "pdf_text",
            "printed_dates": [{"label": "Effective", "as_printed": "January 1, 2026"}], "page_count": 12, "sha256": SHA,
            "last_modified_header": None, "checked_on": "2026-11-10", "check_method": "one request; page 1 read",
            "metadata_verified": True}


def link_only_document(url="https://files.example.net/rules.pdf"):
    return {"link_text": "Circuit Court Rules", "title_as_printed": None, "kind": "rules", "url": url,
            "host": url.split("/")[2], "host_class": "outside", "format": None, "printed_dates": [], "page_count": None,
            "sha256": None, "last_modified_header": None, "checked_on": None, "check_method": None,
            "metadata_verified": False}


def synthetic_index():
    """A 72-county index built from invented hosts: one posted, one link-only, one none found, one incomplete."""
    counties = []
    for name in local_rules.county_names():
        counties.append({"county": name, "coverage": "not_checked", "access": "not_attempted", "checked_on": None,
                         "sites_checked": [], "county_hosts": [], "clerk_website": "https://county.example/clerk",
                         "note": "", "documents": [], "digest": "", "legally_reviewed_at": None})
    by_name = {c["county"]: c for c in counties}
    by_name["Ashland"].update(coverage="rules_posted", access="ok", checked_on="2026-11-10", county_hosts=["county.example"],
                              sites_checked=["https://county.example/courts"], documents=[verified_document()])
    by_name["Barron"].update(coverage="rules_posted", access="ok", checked_on="2026-11-10",
                             sites_checked=["https://county.example/courts"], documents=[link_only_document()])
    by_name["Bayfield"].update(coverage="none_found", access="ok", checked_on="2026-11-10", county_hosts=["county.example"],
                               sites_checked=["https://county.example/courts"], note="Only that page was read.")
    by_name["Brown"].update(coverage="not_checked", access="timeout", checked_on="2026-11-10",
                            sites_checked=["https://county.example/courts"], note="The page did not answer.")
    return {"schema_version": 1, "review_label": local_rules.REVIEW_LABEL, "scope": "Synthetic test index.",
            "clerk_directory": {"url": "https://www.wicourts.gov/courts/circuit/clerkcontact.htm",
                                "page_updated_as_printed": "June 15, 2026", "read_on": "2026-11-10"},
            "counties": counties}


class LocalRulesIndexTests(unittest.TestCase):
    def county(self, data, name):
        return next(c for c in data["counties"] if c["county"] == name)

    def assertRefused(self, mutate, fragment):
        data = synthetic_index()
        mutate(data)
        errors = local_rules.validate(data)
        self.assertTrue(any(fragment in e for e in errors), f"expected a refusal containing {fragment!r}; got {errors}")

    # --- the committed files ---

    def test_committed_index_is_valid_and_has_72_counties(self):
        data = json.loads(local_rules.INDEX.read_text(encoding="utf-8"))
        self.assertEqual(local_rules.validate(data), [])
        self.assertEqual(len(data["counties"]), 72)
        self.assertTrue(all(c["digest"] == "" and c["legally_reviewed_at"] is None for c in data["counties"]))

    def test_committed_markdown_is_the_rendering_of_the_index(self):
        data = json.loads(local_rules.INDEX.read_text(encoding="utf-8"))
        self.assertEqual(local_rules.MARKDOWN.read_text(encoding="utf-8"), local_rules.render(data),
                         "run: python scripts/local_rules.py render")

    def test_committed_index_never_names_the_state_bar_site(self):
        for path in (local_rules.INDEX, local_rules.MARKDOWN):
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("wisbar.org/", text)
            self.assertNotIn("//wisbar.org", text)
            self.assertNotIn(".wisbar.org", text)

    # --- the synthetic index ---

    def test_synthetic_index_is_valid(self):
        self.assertEqual(local_rules.validate(synthetic_index()), [])

    def test_county_list_must_be_exact(self):
        self.assertRefused(lambda d: d["counties"].pop(), "exactly the 72 county names")
        self.assertRefused(lambda d: d["counties"].reverse(), "exactly the 72 county names")
        self.assertRefused(lambda d: self.county(d, "Dane").update(county="Example"), "exactly the 72 county names")

    def test_reserved_and_fixed_fields(self):
        self.assertRefused(lambda d: self.county(d, "Ashland").update(digest="Briefs are limited to ten pages."), "digest is reserved")
        self.assertRefused(lambda d: self.county(d, "Ashland").update(legally_reviewed_at="2026-11-10"), "legally_reviewed_at must be null")
        self.assertRefused(lambda d: d.update(review_label="Reviewed"), "review_label")
        self.assertRefused(lambda d: self.county(d, "Dane").update(extra=1), "expected exactly the keys")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(extra=1), "expected exactly the keys")

    def test_a_county_that_was_not_checked_carries_nothing(self):
        self.assertRefused(lambda d: self.county(d, "Dane").update(checked_on="2026-11-10"), "carries no date")
        self.assertRefused(lambda d: self.county(d, "Dane").update(sites_checked=["https://county.example/x"]), "carries no date")
        self.assertRefused(lambda d: self.county(d, "Dane").update(documents=[verified_document()]), "carries no date")

    def test_an_incomplete_check_is_not_a_finding(self):
        self.assertRefused(lambda d: self.county(d, "Brown").update(note=""), "needs a note")
        self.assertRefused(lambda d: self.county(d, "Brown").update(access="ok"), "must record what it found")
        self.assertRefused(lambda d: self.county(d, "Brown").update(documents=[verified_document()]), "records no documents")
        self.assertRefused(lambda d: self.county(d, "Brown").update(checked_on=None), "checked_on must be a date")
        self.assertRefused(lambda d: self.county(d, "Bayfield").update(access="timeout"), "needs access ok")
        self.assertRefused(lambda d: self.county(d, "Bayfield").update(access="not_attempted"), "needs the access outcome")

    def test_coverage_must_match_the_documents(self):
        self.assertRefused(lambda d: self.county(d, "Bayfield").update(documents=[verified_document()]), "none_found records no documents")
        self.assertRefused(lambda d: self.county(d, "Ashland").update(documents=[]), "needs at least one document")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(kind="form"), "needs a document of kind rules")
        self.assertRefused(lambda d: self.county(d, "Ashland").update(coverage="other_documents_only"), "cannot hold a document of kind rules")
        self.assertRefused(lambda d: self.county(d, "Bayfield").update(sites_checked=[]), "must name the pages requested")

    def test_state_bar_copies_are_never_indexed(self):
        for host in ("wisbar.org", "www.wisbar.org"):
            url = f"https://{host}/rules.pdf"
            self.assertRefused(lambda d: self.county(d, "Barron").update(documents=[link_only_document(url)]), "wisbar.org")
            self.assertRefused(lambda d: self.county(d, "Bayfield").update(sites_checked=[url]), "wisbar.org")
            self.assertRefused(lambda d: self.county(d, "Dane").update(clerk_website=url), "wisbar.org")
            self.assertRefused(lambda d: self.county(d, "Ashland").update(county_hosts=["county.example", host]), "county_hosts")

    def test_hosts_are_parsed_not_trusted(self):
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(host="other.example"), "host must be the url's own host")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(host_class="court"), "host_class must be county")
        self.assertRefused(lambda d: self.county(d, "Ashland").update(county_hosts=[]), "host_class must be outside")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(url="http://county.example/rules.pdf"), "https")

    def test_an_outside_host_document_is_a_link_only(self):
        def claim_metadata(d):
            self.county(d, "Barron")["documents"] = [dict(verified_document("https://files.example.net/rules.pdf"), host_class="outside")]
        self.assertRefused(claim_metadata, "metadata from an outside host is unverified")
        self.assertRefused(lambda d: self.county(d, "Barron")["documents"][0].update(title_as_printed="RULES"), "records only its link")
        self.assertRefused(lambda d: self.county(d, "Barron")["documents"][0].update(page_count=3), "records only its link")
        self.assertRefused(lambda d: self.county(d, "Barron")["documents"][0].update(printed_dates=[{"label": "Effective", "as_printed": "2026"}]),
                           "records only its link")
        # The two approved exceptions may record what one read of the named document showed.
        data = synthetic_index()
        adams = self.county(data, "Adams")
        adams.update(coverage="rules_posted", access="ok", checked_on="2026-11-10", sites_checked=["https://county.example/courts"],
                     documents=[dict(verified_document("https://files.example.net/rules.pdf"), host_class="outside")])
        self.assertEqual(local_rules.validate(data), [])

    def test_a_verified_document_needs_its_evidence(self):
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(sha256="abc"), "sha256")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(checked_on=None), "checked_on")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(check_method=""), "check_method")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(page_count=None), "needs its page count")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(format="html"), "has no page count")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(printed_dates=[{"label": "Effective"}]), "printed_dates")
        self.assertRefused(lambda d: self.county(d, "Ashland")["documents"][0].update(format="docx"), "format must be one of")

    # --- rendering ---

    def test_rendering_states_each_status_in_fixed_words(self):
        text = local_rules.render(synthetic_index())
        rows = [line for line in text.splitlines() if line.startswith("| ") and not line.startswith("| County") and not line.startswith("|---")]
        self.assertEqual(len(rows), 72)
        self.assertIn("| Ashland | Rules found posted on 2026-11-10. |", text)
        self.assertIn("| Barron | A link to a rules document was found on 2026-11-10; the document was not read. |", text)
        self.assertIn("| Bayfield | No in-scope copy found in the government sources checked as of 2026-11-10. |", text)
        self.assertIn("| Brown | Check incomplete on 2026-11-10 (timeout). The index cannot say what this county posts. |", text)
        self.assertIn("| Dane | Not yet indexed. |", text)
        self.assertIn("Title, date, length and contents were not read.", text)
        self.assertNotIn("has no local rules\n", text.replace("Never say the county has no local rules", ""))
        self.assertNotIn("—", text)
        self.assertNotIn("–", text)

    def test_rendering_does_not_depend_on_field_order(self):
        data = synthetic_index()
        shuffled = copy.deepcopy(data)
        shuffled["counties"] = [dict(reversed(list(c.items()))) for c in shuffled["counties"]]
        self.assertEqual(local_rules.render(data), local_rules.render(shuffled))

    # --- command line ---

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["local_rules.py", *argv]), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = local_rules.main()
        return code, out.getvalue(), err.getvalue()

    def test_command_line_validates_and_checks_the_committed_files(self):
        code, out, _ = self.run_main("validate")
        self.assertEqual(code, 0)
        self.assertIn("no rule text is held", out)
        code, out, _ = self.run_main("render", "--check")
        self.assertEqual(code, 0)

    def test_command_line_refuses_an_invalid_index(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            bad = synthetic_index()
            self.county(bad, "Ashland")["digest"] = "A rule summary."
            path = Path(directory) / "counties.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with mock.patch.object(local_rules, "INDEX", path):
                code, _, err = self.run_main("validate")
            self.assertEqual(code, 2)
            self.assertIn("digest is reserved", err)

    def test_script_opens_no_network_connection(self):
        source = (ROOT / "scripts/local_rules.py").read_text(encoding="utf-8")
        for name in ("urllib.request", "http.client", "socket", "requests", "subprocess"):
            self.assertNotIn(f"import {name}", source)
            self.assertNotIn(f"from {name}", source)


if __name__ == "__main__":
    unittest.main()
