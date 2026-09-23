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

## Mixam John dummy (saddle-stitch)

A John-only 4.75 × 7 in booklet padded to **52 pages** for a Mixam
saddle-stitch color dummy (50 lb uncoated). It copies the committed John
grid-proof and appends blank end leaves — it does not recompile, so the
typeset stays identical to `bsb-travel-john-grid-proof.pdf`. Same Source
Serif 4 stand-in: no ruled background, no `NOT FINAL FACE` footer, WOC
blue kept. Extra leaves are blank, not filler text. Not Milo.

```bash
make travel-john-mixam
# or
mise run travel-john-mixam
# or
PYTHONPATH=src python -m bsb_pdf_toolkit.generate_travel_pdf \
  drafts/primary/source/engbsb_usfm.zip \
  drafts/travel/bsb-travel-john-mixam-dummy.pdf \
  --pad-source drafts/travel/bsb-travel-john-grid-proof.pdf \
  --pad-pages 52
```

To rebuild the John typeset first: `make travel-john-grid-proof && make travel-john-mixam`.

Output: `drafts/travel/bsb-travel-john-mixam-dummy.pdf`.

| Item | Value |
|------|-------|
| File | `bsb-travel-john-mixam-dummy.pdf` |
| Stand-in | Source Serif 4 Regular/Italic/Bold (SIL OFL 1.1) |
| Source | committed `bsb-travel-john-grid-proof.pdf` plus 2 blank end leaves |
| Trim | 4.75 in × 7.00 in |
| Pages | 52 (50 text + 2 blank) |
| Links | 3438 |
| Size | 892,357 bytes |
| SHA-256 | `803ed3e465764a496c90a464886fd7342ae650fa73d89a25628e91c322ea7bfc` |
| Mixam | saddle-stitch color dummy; WOC `rgb(28, 56, 110)` preserved |

Facing-page QA from the committed densified John grid-proof (50 pages).
Pairs: 2–3 early prose, 6–7 WOC (John 3), 18–19 later-`\p` dialogue,
24–25 mid-book drop 10.

```bash
make travel-john-spreads
```

That composes a 2-up PDF (`bsb-travel-john-facing-spreads-densified.pdf`)
from the committed John grid-proof — it does not recompile — and writes
120 dpi PNGs under [`qa-john/`](qa-john/). Verso is left; recto is right;
each leaf stays 4.75 × 7 in. Still not the loved face. Line-match notes
live in [`HOTSPOTS.md`](HOTSPOTS.md). To rebuild the typeset first:
`make travel-john-grid-proof && make travel-john-spreads`.

## John chapter-opener QA (densified)

`make travel-john-chapter-openers` crops every John chapter start
(chs 1–21) from the committed 50-page grid-proof. Mid-page opens crop
around the drop, not the physical page top, so a top-half leaf still
shows heading + drop + first lines. 120 dpi PNGs and a 21-page crop PDF
land in [`qa-john/`](qa-john/). Does not recompile. Not Milo.

```bash
make travel-john-chapter-openers
```

Output: `drafts/travel/qa-john/bsb-travel-john-chapter-openers.pdf` and
`qa-john/john-ch01-opener.png` … `john-ch21-opener.png`.

## Hotspot sampler (committed, not the 66-book file)

`make travel-hotspot-sampler` compiles only Genesis, Psalms, Obadiah,
1 John, and Revelation, then extracts the QA leaves so Dylan can open
them without the ~70 MiB full-canon PDF. Still Source Serif 4. Not Milo.

```bash
make travel-hotspot-sampler
```

Output: `drafts/travel/bsb-travel-hotspot-sampler-grid-proof.pdf`
(6 leaves, 93,370 bytes, SHA-256
`a37cb173e6458e5aa5a04a178ef98981c576463021c93631bc2f150141fab808`).
120 dpi PNG previews: `drafts/travel/hotspots/*.png`.
Intermediate compile (gitignored): `drafts/travel/work/hotspot-books-grid-proof.pdf`
(335 pages).

Leaf list and PNG hashes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Hyphenation QA

`make travel-hyphenation-qa` compiles Genesis, Psalms, and John on the
current densify compose, then extracts three stress leaves: a dense
John prose page, Psalm 119 poetry, and Genesis 1. Still Source Serif 4.
Not Milo.

```bash
make travel-hyphenation-qa
```

Output: `drafts/travel/bsb-travel-hyphenation-qa-grid-proof.pdf`
(3 leaves, 73,684 bytes, SHA-256
`faeb10afcb46fdd4eb97ae7626799a56d3ad9460ccda919f1d884a2680cfda9a`).
120 dpi PNG previews: `drafts/travel/hyphenation/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Poetry QA

`make travel-poetry-qa` compiles Genesis + Psalms on the current densify
compose and extracts Psalm 1 and Psalm 119 ALEPH leaves so SPEC §3
ragged-right poetry (q1 on measure, q2 +0.18 in, `\b` stanza blanks)
can be checked without the 66-book PDF. Still Source Serif 4. Not Milo.

```bash
make travel-poetry-qa
```

Output: `drafts/travel/bsb-travel-poetry-qa-grid-proof.pdf`
(2 leaves, 46,103 bytes, SHA-256
`8e115eff65a1ec673b7ec1c0b9aba69138170d1cd0446dd2bb71e68aa259ba94`).
120 dpi PNG previews: `drafts/travel/poetry/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Running-header QA

`make travel-running-headers-qa` compiles John on the current densify
compose and extracts four native leaves so SPEC §5 running matter can
be checked: title (no chrome), verso left / recto right, same-chapter
`JOHN · 1:16–33`, and cross-chapter `JOHN · 1:50–2:15`. Still Source
Serif 4. Not Milo.

```bash
make travel-running-headers-qa
```

Output: `drafts/travel/bsb-travel-running-headers-qa-grid-proof.pdf`
(4 leaves, 92,538 bytes, SHA-256
`ebe49aed3abc6e5dc76c1e9ea89f0c00223f12275250add9f38e3804094bd5ed`).
120 dpi PNG previews: `drafts/travel/headers/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Footnotes QA

`make travel-footnotes-qa` compiles John on the current densify compose
and extracts three native leaves so SPEC §4 translator notes can be
checked: alphabetic markers, per-page reset to `a`, run-in grey notes
at the foot, in-text body letters, and `\fqa` italic. Still Source
Serif 4. Not Milo.

```bash
make travel-footnotes-qa
```

Output: `drafts/travel/bsb-travel-footnotes-qa-grid-proof.pdf`
(3 leaves, 78,453 bytes, SHA-256
`a213788d5693f6ac83bc74dac0fcfe24447ce365bece076bd5e8c6f4850f06f6`).
120 dpi PNG previews: `drafts/travel/footnotes/*.png`.
Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

## Words of Christ blue QA

`make travel-woc-qa` compiles Matthew + John on the current densify
compose and extracts four interior leaves so cobalt Words of Christ
(`\wj` → `#woc`, `rgb(28, 56, 110)`) can be checked. Still Source Serif
4. Not Milo.

```bash
make travel-woc-qa
```

Output: `drafts/travel/bsb-travel-woc-qa-grid-proof.pdf`
(4 leaves, 98,012 bytes, SHA-256
`d57cb175f4cebfe551d1f93072decfca95f6035de2bc42376829c59fd29810ee`).
PDF outline: Matthew → 4, 5; John → 3, 14.
Densify pagination puts baptism + temptation on one leaf, so the second
Matthew leaf is the Beatitudes. 120 dpi PNG previews:
`drafts/travel/woc/*.png`. Hashes and leaf notes: [`HOTSPOTS.md`](HOTSPOTS.md).

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
−1.0 pt (recovering the 3.50 in densify page count). Later `\p` takes
a 0.35 in first-line indent; long later `\p` (4+ verses) also take a
0.75-baseline gap. Short dialogue later `\p` keep the indent only —
0.75 baseline on every one of John’s ~510 `\p` marks was the 48 → 62
page blowup. There is no ruled background and no `GRID PROOF` / `NOT FINAL
FACE` footer string. The PDF outline is John → chapters 1–21.
Licensed FF Milo Serif Text is still missing from `fonts/milo/`.

John QA leaves (opener / later-`\p` indent / WOC blue), densified
facing-spread PNGs, and chapter-opener crops live in [`qa-john/`](qa-john/).

| Item | Value |
|------|-------|
| File | `bsb-travel-john-grid-proof.pdf` |
| Label | none (centered folio only) |
| Stand-in | Source Serif 4 Regular/Italic/Bold (SIL OFL 1.1) |
| Loved face | FF Milo Serif Text (not in this PDF) |
| Source | `drafts/primary/source/engbsb_usfm.zip` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-13 |
| Trim | 4.75 in × 7.00 in |
| Pages | 50 |
| Links | 3438 |
| Size | 2,043,507 bytes |
| SHA-256 | `181c4e42f6797d13288518fba389deb63fa53e4862da1d9ebb16809423178494` |

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
(2,327 pages, 32,004,542 bytes, 113,662 links, SHA-256
`14d7b0b56eaa433fe60e19e1edee499695e107ddf9612ca16d6a6ce7f42332d9`).
John inside this file is pages **1997–2046** (50 pages), matching the
standalone densified John grid-proof. Per-book Typst/PDF intermediates
stay in `drafts/travel/work/` (gitignored).

If a single compile runs out of memory, `make travel-bible-ot-grid-proof` and
`make travel-bible-nt-grid-proof` build the testaments separately.

Seeded random-page visual QA (16 leaves, seed `20260911`) plus the
Genesis 16 / mid-John WOC / Psalm 119 / Matthew 1 glance pack live in
[`qa-random/`](qa-random/). Older hotspot notes stay in
[`HOTSPOTS.md`](HOTSPOTS.md).

## Scope

John sample **and** an optional 66-book grid-proof target. Audio/TTS pipelines
are untouched.
