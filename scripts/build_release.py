#!/usr/bin/env python3
"""Build complete, checksum-addressed release assets from a reviewed checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

import skill_tools

ROOT = Path(__file__).resolve().parents[1]


def zip_folder(folder, destination):
    with zipfile.ZipFile(destination, "x") as archive:
        for path in sorted(folder.rglob("*"), key=lambda item: item.relative_to(folder).as_posix()):
            if path.is_symlink():
                raise ValueError(f"symlinks are not packaged: {path}")
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(folder).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def release_files(folder):
    """Relative paths to ship from folder: tracked files and untracked files that are
    not ignored. Git-ignored files (local .env, work/ output) are never shipped.
    Returns None when Git cannot answer, so the caller can decide."""
    try:
        listing = subprocess.check_output(
            ["git", "-c", f"safe.directory={ROOT.as_posix()}", "-C", str(folder), "ls-files", "-z",
             "--cached", "--others", "--exclude-standard"], stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError):
        return None
    names = (name for name in listing.decode("utf-8").split("\0") if name)
    return sorted(name for name in names if (Path(folder) / name).is_file())


def build(destination, version, allow_dirty=False):
    if not re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.\d+", version):
        raise ValueError("use the skill version YYYY.MM.DD.N")
    errors = skill_tools.validate()
    if errors:
        raise ValueError("\n".join(errors))
    build_info = skill_tools.provenance()
    if not allow_dirty and (build_info["dirty"] is not False or not build_info["commit"]):
        raise ValueError("releases require a clean Git checkout; --allow-dirty is for local previews only")
    for folder in skill_tools.folders():
        if f'  version: "{version}"' not in (folder / "SKILL.md").read_text(encoding="utf-8"):
            raise ValueError(f"version mismatch: {folder.name}")
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(f"choose a new output directory: {destination}")
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        assets = temporary / "release"
        skill_tools.package(assets)
        prompts = temporary / "prompts"
        prompts.mkdir()
        for profile in sorted(json.loads(skill_tools.PROFILES.read_text(encoding="utf-8"))):
            skill_tools.export_prompt(None, [], prompts / f"{profile}.md", profile)
        for path in (ROOT / "LEGAL_NOTICE.md", ROOT / "LICENSE", ROOT / "docs/PORTABILITY.md"):
            shutil.copyfile(path, prompts / path.name)
        zip_folder(prompts, assets / "prompt-packs.zip")
        # Keep the evaluation protocol/cases portable without publishing private runs.
        evaluation = temporary / "evaluation-suite"
        shipped = release_files(ROOT / "evals")
        if shipped is None:
            # Without Git, only a local preview is possible (releases need a clean Git checkout above).
            shutil.copytree(ROOT / "evals", evaluation, symlinks=True)
        else:
            evaluation.mkdir()
            for name in shipped:
                (evaluation / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / "evals" / name, evaluation / name, follow_symlinks=False)
        for name in ("LICENSE", "LEGAL_NOTICE.md"):
            shutil.copyfile(ROOT / name, evaluation / name)
        zip_folder(evaluation, assets / "evaluation-suite.zip")
        for name in ("TESTED-COMPATIBILITY.md", "RELEASE-NOTES.md"):
            shutil.copyfile(ROOT / "docs" / name, assets / name)
        metadata = {"version": version, **build_info,
                    "preview": bool(allow_dirty), "evaluation_claim": "See TESTED-COMPATIBILITY.md; packaging does not establish model performance."}
        (assets / "BUILD.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8", newline="\n")
        checksums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(assets.iterdir(), key=lambda item: item.name))
        (assets / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8", newline="\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(assets, destination)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--version", default=(ROOT / "VERSION").read_text(encoding="utf-8").strip())
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.out, args.version, args.allow_dirty), indent=2))
    except (OSError, ValueError) as exc:
        print(f"build_release: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
