# Releasing a reviewed version

Work through a pull request with the four `validate` jobs: Ubuntu and Windows,
each on Python 3.10 and 3.12. Branch protection requires those checks and blocks
force pushes and deletion. It does not require a second human approver for this
solo-maintainer project. Do not bypass a failing check to publish.

Before a release:

1. Update `VERSION`, all three skills' `metadata.version`, release notes, and the
   tested compatibility record, including its claims table (test count and rebuild
   row), and the heading and first paragraph of `docs/KNOWN-LIMITS.md`. The README
   repeats none of these figures. Review source-maintenance reminders and changed
   template records. Describe pending checks explicitly.
2. Refresh manifests after reviewing the changes. Run the test suite, skill/suite/
   source validators, and any required rendered-page or behavioral checks.
3. Merge after CI passes. From the clean merged checkout, build with
   `python scripts/build_release.py --out dist/release` under CPython 3.12, the
   interpreter CI uses: a build under 3.14 has identical ZIP contents but different
   compressed bytes (seen 2026-10-11 and 2026-11-08), so its assets would not match the
   CI artifacts byte for byte. `--allow-dirty` produces local previews only; do not
   publish them as a release.
4. Create a draft GitHub release tagged `v` plus `VERSION` at that exact commit.
   Attach every asset: three skill ZIPs, prompt packs, evaluation fixtures/protocol,
   release notes, compatibility record, build provenance and `SHA256SUMS.txt`.
5. Download the draft assets and compare their SHA-256 values with the local build.
   Verify `BUILD.json` identifies the merged commit and `preview` is false. Then
   publish the complete draft and verify the public downloads and tag.

CI uploads the same asset set from each matrix job for review; CI does not publish
a release or invoke paid models automatically. A dependency-graph run is not the
validation workflow. The source registry, templates, model records, and tests
measure different things; release notes must preserve that distinction.

Checksums detect byte changes but are not signatures or independent legal review.
For dependency changes, review direct and transitive packages and relevant
advisories, then exercise the affected tools and matrix. Keep Actions pinned to
reviewed commit SHAs. See [security reporting](../SECURITY.md).
