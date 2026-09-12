#!/usr/bin/env python3
"""Build a compact poetry QA sheet from Psalms stress leaves.

Compiles Genesis + Psalms (grid proof only) so Psalm 1 keeps the compact
book title, then extracts Psalm 1 and Psalm 119 ALEPH. Never touches
fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compose_travel_hotspots import (
    BookFace,
    HotspotSpec,
    book_catalog,
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    render_hotspot_pngs,
    select_hotspot_pages,
)
from .generate_travel_pdf import DEFAULT_GRID_FONT_DIR, DEFAULT_USFM, GRID_PROOF_WATERMARK

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "poetry-books-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "poetry-books-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-poetry-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "poetry"
PNG_DPI = 120

POETRY_QA_BOOKS = ("Genesis", "Psalms")
POETRY_QA_LEAVES = (
    HotspotSpec(
        slug="psalm-1",
        label="Psalm 1 poetry",
        book="Psalms",
        pick="first",
        require=("Blessed is the man",),
    ),
    HotspotSpec(
        slug="psalm-119",
        label="Psalm 119 ALEPH",
        book="Psalms",
        pick="contains",
        needles=("ALEPH",),
        require=("ALEPH",),
        forbid=("א",),
    ),
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile Genesis/Psalms and extract a poetry QA sheet. "
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
            print(f"Missing poetry source PDF: {args.source_pdf}", file=sys.stderr)
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
            books=POETRY_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        if args.usfm.is_file():
            catalog = book_catalog(args.usfm, books=POETRY_QA_BOOKS)
        else:
            catalog = [BookFace(book=name, title=name, heading=name) for name in POETRY_QA_BOOKS]
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_hotspot_pages(page_texts, catalog, specs=POETRY_QA_LEAVES)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no in chosen]
    slugs = [spec.slug for spec, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(f"Wrote poetry QA PDF: {args.output} ({len(pages)} leaves)")
    print("Poetry QA leaves (source page → leaf):")
    for spec, page_no in chosen:
        print(f"  {spec.slug}: source p.{page_no}  {spec.label} ({spec.book})")
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
