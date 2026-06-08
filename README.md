# BSB Bible PDF Toolkit

Generate custom PDFs from the Berean Standard Bible (BSB) source files.

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
python add_route_links.py --input bsb-book-9.pdf --output bsb-linked.pdf
```

## Add route.bible Links

`add_route_links.py` detects every BSB section heading (e.g., "The Creation", "Elkanah and His Wives") by font heuristics and inserts a clickable link to `https://route.bible/skill.md`.

```bash
# Add links to every chapter heading in a BSB PDF
python add_route_links.py --input bsb-book-9.pdf --output bsb-linked.pdf

# Works on any BSB PDF, including combined or customized ones
python customize_bsb.py --input bsb-book-9.pdf --output temp.pdf --no-footnotes
python add_route_links.py --input temp.pdf --output final.pdf
```

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
```

## License

BSB text is public domain. This toolkit is MIT licensed.
