#!/usr/bin/env python3
"""Compose a compact travel BSB from this toolkit's USFM via Typst.

The loved-face print target requires licensed FF Milo Serif Text desktop
fonts in ``fonts/milo/``. It will not download, scrape, subset, or silently
substitute another face (including Source Serif or Lexend).

``--grid-proof`` is a separate, opt-in metrics compile. It uses a labeled
OFL stand-in and watermarks every page ``GRID PROOF — NOT FINAL FACE``.
That PDF is never the loved face.
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
    "for a watermarked metrics compile. This stand-in is never the loved face."
)

WJ_TOKEN_RE = re.compile(
    r"(\\f\s+.*?\\f\*)|(\\wj\*)|(\\wj)|(\\v\s+(\d+))",
    re.S,
)
WORD_MARKER_RE = re.compile(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*")
NAMED_SPAN_RE = re.compile(r"\\(nd|qs)\s*(.+?)\\\1\*", re.S)
RESIDUAL_MARKER_RE = re.compile(r"\\(?!ref\b|f\b|f\*|wj\b)[a-z0-9]+\*?\s*")
FOOTNOTE_RE = re.compile(r"\\f\s+(.*?)\\f\*", re.S)


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


def footnote_markup(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^\+\s*", "", raw)
    raw = re.sub(r"\\fr\s+\S+\s*", "", raw)
    parts = []
    pos = 0
    pattern = re.compile(r"\\fqa\s+(.*?)(?=\\ft\b|\\fqa\b|$)", re.S)
    working = re.sub(r"\\ft\s*", " ", raw)
    for match in pattern.finditer(working):
        if match.start() > pos:
            parts.append(parse_ref_runs(clean_spaces(re.sub(r"\\[a-z0-9]+\*?", " ", working[pos:match.start()]))))
        emph = clean_spaces(re.sub(r"\\[a-z0-9]+\*?", " ", match.group(1)))
        if emph:
            parts.append(f"#emph[{typst_escape(emph)}]")
        pos = match.end()
    if pos < len(working):
        tail = parse_ref_runs(clean_spaces(re.sub(r"\\(?!ref\b)[a-z0-9]+\*?", " ", working[pos:])))
        if tail:
            parts.append(tail)
    content = " ".join(part for part in parts if part).strip()
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
                pieces.append(f"#smallcaps[{escaped}]")
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
                pieces.append(f"#verse({typst_string(url)}, {typst_string(str(verse))})[{body}]")
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


def travel_preamble(spec: TravelSpec = SPEC, *, grid_proof: bool = False) -> str:
    leading = leading_gap_pt(spec)
    r, g, b = spec.woc_rgb
    ir, ig, ib = spec.ink_rgb
    if grid_proof:
        body_font = GRID_PROOF_FAMILY
        head_font = GRID_PROOF_FAMILY
        body_alias = GRID_PROOF_FAMILY
        face_comment = (
            f"GRID PROOF stand-in: {GRID_PROOF_FAMILY} (SIL OFL). "
            f"Loved face is {spec.body_font} (Text optical). "
            "Never present this stand-in as the loved face."
        )
        proof_lets = f'''#let grid-proof = true
#let proof-mark = "{GRID_PROOF_WATERMARK}"

#let proof-background() = context {{
  let left = if calc.odd(here().page()) {{ margin-inside }} else {{ margin-outside }}
  let width = trim-width - margin-inside - margin-outside
  let line-stroke = 0.25pt + luma(0).transparentize(88%)
  for i in range(lines-per-page + 1) {{
    place(dx: left, dy: margin-head + i * baseline-skip, line(
      length: width,
      stroke: line-stroke,
    ))
  }}
  place(center + horizon, rotate(-50deg)[
    #text(
      font: head-font,
      size: 17pt,
      fill: rgb({r}, {g}, {b}).transparentize(80%),
      weight: 700,
      tracking: 0.08em,
    )[#proof-mark]
  ])
}}
'''
        page_background = "if grid-proof { proof-background() } else { none }"
        title_proof = f'''    #if grid-proof {{
      v(baseline-skip)
      text(font: head-font, size: 9pt, weight: 700, fill: woc-blue)[#proof-mark]
      v(leading-gap)
      text(font: body-font, size: 7pt)[{GRID_PROOF_NOTE}]
    }}
'''
        footer_block = f'''    if grid-proof {{
      if here().page() == 1 {{
        align(center)[#text(size: 6pt, tracking: 0.08em)[#smallcaps[#proof-mark]]]
      }} else {{
        grid(
          columns: (1fr, auto, 1fr),
          align(left)[#text(size: 5.5pt, tracking: 0.04em)[#proof-mark]],
          align(center)[#counter(page).display()],
          [],
        )
      }}
    }} else if here().page() == 1 {{
      none
    }} else {{
      align(center, counter(page).display())
    }}'''
    else:
        body_font = spec.body_font
        head_font = spec.head_font
        body_alias = spec.body_font_alias
        face_comment = f"Face: {spec.body_font} (Text optical). Do not substitute Source Serif."
        proof_lets = "#let grid-proof = false\n"
        page_background = "none"
        title_proof = ""
        footer_block = '''    if here().page() == 1 {
      none
    } else {
      align(center, counter(page).display())
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
#let lines-per-page = {spec.lines_per_page}
#let drop-lines = {spec.drop_lines}
#let body-font = "{body_font}"
#let head-font = "{head_font}"
#let ink = rgb({ir}, {ig}, {ib})
#let woc-blue = rgb({r}, {g}, {b})
#let chapter-label = state("chapter-label", "JOHN")
#let mark-run(label) = {{
  chapter-label.update(label)
  [#metadata(label)<run-head>]
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
    if here().page() == 1 {{
      none
    }} else {{
      set text(font: head-font, size: {spec.running_head_pt}pt, fill: ink, tracking: 0.12em)
      let page-num = here().page()
      let marks = query(<run-head>)
      let on-page = marks.filter(it => it.location().page() == page-num)
      let label-text = if on-page.len() > 0 {{
        on-page.first().value
      }} else {{
        let before = marks.filter(it => it.location().page() < page-num)
        if before.len() > 0 {{ before.last().value }} else {{ chapter-label.get() }}
      }}
      let label = smallcaps(label-text)
      if calc.odd(page-num) {{
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
  costs: (hyphenation: 120%, runt: 160%, widow: 100%, orphan: 100%),
)

#set par(
  justify: true,
  linebreaks: "optimized",
  leading: leading-gap,
  spacing: leading-gap,
  first-line-indent: 0pt,
  hanging-indent: 0pt,
  justification-limits: (
    spacing: (min: 80%, max: 150%),
    tracking: (min: -0.005em, max: 0.01em),
  ),
)

#set footnote(numbering: "a")
#show footnote.entry: set text(font: body-font, size: {spec.footnote_pt}pt, fallback: false)
#show link: it => {{
  set text(fill: ink)
  it
}}

#let woc(body) = text(fill: woc-blue, font: (body-font, "{body_alias}"))[#body]

#let vnum(n) = text(
  font: head-font,
  size: {spec.verse_pt}pt,
  weight: 700,
  baseline: -1.5pt,
  fill: ink,
)[#n]

#let verse(url, n, body) = {{
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
  let gap = 0.08in
  let cap = geometric-cap(n)
  block(breakable: false, spacing: leading-gap)[
    #grid(
      columns: (drop-lines * baseline-skip, 1fr),
      column-gutter: gap,
      align: (top, top),
      link(url, cap),
      {{
        set par(first-line-indent: 0pt)
        verse(url, verse-n, body)
      }},
    )
  ]
}}

#let para(body) = block(spacing: leading-gap)[#body]
#let poetry(level, body) = block(
  spacing: leading-gap,
  inset: (left: 0.14in * level),
)[#body]
#let inscription(body) = block(spacing: baseline-skip)[
  #align(center)[#text(font: head-font, size: body-size, tracking: 0.08em)[#smallcaps(body)]]
]
#let section(title) = block(above: baseline-skip, below: leading-gap)[
  #text(font: head-font, size: {spec.section_pt}pt, weight: 700, fill: ink)[#title]
]
#let chapter-xrefs(body) = block(above: 0pt, below: leading-gap)[
  #set text(font: body-font, size: {spec.xref_pt}pt, style: "italic", fill: ink)
  #set par(justify: true, leading: leading-gap, hanging-indent: 0.75em)
  #body
]
#let book-title(name, sample: false) = {{
  if sample {{
    align(center)[
      #v(3 * baseline-skip)
      #text(font: head-font, size: 8pt, tracking: 0.18em)[#smallcaps[Berean Standard Bible]]
      #v(baseline-skip)
      #text(font: head-font, size: {spec.title_pt}pt, weight: 700)[#name]
      #v(baseline-skip)
      #text(font: body-font, size: 8pt)[{SAMPLE_SUBTITLE}]
{title_proof}    ]
    v(2 * baseline-skip)
  }} else {{
    align(center)[
      #v(baseline-skip)
      #text(font: head-font, size: {spec.title_pt}pt, weight: 700)[#name]
    ]
    v(baseline-skip)
  }}
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
):
    parsed = parse_usfm_zip(usfm_zip, book_names=list(books))
    if not parsed:
        raise ValueError(f"No BSB books matched {books!r} in {usfm_zip}")
    lines = [travel_preamble(spec, grid_proof=grid_proof)]
    for book_index, book in enumerate(parsed):
        if book_index:
            lines.append("#pagebreak()")
            lines.append("#counter(footnote).update(0)")
        display = book.get("title") or book["book"]
        running = (book.get("heading") or book["book"]).upper()
        sample = "true" if book_index == 0 else "false"
        first_chapter = book["chapters"][0]["chapter"] if book["chapters"] else 1
        lines.append(f"#mark-run({typst_string(f'{running} · {first_chapter}')})")
        lines.append(f"#book-title({typst_string(display)}, sample: {sample})")
        for chapter in book["chapters"]:
            heading_ranges(chapter, book["osis"])
            running_chapter = f"{running} · {chapter['chapter']}"
            lines.append(f"#mark-run({typst_string(running_chapter)})")
            chapter_open = True
            chapter_xrefs_emitted = False
            first_heading_refs = ""
            for para in chapter["paras"]:
                if para["kind"] == "heading" and para.get("refs") and not first_heading_refs:
                    first_heading_refs = para["refs"]
                    break
            for para in chapter["paras"]:
                if para["kind"] == "heading":
                    title = clean_spaces(para["raw"])
                    lines.append(f"#section({typst_string(title)})")
                    refs_raw = para.get("refs") or ""
                    if refs_raw and refs_raw == first_heading_refs and not chapter_xrefs_emitted:
                        refs = xref_markup(refs_raw)
                        if refs:
                            lines.append(f"#chapter-xrefs[{refs}]")
                            chapter_xrefs_emitted = True
                    elif refs_raw and refs_raw != first_heading_refs:
                        refs = xref_markup(refs_raw)
                        if refs:
                            lines.append(f"#chapter-xrefs[{refs}]")
                elif para["kind"] == "superscription":
                    body = render_text_chunk(para["raw"])
                    if body:
                        lines.append(f"#superscription[{body}]")
                elif para["kind"] == "acrostic":
                    title = clean_spaces(para["raw"])
                    if title and not is_hebrew_script(title):
                        lines.append(f"#section({typst_string(title)})")
                elif para["kind"] == "blank":
                    lines.append("#v(baseline-skip)")
                else:
                    for markup in paragraph_markup(
                        para, book["osis"], chapter["chapter"], chapter_open=chapter_open
                    ):
                        lines.append(markup)
                    chapter_open = False
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
            "Metrics-only compile with the labeled OFL stand-in. "
            "Watermarks every page 'GRID PROOF — NOT FINAL FACE'. "
            "Never the loved face."
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
    if result.returncode != 0:
        print("Typst compile failed. Source was still generated.", file=sys.stderr)
        return result.returncode
    print(f"Wrote PDF: {args.output_pdf}")
    if args.grid_proof:
        print(f"{GRID_PROOF_WATERMARK}. {GRID_PROOF_NOTE}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
