"""The release installer, and the commands the setup guide prints.

The installer tests start the script with a one-run policy override, on any system that has PowerShell.
The guide tests take the commands out of docs/SETUP.md and run them as printed. On Windows the install
command is run from a PowerShell that refuses script files, which is how a computer with no script policy
behaves. Nothing here shows that a host finds or starts an installed skill.
"""
import base64
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_release_skill.ps1"
GUIDE = ROOT / "docs" / "SETUP.md"
SHELL = shutil.which("pwsh") or shutil.which("powershell")
WINDOWS_SHELLS = [shell for shell in (shutil.which("powershell"), shutil.which("pwsh")) if shell] if os.name == "nt" else []
INSTALL_STEP = "**3. Verify and install the ZIP.**"
INSTALL_COMMAND = ('powershell -ExecutionPolicy Bypass -File "$HOME/Downloads/install_release_skill.ps1" '
                   '-Archive "$HOME/Downloads/cite-check.zip" -SkillsDirectory ".claude/skills"')


def guide_block(marker):
    """The first PowerShell block under one bold heading of the guide, and under no later one."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(marker) + len(marker)
    match = re.compile(r"```powershell\n(.*?)\n```", re.S).search(text, start)
    assert match and "\n**" not in text[start:match.start()], marker
    return match.group(1)


def run_text(shell, text, cwd, *options):
    """Run command text as if it were typed into a newly opened PowerShell window in cwd.

    A window a reader opens works out its own module path. A test process started from PowerShell 7 hands
    down PowerShell 7's, and Windows PowerShell given that path cannot load its own commands, Get-FileHash
    among them. So the inherited module path is left out, as it would be in a new window.
    """
    encoded = base64.b64encode(text.encode("utf-16-le")).decode("ascii")
    env = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    return subprocess.run([shell, "-NoProfile", "-NonInteractive", *options, "-EncodedCommand", encoded],
                          cwd=cwd, env=env, capture_output=True, text=True, errors="replace", timeout=120)


def write_release(folder, name="cite-check.zip", members=None):
    """An invented one-skill release in folder: the ZIP and a checksum list with its one row."""
    path = folder / name
    with zipfile.ZipFile(path, "w") as archive:
        for member, body in (members or {"cite-check/SKILL.md": "released skill",
                                         "cite-check/references/example.md": "example"}).items():
            archive.writestr(member, body)
    row = f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {name}\n"
    (folder / "SHA256SUMS.txt").write_text(row, encoding="ascii")
    return path, row


@unittest.skipUnless(SHELL, "PowerShell is required to exercise the installer")
class ReleaseInstallTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.skills = self.folder / "test project" / ".claude" / "skills"
        self.zip, self.row = write_release(self.folder)
        self.manifest = self.folder / "SHA256SUMS.txt"

    def install(self, archive=None):
        return subprocess.run(
            [SHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File",
             str(SCRIPT), "-Archive", str(archive or self.zip), "-SkillsDirectory", str(self.skills)],
            capture_output=True, text=True, errors="replace", timeout=60,
        )

    def assert_nothing_installed(self):
        self.assertFalse((self.skills / "cite-check").exists())
        self.assertFalse((self.skills / "evaluation-suite").exists())
        self.assertEqual(list(self.skills.parent.glob(".wi-skill-*")), [])

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

    def test_missing_checksum_list_refused(self):
        self.manifest.unlink()
        self.assertNotEqual(self.install().returncode, 0)
        self.assertFalse(self.skills.exists())

    def test_a_zip_with_any_other_name_is_refused_though_its_checksum_is_listed(self):
        for name, top in (("evaluation-suite.zip", "evaluation-suite"), ("cite-check (1).zip", "cite-check")):
            with self.subTest(name=name):
                archive, _ = write_release(self.folder, name, {top + "/SKILL.md": "released skill"})
                result = self.install(archive)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Choose one of the three individual skill ZIPs", result.stderr)
                self.assert_nothing_installed()

    def test_a_zip_without_the_skill_file_is_refused_though_its_checksum_is_right(self):
        write_release(self.folder, members={"cite-check/README.md": "no skill file"})
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Missing cite-check/SKILL.md", result.stderr)
        self.assert_nothing_installed()


class GuideInstallCommand(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.downloads = self.folder / "My Downloads"
        self.downloads.mkdir()
        shutil.copy(SCRIPT, self.downloads / SCRIPT.name)
        write_release(self.downloads)

    def project(self, name):
        path = self.folder / name
        path.mkdir()
        return path

    def test_the_guide_prints_the_form_that_allows_one_run(self):
        self.assertEqual(guide_block(INSTALL_STEP), INSTALL_COMMAND)

    @unittest.skipUnless(WINDOWS_SHELLS, "the printed command starts Windows PowerShell")
    def test_the_printed_command_installs_where_script_files_are_refused(self):
        command = guide_block(INSTALL_STEP).replace("$HOME/Downloads", self.downloads.as_posix())
        self.assertNotIn("$HOME", command)
        for number, shell in enumerate(WINDOWS_SHELLS):
            with self.subTest(shell=Path(shell).name):
                project = self.project("test project %d" % number)
                result = run_text(shell, command, project, "-ExecutionPolicy", "Restricted")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("Verified cite-check.zip", result.stdout)
                target = project / ".claude" / "skills" / "cite-check"
                self.assertEqual((target / "SKILL.md").read_bytes(), b"released skill")

    @unittest.skipUnless(WINDOWS_SHELLS, "script policy applies on Windows only")
    def test_calling_the_script_directly_is_refused_there(self):
        # The control. If this stops failing, the policy is not being applied and the test above shows nothing.
        command = '& "%s/install_release_skill.ps1" -Archive "%s/cite-check.zip" -SkillsDirectory ".claude/skills"' % (
            self.downloads.as_posix(), self.downloads.as_posix())
        project = self.project("test project")
        result = run_text(WINDOWS_SHELLS[0], command, project, "-ExecutionPolicy", "Restricted")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("UnauthorizedAccess", result.stderr)
        self.assertFalse((project / ".claude").exists())


@unittest.skipUnless(SHELL, "PowerShell is required to run the guide's pasted commands")
class GuidePastedChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

    def test_the_check_of_other_downloads_reports_each_file_that_is_present(self):
        (self.folder / "good.zip").write_bytes(b"as published")
        (self.folder / "bad.zip").write_bytes(b"damaged on the way")
        rows = ["%s  good.zip" % hashlib.sha256(b"as published").hexdigest(),
                "%s  bad.zip" % hashlib.sha256(b"what was published").hexdigest(),
                "%s  absent.zip" % hashlib.sha256(b"not downloaded").hexdigest()]
        (self.folder / "SHA256SUMS.txt").write_text("\n".join(rows) + "\n", encoding="ascii")
        result = run_text(SHELL, guide_block("**Other downloads.**"), self.folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split("\n")[:3], ["OK  good.zip", "MISMATCH  bad.zip", ""])

    def test_the_check_of_an_installed_copy_passes_only_when_every_listed_file_matches(self):
        skill = self.folder / "cite-check"
        (skill / "references").mkdir(parents=True)
        files = {"SKILL.md": b"released skill", "references/example.md": b"example"}
        for name, body in files.items():
            (skill / name).write_bytes(body)
        manifest = skill / "MANIFEST.sha256"
        manifest.write_text("".join("%s  %s\n" % (hashlib.sha256(body).hexdigest(), name)
                                    for name, body in files.items()), encoding="ascii")
        block = guide_block("**4. Check an installed copy.**")
        result = run_text(SHELL, block, skill)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified 2 listed files.", result.stdout)

        (skill / "references" / "example.md").write_bytes(b"personal edit")
        result = run_text(SHELL, block, skill)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Verified", result.stdout)

        (skill / "references" / "example.md").write_bytes(b"example")
        manifest.write_text("", encoding="ascii")
        result = run_text(SHELL, block, skill)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Verified", result.stdout)
