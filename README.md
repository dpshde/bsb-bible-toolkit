# BSB Bible PDF Toolkit

Generate custom PDFs and EPUBs from the Berean Standard Bible (BSB) source files.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Download a BSB book (Book 9 = 1 Samuel)
python download_bsb.py --book 9

# Extract text and structure
python extract_bsb.py --input bsb-book-9.pdf --output bsb-book-9.json

# Generate a custom PDF
python customize_bsb.py --input bsb-book-9.pdf --output my-bsb.pdf \
    --font-size 11 --margin 36 --no-footnotes

# Add route.bible links to all chapter headings
python add_route_links.py bsb-book-9.pdf bsb-linked.pdf
```

## Two Paths: PDF vs EPUB

This toolkit supports both PDF and EPUB output. Choose based on your needs:

| Feature | PDF | EPUB |
|---------|-----|------|
| **Font changes** | Layout breaks (fixed format) | ✓ Reflows naturally |
| **route.bible links** | ✓ Verse-range precision | ✓ Chapter-level (easy) |
| **File size** | ~18 MB (full Bible) | ~3.7 MB (full Bible) |
| **Mobile reading** | Heavy | Lightweight |
| **Print-ready** | ✓ Exact layout | Reflows to screen |

**Recommendation:** Use **EPUB** for font customization. Use **PDF** for print-ready output with verse-range links.

---

## EPUB Path (Recommended for Font Changes)

The EPUB is HTML-based, so font changes are trivial and text reflows automatically. No layout breakage.

```bash
# Download the BSB EPUB
# https://bereanbible.com/bsb.epub

# Customize with Lexend fonts + add route.bible links
python customize_epub.py bsb.epub bsb-lexend.epub \
    --font-dir fonts/ --add-links

# Output: bsb-lexend.epub with embedded Lexend fonts and clickable headings
```

The script:
1. Extracts the EPUB
2. Embeds all Lexend font variants (Regular, Medium, Bold, etc.)
3. Updates CSS to use `font-family: "Lexend"`
4. Adds `route.bible/{book}.{chapter}` links to every `<p class="hdg">` heading
5. Re-packages the EPUB

### EPUB Customization Options

| Flag | Description |
|------|-------------|
| `--font-dir` | Directory containing `.ttf` or `.otf` files |
| `--add-links` | Add `route.bible` links to section headings |

---

## PDF Path (Best for Print + Verse-Range Links)

### Add route.bible Links

`add_route_links.py` detects every BSB section heading by font heuristics and inserts a clickable link to the exact OSIS verse range on `https://route.bible`.

```bash
# Add verse-range links to every heading in a BSB PDF
python add_route_links.py bsb-book-9.pdf bsb-linked.pdf

# Works on any BSB PDF, including combined or customized ones
python customize_bsb.py --input bsb-book-9.pdf --output temp.pdf --no-footnotes
python add_route_links.py temp.pdf final.pdf
```

### Verse-Range Links

Each heading is linked to its specific verse range rather than the full chapter:

- `The Creation` → `https://route.bible/Gen.1.1-2`
- `The First Day` → `https://route.bible/Gen.1.3-5`
- `The Fourth Day` → `https://route.bible/Gen.1.14-19`
- `Hannah's Prayer` → `https://route.bible/1Sam.2.1-11`
- `The LORD Calls Samuel` → `https://route.bible/1Sam.3.1-14`

The script detects verse numbers by their small `Cambria-Bold` font (~6.8pt) and tracks them through the two-column layout to compute exact start/end verses for every heading.

### Change Font to Lexend (PDF)

**⚠️ Warning:** PDF is a fixed-layout format. Changing fonts breaks text wrapping because the new font has different character widths. The output is usable but may have overflow or spacing issues.

```bash
# Convert to Lexend (requires fonts in ./fonts/ directory)
python change_font.py input.pdf output.pdf

# The fonts/ directory should contain:
#   Lexend-Regular.ttf
#   Lexend-Bold.ttf
#   Lexend-Medium.ttf
#   Lexend-SemiBold.ttf
#   (and optionally others)
```

**Correct workflow for PDF:**

```bash
# 1. Add links first (detection needs original font names)
python add_route_links.py bsb-book-9.pdf bsb-linked.pdf

# 2. Then change font (layout will shift)
python change_font.py bsb-linked.pdf bsb-lexend.pdf
```

**For perfect font rendering, use the EPUB path instead.**

---

## What You Can Customize

| Flag | Description |
|------|-------------|
| `--font-size` | Base font size (default: 10) |
| `--margin` | Page margin in points (default: 72) |
| `--page-size` | `letter`, `a4`, `6x9`, `5x8` (default: 6x9) |
| `--no-footnotes` | Remove footnotes and cross-references |
| `--no-headers` | Remove section headers (e.g., "The Creation") |
| `--books` | Comma-separated book numbers to combine |
| `--range` | Page range, e.g., `10-50` |
| `--cover` | Path to a custom cover page PDF |
| `--watermark` | Add a watermark text |
| `--grayscale` | Convert to grayscale |
| `--two-column` | Reformat to two-column layout |

## BSB Book Numbers

| # | Book | # | Book | # | Book |
|---|------|---|------|---|------|
| 1 | Genesis | 2 | Exodus | 3 | Leviticus |
| 4 | Numbers | 5 | Deuteronomy | 6 | Joshua |
| 7 | Judges | 8 | Ruth | 9 | 1 Samuel |
| 10 | 2 Samuel | 11 | 1 Kings | 12 | 2 Kings |
| ... | (full list in `download_bsb.py --list`) | | | | |

## Examples

```bash
# Personal study Bible — larger font, no footnotes
python customize_bsb.py --input bsb-book-9.pdf --output study-bible.pdf \
    --font-size 12 --margin 48 --no-footnotes

# Combine multiple books into one PDF
python customize_bsb.py --books 1,2,3 --output pentateuch.pdf

# Extract just a chapter range (pages 100–200)
python customize_bsb.py --input bsb-book-9.pdf --range 100-200 \
    --output 1sam-ch7-15.pdf

# Generate a grayscale pocket edition
python customize_bsb.py --input bsb-book-9.pdf --output pocket.pdf \
    --page-size 5x8 --grayscale --font-size 9

# EPUB: Lexend font + route.bible links
python customize_epub.py bsb.epub bsb-lexend.epub \
    --font-dir fonts/ --add-links
```

## License

BSB text is public domain. This toolkit is MIT licensed.
