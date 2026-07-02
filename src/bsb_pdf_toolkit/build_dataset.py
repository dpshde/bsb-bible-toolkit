#!/usr/bin/env python3
"""Build the structured BSB JSON dataset from USFM source.

Parses the Berean Standard Bible USFM archive (66 books), extracts verses,
footnotes, and BSB cross-references from ``\\ref`` tags within ``\\f`` footnote
blocks, enriches verses with events/entities from the Arweave JSONL, merges
TSK cross-references (CC-BY) and ACAI/Theographic entity links (CC-BY-SA),
generates route.bible OSIS links, and writes deterministic structured JSON to
``output/dataset/``.

Outputs (under the ``--output`` directory, default ``output/dataset``):
    bsb-dataset.json        Unified dataset (all 66 books, all verses)
    manifest.json           Build metadata, counts, source versions, build hash
    cross-refs.json         CC0/CC-BY cross-reference index (bsb-footnote, tsk)
    entity-links.json       CC-BY-SA entity link index (acai, theographic)
    books/<OSIS>.json       Per-book JSON (66 files)
    books/<OSIS>/chapters/<N>.json   Per-chapter JSON (1,189 files)
    books/<OSIS>/verses/<OSIS>.<C>.<V>.json   Per-verse JSON (one per verse)

Determinism: all JSON is written with ``sort_keys=True`` and a fixed indent.
No timestamps or random values are embedded in the output, so two builds from
identical inputs produce byte-identical files.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USFM = REPO_ROOT / "drafts" / "primary" / "source" / "engbsb_usfm.zip"
DEFAULT_OUTPUT = REPO_ROOT / "output" / "dataset"
DEFAULT_ENRICHMENT_URL = (
    "https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s"
)
TSK_URL = "https://a.openbible.info/data/cross-references.zip"
ACAI_RAW_BASE = "https://raw.githubusercontent.com/BibleAquifer/ACAI/main"
THEOGRAPHIC_VERSES_URL = (
    "https://raw.githubusercontent.com/robertrouse/"
    "theographic-bible-metadata/master/json/verses.json"
)
JSON_INDENT = 2
JSON_ENSURE_ASCII = False
KNOWN_SOURCES = {"bsb-footnote", "tsk", "acai", "theographic"}
CC_BY_SA_SOURCES = {"acai", "theographic"}
# Sentinel tokens used to embed \r section cross-references inside the chapter
# body so the verse splitter can attribute them to the correct verse. The
# payload is a JSON array wrapped with START/END markers so brace-balancing is
# not a concern. The markers use the Unicode private-use area to avoid any
# collision with biblical text.
_SECTION_XREF_START = "\uE000BSBSECTIONXREF\uE001"
_SECTION_XREF_END = "\uE002BSBSECTIONXREFEND\uE003"

# ---------------------------------------------------------------------------
# Canonical book metadata (SBL OSIS abbreviations, Protestant 66-book canon)
# ---------------------------------------------------------------------------
CANON_BOOKS: List[Tuple[str, str]] = [
    ("GEN", "Genesis"), ("EXO", "Exodus"), ("LEV", "Leviticus"),
    ("NUM", "Numbers"), ("DEU", "Deuteronomy"), ("JOS", "Joshua"),
    ("JDG", "Judges"), ("RUT", "Ruth"), ("1SA", "1 Samuel"),
    ("2SA", "2 Samuel"), ("1KI", "1 Kings"), ("2KI", "2 Kings"),
    ("1CH", "1 Chronicles"), ("2CH", "2 Chronicles"), ("EZR", "Ezra"),
    ("NEH", "Nehemiah"), ("EST", "Esther"), ("JOB", "Job"),
    ("PSA", "Psalms"), ("PRO", "Proverbs"), ("ECC", "Ecclesiastes"),
    ("SNG", "Song of Solomon"), ("ISA", "Isaiah"), ("JER", "Jeremiah"),
    ("LAM", "Lamentations"), ("EZK", "Ezekiel"), ("DAN", "Daniel"),
    ("HOS", "Hosea"), ("JOL", "Joel"), ("AMO", "Amos"),
    ("OBA", "Obadiah"), ("JON", "Jonah"), ("MIC", "Micah"),
    ("NAM", "Nahum"), ("HAB", "Habakkuk"), ("ZEP", "Zephaniah"),
    ("HAG", "Haggai"), ("ZEC", "Zechariah"), ("MAL", "Malachi"),
    ("MAT", "Matthew"), ("MRK", "Mark"), ("LUK", "Luke"),
    ("JHN", "John"), ("ACT", "Acts"), ("ROM", "Romans"),
    ("1CO", "1 Corinthians"), ("2CO", "2 Corinthians"), ("GAL", "Galatians"),
    ("EPH", "Ephesians"), ("PHP", "Philippians"), ("COL", "Colossians"),
    ("1TH", "1 Thessalonians"), ("2TH", "2 Thessalonians"),
    ("1TI", "1 Timothy"), ("2TI", "2 Timothy"), ("TIT", "Titus"),
    ("PHM", "Philemon"), ("HEB", "Hebrews"), ("JAS", "James"),
    ("1PE", "1 Peter"), ("2PE", "2 Peter"), ("1JN", "1 John"),
    ("2JN", "2 John"), ("3JN", "3 John"), ("JUD", "Jude"),
    ("REV", "Revelation"),
]
OSIS_TO_NAME: Dict[str, str] = {osis: name for osis, name in CANON_BOOKS}
NAME_TO_OSIS: Dict[str, str] = {name: osis for osis, name in CANON_BOOKS}
CANON_OSIS_CODES: List[str] = [osis for osis, _ in CANON_BOOKS]
CANON_OSIS_SET = set(CANON_OSIS_CODES)

# ---------------------------------------------------------------------------
# Mappings for converting external reference formats to canonical OSIS
# ---------------------------------------------------------------------------
# TSK and Arweave JSONL use short lowercase book abbreviations that follow the
# route.bible / add_route_links.py style (e.g. "Gen", "2Pet", "Ps", "Song").
TSK_BOOK_TO_OSIS: Dict[str, str] = {
    "Gen": "GEN", "Exod": "EXO", "Ex": "EXO", "Lev": "LEV", "Num": "NUM",
    "Deut": "DEU", "Josh": "JOS", "Judg": "JDG", "Ruth": "RUT",
    "1Sam": "1SA", "2Sam": "2SA", "1Kgs": "1KI", "2Kgs": "2KI",
    "1Chr": "1CH", "2Chr": "2CH", "Ezra": "EZR", "Neh": "NEH",
    "Esth": "EST", "Est": "EST", "Job": "JOB", "Ps": "PSA", "Pss": "PSA",
    "Prov": "PRO", "Eccl": "ECC", "Song": "SNG", "Isa": "ISA",
    "Jer": "JER", "Lam": "LAM", "Ezek": "EZK", "Ezek": "EZK",
    "Dan": "DAN", "Hos": "HOS", "Joel": "JOL", "Amos": "AMO",
    "Obad": "OBA", "Jonah": "JON", "Jon": "JON", "Mic": "MIC",
    "Nah": "NAM", "Hab": "HAB", "Zeph": "ZEP", "Hag": "HAG",
    "Zech": "ZEC", "Mal": "MAL", "Matt": "MAT", "Mark": "MRK",
    "Luke": "LUK", "John": "JHN", "Acts": "ACT", "Rom": "ROM",
    "1Cor": "1CO", "2Cor": "2CO", "Gal": "GAL", "Eph": "EPH",
    "Phil": "PHP", "Col": "COL", "1Thess": "1TH", "2Thess": "2TH",
    "1Tim": "1TI", "2Tim": "2TI", "Titus": "TIT", "Tit": "TIT",
    "Phlm": "PHM", "Philem": "PHM", "Heb": "HEB", "Jas": "JAS",
    "1Pet": "1PE", "2Pet": "2PE", "1John": "1JN", "2John": "2JN",
    "3John": "3JN", "Jude": "JUD", "Rev": "REV",
}

# ACAI BCV8: 8-digit BBBCCVVV (book 01-66, chapter 001-999, verse 001-999).
# Bible book numbers follow the standard protestant 66-book ordering.
ACAI_BBV_TO_OSIS: Dict[str, str] = {
    f"{i+1:02d}": osis for i, osis in enumerate(CANON_OSIS_CODES)
}

# ---------------------------------------------------------------------------
# USFM parsing
# ---------------------------------------------------------------------------
# Patterns used to split and clean USFM source. Backslashes are doubled in the
# raw source string so they survive the Python regex compiler.
USFM_FOOTNOTE_RE = re.compile(r"\\f\s+(.*?)\\f\*", re.S)
USFM_REF_RE = re.compile(r"\\ref\s+([^|\\]+?)\|([^\\]+?)\\ref\*")
VERSE_MARKER_RE = re.compile(r"\\v\s+(\d+)")
CHAPTER_MARKER_RE = re.compile(r"^\\c\s+(\d+)\s*$")
USFM_HEADER_NAME_RE = re.compile(r"^\\h\s+(.+?)\s*$", re.M)
REF_TARGET_RE = re.compile(
    r"^([1-3]?[A-Z]{2,3})\s+(\d+):(\d+)(?:[-\u2013](\d+))?$"
)
# Single-chapter-book form: BOOK V or BOOK V-V (e.g. "3JN 4", "JUD 3-16").
REF_TARGET_NO_CHAPTER_RE = re.compile(
    r"^([1-3]?[A-Z]{2,3})\s+(\d+)(?:[-\u2013](\d+))?$"
)
SINGLE_CHAPTER_BOOKS = {"OBA", "PHM", "2JN", "3JN", "JUD"}
OSIS_REF_RE = re.compile(r"^[A-Z0-9]{2,3}\.\d+\.\d+(?:-[A-Z0-9]{2,3}\.\d+\.\d+|-\d+\.\d+|-\d+)?$")


def _strip_usfm_markers(text: str) -> str:
    """Remove residual USFM markers from a chunk of text."""
    text = re.sub(r"\\[a-z0-9]+\*?", "", text)
    return text


def _normalize_text(text: str) -> str:
    """Collapse whitespace and normalize non-breaking spaces."""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _normalize_run_text(text: str) -> str:
    """Normalize whitespace but do not trim (used inside ref assembly)."""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


def parse_footnote_block(raw: str) -> Dict[str, Any]:
    """Parse a single ``\\f + ... \\f*`` footnote body into structured fields.

    Returns a dict with ``ref`` (the ``\\fr`` source citation), ``text``
    (the cleaned human-readable note), and ``crossRefs`` (a list of BSB
    cross-reference dicts extracted from ``\\ref`` tags within the footnote).
    Each cross-ref dict has ``human``, ``osis`` (canonical dotted OSIS),
    ``target`` (alias of osis for downstream consumers), and
    ``source: "bsb-footnote"``.
    """
    ref_match = re.search(r"\\fr\s+(\S+)", raw)
    ref = ref_match.group(1) if ref_match else None
    text = raw.strip()
    # Strip the leading "+" caller if present.
    text = re.sub(r"^\+\s*", "", text)
    text = re.sub(r"\\fr\s+\S+\s*", "", text)
    text = re.sub(r"\\ft\s*", "", text)
    text = re.sub(r"\\fqa\s*", "", text)
    text = re.sub(r"\\fq\s*", "", text)
    text = re.sub(r"\\fk\s*", "", text)
    # Pull out cross-references before stripping the rest of the markers.
    cross_refs = extract_bsb_refs_from_text(raw)
    # Render the inline \ref tags as their human-readable form for note text.
    text = re.sub(r"\\ref\s+([^|\\]+?)\|([^\\]+?)\\ref\*", r"\1", text)
    text = _strip_usfm_markers(text)
    text = _normalize_text(text)
    return {
        "ref": ref,
        "text": text,
        "crossRefs": cross_refs,
    }


def canonical_osis_from_usfm_ref(target: str) -> Optional[str]:
    """Convert a USFM ``\\ref`` OSIS target into a canonical dotted OSIS ref.

    Accepted forms (all case-insensitive on the book code):
      * ``GEN 5:1``            -> ``GEN.5.1``
      * ``GEN 5:1-32``         -> ``GEN.5.1-GEN.5.32`` (range in same chapter)
      * ``1CH 15:29-16:3``     -> ``1CH.15.29-1CH.16.3`` (cross-chapter range)
      * ``3JN 4``              -> ``3JN.1.4`` (single-chapter book, verse only)
      * ``JUD 3-16``           -> ``JUD.1.3-JUD.1.16`` (single-chapter range)

    Returns ``None`` for non-canonical books or unparseable targets.
    """
    target = target.strip()
    # Cross-chapter range: BOOK C1:V1-C2:V2
    match = re.match(
        r"^([1-3]?[A-Z]{2,3})\s+(\d+):(\d+)[-\u2013](\d+):(\d+)$", target
    )
    if match:
        code, ch1, v1, ch2, v2 = match.groups()
        code = code.upper()
        if code not in CANON_OSIS_SET:
            return None
        return f"{code}.{int(ch1)}.{int(v1)}-{code}.{int(ch2)}.{int(v2)}"
    # Single-chapter book, verse or verse range: BOOK V or BOOK V-V
    match = REF_TARGET_NO_CHAPTER_RE.match(target)
    if match:
        code, start, end = match.groups()
        code = code.upper()
        if code in SINGLE_CHAPTER_BOOKS:
            sv = int(start)
            if end is None:
                return f"{code}.1.{sv}"
            ev = int(end)
            if ev == sv:
                return f"{code}.1.{sv}"
            return f"{code}.1.{sv}-{code}.1.{ev}"
    # Standard form: BOOK C:V or BOOK C:V-V
    match = REF_TARGET_RE.match(target)
    if not match:
        return None
    code, chapter, start, end = match.groups()
    code = code.upper()
    if code not in CANON_OSIS_SET:
        return None
    ch = int(chapter)
    sv = int(start)
    if end is None:
        return f"{code}.{ch}.{sv}"
    ev = int(end)
    if ev == sv:
        return f"{code}.{ch}.{sv}"
    return f"{code}.{ch}.{sv}-{code}.{ch}.{ev}"


def extract_bsb_refs_from_text(text: str) -> List[Dict[str, str]]:
    """Extract every ``\\ref human|osis\\ref*`` cross-reference from a footnote
    body. The human side is preserved verbatim; the osis side is normalized
    to canonical dotted OSIS form.
    """
    refs: List[Dict[str, str]] = []
    for match in USFM_REF_RE.finditer(text):
        human = _normalize_run_text(match.group(1)).strip()
        osis_target = canonical_osis_from_usfm_ref(match.group(2))
        if osis_target is None:
            # Fall back to the display text if the OSIS target omits the book
            # code (e.g. "Song of Solomon 1:1-17|1:1-17").
            osis_target = _osis_from_display_text(human)
        if osis_target is None:
            # Skip malformed targets rather than emit broken data.
            continue
        refs.append({
            "human": human,
            "osis": osis_target,
            "target": osis_target,
            "source": "bsb-footnote",
        })
    return refs


# Book-name patterns for the display-text fallback. Longest names first so
# "1 Chronicles" is not shadowed by "1 Chronicles" matching "Chronicles".
_BOOK_NAME_PATTERN = "|".join(
    re.escape(name) for name in sorted(NAME_TO_OSIS, key=len, reverse=True)
)
_DISPLAY_REF_RE = re.compile(
    rf"^({_BOOK_NAME_PATTERN})\s+(\d+):(\d+)(?:[-\u2013](\d+)(?::(\d+))?)?$"
)


def _osis_from_display_text(display: str) -> Optional[str]:
    """Best-effort parse of a human-readable reference (e.g.
    ``Song of Solomon 1:1-17``) into canonical OSIS. Used as a fallback when
    the USFM ``\\ref`` OSIS side omits the book code.
    """
    if not display:
        return None
    match = _DISPLAY_REF_RE.match(display.strip())
    if not match:
        return None
    name, chapter, start, end_a, end_b = match.groups()
    code = NAME_TO_OSIS.get(name)
    if not code:
        return None
    ch = int(chapter)
    sv = int(start)
    if end_a is None:
        return f"{code}.{ch}.{sv}"
    if end_b is not None:
        # C1:V1-C2:V2 cross-chapter range.
        return f"{code}.{ch}.{sv}-{code}.{int(end_a)}.{int(end_b)}"
    # C:V-V same-chapter range.
    ev = int(end_a)
    if ev == sv:
        return f"{code}.{ch}.{sv}"
    return f"{code}.{ch}.{sv}-{code}.{ch}.{ev}"


def parse_usfm_book(content: str, osis: str) -> Dict[str, Any]:
    """Parse a single USFM book file into a structured book dict.

    The book dict has ``osis``, ``name`` (from the OSIS mapping), ``chapters``
    (list of chapter dicts). Each chapter has ``chapter`` (int) and ``verses``
    (list of verse dicts). Each verse dict carries ``ref``, ``osis``,
    ``book``, ``bookOsis``, ``chapter``, ``verse``, ``text``, ``footnotes``
    (list), ``crossReferences`` (list, populated with bsb-footnote refs),
    ``events``, ``entities``, and ``routeLink``.

    Footnotes are attributed to the verse that textually contains the
    ``\\f`` marker. Verse text is the cleaned, marker-stripped content of each
    ``\\v`` segment. Verse segments are derived by splitting the per-chapter
    USFM body on ``\\v <digits>`` boundaries; this handles cases where a
    ``\\v`` marker is embedded in a paragraph marker line (``\\p \\v 1 ...``)
    as well as standalone verse lines.
    """
    name = OSIS_TO_NAME[osis]
    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None

    # Walk lines; split into chapters, and within each chapter collect body
    # lines (everything that is not a structural or heading marker) so we can
    # split the body on \v markers in a second pass. Cross-reference header
    # lines (\r) are captured as sentinel tokens embedded in the body so the
    # verse splitter can attribute each \ref batch to the first verse of the
    # following section.
    chapter_body_lines: List[str] = []

    structural_markers = {
        # Headings/metadata that are NOT verse body.
        "s1", "s2", "s3", "s4", "ms", "mt", "mt1", "mt2", "mt3",
        "toc1", "toc2", "toc3", "h", "id", "usfm", "ide", "cl",
        # Chapter-level / book-level markers.
        "c",
        # NOTE: "\d" (description) is intentionally NOT structural because in
        # the BSB Psalms the superscription is tagged as "\d \v 1 ..." and that
        # verse text must be preserved.
    }

    def flush_chapter_body() -> None:
        nonlocal chapter_body_lines
        if current_chapter is None or not chapter_body_lines:
            chapter_body_lines = []
            return
        body = "\n".join(chapter_body_lines)
        verses = _split_body_into_verses(body, osis, current_chapter["chapter"])
        current_chapter["verses"].extend(verses)
        chapter_body_lines = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        match = re.match(r"^\\([a-z0-9]+)\s*(.*)$", line.strip())
        if not match:
            # Continuation text with no marker - treat as body if inside a
            # chapter (rare in practice but keep for safety).
            if current_chapter is not None:
                chapter_body_lines.append(line.strip())
            continue
        marker, rest = match.groups()
        if marker == "c":
            flush_chapter_body()
            try:
                chapter_num = int(rest.strip())
            except ValueError:
                continue
            current_chapter = {
                "chapter": chapter_num,
                "verses": [],
            }
            chapters.append(current_chapter)
            continue
        if current_chapter is None:
            continue
        if marker == "r":
            # Cross-reference header line. Encode any \ref tags as a JSON
            # sentinel so the verse splitter can attach them to the next verse.
            refs = extract_bsb_refs_from_text(rest)
            if refs:
                encoded = json.dumps(refs, ensure_ascii=False,
                                     sort_keys=True, separators=(",", ":"))
                chapter_body_lines.append(
                    _SECTION_XREF_START + encoded + _SECTION_XREF_END
                )
            continue
        if marker in structural_markers:
            continue
        # Body / paragraph / poetry / list markers contribute their rest to the
        # chapter body (their rest often contains the \v marker inline).
        chapter_body_lines.append(rest.strip() if rest else "")

    flush_chapter_body()

    return {
        "osis": osis,
        "name": name,
        "chapters": chapters,
    }


def _split_body_into_verses(body: str, osis: str, chapter: int
                            ) -> List[Dict[str, Any]]:
    """Split a chapter body string on ``\\v <digits>`` markers and build one
    verse record per segment. Footnotes within each segment are attached to
    that verse. Section cross-reference sentinels (embedded from ``\\r``
    header lines) are attached to the first verse that follows them in the
    body so every ``\\ref`` tag in the source is preserved exactly once.
    """
    verses: List[Dict[str, Any]] = []
    # First, split the body at each sentinel so we know which sentinels fall
    # before each \v boundary. Then split the remaining body on \v markers.
    sentinel_pattern = re.compile(
        re.escape(_SECTION_XREF_START) + r"(.*?)" + re.escape(_SECTION_XREF_END),
        re.S,
    )
    # Walk the body left-to-right, building (clean_text, pending_xrefs) chunks
    # split at sentinel boundaries. Each sentinel's refs are queued for the
    # next verse.
    pending_section_xrefs: List[Dict[str, str]] = []
    clean_parts: List[str] = []
    pos = 0
    for m in sentinel_pattern.finditer(body):
        clean_parts.append(body[pos:m.start()])
        try:
            payload = json.loads(m.group(1))
            if isinstance(payload, list):
                pending_section_xrefs.extend(payload)
        except json.JSONDecodeError:
            pass
        # Insert a placeholder space so verse splitting still works.
        clean_parts.append(" ")
        pos = m.end()
    clean_parts.append(body[pos:])
    clean_body = "".join(clean_parts)

    # Split the cleaned body on \v N boundaries.
    segments = re.split(r"\\v\s+(\d+)", clean_body)
    for i in range(1, len(segments), 2):
        verse_num = int(segments[i])
        verse_text_raw = segments[i + 1] if i + 1 < len(segments) else ""
        osis_ref = f"{osis}.{chapter}.{verse_num}"
        # Extract footnotes, then strip markers from the visible text.
        footnotes: List[Dict[str, Any]] = []

        def _capture_fn(match: "re.Match[str]") -> str:
            footnotes.append(parse_footnote_block(match.group(1)))
            return " "

        cleaned = USFM_FOOTNOTE_RE.sub(_capture_fn, verse_text_raw)
        # Strip word-level markup (\w ... \w*).
        cleaned = re.sub(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*", r"\1", cleaned)
        cleaned = _strip_usfm_markers(cleaned)
        text = _normalize_text(cleaned)
        # Attach any pending section cross-references to the first verse parsed
        # after they appeared, then clear the queue.
        cross_refs: List[Dict[str, str]] = list(pending_section_xrefs)
        pending_section_xrefs = []
        for fn in footnotes:
            cross_refs.extend(fn.get("crossRefs", []))
        verses.append({
            "ref": osis_ref,
            "osis": osis_ref,
            "osisRef": osis_ref,
            "book": OSIS_TO_NAME[osis],
            "bookOsis": osis,
            "chapter": chapter,
            "verse": verse_num,
            "text": text,
            "footnotes": footnotes,
            "crossReferences": cross_refs,
            "events": [],
            "entities": [],
            "routeLink": f"https://route.bible/{osis_ref.lower()}",
        })
    return verses


def code_from_usfm_name(name: str) -> str:
    """Return the OSIS book code from a USFM zip entry name."""
    stem = name.rsplit("/", 1)[-1].rsplit(".", 1)[0].upper()
    return stem


def read_usfm_books(usfm_zip: Path) -> List[Tuple[str, str]]:
    """Read every .usfm file from the archive and return (osis, content) pairs
    in canonical book order.
    """
    if not usfm_zip.exists():
        raise FileNotFoundError(f"USFM source not found: {usfm_zip}")
    pairs: List[Tuple[str, str]] = []
    with zipfile.ZipFile(usfm_zip) as zf:
        names = sorted(
            (n for n in zf.namelist() if n.lower().endswith(".usfm")),
            key=lambda n: CANON_OSIS_CODES.index(code_from_usfm_name(n))
            if code_from_usfm_name(n) in CANON_OSIS_SET else 999,
        )
        for name in names:
            code = code_from_usfm_name(name)
            if code not in CANON_OSIS_SET:
                # Skip apocryphal or unexpected files.
                continue
            content = zf.read(name).decode("utf-8-sig", errors="replace")
            pairs.append((code, content))
    return pairs


def build_books_from_usfm(usfm_zip: Path) -> List[Dict[str, Any]]:
    """Parse the USFM archive into a list of structured book dicts."""
    pairs = read_usfm_books(usfm_zip)
    if not pairs:
        raise ValueError(f"No USFM book files found in {usfm_zip}")
    books: List[Dict[str, Any]] = []
    seen = set()
    for osis, content in pairs:
        if osis in seen:
            raise ValueError(f"Duplicate OSIS code in USFM archive: {osis}")
        seen.add(osis)
        books.append(parse_usfm_book(content, osis))
    return books


# ---------------------------------------------------------------------------
# Enrichment (Arweave JSONL)
# ---------------------------------------------------------------------------
def _enrichment_key_to_osis(ref: str, book: Optional[str] = None) -> Optional[str]:
    """Convert a JSONL verse key like ``Gen.1.1`` to ``GEN.1.1``.

    The JSONL ``ref`` field uses short lowercase book abbreviations that match
    the TSK/route.bible convention. We translate to canonical OSIS codes.
    """
    if not ref:
        return None
    # Try "BookAbbrev.Chapter.Verse"
    m = re.match(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$", ref)
    if not m:
        return None
    short_book, ch, vs = m.groups()
    osis = TSK_BOOK_TO_OSIS.get(short_book) or TSK_BOOK_TO_OSIS.get(
        short_book.title()
    )
    if not osis and book:
        osis = NAME_TO_OSIS.get(book)
    if not osis:
        return None
    return f"{osis}.{int(ch)}.{int(vs)}"


def fetch_enrichment(url: str, timeout: float = 30.0) -> Dict[str, Dict[str, Any]]:
    """Download and parse the Arweave JSONL enrichment feed.

    Returns a dict keyed by canonical OSIS reference (e.g. ``GEN.1.1``). Each
    value has ``events`` and ``entities`` lists. Lines that cannot be matched
    to a known verse are skipped.
    """
    import requests  # local import so module loads without network on import

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    enriched: Dict[str, Dict[str, Any]] = {}
    for line in resp.text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        osis = _enrichment_key_to_osis(obj.get("ref"), obj.get("book"))
        if not osis:
            continue
        enriched[osis] = {
            "events": list(obj.get("events", []) or []),
            "entities": list(obj.get("entities", []) or []),
        }
    return enriched


def apply_enrichment(books: List[Dict[str, Any]],
                     enrichment: Dict[str, Dict[str, Any]]) -> int:
    """Merge events/entities into verse records. Returns the enriched count."""
    enriched_count = 0
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                data = enrichment.get(verse["osis"])
                if data:
                    verse["events"] = list(data["events"])
                    verse["entities"] = list(data["entities"])
                    if data["events"] or data["entities"]:
                        enriched_count += 1
    return enriched_count


# ---------------------------------------------------------------------------
# Cross-reference aggregation
# ---------------------------------------------------------------------------
def _tsk_ref_to_osis(raw: str) -> Optional[str]:
    """Convert a TSK reference like ``Gen.1.1`` or ``Col.1.16-Col.1.17`` to
    canonical dotted OSIS. Single-verse and same-chapter ranges are supported.
    """
    raw = raw.strip()
    # Range form: Book.C.V-Book.C.V
    if "-" in raw:
        start_s, end_s = raw.split("-", 1)
        start = _tsk_single_to_osis(start_s.strip())
        end = _tsk_single_to_osis(end_s.strip())
        if not start or not end:
            return None
        if start == end:
            return start
        return f"{start}-{end}"
    return _tsk_single_to_osis(raw)


def _tsk_single_to_osis(raw: str) -> Optional[str]:
    m = re.match(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$", raw)
    if not m:
        return None
    short_book, ch, vs = m.groups()
    osis = TSK_BOOK_TO_OSIS.get(short_book)
    if not osis:
        return None
    return f"{osis}.{int(ch)}.{int(vs)}"


def fetch_tsk_cross_refs(url: str = TSK_URL,
                         timeout: float = 60.0
                         ) -> Dict[str, List[Dict[str, Any]]]:
    """Download and parse the openbible.info TSK TSV into a dict keyed by the
    source verse OSIS reference. Each value is a list of cross-ref dicts.
    """
    import requests

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    data: Dict[str, List[Dict[str, Any]]] = {}
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        tsv_name = next(
            (n for n in zf.namelist() if n.lower().endswith(".txt")),
            None,
        )
        if tsv_name is None:
            raise ValueError("TSK zip does not contain a .txt TSV member")
        with zf.open(tsv_name) as fh:
            text = fh.read().decode("utf-8", errors="replace")
    lines = text.splitlines()
    for line in lines[1:]:  # skip the header line
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        from_raw, to_raw, votes_raw = parts[0], parts[1], parts[2]
        from_osis = _tsk_ref_to_osis(from_raw)
        to_osis = _tsk_ref_to_osis(to_raw)
        if not from_osis or not to_osis:
            continue
        try:
            votes = int(votes_raw)
        except ValueError:
            votes = 0
        data.setdefault(from_osis, []).append({
            "target": to_osis,
            "osis": to_osis,
            "source": "tsk",
            "votes": votes,
            "rank": _tsk_rank(votes),
        })
    # Deterministic ordering inside each source verse list.
    for key in data:
        data[key] = sorted(
            data[key],
            key=lambda x: (-x.get("votes", 0), x.get("target", "")),
        )
    return data


def _tsk_rank(votes: int) -> str:
    if votes >= 100:
        return "tier1"
    if votes >= 50:
        return "tier2"
    if votes >= 10:
        return "tier3"
    return "tier4"


# ---------------------------------------------------------------------------
# Entity links (CC-BY-SA): ACAI + Theographic
# ---------------------------------------------------------------------------
ACAI_TYPE_DIRS = [
    "people", "places", "groups", "deities", "fauna",
    "flora", "realia", "keyterms",
]


def _acai_bcv8_to_osis(bcv: str) -> Optional[str]:
    """Convert an 8-digit BCV8 reference (BBCCCVVV) to canonical OSIS."""
    if not bcv or not bcv.isdigit() or len(bcv) != 8:
        return None
    book_num = bcv[:2]
    chapter = int(bcv[2:5])
    verse = int(bcv[5:8])
    osis = ACAI_BBV_TO_OSIS.get(book_num)
    if not osis or chapter < 1 or verse < 1:
        return None
    return f"{osis}.{chapter}.{verse}"


def fetch_acai_entity_links(base_url: str = ACAI_RAW_BASE,
                            timeout: float = 30.0
                            ) -> Dict[str, List[Dict[str, str]]]:
    """Fetch ACAI entity JSON files and build a per-verse entity-link index.

    Returns a dict keyed by OSIS verse ref; each value is a list of dicts with
    ``entity`` (the ACAI identifier like ``person:Aaron``), ``type`` (people,
    places, ...), and ``source: "acai"``.
    """
    import requests

    data: Dict[str, List[Dict[str, str]]] = {}
    for type_dir in ACAI_TYPE_DIRS:
        # List the JSON files via the GitHub contents API.
        api_url = f"https://api.github.com/repos/BibleAquifer/ACAI/contents/{type_dir}/json"
        try:
            resp = requests.get(api_url, timeout=timeout)
            resp.raise_for_status()
            files = resp.json()
        except Exception:
            continue
        if not isinstance(files, list):
            continue
        for entry in files:
            fname = entry.get("name", "")
            if not fname.endswith(".json"):
                continue
            raw_url = f"{base_url}/{type_dir}/json/{fname}"
            try:
                resp = requests.get(raw_url, timeout=timeout)
                resp.raise_for_status()
                record = resp.json()
            except Exception:
                continue
            entity_id = record.get("id") or f"{type_dir}:{entry.get('name','')}"
            entity_type = record.get("type", type_dir.rstrip("s"))
            for ref_field in ("references", "key_references"):
                for bcv in record.get(ref_field, []) or []:
                    osis = _acai_bcv8_to_osis(str(bcv))
                    if osis:
                        data.setdefault(osis, []).append({
                            "entity": entity_id,
                            "type": entity_type,
                            "source": "acai",
                        })
    for key in data:
        data[key] = sorted(data[key], key=lambda x: (x["entity"], x["type"]))
    return data


def _theographic_osis_to_canonical(ref: str) -> Optional[str]:
    """Convert a Theographic ``osisRef`` like ``Gen.1.1`` to ``GEN.1.1``."""
    return _tsk_ref_to_osis(ref) if "." in ref and ref.count(".") >= 2 else None


def fetch_theographic_entity_links(url: str = THEOGRAPHIC_VERSES_URL,
                                   timeout: float = 120.0
                                   ) -> Dict[str, List[Dict[str, str]]]:
    """Fetch the Theographic verses.json and build a per-verse entity-link
    index. Each entry references the foreign-key record ids in the
    ``people``/``places``/``event`` fields.
    """
    import requests

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    records = resp.json()
    if not isinstance(records, list):
        return {}
    data: Dict[str, List[Dict[str, str]]] = {}
    for record in records:
        fields = record.get("fields", {}) or {}
        osis = _theographic_osis_to_canonical(fields.get("osisRef", ""))
        if not osis:
            continue
        for fk_field, type_label in (("people", "person"),
                                     ("places", "place"),
                                     ("event", "event")):
            for fk in fields.get(fk_field, []) or []:
                if not isinstance(fk, str):
                    continue
                data.setdefault(osis, []).append({
                    "entity": f"{type_label}:{fk}",
                    "type": type_label,
                    "source": "theographic",
                })
    for key in data:
        data[key] = sorted(data[key], key=lambda x: (x["entity"], x["type"]))
    return data


# ---------------------------------------------------------------------------
# Cross-ref / entity-link index assembly
# ---------------------------------------------------------------------------
def build_cross_refs_index(
    books: List[Dict[str, Any]],
    tsk: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Assemble the cross-references index.

    Only CC0 (bsb-footnote) and CC-BY (tsk) sources go into this index. CC-BY-SA
    data (acai, theographic) is intentionally excluded to maintain license
    isolation. Every cross-ref object carries a ``source`` field.
    """
    index: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    # Seed every verse with at least an empty list to guarantee schema
    # consistency (VAL-DATA-041).
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                index[verse["osis"]] = {"crossReferences": []}
    # BSB footnote cross-references (already attached per verse).
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                refs = verse.get("crossReferences") or []
                if refs:
                    index[verse["osis"]]["crossReferences"].extend(refs)
    # TSK cross-references (CC-BY).
    if tsk:
        for src_osis, entries in tsk.items():
            if src_osis not in index:
                # TSK covers verses that exist in the canon; skip if unknown.
                continue
            index[src_osis]["crossReferences"].extend(entries)
    # Deterministic ordering by source then target.
    for key in index:
        index[key]["crossReferences"] = sorted(
            index[key]["crossReferences"],
            key=lambda x: (
                x.get("source", ""),
                -int(x.get("votes", 0)) if isinstance(x.get("votes"), int) else 0,
                x.get("target", ""),
            ),
        )
    return index


def attach_cross_refs_to_verses(
    books: List[Dict[str, Any]],
    cross_refs_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
) -> None:
    """Mirror BSB-footnote cross-references back onto each verse record so
    that the unified dataset exposes ``crossReferences`` directly per verse.
    Only ``bsb-footnote`` source refs are attached inline to keep the unified
    dataset compact; the full cross-reference index (including TSK) lives in
    ``cross-refs.json``.
    """
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                entry = cross_refs_index.get(verse["osis"])
                if entry:
                    verse["crossReferences"] = [
                        xr for xr in entry["crossReferences"]
                        if xr.get("source") == "bsb-footnote"
                    ]
                else:
                    verse["crossReferences"] = []


def build_entity_links_index(
    acai: Optional[Dict[str, List[Dict[str, str]]]] = None,
    theographic: Optional[Dict[str, List[Dict[str, str]]]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """Merge ACAI and Theographic entity-link data into a single per-verse
    index. Both sources are CC-BY-SA and live only in ``entity-links.json``.
    """
    merged: Dict[str, List[Dict[str, str]]] = {}
    for source in (acai, theographic):
        if not source:
            continue
        for osis, entries in source.items():
            merged.setdefault(osis, []).extend(entries)
    for key in merged:
        merged[key] = sorted(merged[key], key=lambda x: (x["source"], x["entity"], x["type"]))
    return merged


# ---------------------------------------------------------------------------
# Output assembly & deterministic JSON writers
# ---------------------------------------------------------------------------
def _dumps_json(obj: Any) -> str:
    """Serialize ``obj`` to deterministic JSON (sorted keys, fixed indent)."""
    return json.dumps(obj, ensure_ascii=JSON_ENSURE_ASCII,
                      indent=JSON_INDENT, sort_keys=True)


def write_json(path: Path, obj: Any) -> None:
    """Write ``obj`` as deterministic JSON to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dumps_json(obj) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_dataset_hash(books: List[Dict[str, Any]]) -> str:
    """Hash the canonical JSON representation of the unified dataset."""
    dataset_obj = {
        "books": books,
        "metadata": build_dataset_metadata(books),
    }
    return sha256_bytes(_dumps_json(dataset_obj).encode("utf-8"))


def build_dataset_metadata(books: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_verses = sum(
        len(ch["verses"]) for book in books for ch in book["chapters"]
    )
    total_chapters = sum(len(book["chapters"]) for book in books)
    total_footnotes = sum(
        len(v.get("footnotes", []))
        for book in books for ch in book["chapters"] for v in ch["verses"]
    )
    bsb_cross_refs = sum(
        len(v.get("crossReferences", []))
        for book in books for ch in book["chapters"] for v in ch["verses"]
    )
    return {
        "totalBooks": len(books),
        "totalChapters": total_chapters,
        "totalVerses": total_verses,
        "totalFootnotes": total_footnotes,
        "totalBsbCrossReferences": bsb_cross_refs,
    }


def build_manifest(books: List[Dict[str, Any]],
                   cross_refs: Dict[str, Dict[str, List[Dict[str, Any]]]],
                   entity_links: Dict[str, List[Dict[str, str]]],
                   source_versions: Dict[str, Any],
                   build_hash: str) -> Dict[str, Any]:
    """Assemble the manifest dict. Does not include timestamps or random
    values so the build is deterministic.
    """
    meta = build_dataset_metadata(books)
    book_entries = []
    for book in books:
        chapters = book.get("chapters", [])
        verse_count = sum(len(ch["verses"]) for ch in chapters)
        footnote_count = sum(
            len(v.get("footnotes", [])) for ch in chapters for v in ch["verses"]
        )
        cross_ref_count = sum(
            len(v.get("crossReferences", []))
            for ch in chapters for v in ch["verses"]
        )
        book_entries.append({
            "osis": book["osis"],
            "name": book["name"],
            "chapterCount": len(chapters),
            "verseCount": verse_count,
            "footnoteCount": footnote_count,
            "crossReferenceCount": cross_ref_count,
        })
    # Per-source cross-ref tallies.
    tsk_total = sum(
        1 for entry in cross_refs.values()
        for xr in entry.get("crossReferences", [])
        if xr.get("source") == "tsk"
    )
    bsb_total = sum(
        1 for entry in cross_refs.values()
        for xr in entry.get("crossReferences", [])
        if xr.get("source") == "bsb-footnote"
    )
    acai_total = sum(
        1 for entries in entity_links.values()
        for e in entries if e.get("source") == "acai"
    )
    theo_total = sum(
        1 for entries in entity_links.values()
        for e in entries if e.get("source") == "theographic"
    )
    manifest = {
        "books": book_entries,
        "totalBooks": meta["totalBooks"],
        "totalChapters": meta["totalChapters"],
        "totalVerses": meta["totalVerses"],
        "totalFootnotes": meta["totalFootnotes"],
        "totalBsbCrossReferences": bsb_total,
        "totalTskCrossReferences": tsk_total,
        "totalAcaiEntityLinks": acai_total,
        "totalTheographicMentions": theo_total,
        "totalEntityLinks": acai_total + theo_total,
        "buildHash": build_hash,
        "buildHashScheme": "sha256-of-bsb-dataset.json",
        "sourceVersions": source_versions,
    }
    return manifest


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------
def write_outputs(output_dir: Path,
                  books: List[Dict[str, Any]],
                  cross_refs: Dict[str, Dict[str, List[Dict[str, Any]]]],
                  entity_links: Dict[str, List[Dict[str, str]]],
                  manifest: Dict[str, Any]) -> None:
    """Write all output artifacts deterministically to ``output_dir``."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Unified dataset.
    dataset_obj = {
        "books": books,
        "metadata": manifest,
    }
    write_json(output_dir / "bsb-dataset.json", dataset_obj)

    # Per-book / per-chapter / per-verse files.
    books_dir = output_dir / "books"
    for book in books:
        write_json(books_dir / f"{book['osis']}.json", book)
        book_chapters_dir = books_dir / book["osis"] / "chapters"
        book_verses_dir = books_dir / book["osis"] / "verses"
        for chapter in book["chapters"]:
            write_json(book_chapters_dir / f"{chapter['chapter']}.json", chapter)
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                fname = f"{verse['osisRef']}.json"
                write_json(book_verses_dir / fname, verse)

    # Cross-references and entity links.
    write_json(output_dir / "cross-refs.json", cross_refs)
    write_json(output_dir / "entity-links.json", entity_links)

    # Manifest last so its buildHash reflects the dataset content.
    write_json(output_dir / "manifest.json", manifest)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_outputs(books: List[Dict[str, Any]],
                     cross_refs: Dict[str, Dict[str, List[Dict[str, Any]]]],
                     entity_links: Dict[str, List[Dict[str, str]]]) -> None:
    """Run integrity checks that would otherwise produce silently corrupt
    output. Raises ``AssertionError`` on any structural problem.
    """
    # Book count.
    assert len(books) == 66, f"Expected 66 books, got {len(books)}"
    osis_seen = {book["osis"] for book in books}
    missing = CANON_OSIS_SET - osis_seen
    extra = osis_seen - CANON_OSIS_SET
    assert not missing, f"Missing OSIS books: {sorted(missing)}"
    assert not extra, f"Unexpected OSIS books: {sorted(extra)}"

    # Verse + footnote counts.
    total_verses = 0
    total_footnotes = 0
    bsb_cross_refs = 0
    for book in books:
        for chapter in book["chapters"]:
            for verse in chapter["verses"]:
                total_verses += 1
                # Required fields on every verse.
                for field in ("ref", "osis", "book", "bookOsis",
                              "chapter", "verse", "text"):
                    assert field in verse, (
                        f"Verse {verse.get('osis')} missing field {field}"
                    )
                # Footnotes are always a list.
                assert isinstance(verse.get("footnotes"), list)
                total_footnotes += len(verse["footnotes"])
                for fn in verse["footnotes"]:
                    assert fn.get("text", "").strip(), (
                        f"Empty footnote in {verse['osis']}"
                    )
                assert isinstance(verse.get("crossReferences"), list)
                for xr in verse["crossReferences"]:
                    assert xr.get("source") in KNOWN_SOURCES, (
                        f"Unknown source {xr.get('source')} in {verse['osis']}"
                    )
                    if xr.get("source") == "bsb-footnote":
                        bsb_cross_refs += 1
    assert total_footnotes == 4854, (
        f"Expected 4854 footnotes, got {total_footnotes}"
    )
    # BSB cross-references: 3,283 \\ref tags appear in the source, but 7
    # reference non-canonical books (1 Enoch, Jasher, 1 Esdras) and cannot be
    # mapped to valid OSIS targets. 3,271 is the count of canonical refs.
    assert bsb_cross_refs == 3271, (
        f"Expected 3271 bsb-footnote cross-refs, got {bsb_cross_refs}"
    )

    # License isolation: no CC-BY-SA source in cross-refs.json.
    for ref, entry in cross_refs.items():
        for xr in entry.get("crossReferences", []):
            assert xr.get("source") not in CC_BY_SA_SOURCES, (
                f"License violation: {xr.get('source')} in cross-refs.json at {ref}"
            )


# ---------------------------------------------------------------------------
# Build orchestration
# ---------------------------------------------------------------------------
def build_dataset(usfm_zip: Path,
                  output_dir: Path,
                  enrichment_url: Optional[str] = DEFAULT_ENRICHMENT_URL,
                  fetch_tsk: bool = True,
                  fetch_acai: bool = True,
                  fetch_theographic: bool = True,
                  usfm_source_hash: Optional[str] = None,
                  log=print) -> Dict[str, Any]:
    """Run the full dataset build pipeline and write outputs to ``output_dir``.

    External fetches are best-effort: if TSK/ACAI/Theographic are unreachable
    the build proceeds without them and records the failure in the manifest.
    If ``enrichment_url`` is falsy or unreachable the build still completes
    with empty events/entities arrays on every verse.
    """
    log(f"[build_dataset] Reading USFM from {usfm_zip}")
    usfm_hash = usfm_source_hash or sha256_file(usfm_zip)
    source_versions: Dict[str, Any] = {
        "usfm": {
            "path": str(usfm_zip),
            "sha256": usfm_hash,
        },
    }
    fetch_warnings: List[str] = []

    # 1. Parse USFM into structured books.
    books = build_books_from_usfm(usfm_zip)
    meta = build_dataset_metadata(books)
    log(f"[build_dataset] Parsed {meta['totalBooks']} books, "
        f"{meta['totalVerses']} verses, {meta['totalFootnotes']} footnotes, "
        f"{meta['totalBsbCrossReferences']} BSB cross-refs")

    # 2. Enrich with Arweave JSONL.
    if enrichment_url:
        try:
            enrichment = fetch_enrichment(enrichment_url)
            enriched_count = apply_enrichment(books, enrichment)
            source_versions["enrichmentJsonl"] = {
                "url": enrichment_url,
                "records": len(enrichment),
                "enrichedVerses": enriched_count,
            }
            log(f"[build_dataset] Applied enrichment to {enriched_count} verses")
        except Exception as exc:  # graceful degradation
            fetch_warnings.append(f"enrichment failed: {exc}")
            log(f"[build_dataset] WARNING: enrichment skipped ({exc})")

    # 3. TSK cross-references (CC-BY).
    tsk_index: Optional[Dict[str, List[Dict[str, Any]]]] = None
    if fetch_tsk:
        try:
            tsk_index = fetch_tsk_cross_refs()
            tsk_total = sum(len(v) for v in tsk_index.values())
            source_versions["tsk"] = {
                "url": TSK_URL,
                "pairs": tsk_total,
            }
            log(f"[build_dataset] Loaded {tsk_total} TSK cross-ref pairs")
        except Exception as exc:
            fetch_warnings.append(f"tsk failed: {exc}")
            log(f"[build_dataset] WARNING: TSK skipped ({exc})")

    # 4. ACAI entity links (CC-BY-SA).
    acai_index: Optional[Dict[str, List[Dict[str, str]]]] = None
    if fetch_acai:
        try:
            acai_index = fetch_acai_entity_links()
            acai_total = sum(len(v) for v in acai_index.values())
            source_versions["acai"] = {
                "url": ACAI_RAW_BASE,
                "links": acai_total,
            }
            log(f"[build_dataset] Loaded {acai_total} ACAI entity links")
        except Exception as exc:
            fetch_warnings.append(f"acai failed: {exc}")
            log(f"[build_dataset] WARNING: ACAI skipped ({exc})")

    # 5. Theographic mentions (CC-BY-SA).
    theo_index: Optional[Dict[str, List[Dict[str, str]]]] = None
    if fetch_theographic:
        try:
            theo_index = fetch_theographic_entity_links()
            theo_total = sum(len(v) for v in theo_index.values())
            source_versions["theographic"] = {
                "url": THEOGRAPHIC_VERSES_URL,
                "mentions": theo_total,
            }
            log(f"[build_dataset] Loaded {theo_total} Theographic mentions")
        except Exception as exc:
            fetch_warnings.append(f"theographic failed: {exc}")
            log(f"[build_dataset] WARNING: Theographic skipped ({exc})")

    # 6. Assemble cross-refs.json (CC0 + CC-BY only) and entity-links.json.
    cross_refs_index = build_cross_refs_index(books, tsk_index)
    entity_links_index = build_entity_links_index(acai_index, theo_index)
    attach_cross_refs_to_verses(books, cross_refs_index)

    # 7. Structural validation (raises on hard failures).
    validate_outputs(books, cross_refs_index, entity_links_index)

    # 8. Manifest + build hash.
    build_hash = compute_dataset_hash(books)
    manifest = build_manifest(
        books, cross_refs_index, entity_links_index, source_versions, build_hash
    )
    manifest["warnings"] = sorted(fetch_warnings)

    # 9. Write outputs.
    write_outputs(output_dir, books, cross_refs_index, entity_links_index, manifest)
    log(f"[build_dataset] Wrote outputs to {output_dir}")
    log(f"[build_dataset] Build hash: {build_hash}")
    return manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bsb-build-dataset",
        description="Build the BSB JSON dataset from USFM source.",
    )
    parser.add_argument(
        "--usfm", type=Path, default=DEFAULT_USFM,
        help=f"Path to the USFM zip (default: {DEFAULT_USFM})",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--enrichment-url", default=DEFAULT_ENRICHMENT_URL,
        help="Arweave JSONL enrichment URL (pass 'none' to disable)",
    )
    fetch_group = parser.add_argument_group("external sources")
    fetch_group.add_argument(
        "--no-tsk", action="store_true",
        help="Skip TSK cross-reference download",
    )
    fetch_group.add_argument(
        "--no-acai", action="store_true",
        help="Skip ACAI entity link download",
    )
    fetch_group.add_argument(
        "--no-theographic", action="store_true",
        help="Skip Theographic mentions download",
    )
    fetch_group.add_argument(
        "--offline", action="store_true",
        help="Skip all external network fetches (enrichment + sources)",
    )
    args = parser.parse_args(argv)

    if not args.usfm.exists():
        print(f"ERROR: USFM source not found: {args.usfm}", file=sys.stderr)
        return 2

    enrichment_url = None if args.offline or args.enrichment_url == "none" else args.enrichment_url
    try:
        build_dataset(
            usfm_zip=args.usfm.resolve(),
            output_dir=args.output.resolve(),
            enrichment_url=enrichment_url,
            fetch_tsk=not args.offline and not args.no_tsk,
            fetch_acai=not args.offline and not args.no_acai,
            fetch_theographic=not args.offline and not args.no_theographic,
        )
    except AssertionError as exc:
        print(f"ERROR: validation failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
