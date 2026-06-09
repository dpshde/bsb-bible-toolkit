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

# Font mapping: original font name pattern → Lexend variant. Lighter profiles
# reduce Lexend's geometric heaviness while staying within the Lexend family.
FONT_PROFILES = {
    "airy": {
        "Cambria-BoldItalic": "Lexend-Regular.ttf",
        "Cambria-Bold": "Lexend-Medium.ttf",
        "Cambria-Italic": "Lexend-Light.ttf",
        "Cambria": "Lexend-Thin.ttf",
    },
    "calm": {
        "Cambria-BoldItalic": "Lexend-Regular.ttf",
        "Cambria-Bold": "Lexend-Medium.ttf",
        "Cambria-Italic": "Lexend-Regular.ttf",
        "Cambria": "Lexend-Light.ttf",
    },
    "soft": {
        "Cambria-BoldItalic": "Lexend-Medium.ttf",
        "Cambria-Bold": "Lexend-SemiBold.ttf",
        "Cambria-Italic": "Lexend-Regular.ttf",
        "Cambria": "Lexend-Light.ttf",
    },
    "standard": {
        "Cambria-BoldItalic": "Lexend-SemiBold.ttf",
        "Cambria-Bold": "Lexend-Bold.ttf",
        "Cambria-Italic": "Lexend-Medium.ttf",
        "Cambria": "Lexend-Regular.ttf",
    },
}

STYLE_PROFILES = {
    "airy": {
        (True, True): "Lexend-Regular.ttf",
        (True, False): "Lexend-Medium.ttf",
        (False, True): "Lexend-Light.ttf",
        (False, False): "Lexend-Thin.ttf",
    },
    "calm": {
        (True, True): "Lexend-Regular.ttf",
        (True, False): "Lexend-Medium.ttf",
        (False, True): "Lexend-Regular.ttf",
        (False, False): "Lexend-Light.ttf",
    },
    "soft": {
        (True, True): "Lexend-Medium.ttf",
        (True, False): "Lexend-SemiBold.ttf",
        (False, True): "Lexend-Regular.ttf",
        (False, False): "Lexend-Light.ttf",
    },
    "standard": {
        (True, True): "Lexend-SemiBold.ttf",
        (True, False): "Lexend-Bold.ttf",
        (False, True): "Lexend-Medium.ttf",
        (False, False): "Lexend-Regular.ttf",
    },
}

# Backward-compatible constants for callers that imported these names.
DEFAULT_FONT_MAP = FONT_PROFILES["standard"]
STYLE_MAP = STYLE_PROFILES["standard"]

# The script also uses font flags to determine bold/italic properties.
STANDARD_FONT_MAP = {
    "Cambria-BoldItalic": "Lexend-SemiBold.ttf",
    "Cambria-Bold": "Lexend-Bold.ttf",
    "Cambria-Italic": "Lexend-Medium.ttf",
    "Cambria": "Lexend-Regular.ttf",
}


def load_font_map(font_dir: Path, weight_profile: str = "calm"):
    """Build a font map pointing to actual font files and their PyMuPDF font names."""
    if weight_profile not in FONT_PROFILES:
        raise ValueError(f"Unknown weight profile: {weight_profile}")

    font_map = {}
    for pattern, rel_path in FONT_PROFILES[weight_profile].items():
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
    for (bold, italic), rel_path in STYLE_PROFILES[weight_profile].items():
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


def copy_link_data(page: fitz.Page):
    links = []
    for link in page.get_links():
        if link.get("from") is None:
            continue
        data = {
            "kind": link.get("kind", fitz.LINK_URI),
            "from": link["from"],
        }
        for key in ("uri", "page", "to", "zoom"):
            if key in link:
                data[key] = link[key]
        if data.get("uri") or data.get("page") is not None:
            links.append(data)
    return links


def delete_links(page: fitz.Page):
    for link in page.get_links():
        page.delete_link(link)


def shift_footer_links(links, page_height: float, footer_threshold: float, footer_shift: float):
    if not footer_shift:
        return links
    shifted = []
    footer_y = page_height - footer_threshold
    for link in links:
        item = dict(link)
        rect = fitz.Rect(item["from"])
        if rect.y0 >= footer_y:
            rect.y0 += footer_shift
            rect.y1 += footer_shift
            item["from"] = rect
        shifted.append(item)
    return shifted


def is_footer_line(line: dict, page_height: float, footer_threshold: float):
    """Detect footnote/cross-reference footer lines without catching body text."""
    if line["bbox"][1] < page_height - footer_threshold:
        return False

    text_spans = [span for span in line["spans"] if span["text"].strip()]
    if not text_spans:
        return False

    # BSB footer notes use 6.43/7.30 pt Cambria spans. Body lines can extend
    # into the same lower band, so position alone makes dense pages worse.
    return max(span["size"] for span in text_spans) <= 7.6


def gray_color(value: float):
    value = max(0.0, min(1.0, value))
    return (value, value, value)


def is_structural_span(span: dict):
    """Keep headings, verse numbers, chapter numbers, and markers fully black."""
    source_font = span.get("source_font", "")
    source_size = span.get("source_size", span["size"])
    flags = span.get("flags", 0)
    return source_size >= 10.5 or source_size <= 7.0 or "Bold" in source_font or (flags & 16) != 0


def is_inline_note_marker(span: dict):
    source_font = span.get("source_font", "")
    source_size = span.get("source_size", span["size"])
    flags = span.get("flags", 0)
    is_bold = "Bold" in source_font or (flags & 16) != 0
    is_italic = "Italic" in source_font
    return source_size <= 7.0 and is_italic and not is_bold


def span_color(span: dict, body_gray: float, footer_gray: float, structural_gray: float):
    if span.get("is_footer"):
        return gray_color(footer_gray)
    if is_inline_note_marker(span):
        return gray_color(footer_gray)
    if is_structural_span(span):
        if span.get("source_size", span["size"]) > 7.0:
            return gray_color(structural_gray)
        return (0, 0, 0)
    return gray_color(body_gray)


def measure_text(font_cache: dict, span: dict, size: float):
    font = font_cache.get(span["font_name"])
    if not font:
        return 0
    width = font.text_length(span["text"], fontsize=size)
    if span["text"].strip() == "":
        width = max(width, size * 0.90)
    return width


def line_fit_scale(line: dict, font_cache: dict):
    spans = line["spans"]
    if not spans:
        return 1.0

    original_left = min(span["bbox"][0] for span in spans)
    original_right = max(span["bbox"][2] for span in spans)
    original_width = max(1.0, original_right - original_left)

    measured_width = 0
    fixed_gap = 0
    previous_right = None
    for span in spans:
        if previous_right is not None:
            fixed_gap += max(0, span["bbox"][0] - previous_right)
        measured_width += measure_text(font_cache, span, span["size"])
        previous_right = span["bbox"][2]

    available = max(1.0, original_width - fixed_gap)
    if measured_width <= available:
        return 1.0
    return max(0.65, min(1.0, available / measured_width))


def change_font_page(
    page: fitz.Page,
    font_map: dict,
    style_font_map: dict,
    scale: float = 1.0,
    footer_scale: float = 1.0,
    footer_shift: float = 0,
    footer_threshold: float = 55,
    footer_text_threshold: float = None,
    body_gray: float = 0.0,
    footer_gray: float = 0.0,
    structural_gray: float = 0.0,
):
    """Replace all text on a single page with the new font."""
    # Extract text structure
    blocks = page.get_text("dict")["blocks"]

    # Save existing links before redaction
    link_data = copy_link_data(page)
    link_data = shift_footer_links(link_data, page.rect.height, footer_threshold, footer_shift)
    delete_links(page)
    footer_text_threshold = footer_text_threshold if footer_text_threshold is not None else footer_threshold

    # Collect all text lines to re-insert. Lexend is wider than Cambria in many
    # places, so draw spans cumulatively per line instead of reusing every
    # original x-coordinate. This preserves line breaks without span collisions.
    lines_to_insert = []
    for b in blocks:
        if "lines" not in b:
            continue
        for line in b["lines"]:
            line_is_footer = is_footer_line(line, page.rect.height, footer_text_threshold)
            spans = []
            for span in line["spans"]:
                text = span["text"]
                if not text:
                    continue
                font_path, font_name = get_font_for_span(span, font_map, style_font_map)
                size = span["size"] * scale
                origin = span["origin"]
                if line_is_footer:
                    size *= footer_scale
                    origin = (origin[0], origin[1] + footer_shift)
                spans.append({
                    "text": text,
                    "origin": origin,
                    "bbox": span["bbox"],
                    "size": size,
                    "source_font": span.get("font", ""),
                    "source_size": span["size"],
                    "font_path": font_path,
                    "font_name": font_name,
                    "flags": span.get("flags", 0),
                    "is_footer": line_is_footer,
                })
            if spans:
                spans.sort(key=lambda item: (item["bbox"][0], item["origin"][1]))
                lines_to_insert.append({
                    "bbox": line["bbox"],
                    "spans": spans,
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
    for line in lines_to_insert:
        for span in line["spans"]:
            if span["font_name"] not in needed_fonts:
                needed_fonts[span["font_name"]] = span["font_path"]
    
    font_cache = {}
    for font_name, font_path in needed_fonts.items():
        if font_path:
            try:
                page.insert_font(fontname=font_name, fontfile=font_path)
                font_cache[font_name] = fitz.Font(fontfile=font_path)
            except Exception as e:
                print(f"Warning: could not insert font {font_name}: {e}", file=sys.stderr)

    # Re-insert text with new font, preserving original baselines and gaps.
    for line in lines_to_insert:
        fit_scale = line_fit_scale(line, font_cache)
        cursor_x = line["spans"][0]["origin"][0]
        previous_right = None
        for span in line["spans"]:
            if previous_right is not None:
                cursor_x += max(0, span["bbox"][0] - previous_right)
            size = span["size"] * fit_scale
            if span["text"].strip():
                page.insert_text(
                    (cursor_x, span["origin"][1]),
                    span["text"],
                    fontsize=size,
                    fontname=span["font_name"],
                    color=span_color(span, body_gray, footer_gray, structural_gray),
                )
            cursor_x += measure_text(font_cache, span, size)
            previous_right = span["bbox"][2]

    # Re-add links
    for link in link_data:
        page.insert_link(link)


def change_font(
    input_path: Path,
    output_path: Path,
    font_dir: Path,
    font_scale: float = 1.0,
    weight_profile: str = "calm",
    footer_scale: float = 0.80,
    footer_shift: float = 9.0,
    footer_threshold: float = 55,
    footer_text_threshold: float = 110,
    body_gray: float = 0.08,
    footer_gray: float = 0.34,
    structural_gray: float = 0.03,
    page_range: str = None,
):
    """Change font throughout a PDF."""
    font_map, style_font_map = load_font_map(font_dir, weight_profile)
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
        change_font_page(
            page,
            font_map,
            style_font_map,
            font_scale,
            footer_scale=footer_scale,
            footer_shift=footer_shift,
            footer_threshold=footer_threshold,
            footer_text_threshold=footer_text_threshold,
            body_gray=body_gray,
            footer_gray=footer_gray,
            structural_gray=structural_gray,
        )
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
    parser.add_argument("--weight-profile", choices=sorted(FONT_PROFILES), default="calm", help="Lexend weight mapping to use")
    parser.add_argument("--font-scale", type=float, default=0.86, help="Scale font size by this factor")
    parser.add_argument("--footer-scale", type=float, default=0.80, help="Additional scale for footer text")
    parser.add_argument("--footer-shift", type=float, default=9.0, help="Move footer text down by this many points")
    parser.add_argument("--footer-threshold", type=float, default=55.0, help="Treat lines this many points from the page bottom as footer text")
    parser.add_argument("--footer-text-threshold", type=float, default=110.0, help="Treat small text this many points from the page bottom as footer text")
    parser.add_argument("--body-gray", type=float, default=0.08, help="Gray value for regular body text, where 0 is black")
    parser.add_argument("--footer-gray", type=float, default=0.34, help="Gray value for footer text, where 0 is black")
    parser.add_argument("--structural-gray", type=float, default=0.03, help="Gray value for headings and large structural text, where 0 is black")
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
        weight_profile=args.weight_profile,
        footer_scale=args.footer_scale,
        footer_shift=args.footer_shift,
        footer_threshold=args.footer_threshold,
        footer_text_threshold=args.footer_text_threshold,
        body_gray=args.body_gray,
        footer_gray=args.footer_gray,
        structural_gray=args.structural_gray,
        page_range=args.range,
    )


if __name__ == "__main__":
    main()
