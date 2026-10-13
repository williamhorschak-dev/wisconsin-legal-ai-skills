"""Check evidence integrity and honest reporting with synthetic text, never law."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = (Path(__file__).resolve().parents[1] / "skills" /
          "cite-check" / "scripts" / "cite_check.py")
MODULE_SPEC = importlib.util.spec_from_file_location("citation_checker_test", SCRIPT)
checker = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(checker)


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
        self.assertIn("reviewer attestation, not compared by the tool", self.report_path.read_text(encoding="utf-8"))
        second = self.root / "second.jsonl"
        checker.append_entry(second, self.evidence("verbatim", method="exact-text", matched=self.inv["uses"][0]["quote"]), self.inv, self.sources)
        text, _ = checker.report(self.inv, checker.read_log(second, self.inv, self.sources))
        self.assertIn("text compared by the tool", text)

    def test_source_paths_cannot_escape_archive_or_use_windows_devices(self):
        outside = self.root / "outside.txt"
        outside.write_text("Outside archive", encoding="utf-8")
        for name in ("../outside.txt", str(outside), "C:/outside.txt", "C:outside.txt", "sources\\test.txt", "CON", "NUL.txt", "source.txt:stream"):
            with self.subTest(name=name):
                with self.assertRaises((ValueError, OSError)):
                    checker.source_path(self.sources, name)
        self.assertEqual(checker.source_path(self.sources, self.source.name), self.source.resolve())

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


if __name__ == "__main__":
    unittest.main()
