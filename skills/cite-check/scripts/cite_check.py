#!/usr/bin/env python3
"""Record citation evidence and generate a hash-bound completeness report.

This tool does not discover citations, evaluate holdings, run a citator, or contact
any source. Only plain-text quote matching is automated: the quote command labels a
quotation VERIFIED, QUOTE_ALTERED, MISATTRIBUTED or UNRESOLVED against the archived
text. Other results are reviewer attestations.

Unpublished Wisconsin opinions. A case use marked "unpublished": true in the inventory
needs a citability check. Wis. Stat. s. 809.23(3)(a) bars citing an unpublished opinion as
precedent or authority except to support claim preclusion, issue preclusion or the law of
the case; s. 809.23(3)(b) allows citing one for persuasive value only if it was issued on
or after July 1, 2009 and is authored by a member of a three-judge panel or by a single
judge under s. 752.31(2), not a per curiam opinion, memorandum opinion, summary disposition
order or other order; s. 809.23(3)(c) requires filing and serving a copy with the paper
that cites it. The tool refuses a citability pass whose recorded facts do not meet those
conditions. It does not find unpublished opinions or read the opinion to confirm the
recorded facts; marking the use and recording the facts are the reviewer's.

Wisconsin citation form. SCR 80.02 sets the form for citing published Wisconsin opinions
in documents filed with the court of appeals or the supreme court: the public domain
citation first when it exists, then Wisconsin Reports, then North Western Reporter, SCR
80.02(1); page pinpoints for opinions before January 1, 2000 and paragraph pinpoints from
that date, SCR 80.02(3). The tool refuses a format pass for a case use whose citation text
breaks one of those mechanical rules, and the lint command applies the same rules to a
whole draft and exits 1 when it finds a departure. It reads citation text only: it does
not find every citation, check that a cited volume or number is right, or apply the rest
of the citation manual.
Requires Python 3.10+; standard library only. Run --help for commands.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import sys


LABELS = {"VERIFIED": {"pass"}, "QUOTE_ALTERED": {"fail", "caution"},
          "MISATTRIBUTED": {"fail", "caution"}, "UNRESOLVED": {"fail", "caution", "unverified"}}
ORIGINS = ("retrieved_this_session", "user_supplied", "remembered")
REACH = ("reachable", "unreachable", "not_attempted")
TEXT_SUFFIXES = {".txt", ".md"}
# Reviewer annotations in a .txt/.md source, each on its own line: "[locator: s. 999.01]"
# starts a segment that runs to the next locator marker; one "[version: ...]" names the
# dated text the file holds. Marker lines are not source text and are never matched.
# The word and the colon may be spaced or capitalised; a line that starts like a marker
# but does not parse is refused rather than read as source text, which would silently
# drop the locator boundaries and compare the whole file.
MARKER = re.compile(r"^\s*\[\s*(locator|version)\s*:\s*(.*?)\s*\]\s*$", re.I)
MARKER_LIKE = re.compile(r"^\s*\[\s*(?:locator|version)\b", re.I)
TOKEN = re.compile(r"\w+|[^\w\s]")
NEAR_RATIO = 0.7
NEAR_MIN_WORDS = 4
# A version line with one of these phrases says the file is not the text in force now.
# Phrase matching on a reviewer annotation; its absence does not establish the version in force.
# Wis. Stat. s. 809.23(3): purposes for which an unpublished opinion may be cited, and the
# kinds of unpublished disposition. Only "authored" may be cited for persuasive value.
CITABILITY_PURPOSES = ("persuasive", "claim_preclusion", "issue_preclusion", "law_of_the_case")
OPINION_TYPES = ("authored", "per_curiam", "memorandum", "summary_disposition", "other_order")
PERSUASIVE_FROM = "2009-07-01"
# SCR 80.001 (public domain citation form "2000 WI 14", "2001 WI App 9") and SCR 80.02.
PUBLIC_DOMAIN = re.compile(r"\b((?:19|20)\d{2}) WI( App)? (\d+)\b")
WIS_REPORTS = re.compile(r"\b\d{1,3} Wis\. ?2d \d+")
NW_BEFORE_WIS = re.compile(r"\b\d{1,3} N\.W\.2d \d+,\s*(?:\d+,\s*)?\d{1,3} Wis\. ?2d \d+")
WIS_BEFORE_PUBLIC_DOMAIN = re.compile(
    r"\b\d{1,3} (?:Wis\. ?2d|N\.W\.2d) \d+(?:,\s*(?:\d{1,3} (?:Wis\. ?2d|N\.W\.2d) \d+|\d+))*,\s*"
    r"(?:19|20)\d{2} WI(?: App)? \d+\b")
MALFORMED_PUBLIC_DOMAIN = re.compile(
    r"\b(?:19|20)\d{2},\s*WI(?: App)?\s+\d+\b|\b(?:19|20)\d{2}\s+WI\s+App\.\s*\d+"
    r"|\b(?:19|20)\d{2}\s+(?:Wi|wi)\s+(?:App\s+)?\d+\b|\b(?:19|20)\d{2}\s+WI\s+(?:APP|app)\s+\d+\b")
PAGE_PIN = re.compile(r",\s*(?:at\s+)?(\d+)(?:[-\u2013]\d+)?\s*(?=[,(.;]|$)")
YEAR_PARENTHETICAL = re.compile(r"\((?:[^()\n]{0,30}?\s)?((?:19|20)\d{2})\)")
NOT_IN_FORCE = re.compile(r"\b(?:not (?:yet )?in (?:force|effect)|no longer in (?:force|effect)|prior to|superseded|repealed)\b", re.I)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def inventory_digest(inv):
    """Bind the evidence to inventory meaning, independent of JSON indentation."""
    payload = json.dumps(inv, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


WINDOWS_DEVICE_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"{device}{number}" for device in ("COM", "LPT") for number in "123456789¹²³"}
)


def is_windows_reserved_name(part):
    """True for a Windows device name (CON, PRN, AUX, NUL, COM1-9, LPT1-9, ...) on any platform.

    Case-insensitive, with or without an extension ("nul.txt" is reserved), as Windows
    treats them. Local replacement for PurePath.is_reserved(), which is deprecated for
    removal in Python 3.15 and only answers for Windows path flavours.
    """
    stem = part.partition(".")[0].partition(":")[0].rstrip(" ")
    return stem.upper() in WINDOWS_DEVICE_NAMES


def source_path(root, name):
    """Reject absolute paths, traversal, Windows device/ADS names and escaped links."""
    if not isinstance(name, str) or not name or "\\" in name or ":" in name or "\x00" in name:
        raise ValueError("source file must be a non-empty relative POSIX path")
    relative = Path(name)
    if relative.is_absolute() or PureWindowsPath(name).is_absolute() or ".." in relative.parts:
        raise ValueError(f"unsafe source path: {name}")
    if any(is_windows_reserved_name(part) for part in relative.parts):
        raise ValueError(f"reserved source path: {name}")
    root = Path(root).resolve(strict=True)
    candidate = (root / relative).resolve(strict=True)
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise ValueError(f"source is not a file inside the archive: {name}")
    return candidate


def required_checks(use):
    if use["kind"] == "record":
        checks = {"record", "pincite", "format"}
    else:
        checks = {"citation", "pincite", "treatment", "proposition", "format"}
    if use.get("quote"):
        checks.add("verbatim")
    if use.get("unpublished"):
        checks.add("citability")
    return checks


def inventory(path, document):
    data = load_json(path)
    if not isinstance(data, dict) or data.get("document_sha256") != digest(document):
        raise ValueError("document hash differs from inventory; create a new run for the revised draft")
    uses = data.get("uses")
    if not isinstance(uses, list) or not uses:
        raise ValueError("inventory must include at least one citation use")
    ids = set()
    for use in uses:
        if not isinstance(use, dict) or any(not isinstance(use.get(k), str) or not use[k].strip() for k in ("id", "citation", "proposition", "kind")):
            raise ValueError("each use needs non-empty id, citation, proposition and kind strings")
        if use["id"] in ids:
            raise ValueError(f"duplicate citation use: {use['id']}")
        if use["kind"] not in {"case", "statute", "regulation", "rule", "record"}:
            raise ValueError(f"unsupported kind: {use['kind']}")
        if "unpublished" in use and (not isinstance(use["unpublished"], bool) or use["kind"] != "case"):
            raise ValueError("unpublished must be true or false and applies only to a case use")
        if "quote" in use and (not isinstance(use["quote"], str) or not normalized(use["quote"])):
            raise ValueError("quote must contain non-empty text after normalization; omit it when there is no quote")
        ids.add(use["id"])
    return data


def normalized(text):
    # Preserve dashes, word boundaries and punctuation. Dehyphenation, OCR repairs,
    # omissions and bracketed alterations require visual/manual review.
    translation = str.maketrans({"\u201c": '"', "\u201d": '"', "\u2018": "'", "\u2019": "'", "\ufb01": "fi", "\ufb02": "fl", "\u00ad": ""})
    return re.sub(r"\s+", " ", text.translate(translation)).strip()


def quote_in_text(quote, text):
    """Normalized match that does not start or end inside a word or number.

    "30 days after entry" must not match "130 days after entry"."""
    needle = normalized(quote)
    prefix = r"(?<!\w)" if re.match(r"\w", needle) else ""
    suffix = r"(?!\w)" if re.search(r"\w$", needle) else ""
    return re.search(prefix + re.escape(needle) + suffix, normalized(text)) is not None


def read_text_source(path):
    """Return (declared version or None, [(locator or None, text), ...])."""
    version, segments, label, lines, seen = None, [], None, [], set()
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        marker = MARKER.match(line)
        if not marker:
            if MARKER_LIKE.match(line):
                raise ValueError(f"malformed marker line in {Path(path).name}: {line.strip()!r}; "
                                 "write [locator: ...] or [version: ...] on a line of its own")
            lines.append(line)
            continue
        kind, value = marker.groups()
        kind = kind.lower()
        if not value:
            raise ValueError(f"empty {kind} marker in {Path(path).name}")
        if kind == "version":
            if version is not None:
                raise ValueError(f"{Path(path).name} declares more than one version; archive each dated text separately")
            version = value
            continue
        if locator_key(value) in seen:
            raise ValueError(f"{Path(path).name} repeats locator marker {value}")
        seen.add(locator_key(value))
        segments.append((label, "\n".join(lines)))
        label, lines = value, []
    segments.append((label, "\n".join(lines)))
    return version, segments


def locator_key(text):
    # Spacing is not part of a locator: "¶12" and "¶ 12" cite the same segment.
    return re.sub(r"\s+", "", normalized(text)).casefold()


def cited_segment(segments, locator):
    """Pick the marked segment a locator cites; "s. 999.01(2)" cites the "s. 999.01" segment."""
    if all(label is None for label, _ in segments):
        return "whole file (no locator markers)", list(range(len(segments)))
    key, best = locator_key(locator), None
    for index, (label, _) in enumerate(segments):
        mark = None if label is None else locator_key(label)
        if mark and (key == mark or (key.startswith(mark) and not key[len(mark)].isalnum())):
            if best is None or len(mark) > len(locator_key(segments[best][0])):
                best = index
    if best is None:
        return "nothing (cited locator not marked in this source)", []
    return f"marked locator {segments[best][0]}", [best]


def word_diff(quote, source):
    """[-draft only-]{+source only+} word diff of a quotation against source wording."""
    qn, sn = normalized(quote), normalized(source)
    q, s = list(TOKEN.finditer(qn)), list(TOKEN.finditer(sn))
    parts = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, [t.group() for t in q], [t.group() for t in s], autojunk=False).get_opcodes():
        draft = qn[q[i1].start():q[i2 - 1].end()] if i2 > i1 else ""
        found = sn[s[j1].start():s[j2 - 1].end()] if j2 > j1 else ""
        parts.append(found if tag == "equal" else (f"[-{draft}-]" if draft else "") + (f"{{+{found}+}}" if found else ""))
    return " ".join(parts)


def near_match(quote, text):
    """Return the closest source wording when it is at least NEAR_RATIO similar, else None."""
    sn = normalized(text)
    q = TOKEN.findall(normalized(quote))
    spans = list(TOKEN.finditer(sn))
    s = [t.group() for t in spans]
    if sum(bool(re.match(r"\w", t)) for t in q) < NEAR_MIN_WORDS or not s:
        return None

    def ratio(lo, hi):
        return SequenceMatcher(None, q, s[lo:hi], autojunk=False).ratio()

    # Rank windows of quotation length by shared words, then align the best few exactly.
    want, have, folded = Counter(t.casefold() for t in q), Counter(), [t.casefold() for t in s]
    shared, starts = 0, []
    for index, token in enumerate(folded):
        shared += have[token] < want[token]
        have[token] += 1
        if index >= len(q):
            old = folded[index - len(q)]
            have[old] -= 1
            shared -= have[old] < want[old]
        if index >= len(q) - 1:
            starts.append((shared, index - len(q) + 1))
    best = None
    for _, start in sorted(starts or [(shared, 0)], key=lambda item: (-item[0], item[1]))[:8]:
        for lo in range(max(0, start - 2), min(len(s), start + 3)):
            for hi in range(max(lo + 1, start + len(q) - 3), min(len(s), start + len(q) + 3) + 1):
                key = (ratio(lo, hi), -lo, lo - hi)
                if best is None or key > best[0]:
                    best = (key, lo, hi)
    if best is None:
        # The compared segment is shorter than the quotation; nothing to align.
        return None
    _, lo, hi = best
    # Keep a changed first or last word in view instead of trimming it away.
    ops = SequenceMatcher(None, q, s[lo:hi], autojunk=False).get_opcodes()
    edge = lambda op: op[0] == "delete" and any(re.match(r"\w", t) for t in q[op[1]:op[2]])
    wide_lo = max(0, lo - (ops[0][2] - ops[0][1])) if edge(ops[0]) else lo
    wide_hi = min(len(s), hi + (ops[-1][2] - ops[-1][1])) if edge(ops[-1]) else hi
    if (wide_lo, wide_hi) != (lo, hi) and ratio(wide_lo, wide_hi) >= NEAR_RATIO:
        lo, hi = wide_lo, wide_hi
    if ratio(lo, hi) < NEAR_RATIO:
        return None
    return sn[spans[lo].start():spans[hi - 1].end()]


def cited_check(quote, root, name, locator):
    path = source_path(root, name)
    if path.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError("quote requires a UTF-8 text source; archive/examine the original PDF separately")
    version, segments = read_text_source(path)
    compared, chosen = cited_segment(segments, locator)
    text = "\n".join(segments[i][1] for i in chosen) if chosen else None
    exact = text is not None and quote_in_text(quote, text)
    near = None if exact or text is None else near_match(quote, text)
    return {"version": version, "compared": compared, "chosen": chosen, "exact": exact, "near": near}


def search_archive(quote, root, cited_name, chosen):
    """Find the exact quotation in every other archived text segment of this run."""
    base, cited_name = Path(root).resolve(strict=True), Path(cited_name).as_posix()
    found, searched, skipped = [], 0, []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        rel = path.relative_to(base).as_posix()
        try:
            safe = source_path(root, rel)
            if safe.suffix.lower() not in TEXT_SUFFIXES:
                raise ValueError("not text")
            version, segments = read_text_source(safe)
        except (ValueError, OSError):
            skipped.append(rel)
            continue
        others = [i for i in range(len(segments)) if not (rel == cited_name and i in chosen)]
        searched += bool(others)
        for i in others:
            if quote_in_text(quote, segments[i][1]):
                found.append({"file": rel, "sha256": digest(safe), "locator": segments[i][0],
                              **({"version": version} if version else {})})
    return found, searched, skipped


def not_in_force(version):
    return bool(version and NOT_IN_FORCE.search(normalized(version)))


def tool_result(label, version):
    """Result the quote command records: VERIFIED against a not-in-force version is caution."""
    if label != "VERIFIED":
        return "fail"
    return "caution" if not_in_force(version) else "pass"


def classify(quote, root, name, locator):
    """Fields for a tool-labelled verbatim entry."""
    cited = cited_check(quote, root, name, locator)
    fields = {"compared": cited["compared"], **({"version_compared": cited["version"]} if cited["version"] else {})}
    if cited["exact"]:
        note = "Exact text found in the compared text. Pincite, attribution and the version in force need separate review."
        if not_in_force(cited["version"]):
            note += (" The compared file's version line says this text is not in force or is a prior version,"
                     " so the result is caution until a reviewer confirms which version applies on the operative date.")
        return dict(fields, label="VERIFIED", matched=quote, note=note)
    found, searched, skipped = search_archive(quote, root, name, cited["chosen"])
    note = f"Searched {searched} archived text source(s) outside the compared text for the exact quotation."
    if skipped:
        note += (f" Not searched ({len(skipped)}, not UTF-8 .txt/.md): " + ", ".join(skipped[:5])
                 + (", ..." if len(skipped) > 5 else "") + ".")
    if found:
        return dict(fields, label="MISATTRIBUTED", matched="", found_in=found, note=note)
    if not searched:
        note += " MISATTRIBUTED was not assessed: no other archived text could be searched."
    if cited["near"] is not None:
        return dict(fields, label="QUOTE_ALTERED", matched=cited["near"], diff=word_diff(quote, cited["near"]), note=note)
    return dict(fields, label="UNRESOLVED", matched="", note=note)


def check_found_in(entry, quote, root):
    places = entry.get("found_in")
    if not isinstance(places, list) or not places:
        raise ValueError("MISATTRIBUTED needs found_in naming where the quotation was found")
    for place in places:
        if not isinstance(place, dict) or not isinstance(place.get("file"), str) or not (
                place.get("locator") is None or isinstance(place["locator"], str)):
            raise ValueError("each found_in place needs file, sha256 and locator")
        path = source_path(root, place["file"])
        if place.get("sha256") != digest(path):
            raise ValueError(f"found_in source hash differs: {place['file']}")
        if path.suffix.lower() in TEXT_SUFFIXES:
            version, segments = read_text_source(path)
            if place.get("version") != version or not any(
                    label == place.get("locator") and quote_in_text(quote, text) for label, text in segments):
                raise ValueError(f"found_in does not match the archived text: {place['file']}")


def check_quote_label(entry, use, root):
    label = entry.get("label")
    if label is None:
        return
    if entry["check"] != "verbatim" or label not in LABELS:
        raise ValueError("label applies only to verbatim checks: VERIFIED, QUOTE_ALTERED, MISATTRIBUTED or UNRESOLVED")
    allowed = LABELS[label] | ({"caution"} if label == "VERIFIED" and entry.get("method") == "exact-text" else set())
    if entry["result"] not in allowed:
        raise ValueError(f"{label} cannot be recorded as {entry['result']}; only VERIFIED supports a pass")
    if label == "MISATTRIBUTED":
        check_found_in(entry, use["quote"], root)
    if label == "QUOTE_ALTERED" and (not isinstance(entry.get("matched"), str) or not entry["matched"].strip()):
        raise ValueError("QUOTE_ALTERED needs the differing source wording in matched")
    if entry.get("method") != "exact-text":
        return
    if not isinstance(entry.get("file"), str) or not isinstance(entry.get("locator"), str):
        raise ValueError("exact-text needs the compared file and locator")
    cited = cited_check(use["quote"], root, entry["file"], entry["locator"])
    expected = {"VERIFIED": cited["exact"], "QUOTE_ALTERED": not cited["exact"] and cited["near"] is not None,
                "MISATTRIBUTED": not cited["exact"], "UNRESOLVED": not cited["exact"] and cited["near"] is None}[label]
    matched = {"VERIFIED": use["quote"], "QUOTE_ALTERED": cited["near"]}.get(label, "")
    if (not expected or entry["result"] != tool_result(label, cited["version"]) or entry.get("matched") != matched
            or entry.get("compared") != cited["compared"] or entry.get("version_compared") != cited["version"]
            or (label == "QUOTE_ALTERED" and entry.get("diff") != word_diff(use["quote"], matched))):
        raise ValueError("exact-text label does not match the archived text")


def scr_80_02_problems(text):
    """Mechanical departures from SCR 80.02 in citation text; an empty list is not approval."""
    problems = []

    def add(rule, message, start, end):
        excerpt = " ".join(text[max(0, start - 30):min(len(text), end + 40)].split())
        problems.append(f"{rule}: {message}: \"{excerpt}\"")

    for match in MALFORMED_PUBLIC_DOMAIN.finditer(text):
        add("SCR 80.001", "a public domain citation takes the form 2000 WI 14 or 2001 WI App 9, with no comma "
            "after the year and no period after App", match.start(), match.end())
    for match in PUBLIC_DOMAIN.finditer(text):
        if int(match.group(1)) < 2000:
            add("SCR 80.01(2)-(3)", "public domain citations begin with opinions issued or ordered published on or "
                "after January 1, 2000", match.start(), match.end())
        if re.match(r",?\s*at\s+\d+", text[match.end():match.end() + 20]):
            add("SCR 80.02(3)(b)", "an opinion issued on or after January 1, 2000 is cited to paragraph numbers, "
                "not pages", match.start(), match.end() + 12)
    for match in NW_BEFORE_WIS.finditer(text):
        add("SCR 80.02(1)", "the Wisconsin Reports citation comes before the North Western Reporter citation",
            match.start(), match.end())
    for match in WIS_BEFORE_PUBLIC_DOMAIN.finditer(text):
        add("SCR 80.02(1)", "the public domain citation comes first", match.start(), match.end())
    for match in WIS_REPORTS.finditer(text):
        before = text[max(0, match.start() - 45):match.start()]
        after = text[match.end():match.end() + 110]
        # Stop at the end of this citation: a semicolon, a line break, or a sentence end.
        after = re.split(r";|\n|\.\s+(?!(?:App|Ct|2d|Jan|Feb|Mar|Apr|Aug|Sept|Oct|Nov|Dec)\b)(?=[A-Z*_])",
                         after, maxsplit=1)[0]
        cited = [found for found in PUBLIC_DOMAIN.finditer(before) if not re.search(r"[;\n]", before[found.end():])]
        year = YEAR_PARENTHETICAL.search(after)
        modern = bool(cited) and int(cited[-1].group(1)) >= 2000 or bool(year) and int(year.group(1)) >= 2000
        if not cited and year and int(year.group(1)) >= 2000:
            add("SCR 80.02(1)(a)", f"an opinion dated {year.group(1)} is cited without its public domain citation, "
                "which comes first when it exists", match.start(), match.end())
        pin = PAGE_PIN.match(after)
        if modern and pin:
            add("SCR 80.02(3)(b)", "an opinion issued on or after January 1, 2000 is cited to paragraph numbers, "
                f"not to page {pin.group(1)}", match.start(), match.end() + pin.end())
    return problems


def document_text(path):
    """Plain text of a .txt, .md or .docx draft for the lint command."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8-sig")
    if suffix == ".docx":
        import zipfile
        from xml.etree import ElementTree
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        with zipfile.ZipFile(path) as archive:
            root = ElementTree.fromstring(archive.read("word/document.xml"))
        return "\n".join("".join(node.text or "" for node in paragraph.iter(namespace + "t"))
                         for paragraph in root.iter(namespace + "p"))
    raise ValueError("lint reads a .txt, .md or .docx draft")


def check_citability(entry):
    """Refuse a citability pass that Wis. Stat. s. 809.23(3) does not allow on the recorded facts."""
    facts = entry.get("citability")
    if facts is None and entry["result"] != "pass":
        return
    if not isinstance(facts, dict) or facts.get("purpose") not in CITABILITY_PURPOSES:
        raise ValueError("citability needs a citability object whose purpose is persuasive, claim_preclusion, "
                         "issue_preclusion or law_of_the_case (Wis. Stat. s. 809.23(3)(a)-(b))")
    if "opinion_type" in facts and facts["opinion_type"] not in OPINION_TYPES:
        raise ValueError("citability opinion_type must be authored, per_curiam, memorandum, summary_disposition or other_order")
    if "issued" in facts:
        try:
            issued = datetime.strptime(facts["issued"], "%Y-%m-%d").date().isoformat() if isinstance(facts["issued"], str) else None
        except ValueError:
            issued = None
        if issued is None:
            raise ValueError("citability issued must be the opinion's date as YYYY-MM-DD")
    if "copy_filed_and_served" in facts and not isinstance(facts["copy_filed_and_served"], bool):
        raise ValueError("citability copy_filed_and_served must be true or false")
    if entry["result"] != "pass":
        return
    if facts["purpose"] == "persuasive":
        if facts.get("opinion_type") != "authored":
            raise ValueError("citability pass refused: Wis. Stat. s. 809.23(3)(b) allows citing an unpublished opinion "
                             "for persuasive value only if it is authored by a member of a three-judge panel or by a "
                             "single judge under s. 752.31(2); a per curiam opinion, memorandum opinion, summary "
                             "disposition order or other order is not an authored opinion. Record opinion_type "
                             "authored from the opinion itself, or record fail")
        if "issued" not in facts or facts["issued"] < PERSUASIVE_FROM:
            raise ValueError("citability pass refused: Wis. Stat. s. 809.23(3)(b) reaches only an unpublished opinion "
                             "issued on or after July 1, 2009; record the issue date from the opinion, or record fail")
    if facts.get("copy_filed_and_served") is not True:
        raise ValueError("citability pass refused: Wis. Stat. s. 809.23(3)(c) requires a party citing an unpublished "
                         "opinion to file and serve a copy with the brief or other paper; record "
                         "copy_filed_and_served true once the copy is with the filing, or record caution")


def validate_entry(entry, inv, root):
    if not isinstance(entry, dict):
        raise ValueError("each evidence entry must be a JSON object")
    if entry.get("document_sha256") != inv["document_sha256"]:
        raise ValueError("evidence belongs to another draft")
    if entry.get("inventory_sha256") != inventory_digest(inv):
        raise ValueError("evidence belongs to another inventory; create a new run after inventory changes")
    use = next((u for u in inv["uses"] if u["id"] == entry.get("use")), None)
    if use is None or entry.get("check") not in required_checks(use):
        raise ValueError("evidence names an unknown use or inapplicable check")
    if entry.get("result") not in {"pass", "fail", "unverified", "caution"}:
        raise ValueError("result must be pass, fail, unverified or caution")
    if not isinstance(entry.get("note"), str) or not entry["note"].strip():
        raise ValueError("every check needs a note describing what was reviewed or what blocked it")
    if "provenance" in entry:
        provenance = entry["provenance"]
        if not isinstance(provenance, dict) or any(not isinstance(provenance.get(k), str) or not provenance[k].strip()
                for k in ("origin", "retrieved_at", "version", "extraction_method")):
            raise ValueError("provenance needs origin, retrieved_at, version and extraction_method strings")
        try:
            retrieved = datetime.fromisoformat(provenance["retrieved_at"].replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("provenance retrieved_at must be an ISO-8601 timestamp") from exc
        if retrieved.tzinfo is None:
            raise ValueError("provenance retrieved_at needs a timezone")
        if "original_file" in provenance or "original_sha256" in provenance:
            original = source_path(root, provenance.get("original_file"))
            if provenance.get("original_sha256") != digest(original):
                raise ValueError("provenance original source hash differs")
    if "provenance_origin" in entry and entry["provenance_origin"] not in ORIGINS:
        raise ValueError("provenance_origin must be retrieved_this_session, user_supplied or remembered")
    if entry["result"] == "pass" and entry.get("provenance_origin") == "remembered":
        raise ValueError(f"{entry['check']} pass refused: remembered text is not a source; retrieve the source, or record caution or unverified")
    if "source_status" in entry:
        status = entry["source_status"]
        if not isinstance(status, dict) or status.get("status") not in REACH or any(
                not isinstance(status.get(k), str) or not status[k].strip() for k in ("source", "reason")):
            raise ValueError("source_status needs source, reason and status (reachable, unreachable or not_attempted)")
        if entry["result"] == "pass" and status["status"] != "reachable":
            raise ValueError("a check cannot pass from a source that was not reached")
    if "version_compared" in entry and (not isinstance(entry["version_compared"], str) or not entry["version_compared"].strip()):
        raise ValueError("version_compared must name the dated text that was compared")
    if entry["result"] == "pass":
        if not all(isinstance(entry.get(k), str) and entry[k].strip() for k in ("file", "sha256", "locator", "matched")):
            raise ValueError("passing checks need file, sha256, locator and matched source evidence")
        if entry["check"] == "treatment" and use["kind"] == "case" and (not isinstance(entry.get("citator"), str) or not entry["citator"].strip()):
            raise ValueError("case treatment cannot pass without a named citator; use caution for a free-source screen")
    if entry["check"] == "format" and entry["result"] == "pass" and use["kind"] == "case":
        departures = scr_80_02_problems(use["citation"])
        if departures:
            raise ValueError("format pass refused: the citation text departs from SCR 80.02; correct the draft and "
                             "start a new run, or record fail or caution with the reason: " + " | ".join(departures))
    if entry["check"] == "citability":
        check_citability(entry)
    elif "citability" in entry:
        raise ValueError("citability facts belong only on a citability check")
    if entry.get("file"):
        path = source_path(root, entry["file"])
        if entry.get("sha256") != digest(path):
            raise ValueError(f"source hash differs: {entry['file']}")
    elif entry.get("sha256"):
        raise ValueError("source hash without a source file")
    if entry["check"] == "verbatim" and entry.get("file") and Path(entry["file"]).suffix.lower() in TEXT_SUFFIXES:
        version = read_text_source(source_path(root, entry["file"]))[0]
        if version is not None and entry.get("version_compared") != version:
            raise ValueError(f"the source declares version {version!r}; the entry must name it in version_compared")
    check_quote_label(entry, use, root)
    if entry.get("method") == "exact-text" and entry.get("label") is None:
        # Records written before quote labels: the result must agree with a whole-file search;
        # a pass is also checked at the cited locator below.
        path = source_path(root, entry["file"])
        if entry["check"] != "verbatim" or path.suffix.lower() not in {".txt", ".md"}:
            raise ValueError("exact-text only supports verbatim checks against .txt/.md sources")
        found = quote_in_text(use["quote"], path.read_text(encoding="utf-8-sig"))
        expected = tool_result("VERIFIED", read_text_source(path)[0]) if found else "fail"
        if found and expected == "caution" and entry["result"] == "pass":
            raise ValueError("exact-text pass refused: the compared file's version line says the text is not in force "
                             "or is a prior version; record caution, or a manual pass whose note says which version applies")
        if entry["result"] != expected or entry.get("matched") != (use["quote"] if found else ""):
            raise ValueError("exact-text result does not match the archived text")
    if entry["check"] == "verbatim" and entry["result"] == "pass" and Path(entry["file"]).suffix.lower() in TEXT_SUFFIXES:
        # No verbatim pass (manual, legacy or hand-edited) may assert a quotation that the
        # readable archived text lacks at the cited locator.
        cited = cited_check(use["quote"], root, entry["file"], entry["locator"])
        if not cited["exact"]:
            place = ("the archived text" if not cited["compared"].startswith("marked") and cited["chosen"]
                     else f"the segment marked for the cited locator {entry['locator']!r}" if cited["chosen"]
                     else f"the cited locator: {entry['file']} has locator markers but none matches {entry['locator']!r}")
            raise ValueError(f"verbatim pass refused: the quotation is not in {place}; "
                             "use the quote command, or record fail, caution or unverified")
    return use


def read_log(path, inv, root):
    if not Path(path).exists():
        return []
    entries, seen = [], set()
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            validate_entry(entry, inv, root)
        except (ValueError, OSError) as exc:
            raise ValueError(f"log line {number}: {exc}") from exc
        key = (entry["use"], entry["check"])
        if key in seen:
            raise ValueError(f"duplicate evidence for {key}; start a new run for corrections")
        seen.add(key)
        entries.append(entry)
    return entries


def append_entry(log, entry, inv, root):
    if not isinstance(entry, dict):
        raise ValueError("each evidence entry must be a JSON object")
    entry = dict(entry)
    entry.setdefault("inventory_sha256", inventory_digest(inv))
    entries = read_log(log, inv, root)
    validate_entry(entry, inv, root)
    if any((e["use"], e["check"]) == (entry["use"], entry["check"]) for e in entries):
        raise ValueError("check already recorded; preserve this log and start a new run for corrections")
    entry = dict(entry, recorded_at=datetime.now(timezone.utc).isoformat())
    # One writer per log. Preserve every prior byte, including an unterminated
    # final record accepted by read_log; separate it before appending another.
    with Path(log).open("ab+") as stream:
        stream.seek(0, 2)
        if stream.tell():
            stream.seek(-1, 2)
            if stream.read(1) not in (b"\n", b"\r"):
                stream.write(b"\n")
        stream.write((json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8"))


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def sources_status(path, inv):
    """Load the reviewer's per-source reachability record for the report."""
    data = load_json(path)
    rows = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError("sources-status needs a non-empty sources list")
    ids = {use["id"] for use in inv["uses"]}
    for row in rows:
        if not isinstance(row, dict) or row.get("status") not in REACH or any(
                not isinstance(row.get(k), str) or not row[k].strip() for k in ("source", "reason")):
            raise ValueError("each sources-status row needs source, reason and status (reachable, unreachable or not_attempted)")
        if not isinstance(row.get("uses"), list) or not row["uses"] or any(use not in ids for use in row["uses"]):
            raise ValueError(f"sources-status row for {row['source']} must list the inventory uses it affects")
    return rows, digest(path)


def where(place):
    locator = place["locator"] if place.get("locator") is not None else "unmarked text"
    return f"{place['file']} @ {locator}" + (f" (version: {place['version']})" if place.get("version") else "")


def quote_label(entry, quote):
    label = entry.get("label")
    if label is None:
        return "quote label not recorded"
    tool = entry.get("method") == "exact-text"
    text = f"{label}: " + {"VERIFIED": "exact text found", "QUOTE_ALTERED": "near match, wording differs",
                          "MISATTRIBUTED": "exact text not at the cited locator", "UNRESOLVED": "not found"}[label]
    text += f"; compared {entry['compared']}" if tool else " (reviewer label)"
    if label == "VERIFIED" and entry.get("result") == "caution":
        text += "; caution: the compared file's version line says the text is not in force or is a prior version"
    if label == "QUOTE_ALTERED":
        text += "; diff ([-draft only-] {+source only+}): " + word_diff(quote, entry["matched"])
    if label == "MISATTRIBUTED":
        text += "; found at " + "; ".join(where(place) for place in entry["found_in"])
    if label == "UNRESOLVED" and tool:
        text += "; see the note for what the archive search covered"
    return text


def reachability(inv, entries, reach=None):
    """Per-source, per-authority reachability lines; never a blanket verdict."""
    rows = {}

    def add(source, state, reason, basis, use, check=None):
        checks = rows.setdefault((source, state, reason, basis), {}).setdefault(use, set())
        if check:
            checks.add(check)

    for row in reach[0] if reach else []:
        for use in row["uses"]:
            add(row["source"], row["status"], row["reason"], "sources-status file", use)
    for entry in entries:
        if "source_status" in entry:
            found = entry["source_status"]
            add(found["source"], found["status"], found["reason"], "evidence record", entry["use"], entry["check"])
    for entry in sorted((e for e in entries if e.get("file")), key=lambda e: e["file"]):
        # The tool reads a file's contents only for a verbatim check it compared: an exact-text
        # record, or a verbatim pass against a .txt/.md file. Otherwise it only checks the hash.
        compared = entry["check"] == "verbatim" and Path(entry["file"]).suffix.lower() in TEXT_SUFFIXES and (
            entry.get("method") == "exact-text" or entry["result"] == "pass")
        reason = ("archived copy read for the recorded check; its hash matched when this report ran" if compared else
                  "archived file present and its hash matched when this report ran; contents not compared by the tool")
        add(entry["file"], "reachable", reason, "evidence records", entry["use"], entry["check"])
    order = [use["id"] for use in inv["uses"]]
    citation = {use["id"]: use["citation"] for use in inv["uses"]}
    lines = ["## Sources reachable", "",
             "Recorded per source and per affected authority. The tool contacts no source: each status comes from the reviewer's sources-status file or from the evidence records. An unreachable or unattempted source limits only the authorities listed against it, and a reachable source does not make any check pass.", "",
             f"Sources-status file SHA-256: `{reach[1]}`" if reach else "No sources-status file was supplied.", ""]
    if rows:
        lines += ["| Source | Status | Reason | Affected authorities | Recorded in |", "|---|---|---|---|---|"]
        for (source, state, reason, basis), uses in rows.items():
            affected = "; ".join(f"{use} {citation[use]}" + (f" ({', '.join(sorted(uses[use]))})" if uses[use] else "")
                                 for use in order if use in uses)
            lines.append("| " + " | ".join(map(cell, [source, state.replace("_", " "), reason, affected, basis])) + " |")
        lines.append("")
    listed = {use for uses in rows.values() for use in uses}
    missing = [f"{use} {citation[use]}" for use in order if use not in listed]
    if missing:
        lines += ["No source recorded for: " + cell("; ".join(missing)) + ".", ""]
    return lines


def report(inv, entries, reach=None):
    rows, incomplete = [], False
    for use in inv["uses"]:
        checks = {e["check"]: e for e in entries if e["use"] == use["id"]}
        missing = required_checks(use) - checks.keys()
        failed = [k for k, e in checks.items() if e["result"] == "fail"]
        unresolved = [k for k, e in checks.items() if e["result"] in {"unverified", "caution"}]
        status = "FLAGGED" if failed else "UNVERIFIED" if missing or unresolved else "RECORDED PASS"
        incomplete |= status != "RECORDED PASS"
        detail = []
        for name in sorted(required_checks(use)):
            entry = checks.get(name)
            if entry is None:
                detail.append(f"{name}: missing")
            else:
                evidence = f"{entry.get('file', 'no copy')} @ {entry.get('locator', 'no locator')}"
                if name == "verbatim":
                    if entry.get("method") == "exact-text":
                        evidence += ", text compared by the tool"
                    elif entry["result"] == "pass" and Path(entry.get("file") or "").suffix.lower() in {".txt", ".md"}:
                        evidence += ", reviewer attestation; the tool confirmed the quotation appears in the archived text, nothing more"
                    else:
                        evidence += ", reviewer attestation, not compared by the tool"
                parts = [f"{name}: {entry['result']} ({evidence})"]
                if name == "verbatim":
                    parts.append(quote_label(entry, use["quote"]))
                if name == "citability" and isinstance(entry.get("citability"), dict):
                    facts = entry["citability"]
                    parts.append("s. 809.23(3) facts recorded by the reviewer: purpose " + facts["purpose"].replace("_", " ")
                                 + f", opinion type {str(facts.get('opinion_type', 'not recorded')).replace('_', ' ')}"
                                 + f", issued {facts.get('issued', 'not recorded')}"
                                 + ", copy filed and served: " + {True: "yes", False: "no"}.get(facts.get("copy_filed_and_served"), "not recorded"))
                if entry.get("version_compared"):
                    parts.append(f"compared against version: {entry['version_compared']}")
                origin = entry.get("provenance_origin")
                parts += [f"provenance: {origin.replace('_', ' ')}" if origin else "provenance not recorded", entry["note"]]
                detail.append("; ".join(parts))
        rows.append("| " + " | ".join(map(cell, [use["id"], use["citation"], use["proposition"], status, "; ".join(detail)])) + " |")
    text = "\n".join([
        "# Citation evidence report", "", f"Document SHA-256: `{inv['document_sha256']}`",
        f"Inventory SHA-256 (canonical JSON): `{inventory_digest(inv)}`", "",
        "RECORDED PASS means every required check has a passing evidence record. It is not an independent finding of legal accuracy, good-law status, or filing readiness. Citation inventory completeness and manual judgments require review. Exact text matching does not verify attribution, pagination, or proposition support. For quotations only VERIFIED supports a pass; QUOTE_ALTERED, MISATTRIBUTED and UNRESOLVED do not. The evidence log is an ordinary local file: this tool detects a changed draft, source or inventory, but not a deleted, inserted or hand-edited log line.", "",
        "| Use | Citation | Proposition | Status | Checks and evidence |", "|---|---|---|---|---|", *rows, "",
        *(["Unpublished opinions: " + "; ".join(f"{use['id']} {use['citation']}" for use in inv["uses"] if use.get("unpublished"))
           + ". Wis. Stat. s. 809.23(3)(c): a party citing an unpublished opinion shall file and serve a copy of the opinion "
             "with the brief or other paper in which it is cited. An archived copy in the sources folder is not a filed or "
             "served copy. The citability facts above are the reviewer's record; the tool applied the conditions of "
             "s. 809.23(3)(a)-(c) to them and did not read the opinion.", ""]
          if any(use.get("unpublished") for use in inv["uses"]) else []),
        *reachability(inv, entries, reach),
        "## Evidence records", "",
        "The records below preserve source hashes, locators, matched text, methods, and reviewer notes. Corrected drafts require a new inventory and log; prior runs remain unchanged.", "", "```json", json.dumps(entries, indent=2, ensure_ascii=False), "```", ""
    ])
    return text, incomplete


def main():
    # A path or name outside the console code page must not turn finished work into a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("record", "quote", "report", "lint"))
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--document", required=True, type=Path)
    parser.add_argument("--sources", type=Path)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--entry", type=Path, help="JSON evidence for record")
    parser.add_argument("--use", help="inventory use id for quote")
    parser.add_argument("--file", help="archive-relative .txt/.md source for quote")
    parser.add_argument("--locator", help="source locator; independently verify the pincite")
    parser.add_argument("--out", type=Path, help="new Markdown report path; never overwritten")
    parser.add_argument("--provenance-origin", choices=ORIGINS, help="how the quote source text reached this session")
    parser.add_argument("--sources-status", type=Path, help="JSON reachability per source for report")
    args = parser.parse_args()
    if args.command != "lint" and not all((args.inventory, args.sources, args.log)):
        parser.error(f"{args.command} requires --inventory, --sources and --log")
    try:
        if args.command == "lint":
            departures = scr_80_02_problems(document_text(args.document))
            for line in departures:
                print(line)
            print(f"{len(departures)} departure(s) from SCR 80.02 found in the citation forms this command recognises. "
                  "It does not find every citation, verify volumes, pages or paragraph numbers, or apply any other "
                  "citation rule; SCR 80.02 by its terms governs documents filed with the court of appeals or the "
                  "supreme court.")
            return 1 if departures else 0
        inv = inventory(args.inventory, args.document)
        if args.command == "record":
            if not args.entry:
                parser.error("record requires --entry")
            entry = load_json(args.entry)
            if not isinstance(entry, dict):
                raise ValueError("entry must be a JSON object")
            entry.setdefault("document_sha256", inv["document_sha256"])
            append_entry(args.log, entry, inv, args.sources)
        elif args.command == "quote":
            if not all((args.use, args.file, args.locator)):
                parser.error("quote requires --use, --file and --locator")
            use = next((u for u in inv["uses"] if u["id"] == args.use), None)
            if not use or not use.get("quote"):
                raise ValueError("use must have a non-empty quote in the inventory")
            path = source_path(args.sources, args.file)
            fields = classify(use["quote"], args.sources, args.file, args.locator)
            entry = {"document_sha256": inv["document_sha256"], "use": args.use, "check": "verbatim",
                     "result": tool_result(fields["label"], fields.get("version_compared")), "method": "exact-text",
                     "file": args.file, "sha256": digest(path), "locator": args.locator, **fields}
            if args.provenance_origin:
                entry["provenance_origin"] = args.provenance_origin
            append_entry(args.log, entry, inv, args.sources)
            print(quote_label(entry, use["quote"]))
        else:
            if not args.out or args.out.suffix.lower() != ".md":
                parser.error("report requires --out with a new .md path")
            entries = read_log(args.log, inv, args.sources)
            status = sources_status(args.sources_status, inv) if args.sources_status else None
            text, incomplete = report(inv, entries, status)
            with args.out.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            print(args.out)
            return 1 if incomplete else 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"cite_check: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
