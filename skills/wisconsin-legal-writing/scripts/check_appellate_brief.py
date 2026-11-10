#!/usr/bin/env python3
"""Measure a Court of Appeals brief (.docx) against the form and length rules of Wis. Stat. s. 809.19(8).

    python check_appellate_brief.py brief.docx --kind appellant
    python check_appellate_brief.py reply.docx --kind reply

Kinds: appellant, respondent (s. 809.19(8)(c)1.: the portions referred to in s. 809.19(1)(d),
(e) and (f), 11,000 words), reply (s. 809.19(8)(c)2.) and nonparty (s. 809.19(8)(c)3.): the
portions referred to in s. 809.19(1)(e) and (f), 3,000 words. What is checked, for a brief
in a proportional serif font:

  page size 8.5 by 11 inches                                   s. 809.19(8)(b)2.
  body text at least 13 point; block quotes at least 11 point  s. 809.19(8)(b)3.c.
  body line spacing between 1.15 and 1.5                       s. 809.19(8)(b)3.c.
  side margins at least 1.25 inch, top and bottom at least 1   s. 809.19(8)(b)3.e.
  a centered page number in every footer, starting at 1        s. 809.19(8)(bm)
  words in the counted portions                                s. 809.19(8)(c)

Exit 0 when nothing measured departs from those rules, 1 when something does or cannot be
verified, 2 for a file or usage error. It reads the DOCX, not the rendered or filed PDF.
It does not tell a proportional serif font from another font, does not see text inside
images, counts footnote words toward the limit without knowing where they fall, and finds
the counted portions by their headings (STATEMENT OF THE CASE, ARGUMENT, CONCLUSION). Under
s. 809.19(8g)(a)2. the certified count may be the one a commercial word processor reports
and must include words in images; this tool's count is a cross-check, and the
certification is the filer's. Passing here is not compliance and not filing readiness.
Requires python-docx.
"""
import argparse
from pathlib import Path
import re
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wi_values  # noqa: E402

try:
    from docx import Document
except ImportError:
    sys.exit("python-docx is required: python -m pip install -r <skill-dir>/requirements.txt")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
KINDS = {
    "appellant": ("appellate_brief_words", ("statement", "argument")),
    "respondent": ("appellate_brief_words", ("statement", "argument")),
    "reply": ("appellate_reply_brief_words", ("argument",)),
    "nonparty": ("appellate_nonparty_brief_words", ("argument",)),
}
HEADINGS = {
    "statement": re.compile(r"^\W*STATEMENT\s+OF\s+(?:THE\s+)?CASE\b", re.IGNORECASE),
    "argument": re.compile(r"^\W*ARGUMENT\W*$", re.IGNORECASE),
    "conclusion": re.compile(r"^\W*CONCLUSION\W*$", re.IGNORECASE),
}
END_OF_CONCLUSION = re.compile(
    r"^\W*(?:Dated\b|Respectfully\s+submitted|Electronically\s+signed\s+by|Signed\b|CERTIFICATION\b|"
    r"FORM\s+AND\s+LENGTH|CERTIFICATE\b|\[CERTIFICATION)", re.IGNORECASE)


def _size(run, paragraph, document):
    """Effective point size of a run: its own, then its styles', then the paragraph style chain."""
    if run.font.size:
        return run.font.size.pt
    for style in (run.style, paragraph.style):
        while style is not None:
            if style.font is not None and style.font.size:
                return style.font.size.pt
            style = style.base_style
    normal = document.styles["Normal"].font.size
    return normal.pt if normal else None


def _spacing(paragraph):
    """Line spacing as a multiple, or None when it is unset or set in points."""
    style = paragraph.style
    value = paragraph.paragraph_format.line_spacing
    while value is None and style is not None:
        value = style.paragraph_format.line_spacing
        style = style.base_style
    return value if isinstance(value, float) else (1.0 if value is None else None)


def _is_block_quote(paragraph):
    fmt = paragraph.paragraph_format
    indented = bool(fmt.left_indent and fmt.left_indent.inches >= 0.4 and fmt.right_indent and fmt.right_indent.inches >= 0.4)
    return indented or "quote" in (paragraph.style.name or "").lower()


def _footnote_words(path):
    with zipfile.ZipFile(path) as archive:
        if "word/footnotes.xml" not in archive.namelist():
            return 0
        from xml.etree import ElementTree
        root = ElementTree.fromstring(archive.read("word/footnotes.xml"))
    words = 0
    for note in root.iter(W + "footnote"):
        if note.get(W + "type") in ("separator", "continuationSeparator"):
            continue
        words += len("".join(node.text or "" for node in note.iter(W + "t")).split())
    return words


def measure(path, kind, on=None):
    """Return (problems, facts): departures or unverifiable items, and the measured facts."""
    document = Document(path)
    value = lambda name: wi_values.value_on(name, on)
    problems, facts = [], []

    def need(ok, text, authority):
        (facts if ok else problems).append(f"{text}  [Wis. Stat. {authority}]")

    side, vertical = value("appellate_side_margin_min")["value"], value("appellate_top_bottom_margin_min")["value"]
    for index, section in enumerate(document.sections, 1):
        label = f"section {index}: "
        width, height = round(section.page_width.inches, 2), round(section.page_height.inches, 2)
        need((width, height) == (8.5, 11.0), f"{label}page is {width} by {height} inches; required 8.5 by 11", "s. 809.19(8)(b)2.")
        left, right = round(section.left_margin.inches, 3), round(section.right_margin.inches, 3)
        need(left >= side and right >= side, f"{label}left and right margins are {left} and {right} inches; minimum {side}",
             "s. 809.19(8)(b)3.e.")
        top, bottom = round(section.top_margin.inches, 3), round(section.bottom_margin.inches, 3)
        need(top >= vertical and bottom >= vertical,
             f"{label}top and bottom margin settings are {top} and {bottom} inches; minimum {vertical}", "s. 809.19(8)(b)3.e.")
        footers = [("footer", section.footer)]
        if section.different_first_page_header_footer:
            footers.append(("first-page footer", section.first_page_footer))
        for name, footer in footers:
            xml = footer._element.xml
            has_field = bool(re.search(r"<w:instrText[^>]*>\s*PAGE\b", xml)) or 'w:instr=" PAGE' in xml or 'w:instr="PAGE' in xml
            centered = 'w:jc w:val="center"' in xml
            need(has_field and centered, f"{label}{name} " + ("has" if has_field else "has no") + " page-number field"
                 + ("" if not has_field else " and it is " + ("centered" if centered else "not centered"))
                 + "; required: page numbers centered in the bottom margin", "s. 809.19(8)(bm)")
        numbering = section._sectPr.find(W + "pgNumType")
        start = numbering.get(W + "start") if numbering is not None else None
        fmt = numbering.get(W + "fmt") if numbering is not None else None
        if index == 1:
            need(start in (None, "1") and fmt in (None, "decimal"),
                 f"{label}page numbering starts at {start or '1 (default)'} in format {fmt or 'decimal (default)'}; required: Arabic "
                 "numerals starting at 1 on the cover", "s. 809.19(8)(bm)")

    paragraphs = document.paragraphs
    found = {}
    for position, paragraph in enumerate(paragraphs):
        text = paragraph.text.strip()
        if not text or len(text.split()) > 12:
            continue
        for name, pattern in HEADINGS.items():
            if name not in found and pattern.search(text):
                found[name] = position
    limit_name, starts = KINDS[kind]
    limit = value(limit_name)
    begin = next((found[name] for name in starts if name in found), None)
    counted = []
    if begin is None or "conclusion" not in found or found["conclusion"] < begin:
        problems.append("the counted portions could not be located: the brief needs the headings "
                        + (" or ".join(name.upper() if name != "statement" else "STATEMENT OF THE CASE" for name in starts))
                        + f" and CONCLUSION on their own lines, so the length was not verified  [Wis. Stat. {limit['authority'][11:]}]")
    else:
        end = len(paragraphs)
        for position in range(found["conclusion"] + 1, len(paragraphs)):
            if END_OF_CONCLUSION.search(paragraphs[position].text.strip()):
                end = position
                break
        counted = paragraphs[begin:end]
        body_words = sum(len(paragraph.text.split()) for paragraph in counted)
        notes = _footnote_words(path)
        total = body_words + notes
        portions = "s. 809.19(1)(d), (e) and (f)" if "statement" in starts and begin == found.get("statement") else "s. 809.19(1)(e) and (f)"
        need(total <= limit["value"],
             f"counted portions ({portions}) hold {body_words} words" + (f" plus {notes} footnote words" if notes else "")
             + f" = {total}; limit {limit['value']} for a {kind} brief", limit["authority"][11:])
        images = sum(len(paragraph._element.findall(".//" + W + "drawing")) + len(paragraph._element.findall(".//" + W + "pict"))
                     for paragraph in counted)
        if images:
            problems.append(f"{images} image(s) sit in the counted portions; words in an image count toward the length and this "
                            "tool cannot read them, so the length was not verified  [Wis. Stat. s. 809.19(8g)(a)2.]")

    body_min, quote_min = value("appellate_body_point_min")["value"], value("appellate_quote_footnote_point")["value"]
    low, high = value("appellate_line_spacing_min")["value"], value("appellate_line_spacing_max")["value"]
    small, tight = [], []
    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        quote = _is_block_quote(paragraph)
        sizes = [size for size in (_size(run, paragraph, document) for run in paragraph.runs if run.text.strip()) if size]
        floor = quote_min if quote else body_min
        if sizes and min(sizes) < floor:
            small.append(f"{min(sizes):g} pt in {'block quote' if quote else 'body text'} \"{text[:50]}\"")
    for paragraph in counted:
        if len(paragraph.text.split()) < 40 or _is_block_quote(paragraph):
            continue
        spacing = _spacing(paragraph)
        if spacing is None:
            tight.append(f"fixed-point spacing (check by hand) in \"{paragraph.text.strip()[:50]}\"")
        elif not low <= round(spacing, 2) <= high:
            tight.append(f"{spacing:g} lines in \"{paragraph.text.strip()[:50]}\"")
    need(not small, "text below the minimum size: " + "; ".join(small[:5]) + (f"; and {len(small) - 5} more" if len(small) > 5 else "")
         if small else f"no text below {body_min} point in body text or {quote_min} point in block quotes", "s. 809.19(8)(b)3.c.")
    need(not tight, "body line spacing outside " + f"{low} to {high}: " + "; ".join(tight[:5])
         + (f"; and {len(tight) - 5} more" if len(tight) > 5 else "")
         if tight else f"body paragraphs of 40 words or more in the counted portions are spaced between {low} and {high} lines",
         "s. 809.19(8)(b)3.c.")
    return problems, facts


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("brief", type=Path, help="the brief as a .docx file")
    parser.add_argument("--kind", required=True, choices=sorted(KINDS))
    args = parser.parse_args(argv)
    if args.brief.suffix.lower() != ".docx" or not args.brief.is_file():
        parser.exit(2, "check_appellate_brief: give an existing .docx file\n")
    try:
        problems, facts = measure(args.brief, args.kind)
    except Exception as exc:  # a damaged or unusual file is a usage error, not a pass
        parser.exit(2, f"check_appellate_brief: could not read the document: {exc}\n")
    for line in facts:
        print("ok    " + line)
    for line in problems:
        print("CHECK " + line)
    print(f"{len(problems)} item(s) depart from s. 809.19(8) or could not be verified. This measures the DOCX, not the filed PDF; "
          "it cannot tell a proportional serif font from another font or read text in images. The form and length "
          "certification under s. 809.19(8g)(a) is the filer's own statement.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
