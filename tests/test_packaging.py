import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("skill_tools", ROOT / "scripts/skill_tools.py")
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class PackagingTests(unittest.TestCase):
    def test_manifest_uses_platform_independent_case_sensitive_path_order(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("SKILL.md", "LICENSE", "agents/openai.yaml", "references/example.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name, encoding="utf-8")
            entries = [line.split("  ", 1)[1] for line in tools.manifest(root).splitlines()]
            self.assertEqual(entries, ["LICENSE", "SKILL.md", "agents/openai.yaml", "references/example.md"])

    def test_packages_are_deterministic_complete_and_independently_licensed(self):
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory)/"first", Path(directory)/"second"
            tools.package(first)
            tools.package(second)
            for folder in tools.folders():
                archive_path = first / f"{folder.name}.zip"
                self.assertEqual(archive_path.read_bytes(), (second/archive_path.name).read_bytes())
                with zipfile.ZipFile(archive_path) as archive:
                    names = archive.namelist()
                    self.assertTrue(all(item.create_system == 3 for item in archive.infolist()))
                    self.assertIn(f"{folder.name}/SKILL.md", names)
                    self.assertIn(f"{folder.name}/LICENSE", names)
                    self.assertEqual(archive.read(f"{folder.name}/LEGAL_NOTICE.md"), (ROOT / "LEGAL_NOTICE.md").read_bytes())
                    self.assertIn(f"{folder.name}/MANIFEST.sha256", names)
                    self.assertTrue(all(name.startswith(folder.name+"/") for name in names))
                    self.assertFalse(any("__pycache__" in name for name in names))
                    for file in tools.files(folder):
                        self.assertEqual(archive.read(f"{folder.name}/{file.relative_to(folder).as_posix()}"),file.read_bytes())
            with self.assertRaises(FileExistsError):
                tools.package(first)

    def test_manifest_changes_when_source_bytes_change(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.md"
            source.write_text("first", encoding="utf-8")
            before = tools.manifest(root)
            source.write_text("changed", encoding="utf-8")
            self.assertNotEqual(before, tools.manifest(root))

    def test_prompt_export_is_selective_and_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"prompt.md"
            tools.export_prompt("cite-check", ["references/verification.md"], target)
            text = target.read_text(encoding="utf-8")
            self.assertIn("Included file: SKILL.md", text)
            self.assertIn((ROOT / "LEGAL_NOTICE.md").read_text(encoding="utf-8"), text)
            self.assertLess(text.index("Included file: LEGAL_NOTICE.md"), text.index("Included file: SKILL.md"))
            self.assertIn("Included file: references/verification.md", text)
            self.assertNotIn("Included file: references/sources.md", text)
            with self.assertRaises(FileExistsError):
                tools.export_prompt("cite-check", [], target)
            self.assertEqual(text, target.read_text(encoding="utf-8"))

    def test_prompt_export_retains_notice_once_when_also_requested(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "prompt.md"
            tools.export_prompt("cite-check", ["LEGAL_NOTICE.md"], target)
            self.assertEqual(target.read_text(encoding="utf-8").count("Included file: LEGAL_NOTICE.md"), 1)

    def test_missing_or_changed_notice_blocks_validation_and_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills/cite-check"
            skill.mkdir(parents=True)
            (root / "LEGAL_NOTICE.md").write_bytes((ROOT / "LEGAL_NOTICE.md").read_bytes())
            for name in ("SKILL.md", "LICENSE"):
                (skill / name).write_bytes((tools.SKILLS / "cite-check" / name).read_bytes())
            target = root / "prompt.md"
            with mock.patch.multiple(tools, ROOT=root, SKILLS=root / "skills"):
                for content in (None, b"Replaced notice\n"):
                    with self.subTest(content=content):
                        if content is not None:
                            (skill / "LEGAL_NOTICE.md").write_bytes(content)
                        (skill / "MANIFEST.sha256").write_text(tools.manifest(skill), encoding="utf-8", newline="\n")
                        self.assertTrue(any("LEGAL_NOTICE.md" in error for error in tools.validate(root / "skills")))
                        with self.assertRaisesRegex(ValueError, "LEGAL_NOTICE.md"):
                            tools.export_prompt("cite-check", [], target)
                        self.assertFalse(target.exists())

    def test_prompt_export_refuses_traversal_and_unknown_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/"prompt.md"
            for name, references in (("unknown", []), ("cite-check", ["../../README.md"]), ("cite-check", ["scripts/cite_check.py"])):
                with self.subTest(name=name, references=references), self.assertRaises(ValueError):
                    tools.export_prompt(name, references, target)
                self.assertFalse(target.exists())

    def test_named_profiles_bind_exact_files_version_and_checkout(self):
        for profile, config in json.loads(tools.PROFILES.read_text(encoding="utf-8")).items():
            with self.subTest(profile=profile):
                text, build = tools.render_prompt(None, profile=profile)
                self.assertEqual(build["skill"], config["skill"])
                self.assertEqual(build["version"], (ROOT / "VERSION").read_text(encoding="utf-8").strip())
                self.assertEqual(set(build["files"]), {"SKILL.md", "LEGAL_NOTICE.md", *config["references"]})
                for relative, digest in build["files"].items():
                    self.assertEqual(digest, hashlib.sha256((tools.SKILLS / config["skill"] / relative).read_bytes()).hexdigest())
                self.assertIn("dirty", build)
                self.assertIn("commit", build)
        with self.assertRaisesRegex(ValueError, "belongs to"):
            tools.render_prompt("cite-check", profile="formal-memo")

    def test_release_assets_are_complete_checksum_bound_and_refuse_overwrite(self):
        import build_release
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "release"
            version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
            with mock.patch.object(build_release.skill_tools, "provenance", return_value={"commit": "1" * 40, "dirty": False}):
                metadata = build_release.build(target, version)
            self.assertFalse(metadata["preview"])
            expected = {p.name + ".zip" for p in tools.folders()} | {"prompt-packs.zip", "evaluation-suite.zip", "BUILD.json", "SHA256SUMS.txt", "TESTED-COMPATIBILITY.md", "RELEASE-NOTES.md"}
            self.assertEqual({p.name for p in target.iterdir()}, expected)
            lines = (target / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), len(expected) - 1)
            for line in lines:
                digest, name = line.split("  ", 1)
                self.assertEqual(digest, hashlib.sha256((target / name).read_bytes()).hexdigest())
            with zipfile.ZipFile(target / "prompt-packs.zip") as archive:
                self.assertEqual(archive.namelist(), sorted(archive.namelist()))
                for profile in json.loads(tools.PROFILES.read_text(encoding="utf-8")):
                    self.assertIn(profile + ".md", archive.namelist())
            with self.assertRaises(FileExistsError):
                build_release.build(target, version, allow_dirty=True)

    def test_release_files_never_include_git_ignored_files(self):
        import build_release
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            try:
                subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                self.skipTest(f"git unavailable: {exc}")
            (repo / ".gitignore").write_text(".env\nwork/\n", encoding="utf-8")
            (repo / "evals" / "fixtures").mkdir(parents=True)
            (repo / "evals" / "work").mkdir()
            (repo / "evals" / "cases.json").write_text("{}", encoding="utf-8")
            (repo / "evals" / "fixtures" / "a.md").write_text("synthetic", encoding="utf-8")
            (repo / "evals" / ".env").write_text("X=1", encoding="utf-8")
            (repo / "evals" / "work" / "response.json").write_text("{}", encoding="utf-8")
            self.assertEqual(build_release.release_files(repo / "evals"), ["cases.json", "fixtures/a.md"])

    def test_release_refuses_dirty_or_unknown_provenance(self):
        import build_release
        with tempfile.TemporaryDirectory() as directory:
            for provenance in ({"commit": "1" * 40, "dirty": True}, {"commit": None, "dirty": None}):
                with self.subTest(provenance=provenance), mock.patch.object(build_release.skill_tools, "provenance", return_value=provenance):
                    with self.assertRaisesRegex(ValueError, "clean Git checkout"):
                        build_release.build(Path(directory) / "release", (ROOT / "VERSION").read_text().strip())
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_cite_check_source_behavior_copy_matches_canonical_file(self):
        canonical = ROOT / "skills/wisconsin-legal-interpretation/references/source-behavior.md"
        copy = ROOT / "skills/cite-check/references/source-behavior.md"
        self.assertEqual(copy.read_bytes(), canonical.read_bytes(),
                         "copy the interpretation skill's source-behavior.md over the cite-check copy")


if __name__ == "__main__":
    unittest.main()
