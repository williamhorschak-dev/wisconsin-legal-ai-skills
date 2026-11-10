# Templates

Each `NN-name.json` is a spec for `scripts/build_filing.py`; each `NN-name.docx` is
the rendered starting document. `09-letter-to-court`, `10-appellate-brief`, and `13-memorandum` have
no JSON spec: a letter takes no caption and an appellate brief needs a cover page,
and the memo has its own layout. These three are maintained directly in Word/OOXML.
For JSON-backed templates, edit the spec and build into a new directory with
`python scripts/make_templates.py --out-dir <scratch-directory>`, then render and review
before replacing bundled assets. Existing outputs need an explicit `--overwrite`.

| File | Use |
|---|---|
| `01-motion` | Circuit court motion. Short, the argument goes in the brief. |
| `02-brief` | Brief in support. INTRODUCTION → BACKGROUND → ARGUMENT → CONCLUSION. |
| `03-brief-in-opposition` | Brief opposing another party's motion. |
| `04-discovery-response` | Interrogatories, RFPs, RFAs, with the default objection formula. |
| `05-declaration` | **Default.** Wis. Stat. § 887.015 unsworn declaration. No notary. The builder prints the closing sentence and execution line from the `declaration` object. |
| `05b-affidavit` | Ordinary notarized affidavit when required or chosen; not a substitute for specialized excluded instruments. |
| `06-proposed-order` | .docx, 3″ top margin, no judicial signature block. |
| `07-motion-to-enlarge-time` | § 801.15(2)(a): pick the right tier in the first sentence. |
| `08-motion-for-reconsideration` | Branches on final vs non-final. NOT § 805.17(3) unless it follows a court trial. |
| `09-letter-to-court` | No caption. Business letter with a `Re:` line. |
| `10-appellate-brief` | Rule 809.19 cover and section skeleton, 13 pt / 1.25″ margins. |
| `13-memorandum` | Objective memo to a supervising attorney. Hand-built; edit in Word. No caption. |
| `12-motion-to-compel` | Per-request structure, conferral paragraph, § 804.12(1)(b) framing. |
| `11-motion-attorney-signed` | Firm-signed motion with the right-side attorney block. Use only when an attorney is signing. |

All templates set `"font": "Century Schoolbook"`. The only permitted alternate is
`"Times New Roman"`; the builder rejects anything else.

Most examples show a pro se signer; `11` demonstrates an attorney block, `06` has no
party signature, and `05b` places the affiant signature before its jurat. These are
examples, not assumptions about the user. Use the actual signer and role; see
`references/signature-blocks.md`. The builder supports that affidavit layout through
`document_type: "affidavit"`, `signature_in_body: true`, and `signature: null`.

All 14 files are starting templates with visible placeholders. Resolve every applicable
placeholder, verify current requirements, and inspect the rendered final document.
