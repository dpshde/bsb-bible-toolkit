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
compiled so trim, hyphenation, drop cap, WOC blue, and footnotes can
be checked digitally. The stand-in is Source Serif 4 (SIL OFL 1.1)
from `fonts/grid-proof/`. Interior pages keep a centered folio and do
not print `GRID PROOF — NOT FINAL FACE` or a ruled background. Footnotes
run in and sit in a lighter grey. The PDF outline is Book → Chapter.
It is never presented as FF Milo Serif Text.

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

## Hotspot sampler (committed, not the 66-book file)

`make travel-hotspot-sampler` compiles only Genesis, Psalms, Obadiah,
1 John, and Revelation, then extracts the QA leaves so Dylan can open
them without the ~70 MiB full-canon PDF. Still Source Serif 4. Not Milo.

```bash
make travel-hotspot-sampler
```

Output: `drafts/travel/bsb-travel-hotspot-sampler-grid-proof.pdf`
(6 leaves, 86,279 bytes, SHA-256
`a85c11a15610d4dce39c312dda6a6dc5461fab9f254de31f5be4087f827b6945`).
120 dpi PNG previews: `drafts/travel/hotspots/*.png`.
Intermediate compile (gitignored): `drafts/travel/work/hotspot-books-grid-proof.pdf`
(335 pages).

Leaf list and PNG hashes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Hyphenation QA

`make travel-hyphenation-qa` compiles Genesis, Psalms, and John with the
current travel hyphen settings, then extracts three stress leaves: a dense
John prose page, Psalm 119 poetry, and Genesis 1. Still Source Serif 4.
Not Milo.

```bash
make travel-hyphenation-qa
```

Output: `drafts/travel/bsb-travel-hyphenation-qa-grid-proof.pdf`
(3 leaves, 70,209 bytes, SHA-256
`49ffa72caf8532833de43b65ec7bb17067c752ecb3a40b51c8be9bd67d5b1f52`).
120 dpi PNG previews: `drafts/travel/hyphenation/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Poetry QA

`make travel-poetry-qa` compiles Genesis + Psalms and extracts Psalm 1 and
Psalm 119 ALEPH so verse lines can be checked after the ragged-right,
q1-on-measure / q2-step poetry change. Still Source Serif 4. Not Milo.

```bash
make travel-poetry-qa
```

Output: `drafts/travel/bsb-travel-poetry-qa-grid-proof.pdf`
(2 leaves, 48,582 bytes, SHA-256
`767ad2fe1ec6635a1534d60815cab9f93406f2af738d7a9fb38cb4fd3a4a8e13`).
120 dpi PNG previews: `drafts/travel/poetry/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Running-header QA

`make travel-running-headers-qa` compiles John and extracts four interior
leaves so verso/recto running heads can be checked after the
`JOHN · <chapter>:<first>–<last>` change. Still Source Serif 4. Not Milo.

```bash
make travel-running-headers-qa
```

Output: `drafts/travel/bsb-travel-running-headers-qa-grid-proof.pdf`
(4 leaves, 99,227 bytes, SHA-256
`d715f8419b393f4eac5007873f22437d184c977444f223e02502f9908a73e463`).
120 dpi PNG previews: `drafts/travel/headers/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Words of Christ blue QA

`make travel-woc-qa` compiles Matthew + John and extracts four interior
leaves so cobalt Words of Christ (`\wj` → `#woc`, `rgb(28, 56, 110)`)
can be checked. Still Source Serif 4. Not Milo.

```bash
make travel-woc-qa
```

Output: `drafts/travel/bsb-travel-woc-qa-grid-proof.pdf`
(4 leaves, 101,655 bytes, SHA-256
`32c268e297f0707626513b9fc81ae3d0a2797152350f7b8b3ccc1c1aaa066dcb`).
PDF outline: Matthew → 3, 4; John → 3, 14.
120 dpi PNG previews: `drafts/travel/woc/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

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
the workstation owner. The committed PDF in this folder is a Source Serif
metrics proof only.

## Current grid-proof artifact

This file is a **metrics proof**, not the loved-face print. Do not treat it
as FF Milo Serif Text. Notes run in as one wrapping paragraph in grey
`rgb(76, 76, 76)`; section titles take 1.5 baselines above and 0.5
below, wrapped with the following verse or chapter drop so they cannot
orphan. Book openers are the USFM title only. Body prose leading is
+0.65 pt, with a 0.35 in first-line indent and 0.75-baseline gap on later `\p` blocks.
There is no ruled background and no `GRID PROOF` / `NOT FINAL
FACE` footer string. The PDF outline is John → chapters 1–21.
Licensed FF Milo Serif Text is still missing from `fonts/milo/`.

| Item | Value |
|------|-------|
| File | `bsb-travel-john-grid-proof.pdf` |
| Label | none (centered folio only) |
| Stand-in | Source Serif 4 Regular/Italic/Bold (SIL OFL 1.1) |
| Loved face | FF Milo Serif Text (not in this PDF) |
| Source | `drafts/primary/source/engbsb_usfm.zip` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-11 |
| Trim | 4.75 in × 7.00 in |
| Pages | 48 |
| Links | 3263 |
| Size | 1,977,058 bytes |
| SHA-256 | `a7adcc9d9d568a8ab723b25db2741759d1cfe0a26712215b7b805471db0ad961` |

Re-hash after any recompile. The loved-face PDF is not committed until
licensed Milo OTFs are present.

## Full Protestant canon (grid proof only)

`make travel-bible-grid-proof` composes all 66 Protestant books in canonical
order at the same travel spec. Every book opener is the USFM title only —
no “Berean Standard Bible” line and no travel-sample metadata.
Loved-face Milo compile remains fail-closed without `fonts/milo/`.

This is still **not** the loved face. The stand-in is Source Serif 4.
A single 66-book Typst compile can run out of memory; the committed
preview is one book at a time, then merged, with continuous folios and
a Book → Chapter outline.

```bash
make travel-john-grid-proof     # John sample
make travel-bible-grid-proof    # 66-book metrics preview
```

Output: `drafts/travel/bsb-travel-bible-grid-proof.pdf`
(2,433 pages, 32,150,589 bytes, SHA-256
`43c389f0f0c5b08df9cde98dbe9f4fa877d3d6e7f44367f6020a86e7e5a50548`).
Per-book Typst/PDF intermediates stay in `drafts/travel/work/` (gitignored).

If a single compile runs out of memory, `make travel-bible-ot-grid-proof` and
`make travel-bible-nt-grid-proof` build the testaments separately.

Seeded random-page visual QA (16 leaves, seed `20260911`) lives in
[`qa-random/`](qa-random/). Older hotspot notes stay in
[`HOTSPOTS.md`](HOTSPOTS.md).
That note records page counts for a local compile; the PDF itself is not
committed.

## Scope

John sample **and** an optional 66-book grid-proof target. Audio/TTS pipelines
are untouched.
