"""The release installer, and the commands the setup guide prints.

The guide tests use disposable downloads and project folders. Windows controls exercise Restricted
and a local checkout under RemoteSigned. Host discovery is outside these tests.

All but three of these tests start PowerShell from Python, write a ZIP and move folders. Antivirus
software that watches behavior can take that for an attack and block Python. So those tests run on
GitHub, and on a person's own machine only when WI_RUN_POWERSHELL_TESTS=1 is set. Anywhere else they are
skipped and say why. Commands are passed to PowerShell in the open, never encoded.
"""
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
ON_GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"
ASKED_FOR = ON_GITHUB or os.environ.get("WI_RUN_POWERSHELL_TESTS") == "1"
WHY_SKIPPED = "starts PowerShell: runs on GitHub, or locally with WI_RUN_POWERSHELL_TESTS=1 where PowerShell is installed"
# Looking for a program on the path starts nothing.
SHELL = (shutil.which("pwsh") or shutil.which("powershell")) if ASKED_FOR else None
WINDOWS_SHELLS = ([shell for shell in (shutil.which("powershell"), shutil.which("pwsh")) if shell]
                  if os.name == "nt" and ASKED_FOR else [])
INSTALL_STEP = "**Optional PowerShell installer.**"


def guide_block(marker):
    """The first PowerShell block under one bold heading of the guide, and under no later one."""
    text = GUIDE.read_text(encoding="utf-8")
    start = text.index(marker) + len(marker)
    match = re.compile(r"```powershell\n(.*?)\n```", re.S).search(text, start)
    assert match and "\n**" not in text[start:match.start()], marker
    return match.group(1)


def run_text(shell, text, cwd, *options, fresh=False):
    """Run command text in a PowerShell started in cwd. The text is one readable argument.

    Preserve the parent environment unless a test explicitly requests shell defaults.
    """
    env = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"} if fresh else None
    return subprocess.run([shell, "-NoProfile", "-NonInteractive", *options, "-Command", text],
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


class WhereTheseTestsRun(unittest.TestCase):
    def test_github_runs_them_and_does_not_skip_them(self):
        if not ASKED_FOR:
            self.assertIsNone(SHELL)
            self.assertEqual(WINDOWS_SHELLS, [])
        if ON_GITHUB:
            self.assertTrue(SHELL, "GitHub's machine has no PowerShell, so these tests would check nothing")
            if os.name == "nt":
                self.assertEqual(len(WINDOWS_SHELLS), 2, "both Windows PowerShell and PowerShell 7 are expected there")

    def test_no_command_is_passed_to_powershell_in_encoded_form(self):
        source = Path(__file__).read_text(encoding="utf-8")
        for hidden in ("Encoded" + "Command", "base" + "64"):
            self.assertNotIn(hidden, source)


@unittest.skipUnless(SHELL, WHY_SKIPPED)
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
            [SHELL, "-NoProfile", "-NonInteractive", *(["-ExecutionPolicy", "RemoteSigned"] if os.name == "nt" else []), "-File",
             str(SCRIPT), "-Archive", str(archive or self.zip), "-SkillsDirectory", str(self.skills)],
            capture_output=True, text=True, errors="replace", timeout=60,
        )

    def assert_nothing_installed(self):
        self.assertFalse((self.skills / "cite-check").exists())
        self.assertFalse((self.skills / "evaluation-suite").exists())
        self.assertEqual(list(self.skills.parent.glob(".wi-skill-*")), [])
        self.assertEqual(list(self.folder.rglob(".wi-skill-*")), [])
        self.assertFalse(self.skills.parent.exists())

    def test_installs_complete_selected_skill(self):
        self.skills = self.folder / "test project [local]" / ".claude" / "skills"
        self.skills.parent.parent.mkdir()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Verified cite-check.zip", result.stdout)
        target = self.skills / "cite-check"
        self.assertEqual((target / "SKILL.md").read_bytes(), b"released skill")
        self.assertEqual((target / "references/example.md").read_bytes(), b"example")
        self.assertEqual(list(self.folder.rglob(".wi-skill-*")), [])

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
                self.assert_nothing_installed()

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
                self.assertIn(name, result.stderr)
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
        write_release(self.downloads)

    def project(self, name):
        path = self.folder / name
        path.mkdir()
        return path

    def command(self):
        return (guide_block(INSTALL_STEP)
                .replace("$HOME/wisconsin-legal-ai-skills/scripts", SCRIPT.parent.as_posix())
                .replace("$HOME/Downloads/wi-release", self.downloads.as_posix()))

    def test_the_guide_uses_the_current_shell_policy(self):
        command = guide_block(INSTALL_STEP)
        self.assertTrue(command.startswith('& "'))
        self.assertNotIn("ExecutionPolicy", command)
        self.assertNotIn("Bypass", GUIDE.read_text(encoding="utf-8"))

    @unittest.skipUnless(SHELL, WHY_SKIPPED)
    def test_optional_command_installs_in_the_current_shell(self):
        shells = WINDOWS_SHELLS or [SHELL]
        options = ["-ExecutionPolicy", "RemoteSigned"] if os.name == "nt" else []
        for number, shell in enumerate(shells):
            with self.subTest(shell=shell):
                project = self.project("fresh project %d" % number)
                result = run_text(shell, self.command(), project, *options, fresh=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((project / ".claude/skills/cite-check/SKILL.md").read_bytes(), b"released skill")
        result = run_text(SHELL, self.command(), self.project("inherited project"), *options)
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(WINDOWS_SHELLS, "script policy applies on Windows only; " + WHY_SKIPPED)
    def test_optional_command_stops_under_restricted(self):
        project = self.project("restricted project")
        for shell in WINDOWS_SHELLS:
            with self.subTest(shell=shell):
                command = ("try { " + self.command() + " } catch [System.Management.Automation.PSSecurityException] "
                           "{ 'Restricted refused the script'; exit 1 }")
                result = run_text(shell, command, project, "-ExecutionPolicy", "Restricted", fresh=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Restricted refused the script", result.stdout)
                self.assertFalse((project / ".claude").exists())

    @unittest.skipUnless(WINDOWS_SHELLS, "Windows by-hand move; " + WHY_SKIPPED)
    def test_pasted_move_under_restricted_preserves_a_personal_edit(self):
        project = self.project("manual project")
        unpacked = self.downloads / "wi-unpacked"
        command = guide_block("**By hand.**").replace("$HOME/Downloads/wi-release", self.downloads.as_posix())
        for shell in WINDOWS_SHELLS:
            with self.subTest(shell=shell):
                with zipfile.ZipFile(self.downloads / "cite-check.zip") as archive:
                    archive.extractall(unpacked)
                target = project / ".claude/skills/cite-check/SKILL.md"
                first = run_text(shell, command, project, "-ExecutionPolicy", "Restricted", fresh=True)
                self.assertEqual(first.returncode, 0, first.stderr)
                self.assertEqual(target.read_bytes(), b"released skill")
                target.write_bytes(b"personal edit")
                with zipfile.ZipFile(self.downloads / "cite-check.zip") as archive:
                    archive.extractall(unpacked)
                repeat = run_text(shell, command, project, "-ExecutionPolicy", "Restricted", fresh=True)
                self.assertNotEqual(repeat.returncode, 0)
                self.assertEqual(target.read_bytes(), b"personal edit")
                project = self.project("another " + Path(shell).stem)


@unittest.skipUnless(SHELL, WHY_SKIPPED)
class GuidePastedChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)

    def test_partial_download_checks_and_mismatch(self):
        (self.folder / "good.zip").write_bytes(b"as published")
        (self.folder / "bad.zip").write_bytes(b"damaged on the way")
        rows = ["%s  absent.zip" % hashlib.sha256(b"not downloaded").hexdigest(),
                "%s  good.zip" % hashlib.sha256(b"as published").hexdigest().upper(),
                "%s  bad.zip" % hashlib.sha256(b"as published").hexdigest()]
        manifest = self.folder / "SHA256SUMS.txt"
        manifest.write_text("\n".join(rows[:2]) + "\n", encoding="ascii")
        block = guide_block("**Other downloads.**")
        result = run_text(SHELL, block, self.folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["SKIPPED  absent.zip", "OK  good.zip"])

        manifest.write_text("\n".join(rows) + "\n", encoding="ascii")
        result = run_text(SHELL, block, self.folder)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MISMATCH", result.stderr)

    def test_download_check_refuses_an_unusable_list(self):
        manifest = self.folder / "SHA256SUMS.txt"
        block = guide_block("**Other downloads.**")
        absent = "0" * 64 + "  absent.zip\n"
        for content in (None, "", absent, absent * 2, "bad checksum\n"):
            with self.subTest(content=content):
                if content is not None:
                    manifest.write_text(content, encoding="ascii")
                result = run_text(SHELL, block, self.folder)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("OK  ", result.stdout)

    @unittest.skipUnless(WINDOWS_SHELLS, "Windows PowerShell path handling; " + WHY_SKIPPED)
    def test_pasted_checks_in_a_project_with_brackets(self):
        folder = self.folder / "Workshop [65]"
        folder.mkdir()
        archive, row = write_release(folder)
        (folder / "MANIFEST.sha256").write_text(row, encoding="ascii")
        cd = "Set-Location -LiteralPath '" + str(folder).replace("'", "''") + "'\n"
        for heading, expected in (("**Other downloads.**", "OK  " + archive.name),
                                  ("**4. Check an installed copy.**", "Verified 1 listed files.")):
            result = run_text(WINDOWS_SHELLS[0], cd + guide_block(heading), self.folder,
                              "-ExecutionPolicy", "Restricted", fresh=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(expected, result.stdout)

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
