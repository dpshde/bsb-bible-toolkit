#!/usr/bin/env python3
"""
Add https://route.bible/skill.md links to every BSB section heading.

Detects headings by font heuristics (Cambria-Bold/Cambria-Italic at ~9pt)
and inserts a URI link covering the heading's bounding box.
"""
import argparse
import sys
from pathlib import Path
import fitz  # pymupdf

LINK_URL = "https://route.bible/skill.md"


def is_heading_span(span: dict) -> bool:
    """Check if a text span is a section heading."""
    text = span.get("text", "").strip()
    if not text:
        return False
    font = span.get("font", "")
    size = span.get("size", 0.0)

    # BSB section headings are Cambria-Bold or Cambria-Italic at ~9pt
    if not (8.5 <= size <= 9.5):
        return False
    if "Cambria-Bold" not in font and "Cambria-Italic" not in font:
        return False

    # Filter out page headers/footers (e.g., "250    |    1 Samuel 1:24")
    if "|" in text:
        return False

    # Filter out tiny fragments
    if len(text) <= 2:
        return False

    return True


def is_heading_block(block: dict) -> bool:
    """Check if a text block contains heading spans."""
    if "lines" not in block:
        return False
    for line in block["lines"]:
        for span in line["spans"]:
            if is_heading_span(span):
                return True
    return False


def add_links_to_pdf(input_path: Path, output_path: Path):
    doc = fitz.open(input_path)
    total_links = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if not is_heading_block(block):
                continue

            bbox = fitz.Rect(block["bbox"])
            lnk = {
                "kind": fitz.LINK_URI,
                "from": bbox,
                "uri": LINK_URL,
            }
            page.insert_link(lnk)
            total_links += 1

    doc.save(output_path)
    doc.close()

    print(f"Added {total_links} links to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Add route.bible links to all BSB section headings"
    )
    parser.add_argument("--input", type=Path, required=True, help="Input BSB PDF")
    parser.add_argument("--output", type=Path, required=True, help="Output PDF")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    add_links_to_pdf(args.input, args.output)


if __name__ == "__main__":
    main()
