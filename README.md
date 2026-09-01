# BSB Bible PDF Toolkit

Generate custom PDFs and EPUBs from the Berean Standard Bible (BSB) source files.

## Mission

This project exists to help Christian technologists, designers, publishers, and
builders download, study, remix, and share Scripture resources in creative new
ways. The BSB text has been dedicated to the public domain, so the goal here is
to make practical tooling and example editions that encourage more people to
distribute Scripture freely.

This is an unofficial community toolkit. It is not affiliated with or endorsed
by the Berean Bible Translation Committee, Bible Hub, or the other BSB project
partners.

## Download and Share

If you only want the current generated Bible PDFs, download them directly:

| Edition | File |
|---------|------|
| Primary fixed-layout PDF | [`drafts/primary/bsb-primary-draft.pdf`](drafts/primary/bsb-primary-draft.pdf) |
| Single-column PDF | [`drafts/primary/bsb-single-column-draft.pdf`](drafts/primary/bsb-single-column-draft.pdf) |

If GitHub Releases are available for this repo, prefer the latest release for
versioned PDFs and SHA-256 checksums.

You are encouraged to copy, share, print, adapt, and build new Scripture tools
from these resources. Keep the BSB text verbatim if you use the Berean name; if
you make textual changes, present the result as your own derivative rather than
as an official Berean Bible text.

## Build Your Own Edition

```bash
# Create and activate an isolated environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Build the primary PDF draft from the official fixed-layout BSB PDF
python design_bsb.py
```

Commands use `python` for readability; use `python3` on systems where `python`
is not available.

After installing the package in editable mode, you can use the console commands
directly:

```bash
python -m pip install -e .
bsb-design --qa-only --verify
bsb-reflow-pdf drafts/primary/source/engbsb_usfm.zip my-single-column.pdf --font-dir fonts --columns 1
```

The current prototyping flow has one primary draft. It uses
`https://bereanbible.com/bsb-book-9.pdf` as the visual baseline, adds
route.bible annotations, then redraws the fixed layout with Lexend.

| Path | Purpose |
|------|---------|
| `design_bsb.py` | Single entry point for the draft workflow |
| `src/bsb_pdf_toolkit/` | Python package containing generators and utilities |
| `audio/` | BSB audio tooling: `production/` (ElevenLabs) and `local/` (Kokoro, Chatterbox MLX/torch) |
| `scripts/` | Compatibility shims and `scripts/pdf/` utilities |
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

### Travel print sample (John)

A compact **4.75 × 7 in** single-column sample of John, composed in Typst
from this toolkit’s BSB USFM. It follows a travel Bible spec (8.5 pt
FF Milo Serif **Text**, 10.5 pt baseline grid, footnotes, chapter-start
cross-references, words of Christ in blue). It is not Humble Lamb Maker’s
6×9 10 pt desk setting, and it does not copy Maker fonts, Doré art, or
drop-cap artwork.

How to build, the BSB license notice, and an explicit “what was not copied
from Humble Lamb” list: [`drafts/travel/README.md`](drafts/travel/README.md).
The typesetting spec a human typesetter can follow:
[`drafts/travel/SPEC.md`](drafts/travel/SPEC.md).

```bash
# Licensed FF Milo Serif Text + Text Italic must already be in fonts/milo/
make travel-john
# or: mise run travel-john
```

The loved-face print target fails closed if those fonts are missing. It will
not download Milo, and it will not silently substitute Source Serif or Lexend.

A separate metrics compile, watermarked `GRID PROOF — NOT FINAL FACE`, uses
the OFL stand-in in `fonts/grid-proof/`. That PDF is not the loved face.

```bash
make travel-john-typst          # markup only; no fonts required
make travel-john-grid-proof     # watermarked John OFL metrics PDF; not Milo
make travel-bible-grid-proof    # watermarked 66-book OFL metrics PDF; not Milo; do not commit
PYTHONPATH=src python -m bsb_pdf_toolkit.generate_travel_pdf --help
```

Common single-column tuning flags include `--single-margin-x`,
`--single-body-size`, `--single-body-leading`, `--single-book-title-font`,
`--single-dropcap-size`, `--single-dropcap-padding`,
`--single-dropcap-protected-lines`, `--single-verse-size`, and
`--single-verse-baseline-shift`.
The default book title face is `Lexend-Bold`.
Both PDF generators accept `--release-stage`; local builds default to `Draft`,
while the delivery workflow stamps packaged release copies with a semantic
version label such as `Version 0.0.1`.

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

## BSB JSON API

In addition to the PDF/EPUB tooling, this repo publishes a free, structured
**BSB JSON API** that serves the public-domain Berean Standard Bible over
HTTPS with no API key and no rate limit. The API is a Cloudflare Worker using
a 4-tier cache-aside pattern: edge cache, then an R2 bucket, then the Arweave
permanent origin (`api_bsb` undername on the `scripture` ArNS name), and
finally a 503 if every tier is exhausted. All Bible reference parsing is
delegated to `grab-bcv`.

| Endpoint | Example | Returns |
|----------|---------|---------|
| `GET /v1/books` | `/v1/books` | All 66 books with metadata |
| `GET /v1/book/:osis` | `/v1/book/GEN` | Full book JSON |
| `GET /v1/chapter/:osis/:ch` | `/v1/chapter/GEN/1` | Full chapter |
| `GET /v1/verse/:osisRef` | `/v1/verse/GEN.1.1` | Single verse with footnotes, cross-refs, events |
| `GET /v1/passage/:ref` | `/v1/passage/John%203:16-18` | Parsed range expanded to verses |
| `GET /v1/search?q=...` | `/v1/search?q=beginning` | Verses matching the query |
| `GET /v1/crossrefs/:osisRef` | `/v1/crossrefs/GEN.1.1` | Cross-references (with `?source=` filtering) |
| `GET /v1/health` | `/v1/health` | Service health, version, cache tier status |

Quick start:

```bash
# Local Worker on port 8787
cd api && npm install && npx wrangler dev --port 8787

# Fetch a verse
curl 'http://localhost:8787/v1/verse/JHN.3.16'

# Fetch a passage (URL-encode spaces)
curl 'http://localhost:8787/v1/passage/John%203:16-18'

# Filter cross-references by source (tsk, bsb-footnote, acai, theographic)
curl 'http://localhost:8787/v1/crossrefs/GEN.1.1?source=tsk'
```

The `/v1/` paths are frozen forever; schema changes go to `/v2/`. Responses are
CORS-enabled with `Cache-Control: public, max-age=31536000, immutable` and an
`X-Origin` header indicating which cache tier served the request (`edge`, `r2`,
or `arweave`).

See [`dataset/README.md`](dataset/README.md) for the full JSON schema, OSIS
reference format, source-filtering docs, and Python/JavaScript quickstarts.
Example consumers live in [`dataset/examples/`](dataset/examples/).

## How to Help

Ideas that fit this repo's mission:

- improve readable, printable BSB layouts;
- build web, mobile, EPUB, print, or study-tool experiments around the public-domain BSB;
- improve route.bible linking, OSIS indexing, and reader navigation;
- add clear documentation so churches, ministries, and developers can reuse the work;
- share examples of creative Scripture distribution projects inspired by this toolkit.

Please keep changes reproducible, document generated artifacts, and run the
structural verifier before proposing release-affecting changes.

## CI/CD Asset Delivery

This repo includes a GitHub Actions workflow at
`.github/workflows/deliver-assets.yml` that verifies the committed PDF
artifacts, stamps release copies as `Version`, and packages them with SHA-256
checksums. Manual dispatch runs can also upload the generated PDFs and checksums
to a GitHub Release, publish the variants to itch.io through Butler, and deploy
the web-reader bundle to Permaweb.

Configure these repository secrets before enabling manual delivery targets:

| Secret | Value |
|--------|-------|
| `BUTLER_API_KEY` | itch.io Butler API key, required only when publishing to itch.io |
| `DEPLOY_KEY` | Arweave upload wallet JWK, base64-encoded, required only for Permaweb deploys |
| `ARNS_KEY` | Solana key that controls the configured ArNS name, required only for Permaweb deploys |

The itch.io target is configured in the workflow as `ITCH_TARGET`.

The workflow publishes two Butler channels:

| Channel | Contents |
|---------|----------|
| `primary-fixed-layout-pdf` | `BSB - Primary Layout.pdf` |
| `single-column-pdf` | `BSB - Single Column.pdf` |

The workflow also uploads each variant as an individually downloadable GitHub
Actions artifact:

| Artifact prefix | Contents |
|-----------------|----------|
| `berean-standard-bible-primary-fixed-layout-pdf-` | Primary fixed-layout PDF package |
| `berean-standard-bible-single-column-pdf-` | Single-column PDF package |

When a manual run sets `dry_run` to false, the workflow creates or updates the
GitHub Release tagged `v<release_version>` and uploads:

| Release asset | Contents |
|---------------|----------|
| `BSB - Primary Layout.pdf` | Primary fixed-layout PDF |
| `BSB - Single Column.pdf` | Single-column PDF |
| `primary-fixed-layout-SHA256SUMS.txt` | Primary fixed-layout checksum |
| `single-column-SHA256SUMS.txt` | Single-column checksum |

Run it manually from GitHub Actions with the default `dry_run: true` to
verify/package without publishing. Set `dry_run: false` only when you are ready
to publish. The workflow defaults to version `0.0.1`; provide `release_version`
when dispatching manually to publish another semantic version.

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

The Berean Bible and Majority Bible texts were dedicated to the public domain
under CC0 on April 30, 2023. The official terms say all uses are freely
permitted; attribution is appreciated but not required. See
<https://berean.bible/terms.htm>.

Toolkit source code is MIT licensed; see [`LICENSE`](LICENSE). Bundled Lexend
font files are distributed under the SIL Open Font License 1.1; see
[`fonts/OFL.txt`](fonts/OFL.txt). Generated documents may embed the fonts under
the OFL, but the font files must not be sold by themselves. FF Milo Serif is
not bundled; the travel edition expects a desktop-licensed copy in
`fonts/milo/`. See [`fonts/milo/README.md`](fonts/milo/README.md).

Additional attribution and project notices are collected in [`NOTICE`](NOTICE).
