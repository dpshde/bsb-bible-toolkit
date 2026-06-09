#!/usr/bin/env python3
"""Render side-by-side visual comparison sheets for BSB PDF drafts."""

import argparse
from pathlib import Path

import fitz
from PIL import Image, ImageDraw


DEFAULT_PAGES = "249,252,500,1000"


def parse_pages(value: str):
    pages = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        pages.append(int(item))
    if not pages:
        raise argparse.ArgumentTypeError("at least one page is required")
    return pages


def render_page(pdf_path: Path, page_no: int, width: int):
    with fitz.open(pdf_path) as doc:
        if page_no < 1 or page_no > len(doc):
            raise ValueError(f"{pdf_path} has no page {page_no}")
        page = doc[page_no - 1]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    scale = width / img.width
    return img.resize((width, int(img.height * scale)), Image.Resampling.LANCZOS)


def draw_label(draw, xy, text):
    draw.text(xy, text, fill=(20, 20, 20))


def build_primary_sheet(reference_pdf: Path, primary_pdf: Path, output_path: Path, pages, width: int):
    rows = []
    gap = 30
    label_height = 28
    row_width = width * 2 + gap
    for page_no in pages:
        reference = render_page(reference_pdf, page_no, width)
        primary = render_page(primary_pdf, page_no, width)
        row_height = max(reference.height, primary.height) + label_height + 10
        row = Image.new("RGB", (row_width, row_height), (255, 255, 255))
        draw = ImageDraw.Draw(row)
        draw_label(draw, (0, 0), f"Official page {page_no}")
        draw_label(draw, (width + gap, 0), f"Current primary page {page_no}")
        row.paste(reference, (0, label_height))
        row.paste(primary, (width + gap, label_height))
        rows.append(row)

    sheet_gap = 20
    sheet_height = sum(row.height for row in rows) + sheet_gap * (len(rows) - 1)
    sheet = Image.new("RGB", (row_width, sheet_height), (245, 245, 245))
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + sheet_gap
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def build_single_sheet(single_pdf: Path, output_path: Path, page_no: int, width: int):
    page = render_page(single_pdf, page_no, width)
    label_height = 32
    margin = 20
    sheet = Image.new("RGB", (page.width + margin * 2, page.height + label_height + margin), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    draw_label(draw, (0, 0), f"Single-column variant page {page_no}")
    sheet.paste(page, (margin, label_height))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main():
    parser = argparse.ArgumentParser(description="Create BSB PDF visual comparison sheets")
    parser.add_argument("--reference", type=Path, default=Path("references/bsb-book-9.pdf"))
    parser.add_argument("--primary", type=Path, default=Path("drafts/primary/bsb-primary-draft.pdf"))
    parser.add_argument("--single", type=Path, default=Path("drafts/primary/bsb-single-column-draft.pdf"))
    parser.add_argument("--pages", type=parse_pages, default=parse_pages(DEFAULT_PAGES))
    parser.add_argument("--single-page", type=int, default=474)
    parser.add_argument("--output-dir", type=Path, default=Path("drafts/primary/work"))
    parser.add_argument("--width", type=int, default=360)
    parser.add_argument("--single-width", type=int, default=520)
    args = parser.parse_args()

    primary_output = args.output_dir / "primary-reference-comparison-sheet.png"
    single_output = args.output_dir / "single-column-comparison-sheet.png"

    build_primary_sheet(args.reference, args.primary, primary_output, args.pages, args.width)
    build_single_sheet(args.single, single_output, args.single_page, args.single_width)
    print(primary_output)
    print(single_output)


if __name__ == "__main__":
    main()
