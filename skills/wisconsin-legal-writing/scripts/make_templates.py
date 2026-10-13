#!/usr/bin/env python3
"""Generate JSON-backed templates into an explicit directory."""
import argparse
import json
from pathlib import Path
import sys

from build_filing import build


def main():
    # A path or name outside the console code page must not turn finished work into a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    assets = Path(__file__).resolve().parents[1] / "assets"
    specs = sorted(assets.glob("*.json"))
    targets = [args.out_dir / f"{source.stem}.docx" for source in specs]
    for target in targets:
        if target.is_symlink() or (target.exists() and not args.overwrite):
            parser.error(f"refusing to overwrite {target}; choose a fresh directory or --overwrite")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for source, target in zip(specs, targets):
        build(json.loads(source.read_text(encoding="utf-8-sig")), target,
              draft=True, overwrite=args.overwrite)
        print(target)


if __name__ == "__main__":
    main()
