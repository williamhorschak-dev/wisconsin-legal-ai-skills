"""Exercise the same installer command that the setup guide gives a reader."""
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "install_release_skill.ps1"
SHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(SHELL, "PowerShell is required to exercise the installer")
class ReleaseInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.skills = self.folder / "test project" / ".claude" / "skills"
        self.zip = self.folder / "cite-check.zip"
        with zipfile.ZipFile(self.zip, "w") as archive:
            archive.writestr("cite-check/SKILL.md", "released skill")
            archive.writestr("cite-check/references/example.md", "example")
        digest = hashlib.sha256(self.zip.read_bytes()).hexdigest()
        self.row = f"{digest}  {self.zip.name}\n"
        self.manifest = self.folder / "SHA256SUMS.txt"
        self.manifest.write_text(self.row, encoding="ascii")

    def install(self):
        return subprocess.run(
            [SHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
             str(SCRIPT), "-Archive", str(self.zip), "-SkillsDirectory", str(self.skills)],
            capture_output=True, text=True, errors="replace", timeout=60,
        )

    def test_installs_complete_selected_skill(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified cite-check.zip", result.stdout)
        target = self.skills / "cite-check"
        self.assertEqual((target / "SKILL.md").read_bytes(), b"released skill")
        self.assertEqual((target / "references/example.md").read_bytes(), b"example")
        self.assertEqual(list(self.skills.parent.glob(".wi-skill-*")), [])

    def test_existing_skill_remains_byte_for_byte_intact(self):
        target = self.skills / "cite-check"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_bytes(b"personal edit")
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Already installed", result.stderr)
        self.assertEqual(list(target.iterdir()), [target / "SKILL.md"])
        self.assertEqual((target / "SKILL.md").read_bytes(), b"personal edit")

    def test_missing_zip_refused(self):
        self.zip.unlink()
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.skills.exists())

    def test_missing_duplicate_and_incorrect_checksums_refused(self):
        for record in (self.row.replace("cite-check.zip", "other.zip"), self.row * 2,
                       "0" * 64 + "  cite-check.zip\n"):
            with self.subTest(record=record):
                self.manifest.write_text(record, encoding="ascii")
                self.assertNotEqual(self.install().returncode, 0)
                self.assertFalse((self.skills / "cite-check").exists())
                self.assertEqual(list(self.skills.parent.glob(".wi-skill-*")), [])
