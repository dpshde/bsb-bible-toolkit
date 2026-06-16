#!/usr/bin/env python3
"""
Primary draft workflow for designing the current BSB PDF.

During prototyping this is intentionally the single clear entry point:
download/reuse the current BSB USFM source, then render the primary PDF draft.
"""

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

import fitz

from .add_route_links import add_lexend_verse_links, add_route_links
from .change_font import FONT_PROFILES, change_font
from .compare_renders import DEFAULT_PAGES, build_primary_sheet, build_single_sheet, parse_pages
from .verify_artifacts import (
    EXPECTED_PRIMARY_COLORS,
    EXPECTED_PRIMARY_FONTS,
    EXPECTED_PRIMARY_SEMANTIC_SHA256,
    EXPECTED_PRIMARY_SHA256,
    EXPECTED_PRIMARY_SIZE,
    EXPECTED_SINGLE_COLORS,
    EXPECTED_SINGLE_FONTS,
    EXPECTED_SINGLE_LINKS,
    EXPECTED_SINGLE_ROUTE_LINKS,
    EXPECTED_SINGLE_SEMANTIC_SHA256,
    EXPECTED_SINGLE_SHA256,
    EXPECTED_SINGLE_SIZE,
    print_info,
    verify_artifact,
)


SOURCE_URL = "https://bereanbible.com/bsb-book-9.pdf"
DEFAULT_DRAFT_DIR = Path("drafts/primary")
SOURCE_FILENAME = "bsb-book-9.pdf"
LINKED_FILENAME = "bsb-route-links.pdf"
PDF_FILENAME = "bsb-primary-draft.pdf"
SINGLE_COLUMN_FILENAME = "bsb-single-column-draft.pdf"


def download_source(url: str, output_path: Path, force: bool = False) -> Path:
    if output_path.exists() and not force:
        print(f"Using existing source: {output_path}")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    print(f"Downloading source: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "bsb-bible-pdf-toolkit/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        with tmp_path.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    tmp_path.replace(output_path)
    print(f"Wrote source: {output_path}")
    return output_path


def render_pdf(
    source_path: Path,
    pdf_path: Path,
    font_dir: Path,
    work_dir: Path,
    font_scale: float,
    weight_profile: str,
    footer_scale: float,
    footer_shift: float,
    footer_text_threshold: float,
    body_gray: float,
    footer_gray: float,
    structural_gray: float,
    release_stage: str,
) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir.mkdir(parents=True, exist_ok=True)
    linked_path = work_dir / LINKED_FILENAME
    add_route_links(source_path, linked_path)
    change_font(
        linked_path,
        pdf_path,
        font_dir,
        font_scale=font_scale,
        weight_profile=weight_profile,
        footer_scale=footer_scale,
        footer_shift=footer_shift,
        footer_text_threshold=footer_text_threshold,
        body_gray=body_gray,
        footer_gray=footer_gray,
        structural_gray=structural_gray,
    )
    add_lexend_verse_links(pdf_path)
    add_primary_title_label(pdf_path, font_dir, release_stage)
    print(f"Wrote PDF: {pdf_path}")


def add_primary_title_label(pdf_path: Path, font_dir: Path, release_stage: str = "Draft") -> None:
    doc = fitz.open(pdf_path)
    page = doc[0]
    label = f"Primary Layout {release_stage}"
    font_path = font_dir / "Lexend-Bold.ttf"
    font_name = "LexendBold"
    font_size = 11
    page.insert_font(fontname=font_name, fontfile=str(font_path))
    font = fitz.Font(fontfile=str(font_path))
    text_width = font.text_length(label, fontsize=font_size)
    x = (page.rect.width - text_width) / 2
    page.insert_text((x, 388), label, fontsize=font_size, fontname=font_name, color=(0.08, 0.08, 0.08))
    doc.saveIncr()
    doc.close()


def verify_drafts(draft_dir: Path) -> None:
    checks = [
        (
            "primary",
            draft_dir / PDF_FILENAME,
            1120,
            (432.0, 648.0),
            4798,
            4798,
            EXPECTED_PRIMARY_FONTS,
            EXPECTED_PRIMARY_COLORS,
            EXPECTED_PRIMARY_SIZE,
            EXPECTED_PRIMARY_SHA256,
            EXPECTED_PRIMARY_SEMANTIC_SHA256,
        ),
        (
            "single-column",
            draft_dir / SINGLE_COLUMN_FILENAME,
            2251,
            (504.0, 756.0),
            EXPECTED_SINGLE_ROUTE_LINKS,
            EXPECTED_SINGLE_LINKS,
            EXPECTED_SINGLE_FONTS,
            EXPECTED_SINGLE_COLORS,
            EXPECTED_SINGLE_SIZE,
            EXPECTED_SINGLE_SHA256,
            EXPECTED_SINGLE_SEMANTIC_SHA256,
        ),
    ]
    errors = []
    for check in checks:
        item_errors, info = verify_artifact(*check)
        errors.extend(item_errors)
        if info:
            print_info(check[0], check[1], info)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("Verification passed.")


def compare_drafts(draft_dir: Path, reference_path: Path, pages, single_page: int) -> None:
    work_dir = draft_dir / "work"
    primary_output = work_dir / "primary-reference-comparison-sheet.png"
    single_output = work_dir / "single-column-comparison-sheet.png"
    build_primary_sheet(reference_path, draft_dir / PDF_FILENAME, primary_output, pages, 360)
    build_single_sheet(draft_dir / SINGLE_COLUMN_FILENAME, single_output, single_page, 520)
    print(primary_output)
    print(single_output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the primary BSB PDF draft")
    parser.add_argument("--draft-dir", type=Path, default=DEFAULT_DRAFT_DIR)
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--source", type=Path, help="Use a local BSB PDF instead of downloading")
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"))
    parser.add_argument("--weight-profile", choices=sorted(FONT_PROFILES), default="calm")
    parser.add_argument("--font-scale", type=float, default=0.86)
    parser.add_argument("--footer-scale", type=float, default=0.80)
    parser.add_argument("--footer-shift", type=float, default=9.0)
    parser.add_argument("--footer-text-threshold", type=float, default=110.0)
    parser.add_argument("--body-gray", type=float, default=0.08)
    parser.add_argument("--footer-gray", type=float, default=0.34)
    parser.add_argument("--structural-gray", type=float, default=0.03)
    parser.add_argument("--release-stage", default="Draft", help="Title-page status label, such as Draft or Version")
    parser.add_argument("--refresh-source", action="store_true", help="Download source even if it already exists")
    parser.add_argument("--source-only", action="store_true", help="Fetch/copy source without rendering PDF")
    parser.add_argument("--verify", action="store_true", help="Verify generated draft artifacts after rendering")
    parser.add_argument("--compare", action="store_true", help="Generate visual comparison sheets after rendering")
    parser.add_argument("--qa-only", action="store_true", help="Skip source/rendering and only run requested QA steps")
    parser.add_argument("--compare-pages", type=parse_pages, default=parse_pages(DEFAULT_PAGES))
    parser.add_argument("--single-compare-page", type=int, default=474)
    args = parser.parse_args()

    if args.qa_only and not (args.verify or args.compare):
        parser.error("--qa-only requires --verify and/or --compare")
    if args.source_only and (args.verify or args.compare):
        parser.error("--source-only cannot be combined with --verify or --compare")

    source_path = args.draft_dir / "source" / SOURCE_FILENAME
    work_dir = args.draft_dir / "work"
    pdf_path = args.draft_dir / PDF_FILENAME

    if not args.qa_only:
        if args.source:
            if not args.source.exists():
                raise SystemExit(f"Source not found: {args.source}")
            source_path.parent.mkdir(parents=True, exist_ok=True)
            if args.source.resolve() != source_path.resolve():
                shutil.copy2(args.source, source_path)
            print(f"Using local source: {source_path}")
        else:
            download_source(args.source_url, source_path, args.refresh_source)

    if not args.source_only and not args.qa_only:
        render_pdf(
            source_path,
            pdf_path,
            args.font_dir,
            work_dir,
            args.font_scale,
            args.weight_profile,
            args.footer_scale,
            args.footer_shift,
            args.footer_text_threshold,
            args.body_gray,
            args.footer_gray,
            args.structural_gray,
            args.release_stage,
        )

    if args.verify:
        verify_drafts(args.draft_dir)
    if args.compare:
        compare_drafts(args.draft_dir, source_path, args.compare_pages, args.single_compare_page)


if __name__ == "__main__":
    main()
