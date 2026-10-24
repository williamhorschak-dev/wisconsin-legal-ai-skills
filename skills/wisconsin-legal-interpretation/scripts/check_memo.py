#!/usr/bin/env python3
"""
check_memo.py — structural lint for a wisconsin-legal-interpretation research memo.

This checks what a machine can check: that the memo's structure is present, that quotes
carry pincites, that the authority table is filled in rather than templated, that nothing
is silently unverified, and that the red team section exists and says something.

It cannot check whether the law is right. That is the red team's job. A clean run here
means the memo is auditable, not that it is correct.

    python3 scripts/check_memo.py path/to/memo.md
    python3 scripts/check_memo.py path/to/memo.md --sources /path/to/sources

Exit codes: 0 clean, 1 warnings only, 2 errors present.
"""

import argparse
import datetime
import html
import urllib.parse
import os
import re
import sys
import unicodedata

REQUIRED_SECTIONS = [
    "Question Presented",
    "Short Answer",
    "Governing Text",
    "Lens 1",
    "Lens 2",
    "Lens 3",
    "Application",
    "Authority Table",
    "Red Team Report",
    "Retrieval Record",
]

REQUIRED_FRONTMATTER = [
    "type",
    "status",
    "updated",
    "operative_date",
    "framework_checked",
    "citator",
    "red_team",
    "fatal_findings",
    "confidence",
]

VALID_CONFIDENCE = {"HIGH", "MODERATE", "LOW", "UNRESOLVED"}

# ---------------------------------------------------------------------------
# Why these fields are enums and not sentences.
#
# The three claims this linter has to police -- was a citator run, was the red
# team run, were there FATAL findings -- are claims made by the same author the
# check exists to police. An earlier version tested them by pattern-matching the
# author's prose. That cannot work: a word-list over free text is defeated by a
# synonym, another language, a homoglyph, or an abbreviation, and it
# simultaneously produces false accusations against honest authors whose wording
# happens to contain "no".
#
# So the checkable claims are constrained tokens with no room to be clever in,
# and every narrative belongs in a *_notes field the linter never parses. Prose
# is still scanned, but only to raise a MISMATCH when what the memo says and
# what its fields declare disagree -- which is a useful signal in both
# directions and is never the sole basis for a pass.
# ---------------------------------------------------------------------------

VALID_CITATOR = {"KEYCITE", "SHEPARDS", "NONE"}
VALID_SIGNAL = {"NONE", "YELLOW", "RED", "OTHER"}
VALID_RED_TEAM = {"FULL", "COMPACT", "NONE"}
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _strip_yaml_comment(value: str) -> str:
    """Drop a trailing ' # ...' comment. The comment text is still fed to the
    prose backstop, so a comment that contradicts the token is caught there."""
    return re.sub(r"\s+#.*$", "", value or "")


def _token(value: str) -> str:
    """Normalize a frontmatter enum value, and refuse anything that is not plain
    ASCII. Homoglyph substitution (Cyrillic o, fullwidth letters) is how an enum
    check gets defeated; rejecting non-ASCII in a token field costs nothing."""
    v = _strip_yaml_comment(value).strip().strip("\"'").strip()
    v = v.replace("'", "").replace("\u2019", "")
    return v.upper()


def _is_ascii_token(value: str) -> bool:
    return all(ord(ch) < 128 for ch in (value or ""))

# A pincite looks like one of: ¶46 / ¶¶ 44-46 / at 172 / § 809.23(3)(a) / p. 19 / (2004)
PINCITE = re.compile(
    # "§ 809.23(3)" and "§ DHS 134.31(3)(g)" and "ch. NR 102" all count: the
    # Administrative Code puts an agency prefix between the section symbol and
    # the number, and requiring a digit there rejected the whole Code.
    r"(¶+\s?\d+|\bat\s+\d+|§+\s?(?:[A-Z][A-Za-z]{1,5}\s*)?\d|\bp{1,2}\.\s?\d+|"
    r"\bsub\.\s?\(|\bsubd?\.\s?\(|\bch\.\s?[A-Z][A-Za-z]{1,5}\s*\d|\bs\.\s?\d)",
    re.IGNORECASE,
)

# Placeholder text that means the template was never filled in.
PLACEHOLDER = re.compile(
    # A template placeholder looks like <describe this>. An autolink, an email
    # address, an HTML comment, and a real HTML tag (with or without attributes)
    # are none of those, and blocking a memo addressed to "Name <a@b.com>" for
    # having a placeholder is a false accusation.
    # The HTML-tag exemption uses a real tag grammar. An earlier version
    # exempted "<word ...anything...>", which exempted almost every multi-word
    # placeholder the template ships -- "<matter name / case number>",
    # "<date whose law governs, and why>" -- and left the check inoperative.
    r"<(?!"
    r"https?://|mailto:|!--"
    r"|/?(?:a|abbr|b|br|code|div|em|h[1-6]|hr|i|img|li|ol|p|pre|s|small|span|strong|"
    r"sub|sup|table|tbody|td|th|thead|tr|u|ul)(?:\s[^>\n]*)?/?>"
    r"|[^>\s@]+@[^>\s@]+\.[a-z]{2,}>"
    r")"
    r"[^>\n]{2,80}>",
    re.IGNORECASE,
)

UNVERIFIED = re.compile(r"\[UNVERIFIED\]")
FILL_IN = re.compile(r"\[FILL-IN\]")

errors: list[str] = []
warnings: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def warn(msg: str) -> None:
    warnings.append(msg)


def note(msg: str) -> None:
    notes.append(msg)


def split_frontmatter(text: str):
    """Parse the frontmatter into top-level scalar keys.

    Deliberately strict, because the frontmatter is where this linter's
    load-bearing claims live. Only column-zero keys count -- an indented key is
    nested under something and is not the field the reader sees -- and a
    duplicate top-level key is an error rather than a last-one-wins overwrite,
    because a memo whose visible citator line differs from the one the tool
    reads is exactly the failure the fields exist to prevent.

    Returns (fields, raw_frontmatter_text, body).
    """
    if not text.startswith("---"):
        return {}, "", text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, "", text
    raw = text[3:end]
    body = text[end + 4 :]
    fm = {}
    seen_nested = []
    for line in raw.splitlines():
        if not line.strip() or line.strip().startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        key = k.strip()
        if line[:1].strip() == "":  # indented: nested under a parent key
            if key in REQUIRED_FRONTMATTER:
                seen_nested.append(key)
            continue
        if key in fm:
            err(
                f"Frontmatter defines '{key}' more than once. The reader sees the first and "
                "the tool would take the last; a memo cannot make two different claims in the "
                "same field."
            )
        fm[key] = v.strip()
    for key in seen_nested:
        err(
            f"Frontmatter has a nested '{key}:' key. Required fields must be top-level; a "
            "nested one is invisible to a reader skimming the header."
        )
    return fm, raw, body


def check_frontmatter(fm: dict) -> None:
    if not fm:
        err("No YAML frontmatter. type, status, and updated are required.")
        return
    for key in REQUIRED_FRONTMATTER:
        if key not in fm:
            err(f"Frontmatter missing required key: {key}")
        elif not fm[key] or PLACEHOLDER.search(fm[key]):
            err(f"Frontmatter key '{key}' is empty or still a placeholder: {fm[key]!r}")
    tval = _token(fm.get("type", "")).replace("-", "").replace(" ", "")
    if tval and tval not in {"RESEARCHMEMO", "MEMO"} and not PLACEHOLDER.search(fm.get("type", "")):
        warn(
            "type should be 'research-memo' for a Mode 3 deliverable. An unrecognized type "
            "suppresses the reminder to run with --formal, which is where the Mode 3 checks "
            f"live. Found: {fm.get('type', '')!r}"
        )
    conf = _token(fm.get("confidence", ""))
    if conf and conf not in VALID_CONFIDENCE and not PLACEHOLDER.search(conf):
        err(
            f"confidence must be one of {sorted(VALID_CONFIDENCE)}; found {fm['confidence']!r}"
        )
    check_citator(fm)


# --- Prose backstops. These NEVER decide a pass; they only raise a mismatch ---
# The backstops below must fire on "the check did not run" and stay silent on
# "the check ran and found nothing". An earlier version matched any negation
# near a citator word, which blocked honest sentences like "KeyCite shows none
# of the five carries a flag" and "the red team found no missing authority" --
# the exact false accusation this design exists to avoid. They are therefore
# written against the VERBS OF RUNNING, not against negation in general.
_RUN_VERB = (r"(?:run|ran|performed|conducted|completed|done|carried\s+out|attempted|"
             r"available|possible|accessible|reachable)")
# "defer" and "waive" are also out: in Wisconsin practice a court defers to an
# agency and a party waives an argument, both constantly, and neither has
# anything to do with whether the adversarial pass ran. The pass-specific
# senses are picked up by the explicit "red team deferred / waived" alternative
# added to the pattern below.
_SKIP_VERB = r"(?:skipp?\w*|bypass\w*|forgone|foregone|omitt?\w*|abandon\w*|dropped)"
_SKIP_VERB_NARROW = r"(?:deferred|waived|postponed|shelved)"

PROSE_CITATOR_NOT_RUN = re.compile(
    # "not Shepardized", "has not been KeyCited", "never Shepardized or KeyCited"
    r"\b(?:not|never)\b(?:\s+(?:been|yet))?\s+(?:shepardi[sz]ed|keycited|key\s?cited)\b|"
    # "neither Shepard's nor KeyCite was run"
    r"\bneither\b[^.\n]{0,60}\bnor\b[^.\n]{0,60}?(?:was|were|has|have)\s+(?:not\s+|been\s+)?"
    + _RUN_VERB + r"\b|"
    # "no citator", "without a citator", "no citator check was performed"
    r"\b(?:no|without\s+an?y?|without)\s+citator\b|"
    # "the citator was not run / could not be run / is unavailable / was skipped"
    r"\bcitator\b[^.\n]{0,40}?\b(?:not|never)\s+(?:be\s+|been\s+)?" + _RUN_VERB + r"\b|"
    r"\bcitator\b[^.\n]{0,40}?\b" + _SKIP_VERB + r"\b|"
    # "the citator check is still pending", "citator unavailable" -- immediate,
    # so "the citator entry is pending an update by the publisher" and "the
    # citator was run and the result is unavailable to opposing counsel" do not
    # match. Those describe the entry and the result, not the check.
    r"\bcitator\s+(?:check\s+|run\s+|result\s+)?"
    r"(?:is\s+|was\s+|were\s+|remains\s+)?(?:still\s+|yet\s+)?"
    r"(?:pending|outstanding|unavailable|inaccessible)\b|"
    r"\bcitator\s*:\s*(?:not\s*run|none|n/?a|unavailable|skipped)\b|"
    # "no Shepard's or KeyCite access", "no access to Westlaw"
    r"\bno\s+(?:shepard'?s?|keycite|key\s?cite|westlaw|lexis)[^.\n]{0,40}?\baccess\b|"
    r"\bno\s+access\b[^.\n]{0,40}?(?:shepard|keycite|key\s?cite|westlaw|lexis)",
    re.IGNORECASE,
)

# NOTE on what is deliberately NOT here. "independent review" was in this list
# and had to come out: it is the standard Wisconsin formulation of de novo
# review -- "independent review, without deference" -- which memo-format.md's
# Lens 3 and red-team.md Attack 7 both require the memo to state. Matching it
# meant a paralegal writing the prescribed standard-of-review sentence got a
# hard error accusing them of skipping the red team. A term of art in the
# subject matter must never be a keyword in a check about the process.
_PASS = (r"(?:red[-\s]?team|adversarial\s+(?:pass|review|check)|"
         r"seven[-\s]attack\s+pass|the\s+seven\s+attacks)")
PROSE_RED_TEAM_SKIPPED = re.compile(
    "|".join([
        # "the red team was not run / was not performed / could not be run"
        _PASS + r"[^.\n]{0,40}?\b(?:was|were|is|are|could|can|did)?\s*"
              + r"(?:not|never)\s+(?:be\s+|been\s+)?" + _RUN_VERB + r"\b",
        # "the red team was skipped / deferred / bypassed"
        _PASS + r"[^.\n]{0,40}?\b" + _SKIP_VERB + r"\b",
        r"\b" + _SKIP_VERB + r"\b[^.\n]{0,40}?" + _PASS,
        # "the red team was deferred/waived" -- immediate, so that a court
        # deferring to an agency or a party waiving an argument does not match.
        _PASS + r"\s+(?:pass\s+)?(?:was|were|is|has\s+been)?\s*" + _SKIP_VERB_NARROW,
        # "no adversarial pass was performed", "without a red team"
        r"\b(?:no|without\s+an?|neither)\s+" + _PASS + r"\b",
        # "red team: pending / outstanding / none"
        _PASS + r"\s*:\s*(?:none|pending|outstanding|not\s*run|skipped|n/?a|0\b)",
        _PASS + r"[^.\n]{0,40}?\b(?:remains?\s+)?(?:pending|outstanding)\b",
        # explicit tallies and the deadline formula
        r"attacks?\s+(?:run|attempted)\s*:\s*(?:none|no\b|0\b|zero)",
        r"\b0\s+of\s+7\b",
        r"checks?\s+not\s+run\s*:\s*all",
        r"\btime\s+did\s+not\s+permit\b[^.\n]{0,40}?" + _PASS,
    ]),
    re.IGNORECASE,
)
# A grade, not an adjective. "Severity: FATAL - the case does not exist" is a
# grade; "Fatal variance doctrine does not apply" is Wisconsin pleading law and
# "Disposition: Fatal variance argument rejected" is a case-table row. The
# distinction is what follows the word: a grade is followed by end-of-line or
# punctuation, an adjective by its noun. This is the same lesson as
# "independent review" -- a process check must not key on a word the subject
# matter owns.
# "FATAL" written in capitals is a grade. "Fatal variance" is Wisconsin
# pleading law and "a fatal flaw" is English. Case is the reliable separator, so
# the primary patterns are CASE-SENSITIVE on the all-caps form and impose no
# constraint on what follows -- which is what lets them see
# "Severity: FATAL (Attack 1 fire alarm)", "Severity: **FATAL**",
# "Severity: FATAL/Attack 1", and "Severity: FATAL findings do exist here".
# A case-insensitive fallback catches a lowercase grade ("severity: fatal") but
# only when nothing follows it except punctuation or end of line.
GRADE_TAIL = r"(?=\s*(?:$|[.,;:|)\]\-\u2013\u2014\"\u201d\u2019'`]))"
LABEL = r"(?:Severity(?:\s+(?:level|rating|grade))?|Grade|Rating|Disposition|Finding\s+severity)"

PROSE_FATAL = [
    # All-caps grade after a label. Case-sensitive; no tail constraint.
    re.compile(
        r"^[ \t]*(?:[-*+>|`\"\u201c\u2018']\s*)*(?:\*\*|__)?" + LABEL
        + r"(?:\*\*|__)?[ \t]*(?:[:\-\u2013\u2014|]|\bis\b)[ \t]*(?:\*\*|__)?F[\*_]{0,2}ATAL\b",
        re.MULTILINE,
    ),
    # All-caps grade after a label ANYWHERE on the line. Anchoring every pattern
    # to the start of a line meant "Attack 1 returned Severity: FATAL on the DHS
    # pincite" -- a perfectly ordinary sentence in a report -- was invisible.
    re.compile(
        LABEL + r"(?:\s*\([^)\n]{0,20}\))?[ \t]*(?:[:=>\-\u2013\u2014]+|\bis\b|\breturned\b)"
        r"[ \t]*(?:\*\*|__|`|\")?FATAL\b",
    ),
    # A bare declarative: "This finding is FATAL", "One FATAL finding remains".
    re.compile(r"\b(?:is|was|graded|grades?|remains?)\s+FATAL\b"),
    re.compile(r"\b(?:one|two|three|four|five|\d+)\s+FATAL\s+(?:finding|defect|item)s?\b"),
    re.compile(r"\bFATAL\s+(?:finding|defect)s?\s+(?:remains?|stands?|is\s+outstanding|"
               r"are\s+outstanding|persists?)\b", re.IGNORECASE),
    # Lowercase or mixed-case grade, only with a punctuation tail.
    re.compile(
        r"^[ \t]*(?:[-*+>|`\"\u201c\u2018']\s*)*(?:\*\*|__)?" + LABEL
        + r"(?:\*\*|__)?[ \t]*(?:[:\-\u2013\u2014|]|\bis\b)[ \t]*(?:\*\*|__)?F[\*_]{0,2}ATAL\b"
        + GRADE_TAIL,
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(r"^[ \t]*\|[^\n]*\|[ \t]*(?:\*\*|__)?FATAL\b[ \t]*(?:\*\*|__)?[ \t]*(?=\|)",
               re.MULTILINE),
    re.compile(r"\(\s*FATAL\s*\)"),
    # A quoted or code-spanned label anywhere on a line. Reproducing a subagent's
    # report as a quotation is the format memo-format.md asks for, so a quoted
    # finding is a finding. FATAL_LEGEND / FATAL_NEGATED still exempt a quoted
    # *rule* ("a 'Severity: FATAL' finding stops delivery; none was found").
    re.compile(
        r"[`\"\u201c\u2018'][ \t]*(?:\*\*|__)?" + LABEL + r"(?:\*\*|__)?"
        r"[ \t]*[:\-\u2013\u2014][ \t]*(?:\*\*|__)?FATAL\b",
    ),
    re.compile(r"^[ \t]*(?:[-*+>]\s*)*(?:\*\*|__)?FATAL(?:\*\*|__)?[ \t]*[:\-\u2013\u2014]",
               re.MULTILINE),
    # "Severity:" then the grade on the following line.
    # Label and grade split across lines.
    re.compile(
        r"^[ \t]*(?:[-*+>|`\"]\s*)*(?:\*\*|__)?" + LABEL + r"(?:\*\*|__)?"
        r"[ \t]*[:\-\u2013\u2014]?[ \t]*\n[ \t]*(?:[-*+>|`\"]\s*)*(?:\*\*|__)?FATAL\b",
        re.MULTILINE,
    ),
]
# Phrasings that mention FATAL only to say there were NONE.
#
# The negation must attach to the label itself. An earlier version exempted any
# match with a negation word anywhere within 80 characters, which meant the
# single most likely real FATAL line in this protocol --
# "Severity: FATAL - NOT FOUND in the reporter", the fire alarm red-team.md
# Attack 1 teaches you to write -- was silently exempted. Only these shapes
# count as saying there were none:
FATAL_NEGATED = re.compile(
    # "FATAL: none", "FATAL findings: 0", "FATAL - nil"
    r"\bFATAL(?:\s+(?:findings?|defects?|items?|grade))?\s*[:=\-\u2013\u2014]?\s*"
    r"(?:none|nil|0\b|zero)\b|"
    # "no FATAL findings", "none of the FATAL kind", "zero FATAL defects"
    r"\b(?:no|none|zero|not\s+one)\b(?:\s+\w+){0,3}?\s+FATAL\b|"
    # "No FATAL finding was made", "no FATAL defect arose"
    r"\bno\s+FATAL\b|"
    # "FATAL: none found", "FATAL was not found", "no such finding"
    r"\bFATAL\b[^.\n]{0,20}\b(?:was\s+not\s+(?:found|made|recorded)|"
    r"(?:were|was)\s+none|none\s+(?:found|arose|were\s+made))\b",
    re.IGNORECASE,
)
# A line that DEFINES the severity scale rather than applying it to a finding.
# Also narrowed: the definitional verb must follow FATAL closely, and a bare
# mention of "severity scale" elsewhere on the line no longer exempts a grade.
FATAL_LEGEND = re.compile(
    r"\bFATAL\b\s*(?:[:=\-\u2013\u2014]\s*)?(?:is\s+)?"
    r"(?:reserved|means|denotes|defined\s+as|refers\s+to|=\s)|"
    r"^[ \t]*(?:severity\s+scale|severity\s+grades?|the\s+grades?\s+are|rubric)\b",
    re.IGNORECASE | re.MULTILINE,
)


# A first-pass FATAL finding that was corrected must still be reproduced in the
# report, unedited (memo-format.md §4, red-team.md §5). fatal_findings then
# correctly reads 0 -- there is no FATAL finding outstanding. Without this the
# package's own required output for that case is unlintable, and the only way
# past the linter is to edit the reproduced finding, which is exactly the
# softening the protocol exists to prevent.
PRIOR_PASS_HEADING = re.compile(
    r"^[ \t]*#{1,6}[ \t]*(?:\*\*|__)?(?:corrected|resolved|fixed)\b[^\n]{0,80}$",
    re.IGNORECASE | re.MULTILINE,
)
ANY_HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]*\S", re.MULTILINE)


def _in_reproduced_prior_finding(text: str, pos: int) -> bool:
    """True only for a finding reproduced **as a block quotation** under a
    **heading** that names it corrected.

    Deliberately narrow, and narrowed twice. The first version fenced 1200
    characters after any line beginning "corrected/resolved/fixed", which meant
    one line of prose -- "Resolved -- see the note below." -- typed above a
    LIVE finding took a formal deliverable from blocked to clean. Three
    conditions now hold together:

      1. the marker is a real heading (``### Corrected on the second pass``),
      2. the match is inside a block quotation (``>``) under that heading, which
         is how memo-format.md asks a prior finding to be reproduced, and
      3. no other heading intervenes between the marker and the match.

    A live finding written in the ordinary bullet form satisfies none of them.
    """
    line_start = text.rfind("\n", 0, pos) + 1
    line_end = text.find("\n", pos)
    line = text[line_start : line_end if line_end != -1 else len(text)]
    # (2) the reproduced finding is a block quotation.
    if not re.match(r"^[ \t]*>", line):
        return False
    # (1) the nearest preceding heading names it corrected.
    last = None
    for m in ANY_HEADING.finditer(text, 0, line_start):
        last = m
    if last is None:
        return False
    head_line_end = text.find("\n", last.start())
    heading = text[last.start() : head_line_end if head_line_end != -1 else len(text)]
    if not PRIOR_PASS_HEADING.match(heading):
        return False
    # (3) nothing but the quoted block between the heading and the match.
    return True


def _prose_has_fatal(text: str) -> bool:
    """Negation is evaluated per match, not per document. A report that says
    "FATAL: none" in one line and grades a finding FATAL in another has a real
    FATAL finding; an earlier version let the first line excuse the second."""
    for pat in PROSE_FATAL:
        for m in pat.finditer(text):
            line_start = text.rfind("\n", 0, m.start()) + 1
            line_end = text.find("\n", m.end())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            # The exemption is judged on the matched span and the words
            # immediately around it, NOT on the whole line or sentence: a
            # negation elsewhere in the sentence describes the defect, not the
            # grade ("Severity: FATAL - the sentence is NOT FOUND in the
            # reporter" is a FATAL finding, and the "NOT" belongs to the
            # sentence, not to the grade).
            # FATAL_NEGATED is narrow enough to be safe at line scope now: it
            # matches only shapes where the negation attaches to the LABEL
            # ("FATAL: none", "no FATAL findings"), never a negation that
            # belongs to the defect being described ("FATAL - NOT FOUND in the
            # reporter", "FATAL, because no such subsection exists").
            # Scope the negation test to the LINE the match is on. An earlier
            # version also looked 60 characters past the match, which crossed
            # into the next line -- so a report listing a real FATAL finding
            # and, on the following line, "FATAL: none", exempted the real one.
            # The negation must sit at the grade, not later in the line: a line
            # reading "Severity: FATAL - no other FATAL findings arose" grades
            # this finding FATAL and says nothing about it being absent.
            # Clamped to the END OF THE LINE. A short lookahead past the match
            # crossed the newline, so a real grade on one line was exempted by a
            # "FATAL: none" tally on the next.
            line_stop = line_end if line_end != -1 else len(text)
            window = text[line_start : min(line_stop, m.end() + 14)]
            if FATAL_NEGATED.search(window):
                continue
            # A rule-statement exemption applies only when the line is not also
            # grading something: "This finding is FATAL and stops delivery" is a
            # finding that happens to quote its own consequence.
            if FATAL_LEGEND.search(line):
                continue
            if _is_rule_statement(line) and not re.search(
                r"\b(?:this|the)\s+finding\b|^\s*(?:[-*+>|]\s*)*" + LABEL, line, re.IGNORECASE
            ):
                continue
            if _in_reproduced_prior_finding(text, m.start()):
                continue
            return True
    return False


# Confusable letters used to hide a keyword from a text scan. Cyrillic and Greek
# capitals that render identically to Latin, plus the fullwidth forms.
_CONFUSABLE = str.maketrans({
    "\u0410": "A", "\u0412": "B", "\u0415": "E", "\u041a": "K", "\u041c": "M",
    "\u041d": "H", "\u041e": "O", "\u0420": "P", "\u0421": "C", "\u0422": "T",
    "\u0430": "a", "\u0435": "e", "\u043a": "k", "\u043c": "m", "\u043e": "o",
    "\u0440": "p", "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\u0391": "A", "\u0392": "B", "\u0395": "E", "\u039a": "K", "\u039c": "M",
    "\u039d": "N", "\u039f": "O", "\u03a1": "P", "\u03a4": "T",
    "\u200b": "", "\u200c": "", "\u200d": "", "\ufeff": "",
})


# Unicode names whose final token is a single ASCII letter are, in practice, the
# homoglyph families: "CHEROKEE LETTER A", "MATHEMATICAL BOLD CAPITAL F",
# "FULLWIDTH LATIN CAPITAL LETTER K". Fold them to that letter.
_LOOKALIKE_TAIL = re.compile(r"(?:^|\s)(?:LETTER|CAPITAL|SMALL|SYLLABLE)\s+([A-Z])$")


def _ascii_lookalike(ch: str) -> str:
    if ord(ch) < 128:
        return ch
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return ch
    m = _LOOKALIKE_TAIL.search(name)
    if m:
        return m.group(1)
    return ch


def _fold(text: str) -> str:
    """Unescape, normalize, fold confusables, drop combining and format chars.

    Order matters and an earlier version had it wrong: entities were unescaped
    *after* the confusable fold, so "F&#x410;TAL" decoded into a Cyrillic A that
    nothing folded. Unescape first, repeatedly, then normalize, then fold."""
    t = text
    for _ in range(3):
        u = html.unescape(t)
        if u == t:
            break
        t = u
    # NFKD, not NFKC: decomposing first means a precomposed accented letter
    # (U+00C1 A-acute) becomes A + combining acute, and the combining mark is
    # then dropped below. NFKC would leave U+00C1 intact and unmatched.
    t = unicodedata.normalize("NFKD", t)
    # Drop combining marks (Mn) and format/invisible characters (Cf), which are
    # how a keyword gets hidden from a scan while still rendering normally.
    t = "".join(ch for ch in t if unicodedata.category(ch) not in {"Mn", "Cf"})
    t = unicodedata.normalize("NFKC", t)
    t = t.translate(_CONFUSABLE)
    # Anything still non-ASCII but confusable with an ASCII letter: fold it by
    # its Unicode name, which catches scripts the hand table does not list
    # (Cherokee, Coptic, Lisu, Deseret, and the mathematical alphanumerics).
    t = "".join(_ascii_lookalike(ch) for ch in t)
    return t


def _normalize_for_scan(text: str) -> str:
    """Fold the text before any prose backstop reads it.

    These scans exist to catch a memo whose narrative contradicts its declared
    fields. An author hiding a keyword behind an HTML entity or a Cyrillic A is
    doing so deliberately; normalizing costs nothing and removes the cheapest
    ways to do it. It is a backstop either way -- the authoritative claims are
    the frontmatter tokens, not this scan."""
    t = _fold(text)
    # Strip inline emphasis markers so "**F**ATAL" reads as "FATAL".
    # Emphasis markers, at both edges of a token and inside it, so "**FATAL**",
    # "__FATAL__", and "**F**ATAL" all fold to "FATAL". Note that "_" is a word
    # character in Python's \w, which is why the edge rules run first.
    t = re.sub(r"(?<!\w)[*_]{1,2}(?=[A-Za-z0-9])", "", t)
    t = re.sub(r"(?<=[A-Za-z0-9])[*_]{1,2}(?![A-Za-z0-9])", "", t)
    t = re.sub(r"(?<=[A-Za-z0-9])(?:\*\*|__|\*|_)(?=[A-Za-z0-9])", "", t)
    # "**Severity:**" -- emphasis wrapping a label INCLUDING its punctuation is
    # the most idiomatic Markdown form and the folds above miss it, because the
    # closing "**" abuts ":" rather than a letter. Drop any emphasis run that
    # sits between a non-space and a space, or vice versa.
    t = re.sub(r"(?:\*\*|__|\*|_)+(?=[:;,.\-\u2013\u2014]|\s|$)", "", t)
    t = re.sub(r"(?<=[\s:;,>|(\[])(?:\*\*|__|\*|_)+", "", t)
    t = re.sub(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^>\n]*)?>", "", t)  # <b>Severity:</b>
    # Collapse intra-word spacing used to break a keyword up ("F A T A L").
    t = re.sub(r"\b(?:[A-Za-z][ \t]){3,}[A-Za-z]\b",
               lambda m: m.group(0).replace(" ", "").replace("\t", ""), t)
    return t


RULE_STATEMENT = re.compile(
    r"(?:red-team|memo-format|sources|authority-hierarchy|canons|SKILL)\.md|"
    r"\bstops\s+delivery\b|\bthe\s+rule\s+is\b|\bthe\s+package\s+requires\b|"
    r"\brequires\s+the\s+(?:memo|report)\s+to\b",
    re.IGNORECASE,
)


# A line that MAKES a claim about this memo, whatever else it also says. A
# reference to the rulebook does not neutralize it.
OWN_CLAIM = re.compile(
    r"^\s*(?:[-*+>|#]\s*)*(?:\*\*|__)?(?:red[-\s]?team|attacks?\s+run|checks?\s+not\s+run|"
    r"citator|confidence)\b[^.\n]{0,40}?[:\-\u2013\u2014]|"
    r"\b(?:we|i|this\s+memo|this\s+draft|this\s+run|the\s+author)\b[^.\n]{0,60}?"
    r"\b(?:did\s+not|was\s+not|were\s+not|skipped|not\s+run)\b|"
    # A bare declarative opening the line: "Red team not run; the rule is ..."
    r"^\s*(?:[-*+>|#]\s*)*(?:\*\*|__)?(?:red[-\s]?team|adversarial\s+(?:pass|review))\b"
    r"[^.\n]{0,20}\b(?:not\s+run|skipped|bypassed|deferred|pending)\b",
    re.IGNORECASE,
)


def _is_rule_statement(line: str) -> bool:
    """A line describing the package's OWN rules is not a claim about this memo.

    A memo that says ``red-team.md \u00a73 provides that a "Severity: FATAL" finding
    stops delivery; none was found here`` is quoting the rulebook. Reading that
    as a FATAL finding, or as a disclosure that no citator ran, is a false
    accusation -- and it punishes exactly the authors who read the references."""
    if OWN_CLAIM.search(line):
        # "Red team not run - see `red-team.md` §1" cites the rulebook AND
        # declares a skip. Citing the rule you are breaking is not an exemption.
        return False
    return bool(RULE_STATEMENT.search(line))


def _strip_quoted(text: str) -> str:
    """Blank out inline code spans, block quotations, and double-quoted strings.

    A memo that *quotes the rule* ("a run that skips it discloses that fact ...
    in those words: 'Red team not run'") is describing the rule, not disclosing
    a skip. A memo that *discloses* a skip says it in its own voice. Scanning
    only the memo's own voice is what separates the two."""
    t = re.sub(r"`[^`\n]*`", " ", text)
    t = re.sub(r"[\"\u201c][^\"\u201d\n]{0,300}[\"\u201d]", " ", t)
    t = re.sub(r"\u2018[^\u2019\n]{0,300}\u2019", " ", t)
    # ASCII single quotes, but only when they open and close outside a word, so
    # an apostrophe in "Shepard's" is not read as a quotation mark.
    t = re.sub(r"(?<![\w])'[^'\n]{2,300}'(?![\w])", " ", t)
    return t


def check_citator(fm: dict) -> None:
    """sources.md \u00a74, enforced on tokens rather than on sentences.

    citator:         KeyCite | Shepards | NONE          (required)
    citator_date:    YYYY-MM-DD                          (required unless NONE)
    citator_signal:  none | yellow | red | other         (required unless NONE)
    citator_notes:   free text, never parsed             (optional)
    """
    raw = _strip_yaml_comment(fm.get("citator", "")).strip()
    if not raw or PLACEHOLDER.search(raw):
        return  # already reported by the required-key check
    if not _is_ascii_token(raw):
        err(f"citator must be a plain-ASCII token; found non-ASCII characters: {raw!r}")
        return
    tok = _token(raw)
    if tok not in VALID_CITATOR:
        err(
            "citator must be exactly one of KeyCite, Shepards, or NONE \u2014 nothing else, and "
            "no commentary in this field. Put every explanation, flag description, and "
            f"substitute-check narrative in citator_notes: instead. Found: {raw!r}"
        )
        return

    conf = _token(fm.get("confidence", ""))
    ran = tok != "NONE"

    if ran:
        d = _strip_yaml_comment(fm.get("citator_date", "")).strip().strip("\"'")
        parsed = None
        if ISO_DATE.match(d):
            try:
                parsed = datetime.date.fromisoformat(d)
            except ValueError:
                parsed = None
        if parsed is None:
            err(
                f"citator: {tok} requires citator_date: a real calendar date in YYYY-MM-DD "
                f"form. A citator result without the date it was run cannot be relied on. "
                f"Found: {d!r}"
            )
        else:
            try:
                today = datetime.date.today()
            except Exception:  # pragma: no cover
                today = None
            if today and parsed > today:
                err(
                    f"citator_date: {d} is in the future. A citator run cannot have happened "
                    "yet."
                )
            elif today and (today - parsed).days > 365 and conf == "HIGH":
                err(
                    f"citator_date: {d} is more than a year old and the memo claims "
                    "confidence: HIGH. A year-old citator result and no citator result are the "
                    "same fact about negative treatment since. Re-run it, or cap the confidence."
                )
            elif today and (today - parsed).days > 180:
                warn(
                    f"citator_date: {d} is more than six months old. sources.md \u00a74 treats a "
                    "stale check as ageing into a missing one: re-run it, or say in the memo how "
                    "old it is and cap the confidence accordingly."
                )
        sig = _token(fm.get("citator_signal", ""))
        if sig not in VALID_SIGNAL:
            err(
                f"citator: {tok} requires citator_signal: one of none, yellow, red, other. "
                f"Found: {fm.get('citator_signal', '')!r}"
            )
        elif sig == "RED" and conf == "HIGH":
            err(
                "citator_signal: red with confidence: HIGH. A red flag means an authority has "
                "been reversed, superseded, or overruled in relevant part. Resolve it \u2014 drop "
                "the authority, or show the flag does not reach this proposition \u2014 and grade "
                "the memo at the confidence that resolution supports."
            )
        elif sig in {"YELLOW", "OTHER"} and conf == "HIGH":
            warn(
                f"citator_signal: {sig.lower()} with confidence: HIGH. A flagged authority can "
                "still support a high-confidence answer, but the memo must say why the flag "
                "does not bite."
            )
        return

    # citator: NONE \u2014 disclosure and cap both required.
    if conf == "HIGH":
        err(
            "confidence: HIGH is not available when the citator was not run. Cap at MODERATE "
            "or below and disclose the gap (sources.md \u00a74)."
        )
    if not (fm.get("citator_notes", "") or "").strip():
        warn(
            "citator: NONE without citator_notes:. Name the sources.md \u00a73 substitutes actually "
            "performed \u2014 cited-by, vintage comparison, review check, override check \u2014 or say "
            "that none were."
        )


def check_red_team_fields(body: str, fm: dict, *, formal: bool) -> None:
    """red_team: full | compact | none, and fatal_findings: an integer."""
    raw = _strip_yaml_comment(fm.get("red_team", "")).strip()
    if raw and not PLACEHOLDER.search(raw):
        if not _is_ascii_token(raw):
            err(f"red_team must be a plain-ASCII token; found non-ASCII: {raw!r}")
        else:
            tok = _token(raw)
            if tok not in VALID_RED_TEAM:
                err(
                    "red_team must be exactly one of full, compact, or none \u2014 no commentary. "
                    f"Found: {raw!r}"
                )
            else:
                conf = _token(fm.get("confidence", ""))
                if tok == "NONE":
                    if formal:
                        err(
                            "red_team: none. A disclosed skip is honest, but it is not a pass, "
                            "and a formal deliverable does not ship without one. Run it, or "
                            "deliver this as a Mode 2 answer instead."
                        )
                    else:
                        warn(
                            "red_team: none \u2014 no adversarial pass was run. This is a warning "
                            "only because --formal was not supplied; in a formal deliverable it "
                            "blocks. The output must say so in its first line, in those words: "
                            '"Red team not run."'
                        )
                    if conf in {"HIGH", "MODERATE"}:
                        err(
                            f"confidence: {conf} is not available when the red team was not "
                            "run. Cap at LOW or UNRESOLVED."
                        )
                elif tok == "COMPACT" and formal:
                    err(
                        "red_team: compact in a formal deliverable. Mode 3 requires the full "
                        "seven-attack pass (red-team.md \u00a71)."
                    )

    # fatal_findings: an integer the author states, not a phrase the linter guesses at.
    fatal_raw = _strip_yaml_comment(fm.get("fatal_findings", "")).strip()
    if fatal_raw and not PLACEHOLDER.search(fatal_raw):
        if not _is_ascii_token(fatal_raw):
            err(f"fatal_findings must be a plain-ASCII integer; found: {fatal_raw!r}")
        elif not re.fullmatch(r"\d{1,3}", fatal_raw):
            err(
                "fatal_findings must be a plain integer (0 if the red team found none). "
                f"Found: {fatal_raw!r}"
            )
        elif int(fatal_raw) > 0:
            err(
                f"fatal_findings: {fatal_raw}. Delivery stops until every FATAL finding is "
                "corrected and the memo is re-red-teamed (red-team.md \u00a73). If the finding "
                "was already corrected, it is no longer outstanding: set fatal_findings: 0, "
                "record fatal_findings_first_pass, and reproduce the corrected finding under a "
                "heading naming it as corrected."
            )
        elif PRIOR_PASS_HEADING.search(_normalize_for_scan(body)):
            fp = _strip_yaml_comment(fm.get("fatal_findings_first_pass", "")).strip()
            # Count the FATAL findings actually reproduced under the corrected
            # heading. More of them than the first pass declared means one of
            # them is not a corrected finding, which is the only way left to
            # smuggle a live one through the fence.
            folded_body = _normalize_for_scan(body)
            # Count LINES that carry a reproduced grade, not pattern hits: an
            # earlier version incremented once per pattern per match, so a
            # single reproduced finding whose text also says "(FATAL)" counted
            # twice and blocked a correctly formatted second-pass memo.
            # Count reproduced FINDINGS -- contiguous block-quotation
            # paragraphs carrying a grade -- not grade-shaped lines. A finding
            # reproduced unedited often names FATAL more than once (its own
            # Disposition line does), and counting lines blocked the shape
            # red-team.md \u00a73 prescribes.
            grade_lines = set()
            for pat in PROSE_FATAL:
                for m in pat.finditer(folded_body):
                    if _in_reproduced_prior_finding(folded_body, m.start()):
                        grade_lines.add(folded_body.count("\n", 0, m.start()))
            body_lines = folded_body.splitlines()
            blocks = set()
            for ln in sorted(grade_lines):
                top = ln
                while top > 0 and re.match(r"^[ \t]*>", body_lines[top - 1] or ""):
                    top -= 1
                blocks.add(top)
            reproduced = len(blocks)
            # Arithmetic alone is not verification; the author must explain the
            # correction and second-pass result outside the historical quote.
            # The required verbatim reproduction describes the FIRST pass. Its
            # original words may say "unresolved" or "not fixed" even after the
            # author has corrected the defect. Current status belongs outside
            # that quotation; matching historical adjectives cannot verify it.
            if re.fullmatch(r"\d{1,3}", fp) and reproduced and reproduced < int(fp):
                warn(
                    f"fatal_findings_first_pass declares {fp} but only {reproduced} corrected "
                    "finding(s) are reproduced. Reproduce each one, unedited, so the reader "
                    "can see what the first pass caught."
                )
            if re.fullmatch(r"\d{1,3}", fp) and reproduced > int(fp):
                err(
                    f"The corrected-finding block reproduces {reproduced} FATAL finding(s) but "
                    f"fatal_findings_first_pass declares {fp}. A finding under that heading is "
                    "asserted to be already corrected; if one of them is not, it is outstanding "
                    "and delivery stops."
                )
            if reproduced and not re.fullmatch(r"\d{1,3}", fp):
                err(
                    "The report reproduces a corrected finding but fatal_findings_first_pass "
                    "is missing or is not an integer. A clean report on the second pass is not "
                    "the same artifact as a clean report on the first, and the reader is "
                    "entitled to know which one they are reading (memo-format.md \u00a74)."
                )


MIXED_SCRIPT_LABEL = re.compile(
    r"^[ \t]*(?:[-*+>|]\s*)*(?:\*\*|__)?(?:Severity|Grade|Disposition)(?:\*\*|__)?"
    r"[ \t]*[:\-\u2013\u2014|][ \t]*(?:\*\*|__)?([^\s|*_]{2,20})",
    re.IGNORECASE | re.MULTILINE,
)


def check_mixed_script_labels(body: str) -> None:
    """A severity value that mixes scripts is either a copy-paste accident or an
    attempt to hide a grade from a text scan. Either way the author should see
    it. Folding catches the common homoglyph families; this catches the rest by
    shape rather than by table, which is the only way to cover scripts nobody
    thought to list."""
    for m in MIXED_SCRIPT_LABEL.finditer(body):
        val = m.group(1)
        letters = [c for c in val if c.isalpha()]
        if not letters:
            continue
        if any(ord(c) > 127 for c in letters) and any(ord(c) < 128 for c in letters):
            err(
                f"Severity value {val!r} mixes ASCII and non-ASCII letters. Write severity "
                "grades in plain ASCII; a mixed-script grade cannot be read reliably by "
                "anyone, including the reader."
            )


# A more generous set for the REQUIRED disclosure only. Refusing to recognize an
# honest disclosure because it was worded differently is the worse error of the
# two: it accuses the author of hiding what they just said.
DISCLOSURE_GENEROUS = re.compile(
    r"\b(?:no|none|nothing|neither|nor|not|never|without|lack\w*|absent|unable)\b"
    r"[^.\n]{0,70}?(?:shepardi[sz]|keycit|key\s?cit|shepard's|citator|westlaw|lexis)|"
    r"(?:shepardi[sz]|keycit|key\s?cit|citator)[^.\n]{0,60}?"
    r"\b(?:not\s+run|never\s+run|was\s+not|were\s+not|unavailable|skipped)\b",
    re.IGNORECASE,
)


def _matching_line(text: str, *patterns, raw: str | None = None) -> str | None:
    """The first line a pattern matches, skipping rule statements. Returns the
    line so the caller can judge its scope; None when nothing matches."""
    folded = _normalize_for_scan(text)
    raw_lines = _normalize_for_scan(raw).splitlines() if raw is not None else None
    for i, line in enumerate(folded.splitlines()):
        probe = raw_lines[i] if raw_lines is not None and i < len(raw_lines) else line
        if _is_rule_statement(probe) or _is_rule_statement(line):
            continue
        if any(p.search(line) for p in patterns):
            return line
    return None


def _scan_lines(text: str, *patterns, raw: str | None = None) -> bool:
    """Run the patterns line by line, skipping lines that state the package's own
    rules rather than making a claim about this memo.

    ``raw`` is the same text before quotation stripping. The rule test keys on
    backticked file names (``red-team.md``), and stripping runs first -- so
    testing the stripped line looked for a name that had just been blanked, and
    the exemption never fired for its main case."""
    folded = _normalize_for_scan(text)
    raw_lines = _normalize_for_scan(raw).splitlines() if raw is not None else None
    for i, line in enumerate(folded.splitlines()):
        probe = raw_lines[i] if raw_lines is not None and i < len(raw_lines) else line
        if _is_rule_statement(probe) or _is_rule_statement(line):
            continue
        if any(p.search(line) for p in patterns):
            return True
    return False


def check_prose_mismatch(body: str, fm: dict, frontmatter_raw: str = "", *,
                         formal: bool = False, found: dict | None = None) -> None:
    """The fields decide; the prose is read only to catch a disagreement between
    the two. A mismatch is reported in whichever direction it points, and it is
    never the reason a memo passes.

    The frontmatter's own text is scanned too, so a YAML comment that
    contradicts the token it annotates (``citator: KeyCite  # not actually
    run``) is caught rather than silently stripped."""
    # Two different texts, on purpose:
    #   body_only  -- for the REQUIRED disclosure. "citator: NONE" in the
    #                 frontmatter is the field, not the disclosure; letting it
    #                 satisfy its own body-disclosure test made that check dead
    #                 code and silently voided the rule it enforces.
    #   with_fm    -- for the MISMATCH, so a YAML comment that contradicts the
    #                 token it annotates is still caught.
    body_only = body
    # Strip the free-text *_notes fields from the frontmatter before scanning.
    # README, sources.md \u00a74, and check_citator's own docstring all promise
    # citator_notes is never parsed -- and scanning it hard-blocked the scoped
    # disclosure the error message tells the author to write there.
    fm_scan = "\n".join(
        ln for ln in (frontmatter_raw or "").splitlines()
        if not re.match(r"^\s*\w*_?notes\s*:", ln, re.IGNORECASE)
    )
    with_fm = fm_scan + "\n" + body
    cit = _token(fm.get("citator", ""))
    if cit in VALID_CITATOR:
        # REQUIRED disclosure: the memo's own text, quotation marks included --
        # a memo that writes the prescribed words in quotes has still written
        # them -- but NOT the frontmatter, which is the claim being disclosed.
        discloses = _scan_lines(body_only, PROSE_CITATOR_NOT_RUN, DISCLOSURE_GENEROUS)
        # MISMATCH: the memo's own voice only, plus the frontmatter's comments,
        # so quoting the rule is not mistaken for making the claim.
        says_not_run = _scan_lines(_strip_quoted(with_fm), PROSE_CITATOR_NOT_RUN, raw=with_fm)
        if cit == "NONE" and formal:
            if found is None:
                found = check_sections(body_only)
            for section in ("Short Answer", "Retrieval Record"):
                if section in found and not _scan_lines(
                    section_text(body_only, found, section),
                    PROSE_CITATOR_NOT_RUN, DISCLOSURE_GENEROUS,
                ):
                    err(
                        f"citator: NONE, but the {section} does not disclose it. "
                        "State 'not Shepardized or KeyCited' in both the Short Answer "
                        "and the Retrieval Record (sources.md \u00a74). A disclosure "
                        "elsewhere does not inform a reader who stops at the answer."
                    )
        elif cit == "NONE" and not discloses:
            err(
                "citator: NONE, but the memo body never discloses it. The disclosure belongs "
                "where the reader decides \u2014 in the Short Answer and the Retrieval Record, in "
                "words (\u2018not Shepardized or KeyCited\u2019), not only in the frontmatter "
                "(sources.md \u00a74)."
            )
        hit_line = _matching_line(
            _strip_quoted(with_fm), PROSE_CITATOR_NOT_RUN, raw=with_fm
        )
        # Judge the scope cue on the MATCHING LINE, not the whole memo: any
        # long document contains "because" or "only" somewhere.
        scoped = bool(hit_line) and bool(re.search(
            r"\b(?:the\s+(?:ordinance|rule|regulation|third|second|other|remaining)|"
            r"rows?\s+\d|authority\s+\d|one\s+of\s+the|administrative\s+(?:rule|code)|"
            r"\bexcept\b|\bonly\b)",
            hit_line, re.IGNORECASE,
        ))
        if cit != "NONE" and says_not_run:
            # A SCOPED statement -- "the ordinance was not Shepardized, the two
            # opinions were" -- is more precise than the field can be, not a
            # contradiction of it. Warn so the author records the scope in
            # citator_notes; do not block, or the honest sentence gets deleted.
            (warn if scoped else (err if formal else warn))(
                f"MISMATCH: citator: {cit.title()} declares a citator result, but the body says "
                "an authority was not Shepardized or KeyCited. If the check really was scoped "
                "to some authorities and not others, say so in citator_notes and make the "
                "sentence name what it covers. If it was not run at all, the field is wrong."
            )

    rt = _token(fm.get("red_team", ""))
    if rt in VALID_RED_TEAM:
        discloses_skip = _scan_lines(body_only, PROSE_RED_TEAM_SKIPPED)
        says_skipped = _scan_lines(_strip_quoted(with_fm), PROSE_RED_TEAM_SKIPPED, raw=with_fm)
        if rt == "NONE" and not discloses_skip:
            err(
                "red_team: none, but the body never says so. The skip is disclosed in the "
                'first line of the output, in those words: "Red team not run."'
            )
        if rt != "NONE" and says_skipped:
            (err if formal else warn)(
                f"MISMATCH: red_team: {rt.lower()} declares a pass was run, but the body "
                "describes a pass as skipped or bypassed. If some checks inside the attacks "
                "did not run, that is what the report's 'Checks not run' line is for. If the "
                "pass itself did not run, the field is wrong."
            )

    # A reader looks at the Short Answer and the red team's grade line, not at
    # the frontmatter. A document whose visible grade contradicts its declared
    # one is making two claims, and the declared one is what the caps apply to.
    declared_conf = _token(fm.get("confidence", ""))
    if declared_conf in VALID_CONFIDENCE:
        # Declarative forms only. "that would drop the confidence to LOW" is a
        # conditional -- memo-format.md's Lens 3 REQUIRES that sentence -- and
        # reading it as the memo's own grade blocked the prescribed shape.
        # Not _strip_quoted: "The red team graded this \"HIGH confidence\" and we
        # adopt that grade" states the grade. Rule-statement lines are skipped
        # instead, which is the distinction that actually matters.
        scan_conf = "\n".join(
            ln for ln in _normalize_for_scan(body_only).splitlines()
            if not _is_rule_statement(ln)
        )
        # Blank only the conditional clause -- from the conditional word to the
        # next clause boundary -- not the whole sentence. Blanking the sentence
        # let "If the Register is as retrieved, and it is, this is a HIGH
        # confidence conclusion" hide a real grade behind the word "if".
        scan_conf = re.sub(
            r"\b(?:would|could|might|unless|drop\w*\s+to|raise\w*\s+to)\b[^.,;\n]*",
            " ", scan_conf, flags=re.IGNORECASE,
        )
        scan_conf = re.sub(r"\bif\b[^,.;\n]*[,;]?", " ", scan_conf, flags=re.IGNORECASE)
        visible = {
            (m.group(1) or m.group(2)).upper()
            for m in re.finditer(
                r"\bconfidence\s*(?:[:=\-\u2013\u2014]|\bis\b|\bgrade\s+is\b|\brated\b)?\s*"
                r"\b(HIGH|MODERATE|LOW|UNRESOLVED)\b"
                r"|\b(HIGH|MODERATE|LOW)[-\s]confidence\b",
                scan_conf, re.IGNORECASE,
            )
        }
        conflicting = sorted(v for v in visible if v != declared_conf)
        if conflicting:
            err(
                f"MISMATCH: confidence: {declared_conf} in the frontmatter, but the memo states "
                f"{', '.join(conflicting)} where the reader will see it. The stated grade and "
                "the declared grade must be the same word."
            )

    fatal_raw = (fm.get("fatal_findings", "") or "").strip()
    # S2: a FATAL finding must not be hidden by quoting it. The red team report
    # is routinely reproduced as a block quotation or a fenced block -- the
    # format memo-format.md requires -- so the FATAL scan reads the memo with
    # only inline emphasis folded, not with quoted spans blanked. Legend and
    # negation handling (FATAL_LEGEND / FATAL_NEGATED) is what keeps a quoted
    # *rule* from reading as a quoted *finding*.
    if re.fullmatch(r"\d{1,3}", fatal_raw) and int(fatal_raw) == 0 and _prose_has_fatal(
        _normalize_for_scan(with_fm)
    ):
        err(
            "MISMATCH: fatal_findings: 0, but the memo records what reads as a FATAL finding. "
            "Either grade it and stop delivery, or re-label it if it is not FATAL."
        )


def check_sections(body: str) -> dict:
    found = {}
    for name in REQUIRED_SECTIONS:
        pattern = re.compile(r"^#{1,3}\s*.*" + re.escape(name), re.MULTILINE | re.IGNORECASE)
        m = pattern.search(body)
        if not m:
            err(f"Missing required section: {name}")
        else:
            found[name] = m.start()
    return found


def section_text(body: str, found: dict, name: str) -> str:
    if name not in found:
        return ""
    start = found[name]
    later = [pos for pos in found.values() if pos > start]
    end = min(later) if later else len(body)
    return body[start:end]


def check_quotes(body: str, found: dict | None = None) -> None:
    """Every block quote must be followed within a few lines by a pincite.

    Except inside the Red Team Report and any corrected-finding block: a
    reproduced red-team finding is a quotation of the *report*, not of law, and
    has no pincite to give. Demanding one there blocked the shape
    memo-format.md \u00a74 prescribes."""
    exempt_from, exempt_to = _report_span(body, found)
    lines = body.splitlines()
    i = 0
    quote_count = 0
    unpincited = []
    while i < len(lines):
        if lines[i].lstrip().startswith(">"):
            start_line = i
            while i < len(lines) and (
                lines[i].lstrip().startswith(">") or not lines[i].strip()
            ):
                if lines[i].strip() and not lines[i].lstrip().startswith(">"):
                    break
                i += 1
            quote_count += 1
            block = "\n".join(lines[start_line:i])
            trailing = "\n".join(lines[i : i + 4])
            block_off = sum(len(x) + 1 for x in lines[:start_line])
            in_report = exempt_from <= block_off < exempt_to
            if not in_report and not PINCITE.search(block) and not PINCITE.search(trailing):
                unpincited.append(start_line + 1)
        else:
            i += 1
    if quote_count == 0:
        err(
            "No block quotations found. Every proposition of Wisconsin law requires a "
            "verbatim quote of the operative language."
        )
    else:
        note(f"{quote_count} block quotation(s) found.")
    for ln in unpincited:
        err(f"Block quote at line {ln} has no pincite within 4 lines.")


def _report_span(body: str, found: dict | None):
    """Character range of the Red Team Report section, plus any corrected-finding
    block, within which a block quotation needs no pincite."""
    if not found or "Red Team Report" not in found:
        m = PRIOR_PASS_HEADING.search(body)
        if not m:
            return len(body), len(body)
        # The corrected-finding block ends at the next heading. Running it to
        # the end of the file exempted every later block quote in the memo.
        nxt = ANY_HEADING.search(body, m.end())
        return m.start(), (nxt.start() if nxt else len(body))
    start = found["Red Team Report"]
    # The report ends at the next heading of its own level or higher, whether or
    # not that heading is a required section. Bounding it only by required
    # headings let a "## Further Analysis" placed after the report inherit the
    # exemption. A deeper heading inside the report ("### Corrected on the
    # second pass") does not end it.
    heading = re.match(r"[ \t]*(#{1,6})", body[start:])
    level = len(heading.group(1)) if heading else 3
    peer = re.compile(r"^[ \t]*#{1,%d}(?!#)[ \t]*\S" % level, re.MULTILINE)
    nxt = peer.search(body, start + (heading.end() if heading else 1))
    later = [p for p in found.values() if p > start] + ([nxt.start()] if nxt else [])
    return start, (min(later) if later else len(body))


def check_table(body: str, found: dict) -> None:
    tbl = section_text(body, found, "Authority Table")
    if not tbl:
        return
    rows = [
        ln
        for ln in tbl.splitlines()
        if ln.strip().startswith("|") and not re.match(r"^\s*\|[\s\-:|]+\|\s*$", ln)
    ]
    if len(rows) < 2:
        err("Authority Table has no data rows.")
        return
    data_rows = rows[1:]
    real = 0
    for idx, row in enumerate(data_rows, start=1):
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if not any(cells):
            continue
        if all(c == "" for c in cells):
            continue
        real += 1
        if PLACEHOLDER.search(row):
            err(f"Authority Table row {idx} still contains template placeholders.")
            continue
        # Evidence is the last column; a filled row with empty evidence is a contradiction.
        if len(cells) >= 9:
            evidence = cells[8]
            copy_cell = cells[6]
            vintage = cells[5]
            if not evidence:
                err(
                    f"Authority Table row {idx}: empty Evidence cell. "
                    "A row without a file + locator cannot be presented as verified."
                )
            if not copy_cell:
                warn(f"Authority Table row {idx}: no source copy path recorded.")
            if not vintage:
                warn(f"Authority Table row {idx}: Vintage OK column is blank.")
        else:
            warn(
                f"Authority Table row {idx} has {len(cells)} columns; expected 9 "
                "(see memo-format.md §3)."
            )
    if real == 0:
        err("Authority Table contains no filled rows.")
    else:
        note(f"{real} authority row(s).")


def check_red_team(body: str, found: dict) -> None:
    rt = section_text(body, found, "Red Team Report")
    if not rt:
        return
    stripped = re.sub(r"^#{1,3}.*$", "", rt, flags=re.MULTILINE).strip()
    if len(stripped) < 200:
        err(
            "Red Team Report is empty or near-empty. The pass is mandatory; a run that "
            "skipped it must say so in the first line of the output."
        )
    if not re.search(r"attacks?\s+(?:\w+\s+){0,2}run|run\s+(?:all\s+)?(?:\w+\s+){0,2}attacks?|attacks?\s+run", rt, re.IGNORECASE):
        err("Red Team Report does not record which attacks were run.")
    if not re.search(r"confidence", rt, re.IGNORECASE):
        err("Red Team Report does not assign a confidence grade.")
    if not re.search(r"contrary reading", rt, re.IGNORECASE):
        warn(
            "Red Team Report has no 'best contrary reading' subsection (Attack 4). "
            "It is preserved even when answered."
        )
    # FATAL findings are checked at document scope by check_prose_mismatch()
    # against the fatal_findings field; nothing to do here.


def _applied_markers(line: str, rule_line: bool = False) -> int:
    """Count [UNVERIFIED] tokens on a line that the memo APPLIES.

    A token is exempt only when the sentence is about the marker itself, which
    means the token is used as a noun: the word "marker(s)" or "remain(s)"
    follows it directly. Then either a negation word shortly before it ("no
    [UNVERIFIED] marker remains") or a negation later in the same sentence
    ("the [UNVERIFIED] marker, now obsolete, no longer applies"; the tally form
    "[UNVERIFIED] markers: none") exempts it. A token followed by anything
    else is an applied marker, whatever the rest of the sentence says: "the
    cite is [UNVERIFIED]; markers are not optional" and "the date is
    [UNVERIFIED] and the marker is not removed" both count. The negation before
    the token may not cross a clause boundary ("was not retrieved; [UNVERIFIED]
    marker applies" counts).

    rule_line says the line cites the package's own rules (_is_rule_statement).
    On such a line a noun use of the token ("memo-format.md requires an
    [UNVERIFIED] marker on every unretrieved cite") is exempt without a
    negation, but an applied token on the same line still counts: naming a
    rule file beside a live marker does not clear the marker."""
    count = 0
    for m in UNVERIFIED.finditer(line):
        before = line[max(0, m.start() - 60):m.start()]
        after = line[m.end():]
        noun = re.match(r"\s*(?:markers?|remains?)\b", after, re.IGNORECASE)
        says_none = noun and re.search(
            r"\b(?:no|none|zero|not|never|without)\b[^.,;:!?\n]{0,40}$", before, re.IGNORECASE
        )
        says_cleared = noun and re.match(
            r"\s*(?:markers?|remains?)\b(?:\s+(?:markers?|remains?)\b)?(?:\s*:)?[^.;:!?\n]{0,60}"
            r"\b(?:no|none|not|never)\b",
            after, re.IGNORECASE,
        )
        if not (says_none or says_cleared or (rule_line and noun)):
            count += 1
    return count


def check_markers(body: str, fm: dict) -> None:
    # Count markers the memo APPLIES, not sentences about the marker. A red
    # team explaining "HIGH because no [UNVERIFIED] marker remains" is stating
    # the rule; counting it blocked the memo on the sentence that justified it.
    n_unver = sum(
        _applied_markers(line, _is_rule_statement(line))
        for line in body.splitlines()
    )
    if n_unver:
        warn(
            f"{n_unver} [UNVERIFIED] marker(s). Confirm the Short Answer discloses any "
            "conclusion that leans on unretrieved authority."
        )
    if FILL_IN.search(body):
        note("[FILL-IN] present — route to the requester before delivery is final.")
    conf = _token(fm.get("confidence", ""))
    if conf == "HIGH" and n_unver:
        err("confidence: HIGH is not available while [UNVERIFIED] markers remain.")
    if re.search(r"\bem dash\b", body) or "\u2014" in body:
        note(
            "Em dashes present. Some default styles ban them in filings; in a memo this is the "
            "requester's call."
        )


UNSAFE_PATH = re.compile(
    r"""^(?:
          [A-Za-z]:            # drive-letter absolute, C:\...
        | \\\\               # UNC, \\server\share
        | \\                 # single leading backslash = drive-relative on Windows
        | /                    # POSIX absolute
        | ~                    # home expansion
    )""",
    re.VERBOSE,
)


# A backticked token is treated as a filesystem path if it carries a separator or
# an obviously path-leading prefix. Statute cites (`§ 809.23(3)`) and bare file
# names never match; `references/canons.md` and `~/x` both do.
PATH_LIKE = re.compile(r"""^(?:[A-Za-z]:|~|\\\\|/|\$|%)|[/\\]""", re.VERBOSE)


def _is_unsafe_literal(p: str) -> str | None:
    """Reject a cited path on its text alone, before touching the filesystem."""
    if UNSAFE_PATH.match(p):
        return "absolute, drive-relative, UNC, or home-relative path"
    if "\x00" in p:
        return "null byte in path"
    parts = re.split(r"[\\/]+", p)
    if ".." in parts:
        return "parent-directory traversal (..)"
    return None


# Locations that are never a legitimate source citation and never a legitimate
# thing to have opened. A path landing here is an error, not a style warning.
HOSTILE_LOCATION = re.compile(
    r"^(?:(?:/private)?/(?:etc|proc|sys|dev|root|boot)\b"
    r"|/var/(?:log|lib|run|spool)\b"
    r"|/(?:home|Users)/[^/]+/(?:\.[^/]+|Library/(?:Keychains|Application[ _]Support))"
    r"|/Library/(?:Keychains|Application[ _]Support)"
    r"|~/\.[^/]+"
    r"|[A-Za-z]:[\\/](?:Windows|Program Files|ProgramData|Users[\\/][^\\/]+[\\/]AppData)\b"
    r"|\\\\"
    r"|//[^/]+/)",
    re.IGNORECASE,
)
SECRETY = re.compile(
    r"(?:^|[\\/])(?:\.ssh|\.aws|\.gnupg|\.env|id_[rd]sa|id_ecdsa|id_ed25519|shadow|passwd|"
    r"credentials?|secrets?|\.netrc|\.pgpass|known_hosts|token|api[_-]?key|"
    r"master\.passwd|[^\\/]*\.(?:key|pem|p12|pfx|keychain(?:-db)?)|TCC\.db)(?:$|[\\/.])",
    re.IGNORECASE,
)
# Ellipsis placeholders and short glyphs that are not paths at all.
PROSE_NOT_PATH = re.compile(r"\.\.\.|\u2026|^/s/$|^/$|^~$|^[A-Za-z]:$")
# A path rooted in an environment variable rather than a literal separator.
ENV_PREFIXED = re.compile(
    r"^(?:\$\{?[A-Za-z_][A-Za-z0-9_]*\}?|%[A-Za-z_][A-Za-z0-9_]*%)[\\/]", re.IGNORECASE
)


def _normalize_path_candidate(t: str) -> str:
    """Fold a candidate before it is judged.

    Percent-encoding, fullwidth separators, zero-width characters, and doubled
    separators are all ways to spell the same path while dodging a literal
    test. Judge the folded form; report the original."""
    x = _fold(t)
    for _ in range(3):
        y = urllib.parse.unquote(x)
        if y == x:
            break
        x = y
    x = x.replace("\uff0f", "/").replace("\u2044", "/").replace("\u2215", "/")
    x = x.replace("\uff3c", "\\")
    return x


SAFE_SCHEME = re.compile(r"^(?:https?|ftp|mailto)://|^(?:mailto:|www\.)", re.IGNORECASE)
ANY_SCHEME = re.compile(r"^([A-Za-z][A-Za-z0-9+.-]*)://(.*)$")


def _looks_like_url(t: str) -> bool:
    """Only web schemes are exempt.

    A custom scheme is a wrapper, not a safety property: "vscode://file/etc/shadow"
    and "app://../../etc/passwd" name filesystem paths. Anything that is not
    http(s)/ftp/mailto is unwrapped by the caller and screened as a path."""
    return bool(SAFE_SCHEME.match(t))


def _is_prose_not_path(t: str) -> bool:
    if PROSE_NOT_PATH.search(t):
        return True
    # A bare "/s/" e-signature, a lone slash, or anything with no path body.
    if len(t.strip("/~\\")) < 2:
        return True
    # A span with internal whitespace is a path only if its last segment looks
    # like a filename. That keeps '/s/ Hon. Jane Doe, Circuit Judge' out while
    # keeping 'sources/statutes/Wis-Stat-809.23 (2023-24).md' in.
    if re.search(r"\s", t):
        last = re.split(r"[\\/]", t.rstrip("\\/"))[-1]
        if not re.search(r"\.[A-Za-z0-9]{1,5}$", last):
            return True
    return False


def _is_hostile_literal(t: str, reason: str) -> bool:
    """An error, as opposed to a style warning. Judged on the folded form."""
    if "traversal" in reason or "null byte" in reason:
        return True
    x = _normalize_path_candidate(t)
    # Collapse repeated separators, except a leading "//" which is itself a UNC
    # spelling and is handled by HOSTILE_LOCATION.
    # Normalize separators to "/", collapsing interior runs but preserving
    # whether the path STARTED with two or more of them -- that leading run is
    # the UNC marker and is the whole point of the distinction. An earlier
    # version rebuilt the string with an unconditional "//" prefix, which made
    # every absolute path read as UNC and errored on every legitimate retrieval
    # transcript. The WARN tier existed only in the documentation.
    was_unc = bool(re.match(r"^[\\/]{2,}", x))
    flat = re.sub(r"[\\/]+", "/", x)
    body = ("//" + flat.lstrip("/")) if was_unc else flat
    return bool(HOSTILE_LOCATION.match(body) or SECRETY.search(body))


def check_sources(body: str, frontmatter_raw: str, sources_dir: str | None, *,
                  formal: bool) -> None:
    """Verify every cited `sources/...` path.

    Fails CLOSED. In formal-deliverable mode --sources is required, every cited
    path must be literally safe, and every candidate must resolve to a real file
    that stays inside the authorized root even after symlinks are followed.
    """
    # ------------------------------------------------------------------
    # Path screen. Two tiers, because not every absolute path in a memo is
    # hostile: a Retrieval Record that shows the command actually run is
    # legitimate and useful, while a cited *source* outside the archive, a
    # traversal, or a system or credential path never is.
    #
    #   ERROR  traversal, UNC, null byte, or a system/credential location
    #   WARN   any other absolute, drive-relative, or home-relative path
    #
    # Candidates are gathered from every shape a path can take in Markdown --
    # backticks (including spans broken across a line), link and image targets,
    # reference-style link definitions, quoted spans, table cells, frontmatter
    # values, and bare prose tokens -- because a screen that only reads one
    # shape is a screen you get past by using another.
    # ------------------------------------------------------------------
    scan = frontmatter_raw + "\n" + body
    # Join *inline* backtick spans broken across a newline. Fenced blocks are
    # protected first so a pair of ``` fences is not read as one giant span.
    fences: list[str] = []

    def _stash(m: "re.Match[str]") -> str:
        fences.append(m.group(0))
        return f"\x00FENCE{len(fences) - 1}\x00"

    protected = re.sub(r"^[ \t]*(?:```|~~~).*?^[ \t]*(?:```|~~~)[ \t]*$", _stash, scan,
                       flags=re.DOTALL | re.MULTILINE)
    joined = re.sub(r"`([^`\x00]{1,400}?)`",
                    lambda m: "`" + re.sub(r"\s*\n\s*", "", m.group(1)) + "`",
                    protected, flags=re.DOTALL)
    for i, blk in enumerate(fences):
        joined = joined.replace(f"\x00FENCE{i}\x00", blk)

    candidates = set()
    # file: URLs are filesystem paths wearing a scheme.
    candidates.update(
        "/" + m.lstrip("/")
        for m in re.findall(r"file:/{0,3}([^\s`\"'<>|)\]]{2,})", joined, re.IGNORECASE)
    )
    # Backticked spans.
    candidates.update(m.strip() for m in re.findall(r"`([^`\n]{2,})`", joined))
    # Markdown inline link / image targets and reference-style definitions.
    candidates.update(m.strip() for m in re.findall(r"\]\(\s*<?([^)\s>]{2,})\s*>?\)", joined))
    candidates.update(m.strip() for m in re.findall(r"^\s*\[[^\]]+\]:\s*<?(\S{2,})>?\s*$",
                                                    joined, re.MULTILINE))
    # Quoted spans.
    candidates.update(
        m.strip()
        for m in re.findall(r"[\"\u201c\u2018']([^\"\u201d\u2019'\n]{2,})[\"\u201d\u2019']", joined)
    )
    # Table cells.
    for row in re.findall(r"^\s*\|.*\|\s*$", joined, re.MULTILINE):
        candidates.update(c.strip().strip("`") for c in row.strip().strip("|").split("|"))
    # Bare prose tokens. URLs are blanked first so "https://host/path" does not
    # surface as the POSIX-absolute token "//host/path".
    # Unwrap non-web schemes first: "vscode://file/etc/shadow" is a path in a
    # wrapper, and blanking every scheme:// token before harvesting deleted it.
    unwrapped = re.sub(
        r"(?<![A-Za-z0-9+.\-/])(?!(?:https?|ftp|mailto)://)[A-Za-z][A-Za-z0-9+.-]*://(\S+)",
        lambda m: " " + (m.group(1) if m.group(1).startswith(("/", "~", "\\")) else "/" + m.group(1)),
        joined,
    )
    deurled = re.sub(r"[A-Za-z][A-Za-z0-9+.-]*://\S+", " ", unwrapped)
    deurled = re.sub(r"\bwww\.\S+", " ", deurled)
    # Code-span and quote delimiters are *delimiters*, not boundaries a path can
    # hide behind: blank them so the harvester below sees the path that follows.
    # An earlier version used them as negative lookbehind, which meant
    # "`/etc/shadow was read`" produced no candidate at all.
    deurled = re.sub(r"[`\"\u201c\u201d\u2018\u2019]", " ", deurled)
    # Markdown emphasis wrapped around a path ( _/etc/shadow_ , */etc/shadow* )
    # must not hide its leading separator behind a word character.
    deurled = re.sub(r"(?:^|(?<=\s))[_*]{1,2}(?=[/~\\]|[A-Za-z]:[\\/])", " ", deurled)
    deurled = re.sub(r"(?<=[^\s_*])[_*]{1,2}(?=\s|$)", " ", deurled)
    bare = (r"(?<![\w`\"'~.])"
            r"((?:[A-Za-z]:[\\/]|~[\\/]|\\|/|\$\{?[A-Za-z_][A-Za-z0-9_]*\}?[\\/]"
            r"|%[A-Za-z_][A-Za-z0-9_]*%[\\/])[^\s`\"'<>|]{2,})")
    # "/Library/Application Support/..." -- one of the few real paths with a
    # space in it. Join it back up so the harvester sees the whole thing.
    deurled = re.sub(r"(/(?:Library|Users/[^/\s]+/Library)/Application) (Support/)",
                     r"\1_\2", deurled)
    for text in (deurled, _normalize_path_candidate(deurled)):
        # The folded pass is what finds a path spelled with entities, percent
        # encoding, or a fullwidth solidus in plain prose, where no ASCII
        # separator exists for the raw pass to anchor on.
        candidates.update(m.strip().rstrip(".,;:)_*") for m in re.findall(bare, text))
    # Relative traversal anywhere, in or out of backticks. This is the shape the
    # bare-token rule above cannot see, because it has no leading separator.
    candidates.update(
        m.strip().rstrip(".,;:)")
        for m in re.findall(r"(?<![\w])((?:\.\.[\\/]|[\w.-]+[\\/]\.\.[\\/])[^\s`\"'<>|]{1,})",
                            deurled)
    )

    # A multi-word span may be a path followed by prose ("`/etc/shadow was
    # read`"). Screen its leading token as well as the whole span.
    # The safety screen also inspects the first word of a path-shaped cell.
    # Keep those fragments out of existence checks: spaces are valid in source
    # filenames, including the names prescribed by sources.md.
    source_candidates = candidates.copy()
    for t in list(candidates):
        if t and re.search(r"\s", t):
            head = t.split()[0].rstrip(".,;:)")
            if head:
                candidates.add(head)

    # Unwrap non-web schemes so the path inside is screened.
    for t in list(candidates):
        m = ANY_SCHEME.match(t or "")
        if m and not SAFE_SCHEME.match(t):
            inner = m.group(2)
            candidates.add(inner if inner.startswith(("/", "~", "\\")) else "/" + inner)

    for t in sorted(c for c in candidates if c):
        if _looks_like_url(t) or _is_prose_not_path(t):
            continue
        # Judge the folded spelling (percent-decoded, unicode separators mapped
        # to ASCII), but report the original so the author can find it.
        norm = _normalize_path_candidate(t).replace("Application_Support", "Application Support")
        if not PATH_LIKE.search(norm):
            continue
        reason = _is_unsafe_literal(norm)
        if not reason:
            # A path with no leading separator is not "safe" merely because it
            # is relative: "$HOME/.ssh/id_rsa" and "%APPDATA%/creds" name a
            # credential file just as plainly. Consult the sensitive-name test
            # before letting one through.
            if ENV_PREFIXED.match(norm) or SECRETY.search(norm):
                err(
                    "Sensitive path cited in the memo (credential or configuration "
                    f"location): {t}"
                )
            continue
        if _is_hostile_literal(norm, reason):
            why = reason
            if "traversal" not in reason and "null byte" not in reason:
                why = "system, credential, or network location"
            err(f"Unsafe path cited in the memo ({why}): {t}")
        else:
            warn(
                f"Absolute or home-relative path in the memo ({reason}): {t} \u2014 source "
                "citations are relative to the archive root (sources.md \u00a78). Fine in a "
                "transcript of a command actually run; never as a source citation."
            )

    # Archive paths. Case-insensitive prefix: on a case-insensitive filesystem
    # `Sources/x` and `sources/x` are the same file, so a capitalized citation
    # must not skip the existence and containment checks.
    # Archive citations, from the SAME candidate set as the hostile-path screen.
    # Reading only backticked spans meant a memo citing sources/... unwrapped in
    # its Authority Table was told "No `sources/...` paths referenced" -- a false
    # statement about a memo whose paths are right there.
    paths = [m.group(0).lstrip("`") for m in re.finditer(r"`(?i:sources)/[^`\n]+(?=`)", joined)]
    paths += [
        c for c in source_candidates
        if re.match(r"^(?i:sources)/", c or "") and c not in paths
    ]
    # A reference to a directory ("no file in `sources/opinions/` corresponds to
    # the 2019 disposition") is an Attack 1 Evidence line, not a cited file.
    # Blocking a formal deliverable for it punishes the discipline red-team.md
    # asks for.
    paths = [p for p in paths if not _is_prose_not_path(p) and not p.rstrip().endswith("/")]

    if not paths:
        if formal:
            err("No `sources/...` paths referenced. A formal deliverable must cite "
                "its retrieved sources so retrieval can be audited.")
        else:
            warn("No `sources/...` paths referenced. Retrieval cannot be audited.")
        return

    note(f"{len(set(paths))} distinct source path(s) referenced.")

    # Literal rejection happens for every run, with or without --sources, because
    # a malicious path in a delivered memo is a defect even when unresolvable here.
    unsafe = False
    for p in sorted(set(paths)):
        reason = _is_unsafe_literal(p.split("/", 1)[1] if "/" in p else p)
        if reason:
            err(f"Unsafe source path rejected ({reason}): {p}")
            unsafe = True
    if unsafe:
        return

    if not sources_dir:
        if formal:
            err("--sources is required in formal-deliverable mode. Cited sources "
                "cannot be confirmed to exist without it.")
        else:
            note("--sources not supplied; existence of cited sources not checked.")
        return

    try:
        root = os.path.realpath(sources_dir)
    except OSError as exc:
        err(f"cannot resolve --sources root: {exc}")
        return
    if not os.path.isdir(root):
        err(f"--sources is not a directory: {sources_dir}")
        return

    for p in sorted(set(paths)):
        rel = p.split("/", 1)[1] if "/" in p else p
        candidate = os.path.realpath(os.path.join(root, rel))
        # Containment check AFTER realpath, so a symlink pointing out of the
        # authorized root is caught rather than followed.
        if not (candidate == root or candidate.startswith(root + os.sep)):
            err(f"Source path escapes the authorized source root (symlink or "
                f"traversal): {p}")
            continue
        if not os.path.isfile(candidate):
            err(f"Referenced source file not found on disk: {p}")


def main() -> int:
    # A path or name outside the console code page must not turn finished work into a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("memo", help="path to the research memo .md")
    ap.add_argument(
        "--sources",
        default=None,
        help="path to the matter's sources/ directory, to confirm referenced files "
             "exist. REQUIRED with --formal.",
    )
    ap.add_argument(
        "--formal",
        action="store_true",
        help="formal-deliverable mode: --sources is required, cited sources must "
             "exist inside the authorized root, and missing sources are fatal.",
    )
    args = ap.parse_args()

    try:
        with open(args.memo, encoding="utf-8-sig") as fh:
            text = fh.read()
    except (OSError, ValueError) as exc:
        # ValueError covers UnicodeDecodeError: the memo must be UTF-8.
        print(f"cannot read memo (UTF-8 required): {exc}", file=sys.stderr)
        return 2

    fm, fm_raw, body = split_frontmatter(text)
    check_frontmatter(fm)
    found = check_sections(body)
    check_quotes(body, found)
    check_table(body, found)
    check_red_team(body, found)
    check_red_team_fields(body, fm, formal=args.formal)
    check_mixed_script_labels(body)
    check_prose_mismatch(body, fm, fm_raw, formal=args.formal, found=found)
    check_markers(body, fm)
    if not args.formal and _token(fm.get("type", "")).replace("-", "").replace(
        " ", ""
    ) == "RESEARCHMEMO":
        note(
            "Linted WITHOUT --formal. This memo declares itself a research memo, which is the "
            "Mode 3 deliverable: re-run with --formal --sources <archive> before delivering. "
            "Without it, source existence is not checked and a missing red team is only a "
            "warning."
        )
    check_sources(body, fm_raw, args.sources, formal=args.formal)

    leftover = PLACEHOLDER.findall(body)
    if leftover:
        err(f"{len(leftover)} template placeholder(s) remain in the body, e.g. {leftover[0]!r}")

    print(f"check_memo: {os.path.basename(args.memo)}")
    for m in notes:
        print(f"  note    {m}")
    for m in warnings:
        print(f"  WARN    {m}")
    for m in errors:
        print(f"  ERROR   {m}")
    mode = "formal deliverable (--formal)" if args.formal else "draft (--formal NOT supplied)"
    print(f"  {len(errors)} error(s), {len(warnings)} warning(s)   [mode: {mode}]")

    if errors:
        print("\n  Not deliverable. Fix the errors above.")
        return 2
    if warnings:
        print("\n  Deliverable with warnings. Read them.")
        return 1
    print(
        "\n  Structurally clean. This says the memo is auditable \u2014 sections present, "
        "quotations\n  pincited, cited paths inside the archive, declared fields consistent with "
        "the text.\n  It does NOT say the citator ran, the red team ran, or the law is right."
    )
    if not args.formal:
        print(
            "  Run again with --formal --sources <archive> before delivering: source existence "
            "and\n  a missing adversarial pass are only warnings without it."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
