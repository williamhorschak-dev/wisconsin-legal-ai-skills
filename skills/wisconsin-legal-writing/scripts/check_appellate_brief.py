#!/usr/bin/env python3
"""Measure a Wisconsin Court of Appeals brief in DOCX form against Wis. Stat. s. 809.19(8).

    python check_appellate_brief.py brief.docx --kind appellant
    python check_appellate_brief.py brief.docx --kind respondent --no-statement-of-case
    python check_appellate_brief.py reply.docx --kind reply

Exit 0 only when every check below was measured and passed. Exit 1 when a measured value
departs from the rule. Exit 3 when nothing measured departs but something in scope could not
be measured; the tool never reports an unmeasured item as passing. Exit 2 for a usage error
or a file it cannot read.

What it measures, for a brief in a proportional serif font:

  page setup    every section is 8.5 by 11 inches with side margins of at least 1.25 inches
                and top and bottom margins of at least 1 inch, s. 809.19(8)(b)2. and 3.e.
  pagination    every footer Word will print (default, first page, even page, in every
                section) has a PAGE field in a centered paragraph; numbering is Arabic,
                starts at 1 and is not restarted, s. 809.19(8)(bm).
  length        the words from the statement of the case (or from the argument, for a
                reply or nonparty brief or a respondent who omits the statement) through
                the conclusion, with the footnotes cited there, against the limit in
                s. 809.19(8)(c). It counts twice: up to the first line after the conclusion
                that opens a date, signature or certification, and through the end of the
                file. It passes only when the larger count is under the limit by a 1 percent
                margin and reports a departure only when the smaller count is over by that
                margin. In between it exits 3, because its count can differ from a word
                processor's and it cannot be sure where the conclusion ends.
  text form     in those same paragraphs: body text of at least 13 points spaced 1.15 to 1.5
                lines, or, for a paragraph indented at least half an inch or in a quotation
                style, single-spaced text of at least 11 points; and footnotes single-spaced
                in at least 11 points, s. 809.19(8)(b)3.c.

What makes it exit 3: a table, picture, drawing or text box in the counted portions (words in
an image count, s. 809.19(8g)(a)2., and it cannot read them); tracked changes; endnotes; a
"Combined Brief" or a second ARGUMENT or CONCLUSION heading (each part of a combined brief
under s. 809.19(6) has its own limit and certification); a missing section heading; fixed
line spacing, which the rule allows when "equivalent" and the tool does not judge; a heading
outside the body numbers, because the tool does not decide whether the body-text numbers
reach headings; a page number placed by a tab, table or text box; numbering restarted at a
number other than 1; a missing page size or margin.

What it does not examine: the cover, the tables of contents and authorities, the statement of
issues, the signature block and the certifications; the font family, the use of italics and
bold, and whether an indented paragraph really is a quotation; the rendered page, where a
header, footer or positioned object can still intrude on a margin; the content of the brief.
It treats 11 points as a minimum for block quotes and footnotes. It does not apply the page
limits for monospaced or handwritten briefs. The numbers come from wi_values.py.

Counsel must submit a signed certification of form and length with the brief,
s. 809.19(8g)(a)1., and may use the word count of a commercial word processor,
s. 809.19(8g)(a)2. A self-represented filer must still meet the form and length rules. This
tool's count is a cross-check, not the certified count. Standard library only.
"""
import argparse
import math
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wi_values  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
MAX_PART = 64 * 1024 * 1024
MARGIN = 0.01  # this project's screening margin around the word limit, not a legal tolerance

# kind: (limit id in wi_values, whether the count starts at the statement of the case)
KINDS = {
    "appellant": ("appellate_brief_words", True),
    "respondent": ("appellate_brief_words", True),
    "reply": ("appellate_reply_brief_words", False),
    "nonparty": ("appellate_nonparty_brief_words", False),
}
_LEAD = r"^(?:[IVXLC]+\.|\d+\.)?\s*"
CASE_HEADING = re.compile(_LEAD + r"STATEMENT OF (?:THE )?CASE(?: AND (?:OF )?(?:THE )?(?:STATEMENT OF )?FACTS)?[.:]?$", re.IGNORECASE)
ARGUMENT_HEADING = re.compile(_LEAD + r"ARGUMENT[.:]?$", re.IGNORECASE)
CONCLUSION_HEADING = re.compile(_LEAD + r"CONCLUSION[.:]?$", re.IGNORECASE)
AFTER_CONCLUSION = re.compile(r"^\W*(?:dated\b|respectfully submitted\b|electronically signed\b|signed\b|certifications?\b|"
                              r"form and length\b)", re.IGNORECASE)
COMBINED = re.compile(r"\bcombined\s+brief\b", re.IGNORECASE)
PAGE_FIELD = re.compile(r"(?<![A-Za-z])PAGE(?![A-Za-z])(?:\s*\\\*\s*([A-Za-z]+))?")
NOT_ARABIC = {"roman", "alphabetic", "ordinal", "cardtext", "ordtext", "hex", "dollartext"}
UNREADABLE_INLINE = ("txbxContent", "drawing", "pict", "object")


class Unreadable(Exception):
    """The file is not a DOCX this tool can open."""


def _true(element):
    return element is not None and element.get(W + "val") not in ("0", "false", "off")


def _int(text):
    try:
        return int(text)
    except (TypeError, ValueError):
        return None


class Brief:
    def __init__(self, path):
        try:
            archive = zipfile.ZipFile(path)
        except (OSError, zipfile.BadZipFile) as exc:
            raise Unreadable(f"not a readable DOCX: {exc}") from exc
        with archive:
            self.archive = archive
            document = self._part("word/document.xml")
            if document is None or document.find(W + "body") is None:
                raise Unreadable("no word/document.xml with a body; is this a DOCX?")
            self.body = document.find(W + "body")
            self.parents = {child: parent for parent in document.iter() for child in parent}
            styles = self._part("word/styles.xml")
            settings = self._part("word/settings.xml")
            footnotes = self._part("word/footnotes.xml")
            rels = self._part("word/_rels/document.xml.rels")
            self.even_pages = settings is not None and _true(settings.find(W + "evenAndOddHeaders"))
            self.styles, self.default_style = {}, None
            self.doc_rpr = self.doc_ppr = None
            if styles is not None:
                for style in styles.iter(W + "style"):
                    self.styles[style.get(W + "styleId")] = style
                    if style.get(W + "type") == "paragraph" and style.get(W + "default") in ("1", "true"):
                        self.default_style = style.get(W + "styleId")
                self.doc_rpr = styles.find(f"{W}docDefaults/{W}rPrDefault/{W}rPr")
                self.doc_ppr = styles.find(f"{W}docDefaults/{W}pPrDefault/{W}pPr")
            self.footnotes = {}
            if footnotes is not None:
                for note in footnotes.findall(W + "footnote"):
                    if note.get(W + "type") in (None, "normal"):
                        self.footnotes[note.get(W + "id")] = note
            self.footers = {}
            if rels is not None:
                for rel in rels:
                    if rel.get("Type", "").endswith("/footer"):
                        target = rel.get("Target", "").lstrip("/")
                        name = target if target.startswith("word/") else "word/" + target
                        self.footers[rel.get("Id")] = self._part(name)
        self.blocks = list(self._blocks(self.body))
        self.tracked = any(next(document.iter(W + tag), None) is not None for tag in ("ins", "del", "moveFrom", "moveTo"))
        self.endnotes = next(document.iter(W + "endnoteReference"), None) is not None

    def _part(self, name):
        try:
            info = self.archive.getinfo(name)
        except KeyError:
            return None
        if info.file_size > MAX_PART:
            raise Unreadable(f"{name} is larger than this tool reads")
        data = self.archive.read(name)
        if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
            raise Unreadable(f"{name} carries a document type declaration")
        try:
            return ET.fromstring(data)
        except ET.ParseError as exc:
            raise Unreadable(f"{name} is not well-formed XML: {exc}") from exc

    def _blocks(self, parent):
        """Top-level paragraphs and tables in order; content controls are transparent."""
        for child in parent:
            if child.tag == W + "p":
                yield "p", child
            elif child.tag == W + "tbl":
                yield "tbl", child
            elif child.tag == W + "sdt":
                content = child.find(W + "sdtContent")
                if content is not None:
                    yield from self._blocks(content)
            elif child.tag in (W + "customXml", W + "smartTag"):
                yield from self._blocks(child)

    # ---- effective formatting

    def _chain(self, style_id):
        seen = []
        while style_id in self.styles and style_id not in seen:
            seen.append(style_id)
            based = self.styles[style_id].find(W + "basedOn")
            style_id = based.get(W + "val") if based is not None else None
        return [self.styles[item] for item in seen]

    def _par_chain(self, paragraph):
        ppr = paragraph.find(W + "pPr")
        named = ppr.find(W + "pStyle") if ppr is not None else None
        chain = self._chain(named.get(W + "val")) if named is not None else []
        return ppr, chain or self._chain(self.default_style)

    def par_attr(self, paragraph, child, attr):
        ppr, chain = self._par_chain(paragraph)
        for holder in [ppr] + [style.find(W + "pPr") for style in chain] + [self.doc_ppr]:
            element = holder.find(W + child) if holder is not None else None
            if element is not None and element.get(W + attr) is not None:
                return element.get(W + attr)
        return None

    def _run_property(self, paragraph, run, name):
        rpr = run.find(W + "rPr")
        holders = [rpr]
        named = rpr.find(W + "rStyle") if rpr is not None else None
        if named is not None:
            holders += [style.find(W + "rPr") for style in self._chain(named.get(W + "val"))]
        holders += [style.find(W + "rPr") for style in self._par_chain(paragraph)[1]] + [self.doc_rpr]
        for holder in holders:
            element = holder.find(W + name) if holder is not None else None
            if element is not None:
                return element
        return None

    def text_runs(self, paragraph):
        """(points, bold) for each run of the paragraph that prints text."""
        found = []
        for run in paragraph.iter(W + "r"):
            if not "".join(item.text or "" for item in run.findall(W + "t")).strip():
                continue
            size = self._run_property(paragraph, run, "sz")
            half_points = _int(size.get(W + "val")) if size is not None else 20
            found.append((None if half_points is None else half_points / 2, _true(self._run_property(paragraph, run, "b"))))
        return found

    def style_names(self, paragraph):
        return [name.get(W + "val", "") for style in self._par_chain(paragraph)[1]
                for name in [style.find(W + "name")] if name is not None]

    @staticmethod
    def text(paragraph):
        parts = []
        for element in paragraph.iter():
            if element.tag == W + "t":
                parts.append(element.text or "")
            elif element.tag in (W + "tab", W + "br", W + "cr"):
                parts.append(" ")
            elif element.tag == W + "noBreakHyphen":
                parts.append("-")
        return "".join(parts)

    @staticmethod
    def unreadable_inline(element):
        return sorted({tag for tag in UNREADABLE_INLINE if next(element.iter(W + tag), None) is not None}
                      | ({"AlternateContent"} if next(element.iter(MC + "AlternateContent"), None) is not None else set()))

    def sections(self):
        return [element for element in self.body.iter(W + "sectPr")
                if self.parents.get(element) is None or self.parents[element].tag != W + "sectPrChange"]


def _role_status(points, line, rule, role):
    """'ok', ('departs', why) or ('unknown', why) for a paragraph read as body text or as a block quote."""
    minimum = 13 if role == "body text" else 11
    if points is None:
        return "unknown", "a font size could not be read"
    if points < minimum:
        return "departs", f"{points:g}-point text, under the {minimum}-point minimum for {role}"
    if rule != "auto" or line is None:
        return "unknown", (f"line spacing is fixed at {line / 20:g} points; the rule allows \"an equivalent line spacing\" and this "
                           "tool does not judge equivalence") if line is not None else "line spacing could not be read"
    multiple = line / 240
    if role == "body text" and not 1.15 - 1e-9 <= multiple <= 1.5 + 1e-9:
        return "departs", f"line spacing of {multiple:.3g} lines, outside 1.15 to 1.5 for body text"
    if role != "body text" and line != 240:
        return "departs", f"line spacing of {multiple:.3g} lines, not single-spaced as a {role} must be"
    return "ok"


def measure(path, kind, no_statement_of_case=False):
    """Return {'departs': [...], 'unmeasured': [...], 'measured': [...], 'not_examined': [...]}."""
    brief = Brief(path)
    limit_row = wi_values.value_on(KINDS[kind][0])
    limit = limit_row["value"]
    out = {"departs": [], "unmeasured": [], "measured": [], "not_examined": [], "limit": limit_row}
    departs, unmeasured, measured = out["departs"].append, out["unmeasured"].append, out["measured"].append

    if brief.tracked:
        unmeasured("the file has tracked changes; accept or reject them, then run this again")
    if brief.endnotes:
        unmeasured("the file uses endnotes; the rule speaks of footnotes and this tool does not place endnotes")

    # ---- page setup, s. 809.19(8)(b)2. and 3.e.
    sections = brief.sections()
    page_ok = bool(sections)
    for number, section in enumerate(sections, 1):
        size, margins = section.find(W + "pgSz"), section.find(W + "pgMar")
        where = f"section {number}"
        if size is None or margins is None:
            page_ok = False
            unmeasured(f"{where}: no page size or margins are stored, so they could not be measured")
            continue
        width, height = _int(size.get(W + "w")), _int(size.get(W + "h"))
        if (width, height) != (12240, 15840):
            page_ok = False
            departs(f"{where}: page is {(width or 0) / 1440:g} by {(height or 0) / 1440:g} inches; s. 809.19(8)(b)2. requires a brief "
                    "formatted to fit 8.5 by 11 inch paper")
        for side, minimum in (("left", 1800), ("right", 1800), ("top", 1440), ("bottom", 1440)):
            value = _int(margins.get(W + side))
            if value is None:
                page_ok = False
                unmeasured(f"{where}: the {side} margin could not be read")
            elif abs(value) < minimum:
                page_ok = False
                departs(f"{where}: {side} margin is {abs(value) / 1440:g} inches; s. 809.19(8)(b)3.e. requires at least "
                        f"{minimum / 1440:g}")
    if page_ok:
        measured(f"page setup: {len(sections)} section(s), each 8.5 by 11 inches with side margins of at least 1.25 inches and "
                 "top and bottom margins of at least 1 inch (document settings, not the rendered page)")

    # ---- pagination, s. 809.19(8)(bm)
    before = len(out["departs"]) + len(out["unmeasured"])
    inherited = {}
    for number, section in enumerate(sections, 1):
        where = f"section {number}"
        numbering = section.find(W + "pgNumType")
        fmt = numbering.get(W + "fmt") if numbering is not None else None
        start = numbering.get(W + "start") if numbering is not None else None
        if fmt not in (None, "decimal"):
            departs(f"{where}: page numbers use the {fmt} format; s. 809.19(8)(bm) requires Arabic numerals")
        if number == 1 and start not in (None, "1"):
            departs(f"{where}: numbering starts at {start}; s. 809.19(8)(bm) requires sequential numbering starting at 1 on the cover")
        if number > 1 and start == "1":
            departs(f"{where}: numbering restarts at 1; s. 809.19(8)(bm) requires sequential numbering from the cover")
        elif number > 1 and start is not None:
            unmeasured(f"{where}: numbering restarts at {start}; whether that continues the sequence cannot be told without rendering")
        for reference in section.findall(W + "footerReference"):
            inherited[reference.get(W + "type")] = reference.get(R + "id")
        active = ["default"] + (["first"] if _true(section.find(W + "titlePg")) else []) + (["even"] if brief.even_pages else [])
        for kind_of_footer in active:
            label = f"{where}, {kind_of_footer}-page footer"
            footer = brief.footers.get(inherited.get(kind_of_footer))
            if footer is None:
                departs(f"{label}: there is no footer, so those pages carry no page number; s. 809.19(8)(bm) requires page "
                        "numbers centered in the bottom margin")
                continue
            parents = {child: parent for parent in footer.iter() for child in parent}
            fields = []
            for paragraph in footer.iter(W + "p"):
                if next((inner for inner in paragraph.iter(W + "p") if inner is not paragraph), None) is not None:
                    continue  # a paragraph that only wraps a text box; the inner paragraph is read on its own
                instructions = " ".join([field.get(W + "instr") or "" for field in paragraph.iter(W + "fldSimple")]
                                        + ["".join(item.text or "" for item in paragraph.iter(W + "instrText"))])
                found = PAGE_FIELD.search(instructions)
                if found:
                    fields.append((paragraph, found.group(1)))
            if not fields:
                departs(f"{label}: no PAGE field, so those pages carry no page number; s. 809.19(8)(bm)")
            for paragraph, switch in fields:
                ancestor, boxed = parents.get(paragraph), False
                while ancestor is not None:
                    boxed = boxed or ancestor.tag in (W + "tbl", W + "txbxContent")
                    ancestor = parents.get(ancestor)
                ppr = paragraph.find(W + "pPr")
                if (switch or "").lower() in NOT_ARABIC:
                    departs(f"{label}: the PAGE field is formatted as {switch}; s. 809.19(8)(bm) requires Arabic numerals")
                if boxed or (ppr is not None and ppr.find(W + "framePr") is not None):
                    unmeasured(f"{label}: the page number sits in a table, text box or frame, so its position was not measured")
                elif brief.par_attr(paragraph, "jc", "val") == "center":
                    continue
                elif any(parents[tab].tag == W + "r" for tab in paragraph.iter(W + "tab")) or next(paragraph.iter(W + "ptab"), None) is not None:
                    unmeasured(f"{label}: the page number is placed with a tab, not a centered paragraph, so centering was not measured")
                else:
                    departs(f"{label}: the paragraph holding the PAGE field is not centered; s. 809.19(8)(bm) requires page "
                            "numbers centered in the bottom margin")
    if sections and len(out["departs"]) + len(out["unmeasured"]) == before:
        measured("pagination: every footer Word prints has a PAGE field in a centered paragraph; Arabic numbering from 1 "
                 "with no restart")

    # ---- counted portions
    paragraphs = [(index, element) for index, (what, element) in enumerate(brief.blocks) if what == "p"]
    texts = {index: " ".join(Brief.text(element).split()) for index, element in paragraphs}

    def headings(pattern):
        return [index for index, _ in paragraphs if pattern.match(texts[index])]

    case, argument, conclusion = headings(CASE_HEADING), headings(ARGUMENT_HEADING), headings(CONCLUSION_HEADING)
    structure = []
    if len(argument) != 1 or len(conclusion) != 1:
        structure.append(f"found {len(argument)} ARGUMENT and {len(conclusion)} CONCLUSION heading(s) standing alone on a line; "
                         "exactly one of each is needed. A combined brief under s. 809.19(6) is not supported, and a table of "
                         "contents line without a page number also counts as a heading")
    elif argument[0] > conclusion[0]:
        structure.append("the CONCLUSION heading comes before the ARGUMENT heading")
    start = argument[0] if argument else None
    if KINDS[kind][1] and not structure:
        usable = [index for index in case if index < argument[0]]
        if len(usable) == 1 and len(case) == 1:
            if no_statement_of_case:
                structure.append("--no-statement-of-case was given but a STATEMENT OF THE CASE heading is present")
            start = usable[0]
        elif case:
            structure.append(f"found {len(case)} STATEMENT OF THE CASE heading(s), not one before the argument")
        elif kind == "respondent" and no_statement_of_case:
            pass  # s. 809.19(3)(a)2.: a respondent may exclude the statement of the case
        else:
            structure.append("no STATEMENT OF THE CASE heading was found, so the start of the counted portions is unknown"
                             + ("; if this respondent's brief omits the statement under s. 809.19(3)(a)2., pass "
                                "--no-statement-of-case" if kind == "respondent" else ""))
    if not structure and any(COMBINED.search(texts[index]) for index, _ in paragraphs if index < start):
        structure.append("the brief is titled a combined brief; each part of a combined brief has its own limit and "
                         "certification, s. 809.19(6)(b), (c) and (e), and this tool does not separate the parts")
    if structure:
        for line in structure:
            unmeasured("length and text form: " + line)
        out["not_examined"].append("length and text form were not measured")
    else:
        stop = next((index for index, _ in paragraphs if index > conclusion[0] and AFTER_CONCLUSION.match(texts[index])), None)
        end = len(brief.blocks)

        def notes_in(first, last):
            return [note for index, element in paragraphs if first <= index < last
                    for note in (ref.get(W + "id") for ref in element.iter(W + "footnoteReference"))]

        def words(first, last):
            total = sum(len(texts[index].split()) for index, _ in paragraphs if first <= index < last)
            for note in notes_in(first, last):
                if note in brief.footnotes:
                    total += sum(len(Brief.text(paragraph).split()) for paragraph in brief.footnotes[note].iter(W + "p"))
            return total

        blocked = False
        for index, (what, element) in enumerate(brief.blocks):
            if index < start:
                continue
            if what == "tbl":
                blocked = True
                unmeasured(f"block {index + 1} is a table inside or after the counted portions; its words and form were not measured")
            elif Brief.unreadable_inline(element):
                blocked = True
                unmeasured(f"paragraph {index + 1} holds a picture, drawing or text box; words in an image count, "
                           "s. 809.19(8g)(a)2., and this tool cannot read them")
        for note in notes_in(0, end):
            if note not in brief.footnotes:
                blocked = True
                unmeasured(f"footnote {note} is cited but could not be found")
            elif next(brief.footnotes[note].iter(W + "tbl"), None) is not None or Brief.unreadable_inline(brief.footnotes[note]):
                blocked = True
                unmeasured(f"footnote {note} holds a table, picture or text box that was not measured")

        upper, lower = words(start, end), (words(start, stop) if stop is not None else None)
        margin = math.ceil(limit * MARGIN)
        basis = f"limit {limit} words, {limit_row['authority']}"
        if lower is not None and lower > limit + margin and not blocked:
            departs(f"length: at least {lower} words from \"{texts[start]}\" to the line \"{texts[stop][:40]}\"; {basis}")
        elif lower is not None and lower > limit + margin:
            departs(f"length: at least {lower} words in the text that could be read, before anything unmeasured is added; {basis}")
        elif blocked:
            pass  # the unmeasured lines above already say why no count is reported as passing
        elif upper <= limit - margin:
            measured(f"length: at most {upper} words from \"{texts[start]}\" through the end of the file, which overstates the "
                     f"counted portions" + (f" ({lower} to the line \"{texts[stop][:40]}\")" if lower is not None else "")
                     + f"; {basis}")
        else:
            unmeasured(f"length: {'between ' + str(lower) + ' and ' if lower is not None else 'up to '}{upper} words against a "
                       f"limit of {limit}; that is within {margin} words of the limit or depends on where the conclusion ends, "
                       "and this tool's count can differ from a word processor's. Use the word processor's count of the "
                       "portions named in s. 809.19(8)(c)")

        # ---- text form, s. 809.19(8)(b)3.c., in the counted portions
        before = len(out["departs"]) + len(out["unmeasured"])
        last = stop if stop is not None else end
        checked = quotes = 0
        for index, element in paragraphs:
            if not start <= index < last or not texts[index]:
                continue
            runs = brief.text_runs(element)
            if not runs:
                continue
            checked += 1
            points = None if any(size is None for size, _ in runs) else min(size for size, _ in runs)
            line = _int(brief.par_attr(element, "spacing", "line") or "240")
            rule = brief.par_attr(element, "spacing", "lineRule") or "auto"
            indent = _int(brief.par_attr(element, "ind", "left") or brief.par_attr(element, "ind", "start") or "0") or 0
            quoted = indent >= 720 or any("quot" in name.lower() for name in brief.style_names(element))
            results = [(role, _role_status(points, line, rule, role)) for role in ["body text"] + (["block quote"] if quoted else [])]
            if any(status == "ok" for _, status in results):
                quotes += results[0][1] != "ok"
                continue
            label = f"paragraph {index + 1} (\"{texts[index][:40]}\")"
            heading = (brief.par_attr(element, "outlineLvl", "val") not in (None, "9")) or all(bold for _, bold in runs)
            reasons = "; ".join(f"as {role}: {status[1]}" for role, status in results)
            if heading:
                unmeasured(f"{label} looks like a heading (bold or outline level): {reasons}. The numbers in s. 809.19(8)(b)3.c. "
                           "speak of body text and this tool does not decide whether they reach headings")
            elif any(status[0] == "unknown" for _, status in results):
                unmeasured(f"{label}: {reasons}")
            else:
                departs(f"{label}: {reasons}; s. 809.19(8)(b)3.c.")
        cited = list(dict.fromkeys(note for note in notes_in(0, end) if note in brief.footnotes))
        for note in cited:
            for paragraph in brief.footnotes[note].iter(W + "p"):
                runs = brief.text_runs(paragraph)
                if not runs:
                    continue
                points = None if any(size is None for size, _ in runs) else min(size for size, _ in runs)
                status = _role_status(points, _int(brief.par_attr(paragraph, "spacing", "line") or "240"),
                                      brief.par_attr(paragraph, "spacing", "lineRule") or "auto", "footnote")
                if status != "ok":
                    (unmeasured if status[0] == "unknown" else departs)(f"footnote {note}: {status[1]}; s. 809.19(8)(b)3.c.")
        if len(out["departs"]) + len(out["unmeasured"]) == before:
            measured(f"text form: {checked} paragraph(s) of the counted portions and {len(cited)} footnote(s); {quotes} "
                     "paragraph(s) passed as block quotes because they are indented at least half an inch or use a quotation "
                     "style and are single-spaced in at least 11 points")
        outside = sum(1 for index, (what, _) in enumerate(brief.blocks) if what == "tbl" and index < start)
        out["not_examined"].append(
            f"blocks 1 to {start} (cover, tables, statement of issues" + (f", including {outside} table(s)" if outside else "")
            + ") and " + (f"blocks {stop + 1} to {end} (signature block and certifications)" if stop is not None
                          else "nothing after the conclusion, because no date, signature or certification line was found"))
    out["not_examined"].append("font family, italics and bold, whether an indented paragraph is a quotation, the rendered page, "
                               "and the content of the brief")
    return out


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("brief", type=Path, help="the brief as a .docx file")
    parser.add_argument("--kind", required=True, choices=sorted(KINDS),
                        help="appellant or respondent (main brief), reply, or nonparty under s. 809.19(7)")
    parser.add_argument("--no-statement-of-case", action="store_true",
                        help="a respondent's brief that omits the statement of the case, s. 809.19(3)(a)2.")
    args = parser.parse_args(argv)
    if args.no_statement_of_case and args.kind != "respondent":
        parser.error("--no-statement-of-case applies only to --kind respondent")
    if args.brief.suffix.lower() != ".docx":
        parser.exit(2, "check_appellate_brief: give a .docx file; a PDF or other format is not read\n")
    try:
        result = measure(args.brief, args.kind, args.no_statement_of_case)
    except Unreadable as exc:
        parser.exit(2, f"check_appellate_brief: {exc}\n")
    row = result["limit"]
    print(f"{args.brief.name}: brief kind {args.kind}, checked as a brief in a proportional serif font. Word limit {row['value']}, "
          f"{row['authority']}; basis: {wi_values.basis()}.")
    for label, key in (("DEPARTS", "departs"), ("UNMEASURED", "unmeasured"), ("measured", "measured"), ("not examined", "not_examined")):
        for line in result[key]:
            print(f"{label:<12} {line}")
    departs, unknown = len(result["departs"]), len(result["unmeasured"])
    if departs:
        verdict = f"{departs} measured departure(s)" + (f" and {unknown} unmeasured item(s)" if unknown else "")
    elif unknown:
        verdict = f"no measured departure, but {unknown} item(s) in scope could not be measured, so this is not a pass"
    else:
        verdict = "every check this tool makes was measured and passed; that covers only the lines marked measured"
    print(f"Result: {verdict}. Counsel must submit a signed certification of form and length, s. 809.19(8g)(a)1., and may use a "
          "commercial word processor's count, s. 809.19(8g)(a)2.; a self-represented filer must still meet the form and length "
          "rules. This count is a cross-check, not the certified count, and nothing here is legal review.")
    return 1 if departs else 3 if unknown else 0


if __name__ == "__main__":
    sys.exit(main())
