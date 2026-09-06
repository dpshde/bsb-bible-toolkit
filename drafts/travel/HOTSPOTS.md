# Travel Bible grid-proof hotspot QA

Watermarked metrics PDF only. Stand-in face is Source Serif 4 (SIL OFL).
**Not** FF Milo Serif Text. Do not present this file as the loved face.

Compile: `make travel-bible-grid-proof`

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-bible-grid-proof.pdf` (gitignored; do not commit) |
| Engine | Typst 0.14.2 |
| Pages | 2299 |
| Bytes | 73,809,442 (~70.4 MiB) |
| SHA-256 | `c25c46e86d845840aac7abf08ab779b57bb1cc86938f53f0c44c83df5ad8cf19` |
| Wall time | 62.86 s |
| Peak RSS | ~10.3 GiB |
| Trim | 4.75 in × 7.00 in (342 × 504 pt) |
| Books | 66, Protestant canon order, `#pagebreak()` between books |

## Fixes from this QA pass

- Running heads on the first page of a book still showed the previous book (`MALACHI · 4` on Matthew, `JOHN · 21` on Acts, etc.). Headers now query a per-page `<run-head>` mark.
- Psalm 119 `\qa א` rendered as a missing-glyph box in the OFL stand-in. Hebrew-only acrostic lines are omitted; the Latin `ALEPH` / `BETH` labels remain.
- Translator-note letters ran into three-character markers (`cdh`, `gdp`) across the canon. The footnote counter now resets **on every page** (header) and still at each book pagebreak.

## Checks

| Check | Page | Result | Notes |
|-------|------|--------|-------|
| Genesis 1 title + drop cap 1 + first footnotes | 1 | Pass | Title page with sample line; drop 1; notes a–c at the foot; watermark + grid. |
| Exodus 20 / Decalogue | 130–131 | Pass | Drop 20 on 130; `\li1` commandments on 131 with hanging indent; 7 notes at the foot of 131. |
| Psalm 1 poetry indent | 960 | Pass | `q1`/`q2` indent; BOOK I + “Psalms 1–41”; drop 1. |
| Psalm 119 longest chapter; acrostic | 1118+ | Pass after fix | ALEPH + drop 119; later stanzas BETH/GIMEL; no tofu. |
| Selah | 962 (Ps 4) | Pass | `\qr Selah` as centered small-caps inscription. |
| Proverbs 1 poetry | 1157 | Pass | Compact book title (no repeating “sample”); `q1`/`q2` indent. |
| Isaiah 53 | 1369 | Pass | Poetry + drop 53; notes at the foot. |
| Matthew 1 genealogy | 1797 | Pass | Poetry genealogy; drop 1. USFM `\p Next:` is a one-word paragraph (source). |
| First WoC in Matthew | 1802 (Mt 3–4) | Pass | “Let it be so now” and temptation replies in `rgb(28,56,110)`. |
| John 1 (parity with John sample) | 1976 | Pass | Same grammar: title, drop 1, xrefs, footnotes, WOC unused in 1:1–18 (narration). |
| Obadiah | 1728 | Pass | Title + body on one opening page; not exploded. |
| Philemon | 2210–2211 | Pass | Compact opening; letter fits without a blank-title blow-up. |
| 2 John / 3 John / Jude | 2261 / 2263 / 2265 | Pass | Tiny books: title + body; last page of 2 John is sparse (vv. 12–13), not overflow. |
| Revelation 22 last page | 2299 | Pass | 22:18–21 present, including “The grace of the Lord Jesus be with all the saints. Amen.” |
| Heavy NT footnotes | 2256 (1 John 3) | Pass | Five notes at the foot; none dropped. Book-level reset keeps markers short in NT. |
| Malachi → Matthew | 1796 → 1797 | Pass after fix | Mal 4:6 on 1796; Matthew title on 1797 with `MATTHEW · 1` (not Malachi). |
| John → Acts | 2024 → 2025 | Pass after fix | John 21:25 on 2024; Acts title on 2025 with `ACTS · 1`. |
| Grid watermark | interior pages | Pass | `GRID PROOF — NOT FINAL FACE` on sampled pages. |
| Overflow / overlapping text | sampled hotspots | Pass | No text outside trim on inspected pages. |

## Footnote numbering (2026-09-02)

Letter markers reset at the start of each page via `counter(footnote).update(0)`
in the Typst page header (the documented Typst pattern). Book pagebreaks still
reset as a safety net.

John-only recompile (`--grid-proof --book John`, 49 pages): every sampled
footnote listing starts at `a`. Page 2 carries notes **a–f**; page 3 starts
again at **a**. No two-letter markers in the 49-page John PDF.

Psalms-only targeted compile (`--book Psalms`, 197 pages): same reset. Page 2
has **a–e**; page 3 starts at **a**. Zero two-letter markers across the book.

Do not treat two-letter markers inside a single page as a regression unless
that page has more than 26 notes.

## Facing spreads (John 2–3, 4–5, 10–11)

`make travel-john-spreads` recompiles the John grid-proof and writes a 2-up
QA sheet of three openings. Verso is left; recto is right; each leaf stays
4.75 × 7 in. Still watermarked `GRID PROOF — NOT FINAL FACE`. Not Milo.

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-john-grid-proof.pdf` |
| Spread PDF | `drafts/travel/bsb-travel-john-spreads-grid-proof.pdf` (3 pages, 70,080 bytes) |
| Spread SHA-256 | `8d3d1ff461f797d47a34bc228a8bcbb7ce85ac65ca067c164e6d0dfdd3114fb3` |
| PNGs | `drafts/travel/spreads/john-spread-02-03.png`, `john-spread-04-05.png`, `john-spread-10-11.png` (120 dpi) |
| Pairs | 2–3 (John 1), 4–5 (ch. 2 drop on 4, ch. 3 drop on 5), 10–11 (ch. 5 open on 10) |

### Verso/recto line-match

Body 8.5 pt spans sit on a shared 10.5 pt y lattice. Facing pages use the
same slot coordinates (phase Δ 0.0 pt). Shared body y-slots: **23** on 2–3,
**21** on 4–5, **25** on 10–11. Visual check of the three PNGs matches:
text lines meet across the gutter; drop-cap squares and footnotes do not
break the body grid.

Recompiled John PDF 2026-09-04 (Typst 0.14.2, current layout, not the
2026-09-01 file): 49 pages, 2,029,571 bytes, SHA-256
`0b005230c7fdaa30915078fee3ea115ba50a2d465302565808b1e34ca22ea82c`.
Page 2 notes **a–f**; page 3 starts at **a**. Spread PDF SHA-256
`8d3d1ff461f797d47a34bc228a8bcbb7ce85ac65ca067c164e6d0dfdd3114fb3`
(70,080 bytes). Facing PNGs are unchanged from the 2026-09-03 line-match
pass.

## Compact sampler (2026-09-06)

`make travel-hotspot-sampler` builds a committed multi-leaf PDF from a
targeted book compile (Genesis, Psalms, Obadiah, 1 John, Revelation) —
not the 2299-page file. Source Serif 4 stand-in. Watermark
`GRID PROOF — NOT FINAL FACE`. Not Milo.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-hotspot-sampler-grid-proof.pdf` |
| Regen | `make travel-hotspot-sampler` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-06 |
| Pages | 6 (native 4.75 × 7 in leaves) |
| Size | 86,279 bytes |
| SHA-256 | `a85c11a15610d4dce39c312dda6a6dc5461fab9f254de31f5be4087f827b6945` |
| Source compile | `drafts/travel/work/hotspot-books-grid-proof.pdf` (335 pages, gitignored) |
| PNGs | `drafts/travel/hotspots/*.png` (120 dpi) |

| Leaf | Source page | What to check |
|------|-------------|---------------|
| `genesis-1` | 1 | Title + boxed drop 1 + footnotes a–c |
| `psalm-1` | 96 | `q1`/`q2` indent; BOOK I; drop 1 |
| `psalm-119` | 254 | ALEPH Latin label + boxed drop 119; no Hebrew tofu |
| `obadiah` | 293 | Title + body on one opening; not exploded |
| `1-john-3` | 298 | Ch. 3 open + notes a–e; letters stay short |
| `revelation-22` | 335 | 22:18–21 including Amen |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `hotspots/genesis-1.png` | 104,081 | `bef78cd1dc51babe2d9188e9752682f44646bf923e7f90db540ed636c5f2cb41` |
| `hotspots/psalm-1.png` | 98,678 | `d82b83ce120c7e6c016cb8afb2eb95bc7c18b187db856ebb4b3d19e5744abdc9` |
| `hotspots/psalm-119.png` | 125,274 | `e28e73343403103e960068d5680e8c07e405ee0bc474ab53d2a2fd0dcc6444c2` |
| `hotspots/obadiah.png` | 102,471 | `62c224771c2e5d7544d827c6dcb52dcb303e01486a8c3aa39ccf130ae70305e5` |
| `hotspots/1-john-3.png` | 155,867 | `05e622507ce9b41b400fcf767cb61c33eed426c3ebe81425b99c14eb6145e613` |
| `hotspots/revelation-22.png` | 63,982 | `7229176492939b00306966188394730a5b7fb84348f25bc5db930de350e9563d` |

## Known leftovers (not chased)

- Loved-face Milo compile is unchanged and still fail-closed without `fonts/milo/`.
- Typst can fail to converge if a footnote sits exactly at a page break when the counter resets (upstream issue). If a compile warns, re-check that page; do not widen the page spec to paper over it.
