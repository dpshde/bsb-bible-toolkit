# BSB Bible PDF Toolkit

Generate custom PDFs and EPUBs from the Berean Standard Bible (BSB) source files.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Build the primary PDF draft from the official fixed-layout BSB PDF
python design_bsb.py
```

The current prototyping flow has one primary draft. It uses
`https://bereanbible.com/bsb-book-9.pdf` as the visual baseline, adds
route.bible annotations, then redraws the fixed layout with Lexend.

| Path | Purpose |
|------|---------|
| `design_bsb.py` | Single entry point for the draft workflow |
| `src/bsb_pdf_toolkit/` | Python package containing generators and utilities |
| `fonts/` | Font assets used by draft rendering |
| `drafts/primary/README.md` | Current draft manifest and QA record |
| `drafts/primary/source/bsb-book-9.pdf` | Downloaded or supplied fixed-layout source |
| `drafts/primary/work/bsb-route-links.pdf` | Intermediate source with route.bible links |
| `drafts/primary/bsb-primary-draft.pdf` | Latest generated PDF iteration |

To rebuild from a freshly downloaded source:

```bash
python design_bsb.py --refresh-source
```

To use a local BSB PDF instead of downloading:

```bash
python design_bsb.py --source path/to/bsb-book-9.pdf
```

To verify the current generated artifacts and refresh the visual comparison
sheets without rebuilding:

```bash
python design_bsb.py --qa-only --verify --compare
```

`--qa-only` must be paired with `--verify`, `--compare`, or both.

Spacing can be tuned without changing the source layout:

```bash
python design_bsb.py --weight-profile calm --font-scale 0.86 --footer-scale 0.80 --footer-shift 9 --body-gray 0.08 --footer-gray 0.34 --structural-gray 0.03
```

The primary draft uses the calmer Lexend profile by default:

| Profile | Mapping |
|---------|---------|
| `calm` | Lexend Light body, Regular italics, Medium headings/verse numbers |
| `soft` | Lexend Light body, Regular italics, SemiBold headings/verse numbers |
| `airy` | Lexend Thin body, Light italics, Medium headings/verse numbers |
| `standard` | Lexend Regular body, Medium italics, Bold headings/verse numbers |
 
An exploratory single-column reflow is also available:

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.generate_reflow_pdf \
    drafts/primary/source/engbsb_usfm.zip \
    drafts/primary/bsb-single-column-draft.pdf \
    --font-dir fonts --columns 1
```

Common single-column tuning flags include `--single-margin-x`,
`--single-body-size`, `--single-body-leading`, `--single-book-title-font`,
`--single-dropcap-size`, `--single-dropcap-padding`,
`--single-dropcap-protected-lines`, `--single-verse-size`, and
`--single-verse-baseline-shift`.
The default book title face is `Lexend-Bold`.

To generate visual QA sheets for judging the current typography against the
official source:

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.compare_renders
```

To verify the generated PDF artifacts structurally:

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.verify_artifacts
```

Add `--strict-fingerprints` when you need the current SHA-256 fingerprints to
match exactly. The default verifier enforces stable semantic fingerprints and
reports raw PDF hashes.

## CI/CD Asset Delivery

This repo includes a GitHub Actions workflow at
`.github/workflows/deliver-assets.yml` that verifies the committed PDF
artifacts, packages them with SHA-256 checksums, uploads the package as a
separate GitHub Actions artifact per variant, and publishes the variants to
itch.io through Butler.

Configure these repository secrets before enabling delivery:

| Secret | Value |
|--------|-------|
| `BUTLER_API_KEY` | itch.io Butler API key |
| `ITCH_PROJECT` | itch project target in `user/project` format |

The workflow publishes two Butler channels:

| Channel | Contents |
|---------|----------|
| `primary-fixed-layout-pdf` | `Berean Standard Bible - Primary Fixed Layout Draft.pdf` |
| `single-column-pdf` | `Berean Standard Bible - Single Column Draft.pdf` |

The workflow also uploads each variant as an individually downloadable GitHub
Actions artifact:

| Artifact prefix | Contents |
|-----------------|----------|
| `berean-standard-bible-primary-fixed-layout-pdf-` | Primary fixed-layout PDF package |
| `berean-standard-bible-single-column-pdf-` | Single-column PDF package |

Run it manually from GitHub Actions with `dry_run: true` to verify/package
without pushing to itch.io.

## Legacy/Utility Commands

```bash
# Legacy downloader utility
PYTHONPATH=src python -m bsb_pdf_toolkit.download_bsb --book 9

# Extract text and structure
PYTHONPATH=src python -m bsb_pdf_toolkit.extract_bsb --input bsb-book-9.pdf --output bsb-book-9.json

# Generate a custom PDF
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --input bsb-book-9.pdf --output my-bsb.pdf \
    --font-size 11 --margin 36 --no-footnotes

# Add route.bible links to all chapter headings
PYTHONPATH=src python -m bsb_pdf_toolkit.add_route_links bsb-book-9.pdf bsb-linked.pdf
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
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_epub bsb.epub bsb-lexend.epub \
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
It adds new route.bible annotations; it does not rewrite existing URI annotations such as Bible reference links.

```bash
# Add verse-range links to every heading in a BSB PDF
PYTHONPATH=src python -m bsb_pdf_toolkit.add_route_links bsb-book-9.pdf bsb-linked.pdf

# Works on any BSB PDF, including combined or customized ones
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --input bsb-book-9.pdf --output temp.pdf --no-footnotes
PYTHONPATH=src python -m bsb_pdf_toolkit.add_route_links temp.pdf final.pdf
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

**⚠️ Warning:** PDF is a fixed-layout format. The font changer preserves the original line breaks and baselines, but Lexend has different metrics from Cambria.

```bash
# Convert to Lexend (requires fonts in ./fonts/ directory)
PYTHONPATH=src python -m bsb_pdf_toolkit.change_font input.pdf output.pdf

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
PYTHONPATH=src python -m bsb_pdf_toolkit.add_route_links bsb-book-9.pdf bsb-linked.pdf

# 2. Then change font while preserving existing URI annotations
PYTHONPATH=src python -m bsb_pdf_toolkit.change_font bsb-linked.pdf bsb-lexend.pdf
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
| ... | (full list in `PYTHONPATH=src python -m bsb_pdf_toolkit.download_bsb --list`) | | | | |

## Examples

```bash
# Personal study Bible — larger font, no footnotes
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --input bsb-book-9.pdf --output study-bible.pdf \
    --font-size 12 --margin 48 --no-footnotes

# Combine multiple books into one PDF
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --books 1,2,3 --output pentateuch.pdf

# Extract just a chapter range (pages 100–200)
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --input bsb-book-9.pdf --range 100-200 \
    --output 1sam-ch7-15.pdf

# Generate a grayscale pocket edition
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_bsb --input bsb-book-9.pdf --output pocket.pdf \
    --page-size 5x8 --grayscale --font-size 9

# EPUB: Lexend font + route.bible links
PYTHONPATH=src python -m bsb_pdf_toolkit.customize_epub bsb.epub bsb-lexend.epub \
    --font-dir fonts/ --add-links
```

## License

BSB text is public domain. This toolkit is MIT licensed.
