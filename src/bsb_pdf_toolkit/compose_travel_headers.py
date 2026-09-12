"""Extract a running-header QA sheet from compiled John (grid proof).

Compiles John only, then copies interior leaves so verso/recto book +
chapter:verse-range heads can be checked. Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .compose_travel_hotspots import (
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    render_hotspot_pngs,
)
from .generate_travel_pdf import DEFAULT_GRID_FONT_DIR, DEFAULT_USFM, GRID_PROOF_WATERMARK

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "headers-john-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "headers-john-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-running-headers-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "headers"
PNG_DPI = 120

HEADER_QA_BOOKS = ("John",)
HEADER_PAGES = (2, 3, 6, 10)
HEADER_SLUGS = (
    "john-p02",
    "john-p03",
    "john-p06",
    "john-p10",
)

# Compact travel grammar: JOHN · 4:17–38 or JOHN · 3:31–4:2
HEADER_RANGE_RE = re.compile(
    r"JOHN\s*[·.]\s*\d+:\d+(?:[–-]\d+(?::\d+)?)?",
    re.IGNORECASE,
)


def page_has_verse_header(text: str) -> bool:
    """True when extracted page text includes a book + chapter:verse running head."""
    compact = re.sub(r"\s+", " ", text or "")
    return bool(HEADER_RANGE_RE.search(compact))


def validate_header_pages(page_texts: list[str], pages: tuple[int, ...] = HEADER_PAGES) -> None:
    """Require a verse-range running head on each selected 1-based source page."""
    count = len(page_texts)
    for page_no in pages:
        if page_no < 1 or page_no > count:
            raise ValueError(f"John PDF has {count} pages; cannot take {page_no}")
        text = page_texts[page_no - 1]
        if not page_has_verse_header(text):
            raise ValueError(
                f"page {page_no} is missing a JOHN chapter:verse running head"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile John and extract running-header QA leaves. "
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
            print(f"Missing header source PDF: {args.source_pdf}", file=sys.stderr)
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
            books=HEADER_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        page_texts = load_page_texts(args.source_pdf)
        validate_header_pages(page_texts, HEADER_PAGES)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    extract_sampler_pdf(args.source_pdf, args.output, list(HEADER_PAGES))
    print(
        f"Wrote running-header QA PDF: {args.output} "
        f"({len(HEADER_PAGES)} leaves; source pages {', '.join(str(p) for p in HEADER_PAGES)})"
    )
    if not args.no_png:
        pngs = render_hotspot_pngs(
            args.output, args.png_dir, list(HEADER_SLUGS), dpi=args.dpi
        )
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
