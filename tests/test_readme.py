"""The README stays short, its links resolve, and its example is what the builder actually produces."""
import contextlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest

from docx import Document

from test_builder import builder

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EXAMPLES = ROOT / "docs" / "examples"
LINK = re.compile(r"\]\(([^)\s]+)\)|(?:src|href)=\"([^\"]+)\"")


def local_links(path):
    for match in LINK.finditer(path.read_text(encoding="utf-8")):
        target = (match.group(1) or match.group(2)).split("#")[0]
        if target and not target.startswith(("http://", "https://", "mailto:")):
            yield target


class ReadmeTests(unittest.TestCase):
    def test_readme_is_short_and_keeps_its_notices(self):
        text = " ".join(README.read_text(encoding="utf-8").split())
        self.assertLessEqual(len(text.split()), 1300, "the README is the short version; move detail into docs/ and link it")
        for phrase in ("is **not a licensed attorney**", "No attorney has reviewed any of it",
                       "recorded model runs are few and exploratory", "LEGAL_NOTICE.md",
                       "Every name, date and fact in it is invented, and it states no law",
                       "Not established as correct or current"):
            self.assertIn(phrase, text)

    def test_local_links_in_the_readme_and_the_documents_it_points_to_resolve(self):
        for document in (README, ROOT / "docs/SETUP.md", ROOT / "docs/KNOWN-LIMITS.md", ROOT / "docs/TESTED-COMPATIBILITY.md",
                         ROOT / "CONTRIBUTING.md"):
            for target in local_links(document):
                with self.subTest(document=document.name, link=target):
                    self.assertTrue((document.parent / target).exists(), f"{document.name} links to {target}, which does not exist")

    def test_the_example_is_synthetic_and_is_what_the_builder_produces(self):
        spec = json.loads((EXAMPLES / "example-motion.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["case_no"], "2025CV000123")
        self.assertIn("Every name, date and fact in this document is invented", spec["body"][0]["text"])
        self.assertTrue(spec["signature"]["email"].endswith("@example.invalid"))
        self.assertEqual(spec["signature"]["address"], "123 Main Street, Anytown, WI 54000")
        with tempfile.TemporaryDirectory() as folder:
            rebuilt = Path(folder) / "example-motion.docx"
            with contextlib.redirect_stderr(io.StringIO()) as notices:
                builder.build(spec, rebuilt)
            self.assertIn("This is not a check of statutory compliance", notices.getvalue())
            built = [paragraph.text for paragraph in Document(rebuilt).paragraphs]
        committed = [paragraph.text for paragraph in Document(EXAMPLES / "example-motion.docx").paragraphs]
        self.assertEqual(built, committed)
        for page in ("example-motion-page1.png", "example-motion-page2.png"):
            data = (EXAMPLES / page).read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertLess(len(data), 400_000)


if __name__ == "__main__":
    unittest.main()
