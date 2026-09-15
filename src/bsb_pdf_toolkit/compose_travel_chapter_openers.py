#!/usr/bin/env python3
"""Build a John chapter-opener QA pack from a travel grid-proof PDF.

Crops every chapter-start leaf so Dylan can scan drop caps, running heads,
first-verse-after-heading indent, and chapter-open air without a 66-book
recompile. Mid-page opens crop around the drop, not the physical page top.

This is a metrics/grid-proof helper. It never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from .generate_travel_pdf import GRID_PROOF_WATERMARK, SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-john-grid-proof.pdf"
DEFAULT_PDF = REPO_ROOT / "drafts" / "travel" / "qa-john" / "bsb-travel-john-chapter-openers.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "qa-john"
PNG_DPI = 120
JOHN_CHAPTER_COUNT = 21
DROP_SIZE_PT = SPEC.drop_lines * SPEC.baseline_pt
DROP_SIZE_TOLERANCE_PT = 1.0
CROP_HEIGHT_RATIO = 0.52
HEADING_LOOKBACK_PT = 80.0
AFTER_DROP_PAD_PT = 84.0
SECTION_SIZE_MIN = 8.0
SECTION_SIZE_MAX = 9.2
BOOK_TITLE_SIZE_MIN = 13.0


@dataclass(frozen=True)
class ChapterOpener:
    chapter: int
    page: int
    clip: fitz.Rect
    drop: fitz.Rect


def opener_slug(chapter: int) -> str:
    return f"john-ch{int(chapter):02d}-opener"


def chapter_openers_from_toc(toc: list) -> list[tuple[int, int]]:
    """Level-2 outline rows become (chapter, 1-based page) pairs."""
    openers = []
    for entry in toc or []:
        if not entry or entry[0] != 2:
            continue
        title = str(entry[1]).strip()
        if not title.isdigit():
            raise ValueError(f"chapter outline title {title!r} is not a number")
        page = int(entry[2])
        if page < 1:
            raise ValueError(f"chapter {title} dest page {page} is not 1-based")
        openers.append((int(title), page))
    if not openers:
        raise ValueError("no chapter outline entries")
    return openers


def drop_rect_on_page(page: fitz.Page) -> fitz.Rect | None:
    """Topmost geometric drop-cap square (3 baselines on the travel grid)."""
    found = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None:
            continue
        if (
            abs(rect.width - DROP_SIZE_PT) <= DROP_SIZE_TOLERANCE_PT
            and abs(rect.height - DROP_SIZE_PT) <= DROP_SIZE_TOLERANCE_PT
        ):
            found.append(fitz.Rect(rect))
    if not found:
        return None
    return min(found, key=lambda rect: (rect.y0, rect.x0))


def heading_top_above_drop(page: fitz.Page, drop: fitz.Rect) -> float | None:
    """Y of the section or book title that sits just above the drop."""
    top = None
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                font = span.get("font") or ""
                size = float(span.get("size") or 0)
                bold = "Bold" in font
                section = bold and SECTION_SIZE_MIN <= size <= SECTION_SIZE_MAX
                book_title = bold and size >= BOOK_TITLE_SIZE_MIN
                if not (section or book_title):
                    continue
                y0 = float(span["bbox"][1])
                if drop.y0 - HEADING_LOOKBACK_PT < y0 < drop.y0:
                    if top is None or y0 < top:
                        top = y0
    return top


def opener_clip_rect(page: fitz.Page, drop: fitz.Rect) -> fitz.Rect:
    """Half-leaf window that keeps heading + drop + first lines in frame."""
    crop_height = page.rect.height * CROP_HEIGHT_RATIO
    heading_top = heading_top_above_drop(page, drop)
    need_bottom = min(page.rect.height, drop.y1 + AFTER_DROP_PAD_PT)
    # If the open fits in a top-half crop, keep the running head.
    if need_bottom <= crop_height:
        return fitz.Rect(0, 0, page.rect.width, crop_height)
    y1 = need_bottom
    y0 = max(0.0, y1 - crop_height)
    if heading_top is not None and heading_top < y0:
        y0 = max(0.0, heading_top - 12.0)
        y1 = min(page.rect.height, max(y0 + crop_height, need_bottom))
        y0 = max(0.0, y1 - crop_height)
    if y1 > page.rect.height:
        y1 = page.rect.height
        y0 = max(0.0, y1 - crop_height)
    return fitz.Rect(0, y0, page.rect.width, y1)


def load_chapter_openers(source: Path) -> list[ChapterOpener]:
    with fitz.open(source) as doc:
        pairs = chapter_openers_from_toc(doc.get_toc())
        openers = []
        for chapter, page_no in pairs:
            if page_no > doc.page_count:
                raise ValueError(
                    f"{source} has {doc.page_count} pages; cannot take chapter {chapter} on {page_no}"
                )
            page = doc[page_no - 1]
            drop = drop_rect_on_page(page)
            if drop is None:
                raise ValueError(f"page {page_no} (John {chapter}) has no drop-cap square")
            clip = opener_clip_rect(page, drop)
            openers.append(ChapterOpener(chapter=chapter, page=page_no, clip=clip, drop=drop))
    return openers


def validate_john_openers(openers: list[ChapterOpener]) -> None:
    chapters = [item.chapter for item in openers]
    if chapters != list(range(1, JOHN_CHAPTER_COUNT + 1)):
        raise ValueError(
            f"expected John chapters 1–{JOHN_CHAPTER_COUNT}, got {chapters}"
        )


def compose_opener_pdf(
    source: Path,
    output: Path,
    openers: list[ChapterOpener],
) -> list[ChapterOpener]:
    """Place each opener clip on its own native-width page."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src:
        out = fitz.open()
        for opener in openers:
            dest = out.new_page(width=opener.clip.width, height=opener.clip.height)
            dest.show_pdf_page(dest.rect, src, opener.page - 1, clip=opener.clip)
        out.save(output, deflate=True, garbage=4)
        out.close()
    return openers


def render_opener_pngs(
    source: Path,
    png_dir: Path,
    openers: list[ChapterOpener],
    *,
    dpi: int = PNG_DPI,
) -> list[Path]:
    """Raster each opener clip at 120 dpi from the source leaf."""
    png_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(source) as doc:
        for opener in openers:
            pix = doc[opener.page - 1].get_pixmap(
                dpi=dpi, clip=opener.clip, alpha=False
            )
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            path = png_dir / f"{opener_slug(opener.chapter)}.png"
            image.save(path, format="PNG", optimize=True)
            written.append(path)
    return written


def format_opener_report(openers: list[ChapterOpener]) -> str:
    lines = [f"John chapter openers ({len(openers)}):"]
    for opener in openers:
        lines.append(
            f"  ch {opener.chapter:>2}  p.{opener.page:<3}  "
            f"clip y {opener.clip.y0:.1f}–{opener.clip.y1:.1f}  "
            f"drop y {opener.drop.y0:.1f}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Crop every John chapter opener from a travel grid-proof PDF. "
            "Not the loved face."
        )
    )
    parser.add_argument("input_pdf", type=Path, nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("output_pdf", type=Path, nargs="?", default=DEFAULT_PDF)
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    parser.add_argument("--no-png", action="store_true")
    parser.add_argument(
        "--allow-any-chapters",
        action="store_true",
        help="Skip the John 1–21 outline check (for fixtures).",
    )
    args = parser.parse_args(argv)

    if not args.input_pdf.is_file():
        print(f"Missing grid-proof PDF: {args.input_pdf}", file=sys.stderr)
        return 1

    try:
        openers = load_chapter_openers(args.input_pdf)
        if not args.allow_any_chapters:
            validate_john_openers(openers)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    compose_opener_pdf(args.input_pdf, args.output_pdf, openers)
    print(f"Wrote opener PDF: {args.output_pdf} ({len(openers)} chapter opens)")
    if not args.no_png:
        pngs = render_opener_pngs(
            args.input_pdf, args.png_dir, openers, dpi=args.dpi
        )
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(format_opener_report(openers), file=sys.stderr)
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
