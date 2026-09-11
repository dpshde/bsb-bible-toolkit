#!/usr/bin/env python3
"""Compose a compact travel BSB from this toolkit's USFM via Typst.

The loved-face print target requires licensed FF Milo Serif Text desktop
fonts in ``fonts/milo/``. It will not download, scrape, subset, or silently
substitute another face (including Source Serif or Lexend).

``--grid-proof`` is a separate, opt-in metrics compile. It uses a labeled
OFL stand-in (Source Serif 4). That PDF is never the loved face.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .add_route_links import build_url
from .download_bsb import BOOK_NAMES
from .generate_typst_pdf import (
    BOOK_ORDER,
    NEW_TESTAMENT_START,
    clean_spaces,
    heading_ranges,
    parse_ref_runs,
    parse_usfm_zip,
    strip_osis_display_tails,
    typst_escape,
    typst_string,
    usfm_code_from_name,
)
from .generate_reflow_pdf import USFM_TO_BOOK

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_USFM = REPO_ROOT / "drafts" / "primary" / "source" / "engbsb_usfm.zip"
DEFAULT_PDF = REPO_ROOT / "drafts" / "travel" / "bsb-travel-john.pdf"
DEFAULT_TYPST = REPO_ROOT / "drafts" / "travel" / "work" / "john.typ"
DEFAULT_FONT_DIR = REPO_ROOT / "fonts" / "milo"
DEFAULT_GRID_PDF = REPO_ROOT / "drafts" / "travel" / "bsb-travel-john-grid-proof.pdf"
DEFAULT_GRID_TYPST = REPO_ROOT / "drafts" / "travel" / "work" / "john-grid-proof.typ"
DEFAULT_GRID_FONT_DIR = REPO_ROOT / "fonts" / "grid-proof"
DEFAULT_BIBLE_PDF = REPO_ROOT / "drafts" / "travel" / "bsb-travel-bible.pdf"
DEFAULT_BIBLE_TYPST = REPO_ROOT / "drafts" / "travel" / "work" / "bible.typ"
DEFAULT_BIBLE_GRID_PDF = REPO_ROOT / "drafts" / "travel" / "bsb-travel-bible-grid-proof.pdf"
DEFAULT_BIBLE_GRID_TYPST = REPO_ROOT / "drafts" / "travel" / "work" / "bible-grid-proof.typ"
USFM_URL = "https://bereanbible.com/bsb_usfm.zip"
PROTESTANT_CANON = tuple(BOOK_NAMES[number] for number in range(1, 67))
SAMPLE_SUBTITLE = "Travel print sample · 4.75 × 7 in"

MILO_TEXT_FAMILY = "FF Milo Serif Text"
MILO_HEAD_FAMILY = "FF Milo Serif"
MILO_TEXT_ALIAS = "MiloSerif-Text"

GRID_PROOF_WATERMARK = "GRID PROOF — NOT FINAL FACE"
GRID_PROOF_FAMILY = "Source Serif 4"
GRID_PROOF_NOTE = (
    "Stand-in face: Source Serif 4 (SIL OFL 1.1). "
    "Loved face: FF Milo Serif Text."
)

FONT_MISSING_MESSAGE = (
    "Place licensed desktop OTFs from FontFont/MyFonts here "
    "(Text + Text Italic minimum; Regular/Bold for heads). "
    "Desktop license, 1 workstation."
)

GRID_PROOF_FONT_MISSING_MESSAGE = (
    "Place SIL OFL Source Serif 4 Regular + Italic in fonts/grid-proof/ "
    "for a metrics compile. This stand-in is never the loved face."
)

WJ_TOKEN_RE = re.compile(
    r"(\\f\s+.*?\\f\*)|(\\wj\*)|(\\wj)|(\\v\s+(\d+))",
    re.S,
)
WORD_MARKER_RE = re.compile(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*")
NAMED_SPAN_RE = re.compile(r"\\(nd|qs)\s*(.+?)\\\1\*", re.S)
RESIDUAL_MARKER_RE = re.compile(r"\\(?!ref\b|f\b|f\*|wj\b)[a-z0-9]+\*?\s*")
FOOTNOTE_RE = re.compile(r"\\f\s+(.*?)\\f\*", re.S)
# USFM sometimes inserts a one-word `\p Next:` genealogy break. Not body text.
SOURCE_NAV_MARKER_RE = re.compile(r"^next\s*:\s*$", re.I)
KEEP_REF_MARKER_RE = re.compile(r"\\(?!ref\b)[a-z0-9]+\*?")


@dataclass(frozen=True)
class TravelSpec:
    """Page and type constants. Keep in lockstep with drafts/travel/SPEC.md."""

    trim_width_in: float = 4.75
    trim_height_in: float = 7.0
    margin_inside_in: float = 0.55
    margin_outside_in: float = 0.40
    margin_head_in: float = 0.50
    margin_foot_in: float = 0.375
    body_pt: float = 8.5
    baseline_pt: float = 10.5
    lines_per_page: int = 42
    measure_in: float = 3.80
    target_cpl_min: int = 60
    target_cpl_max: int = 70
    drop_lines: int = 3
    footnote_pt: float = 7.0
    footnote_baseline_pt: float = 8.5
    footnote_ink_rgb: tuple[int, int, int] = (76, 76, 76)
    running_head_pt: float = 7.0
    folio_pt: float = 7.0
    section_pt: float = 8.5
    xref_pt: float = 7.0
    verse_pt: float = 6.0
    title_pt: float = 14.0
    woc_rgb: tuple[int, int, int] = (28, 56, 110)
    ink_rgb: tuple[int, int, int] = (20, 20, 20)
    body_font: str = MILO_TEXT_FAMILY
    body_font_alias: str = MILO_TEXT_ALIAS
    head_font: str = MILO_HEAD_FAMILY
    hyphen_lang: str = "en"
    # 120% left the 60–70 cpl travel measure almost unhyphenated (2 breaks
    # in 49 John pages). 80% is still conservative vs Typst's 50% eagerness.
    hyphenation_cost_pct: int = 80
    # Tiny extra leading on body prose only. Poetry / drop geometry stay
    # on the 10.5 pt structural grid (leading-gap = baseline − body).
    body_leading_extra_pt: float = 0.35


SPEC = TravelSpec()


def select_travel_books(*, all_books: bool = False, book_args=None, testament: str = "all") -> list[str]:
    """Choose John, explicit ``--book`` values, or the 66-book Protestant canon."""
    if all_books and book_args:
        raise ValueError("use --all-books or --book, not both")
    if all_books:
        names = list(PROTESTANT_CANON)
    elif book_args:
        names = list(book_args)
    else:
        names = ["John"]
    if testament == "all":
        return names
    if testament == "ot":
        return [name for name in names if BOOK_ORDER.get(name, 999) < NEW_TESTAMENT_START]
    if testament == "nt":
        return [name for name in names if BOOK_ORDER.get(name, 0) >= NEW_TESTAMENT_START]
    raise ValueError(f"Unknown testament: {testament}")


def usfm_zip_book_count(usfm_zip: Path) -> int:
    with zipfile.ZipFile(usfm_zip) as archive:
        return sum(
            1
            for name in archive.namelist()
            if name.lower().endswith(".usfm") and USFM_TO_BOOK.get(usfm_code_from_name(name))
        )


def default_output_paths(*, grid_proof: bool, all_books: bool, testament: str = "all"):
    """John defaults stay put; full-Bible / testament compiles use distinct paths."""
    testament_suffix = ""
    if testament == "ot":
        testament_suffix = "-ot"
    elif testament == "nt":
        testament_suffix = "-nt"
    if all_books or testament != "all":
        stem = f"bible{testament_suffix}"
        if grid_proof:
            return (
                REPO_ROOT / "drafts" / "travel" / f"bsb-travel-{stem}-grid-proof.pdf",
                REPO_ROOT / "drafts" / "travel" / "work" / f"{stem}-grid-proof.typ",
                DEFAULT_GRID_FONT_DIR,
            )
        return (
            REPO_ROOT / "drafts" / "travel" / f"bsb-travel-{stem}.pdf",
            REPO_ROOT / "drafts" / "travel" / "work" / f"{stem}.typ",
            DEFAULT_FONT_DIR,
        )
    if grid_proof:
        return DEFAULT_GRID_PDF, DEFAULT_GRID_TYPST, DEFAULT_GRID_FONT_DIR
    return DEFAULT_PDF, DEFAULT_TYPST, DEFAULT_FONT_DIR


def leading_gap_pt(spec: TravelSpec = SPEC) -> float:
    """Typst ``par.leading`` is the gap between line boxes, not baselineskip."""
    return spec.baseline_pt - spec.body_pt


def body_leading_gap_pt(spec: TravelSpec = SPEC) -> float:
    """Body-prose leading. Slightly looser than the 10.5 pt structural grid."""
    return leading_gap_pt(spec) + spec.body_leading_extra_pt


def measure_em(spec: TravelSpec = SPEC) -> float:
    return spec.measure_in * 72.0 / spec.body_pt


class MiloFontError(Exception):
    """Raised when licensed Milo files are missing."""

    exit_code = 2

    def __init__(self, font_dir: Path):
        self.font_dir = font_dir
        super().__init__(f"{font_dir}: {FONT_MISSING_MESSAGE}")


class GridProofFontError(Exception):
    """Raised when the labeled OFL stand-in for a grid proof is missing."""

    exit_code = 2

    def __init__(self, font_dir: Path):
        self.font_dir = font_dir
        super().__init__(f"{font_dir}: {GRID_PROOF_FONT_MISSING_MESSAGE}")


def _norm_name(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "", path.name.lower())


def _is_font_file(path: Path) -> bool:
    return path.suffix.lower() in {".otf", ".ttf", ".woff", ".woff2"}


def classify_milo_fonts(font_dir: Path) -> dict[str, list[Path]]:
    """Classify desktop files in <font_dir>. Names must look like Milo/FF Milo."""
    found = {"text": [], "text-italic": [], "regular": [], "bold": [], "other-milo": []}
    if not font_dir.is_dir():
        return found
    for path in sorted(font_dir.iterdir()):
        if not path.is_file() or not _is_font_file(path):
            continue
        token = _norm_name(path)
        if "sourceserif" in token or "lexend" in token:
            continue
        if "milo" not in token:
            continue
        italic = any(hint in token for hint in ("italic", "oblique"))
        if "text" in token and italic:
            found["text-italic"].append(path)
        elif "text" in token:
            found["text"].append(path)
        elif italic:
            found["other-milo"].append(path)
        elif "bold" in token:
            found["bold"].append(path)
        elif "regular" in token or token.endswith("miloserif.otf") or token.endswith("miloserif.ttf"):
            found["regular"].append(path)
        else:
            found["other-milo"].append(path)
    return found


def require_milo_fonts(font_dir: Path) -> dict[str, list[Path]]:
    """Fail closed unless Text + Text Italic desktop files are present."""
    found = classify_milo_fonts(font_dir)
    if not found["text"] or not found["text-italic"]:
        raise MiloFontError(font_dir)
    return found


def _is_source_serif_file(path: Path) -> bool:
    token = _norm_name(path)
    return "sourceserif" in token


def classify_grid_proof_fonts(font_dir: Path) -> dict[str, list[Path]]:
    """Classify the labeled OFL stand-in. Never accept Milo as that stand-in."""
    found = {"regular": [], "italic": [], "bold": [], "other": []}
    if not font_dir.is_dir():
        return found
    for path in sorted(font_dir.iterdir()):
        if not path.is_file() or not _is_font_file(path):
            continue
        token = _norm_name(path)
        if "milo" in token or not _is_source_serif_file(path):
            continue
        stem = path.stem.lower()
        italic = (
            "italic" in token
            or "oblique" in token
            or stem.endswith("-it")
            or stem.endswith("it")
        )
        if italic:
            found["italic"].append(path)
        elif "bold" in token:
            found["bold"].append(path)
        elif "regular" in token or "roman" in token:
            found["regular"].append(path)
        else:
            found["other"].append(path)
    return found


def require_grid_proof_fonts(font_dir: Path) -> dict[str, list[Path]]:
    """Fail unless Source Serif 4 Regular + Italic are present for a grid proof."""
    found = classify_grid_proof_fonts(font_dir)
    if not found["regular"] or not found["italic"]:
        raise GridProofFontError(font_dir)
    return found


def ensure_usfm_zip(path: Path, download: bool = False) -> Path:
    if path.exists():
        return path
    if not download:
        raise FileNotFoundError(
            f"BSB USFM source not found: {path}\n"
            f"Download the official archive from {USFM_URL} "
            f"or rerun with --download-usfm."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        import urllib.request
    except ImportError as exc:  # pragma: no cover
        raise FileNotFoundError(f"Cannot download USFM: {exc}") from exc
    print(f"Downloading official BSB USFM from {USFM_URL} ...")
    urllib.request.urlretrieve(USFM_URL, path)
    return path


def is_hebrew_script(text: str) -> bool:
    """True when visible letters are Hebrew (Psalm 119 ``\\qa א`` stand-ins)."""
    letters = [char for char in text if char.isalpha()]
    return bool(letters) and all("\u0590" <= char <= "\u05FF" for char in letters)


def strip_word_markers(text: str) -> str:
    return WORD_MARKER_RE.sub(r"\1", text)


def is_source_nav_marker(text: str) -> bool:
    r"""True for leftover USFM `\p Next:` genealogy markers (not body text)."""
    cleaned = clean_spaces(KEEP_REF_MARKER_RE.sub(" ", text or ""))
    cleaned = strip_osis_display_tails(cleaned)
    return bool(SOURCE_NAV_MARKER_RE.match(cleaned))


def _footnote_plain(text: str) -> str:
    text = re.sub(r"\\ft\s*", " ", text)
    return clean_spaces(KEEP_REF_MARKER_RE.sub(" ", text))


def footnote_markup(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^\+\s*", "", raw)
    raw = re.sub(r"\\fr\s+\S+\s*", "", raw)
    parts = []
    pos = 0
    # Keep `\\ft` in the working string so it still terminates `\\fqa`.
    # Stripping it first lets the last italic gloss swallow `\\ref`.
    pattern = re.compile(r"\\fqa\s+(.*?)(?=\\ft\b|\\fqa\b|\\ref\b|$)", re.S)
    for match in pattern.finditer(raw):
        if match.start() > pos:
            prefix = parse_ref_runs(_footnote_plain(raw[pos:match.start()]))
            if prefix:
                parts.append(prefix)
        emph = strip_osis_display_tails(_footnote_plain(match.group(1)))
        if emph:
            parts.append(f"#emph[{typst_escape(emph)}]")
        pos = match.end()
    if pos < len(raw):
        tail = parse_ref_runs(_footnote_plain(raw[pos:]))
        if tail:
            parts.append(tail)
    content = " ".join(part for part in parts if part).strip()
    # Close the space before commas. Keep a space before ";" after `#emph[...]`
    # so Typst does not treat the semicolon as a statement terminator.
    content = re.sub(r"\s+,", ",", content)
    return content


def render_text_chunk(raw: str) -> str:
    if not raw:
        return ""
    text = strip_word_markers(raw)
    pieces = []
    pos = 0
    for match in NAMED_SPAN_RE.finditer(text):
        if match.start() > pos:
            pieces.append(parse_ref_runs(_plain_chunk(text[pos:match.start()])))
        inner = clean_spaces(match.group(2))
        if inner:
            escaped = typst_escape(inner)
            if match.group(1) == "nd":
                pieces.append(f"#divine[{escaped}]")
            else:
                pieces.append(f"#emph[{escaped}]")
        pos = match.end()
    if pos < len(text):
        pieces.append(parse_ref_runs(_plain_chunk(text[pos:])))
    return "".join(pieces)


def _plain_chunk(text: str) -> str:
    text = RESIDUAL_MARKER_RE.sub("", text)
    text = text.replace("\\+", "")
    return text


def xref_markup(raw: str) -> str:
    text = clean_spaces(raw)
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    return parse_ref_runs(text)


def wrap_woc(inner: str, woc: bool) -> str:
    if not inner or not inner.strip():
        return ""
    if not woc:
        return inner
    return f"#woc[{inner}]"


def travel_inline(raw: str, woc: bool = False) -> tuple[str, bool]:
    """Render one verse/prefix chunk. Returns (typst, woc_open_after)."""
    out = []
    pos = 0
    for match in FOOTNOTE_RE.finditer(raw):
        if match.start() > pos:
            chunk = render_text_chunk(raw[pos:match.start()])
            if chunk:
                out.append(wrap_woc(chunk, woc))
        suffix = " " if raw[match.end():match.end() + 1] == "(" else ""
        out.append(f"#footnote[{footnote_markup(match.group(1))}]{suffix}")
        pos = match.end()
    if pos < len(raw):
        chunk = render_text_chunk(raw[pos:])
        if chunk:
            out.append(wrap_woc(chunk, woc))
    return "".join(out), woc


def verse_segments_travel(raw: str, osis: str, chapter: int):
    """Split a paragraph on verse markers while tracking ``\\wj`` state."""
    prepared = strip_word_markers(raw)
    tokens = []
    pos = 0
    for match in WJ_TOKEN_RE.finditer(prepared):
        if match.start() > pos:
            tokens.append(("text", prepared[pos:match.start()]))
        if match.group(1):
            tokens.append(("footnote", match.group(1)))
        elif match.group(2):
            tokens.append(("wj-close", ""))
        elif match.group(3):
            tokens.append(("wj-open", ""))
        else:
            tokens.append(("verse", int(match.group(5))))
        pos = match.end()
    if pos < len(prepared):
        tokens.append(("text", prepared[pos:]))

    segments = []
    current_verse = None
    current_url = None
    buf = []
    woc = False

    def flush():
        nonlocal buf
        body = "".join(buf).strip()
        buf = []
        if current_verse is None and not body:
            return
        segments.append((current_verse, current_url, body))

    for kind, value in tokens:
        if kind == "wj-open":
            woc = True
        elif kind == "wj-close":
            woc = False
        elif kind == "verse":
            flush()
            current_verse = value
            current_url = build_url(osis, chapter, value, value)
        elif kind == "footnote":
            inner, _ = travel_inline(value, woc=False)
            buf.append(inner)
        else:
            inner, _ = travel_inline(value, woc=woc)
            if inner:
                buf.append(inner)
    flush()
    if segments and segments[0][0] is None and not segments[0][2]:
        segments = segments[1:]
    return segments


def paragraph_markup(para, osis, chapter, chapter_open=False):
    marker = para["marker"]
    raw = para["raw"]
    if is_source_nav_marker(raw):
        return []
    segments = verse_segments_travel(raw, osis, chapter)
    if not segments:
        return []

    def join_segments(items, drop=False):
        pieces = []
        first = True
        for verse, url, body in items:
            if verse is None:
                if body:
                    pieces.append(body)
                continue
            if drop and first:
                pieces.append(
                    f"#chapter-drop({typst_string(url)}, {chapter}, {typst_string(str(verse))})[{body}]"
                )
            else:
                pieces.append(f"#verse({typst_string(url)}, {int(chapter)}, {int(verse)})[{body}]")
            first = False
        content = " ".join(piece for piece in pieces if piece).strip()
        if not content:
            return ""
        if drop:
            return content
        if marker == "d":
            return content if drop else f"#superscription[{content}]"
        if marker == "pc":
            return f"#inscription[{content}]"
        if marker.startswith("q") or marker in {"li1", "li2"}:
            level = 1
            if marker == "qr" or marker == "qc":
                return f"#inscription[{content}]"
            if marker.startswith("q") and marker[1:].isdigit():
                level = int(marker[1:])
            elif marker == "li2":
                level = 2
            return f"#poetry({level})[{content}]"
        return f"#para[{content}]"

    if chapter_open:
        verse_items = [item for item in segments if item[0] is not None]
        prefix = [item for item in segments if item[0] is None]
        if verse_items:
            drop_items = prefix + verse_items[:1]
            rest_items = verse_items[1:]
            lines = []
            drop_line = join_segments(drop_items, drop=True)
            if drop_line:
                lines.append(drop_line)
            rest_line = join_segments(rest_items, drop=False)
            if rest_line:
                lines.append(rest_line)
            return lines
    line = join_segments(segments, drop=False)
    return [line] if line else []


def travel_preamble(
    spec: TravelSpec = SPEC,
    *,
    grid_proof: bool = False,
    hide_opening_chrome: bool = True,
    page_start: int = 1,
) -> str:
    leading = leading_gap_pt(spec)
    body_leading = body_leading_gap_pt(spec)
    r, g, b = spec.woc_rgb
    ir, ig, ib = spec.ink_rgb
    fr, fg, fb = spec.footnote_ink_rgb
    if grid_proof:
        body_font = GRID_PROOF_FAMILY
        head_font = GRID_PROOF_FAMILY
        body_alias = GRID_PROOF_FAMILY
        face_comment = (
            f"GRID PROOF stand-in: {GRID_PROOF_FAMILY} (SIL OFL). "
            f"Loved face is {spec.body_font} (Text optical). "
            "Never present this stand-in as the loved face."
        )
        proof_lets = (
            "#let grid-proof = true\n"
            f"#let hide-opening-chrome = {'true' if hide_opening_chrome else 'false'}\n"
            f"#let folio-offset = {int(page_start) - 1}\n"
        )
        page_background = "none"
        footer_block = '''    if here().page() == 1 and hide-opening-chrome {
      none
    } else {
      align(center, str(here().page() + folio-offset))
    }'''
    else:
        body_font = spec.body_font
        head_font = spec.head_font
        body_alias = spec.body_font_alias
        face_comment = f"Face: {spec.body_font} (Text optical). Do not substitute Source Serif."
        proof_lets = (
            "#let grid-proof = false\n"
            f"#let hide-opening-chrome = {'true' if hide_opening_chrome else 'false'}\n"
            f"#let folio-offset = {int(page_start) - 1}\n"
        )
        page_background = "none"
        footer_block = '''    if here().page() == 1 and hide-opening-chrome {
      none
    } else {
      align(center, str(here().page() + folio-offset))
    }'''
    return f'''// BSB travel composition — generated from this toolkit's USFM.
// {face_comment}
#let trim-width = {spec.trim_width_in}in
#let trim-height = {spec.trim_height_in}in
#let margin-inside = {spec.margin_inside_in}in
#let margin-outside = {spec.margin_outside_in}in
#let margin-head = {spec.margin_head_in}in
#let margin-foot = {spec.margin_foot_in}in
#let body-size = {spec.body_pt}pt
#let baseline-skip = {spec.baseline_pt}pt
#let leading-gap = {leading}pt
#let body-leading-gap = {body_leading}pt
#let lines-per-page = {spec.lines_per_page}
#let drop-lines = {spec.drop_lines}
#let body-font = "{body_font}"
#let head-font = "{head_font}"
#let ink = rgb({ir}, {ig}, {ib})
#let footnote-ink = rgb({fr}, {fg}, {fb})
#let woc-blue = rgb({r}, {g}, {b})
#let chapter-label = state("chapter-label", "JOHN")
#let mark-run(label) = {{
  chapter-label.update(label)
  [#metadata(label)<run-head>]
}}
#let run-book-from(label) = {{
  if label.contains(" · ") {{
    label.split(" · ").first()
  }} else {{
    label
  }}
}}
#let format-run-head(book, start-ch, start-v, end-ch, end-v) = {{
  if start-ch == end-ch {{
    if start-v == end-v {{
      book + " · " + str(start-ch) + ":" + str(start-v)
    }} else {{
      book + " · " + str(start-ch) + ":" + str(start-v) + "–" + str(end-v)
    }}
  }} else {{
    book + " · " + str(start-ch) + ":" + str(start-v) + "–" + str(end-ch) + ":" + str(end-v)
  }}
}}
{proof_lets}
#set page(
  width: trim-width,
  height: trim-height,
  margin: (
    inside: margin-inside,
    outside: margin-outside,
    top: margin-head,
    bottom: margin-foot,
  ),
  numbering: "1",
  background: {page_background},
  header: context {{
    // Per-page letter numbering (Typst docs: reset counter(footnote) in the header).
    counter(footnote).update(0)
    if here().page() == 1 and hide-opening-chrome {{
      none
    }} else {{
      set text(font: head-font, size: {spec.running_head_pt}pt, fill: ink, tracking: 0.12em)
      let page-num = here().page()
      let folio-num = page-num + folio-offset
      let marks = query(<run-head>)
      let on-page = marks.filter(it => it.location().page() == page-num)
      let label-text = if on-page.len() > 0 {{
        on-page.first().value
      }} else {{
        let before = marks.filter(it => it.location().page() < page-num)
        if before.len() > 0 {{ before.last().value }} else {{ chapter-label.get() }}
      }}
      let book = run-book-from(label-text)
      let verses = query(<run-verse>).filter(it => it.location().page() == page-num)
      let display = if verses.len() > 0 {{
        let a = verses.first().value
        let b = verses.last().value
        format-run-head(book, a.at(0), a.at(1), b.at(0), b.at(1))
      }} else {{
        label-text
      }}
      let label = smallcaps(display)
      if calc.odd(folio-num) {{
        align(right, label)
      }} else {{
        align(left, label)
      }}
    }}
  }},
  footer: context {{
    set text(font: head-font, size: {spec.folio_pt}pt, fill: ink)
{footer_block}
  }},
)

#set text(
  font: (body-font, "{body_alias}"),
  size: body-size,
  fill: ink,
  lang: "{spec.hyphen_lang}",
  hyphenate: true,
  fallback: false,
  overhang: true,
  top-edge: body-size,
  bottom-edge: 0pt,
  costs: (hyphenation: {spec.hyphenation_cost_pct}%, runt: 160%, widow: 100%, orphan: 100%),
)

#set par(
  justify: true,
  linebreaks: "optimized",
  leading: body-leading-gap,
  spacing: body-leading-gap,
  first-line-indent: 0pt,
  hanging-indent: 0pt,
  justification-limits: (
    spacing: (min: 80%, max: 150%),
    tracking: (min: -0.005em, max: 0.01em),
  ),
)

// Letter markers. The page header resets counter(footnote) so each page
// starts at "a" again. Book pagebreaks also reset as a safety net.
// Run-in notes: the first entry on the page draws every note as one
// wrapping paragraph; later entries collapse so they do not stack.
#set footnote(numbering: "a")
#set footnote.entry(
  indent: 0pt,
  gap: 0pt,
  separator: line(length: 30%, stroke: 0.35pt + footnote-ink),
)
#show footnote.entry: set text(
  font: body-font,
  size: {spec.footnote_pt}pt,
  fill: footnote-ink,
  fallback: false,
)
#show footnote.entry: it => context {{
  set text(fill: footnote-ink)
  show link: set text(fill: footnote-ink)
  let page-num = here().page()
  let notes = query(footnote).filter(n => n.location().page() == page-num)
  if notes.len() == 0 {{
    let mark = numbering("a", ..counter(footnote).at(it.note.location()))
    [#super(mark)#h(0.12em) #it.note.body]
  }} else if it.note.location() != notes.first().location() {{
    none
  }} else {{
    set par(
      justify: true,
      leading: {spec.footnote_baseline_pt - spec.footnote_pt}pt,
      first-line-indent: 0pt,
      hanging-indent: 0pt,
    )
    notes.map(n => {{
      let mark = numbering("a", ..counter(footnote).at(n.location()))
      [#super(mark)#h(0.12em) #n.body]
    }}).join([#h(0.7em)])
  }}
}}
// PDF sidebar: Typst emits bookmarks from heading. bookmarked: true with
// outlined: false keeps Book → Chapter in the outline without a printed TOC.
#set heading(numbering: none)
#show heading: none
#let outline-book(name) = heading(level: 1, outlined: false, bookmarked: true)[#name]
#let outline-chapter(n) = heading(level: 2, outlined: false, bookmarked: true)[#str(n)]
#show link: set text(fill: ink)

#let woc(body) = text(fill: woc-blue, font: (body-font, "{body_alias}"))[#body]
#let divine(body) = text(hyphenate: false)[#smallcaps[#body]]

#let vnum(n) = text(
  font: head-font,
  size: {spec.verse_pt}pt,
  weight: 700,
  baseline: -1.5pt,
  fill: ink,
)[#n]

#let verse(url, ch, n, body) = {{
  [#metadata((ch, n))<run-verse>]
  link(url)[#box[#vnum(n)#h(0.12em)]#body]
}}

#let geometric-cap(n) = {{
  let s = drop-lines * baseline-skip
  box(width: s, height: s, {{
    place(rect(width: s, height: s, stroke: 0.45pt + ink))
    place(dx: 2.1pt, dy: 2.1pt, rect(
      width: s - 4.2pt,
      height: s - 4.2pt,
      stroke: 0.28pt + ink,
    ))
    place(line(start: (0pt, s / 2), end: (3.2pt, s / 2), stroke: 0.45pt + ink))
    place(line(start: (s - 3.2pt, s / 2), end: (s, s / 2), stroke: 0.45pt + ink))
    place(line(start: (s / 2, 0pt), end: (s / 2, 3.2pt), stroke: 0.45pt + ink))
    place(line(start: (s / 2, s - 3.2pt), end: (s / 2, s), stroke: 0.45pt + ink))
    place(center + horizon)[
      #text(font: head-font, size: 15pt, weight: 700, fill: ink)[#n]
    ]
  }})
}}

#let chapter-drop(url, n, verse-n, body) = {{
  [#metadata((n, verse-n))<run-verse>]
  let gap = 0.08in
  let cap = geometric-cap(n)
  block(breakable: false, spacing: body-leading-gap)[
    #grid(
      columns: (drop-lines * baseline-skip, 1fr),
      column-gutter: gap,
      align: (top, top),
      link(url, cap),
      {{
        set par(first-line-indent: 0pt)
        verse(url, n, verse-n, body)
      }},
    )
  ]
}}

#let para(body) = block(spacing: body-leading-gap)[#body]
#let poetry(level, body) = block(
  spacing: leading-gap,
  // q1 sits on the measure; each further q-level steps 0.18 in (parallelism).
  inset: (left: 0.18in * calc.max(0, level - 1)),
)[
  // Verse lines, not justified prose. Hanging wrap stays in the indent column.
  #set par(justify: false, leading: leading-gap, hanging-indent: 0.18in)
  #body
]
#let inscription(body) = block(spacing: baseline-skip)[
  #align(center)[#text(font: head-font, size: body-size, tracking: 0.08em)[#smallcaps(body)]]
]
#let section(title) = block(
  above: 1.5 * baseline-skip,
  below: 0.5 * baseline-skip,
  sticky: true,
)[
  #text(font: head-font, size: {spec.section_pt}pt, weight: 700, fill: ink)[#title]
]
#let chapter-xrefs(body) = block(above: 0pt, below: 0.5 * baseline-skip, sticky: true)[
  #set text(font: body-font, size: {spec.xref_pt}pt, style: "italic", fill: ink)
  #set par(justify: true, leading: leading-gap, hanging-indent: 0.75em)
  #body
]
// Title + first verse/drop stay on the same page. sticky alone is not
// enough when a zero-height bookmark heading sits between them.
#let keep-with(body) = block(breakable: false, above: 0pt, below: 0pt)[#body]
#let book-title(name) = {{
  align(center)[
    #v(0.5 * baseline-skip)
    #text(font: head-font, size: {spec.title_pt}pt, weight: 700)[#name]
  ]
  v(0.5 * baseline-skip)
}}
#let superscription(body) = block(above: leading-gap, below: leading-gap)[
  #set text(font: body-font, size: body-size, style: "italic", fill: ink)
  #set par(justify: true, first-line-indent: 0pt)
  #body
]
'''


def generate_travel_typst(
    usfm_zip: Path,
    output_typ: Path,
    books=("John",),
    spec: TravelSpec = SPEC,
    *,
    grid_proof: bool = False,
    hide_opening_chrome: bool = True,
    page_start: int = 1,
):
    parsed = parse_usfm_zip(usfm_zip, book_names=list(books))
    if not parsed:
        raise ValueError(f"No BSB books matched {books!r} in {usfm_zip}")
    lines = [
        travel_preamble(
            spec,
            grid_proof=grid_proof,
            hide_opening_chrome=hide_opening_chrome,
            page_start=page_start,
        )
    ]
    for book_index, book in enumerate(parsed):
        if book_index:
            lines.append("#pagebreak()")
            lines.append("#counter(footnote).update(0)")
        display = book.get("title") or book["book"]
        running = (book.get("heading") or book["book"]).upper()
        first_chapter = book["chapters"][0]["chapter"] if book["chapters"] else 1
        outline_name = book.get("heading") or book["book"]
        lines.append(f"#outline-book({typst_string(outline_name)})")
        lines.append(f"#mark-run({typst_string(f'{running} · {first_chapter}')})")
        lines.append(f"#book-title({typst_string(display)})")
        for chapter in book["chapters"]:
            heading_ranges(chapter, book["osis"])
            running_chapter = f"{running} · {chapter['chapter']}"
            lines.append(f"#mark-run({typst_string(running_chapter)})")
            chapter_open = True
            chapter_xrefs_emitted = False
            chapter_outlined = False
            first_heading_refs = ""
            pending_head: list[str] = []

            def flush_keep(body_parts: list[str]) -> None:
                if pending_head:
                    lines.append("#keep-with[")
                    lines.extend(pending_head)
                    pending_head.clear()
                    lines.extend(body_parts)
                    lines.append("]")
                else:
                    lines.extend(body_parts)

            for para in chapter["paras"]:
                if para["kind"] == "heading" and para.get("refs") and not first_heading_refs:
                    first_heading_refs = para["refs"]
                    break
            for para in chapter["paras"]:
                if para["kind"] == "heading":
                    title = clean_spaces(para["raw"])
                    pending_head.append(f"#section({typst_string(title)})")
                    refs_raw = para.get("refs") or ""
                    if refs_raw and refs_raw == first_heading_refs and not chapter_xrefs_emitted:
                        refs = xref_markup(refs_raw)
                        if refs:
                            pending_head.append(f"#chapter-xrefs[{refs}]")
                            chapter_xrefs_emitted = True
                    elif refs_raw and refs_raw != first_heading_refs:
                        refs = xref_markup(refs_raw)
                        if refs:
                            pending_head.append(f"#chapter-xrefs[{refs}]")
                elif para["kind"] == "superscription":
                    body = render_text_chunk(para["raw"])
                    if body:
                        pending_head.append(f"#superscription[{body}]")
                elif para["kind"] == "acrostic":
                    title = clean_spaces(para["raw"])
                    if title and not is_hebrew_script(title):
                        pending_head.append(f"#section({typst_string(title)})")
                elif para["kind"] == "blank":
                    if pending_head:
                        pending_head.append("#v(baseline-skip)")
                    else:
                        lines.append("#v(baseline-skip)")
                elif is_source_nav_marker(para.get("raw") or ""):
                    continue
                else:
                    body_parts: list[str] = []
                    if not chapter_outlined:
                        body_parts.append(f"#outline-chapter({int(chapter['chapter'])})")
                        chapter_outlined = True
                    body_parts.extend(
                        paragraph_markup(
                            para, book["osis"], chapter["chapter"], chapter_open=chapter_open
                        )
                    )
                    flush_keep(body_parts)
                    chapter_open = False
            if not chapter_outlined:
                flush_keep([f"#outline-chapter({int(chapter['chapter'])})"])
            elif pending_head:
                flush_keep([])
        lines.append("")
    output_typ.parent.mkdir(parents=True, exist_ok=True)
    output_typ.write_text("\n\n".join(lines) + "\n", encoding="utf-8")
    return parsed


def compile_typst(input_typ: Path, output_pdf: Path, font_dir: Path):
    output_pdf.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "typst",
        "compile",
        "--ignore-system-fonts",
        "--font-path",
        str(font_dir),
        str(input_typ),
        str(output_pdf),
    ]
    return subprocess.run(cmd, check=False)


def pdf_page_count(path: Path) -> int:
    import fitz

    with fitz.open(path) as doc:
        return doc.page_count


def book_part_slug(index: int, name: str) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
    safe = "-".join(part for part in safe.split("-") if part)
    return f"{index:02d}-{safe}"


RUN_HEAD_RE = re.compile(
    r"^([A-Z0-9][A-Z0-9 ]*?)\s+·\s+(\d+):(\d+)(?:–(?:(\d+):)?(\d+))?$"
)
LAST_PAGE_VERSE_RE = re.compile(r"(?:(?<=^)|(?<=\s))(\d{1,3})(?:\s|(?=[A-Z“\"‘]))")


def parse_run_head(text: str):
    match = RUN_HEAD_RE.match((text or "").strip())
    if not match:
        return None
    book, start_ch, start_v, end_ch, end_v = match.groups()
    return {
        "book": book.strip(),
        "start_ch": int(start_ch),
        "start_v": int(start_v),
        "end_ch": int(end_ch or start_ch),
        "end_v": int(end_v or start_v),
    }


def infer_last_page_run_head(prev_head: str, last_text: str) -> str | None:
    """Rebuild a running head when Typst copies page-1 chrome onto the last leaf."""
    parsed = parse_run_head(prev_head)
    if not parsed:
        return None
    body = (last_text or "").split("\n")
    # Skip a stale copied head / folio when present.
    useful = [line for line in body if line.strip() and not parse_run_head(line.strip())]
    blob = "\n".join(useful)
    verses = [int(num) for num in LAST_PAGE_VERSE_RE.findall(blob)]
    if not verses:
        return None
    chapter = parsed["end_ch"]
    start_v, end_v = verses[0], verses[-1]
    book = parsed["book"]
    if start_v == end_v:
        return f"{book} · {chapter}:{start_v}"
    return f"{book} · {chapter}:{start_v}–{end_v}"


def _page_text_lines(page):
    lines = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(span.get("text", "") for span in line.get("spans", []))
            if text.strip():
                lines.append((text, line["bbox"], line.get("spans", [{}])[0]))
    return lines


def _grid_proof_regular_font(font_dir: Path) -> Path | None:
    if not font_dir.is_dir():
        return None
    for path in sorted(font_dir.iterdir()):
        token = _norm_name(path)
        if "sourceserif" in token and "italic" not in token and "bold" not in token:
            if path.suffix.lower() in {".otf", ".ttf"}:
                return path
    return None


def repair_unconverged_last_page(pdf_path: Path, page_start: int, font_dir: Path) -> bool:
    """Redraw last-page header/folio when Typst reuses page-1 chrome after a failed converge."""
    import fitz

    font_path = _grid_proof_regular_font(font_dir)
    if font_path is None:
        return False
    with fitz.open(pdf_path) as doc:
        if doc.page_count < 2:
            return False
        first_lines = _page_text_lines(doc[0])
        last_lines = _page_text_lines(doc[-1])
        prev_lines = _page_text_lines(doc[-2])
        if not first_lines or not last_lines or not prev_lines:
            return False
        first_head, last_head = first_lines[0][0].strip(), last_lines[0][0].strip()
        first_folio, last_folio = first_lines[-1][0].strip(), last_lines[-1][0].strip()
        if last_head != first_head or last_folio != first_folio:
            return False
        rebuilt = infer_last_page_run_head(prev_lines[0][0], doc[-1].get_text())
        if not rebuilt:
            return False
        folio = str(int(page_start) + doc.page_count - 1)
        page = doc[-1]
        head_bbox = fitz.Rect(last_lines[0][1])
        folio_bbox = fitz.Rect(last_lines[-1][1])
        # Match Typst running-head / folio bands (7pt at the spec margins).
        header_band = fitz.Rect(0, 14.0, page.rect.width, 30.0)
        folio_band = fitz.Rect(0, 482.0, page.rect.width, page.rect.height)
        header_band.include_rect(head_bbox)
        folio_band.include_rect(folio_bbox)
        page.add_redact_annot(header_band, fill=(1, 1, 1))
        page.add_redact_annot(folio_band, fill=(1, 1, 1))
        page.apply_redactions()
        fontname = "source-serif-repair"
        page.insert_font(fontname=fontname, fontfile=str(font_path))
        odd = int(folio) % 2 == 1
        align = fitz.TEXT_ALIGN_RIGHT if odd else fitz.TEXT_ALIGN_LEFT
        # Recto uses the inside margin on the left; verso uses the outside margin.
        if odd:
            box = fitz.Rect(39.6, header_band.y0, 313.2, header_band.y1)
        else:
            box = fitz.Rect(28.8, header_band.y0, 302.4, header_band.y1)
        page.insert_textbox(box, rebuilt, fontname=fontname, fontsize=7, color=(20 / 255,) * 3, align=align)
        page.insert_textbox(
            fitz.Rect(0, folio_band.y0, page.rect.width, page.rect.height - 4),
            folio,
            fontname=fontname,
            fontsize=7,
            color=(20 / 255,) * 3,
            align=fitz.TEXT_ALIGN_CENTER,
        )
        tmp = pdf_path.with_suffix(pdf_path.suffix + ".repaired")
        doc.save(tmp, deflate=True)
    tmp.replace(pdf_path)
    return True


def compile_canon_by_book(
    usfm_zip: Path,
    books: list[str],
    output_pdf: Path,
    font_dir: Path,
    work_dir: Path,
    *,
    grid_proof: bool = True,
) -> int:
    """Compile each book on its own, then merge. Used when a 66-book Typst run OOMs."""
    parts: list[Path] = []
    page_start = 1
    work_dir.mkdir(parents=True, exist_ok=True)
    for index, book in enumerate(books):
        slug = book_part_slug(index + 1, book)
        suffix = "grid-proof" if grid_proof else "print"
        part_typ = work_dir / f"book-{slug}-{suffix}.typ"
        part_pdf = work_dir / f"book-{slug}-{suffix}.pdf"
        generate_travel_typst(
            usfm_zip,
            part_typ,
            books=(book,),
            grid_proof=grid_proof,
            hide_opening_chrome=(index == 0),
            page_start=page_start,
        )
        print(f"Wrote Typst source: {part_typ} (1 book, page start {page_start})")
        result = compile_typst(part_typ, part_pdf, font_dir)
        if result.returncode != 0:
            print(f"Typst compile failed for {book}.", file=sys.stderr)
            return result.returncode
        if repair_unconverged_last_page(part_pdf, page_start, font_dir):
            print(f"Repaired last-page chrome: {part_pdf}")
        count = pdf_page_count(part_pdf)
        print(f"Wrote PDF: {part_pdf} ({count} pages)")
        parts.append(part_pdf)
        page_start += count
    merge_travel_pdfs(parts, output_pdf)
    print(f"Wrote merged PDF: {output_pdf} ({page_start - 1} pages, {len(parts)} books)")
    return 0


def merge_travel_pdfs(sources: list[Path], output: Path) -> Path:
    """Concatenate testament PDFs and offset Book → Chapter outlines."""
    import fitz

    if len(sources) < 2:
        raise ValueError("merge_travel_pdfs needs at least two PDFs")
    output.parent.mkdir(parents=True, exist_ok=True)
    out = fitz.open()
    outline: list[list] = []
    offset = 0
    for source in sources:
        with fitz.open(source) as src:
            for entry in src.get_toc() or []:
                mapped = list(entry)
                mapped[2] = entry[2] + offset
                outline.append(mapped)
            out.insert_pdf(src)
            offset = out.page_count
    if outline:
        out.set_toc(outline)
    # Incremental save; garbage collection on 2k+ pages can stall for minutes.
    out.save(output, deflate=True)
    out.close()
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate the compact travel BSB from toolkit USFM (John sample or full canon)"
    )
    parser.add_argument("input_usfm_zip", type=Path, nargs="?", default=DEFAULT_USFM)
    parser.add_argument("output_pdf", type=Path, nargs="?", default=None)
    parser.add_argument("--typst-out", type=Path, default=None)
    parser.add_argument("--font-dir", type=Path, default=None)
    parser.add_argument("--book", action="append", default=None, help="Book name or USFM code (default: John)")
    parser.add_argument(
        "--all-books",
        action="store_true",
        help="Compose the 66-book Protestant canon in canonical order (not John-only)",
    )
    parser.add_argument(
        "--testament",
        choices=("all", "ot", "nt"),
        default="all",
        help="Limit --all-books (or an explicit book list) to OT or NT",
    )
    parser.add_argument("--no-compile", action="store_true", help="Write Typst only; skip the print target")
    parser.add_argument("--download-usfm", action="store_true", help="Fetch official BSB USFM if missing")
    parser.add_argument(
        "--grid-proof",
        action="store_true",
        help=(
            "Metrics-only compile with the labeled OFL stand-in "
            "(Source Serif 4). Never the loved face."
        ),
    )
    args = parser.parse_args(argv)

    default_pdf, default_typ, default_fonts = default_output_paths(
        grid_proof=args.grid_proof,
        all_books=args.all_books,
        testament=args.testament,
    )
    if args.output_pdf is None:
        args.output_pdf = default_pdf
    if args.typst_out is None:
        args.typst_out = default_typ
    if args.font_dir is None:
        args.font_dir = default_fonts

    try:
        books = select_travel_books(
            all_books=args.all_books,
            book_args=args.book,
            testament=args.testament,
        )
    except ValueError as exc:
        parser.error(str(exc))
    try:
        usfm_zip = ensure_usfm_zip(args.input_usfm_zip, download=args.download_usfm)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    parsed = generate_travel_typst(
        usfm_zip, args.typst_out, books=books, grid_proof=args.grid_proof
    )
    got = [book["book"] for book in parsed]
    archive_books = usfm_zip_book_count(usfm_zip)
    if args.all_books and archive_books >= len(books) and got != books:
        print(
            "USFM did not yield the requested books in Protestant canon order.\n"
            f"expected {len(books)}: {books}\n"
            f"got {len(got)}: {got}",
            file=sys.stderr,
        )
        return 1
    print(f"Wrote Typst source: {args.typst_out} ({len(got)} books)")

    if args.no_compile:
        return 0

    try:
        if args.grid_proof:
            require_grid_proof_fonts(args.font_dir)
        else:
            require_milo_fonts(args.font_dir)
    except (MiloFontError, GridProofFontError) as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code

    result = compile_typst(args.typst_out, args.output_pdf, args.font_dir)
    if result.returncode != 0 and args.all_books:
        print(
            "Canon Typst compile failed; compiling one book at a time, then merging.",
            file=sys.stderr,
        )
        code = compile_canon_by_book(
            usfm_zip,
            books,
            args.output_pdf,
            args.font_dir,
            args.typst_out.parent,
            grid_proof=args.grid_proof,
        )
        if code == 0 and args.grid_proof:
            print(GRID_PROOF_NOTE, file=sys.stderr)
        return code
    if result.returncode != 0:
        print("Typst compile failed. Source was still generated.", file=sys.stderr)
        return result.returncode
    print(f"Wrote PDF: {args.output_pdf}")
    if args.grid_proof:
        print(GRID_PROOF_NOTE, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
