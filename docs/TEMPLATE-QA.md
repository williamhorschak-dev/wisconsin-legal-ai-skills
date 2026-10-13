# Document-template review

CI rebuilds all 11 JSON-backed templates into temporary directories and compares
their visible paragraph text with the bundled documents. It checks page geometry,
ZIP integrity, and a long Unicode caption/signature fixture. All 14 supplied DOCX
files are covered by [template-review.json](template-review.json).

With one exception, the current DOCX assets are unchanged from the earlier 14-document visual review
recorded in [the assessment](ASSESSMENT-2026-09-20.md); the exception is the appendix certification in
`10-appellate-brief.docx`, a text-only edit on 2026-10-13 that was read back but not rendered. Their content hashes bind
that inherited record to these bytes. This release adds regression checks; it does
not claim a second rendered-page review or renderer-independent layout equality.

When changing a specification, builder layout, or Word asset:

1. Rebuild affected JSON templates into a new scratch directory with
   `python skills/wisconsin-legal-writing/scripts/make_templates.py --out-dir work/template-review`.
   Preserve the originals while reviewing candidates.
2. Render each affected candidate using Word or the actual deployment renderer.
   Record renderer/version, installed fonts or substitutions, and page count.
   For broad layout/font changes, inspect all 14 templates.
3. Inspect every page: clipped text, long captions, headings stranded at page ends,
   blank pages, signature and jurat order, appellate cover pagination, repeated
   headers, placeholders, and any unsupported claims of execution or review.
   A Unicode text-preservation test does not prove the renderer has the glyphs.
4. Correct defects, render again, and record the actual reviewer, date, findings,
   resolution, and reviewed candidate hash. Replace assets only after review.
5. Update `template-review.json` and skill manifests to the reviewed bytes. Run all
   tests. Do not update hashes simply to silence a failing review-record test.

This process validates presentation. Governing requirements, factual accuracy,
signatures, service, and filing remain separate checks for an actual document.
