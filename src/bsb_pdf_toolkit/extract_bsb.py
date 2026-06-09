#!/usr/bin/env python3
"""
Extract text, structure, and metadata from a BSB PDF.
Outputs JSON with pages, text blocks, and detected headers.
"""
import argparse
import json
import sys
from pathlib import Path
import fitz  # pymupdf


def extract_structure(input_path: Path, output_path: Path):
    doc = fitz.open(input_path)
    pages = []

    for i in range(len(doc)):
        page = doc[i]
        blocks = page.get_text("blocks")
        text_blocks = []
        for b in blocks:
            x0, y0, x1, y1, text, block_no, block_type = b[:7]
            text_blocks.append({
                "x": round(float(x0), 2), "y": round(float(y0), 2),
                "width": round(float(x1 - x0), 2), "height": round(float(y1 - y0), 2),
                "text": text.strip(),
                "type": "image" if block_type == 1 else "text",
            })

        pages.append({
            "page_num": i + 1,
            "width": round(float(page.rect.width), 2),
            "height": round(float(page.rect.height), 2),
            "blocks": text_blocks,
        })

    result = {
        "source": str(input_path),
        "pages": len(doc),
        "metadata": doc.metadata,
        "page_data": pages,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"Extracted {len(doc)} pages to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Extract BSB PDF structure")
    parser.add_argument("--input", type=Path, required=True, help="Input PDF")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    extract_structure(args.input, args.output)


if __name__ == "__main__":
    main()
