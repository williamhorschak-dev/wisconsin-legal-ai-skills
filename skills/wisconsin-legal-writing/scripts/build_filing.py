#!/usr/bin/env python3
"""
build_filing.py: build a Wisconsin circuit court DOCX for review.
Structural checks do not establish legal correctness or filing readiness.

    python build_filing.py spec.json -o "Motion.docx"
    python build_filing.py spec.json --draft -o "Template.docx"
    python build_filing.py --example > spec.json

Requires python-docx; see the skill's requirements.txt.

Without --draft, the placeholder screen reports matching string values and their
spec paths: nonempty single-line square, angle or curly brackets; two or more
underscores; whole-word TBD, TBA or TK; and whole-word runs of two or more Xs.
Words and X runs are case-insensitive. X masks ending in four visible digits are
allowed, with whitespace, periods or common dash separators between groups.
This exception affects only X detection, not other markers around a mask.
The screen deliberately does not infer missing facts, recognize other placeholder
words, match single Xs or tokens embedded in words, or validate redaction, law or
filing readiness. Empty angle/curly pairs and pairs spanning lines are not matched.
Intentional matches, including bracketed quotations and literal X runs, still need
--draft. Draft content is unchanged.

Protected-information screen. Wis. Stat. s. 801.19(1)(a) names five kinds of protected
information in a circuit court record (social security, employer or taxpayer
identification, financial account, driver license and passport numbers). For an original
document filed in circuit court, s. 801.19(2)(c)1. requires the party to omit it and, when
it is required by law or necessary to the action, to submit it separately on the protected
information form. Without --draft the builder refuses a spec whose text matches one of the
number patterns below, naming the spec path and the category; with --draft it warns.
--protected-info-reviewed builds after the user has confirmed a match is not protected
information. The screen runs before the placeholder screen, and every diagnostic this
script prints replaces the digits of a matched number with #, so a refusal never repeats
the number. The screen is a pattern match on the spec only: it does not see exhibits, does
not recognise every number format, can match numbers that are not protected information,
and is not a redaction or compliance check.

County check. The caption names the venue, s. 802.04(1). Without --draft the county must be
one of the 72 counties listed in Wis. Stat. s. 752.11(1), which also assigns each county's
judicial circuit to a court of appeals district; with --draft a placeholder county is
accepted and any other unknown county is a warning. --district COUNTY prints the district
s. 752.11(1) assigns. The check knows county names only; it does not decide proper venue
or where an appeal is heard.

Complaints and summonses are outside this builder and are refused in every mode. Wis. Stat.
s. 802.04(1) requires a complaint's caption to carry the case classification type and code
number and its title the names and addresses of all the parties, and s. 801.09(1) requires
the summons to identify the court, the trial county, the classification and the parties'
names and addresses. The builder prints the first party on each side and no classification,
which s. 802.04(1) allows only in pleadings other than the complaint. This is a limit of the
tool, recognised from the title's opening words or document_type; it is not a rule about
who may prepare a complaint.

Declarations. A spec is an unsworn declaration when document_type is "declaration", a
declaration object is present, or the title opens with Declaration. The builder then prints
the closing of the form in Wis. Stat. s. 887.015(6) itself, after the body: the sentence "I
declare under penalty of false swearing under the law of Wisconsin that the foregoing is true
and correct." and the line "Signed on the ... day of ..., ..., at ..., ....", from

    "declaration": {"use": "sworn_declaration_substitute",
                    "purpose": "in support of Plaintiff's motion to compel in this action",
                    "signed_on": "2026-11-09", "location": "Anytown",
                    "state_or_country": "Wisconsin", "body_reviewed": true}

A final build needs the full date, the city or other location, and the state or country.
use is the reviewer's statement that a law of this state requires or permits a sworn
declaration here and that the use is not one s. 887.015(4)(b) excludes; naming an excluded
use (deposition, oath_of_office, oath_before_specified_official, recorded_under_706_or_140,
oath_under_853_04) is refused in every mode. purpose names the intended current use in the
reviewer's words, so the statement is tied to one use and not copied to another.

The builder appends one supported closing. It cannot promise the body holds no other one.
body_reviewed: true is the reviewer's statement that the body contains no separate
declaration or execution closing; a final build needs it. A pattern screen backs that
statement up: a block that mentions a penalty of false swearing or perjury, opens a sentence
with "Signed on", "Executed on" or "Dated this", or has the declarant declare, certify,
swear, affirm or verify that something is true is reported as a possible closing and refused
in every mode, until the block is removed or its index is listed in not_closings, the
reviewer's statement that it is a fact and not a closing. The screen can miss other closings
and can match ordinary facts; it does not decide either.

One restriction cannot be overridden. A body block whose raw text contains the complete
generated sentence, including its final period, is refused after case folding and whitespace
normalization even if its index is listed in not_closings. This comparison does not remove
inline formatting or combine blocks. It does not guarantee that the generated document has
no duplicate closing.

Also refused in every mode: a declaration marked as a proposed order, and a declaration
title or object with another document_type. The statute asks for "substantially" its form;
supporting that one form is a limit of this tool, not a ruling that other wording fails.
Every successful declaration build says so: the form was generated from the reviewer's
stated use, date and place, and applicability, exclusion status, the body review and actual
execution were not independently verified.

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
from datetime import date
import io
import json
import math
from pathlib import Path
import re
import sys

try:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_TAB_ALIGNMENT
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
    """Put exactly INCHES of blank vertical space in a header, to clear an area on page 1.

    One empty paragraph whose line height is fixed with an exact line rule. An
    earlier version stacked line breaks in a 12 pt run, assuming 1/6 inch per line;
    the real height depends on the renderer's line metrics for the font, so Word
    drew the proposed order's 2.5 inch spacer about half an inch too tall (body text
    at 3.5 inches instead of 3) and other viewers drew it taller still. A fixed line
    height is honoured as written.
    """
    para = header.paragraphs[0] if header.paragraphs else header.add_paragraph()
    fmt = para.paragraph_format
    fmt.space_after = Pt(0)
    fmt.space_before = Pt(0)
    fmt.line_spacing = Inches(inches)
    fmt.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    run = para.add_run()
    run.font.size = Pt(12)
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

# Wis. Stat. s. 752.11(1)(a)-(d): the court of appeals districts and the counties whose
# judicial circuits each consists of. Read 2026-11-09; 72 counties.
COURT_OF_APPEALS_DISTRICTS = {
    "I": ("Milwaukee",),
    "II": ("Kenosha", "Racine", "Walworth", "Waukesha", "Washington", "Ozaukee", "Sheboygan", "Manitowoc",
           "Fond du Lac", "Green Lake", "Winnebago", "Calumet"),
    "III": ("Door", "Kewaunee", "Brown", "Oconto", "Marinette", "Forest", "Florence", "Outagamie", "Menominee",
            "Shawano", "Langlade", "Marathon", "Lincoln", "Oneida", "Vilas", "Taylor", "Price", "Iron", "Ashland",
            "Bayfield", "Sawyer", "Rusk", "Chippewa", "Eau Claire", "Trempealeau", "Buffalo", "Pepin", "Dunn",
            "Pierce", "St. Croix", "Barron", "Polk", "Burnett", "Washburn", "Douglas"),
    "IV": ("Rock", "Green", "Jefferson", "Dodge", "Dane", "Lafayette", "Iowa", "Grant", "Richland", "Crawford",
           "Sauk", "Columbia", "Marquette", "Waushara", "Waupaca", "Portage", "Wood", "Adams", "Juneau", "Jackson",
           "Clark", "Monroe", "Vernon", "La Crosse"),
}


def _county_key(name):
    key = re.sub(r"\s+county\s*$", "", name.strip(), flags=re.IGNORECASE)
    key = re.sub(r"^(?:saint|st\.?)\s+", "st ", key, flags=re.IGNORECASE)
    return re.sub(r"[\s.]+", " ", key).strip().lower()


_COUNTY_DISTRICT = {_county_key(county): (county, district)
                    for district, counties in COURT_OF_APPEALS_DISTRICTS.items() for county in counties}


def district_for(county):
    """Return (county name, district) under s. 752.11(1), or None for a name not listed there."""
    return _COUNTY_DISTRICT.get(_county_key(county)) if isinstance(county, str) else None


REQUIRED_TOP = ("county", "case_no", "title", "first_party", "second_party")
_PLACEHOLDER = re.compile(
    r"\[[^\]\n]+\]|_{2,}|<[^<>\r\n]+>|\{[^{}\r\n]+\}|"
    r"\b(?:TBD|TBA|TK)\b|(?P<x_run>\bX{2,}\b)",
    re.IGNORECASE,
)
_NUMBER_MASK = re.compile(
    r"(?<!\w)[Xx]+(?:[\s.\-\u2010-\u2015\u2212]+[Xx]+)*"
    r"[\s.\-\u2010-\u2015\u2212]*[0-9]{4}(?!\w)"
)


def _strings(value, path=""):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str) and key.isidentifier():
                child = f"{path}.{key}" if path else key
            else:
                child = f"{path}[{json.dumps(key)}]"
            yield from _strings(item, child)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, f"{path}[{index}]")


def _placeholders(spec):
    for path, value in _strings(spec):
        masks = [match.span() for match in _NUMBER_MASK.finditer(value)]
        for match in _PLACEHOLDER.finditer(value):
            if match.lastgroup == "x_run" and any(
                start <= match.start() and match.end() <= end for start, end in masks
            ):
                continue
            yield _redact(f"{path}: {json.dumps(match.group(), ensure_ascii=False)}")


# Wis. Stat. s. 801.19(1)(a): the five kinds of protected information. Each pattern's last
# group (or whole match) is the number; keyword patterns look at most 40 characters ahead
# on the same line. Dates and telephone numbers are not account or license numbers.
_PI_GAP = r"[^\n]{0,40}?"
_PI_NOT_DATE_OR_PHONE = r"(?!\d{4}-\d{2}-\d{2}(?!\d))(?!\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d))"
_PROTECTED = (
    ("social security number", re.compile(r"(?<![\w-])\d{3}-\d{2}-\d{4}(?![\w-])")),
    ("social security number", re.compile(
        r"(?:social\s+security|\bSSN\b|\bSS\s*#)" + _PI_GAP + r"(?<!\d)(\d{3}[ .-]?\d{2}[ .-]?\d{4})(?!\d)", re.IGNORECASE)),
    ("social security number", re.compile(r"(?<![\w.-])\d{3} \d{2} \d{4}(?![\w.-])")),
    ("employer or taxpayer identification number", re.compile(r"(?<![\w-])\d{2}-\d{7}(?![\w-])")),
    ("employer or taxpayer identification number", re.compile(
        r"(?:\bF?EIN\b|\bI?TIN\b|taxpayer\s+identification|employer\s+identification|\btax\s+id\b)"
        + _PI_GAP + r"(?<!\d)(\d{9})(?!\d)", re.IGNORECASE)),
    ("financial account number", re.compile(
        r"(?:account|\bacct\b|routing|\bIBAN\b|credit\s+card|debit\s+card|card\s+(?:no|number)|loan\s+(?:no|number))"
        + _PI_GAP + r"(?<!\w)" + _PI_NOT_DATE_OR_PHONE + r"((?:\d[ -]?){7,18}\d)(?!\w)", re.IGNORECASE)),
    ("financial account number", re.compile(
        r"(?i:account|\bacct\b|\bIBAN\b)" + _PI_GAP + r"(?<!\w)((?=[A-Z0-9]*\d{4})[A-Z]{2}\d{2}[A-Z0-9]{10,30})(?!\w)")),
    ("driver license number", re.compile(
        r"(?:driver'?s?\s+licen[sc]e|operator'?s?\s+licen[sc]e|\bDL\s*(?:no|number|#))"
        + _PI_GAP + r"(?<!\w)" + _PI_NOT_DATE_OR_PHONE
        + r"((?=[A-Za-z0-9-]*\d{4})[A-Za-z]?\d[A-Za-z0-9-]{5,19})(?![\w-])", re.IGNORECASE)),
    ("passport number", re.compile(
        r"passport" + _PI_GAP + r"(?<!\w)" + _PI_NOT_DATE_OR_PHONE
        + r"((?=[A-Za-z0-9]*\d{4})[A-Za-z0-9]{6,9})(?!\w)", re.IGNORECASE)),
)
_CARD = re.compile(r"(?<![\w-])(?:\d[ -]?){12,18}\d(?![\w-])")
_PROTECTED_MESSAGE = (
    "possible protected information. For an original document filed in circuit court, Wis. Stat. "
    "s. 801.19(2)(c)1. requires the party to omit protected information (a social security "
    "number, an employer or taxpayer identification number, a financial account number, a "
    "driver license number, a passport number) and, when it is required by law or necessary to "
    "the action, to submit it separately on the protected information form. Remove or mask each "
    "item below, or build with --protected-info-reviewed after confirming a match is not "
    "protected information. This is a pattern screen of the spec only; it does not review "
    "exhibits and is not a redaction check:\n")


def _redact(text):
    """Replace the digits of every protected-number match with # so no diagnostic repeats one."""
    spans = [match.span(match.lastindex or 0) for _, pattern in _PROTECTED for match in pattern.finditer(text)]
    spans += [match.span() for match in _CARD.finditer(text) if _luhn(re.sub(r"\D", "", match.group()))]
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            if chars[index].isalnum():
                chars[index] = "#"
    return "".join(chars)


def _luhn(digits):
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2:
            value = value * 2 - 9 if value > 4 else value * 2
        total += value
    return total % 10 == 0


def _protected(spec):
    """Yield 'path: category' for number patterns of s. 801.19(1)(a); never the number."""
    for path, value in _strings(spec):
        seen = set()
        hits = []
        for category, pattern in _PROTECTED:
            for match in pattern.finditer(value):
                hits.append((match.span(match.lastindex or 0), category))
        for match in _CARD.finditer(value):
            if _luhn(re.sub(r"\D", "", match.group())):
                hits.append((match.span(), "financial account number"))
        for (start, end), category in sorted(hits):
            if any(start < other_end and other_start < end for other_start, other_end in seen):
                continue
            seen.add((start, end))
            yield f"{_redact(path)}: {category} pattern ({end - start} characters, not shown)"


# Titles that open as a complaint or summons, after an optional party possessive and any
# number of qualifiers: "Complaint", "Plaintiff's Fourth Amended Complaint", "Summons and Complaint".
_TITLE_QUALIFIER = (r"(?:verified|amended|first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|\d+(?:st|nd|rd|th)|"
                    r"supplemental|class\s+action|third[- ]party|corrected|restated|proposed|consolidated)")
_COMPLAINT_TITLE = re.compile(r"^\W*(?:" + _TITLE_QUALIFIER + r"\s+)*(?:summons|complaint)\b", re.IGNORECASE)
_POSSESSIVE = re.compile(r"(?:'s|s'|\u2019s|s\u2019)$")
_DOCUMENT_WORD = re.compile(r"^(?:answer|motion|brief|response|reply|opposition|notice|order|memorandum|declaration|"
                            r"affidavit|objection|stipulation|to|in|of|for|and)$", re.IGNORECASE)


def _title_opens_as(title, pattern):
    """True when the title opens with the pattern, directly or after a party possessive."""
    if pattern.search(title):
        return True
    words = title.split()
    for index, word in enumerate(words[:6]):
        if _DOCUMENT_WORD.match(word.strip(".,:;")):
            return False
        if _POSSESSIVE.search(word.rstrip(".,:;")):
            return bool(pattern.search(" ".join(words[index + 1:])))
    return False


def _is_complaint_or_summons(spec):
    title = spec.get("title") if isinstance(spec.get("title"), str) else ""
    return spec.get("document_type") in ("complaint", "summons") or _title_opens_as(title, _COMPLAINT_TITLE)


# Unsworn declarations, Wis. Stat. s. 887.015. The builder prints the closing of the form in
# sub. (6) itself; see the module docstring for what it records and what it cannot know.
DECLARATION_SENTENCE = ("I declare under penalty of false swearing under the law of Wisconsin that the foregoing is "
                        "true and correct.")
DECLARATION_USE = "sworn_declaration_substitute"
DECLARATION_EXCLUDED_USES = {
    "deposition": "a deposition, s. 887.015(4)(b)1.",
    "oath_of_office": "an oath of office, s. 887.015(4)(b)2.",
    "oath_before_specified_official": "an oath required to be given before a specified official other than a notary "
                                      "public, s. 887.015(4)(b)3.",
    "recorded_under_706_or_140": "a declaration to be recorded pursuant to s. 706.06 or 706.25 or ch. 140, "
                                 "s. 887.015(4)(b)4.",
    "oath_under_853_04": "an oath required under s. 853.04, s. 887.015(4)(b)5.",
}
_DECLARATION_KEYS = ("use", "purpose", "signed_on", "location", "state_or_country", "body_reviewed", "not_closings")
_DECLARATION_STRINGS = ("use", "purpose", "signed_on", "location", "state_or_country")
_DECLARATION_TITLE = re.compile(r"^\W*(?:(?:" + _TITLE_QUALIFIER + r"|unsworn)\s+)*declaration\b", re.IGNORECASE)
# Wording that may be the declarant's own closing. A match is a question for the reviewer, not a finding.
_POSSIBLE_CLOSING = (
    ("mentions a penalty of false swearing or perjury",
     re.compile(r"\bpenalt(?:y|ies)\s+of\s+(?:false\s+swearing|perjury)\b", re.IGNORECASE)),
    ("opens a sentence with signing, execution or dating words",
     re.compile(r"(?:^|[.;:!?]\s+)\W*(?:signed|executed|dated)\s+(?:on|this|at)\b", re.IGNORECASE)),
    ("has the declarant declare, certify, swear, affirm or verify that something is true",
     re.compile(r"\bI\b[^.]{0,40}\b(?:declare|certify|swear|affirm|verify)\b[^.]{0,120}\b(?:true|correct|foregoing)\b",
                re.IGNORECASE)),
)
DECLARATION_NOTICE = (
    "Declaration form generated from the reviewer's stated current use ({purpose}), signing date, and place. "
    "Applicability, exclusion status, body closing review, and actual execution have not been independently verified. "
    "Recheck these statements before reuse for another purpose.")
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
           "November", "December")


def _ordinal(day):
    return f"{day}{'th' if 10 <= day % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')}"


def _declaration_blocks(spec, *, draft=False, quiet=False):
    """Closing blocks for an unsworn declaration, or None when the spec is another document."""
    title, typed, given = spec["title"], spec.get("document_type"), spec.get("declaration")
    opens = _title_opens_as(title, _DECLARATION_TITLE)
    if typed != "declaration" and given is None and not opens:
        return None
    if typed is not None and typed != "declaration":
        raise ValueError(
            "contradictory spec: " + ("the title opens as a declaration" if opens else "a declaration object is given")
            + f" but document_type is {_redact(repr(typed))}. Set document_type to \"declaration\", or change the title and "
              "remove the declaration object if this is another document.")
    if not re.search(r"\bdeclaration\b", title, re.IGNORECASE):
        raise ValueError("contradictory spec: document_type is \"declaration\" or a declaration object is given, but the "
                         "title does not say Declaration.")
    if spec.get("proposed_order") or spec.get("signature_in_body"):
        raise ValueError(
            "contradictory spec: a declaration cannot be a proposed order or carry signature_in_body. An unsworn "
            "declaration is a declaration in a signed record, Wis. Stat. s. 887.015(2)(g), and the form in s. 887.015(6) "
            "ends with the signature and printed name, which the builder prints from the signature block.")
    if not isinstance(given, dict):
        raise ValueError(
            "a declaration needs a declaration object, for example {\"use\": \"" + DECLARATION_USE + "\", \"purpose\": "
            "\"in support of Plaintiff's motion to compel in this action\", \"signed_on\": \"2026-11-09\", \"location\": "
            "\"Anytown\", \"state_or_country\": \"Wisconsin\", \"body_reviewed\": true}. The builder prints the "
            "declaration sentence and the execution line of the form in Wis. Stat. s. 887.015(6) from it; see "
            "references/circuit-court.md, section 3.")
    unknown = sorted(set(given) - set(_DECLARATION_KEYS))
    if unknown:
        raise ValueError("declaration has unknown key(s): " + ", ".join(_redact(repr(key)) for key in unknown))
    for key in _DECLARATION_STRINGS:
        if given.get(key) is not None and not isinstance(given[key], str):
            raise ValueError(f"declaration.{key} must be a string or null")
    if "body_reviewed" in given and not isinstance(given["body_reviewed"], bool):
        raise ValueError("declaration.body_reviewed must be true or false")
    listed = given.get("not_closings", [])
    if not isinstance(listed, list) or not all(isinstance(item, int) and not isinstance(item, bool) for item in listed):
        raise ValueError("declaration.not_closings must be a list of body block numbers")
    matched = {}
    generated = " ".join(DECLARATION_SENTENCE.casefold().split())
    for index, block in enumerate(spec["body"]):
        if generated in " ".join(block.get("text", "").casefold().split()):
            raise ValueError(f"body[{index}]: this block's raw text contains the complete sentence reserved for the "
                             "builder-generated closing. Remove it from the input; not_closings cannot override this "
                             "raw-text restriction.")
        reasons = [reason for reason, pattern in _POSSIBLE_CLOSING if pattern.search(block.get("text", ""))]
        if reasons:
            matched[index] = reasons
    stale = sorted(set(listed) - set(matched))
    if stale:
        raise ValueError("declaration.not_closings lists " + ", ".join(f"body[{index}]" for index in stale)
                         + ", which the closing screen does not match; remove the entry so the list stays a record of "
                           "blocks a reviewer actually looked at.")
    open_matches = sorted(set(matched) - set(listed))
    if open_matches:
        raise ValueError(
            "possible closing wording in the body:\n"
            + "\n".join(f"body[{index}] {'; '.join(matched[index])}" for index in open_matches)
            + "\nThe builder appends the declaration sentence and the execution line of the form in Wis. Stat. "
              "s. 887.015(6) itself. If a block above is the declarant's own closing, remove it. If it states a fact, add "
              "its number to declaration.not_closings. A match is a question for the reviewer, not a finding. The statute "
              "asks for substantially its form; this builder supports that one form and does not judge whether other "
              "wording conforms.")
    use = given.get("use")
    if use in DECLARATION_EXCLUDED_USES:
        raise ValueError(
            f"declaration.use is {use!r}: Wis. Stat. s. 887.015 does not apply to {DECLARATION_EXCLUDED_USES[use]}. "
            "The builder does not produce an unsworn declaration for that use; see the affidavit template if a sworn "
            "statement fits, and check what the governing law requires.")
    problems = []
    if use != DECLARATION_USE:
        problems.append(
            "declaration.use must be \"" + DECLARATION_USE + "\": the reviewer's statement that a law of this state requires "
            "or permits a sworn declaration here, s. 887.015(4)(a), and that the use is not one s. 887.015(4)(b) excludes ("
            + ", ".join(DECLARATION_EXCLUDED_USES) + "). The builder records that statement; it does not decide it")
    if not (given.get("purpose") or "").strip():
        problems.append("declaration.purpose must name the intended current use in the reviewer's words, for example "
                        "\"in support of Plaintiff's motion to compel in this action\"; the use statement is made for that "
                        "use and has to be made again for another")
    if given.get("body_reviewed") is not True:
        problems.append("declaration.body_reviewed must be true: the reviewer's statement that the body contains no "
                        "separate declaration or execution closing. The pattern screen can miss one")
    signed, raw = None, given.get("signed_on")
    if isinstance(raw, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            signed = date.fromisoformat(raw)
        except ValueError:
            signed = None
    if signed is None:
        problems.append("declaration.signed_on must be the full date of signing as YYYY-MM-DD; the form in s. 887.015(6) "
                        "states the day, the month and the year")
    place = {key: given[key].strip() if isinstance(given.get(key), str) else "" for key in ("location", "state_or_country")}
    if not place["location"]:
        problems.append("declaration.location must be the city or other location where the declarant signs")
    if not place["state_or_country"]:
        problems.append("declaration.state_or_country must be the state or country where the declarant signs; the form "
                        "in s. 887.015(6) states both the location and the state or country")
    if problems and not draft:
        raise ValueError("declaration is incomplete; resolve these or use --draft:\n" + "\n".join(problems))
    if problems and not quiet:
        print("warning: draft declaration is incomplete:\n" + "\n".join(problems), file=sys.stderr)
    when = (f"{_ordinal(signed.day)} day of {_MONTHS[signed.month - 1]}, {signed.year}" if signed
            else "____ day of __________, [YEAR]")
    return [{"type": "p", "text": DECLARATION_SENTENCE},
            {"type": "p", "text": f"Signed on the {when}, at {place['location'] or '[CITY OR OTHER LOCATION]'}, "
                                  f"{place['state_or_country'] or '[STATE OR COUNTRY]'}."}]


def _validate(spec, *, draft=False, protected_info_reviewed=False):
    """Validate supported structure; this is not a legal or filing certification."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    for key in ("appellate", "proposed_order", "stamp_clearance", "bold_court_line", "signature_in_body"):
        if key in spec and not isinstance(spec[key], bool):
            raise ValueError(f"{key} must be true or false")
    if spec.get("stamp_clearance") is False:
        # A filed declaration built with this switch off had the clerk's FILED stamp
        # printed over the county name of its caption. Every eFiled document, a
        # declaration or affidavit filed on its own included, is stamped on page 1.
        raise ValueError("stamp_clearance: false is not supported: the clerk's FILED stamp is applied at the top "
                         "right of page 1 of every eFiled document and overprints a caption that starts at the "
                         "top margin; remove the key")
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
    if not protected_info_reviewed:
        protected = list(_protected(spec))
        if protected and draft:
            print("warning: " + _PROTECTED_MESSAGE + "\n".join(protected), file=sys.stderr)
        elif protected:
            raise ValueError(_PROTECTED_MESSAGE + "\n".join(protected))
    if not draft:
        placeholders = list(_placeholders(spec))
        if placeholders:
            raise ValueError(
                "placeholder markers need review; resolve them or use --draft "
                "(also for intentional legal brackets):\n" + "\n".join(placeholders)
            )
    missing = [k for k in REQUIRED_TOP if not spec.get(k)]
    if missing:
        raise ValueError("spec is missing required key(s): " + ", ".join(missing))
    for key in ("county", "case_no", "title"):
        if not isinstance(spec[key], str) or not spec[key].strip():
            raise ValueError(f"{key} must be a non-empty string")

    if _is_complaint_or_summons(spec):
        raise ValueError(
            "this builder does not produce a complaint or a summons. Wis. Stat. s. 802.04(1) requires the complaint's "
            "caption to include the standardized case classification type and code number approved by the director of "
            "state courts, and its title to include the names and addresses of all the parties, any representative "
            "capacity, and a corporation's existence and domestic or foreign status. Section 801.09(1) requires the "
            "summons to identify the court, the trial county, the approved case classification type and code number, "
            "and the names and addresses of the parties. The builder prints the first party on each side and no "
            "classification, which s. 802.04(1) allows only in pleadings other than the complaint. Prepare the complaint "
            "and summons from the court's forms or by hand.")

    if district_for(spec["county"]) is None:
        # A placeholder county is tolerated only in a draft; a final build always needs a listed county.
        message = (f"county {_redact(repr(spec['county']))} is not one of the 72 Wisconsin counties listed in Wis. Stat. "
                   "s. 752.11(1); the caption must name the venue, s. 802.04(1). Give the county's name, for "
                   "example \"La Crosse\" or \"St. Croix\"")
        if not draft:
            raise ValueError(message + ".")
        if not re.search(r"\[[^\]\n]+\]|_{2,}", spec["county"]):
            print("warning: " + message + ".", file=sys.stderr)

    for side in ("first_party", "second_party"):
        p = spec.get(side) or {}
        if not isinstance(p, dict):
            raise ValueError(f"{side} must be an object")
        for k in ("name", "designation"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                raise ValueError(f"{side}.{k} must be a non-empty string")

    _declaration_blocks(spec, draft=draft)

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


def build(spec, out_path, *, draft=False, overwrite=False, protected_info_reviewed=False):
    global _font
    _validate(spec, draft=draft, protected_info_reviewed=protected_info_reviewed)
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
    # Measured on two circuit court filings stamped in October 2026: the header
    # text runs 0.13" to 0.32" from the top edge; the FILED block runs 0.27" to
    # 1.19" from the top and 6.7" to 8.0" from the left, inside the square and
    # over the end of a court line that starts at the 0.95" margin.
    #
    # The caption's court line carries a right tab at 6.5", which puts the county
    # text inside that square. Rather than break the caption geometry, page 1 gets
    # a full-width 2" clear band, which necessarily clears the top-right square and
    # is what the filed documents in the corpus actually look like once the court
    # applies its stamp. There is no switch to suppress it: a paper filing is
    # stamped in the same place, and an unstamped copy only gains white space.
    #
    # The band is a first-page header that starts 0.5" from the top edge and is
    # taller than the top margin, so Word starts page 1 body text below it. The
    # top margin stays 0.95" so that pages 2 and later, which have no header,
    # also keep body text clear of the court's 1/2" header band. An earlier
    # version set a 0.5" top margin, which put page 2 text at 0.5". The spacer
    # has an exact height, so the body starts at 2.0" (3.0" for a proposed
    # order) in any renderer that honours exact line spacing.
    sec.header_distance = Inches(0.5)
    sec.different_first_page_header_footer = True
    if proposed:
        # A 3" blank top margin belongs on page 1 ONLY; later pages keep the
        # 0.95" margin above. Setting sec.top_margin would apply 3" to every
        # page, so the space is created with a distinct first-page header
        # instead.
        _spacer(sec.first_page_header, inches=2.5)   # 0.5" + 2.5" = 3" clear
    else:
        _spacer(sec.first_page_header, inches=1.5)   # 0.5" + 1.5" = 2" clear

    build_caption(doc, spec, size)
    closing = _declaration_blocks(spec, draft=draft, quiet=True)
    build_body(doc, spec.get("body", []) + (closing or []), size, spacing)

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
    if closing is not None:
        purpose = (spec["declaration"].get("purpose") or "").strip() or "none stated"
        print(DECLARATION_NOTICE.format(purpose=_redact(" ".join(purpose.split()))), file=sys.stderr)
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
    ap.add_argument("--protected-info-reviewed", action="store_true",
                    help="build although the s. 801.19 number screen matched; use only after checking each match")
    ap.add_argument("--example", action="store_true",
                    help="print a worked example spec and exit")
    ap.add_argument("--doctypes", action="store_true",
                    help="list the built-in document skeletons and exit")
    ap.add_argument("--district", metavar="COUNTY",
                    help="print the court of appeals district Wis. Stat. s. 752.11(1) assigns to a county and exit")
    args = ap.parse_args()

    if args.district:
        found = district_for(args.district)
        if not found:
            ap.exit(2, f"build_filing: {args.district!r} is not one of the 72 counties listed in Wis. Stat. s. 752.11(1)\n")
        letter = {"I": "a", "II": "b", "III": "c", "IV": "d"}[found[1]]
        print(f"{found[0]} County: Court of Appeals District {found[1]}, Wis. Stat. s. 752.11(1)({letter}). "
              "This is the statutory district list, not a determination of where a particular appeal is heard.")
        return
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
        print(build(spec, args.out, draft=args.draft, overwrite=args.overwrite,
                    protected_info_reviewed=args.protected_info_reviewed))
        print("Created for review; source verification and rendered layout QA remain required.", file=sys.stderr)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        ap.exit(2, f"build_filing: {exc}\n")


if __name__ == "__main__":
    main()
