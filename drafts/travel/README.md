# Travel print sample (John)

Compact 4.75 × 7 in BSB sample, composed from **this toolkit’s** official
USFM — not a second Bible corpus, not a browser printout.

The typesetting spec a human could follow is [`SPEC.md`](SPEC.md).

## How to build

1. Install Typst 0.14+ (`mise install` if you use mise, or the official Typst installer).
   `par.justification-limits` needs 0.14; 0.13.1 will not compile this sample.
2. Place **licensed** FF Milo Serif desktop OTFs in `fonts/milo/`. See
   [`fonts/milo/README.md`](../../fonts/milo/README.md). The print target
   will not download or substitute a face.
3. Ensure the official BSB USFM archive is present (same file the rest of
   this toolkit already uses):

```bash
mkdir -p drafts/primary/source
curl -L -o drafts/primary/source/engbsb_usfm.zip https://bereanbible.com/bsb_usfm.zip
```

4. Compose John:

```bash
make travel-john
# or
mise run travel-john
# or
PYTHONPATH=src python -m bsb_pdf_toolkit.generate_travel_pdf \
  drafts/primary/source/engbsb_usfm.zip \
  drafts/travel/bsb-travel-john.pdf \
  --font-dir fonts/milo
```

Output: `drafts/travel/bsb-travel-john.pdf`.
Typst source (always written): `drafts/travel/work/john.typ`.

To inspect markup without fonts:

```bash
make travel-john-typst
```

Without Milo Text + Text Italic, `make travel-john` **fails** with:

> Place licensed desktop OTFs from FontFont/MyFonts here (Text + Text Italic
> minimum; Regular/Bold for heads). Desktop license, 1 workstation.

It will not fall back to Source Serif, Lexend, or system fonts
(`--ignore-system-fonts`, `text.fallback: false`).

## Grid proof (not the loved face)

If Milo is not on the workstation, a **metrics-only** PDF can still be
compiled so trim, grid, hyphenation, drop cap, WOC blue, and footnotes can
be checked digitally. Every page is watermarked
`GRID PROOF — NOT FINAL FACE`. The stand-in is Source Serif 4 (SIL OFL 1.1)
from `fonts/grid-proof/`. It is never presented as FF Milo Serif Text.

```bash
make travel-john-grid-proof
```

Output: `drafts/travel/bsb-travel-john-grid-proof.pdf`.
Typst source: `drafts/travel/work/john-grid-proof.typ`.

Facing-page QA for John openings 2–3, 4–5, and the chapter-5 open at 10–11:

```bash
make travel-john-spreads
```

That recompiles the John grid-proof, then writes a 2-up PDF
(`bsb-travel-john-spreads-grid-proof.pdf`) and 120 dpi PNGs under
`spreads/`. Verso is left; recto is right; each leaf stays 4.75 × 7 in.
Still not the loved face. Line-match notes live in [`HOTSPOTS.md`](HOTSPOTS.md).

## BSB license

The Berean Standard Bible text is public domain / CC0 (dedicated 30 April
2023). Official terms: <https://berean.bible/terms.htm>.

This sample keeps the BSB text verbatim from `engbsb_usfm.zip`. It is a
BSB-based resource, not an official Berean Bible project product.

## What was not copied from Humble Lamb

This edition is **inspired by** Humble Lamb BSB Maker’s *reading grammar*
(single column, chapter drop, notes as footnotes, chapter-start parallels,
words of Christ in blue). It does **not** copy:

- Humble Lamb / Maker fonts, including any retail or subsetted face
- Doré (or any other) illustration program
- Maker drop-cap artwork or engraved initials
- 6×9 desk trim or ~10 pt desk type
- Product photography, covers, branding, or marketing assets
- Pagination, line breaks, or ornament from a Maker PDF

The drop cap here is an original geometric double-ruled square on the
baseline grid. The loved face is FF Milo Serif Text, licensed separately by
the workstation owner. The committed PDF in this folder is a watermarked
grid proof only.

## Current grid-proof artifact

This file is a **metrics proof**, not the loved-face print. Do not treat it
as FF Milo Serif Text.

| Item | Value |
|------|-------|
| File | `bsb-travel-john-grid-proof.pdf` |
| Label | `GRID PROOF — NOT FINAL FACE` |
| Stand-in | Source Serif 4 Regular/Italic/Bold (SIL OFL 1.1) |
| Loved face | FF Milo Serif Text (not in this PDF) |
| Source | `drafts/primary/source/engbsb_usfm.zip` |
| Engine | Typst 0.14.2 |
| Trim | 4.75 in × 7.00 in |
| Pages | 49 |
| Links | 3372 |
| Size | 2,033,576 bytes |
| SHA-256 | `5db8eedc02e68394b11c3971336f1ddeb3a93f397f0f1c57329e088252b5fdc7` |

Re-hash after any recompile. The loved-face PDF is not committed until
licensed Milo OTFs are present.

## Full Protestant canon (grid proof only)

`make travel-bible-grid-proof` composes all 66 Protestant books in canonical
order at the same travel spec. Later books get a compact book title — the
“Travel print sample · 4.75 × 7 in” line stays on the first book only
(Genesis). Loved-face Milo compile remains fail-closed without `fonts/milo/`.

This is still **not** the loved face. The stand-in is Source Serif 4, watermarked
`GRID PROOF — NOT FINAL FACE` on every page. Do not commit the full-Bible PDF
(it will be thousands of pages). John-only targets are unchanged:

```bash
make travel-john-grid-proof     # John sample; may be committed
make travel-bible-grid-proof    # 66-book metrics PDF; do not git-add
```

Output: `drafts/travel/bsb-travel-bible-grid-proof.pdf` (gitignored).
Typst source: `drafts/travel/work/bible-grid-proof.typ` (gitignored).

If a single compile runs out of memory, `make travel-bible-ot-grid-proof` and
`make travel-bible-nt-grid-proof` build the testaments separately.

Raster QA of typesetting hotspots (Genesis 1, Exodus 20, Psalms, Matthew,
John → Acts, Revelation 22, tiny books) lives in [`HOTSPOTS.md`](HOTSPOTS.md).
That note records page counts for a local compile; the PDF itself is not
committed.

## Scope

John sample **and** an optional 66-book grid-proof target. Audio/TTS pipelines
are untouched.
