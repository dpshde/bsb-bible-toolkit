# BSB Travel Edition — Typesetting Spec

A compact print specification for a pocket/travel Berean Standard Bible.
This sheet is written so a human typesetter could recreate the book without
reading the generator. The first composed artifact is **John only**.

Engine: Typst (paragraph composer, `linebreaks: "optimized"`).
Not WeasyPrint, paged.js, or browser print CSS.

Text source: this toolkit’s official BSB USFM
(`drafts/primary/source/engbsb_usfm.zip`, from
<https://bereanbible.com/bsb_usfm.zip>). Do not introduce a second Bible corpus.

## 1. Page

| Item | Value |
|------|-------|
| Trim | 4.75 in × 7.00 in (portrait) |
| Binding | Two-sided; inside/outside margins swap on verso/recto |
| Inside (gutter) | 0.55 in |
| Outside | 0.40 in |
| Head | 0.50 in |
| Foot | 0.375 in |
| Measure | 3.80 in (32.2 em at 8.5 pt) |
| Text-block height | 6.125 in |
| Lines per page | 42 |
| Baseline grid | 10.5 pt, shared by verso and recto |

Head + foot + 42 × 10.5 pt = 0.50 in + 0.375 in + 6.125 in = 7.00 in.
Every body, heading, and xref interval is an integer multiple of 10.5 pt so
facing pages line-match.

Target characters per line: **60–70**. At 8.5 pt Text optical, 3.80 in is
about 32 em ≈ 65–70 English characters. If a later proof runs outside 60–70,
change measure or size — do not jump to a 6×9 10 pt desk spec.

## 2. Type

| Role | Face | Size / leading |
|------|------|----------------|
| Body | FF Milo Serif **Text** (optical), roman | 8.5 / 10.5 pt |
| Words of Christ | Same Text face, `rgb(28, 56, 110)` | 8.5 / 10.5 pt |
| Body italic | FF Milo Serif **Text Italic** | 8.5 / 10.5 pt |
| Section heads | FF Milo Serif Regular or Bold | 8.5 pt on the grid |
| Running heads, folios | FF Milo Serif Regular | 7 pt in the head/foot |
| Verse numbers | FF Milo Serif Regular/Bold | 6 pt, superscripted, ink |
| Chapter drop numeral | FF Milo Serif Regular/Bold | ~15 pt inside the 3-line square |
| Footnotes | FF Milo Serif Text | 7 / 8.5 pt |

Use the **Text** optical size at 8.5 pt. Do not set Display, Regular-as-text,
or a caption cut at this size. Regular/Bold are for heads and the drop-cap
numeral only.

Named families the composer asks for:

- `"FF Milo Serif Text"` / `MiloSerif-Text`
- `"FF Milo Serif"` for heads

`text.fallback` is **false**. `--ignore-system-fonts` is passed at compile.
If the licensed desktop fonts are absent, the print target **fails** with:

> Place licensed desktop OTFs from FontFont/MyFonts here (Text + Text Italic
> minimum; Regular/Bold for heads). Desktop license, 1 workstation.

Do not substitute Source Serif, Lexend, or any other face.

Purchase/license: FontFont / MyFonts, desktop license, one workstation.
Designer: Mike Abbink. See <https://mikeabbink.com/typefaces/milo-serif/>.
Place files in `fonts/milo/` (gitignored). This repository does not ship the
font.

## 3. Composition

- Language `en`, hyphenation on.
- Justified body; Typst optimized paragraph line-breaks (whole-paragraph
  composer, not first-fit).
- Justification limits: word space 80–150%; tracking −0.005 em to +0.01 em
  to limit rivers without obvious letterspacing.
- Optical margin alignment: Typst `text.overhang: true` (hanging hyphen and
  punctuation into the margin when the engine supports it).
- Paragraph spacing equals line leading (2 pt gap + 8.5 pt line box = 10.5 pt
  baselineskip) so stacked paragraphs stay on the grid.
- No orphan of a verse number: the verse numeral is boxed with a thin space
  so it cannot sit alone at the end of a line.
- Widows/orphans of paragraph lines: Typst default costs (on).
- Poetry (`\q1`, `\q2`) indents by 0.14 in per level, still on the grid.
- The superscription `\pc` (e.g. the titulus) is a centered small-cap line.

## 4. Structure

- **Single column.**
- **Book opening:** small-cap “Berean Standard Bible”, then the USFM title
  (`\toc1` / `\mt1`, for John: *The Gospel According to John*).
- **Chapter drop cap:** original geometric construction — double-ruled square
  the height of 3 baselines (31.5 pt), hairline mid-edge ticks, chapter
  numeral centered. Sits on the grid beside verse 1. Not a decorated letter,
  not Humble Lamb drop-cap art, not Doré.
- **Section headings:** BSB `\s1` titles in the head face, one baseline above.
- **Chapter-start cross-references:** the first USFM `\r` block in a chapter
  is set as a 7 pt italic justified line under that opening heading. Later
  `\r` blocks stay with their section headings. If a chapter has no `\r`,
  none are invented.
- **Translator notes:** USFM `\f` → footnotes (letter markers). `\fqa`
  alternate readings in italic. Notes are not moved into the side margin.
- **Words of Christ:** USFM `\wj` … `\wj*` in the travel cobalt, same Text
  face. Verse numbers stay ink even when a speech wraps a `\v` marker.

## 5. Running matter

- Page 1 (title) has no header or folio.
- Running head, 7 pt small caps, outer: `JOHN · <chapter>` (book heading
  from USFM `\h`).
- Folio, 7 pt, centered in the foot.
- Folios and running heads live in the head/foot margins, not in the 42-line
  text block.

## 6. Color and ink

- Body ink: `rgb(20, 20, 20)` (near-black, not rich-black build-up).
- Words of Christ: `rgb(28, 56, 110)`. Print as a single spot or process
  match; do not use a red-letter palette.
- Rules in the drop cap: same ink, 0.28–0.45 pt.

## 7. What this spec is not

- Not Humble Lamb BSB Maker’s 6×9 desk size or 10 pt setting.
- Not a copy of Maker fonts, Doré illustrations, drop-cap artwork, or
  product assets.
- Not a whole-canon pagination yet. John is the proof of the travel grammar.

## 8. Rebuild

See `drafts/travel/README.md`. The machine command is `make travel-john`
(or `mise run travel-john`) after licensed Milo files are in `fonts/milo/`.
