#!/usr/bin/env python3
"""
Change the font of a BSB Bible PDF to Lexend (or any custom font family).

This script extracts text from the source PDF, redacts the original text,
and re-inserts it with the new font. Images and page structure are preserved.

The script dynamically selects the appropriate font variant based on the
original text's style (bold, italic, etc.).

Note: Because font metrics differ (character widths, line heights), the
layout may shift slightly. For best results, regenerate the PDF with
`customize_bsb.py` after changing the font.
"""

import argparse
import sys
from pathlib import Path
import fitz

# Font mapping: original font name pattern → Lexend variant
# The script also uses font flags to determine bold/italic properties
DEFAULT_FONT_MAP = {
    "Cambria-BoldItalic": "Lexend-SemiBold.ttf",
    "Cambria-Bold": "Lexend-Bold.ttf",
    "Cambria-Italic": "Lexend-Medium.ttf",
    "Cambria": "Lexend-Regular.ttf",
}

# Fallback mapping for dynamic selection based on font properties
STYLE_MAP = {
    (True, True): "Lexend-SemiBold.ttf",    # bold + italic
    (True, False): "Lexend-Bold.ttf",       # bold only
    (False, True): "Lexend-Medium.ttf",     # italic only
    (False, False): "Lexend-Regular.ttf",   # regular
}


def load_font_map(font_dir: Path):
    """Build a font map pointing to actual font files and their PyMuPDF font names."""
    font_map = {}
    for pattern, rel_path in DEFAULT_FONT_MAP.items():
        font_path = font_dir / rel_path
        if font_path.exists():
            try:
                font = fitz.Font(fontfile=str(font_path))
                # Sanitize font name for PyMuPDF (no spaces allowed)
                safe_name = font.name.replace(" ", "-")
                font_map[pattern] = (str(font_path), safe_name)
            except Exception as e:
                print(f"Warning: could not load font {font_path}: {e}", file=sys.stderr)
        else:
            print(f"Warning: font file not found: {font_path}", file=sys.stderr)
    
    # Also build style map
    style_font_map = {}
    for (bold, italic), rel_path in STYLE_MAP.items():
        font_path = font_dir / rel_path
        if font_path.exists():
            try:
                font = fitz.Font(fontfile=str(font_path))
                safe_name = font.name.replace(" ", "-")
                style_font_map[(bold, italic)] = (str(font_path), safe_name)
            except Exception as e:
                print(f"Warning: could not load font {font_path}: {e}", file=sys.stderr)
    
    return font_map, style_font_map


def get_font_for_span(span: dict, font_map: dict, style_font_map: dict):
    """Determine the appropriate font for a given span based on original font name and flags."""
    font_name = span.get("font", "")
    
    # First try exact font name match
    for pattern, (font_path, safe_name) in font_map.items():
        if pattern in font_name:
            return font_path, safe_name
    
    # Fallback: use font flags to determine style
    flags = span.get("flags", 0)
    # PyMuPDF font flags: bit 0 = fixed pitch, bit 1 = serif, bit 2 = symbolic, bit 3 = script
    # But we can use the font name patterns to detect bold/italic
    is_bold = "Bold" in font_name or (flags & 16) != 0
    is_italic = "Italic" in font_name or (flags & 2) != 0
    
    font_path, safe_name = style_font_map.get((is_bold, is_italic), style_font_map.get((False, False)))
    return font_path, safe_name


def change_font_page(page: fitz.Page, font_map: dict, style_font_map: dict, scale: float = 1.0):
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
                font_path, font_name = get_font_for_span(span, font_map, style_font_map)
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
    needed_fonts = {}
    for s in spans_to_insert:
        if s["font_name"] not in needed_fonts:
            needed_fonts[s["font_name"]] = s["font_path"]
    
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
    font_map, style_font_map = load_font_map(font_dir)
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
        change_font_page(page, font_map, style_font_map, font_scale)
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
    parser.add_argument("--font-scale", type=float, default=0.85, help="Scale font size by this factor")
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
