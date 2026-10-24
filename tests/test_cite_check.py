"""Check evidence integrity and honest reporting with synthetic text, never law."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills" /
          "cite-check" / "scripts" / "cite_check.py")
MODULE_SPEC = importlib.util.spec_from_file_location("citation_checker_test", SCRIPT)
checker = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(checker)
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "cite_check"


class CitationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sources = self.root / "sources"
        self.sources.mkdir()
        self.source = self.sources / "Synthetic Source.txt"
        self.source.write_text("Synthetic source. The fictional rule applies only when stated.\n", encoding="utf-8")
        self.document = self.root / "draft.md"
        self.document.write_text("Synthetic Draft. Test Provision section 1.\n", encoding="utf-8")
        self.inventory_path = self.root / "inventory.json"
        self.inv = {
            "document_sha256": checker.digest(self.document),
            "uses": [{"id": "u1", "citation": "Test Provision section 1",
                      "kind": "rule", "proposition": "A synthetic rule applies."}],
        }
        self.save_inventory()
        self.log = self.root / "evidence.jsonl"
        self.report_path = self.root / "report.md"

    def save_inventory(self):
        self.inventory_path.write_text(json.dumps(self.inv), encoding="utf-8-sig")

    def evidence(self, check="citation", result="pass", **changes):
        entry = {
            "document_sha256": self.inv["document_sha256"],
            "inventory_sha256": checker.inventory_digest(self.inv),
            "use": "u1", "check": check, "result": result,
            "file": self.source.name, "sha256": checker.digest(self.source),
            "locator": "Synthetic section 1", "matched": "The fictional rule applies only when stated.",
            "method": "manual", "note": "Synthetic test attestation only; no real legal review.",
        }
        entry.update(changes)
        return entry

    def cli(self, command, *options):
        return subprocess.run(
            [sys.executable, str(SCRIPT), command, "--inventory", str(self.inventory_path),
             "--document", str(self.document), "--sources", str(self.sources),
             "--log", str(self.log), *options],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def report(self):
        return self.cli("report", "--out", str(self.report_path))

    def test_append_preserves_accepted_log_endings(self):
        for ending in (b"", b"\n", b"\r\n", b"\r"):
            with self.subTest(ending=ending):
                original = json.dumps(self.evidence("citation"), ensure_ascii=False).encode("utf-8") + ending
                self.log.write_bytes(original)
                checker.append_entry(self.log, self.evidence("pincite"), self.inv, self.sources)
                self.assertTrue(self.log.read_bytes().startswith(original))
                self.assertEqual([e["check"] for e in checker.read_log(self.log, self.inv, self.sources)], ["citation", "pincite"])

    def test_append_to_empty_log_and_reject_malformed_without_changing_it(self):
        self.log.write_bytes(b"")
        checker.append_entry(self.log, self.evidence(), self.inv, self.sources)
        self.assertEqual(len(checker.read_log(self.log, self.inv, self.sources)), 1)
        original = b'{"unfinished":'
        self.log.write_bytes(original)
        with self.assertRaises(ValueError):
            checker.append_entry(self.log, self.evidence("pincite"), self.inv, self.sources)
        self.assertEqual(self.log.read_bytes(), original)

    def test_missing_checks_create_unverified_report_with_nonzero_status(self):
        result = self.report()
        self.assertEqual(result.returncode, 1, result.stderr)
        text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("| UNVERIFIED |", text)
        self.assertIn("proposition: missing", text)
        self.assertIn("treatment: missing", text)

    def test_report_path_outside_console_code_page_does_not_report_failure(self):
        # Piped Windows output is cp1252; U+0141 is not in it. The report is already written.
        out = self.root / "report-Łukasz.md"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "report", "--inventory", str(self.inventory_path),
             "--document", str(self.document), "--sources", str(self.sources),
             "--log", str(self.log), "--out", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        )
        self.assertTrue(out.exists())
        self.assertEqual(result.returncode, 1, result.stderr)  # 1 = incomplete evidence, not a crash
    def test_report_says_the_evidence_log_is_not_tamper_evident(self):
        self.assertEqual(self.report().returncode, 1)
        text = " ".join(self.report_path.read_text(encoding="utf-8").split())
        self.assertIn("ordinary local file", text)
        self.assertIn("not a deleted, inserted or hand-edited log line", text)

    def test_structured_provenance_binds_original_and_survives_report(self):
        provenance = {"origin": "supplied synthetic document", "retrieved_at": "2026-09-20T14:00:00Z",
                      "version": "synthetic version 1", "extraction_method": "native text",
                      "original_file": self.source.name, "original_sha256": checker.digest(self.source)}
        entry = self.evidence(provenance=provenance)
        checker.append_entry(self.log, entry, self.inv, self.sources)
        records = checker.read_log(self.log, self.inv, self.sources)
        self.assertEqual(records[0]["provenance"], provenance)
        self.assertIn("synthetic version 1", checker.report(self.inv, records)[0])
        for changes in ({"retrieved_at": "2026-09-20"}, {"retrieved_at": "not a date"},
                        {"original_sha256": "0" * 64}, {"original_file": "../outside.txt"}, {"version": ""}):
            with self.subTest(changes=changes), self.assertRaises((ValueError, OSError)):
                checker.validate_entry(self.evidence(provenance={**provenance, **changes}), self.inv, self.sources)

    def test_complete_log_is_recorded_pass_with_hashes_and_explicit_limits(self):
        for check in checker.required_checks(self.inv["uses"][0]):
            checker.append_entry(self.log, self.evidence(check), self.inv, self.sources)
        result = self.report()
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("| RECORDED PASS |", text)
        self.assertIn(checker.digest(self.document), text)
        self.assertIn(checker.digest(self.source), text)
        self.assertIn(checker.inventory_digest(self.inv), text)
        self.assertIn("not an independent finding", text)
        self.assertIn("inventory completeness", text)

    def test_failed_and_caution_checks_cannot_be_reported_as_complete(self):
        for result_value, expected_status in (("fail", "FLAGGED"), ("caution", "UNVERIFIED")):
            with self.subTest(result=result_value):
                entries = [self.evidence(check, result_value if check == "treatment" else "pass")
                           for check in checker.required_checks(self.inv["uses"][0])]
                text, incomplete = checker.report(self.inv, entries)
                self.assertTrue(incomplete)
                self.assertIn(f"| {expected_status} |", text)

    def test_case_treatment_requires_named_citator_and_free_screen_remains_unverified(self):
        self.inv["uses"][0]["kind"] = "case"
        for missing_name in (None, True, "   "):
            with self.subTest(citator=missing_name):
                with self.assertRaisesRegex(ValueError, "citator"):
                    checker.validate_entry(self.evidence("treatment", citator=missing_name), self.inv, self.sources)
        caution = self.evidence("treatment", "caution", note="Free source screen only.")
        checker.validate_entry(caution, self.inv, self.sources)
        checker.validate_entry(self.evidence("treatment", citator="Synthetic citator test"), self.inv, self.sources)

    def test_record_use_requires_record_checks_instead_of_legal_treatment(self):
        self.inv["uses"][0]["kind"] = "record"
        entries = [self.evidence(name) for name in ("record", "pincite", "format")]
        for entry in entries:
            checker.validate_entry(entry, self.inv, self.sources)
        text, incomplete = checker.report(self.inv, entries)
        self.assertFalse(incomplete)
        self.assertIn("| RECORDED PASS |", text)
        with self.assertRaises(ValueError):
            checker.validate_entry(self.evidence("treatment"), self.inv, self.sources)

    def test_duplicate_check_is_refused_without_rewriting_the_log(self):
        entry = self.evidence()
        checker.append_entry(self.log, entry, self.inv, self.sources)
        original = self.log.read_bytes()
        with self.assertRaises(ValueError):
            checker.append_entry(self.log, self.evidence(result="fail"), self.inv, self.sources)
        self.assertEqual(self.log.read_bytes(), original)

    def test_existing_report_is_never_replaced(self):
        original = b"Existing report for a prior review."
        self.report_path.write_bytes(original)
        result = self.report()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.report_path.read_bytes(), original)

    def test_changed_document_refuses_report_and_preserves_prior_log(self):
        checker.append_entry(self.log, self.evidence(), self.inv, self.sources)
        original = self.log.read_bytes()
        self.document.write_text("Revised synthetic proposition.\n", encoding="utf-8")
        result = self.report()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("document hash differs", result.stderr)
        self.assertFalse(self.report_path.exists())
        self.assertEqual(self.log.read_bytes(), original)

    def test_changed_source_refuses_report_and_preserves_prior_log(self):
        checker.append_entry(self.log, self.evidence(), self.inv, self.sources)
        original = self.log.read_bytes()
        self.source.write_text("Source corrected after attestation.\n", encoding="utf-8")
        result = self.report()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("source hash differs", result.stderr)
        self.assertFalse(self.report_path.exists())
        self.assertEqual(self.log.read_bytes(), original)

    def test_changed_inventory_cannot_reuse_a_complete_log(self):
        for check in checker.required_checks(self.inv["uses"][0]):
            checker.append_entry(self.log, self.evidence(check), self.inv, self.sources)
        original = self.log.read_bytes()
        self.inv["uses"][0]["proposition"] = "An altered proposition never reviewed."
        self.save_inventory()
        result = self.report()
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("inventory", result.stderr)
        self.assertFalse(self.report_path.exists())
        self.assertEqual(self.log.read_bytes(), original)

    def test_whitespace_or_normalized_empty_quote_cannot_pass(self):
        for quote in ("   ", "\n\t", "\u00ad"):
            with self.subTest(quote=repr(quote)):
                self.inv["uses"][0]["quote"] = quote
                self.save_inventory()
                result = self.cli("quote", "--use", "u1", "--file", self.source.name, "--locator", "Synthetic section 1")
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.log.exists())

    def test_cli_refuses_evidence_explicitly_bound_to_another_inventory(self):
        entry_path = self.root / "entry.json"
        entry_path.write_text(json.dumps(self.evidence(inventory_sha256="0" * 64)), encoding="utf-8")
        result = self.cli("record", "--entry", str(entry_path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.log.exists())

    def test_cli_refuses_evidence_explicitly_bound_to_another_draft(self):
        entry_path = self.root / "entry.json"
        entry_path.write_text(json.dumps(self.evidence(document_sha256="0" * 64)), encoding="utf-8")
        result = self.cli("record", "--entry", str(entry_path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(self.log.exists())

    def test_quote_match_checks_text_but_does_not_complete_other_checks(self):
        self.inv["uses"][0]["quote"] = "The fictional rule applies only when stated."
        self.save_inventory()
        result = self.cli("quote", "--use", "u1", "--file", self.source.name, "--locator", "Synthetic section 1")
        self.assertEqual(result.returncode, 0, result.stderr)
        entries = checker.read_log(self.log, self.inv, self.sources)
        self.assertEqual(entries[0]["result"], "pass")
        self.assertEqual(entries[0]["matched"], self.inv["uses"][0]["quote"])
        result = self.report()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("| UNVERIFIED |", self.report_path.read_text(encoding="utf-8"))

    def test_absent_quote_records_failure_and_flags_report(self):
        self.inv["uses"][0]["quote"] = "A sentence absent from the synthetic source."
        self.save_inventory()
        result = self.cli("quote", "--use", "u1", "--file", self.source.name, "--locator", "Synthetic section 1")
        self.assertEqual(result.returncode, 0, result.stderr)  # The failed check was recorded successfully.
        entries = checker.read_log(self.log, self.inv, self.sources)
        self.assertEqual(entries[0]["result"], "fail")
        self.assertEqual(self.report().returncode, 1)
        self.assertIn("| FLAGGED |", self.report_path.read_text(encoding="utf-8"))

    def test_quote_match_does_not_start_or_end_inside_a_word_or_number(self):
        self.source.write_text("Synthetic source. The period is 130 days after entry, subject to rules.\n", encoding="utf-8")
        for quote, expected in (("30 days after entry", "fail"), ("he period is", "fail"),
                                ("130 days after entr", "fail"), ("130 days after entry", "pass"),
                                ("The period is 130 days", "pass")):
            with self.subTest(quote=quote):
                log = self.root / f"log-{abs(hash(quote))}.jsonl"
                self.inv["uses"][0]["quote"] = quote
                self.save_inventory()
                result = subprocess.run(
                    [sys.executable, str(SCRIPT), "quote", "--inventory", str(self.inventory_path),
                     "--document", str(self.document), "--sources", str(self.sources),
                     "--log", str(log), "--use", "u1", "--file", self.source.name, "--locator", "s. 1"],
                    capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
                self.assertEqual(result.returncode, 0, result.stderr)
                entries = checker.read_log(log, self.inv, self.sources)
                self.assertEqual(entries[0]["result"], expected)

    def test_exact_text_record_uses_the_same_word_boundary_rule(self):
        self.source.write_text("Synthetic source. The period is 130 days after entry.\n", encoding="utf-8")
        self.inv["uses"][0]["quote"] = "30 days after entry"
        self.save_inventory()
        pass_entry = self.evidence("verbatim", "pass", method="exact-text", matched="30 days after entry")
        with self.assertRaises(ValueError):
            checker.append_entry(self.log, pass_entry, self.inv, self.sources)
    def test_manual_verbatim_pass_cannot_assert_a_quote_the_text_source_lacks(self):
        self.inv["uses"][0]["quote"] = "A sentence that is not in the synthetic source."
        self.save_inventory()
        forged = self.evidence("verbatim", "pass", matched="A sentence that is not in the synthetic source.")
        with self.assertRaisesRegex(ValueError, "verbatim pass refused"):
            checker.append_entry(self.log, forged, self.inv, self.sources)
        self.assertFalse(self.log.exists() and self.log.read_bytes())
        # The reviewer can still record that the text does not support the quote.
        checker.append_entry(self.log, self.evidence("verbatim", "caution", matched=""), self.inv, self.sources)

    def test_manual_verbatim_pass_also_respects_word_boundaries(self):
        self.source.write_text("Synthetic source. The period is 130 days after entry.\n", encoding="utf-8")
        self.inv["uses"][0]["quote"] = "30 days after entry"
        self.save_inventory()
        forged = self.evidence("verbatim", "pass", matched="30 days after entry")
        with self.assertRaisesRegex(ValueError, "verbatim pass refused"):
            checker.append_entry(self.log, forged, self.inv, self.sources)

    def test_report_distinguishes_compared_from_attested_verbatim_results(self):
        self.inv["uses"][0]["quote"] = "The fictional rule applies only when stated."
        self.save_inventory()
        for check in checker.required_checks(self.inv["uses"][0]):
            checker.append_entry(self.log, self.evidence(check, matched=self.inv["uses"][0]["quote"]) if check == "verbatim"
                                 else self.evidence(check), self.inv, self.sources)
        self.assertEqual(self.report().returncode, 0)
        manual_text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("reviewer attestation; the tool confirmed the quotation appears in the archived text, nothing more", manual_text)
        self.assertNotIn("reviewer attestation, not compared by the tool", manual_text)
        second = self.root / "second.jsonl"
        checker.append_entry(second, self.evidence("verbatim", method="exact-text", matched=self.inv["uses"][0]["quote"]), self.inv, self.sources)
        text, _ = checker.report(self.inv, checker.read_log(second, self.inv, self.sources))
        self.assertIn("text compared by the tool", text)

    def test_report_keeps_not_compared_label_for_manual_verbatim_without_text_source(self):
        pdf = self.sources / "Synthetic Source.pdf"
        pdf.write_bytes(b"%PDF-1.4 synthetic placeholder, not a real document\n")
        self.inv["uses"][0]["quote"] = "The fictional rule applies only when stated."
        self.save_inventory()
        quote = self.inv["uses"][0]["quote"]
        for check in checker.required_checks(self.inv["uses"][0]):
            extra = {"file": pdf.name, "sha256": checker.digest(pdf)} if check == "verbatim" else {}
            checker.append_entry(self.log, self.evidence(check, matched=quote, **extra) if check == "verbatim"
                                 else self.evidence(check), self.inv, self.sources)
        self.assertEqual(self.report().returncode, 0)
        text = self.report_path.read_text(encoding="utf-8")
        self.assertIn("reviewer attestation, not compared by the tool", text)
        self.assertNotIn("the tool confirmed the quotation appears", text)
        # A manual verbatim caution against a text source was not confirmed either.
        second = self.root / "second.jsonl"
        checker.append_entry(second, self.evidence("verbatim", "caution", matched=""), self.inv, self.sources)
        caution, _ = checker.report(self.inv, checker.read_log(second, self.inv, self.sources))
        self.assertIn("reviewer attestation, not compared by the tool", caution)
        self.assertNotIn("the tool confirmed the quotation appears", caution)

    def test_source_paths_cannot_escape_archive_or_use_windows_devices(self):
        outside = self.root / "outside.txt"
        outside.write_text("Outside archive", encoding="utf-8")
        for name in ("../outside.txt", str(outside), "C:/outside.txt", "C:outside.txt", "sources\\test.txt", "CON", "NUL.txt", "source.txt:stream"):
            with self.subTest(name=name):
                with self.assertRaises((ValueError, OSError)):
                    checker.source_path(self.sources, name)
        self.assertEqual(checker.source_path(self.sources, self.source.name), self.source.resolve())

    def test_windows_reserved_names_are_detected_on_any_platform(self):
        for name in ("CON", "con", "Prn", "AUX", "NUL", "nul.txt", "COM1", "com9.log", "LPT1", "lpt9.txt", "NUL .txt"):
            with self.subTest(reserved=name):
                self.assertTrue(checker.is_windows_reserved_name(name))
        for name in ("source.txt", "console.txt", "COM0", "COM10", "LPT0", "nullify", "my.nul", "archive"):
            with self.subTest(allowed=name):
                self.assertFalse(checker.is_windows_reserved_name(name))

    def test_symlink_source_cannot_escape_archive(self):
        outside = self.root / "outside.txt"
        outside.write_text("Outside archive", encoding="utf-8")
        link = self.sources / "linked.txt"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlink creation unavailable: {exc}")
        with self.assertRaises(ValueError):
            checker.source_path(self.sources, link.name)

    def test_invalid_inventory_and_pass_without_evidence_are_rejected(self):
        self.inv["uses"].append(dict(self.inv["uses"][0]))
        self.save_inventory()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            checker.inventory(self.inventory_path, self.document)
        self.inv["uses"].pop()
        entry = self.evidence()
        entry.pop("matched")
        with self.assertRaises(ValueError):
            checker.validate_entry(entry, self.inv, self.sources)

    def test_exact_text_attestation_cannot_claim_an_absent_quote(self):
        self.inv["uses"][0]["quote"] = "Fabricated synthetic quotation."
        forged = self.evidence("verbatim", method="exact-text", matched=self.inv["uses"][0]["quote"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            checker.validate_entry(forged, self.inv, self.sources)


class QuoteLabelAndReachabilityTests(unittest.TestCase):
    """Fictional fixtures in tests/fixtures/cite_check; none of the texts is law."""

    OPINION = "opinions/smith-v-jones-2025-WI-999.txt"
    STATUTE = "statutes/fictional-stat-999.txt"
    IN_FORCE = "statutes/fictional-stat-998-05-in-force.txt"
    AMENDED = "statutes/fictional-stat-998-05-amended.txt"

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sources = self.root / "sources"
        shutil.copytree(FIXTURES / "archive", self.sources)  # "sources/" is git-ignored
        self.document = self.root / "draft.md"
        shutil.copyfile(FIXTURES / "draft.md", self.document)
        self.inv = {"document_sha256": checker.digest(self.document),
                    "uses": json.loads((FIXTURES / "uses.json").read_text(encoding="utf-8"))}
        self.inventory_path = self.root / "inventory.json"
        self.inventory_path.write_text(json.dumps(self.inv, ensure_ascii=False), encoding="utf-8")
        self.quotes = {use["id"]: use["quote"] for use in self.inv["uses"]}
        self.log = self.root / "evidence.jsonl"
        self.report_path = self.root / "report.md"

    def cli(self, command, *options, log=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), command, "--inventory", str(self.inventory_path),
             "--document", str(self.document), "--sources", str(self.sources),
             "--log", str(log or self.log), *options],
            capture_output=True, text=True, encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def quote(self, use, name, locator, *options, log=None):
        result = self.cli("quote", "--use", use, "--file", name, "--locator", locator, *options, log=log)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result, checker.read_log(log or self.log, self.inv, self.sources)[-1]

    def report(self, *options):
        result = self.cli("report", "--out", str(self.report_path), *options)
        self.assertIn(result.returncode, (0, 1), result.stderr)
        return self.report_path.read_text(encoding="utf-8")

    def manual(self, use, check="verbatim", result="caution", **changes):
        entry = {"document_sha256": self.inv["document_sha256"], "inventory_sha256": checker.inventory_digest(self.inv),
                 "use": use, "check": check, "result": result, "method": "manual",
                 "note": "Synthetic test attestation only; no real legal review."}
        entry.update(changes)
        return entry

    def test_verified_needs_exact_text_in_the_cited_locator(self):
        result, entry = self.quote("u5", self.OPINION, "¶13")
        self.assertEqual((entry["result"], entry["label"], entry["matched"]), ("pass", "VERIFIED", self.quotes["u5"]))
        self.assertEqual(result.stdout.strip(), "VERIFIED: exact text found; compared marked locator ¶13")
        # A finer locator resolves to the marked section that contains it.
        _, entry = self.quote("u2", self.STATUTE, "s. 999.02(1)", log=self.root / "second.jsonl")
        self.assertEqual((entry["label"], entry["compared"]), ("VERIFIED", "marked locator s. 999.02"))

    def test_altered_quote_is_flagged_with_a_word_diff(self):
        _, entry = self.quote("u1", self.OPINION, "¶12")
        self.assertEqual((entry["result"], entry["label"]), ("fail", "QUOTE_ALTERED"))
        self.assertEqual(entry["matched"], "A party who seeks relief from a default judgment must file a written notice within ten days")
        diff = "A party [-seeking-]{+who seeks+} relief from a default judgment must file {+a+} written notice within ten days [-.-]"
        self.assertEqual(entry["diff"], diff)
        text = self.report()
        self.assertIn("| FLAGGED |", text)
        self.assertIn("verbatim: fail (opinions/smith-v-jones-2025-WI-999.txt @ ¶12, text compared by the tool); "
                      "QUOTE_ALTERED: near match, wording differs; compared marked locator ¶12; "
                      "diff ([-draft only-] {+source only+}): " + diff + "; provenance not recorded", text)

    def test_quote_under_the_wrong_section_is_misattributed(self):
        _, entry = self.quote("u2", self.STATUTE, "s. 999.01")
        self.assertEqual((entry["result"], entry["label"], entry["matched"]), ("fail", "MISATTRIBUTED", ""))
        self.assertEqual([(p["file"], p["locator"]) for p in entry["found_in"]], [(self.STATUTE, "s. 999.02")])
        self.assertIn("MISATTRIBUTED: exact text not at the cited locator; compared marked locator s. 999.01; "
                      "found at statutes/fictional-stat-999.txt @ s. 999.02", self.report())
        # The place named must still hold the quotation; editing it breaks the log.
        line = json.loads(self.log.read_text(encoding="utf-8"))
        line["found_in"][0]["locator"] = "s. 999.01"
        self.log.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "found_in does not match"):
            checker.read_log(self.log, self.inv, self.sources)

    def test_version_in_force_entry_names_the_dated_text_compared(self):
        in_force = "in force 2024-07-01 through 2026-12-31 (fictional)"
        amended = "as amended by 2025 Fictional Act 999, effective 2027-01-01; not in effect on 2026-10-13 (fictional)"
        _, entry = self.quote("u3", self.IN_FORCE, "s. 998.05")
        self.assertEqual((entry["label"], entry["version_compared"]), ("MISATTRIBUTED", in_force))
        self.assertEqual(entry["found_in"][0]["file"], self.AMENDED)
        self.assertEqual(entry["found_in"][0]["version"], amended)
        text = self.report()
        self.assertIn(f"found at {self.AMENDED} @ s. 998.05 (version: {amended}); compared against version: {in_force}", text)
        # The amended text holds the quotation; the entry says which version that is. Its
        # version line says it is not in effect, so the exact match is recorded as caution.
        _, entry = self.quote("u3", self.AMENDED, "s. 998.05", log=self.root / "amended.jsonl")
        self.assertEqual((entry["result"], entry["label"], entry["version_compared"]), ("caution", "VERIFIED", amended))
        # A manual verbatim record against a dated text must name that version.
        with self.assertRaisesRegex(ValueError, "version_compared"):
            checker.validate_entry(self.manual("u3", file=self.IN_FORCE, sha256=checker.digest(self.sources / self.IN_FORCE),
                                               locator="s. 998.05"), self.inv, self.sources)
        checker.validate_entry(self.manual("u3", file=self.IN_FORCE, sha256=checker.digest(self.sources / self.IN_FORCE),
                                           locator="s. 998.05", version_compared=in_force), self.inv, self.sources)

    def test_unresolved_quote_reports_what_the_archive_search_covered(self):
        _, entry = self.quote("u4", self.STATUTE, "s. 999.01")
        self.assertEqual((entry["result"], entry["label"], entry["matched"]), ("fail", "UNRESOLVED", ""))
        self.assertEqual(entry["note"], "Searched 4 archived text source(s) outside the compared text for the exact quotation.")
        self.assertIn("UNRESOLVED: not found; compared marked locator s. 999.01; see the note for what the archive search covered",
                      self.report())

    def test_misattribution_falls_back_to_unresolved_when_nothing_else_is_searchable(self):
        # The only text source is the cited one, unmarked; the original is a PDF.
        shutil.rmtree(self.sources)
        (self.sources / "opinions").mkdir(parents=True)
        (self.sources / "opinions" / "extract.txt").write_text("FICTIONAL TEST TEXT. A notice may be late.\n", encoding="utf-8")
        (self.sources / "opinions" / "original.pdf").write_bytes(b"%PDF-1.4 synthetic placeholder\n")
        _, entry = self.quote("u2", "opinions/extract.txt", "p. 3")
        self.assertEqual((entry["label"], entry["compared"]), ("UNRESOLVED", "whole file (no locator markers)"))
        self.assertIn("Not searched (1, not UTF-8 .txt/.md): opinions/original.pdf.", entry["note"])
        self.assertIn("MISATTRIBUTED was not assessed: no other archived text could be searched.", entry["note"])

    def test_labels_cannot_be_forged_or_promoted(self):
        opinion = {"file": self.OPINION, "sha256": checker.digest(self.sources / self.OPINION), "locator": "¶12"}
        forged = self.manual("u1", result="pass", method="exact-text", label="VERIFIED", matched=self.quotes["u1"],
                             compared="marked locator ¶12", **opinion)
        with self.assertRaises(ValueError):
            checker.validate_entry(forged, self.inv, self.sources)
        for changes in ({"label": "QUOTE_ALTERED", "result": "pass", "matched": "x"}, {"label": "MISATTRIBUTED", "result": "fail"},
                        {"label": "QUOTE_ALTERED", "result": "fail", "matched": ""}, {"label": "UNRESOLVED", "result": "pass"},
                        {"label": "VERIFIED", "result": "caution"}, {"label": "UNRESOLVED", "check": "citation"},
                        {"label": "PARTLY_VERIFIED"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                checker.validate_entry(self.manual("u1", **changes), self.inv, self.sources)
        checker.validate_entry(self.manual("u1", result="unverified", label="UNRESOLVED"), self.inv, self.sources)
        # A legacy record without a label stays readable and says so.
        legacy = self.manual("u5", result="pass", method="exact-text", matched=self.quotes["u5"],
                             **dict(opinion, locator="¶13"))
        checker.validate_entry(legacy, self.inv, self.sources)
        self.assertIn("quote label not recorded", checker.report(self.inv, [legacy])[0])

    def test_remembered_verbatim_pass_is_refused(self):
        result = self.cli("quote", "--use", "u5", "--file", self.OPINION, "--locator", "¶13", "--provenance-origin", "remembered")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("verbatim pass refused: remembered text is not a source", result.stderr)
        self.assertFalse(self.log.exists())
        remembered = self.manual("u5", result="pass", file=self.OPINION, sha256=checker.digest(self.sources / self.OPINION),
                                 locator="¶13", matched=self.quotes["u5"], provenance_origin="remembered")
        with self.assertRaisesRegex(ValueError, "remembered"):
            checker.validate_entry(remembered, self.inv, self.sources)
        checker.validate_entry(dict(remembered, result="caution"), self.inv, self.sources)
        checker.validate_entry(dict(remembered, provenance_origin="user_supplied"), self.inv, self.sources)
        with self.assertRaisesRegex(ValueError, "provenance_origin"):
            checker.validate_entry(dict(remembered, provenance_origin="memory"), self.inv, self.sources)

    def test_report_shows_provenance_origin_or_its_absence(self):
        self.quote("u5", self.OPINION, "¶13", "--provenance-origin", "retrieved_this_session")
        checker.append_entry(self.log, self.manual("u5", "citation", "unverified"), self.inv, self.sources)
        text = self.report()
        self.assertIn("compared marked locator ¶13; provenance: retrieved this session;", text)
        self.assertIn("citation: unverified (no copy @ no locator); provenance not recorded;", text)

    def test_sources_reachable_block_is_per_source_and_per_authority(self):
        self.quote("u5", self.OPINION, "¶13")
        checker.append_entry(self.log, self.manual("u4", "citation", "unverified", source_status={
            "source": "Fictional annotated statutes service", "status": "unreachable",
            "reason": "Synthetic test: connector not available in this session"}), self.inv, self.sources)
        status = FIXTURES / "sources-status.json"
        text = self.report("--sources-status", str(status))
        for line in (
                "## Sources reachable",
                f"Sources-status file SHA-256: `{checker.digest(status)}`",
                "| Fictional Legislature statutes website | unreachable | Synthetic test: HTTP 503 on 2026-10-13; archived copies were used instead | u2 Fictional Stat. § 999.01; u3 Fictional Stat. § 998.05; u4 Fictional Stat. § 999.01 | sources-status file |",
                "| Fictional Supreme Court opinions website | reachable | Synthetic test: opinion retrieved 2026-10-13 | u1 Smith v. Jones, 2025 WI 999, ¶12; u5 Smith v. Jones, 2025 WI 999, ¶13 | sources-status file |",
                "| Fictional citator | not attempted | Synthetic test: no citator available in this session | u1 Smith v. Jones, 2025 WI 999, ¶12 | sources-status file |",
                "| Fictional annotated statutes service | unreachable | Synthetic test: connector not available in this session | u4 Fictional Stat. § 999.01 (citation) | evidence record |",
                "| opinions/smith-v-jones-2025-WI-999.txt | reachable | archived copy read for the recorded check; its hash matched when this report ran | u5 Smith v. Jones, 2025 WI 999, ¶13 (verbatim) | evidence records |"):
            with self.subTest(line=line):
                self.assertIn(line + "\n", text)
        self.assertNotIn("No source recorded for", text)
        self.assertNotIn("no citation", text.lower())

    def test_reachability_without_records_lists_each_authority_without_a_blanket_line(self):
        text = self.report()
        self.assertIn("No sources-status file was supplied.\n", text)
        self.assertIn("No source recorded for: u1 Smith v. Jones, 2025 WI 999, ¶12; u2 Fictional Stat. § 999.01; "
                      "u3 Fictional Stat. § 998.05; u4 Fictional Stat. § 999.01; u5 Smith v. Jones, 2025 WI 999, ¶13.\n", text)
        self.assertNotIn("no citation", text.lower())

    def test_malformed_sources_status_and_unreached_pass_are_refused(self):
        bad = self.root / "status.json"
        for rows in ([{"source": "Fictional site", "status": "reachable", "reason": "Synthetic", "uses": ["u9"]}],
                     [{"source": "Fictional site", "status": "down", "reason": "Synthetic", "uses": ["u1"]}],
                     [{"source": "Fictional site", "status": "unreachable", "reason": " ", "uses": ["u1"]}], []):
            with self.subTest(rows=rows):
                bad.write_text(json.dumps({"sources": rows}), encoding="utf-8")
                result = self.cli("report", "--out", str(self.report_path), "--sources-status", str(bad))
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse(self.report_path.exists())
        unreached = self.manual("u5", "citation", "pass", file=self.OPINION, sha256=checker.digest(self.sources / self.OPINION),
                                locator="¶13", matched="Smith v. Jones", source_status={
                                    "source": "Fictional site", "status": "unreachable", "reason": "Synthetic"})
        with self.assertRaisesRegex(ValueError, "not reached"):
            checker.validate_entry(unreached, self.inv, self.sources)

    def opinion_pass(self, use, locator, **changes):
        fields = {"result": "pass", "file": self.OPINION, "sha256": checker.digest(self.sources / self.OPINION),
                  "locator": locator, "matched": self.quotes[use], **changes}
        return self.manual(use, **fields)

    def test_manual_verbatim_pass_must_sit_under_the_cited_locator(self):
        # Reviewer attack 2b: the u5 quotation is under ¶13 only.
        entry_path = self.root / "entry.json"
        entry_path.write_text(json.dumps(self.opinion_pass("u5", "¶12"), ensure_ascii=False), encoding="utf-8")
        result = self.cli("record", "--entry", str(entry_path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("verbatim pass refused: the quotation is not in the segment marked for the cited locator '¶12'", result.stderr)
        self.assertFalse(self.log.exists())
        with self.assertRaisesRegex(ValueError, "has locator markers but none matches '¶99'"):
            checker.validate_entry(self.opinion_pass("u5", "¶99"), self.inv, self.sources)
        # A legacy exact-text record without a label gets the same locator check.
        with self.assertRaisesRegex(ValueError, "verbatim pass refused"):
            checker.validate_entry(self.opinion_pass("u5", "¶12", method="exact-text"), self.inv, self.sources)
        checker.validate_entry(self.opinion_pass("u5", "¶13"), self.inv, self.sources)
        checker.validate_entry(self.opinion_pass("u5", "¶12", result="caution", matched=""), self.inv, self.sources)

    def test_hand_edited_verbatim_pass_without_method_is_refused_by_report(self):
        # Reviewer attack 6b: a log line with no method, label VERIFIED and the wrong locator.
        line = dict(self.opinion_pass("u5", "¶12", label="VERIFIED", compared="marked locator ¶12"),
                    recorded_at="2026-10-13T12:00:00+00:00")
        line.pop("method")
        self.log.write_text(json.dumps(line, ensure_ascii=False) + "\n", encoding="utf-8")
        result = self.cli("report", "--out", str(self.report_path))
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("log line 1: verbatim pass refused", result.stderr)
        self.assertFalse(self.report_path.exists())
        # Attack 6a, for contrast: an edited exact-text line is already refused.
        self.quote("u5", self.OPINION, "¶13", log=self.root / "tool.jsonl")
        edited = json.loads((self.root / "tool.jsonl").read_text(encoding="utf-8"))
        edited["locator"] = "¶12"
        self.log.write_text(json.dumps(edited, ensure_ascii=False) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exact-text label does not match"):
            checker.read_log(self.log, self.inv, self.sources)

    def test_exact_match_in_a_version_not_in_force_is_caution(self):
        # Reviewer attack 3b: the quote command run straight against a version not yet in force.
        future = "statutes/fictional-stat-999-02-future.txt"
        version = "as amended by 2025 Fictional Act 999; not yet in force (fictional)"
        (self.sources / future).write_text(f"[version: {version}]\nFICTIONAL TEST TEXT.\n\n[locator: s. 999.02]\n"
                                           "999.02 A notice shall be delivered within 20 days after the hearing.\n", encoding="utf-8")
        result, entry = self.quote("u2", future, "s. 999.02")
        self.assertEqual((entry["result"], entry["label"], entry["version_compared"]), ("caution", "VERIFIED", version))
        self.assertIn("caution: the compared file's version line says the text is not in force or is a prior version",
                      result.stdout)
        self.assertIn("so the result is caution until a reviewer confirms which version applies", entry["note"])
        text = self.report()
        self.assertIn("| u2 | Fictional Stat. § 999.01 | Notice is due within 20 days (fictional). | UNVERIFIED |", text)
        self.assertIn(f"verbatim: caution ({future} @ s. 999.02, text compared by the tool); VERIFIED: exact text found", text)
        # Promoting that record to pass by hand breaks the log.
        line = json.loads(self.log.read_text(encoding="utf-8"))
        self.log.write_text(json.dumps(dict(line, result="pass"), ensure_ascii=False) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "exact-text label does not match"):
            checker.read_log(self.log, self.inv, self.sources)
        # A version line that does not say so keeps the pass; manual VERIFIED stays pass only.
        self.assertTrue(checker.not_in_force("text prior to 2025 Fictional Act 999 (fictional)"))
        self.assertFalse(checker.not_in_force("in force 2024-07-01 through 2026-12-31 (fictional)"))
        _, entry = self.quote("u2", self.STATUTE, "s. 999.02", log=self.root / "current.jsonl")
        self.assertEqual((entry["result"], entry["label"]), ("pass", "VERIFIED"))

    def test_reachability_says_when_the_tool_did_not_read_the_file(self):
        # Reviewer attack 4c: a manual verbatim pass against a binary file the tool never reads.
        pdf = self.sources / "opinions" / "unread.pdf"
        pdf.write_bytes(b"%PDF-1.4 synthetic placeholder\n")
        # Attack 4a, for contrast: the quote command refuses a non-text source.
        result = self.cli("quote", "--use", "u5", "--file", "opinions/unread.pdf", "--locator", "p. 1")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("quote requires a UTF-8 text source", result.stderr)
        checker.append_entry(self.log, self.manual("u5", result="pass", file="opinions/unread.pdf", sha256=checker.digest(pdf),
                                                   locator="p. 1", matched=self.quotes["u5"]), self.inv, self.sources)
        checker.append_entry(self.log, self.opinion_pass("u5", "¶13", check="citation", matched="Smith v. Jones"),
                             self.inv, self.sources)
        self.quote("u1", self.OPINION, "¶12")
        text = self.report()
        not_read = "archived file present and its hash matched when this report ran; contents not compared by the tool"
        read = "archived copy read for the recorded check; its hash matched when this report ran"
        for line in (f"| opinions/unread.pdf | reachable | {not_read} | u5 Smith v. Jones, 2025 WI 999, ¶13 (verbatim) | evidence records |",
                     f"| {self.OPINION} | reachable | {not_read} | u5 Smith v. Jones, 2025 WI 999, ¶13 (citation) | evidence records |",
                     f"| {self.OPINION} | reachable | {read} | u1 Smith v. Jones, 2025 WI 999, ¶12 (verbatim) | evidence records |",
                     "verbatim: pass (opinions/unread.pdf @ p. 1, reviewer attestation, not compared by the tool)"):
            with self.subTest(line=line):
                self.assertIn(line, text)
        self.assertNotIn(f"| opinions/unread.pdf | reachable | {read}", text)

    def test_no_check_passes_from_remembered_text(self):
        # Reviewer attack 5c; 5a and 5b (verbatim) are in test_remembered_verbatim_pass_is_refused.
        for check in ("citation", "pincite", "treatment", "proposition", "format"):
            with self.subTest(check=check):
                entry = self.opinion_pass("u5", "¶13", check=check, matched="Smith v. Jones", provenance_origin="remembered",
                                          citator="Fictional citator")
                with self.assertRaisesRegex(ValueError, f"{check} pass refused: remembered text is not a source; "
                                                        "retrieve the source, or record caution or unverified"):
                    checker.validate_entry(entry, self.inv, self.sources)
                checker.validate_entry(dict(entry, result="caution"), self.inv, self.sources)
                checker.validate_entry(dict(entry, result="unverified"), self.inv, self.sources)


if __name__ == "__main__":
    unittest.main()
