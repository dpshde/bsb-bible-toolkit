#!/usr/bin/env python3
"""Build a compact hyphenation QA sheet from targeted travel books.

Compiles Genesis + Psalms + John (grid proof only), then extracts a dense
John prose leaf, Psalm 119 poetry, and Genesis 1. Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compose_travel_hotspots import (
    BookFace,
    HotspotSpec,
    book_catalog,
    book_ranges,
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    page_has_needles,
    render_hotspot_pngs,
    validate_leaf,
)
from .generate_travel_pdf import DEFAULT_GRID_FONT_DIR, DEFAULT_USFM, GRID_PROOF_WATERMARK

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "hyphenation-books-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "hyphenation-books-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-hyphenation-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "hyphenation"
PNG_DPI = 120

HYPHEN_QA_BOOKS = ("Genesis", "Psalms", "John")


def count_hyphen_breaks(text: str) -> int:
    """Count Typst soft hyphens plus leftover ASCII line-end hyphens."""
    return (text or "").count("\u00ad") + (text or "").count("-\n")


def pick_most_hyphens(page_texts: list[str], start: int, end: int) -> int:
    """1-based page with the most hyphen breaks in ``start..end``."""
    best_page = start
    best_count = -1
    for page_no in range(start, end + 1):
        count = count_hyphen_breaks(page_texts[page_no - 1])
        if count > best_count:
            best_count = count
            best_page = page_no
    return best_page


def select_hyphenation_pages(
    page_texts: list[str],
    catalog: list[BookFace],
) -> list[tuple[HotspotSpec, int]]:
    ranges = book_ranges(page_texts, catalog)
    john_start, john_end = ranges["John"]
    john_page = pick_most_hyphens(page_texts, john_start, john_end)
    psalm_spec = HotspotSpec(
        slug="psalm-119",
        label="Psalm 119 poetry",
        book="Psalms",
        pick="contains",
        needles=("ALEPH",),
        require=("ALEPH",),
        forbid=("א",),
    )
    genesis_spec = HotspotSpec(
        slug="genesis-1",
        label="Genesis 1 open",
        book="Genesis",
        pick="first",
        require=("In the beginning",),
    )
    john_spec = HotspotSpec(
        slug="john-prose",
        label="Dense John prose",
        book="John",
        pick="contains",
    )
    psalm_page = None
    start, end = ranges["Psalms"]
    for page_no in range(start, end + 1):
        if page_has_needles(page_texts[page_no - 1], psalm_spec.needles):
            psalm_page = page_no
            break
    if psalm_page is None:
        raise ValueError("psalm-119: no ALEPH page in Psalms")
    genesis_page = ranges["Genesis"][0]
    chosen = [
        (john_spec, john_page),
        (psalm_spec, psalm_page),
        (genesis_spec, genesis_page),
    ]
    for spec, page_no in chosen:
        validate_leaf(spec, page_texts[page_no - 1])
    return chosen


def format_selection(chosen: list[tuple[HotspotSpec, int]], page_texts: list[str]) -> str:
    lines = ["Hyphenation QA leaves (source page → leaf):"]
    for spec, page_no in chosen:
        breaks = count_hyphen_breaks(page_texts[page_no - 1])
        lines.append(
            f"  {spec.slug}: source p.{page_no}  {spec.label} ({spec.book}); "
            f"{breaks} hyphen break(s)"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile Genesis/Psalms/John and extract a hyphenation QA sheet. "
            "GRID PROOF — NOT FINAL FACE. Not the loved face."
        )
    )
    parser.add_argument("--usfm", type=Path, default=DEFAULT_USFM)
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_WORK_PDF)
    parser.add_argument("--typst-out", type=Path, default=DEFAULT_WORK_TYP)
    parser.add_argument("--font-dir", type=Path, default=DEFAULT_GRID_FONT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)

    if args.no_compile:
        if not args.source_pdf.is_file():
            print(f"Missing hyphenation source PDF: {args.source_pdf}", file=sys.stderr)
            return 1
    else:
        if not args.usfm.is_file():
            print(f"Missing USFM archive: {args.usfm}", file=sys.stderr)
            return 1
        code = compile_hotspot_books(
            args.usfm,
            args.source_pdf,
            args.typst_out,
            args.font_dir,
            books=HYPHEN_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        if args.usfm.is_file():
            catalog = book_catalog(args.usfm, books=HYPHEN_QA_BOOKS)
        else:
            catalog = [BookFace(book=name, title=name, heading=name) for name in HYPHEN_QA_BOOKS]
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_hyphenation_pages(page_texts, catalog)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no in chosen]
    slugs = [spec.slug for spec, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(f"Wrote hyphenation QA PDF: {args.output} ({len(pages)} leaves)")
    print(format_selection(chosen, page_texts))
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
