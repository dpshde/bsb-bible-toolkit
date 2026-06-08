#!/usr/bin/env python3
"""
Change the font of a BSB Bible PDF to Lexend (or any custom font).

This script extracts text from the source PDF, redacts the original text,
and re-inserts it with the new font. Images and page structure are preserved.

Note: Because font metrics differ (character widths, line heights), the
layout may shift slightly. For best results, regenerate the PDF with
`customize_bsb.py` after changing the font.
"""

import argparse
import sys
from pathlib import Path
import fitz

# Font mapping: original font pattern → (fontfile, synthetic_bold)
DEFAULT_FONT_MAP = {
    "Cambria-Bold": ("Lexend-Bold.ttf", False),
    "Cambria-Italic": ("Lexend-Regular.ttf", False),
    "Cambria": ("Lexend-Regular.ttf", False),
}


def load_font_map(font_dir: Path):
    """Build a font map pointing to actual font files and their PyMuPDF font names."""
    font_map = {}
    for pattern, (rel_path, synth_bold) in DEFAULT_FONT_MAP.items():
        font_path = font_dir / rel_path
        if font_path.exists():
            try:
                font = fitz.Font(fontfile=str(font_path))
                # Sanitize font name for PyMuPDF (no spaces allowed)
                safe_name = font.name.replace(" ", "-")
                font_map[pattern] = (str(font_path), safe_name, synth_bold)
            except Exception as e:
                print(f"Warning: could not load font {font_path}: {e}", file=sys.stderr)
        else:
            print(f"Warning: font file not found: {font_path}", file=sys.stderr)
    return font_map


def get_lexend_font(span: dict, font_map: dict):
    """Determine the Lexend font (path, name) for a given span."""
    font = span.get("font", "")
    for pattern, (font_path, font_name, synth_bold) in font_map.items():
        if pattern in font:
            return font_path, font_name, synth_bold
    # Fallback to regular
    fallback = font_map.get("Cambria", (None, "Lexend-Regular", False))
    return fallback[0], fallback[1], fallback[2]


def change_font_page(page: fitz.Page, font_map: dict, scale: float = 1.0):
    """Replace all text on a single page with the new font."""
    # Extract text structure
    blocks = page.get_text("dict")["blocks"]
    
    # Save existing links before redaction
    links = page.get_links()
    link_data = []
    for l in links:
        link_data.append({
            'uri': l['uri'],
            'from': l.get('from', None),
            'kind': l.get('kind', fitz.LINK_URI),
        })
    
    # Collect all text spans to re-insert
    spans_to_insert = []
    for b in blocks:
        if "lines" not in b:
            continue
        for line in b["lines"]:
            for span in line["spans"]:
                text = span["text"]
                if not text.strip():
                    continue
                font_path, font_name, _ = get_lexend_font(span, font_map)
                spans_to_insert.append({
                    "text": text,
                    "origin": span["origin"],
                    "bbox": span["bbox"],
                    "size": span["size"] * scale,
                    "font_path": font_path,
                    "font_name": font_name,
                    "flags": span.get("flags", 0),
                })

    # Add redaction annotations for all text blocks
    for b in blocks:
        if "lines" not in b:
            continue
        bbox = fitz.Rect(b["bbox"])
        page.add_redact_annot(bbox)

    # Apply redactions (removes text but keeps images)
    page.apply_redactions()

    # Load all needed fonts into the page before inserting text
    needed_fonts = {s["font_name"]: s["font_path"] for s in spans_to_insert}
    for font_name, font_path in needed_fonts.items():
        if font_path:
            try:
                page.insert_font(fontname=font_name, fontfile=font_path)
            except Exception as e:
                print(f"Warning: could not insert font {font_name}: {e}", file=sys.stderr)

    # Re-insert text with new font
    for span in spans_to_insert:
        page.insert_text(
            span["origin"],
            span["text"],
            fontsize=span["size"],
            fontname=span["font_name"],
            color=(0, 0, 0),
        )
    
    # Re-add links
    for ld in link_data:
        page.insert_link({
            'kind': ld['kind'],
            'from': ld['from'],
            'uri': ld['uri'],
        })


def change_font(
    input_path: Path,
    output_path: Path,
    font_dir: Path,
    font_scale: float = 1.0,
    page_range: str = None,
):
    """Change font throughout a PDF."""
    font_map = load_font_map(font_dir)
    if not font_map:
        print("Error: No font files found in", font_dir, file=sys.stderr)
        sys.exit(1)

    print(f"Opening {input_path}...")
    doc = fitz.open(input_path)
    
    start_page = 0
    end_page = len(doc) - 1
    
    if page_range:
        parts = page_range.split("-")
        start_page = int(parts[0]) - 1 if parts[0] else 0
        end_page = int(parts[1]) - 1 if len(parts) > 1 and parts[1] else len(doc) - 1

    print(f"Processing pages {start_page + 1}–{end_page + 1}...")
    for page_num in range(start_page, end_page + 1):
        page = doc[page_num]
        change_font_page(page, font_map, font_scale)
        if (page_num + 1) % 50 == 0:
            print(f"  {page_num + 1} pages done")

    print(f"Saving to {output_path}...")
    doc.save(output_path)
    doc.close()
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Change font in a BSB PDF to Lexend")
    parser.add_argument("input", type=Path, help="Input PDF")
    parser.add_argument("output", type=Path, help="Output PDF")
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"), help="Directory containing font files")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Scale font size by this factor")
    parser.add_argument("--range", type=str, help="Page range, e.g. 1-20")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    change_font(
        input_path=args.input,
        output_path=args.output,
        font_dir=args.font_dir,
        font_scale=args.font_scale,
        page_range=args.range,
    )


if __name__ == "__main__":
    main()
