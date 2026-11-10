# Document-template review

CI rebuilds all 11 JSON-backed templates into temporary directories and compares
their visible paragraph text with the bundled documents. It checks page geometry,
ZIP integrity, and a long Unicode caption/signature fixture. All 14 supplied DOCX
files are covered by [template-review.json](template-review.json).

The three hand-built DOCX assets are covered by the earlier 14-document visual review
recorded in [the assessment](ASSESSMENT-2026-09-20.md), except the appendix certification in
`10-appellate-brief.docx`, a text-only edit on 2026-10-13 that was read back but not rendered.
The 11 JSON-backed assets were rebuilt on 2026-10-24 after a top-margin fix (0.95 in on every page);
only that margin value changed, and the rebuilt files were rendered in Word and checked page by page by an AI agent.
They were rebuilt again on 2026-11-07 after the page-1 clearance spacer changed from a stack of line
breaks to one header paragraph of exact height. Only word/header1.xml changed in each file. Word 16.0
now places page 1 body text at 2.00 in from the top edge (3.00 in for the proposed order), where the
line-break version gave 2.31 in and 3.51 in and other renderers gave more; page counts are unchanged;
the Word-exported PDF, read with PyMuPDF, agrees for the four templates exported; page 1 of the
proposed order and the motion was viewed by an AI agent. Not an attorney review.
On 2026-11-08 a second AI reviewer converted 01-motion.docx and 06-proposed-order.docx (the 2026-11-07
bytes) to PDF with LibreOffice 26.8.2.2 and measured the first glyph box with PyMuPDF at 2.034 in (motion
page 1), 0.984 in (motion page 2) and 3.034 in (proposed order page 1), Century Schoolbook embedded, no
clipping; the constant 0.034 in is the glyph box sitting below the line top that Word reports. The other
twelve templates have not been rendered outside Word. Not an attorney review.
On 2026-11-09 05-declaration.docx was rebuilt after its spec moved to the order and wording of the
Wis. Stat. s. 887.015(6) form (facts first, then the false-swearing sentence and the execution line). Only
word/document.xml changed. Word 16.0: 2 pages, unchanged, first paragraph at 2.00 in; the Word-saved PDF
gave 2.00 in on page 1 and 1.18 in on page 2, measured with PyMuPDF and again by a second AI reviewer with
Poppler; both pages viewed by both AI reviewers. In the unfilled template the execution line and signature
block fall on page 2. Not an attorney review.
Content hashes bind each record to these bytes. The Word check is not renderer-independent
layout equality, and it is not an attorney review.

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
