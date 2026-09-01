# Travel print sample (John)

Compact 4.75 × 7 in BSB sample, composed from **this toolkit’s** official
USFM — not a second Bible corpus, not a browser printout.

The typesetting spec a human could follow is [`SPEC.md`](SPEC.md).

## How to build

1. Install Typst 0.13+ (`mise install` if you use mise, or the official Typst installer).
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
baseline grid. The face is FF Milo Serif Text, licensed separately by the
workstation owner.

## Scope

John only. Whole-canon travel typesetting is later work. Audio/TTS pipelines
are untouched.
