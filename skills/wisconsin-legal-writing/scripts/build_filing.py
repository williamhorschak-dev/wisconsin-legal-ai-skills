#!/usr/bin/env python3
"""
build_filing.py: build a Wisconsin circuit court DOCX for review.
Structural checks do not establish legal correctness or filing readiness.

    python build_filing.py spec.json -o "Motion.docx"
    python build_filing.py spec.json --draft -o "Template.docx"
    python build_filing.py --example > spec.json

Requires python-docx; see the skill's requirements.txt.

Geometry reproduced from the reference corpus:
  page 8.5 x 11; L/R margins 1.0"; T/B margins 0.95"
  Century Schoolbook (or Times New Roman) 12 pt body, justified, 1.5 line spacing
  court line with a right tab stop at 9360 twips (6.5")
  full-width underline rule = a single underlined TAB at that same stop
  party designation indented 2160 twips (1.5"); case number 5040 twips (3.5")
  title centered, bold, 14 pt
Appellate briefs and letters are not supported by this caption builder.
"""

import argparse
import io
import json
import math
from pathlib import Path
import re
import sys

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.shared import Inches, Pt
except ImportError:
    sys.exit("python-docx is required: python -m pip install -r <skill-dir>/requirements.txt")

RIGHT_TAB = Inches(6.5)          # 9360 twips
DESIGNATION_INDENT = Inches(1.5)  # 2160 twips
CASENO_INDENT = Inches(3.5)       # 5040 twips
SIG_INDENT = Inches(3.0)        # pro se block; holds "Electronically signed by <name>" on one line
ATTY_INDENT = Inches(2.75)      # attorney block: wider, the firm name and bar line need room
DEFAULT_FONT = "Century Schoolbook"
ALLOWED_FONTS = ("Century Schoolbook", "Times New Roman")
_font = DEFAULT_FONT

DOCTYPES = {
    "motion": "Caption, title, opening relief paragraph, numbered relief, grounds, WHEREFORE, signature.",
    "brief": "Caption, title, INTRODUCTION, BACKGROUND, ARGUMENT with point headings, CONCLUSION, signature.",
    "discovery": "Caption, title, NOW COMES paragraph, section headings, request/ANSWER pairs, signature.",
    "affidavit": "Caption, title, venue block, numbered personal-knowledge paragraphs, jurat.",
    "proposed_order": "Caption, ORDER GRANTING title, recital, IT IS ORDERED that:, ordered items. No signature block.",
    "letter": "No caption. Business letter with a Re: line. Use references/letters.md.",
    "appellate_brief": "White cover, then Rule 809.19(1)(a)-(f) sections in order. Use references/appellate.md.",
}


# ---------------------------------------------------------------- primitives

def _style_run(run, *, size=None, bold=False, underline=False, italic=False):
    run.font.name = _font
    run.font.size = Pt(size) if size else None
    run.bold = bold
    run.underline = underline
    run.italic = italic
    return run


def _para(doc, *, align=None, space_after=0, line_spacing=None,
          first_line_indent=None, left_indent=None, right_indent=None,
          right_tab=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    if align is not None:
        pf.alignment = align
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    if line_spacing:
        pf.line_spacing = line_spacing
    if first_line_indent is not None:
        pf.first_line_indent = first_line_indent
    if left_indent is not None:
        pf.left_indent = left_indent
    if right_indent is not None:
        pf.right_indent = right_indent
    if right_tab:
        pf.tab_stops.add_tab_stop(RIGHT_TAB, WD_TAB_ALIGNMENT.RIGHT)
    return p


# Emphasis markers use the standard markdown adjacency rule: an opening marker
# must be followed by a non-space, a closing marker preceded by a non-space, and
# neither may sit against a word character. That is what keeps "5 * 3 = 15" and
# the "* * *" statutory omission marker intact while still catching *State v.
# Salinas*. Use \* for a literal asterisk that would otherwise pair up.
_ESCAPE = re.compile(r"\\\*")
_BOLD = re.compile(r"(?<![\w*])\*\*(?=[^\s])(.+?)(?<=[^\s])\*\*(?![\w*])")
_ITAL = re.compile(r"(?<![\w*])\*(?=[^\s*])([^*\n]+?)(?<=[^\s*])\*(?![\w*])")
_SENTINEL = "\x00"


def _emit(p, text, *, size, bold=False, underline=False, italic=False):
    r"""Add TEXT to paragraph P, honouring inline markup.

        *case name*      italic   (Bluebook: case names, signals, id., supra)
        **text**         bold
        ***text***       bold italic (bold and italic nest in either order)
        \*               a literal asterisk

    Bluebook italics are mandatory in this default style, and this markup is the
    only way to get them into the .docx, so write body text with the case names
    already marked: "*State v. Salinas*, 2016 WI 44, ¶ 30, ...".

    There is deliberately NO underline markup. Legal text is full of underscore
    blanks (____ day of ______, (Doc. __:__)) and any underscore syntax would eat
    them. Underlining is applied by block type.

    Unpaired asterisks pass through untouched, so "* * *" for omitted statutory
    text survives, as does "5 * 3". \* forces a literal asterisk anywhere.
    """
    # Park escaped asterisks so no pattern can see them, restore at write time.
    text = _ESCAPE.sub(_SENTINEL, text)

    def write(chunk, *, b, i):
        if not chunk:
            return
        _style_run(p.add_run(chunk.replace(_SENTINEL, "*")), size=size,
                   bold=b, underline=underline, italic=i)

    def walk(chunk, b, i):
        """Split on bold, then italic, recursing so the two nest either way."""
        pos = 0
        for m in _BOLD.finditer(chunk):
            walk_italic(chunk[pos:m.start()], b, i)
            walk(m.group(1), True, i)
            pos = m.end()
        walk_italic(chunk[pos:], b, i)

    def walk_italic(chunk, b, i):
        pos = 0
        for m in _ITAL.finditer(chunk):
            write(chunk[pos:m.start()], b=b, i=i)
            write(m.group(1), b=b, i=True)
            pos = m.end()
        write(chunk[pos:], b=b, i=i)

    walk(text, bold, italic)
    return p


def _rule(doc, size):
    """Full-width underline rule: one underlined TAB to a right stop at 6.5"."""
    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, right_tab=True)
    _style_run(p.add_run("\t"), size=size, underline=True)
    return p


def _blank(doc, size):
    p = _para(doc)
    _style_run(p.add_run(""), size=size)
    return p


# ------------------------------------------------------------------ caption

def build_caption(doc, spec, size):
    court = spec.get("court", "CIRCUIT COURT")
    county = spec["county"].upper()
    if not county.endswith("COUNTY"):
        county += " COUNTY"

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, right_tab=True)
    bold = bool(spec.get("bold_court_line"))
    _style_run(p.add_run(f"STATE OF WISCONSIN{' ' * 20}{court}"), size=size, bold=bold)
    _style_run(p.add_run("\t"), size=size, bold=bold)
    _style_run(p.add_run(county), size=size, bold=bold)

    # No branch line. A branch number is docket metadata, not caption text, and
    # it is wrong often enough (reassignment, visiting judges, calendar moves)
    # that printing it adds risk without adding anything the clerk needs.
    # A "branch" key in an older spec is accepted and ignored rather than
    # erroring, so specs written before this change still build.

    _rule(doc, size)
    _blank(doc, size)

    first, second = spec["first_party"], spec["second_party"]

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    _style_run(p.add_run(first["name"].upper().rstrip(",") + ","), size=size)
    _blank(doc, size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              first_line_indent=DESIGNATION_INDENT)
    _style_run(p.add_run(first["designation"]), size=size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              first_line_indent=CASENO_INDENT)
    _style_run(p.add_run("Case No. " + spec["case_no"]), size=size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    _style_run(p.add_run("v."), size=size)
    _blank(doc, size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY)
    _style_run(p.add_run(second["name"].upper().rstrip(",") + ","), size=size)
    _blank(doc, size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
              first_line_indent=DESIGNATION_INDENT)
    _style_run(p.add_run(second["designation"]), size=size)

    _rule(doc, size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    _style_run(p.add_run(""), size=size)

    p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER)
    _emit(p, spec["title"].upper(), size=size + 2, bold=True)

    _rule(doc, size)
    _blank(doc, size)


# --------------------------------------------------------------------- body

def build_body(doc, blocks, size, spacing):
    for b in blocks:
        kind = b.get("type", "p")
        text = b.get("text", "")

        if kind == "p":
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=spacing)
            _emit(p, text, size=size)

        elif kind == "h1":                       # centered bold underlined caps
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.CENTER, line_spacing=spacing,
                      space_after=6)
            _emit(p, text.upper(), size=size, bold=True, underline=True)

        elif kind == "h2":                       # flush left bold proposition
            # Deliberately LEFT, not JUSTIFY: these headings are full sentences and
            # often wrap, and justification stretches the inter-word spacing on the
            # lines the reader looks at hardest.
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=spacing,
                      space_after=6)
            _emit(p, text, size=size, bold=True)

        elif kind == "h3":
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.LEFT, line_spacing=spacing,
                      space_after=6, left_indent=Inches(0.5))
            _emit(p, text, size=size, bold=True)

        elif kind == "num":                      # numbered relief / fact paragraph
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=spacing,
                      left_indent=Inches(0.5), first_line_indent=Inches(-0.5))
            _emit(p, text, size=size)

        elif kind == "quote":                    # block quote
            # 1.15 is the floor Rule 809.19(8)(b) sets for a proportional serif
            # brief; using it in circuit court too keeps one habit.
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=1.15,
                      left_indent=Inches(0.5), right_indent=Inches(0.5),
                      space_after=10)
            _emit(p, text, size=size - 1)

        elif kind == "answer":                   # discovery answer, tab-indented
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=spacing,
                      first_line_indent=DESIGNATION_INDENT)
            label, _, rest = text.partition(":")
            _style_run(p.add_run(label + ":"), size=size, bold=True)
            _emit(p, rest, size=size)

        elif kind == "ordered":                  # proposed order item
            p = _para(doc, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line_spacing=spacing,
                      left_indent=Inches(0.5), space_after=10)
            _emit(p, text, size=size)

        elif kind == "blank":
            _blank(doc, size)

        else:
            raise ValueError(f"unknown block type: {kind!r}")

        if kind in ("h1", "h2", "h3"):
            p.paragraph_format.keep_with_next = True
            p.paragraph_format.keep_together = True
        if kind in ("p", "h2", "h3", "num", "answer"):
            blank = _blank(doc, size)
            if kind in ("h2", "h3"):
                blank.paragraph_format.keep_with_next = True


# ---------------------------------------------------------------- signature

def _spacer(header, *, inches):
    """Put INCHES of blank vertical space in a header, to clear an area on page 1."""
    para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    para.paragraph_format.space_after = Pt(0)
    para.paragraph_format.space_before = Pt(0)
    run = para.add_run()
    run.font.size = Pt(12)
    # 12 pt single-spaced is ~1/6" per line.
    for _ in range(max(0, int(round(inches * 6)) - 1)):
        run.add_break()
    return para


def _keep_together(paragraphs):
    """Stop a signature block from splitting across a page break."""
    for p in paragraphs[:-1]:
        p.paragraph_format.keep_with_next = True
    for p in paragraphs:
        p.paragraph_format.keep_together = True


def build_signature(doc, sig, size):
    if not sig:
        return
    style = sig.get("style", "pro_se")
    start = len(doc.paragraphs)

    if style == "pro_se":
        # (text, italic). The "Electronically signed by <name>" line is ITALIC:
        # it stands in for the handwritten signature. The typed name under it is
        # roman. Both the pro se and the firm documents in the corpus do this.
        lines = []
        if sig.get("name"):
            lines.append(("Electronically signed by " + sig["name"], True))
            lines.append((sig["name"], False))
        for key in ("role", "address", "phone", "email"):
            if sig.get(key):
                lines.append((sig[key], False))

        _blank(doc, size)
        first = True
        for line, italic in lines:
            p = _para(doc, left_indent=SIG_INDENT)
            if first and sig.get("date"):
                pf = p.paragraph_format
                pf.left_indent = Inches(0)
                pf.tab_stops.add_tab_stop(SIG_INDENT, WD_TAB_ALIGNMENT.LEFT)
                _style_run(p.add_run("Dated: " + sig["date"] + "\t"), size=size)
            _style_run(p.add_run(line), size=size, italic=italic)
            first = False

    elif style == "attorney":
        # Right half of the page, same as the pro se block. The date line sits
        # flush left on the first line and tabs across to "Respectfully submitted,".
        indent = Inches(sig["indent"]) if sig.get("indent") else ATTY_INDENT

        def right(text, bold=False, first=False, italic=False):
            if first:
                date = sig.get("date") or ("Dated this ____ day of __________, "
                                           + str(sig.get("year", "20__")) + ".")
                date_paragraph = _para(doc)
                _style_run(date_paragraph.add_run(date), size=size)
            p = _para(doc)
            pf = p.paragraph_format
            pf.left_indent = indent
            _style_run(p.add_run(text), size=size, bold=bold, italic=italic)
            return p

        def gap():
            p = _para(doc)
            p.paragraph_format.left_indent = indent
            _style_run(p.add_run(""), size=size)

        _blank(doc, size)
        right("Respectfully submitted,", first=True)
        gap()
        right(sig["firm"].upper(), bold=True)
        if sig.get("dba"):
            right(sig["dba"])
        gap()
        # Italic: this line stands in for the handwritten signature.
        right("Electronically signed by " + sig["name"], italic=True)
        right(sig["name"], bold=True)
        right("State Bar No. " + sig["bar_no"])
        right(sig["for_party"])
        gap()
        for key in ("address", "city_state_zip", "phone", "email"):
            if sig.get(key):
                right(sig[key])

    else:
        raise ValueError(f"unknown signature style: {style!r}")

    _keep_together(doc.paragraphs[start:])


# --------------------------------------------------------------------- main

REQUIRED_TOP = ("county", "case_no", "title", "first_party", "second_party")


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _validate(spec, *, draft=False):
    """Validate supported structure; this is not a legal or filing certification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    for key in ("appellate", "proposed_order", "stamp_clearance", "bold_court_line", "signature_in_body"):
        if key in spec and not isinstance(spec[key], bool):
            raise ValueError(f"{key} must be true or false")
    court = spec.get("court", "CIRCUIT COURT")
    if not isinstance(court, str) or court.strip().upper() != "CIRCUIT COURT":
        raise ValueError("This builder supports CIRCUIT COURT captions only")
    spacing = spec.get("line_spacing", 1.5)
    if isinstance(spacing, bool) or not isinstance(spacing, (int, float)) or not math.isfinite(spacing) or not 1 <= spacing <= 3:
        raise ValueError("line_spacing must be a finite number between 1 and 3")
    body = spec.get("body")
    if not isinstance(body, list) or not body:
        raise ValueError("body must be a non-empty list of blocks")
    for block in body:
        if not isinstance(block, dict) or not isinstance(block.get("text", ""), str):
            raise ValueError("each body block must be an object with string text")
        if block.get("type", "p") not in {"p", "h1", "h2", "h3", "num", "quote", "answer", "ordered", "blank"}:
            raise ValueError(f"unknown block type: {block.get('type')!r}")
    if not draft and any(re.search(r"\[[^\]\n]+\]|_{2,}", value) for value in _strings(spec)):
        raise ValueError("bracketed text or blanks need review; resolve placeholders or use --draft (also for intentional legal brackets)")
    missing = [k for k in REQUIRED_TOP if not spec.get(k)]
    if missing:
        raise ValueError("spec is missing required key(s): " + ", ".join(missing))
    for key in ("county", "case_no", "title"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValueError(f"{key} must be a non-empty string")

    for side in ("first_party", "second_party"):
        p = spec.get(side) or {}
        if not isinstance(p, dict):
            raise ValueError(f"{side} must be an object")
        for k in ("name", "designation"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                raise ValueError(f"{side}.{k} must be a non-empty string")

    if spec.get("appellate"):
        raise ValueError(
            "This builder produces CIRCUIT COURT filings only.\n"
            "An appellate brief needs a white cover page, a Rule 809.81(9) dual-\n"
            "designation caption, 1.25in side margins with matching tab stops,\n"
            "pagination starting at 1 on the cover, 13pt body with 11pt block\n"
            "quotes, and the Rule 809.19(8g) certifications. This script does none\n"
            "of that, and a brief built with appellate:true would violate\n"
            "Rule 809.19(8)(b). Start from assets/10-appellate-brief.docx and see\n"
            "references/appellate.md.")

    sig = spec.get("signature")
    if spec.get("signature_in_body"):
        if spec.get("document_type") != "affidavit" or sig is not None:
            raise ValueError("signature_in_body is only supported for an affidavit with signature:null")
        return  # The affidavit spec places its affiant signature before the jurat.
    if spec.get("proposed_order"):
        if sig:
            print("note: proposed orders take no signature block; ignoring it.",
                  file=sys.stderr)
        return
    if not sig:
        raise ValueError(
            "no signature block. Pass signature:null only for a proposed order; "
            "see Wis. Stat. s. 802.05(1), including its correction provision.")
    if not isinstance(sig, dict):
        raise ValueError("signature must be an object")
    for key in ("style", "name", "role", "firm", "dba", "bar_no", "for_party", "address", "city_state_zip", "phone", "email", "date"):
        if sig.get(key) is not None and not isinstance(sig[key], str):
            raise ValueError(f"signature.{key} must be a string")

    style = sig.get("style", "pro_se")
    if style == "pro_se":
        need = ("name", "role", "address", "phone", "email")
    elif style == "attorney":
        need = ("firm", "name", "bar_no", "for_party", "address", "phone", "email")
        if not draft and not sig.get("date"):
            raise ValueError("attorney signature.date is required, or use --draft for the date placeholder")
    else:
        raise ValueError(f"unknown signature style: {style!r}")
    lack = [k for k in need if not sig.get(k)]
    if lack:
        if draft and all(key in {"address", "phone", "email"} for key in lack):
            print("warning: incomplete draft signature: " + ", ".join(lack), file=sys.stderr)
            return
        raise ValueError(
            f"{style} signature block is missing: " + ", ".join(lack)
            + ". Wis. Stat. s. 802.05(1) requires the signer's name, address, "
              "telephone number, email, and bar number if any.")


def build(spec, out_path, *, draft=False, overwrite=False):
    global _font
    _validate(spec, draft=draft)
    out_path = Path(out_path)
    if out_path.suffix.lower() != ".docx":
        raise ValueError("output must have a .docx extension")
    if out_path.is_symlink():
        raise ValueError("output must not be a symbolic link")
    if out_path.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite {out_path}; choose a new path or --overwrite")
    _font = spec.get("font", DEFAULT_FONT)
    if _font not in ALLOWED_FONTS:
        raise ValueError(
            f"font must be one of {ALLOWED_FONTS}, not {_font!r}. "
            "The default style permits Century Schoolbook or Times New Roman only.")
    proposed = bool(spec.get("proposed_order"))
    size = 12
    spacing = spec.get("line_spacing", 1.5)

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = _font
    normal.font.size = Pt(size)

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Inches(8.5), Inches(11)
    sec.left_margin = sec.right_margin = Inches(1.0)
    sec.top_margin = sec.bottom_margin = Inches(0.95)
    # Every eFiled document needs a blank 1/2" top margin on every page for the
    # court-applied header (case number, document number, filed date, pagination)
    # and a blank 2" x 2" square at the TOP RIGHT of page 1 for the file stamp.
    # Director of State Courts technical requirements; Wis. Stat. s. 801.18(8).
    #
    # The caption's court line carries a right tab at 6.5", which puts the county
    # text inside that square. Rather than break the caption geometry, page 1 gets
    # a full-width 2" clear band, which necessarily clears the top-right square and
    # is what the filed documents in the corpus actually look like once the court
    # applies its stamp. Set "stamp_clearance": false to suppress it (for a
    # document that will be filed on paper, or one the court will not stamp).
    #
    # The band is a first-page header that starts 0.5" from the top edge and is
    # taller than the top margin, so Word starts page 1 body text below it. The
    # top margin stays 0.95" so that pages 2 and later, which have no header,
    # also keep body text clear of the court's 1/2" header band. An earlier
    # version set a 0.5" top margin, which put page 2 text at 0.5".
    sec.header_distance = Inches(0.5)
    if spec.get("stamp_clearance", True) and not proposed:
        sec.different_first_page_header_footer = True
        _spacer(sec.first_page_header, inches=1.5)   # 0.5" + 1.5" = 2" clear

    if proposed:
        # A 3" blank top margin belongs on page 1 ONLY; later pages keep the
        # 0.95" margin above. Setting sec.top_margin would apply 3" to every
        # page, so the space is created with a distinct first-page header
        # instead.
        sec.different_first_page_header_footer = True
        _spacer(sec.first_page_header, inches=2.5)   # 0.5" + 2.5" = 3" clear

    build_caption(doc, spec, size)
    build_body(doc, spec.get("body", []), size, spacing)

    if not proposed:
        # Keep the conclusion and signature connected across a page break.
        if spec.get("signature"):
            for paragraph in reversed(doc.paragraphs):
                paragraph.paragraph_format.keep_with_next = True
                if paragraph.text.strip():
                    break
        build_signature(doc, spec.get("signature"), size)

    payload = io.BytesIO()
    doc.save(payload)
    with out_path.open("wb" if overwrite else "xb") as output:
        output.write(payload.getvalue())
    return out_path


EXAMPLE = {
    "county": "LA CROSSE",
    "court": "CIRCUIT COURT",
    "case_no": "2025-CV-000123",
    "font": "Century Schoolbook",
    "bold_court_line": False,
    "appellate": False,
    "proposed_order": False,
    "first_party": {"name": "JANE Q. EXAMPLE", "designation": "Plaintiff"},
    "second_party": {"name": "ACME DEBT BUYER, LLC", "designation": "Defendant"},
    "title": "Plaintiff's Motion to Compel",
    "body": [
        {"type": "p", "text": "Plaintiff Jane Q. Example, pro se, moves the Court for an Order compelling Defendant Acme Debt Buyer, LLC (“Acme”) to provide complete discovery responses and production, and for Plaintiff's reasonable expenses incurred in making this motion, pursuant to Wis. Stat. §§ 804.09 and 804.12(1)(a)–(c), with sanctions available for noncompliance under Wis. Stat. § 804.12(2)."},
        {"type": "p", "text": "Plaintiff files contemporaneously a Brief in Support and supporting exhibits identifying the specific deficiencies, the controlling legal standards, and the relief requested."},
        {"type": "h1", "text": "Argument"},
        {"type": "h2", "text": "A. Acme's “possession of third parties” objection does not answer the request, because Wis. Stat. § 804.09 reaches documents within a party's control."},
        {"type": "p", "text": "[Argument text.]"},
        {"type": "p", "text": "WHEREFORE, Plaintiff respectfully requests that the Court enter an order compelling production of the categories identified in the Brief in Support, requiring a privilege log for any withheld materials, and granting such other and further relief as the Court deems just and proper."}
    ],
    "signature": {
        "style": "pro_se",
        "date": "March 2, 2026",
        "name": "Jane Q. Example",
        "role": "Plaintiff, pro se",
        "address": "[STREET ADDRESS], [CITY], WI [ZIP]",
        "phone": "[PHONE]",
        "email": "[email@example.com]"
    }
}


def main():
    # A path or name outside the console code page must not turn finished work into a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?", help="path to the JSON spec")
    ap.add_argument("-o", "--out", help="explicit output .docx path")
    ap.add_argument("--draft", action="store_true", help="allow placeholders and incomplete contact details")
    ap.add_argument("--overwrite", action="store_true", help="explicitly replace the output document")
    ap.add_argument("--example", action="store_true",
                    help="print a worked example spec and exit")
    ap.add_argument("--doctypes", action="store_true",
                    help="list the built-in document skeletons and exit")
    args = ap.parse_args()

    if args.doctypes:
        for k, v in DOCTYPES.items():
            print(f"{k:18s} {v}")
        return
    if args.example:
        print(json.dumps(EXAMPLE, indent=2, ensure_ascii=False))
        return
    if not args.spec:
        ap.error("give a spec file, or --example / --doctypes")
    if not args.out:
        ap.error("--out is required; choose a new output .docx path")

    try:
        with open(args.spec, encoding="utf-8-sig") as fh:
            spec = json.load(fh)
        print(build(spec, args.out, draft=args.draft, overwrite=args.overwrite))
        print("Created for review; source verification and rendered layout QA remain required.", file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        ap.exit(2, f"build_filing: {exc}\n")


if __name__ == "__main__":
    main()
