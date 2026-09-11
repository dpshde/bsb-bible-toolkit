# Travel Bible grid-proof hotspot QA

Watermarked metrics PDF only. Stand-in face is Source Serif 4 (SIL OFL).
**Not** FF Milo Serif Text. Do not present this file as the loved face.

Compile: `make travel-bible-grid-proof`

Seeded 16-page visual QA (2026-09-11): [`qa-random/README.md`](qa-random/README.md)
(`make travel-random-qa`, seed `20260911`). Page numbers follow the 2,365-page
compile. `Next:` and `|OSIS` leaks are gone. Book titles and the Psalm 119
Lamp title have more air.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-bible-grid-proof.pdf` |
| Engine | Typst 0.14.2 (per-book compile + merge; one-shot canon OOMs here) |
| Pages | 2365 |
| Bytes | 31,625,618 (~30.2 MiB) |
| SHA-256 | `128fe796c1f5ff3eb574ab9490c8d933278cef47de190612134cced72341242b` |
| Trim | 4.75 in × 7.00 in (342 × 504 pt) |
| Books | 66, Protestant canon order |
| Outline | Book → Chapter (66 books, 1,189 chapter dests) |

## Fixes from this QA pass

- Running heads on the first page of a book still showed the previous book (`MALACHI · 4` on Matthew, `JOHN · 21` on Acts, etc.). Headers now query a per-page `<run-head>` mark.
- Psalm 119 `\qa א` rendered as a missing-glyph box in the OFL stand-in. Hebrew-only acrostic lines are omitted; the Latin `ALEPH` / `BETH` labels remain.
- Translator-note letters ran into three-character markers (`cdh`, `gdp`) across the canon. The footnote counter now resets **on every page** (header) and still at each book pagebreak.
- USFM `\p Next:` printed as body text in Matthew 1. Those source markers are dropped.
- Footnote *a* on Matthew 1 showed `1 Chronicles 2:9–10|1CH 2:9-10`. Display text now strips leftover `|OSIS` tails across the canon.
- “Your Word Is a Lamp to My Feet” sat crushed between Psalm 118:29 and ALEPH / drop 119. Pericope titles before a stanza letter + chapter drop now use `keep-with-break`.
- Book openers were tight against the running head and first section. Display titles now have two baselines of air above and below.

## Checks

| Check | Page | Result | Notes |
|-------|------|--------|-------|
| Genesis 1 title + drop cap 1 + first footnotes | 1 | Pass | Title page with sample line; drop 1; notes a–c at the foot. |
| Exodus 20 / Decalogue | 130–131 | Pass | Drop 20 on 130; `\li1` commandments on 131 with hanging indent; 7 notes at the foot of 131. |
| Psalm 1 poetry indent | 960 | Pass | `q1`/`q2` indent; BOOK I + “Psalms 1–41”; drop 1. |
| Psalm 119 longest chapter; acrostic | 1118+ | Pass after fix | ALEPH + drop 119; later stanzas BETH/GIMEL; no tofu. |
| Selah | 962 (Ps 4) | Pass | `\qr Selah` as centered small-caps inscription. |
| Proverbs 1 poetry | 1157 | Pass | Compact book title (no repeating “sample”); `q1`/`q2` indent. |
| Isaiah 53 | 1369 | Pass | Poetry + drop 53; notes at the foot. |
| Matthew 1 genealogy | 1836 | Pass after fix | Poetry genealogy; drop 1. `\p Next:` dropped; notes have no `|1CH` tail. |
| First WoC in Matthew | 1802 (Mt 3–4) | Pass | “Let it be so now” and temptation replies in `rgb(28,56,110)`. |
| John 1 (parity with John sample) | 1976 | Pass | Same grammar: title, drop 1, xrefs, footnotes, WOC unused in 1:1–18 (narration). |
| Obadiah | 1728 | Pass | Title + body on one opening page; not exploded. |
| Philemon | 2210–2211 | Pass | Compact opening; letter fits without a blank-title blow-up. |
| 2 John / 3 John / Jude | 2261 / 2263 / 2265 | Pass | Tiny books: title + body; last page of 2 John is sparse (vv. 12–13), not overflow. |
| Revelation 22 last page | 2299 | Pass | 22:18–21 present, including “The grace of the Lord Jesus be with all the saints. Amen.” |
| Heavy NT footnotes | 2256 (1 John 3) | Pass | Five notes at the foot; none dropped. Book-level reset keeps markers short in NT. |
| Malachi → Matthew | 1796 → 1797 | Pass after fix | Mal 4:6 on 1796; Matthew title on 1797 with `MATTHEW · 1` (not Malachi). |
| John → Acts | 2024 → 2025 | Pass after fix | John 21:25 on 2024; Acts title on 2025 with `ACTS · 1`. |
| Page chrome | interior pages | Pass | Centered folio only; no ruled background; no `GRID PROOF` / `NOT FINAL FACE`. |
| Overflow / overlapping text | sampled hotspots | Pass | No text outside trim on inspected pages. |

## Footnote numbering (2026-09-02)

Letter markers reset at the start of each page via `counter(footnote).update(0)`
in the Typst page header (the documented Typst pattern). Book pagebreaks still
reset as a safety net.

John-only recompile (`--grid-proof --book John`, 48 pages): every sampled
footnote listing starts at `a` and the notes on a page run in as one
wrapping paragraph. Page 2 carries notes **a–d**. No two-letter markers
in the 48-page John PDF.

Psalms-only targeted compile (`--book Psalms`, 197 pages): same reset. Page 2
has **a–e**; page 3 starts at **a**. Zero two-letter markers across the book.

Do not treat two-letter markers inside a single page as a regression unless
that page has more than 26 notes.

## Facing spreads (John 2–3, 4–5, 10–11)

`make travel-john-spreads` recompiles the John grid-proof and writes a 2-up
QA sheet of three openings. Verso is left; recto is right; each leaf stays
4.75 × 7 in. Source Serif 4 stand-in. Not Milo.

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

Recompiled John PDF 2026-09-11 (Typst 0.14.2, run-in grey notes, Book →
Chapter PDF outline, 1.5 / 0.5 baseline section air, keep-with heads,
+0.35 pt body leading, no ruled background, no footer watermark):
48 pages, 1,977,058 bytes, SHA-256
`a7adcc9d9d568a8ab723b25db2741759d1cfe0a26712215b7b805471db0ad961`.
Page 2 notes **a–d** run in as one wrapping paragraph. Outline is
`John` → `1`…`21`. The 2-up spread PDF above is the earlier line-match
sheet and was not rebuilt in this pass.

## Words of Christ blue QA (2026-09-11)

`make travel-woc-qa` compiles Matthew + John and extracts four native
4.75 × 7 leaves that carry spoken-Christ text. USFM `\wj` still becomes
`#woc` in cobalt `rgb(28, 56, 110)`. Source Serif 4 stand-in. Not Milo.
Run-in footnotes in grey `rgb(76, 76, 76)`, no ruled background, no
`GRID PROOF` / `NOT FINAL FACE`. PDF outline: Matthew → 3, 4; John → 3, 14.

Baptism and temptation are distinct leaves again. John 14 keeps the
pericope title with drop 14 and with “The Way, the Truth, and the Life”.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-woc-qa-grid-proof.pdf` |
| Regen | `make travel-woc-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-11 |
| Pages | 4 (native 4.75 × 7 in leaves) |
| Size | 101,655 bytes |
| SHA-256 | `32c268e297f0707626513b9fc81ae3d0a2797152350f7b8b3ccc1c1aaa066dcb` |
| Source compile | `drafts/travel/work/woc-books-grid-proof.pdf` (gitignored) |
| PNGs | `drafts/travel/woc/*.png` (120 dpi) |

| Leaf | Source page | Header | What to check |
|------|-------------|--------|---------------|
| `matthew-baptism` | 5 | `MATTHEW · 3:1–16` | “Let it be so now”; notes wrap |
| `matthew-temptation` | 6 | `MATTHEW · 3:17–4:15` | “Man shall not live on bread alone”; boxed drop 4 |
| `john-loved` | 73 | `JOHN · 3:15–34` | 3:16–17 speech in cobalt; notes wrap |
| `john-farewell` | 100 | `JOHN · 13:36–14:13` | Title + drop 14 + “The Way, the Truth, and the Life” stay with their verses |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `woc/matthew-baptism.png` | 154,196 | `e5d46eb06070834d1c282725bd7433e629cc9e0ca27f834beea411e985851e53` |
| `woc/matthew-temptation.png` | 138,947 | `83db73c88c3510d8708b7cc9af250b08073499387b4c49cb5edf5c028c7276cc` |
| `woc/john-loved.png` | 160,193 | `64cde80e4bff605cb4146775e6cc8441e9d3dc4cf573da8aae92f8b7dfdbaa1f` |
| `woc/john-farewell.png` | 158,925 | `bad1eba8ce19b4167e95241b3a66f95863480981da405f2b791e9263c77fd084` |

## Running-header QA (2026-09-09)

`make travel-running-headers-qa` compiles John and extracts four interior
leaves. Running heads now carry the page’s verse range:
`JOHN · 4:17–38`, or `JOHN · 3:31–4:2` when a leaf crosses chapters.
Page 1 still has no header. Verso left / recto right. Heads stay in the
0.50 in head margin, not the 42-line text block. Source Serif 4 stand-in.
Not Milo.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-running-headers-qa-grid-proof.pdf` |
| Regen | `make travel-running-headers-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-09 |
| Pages | 4 (native 4.75 × 7 in leaves) |
| Size | 99,227 bytes |
| SHA-256 | `d715f8419b393f4eac5007873f22437d184c977444f223e02502f9908a73e463` |
| PNGs | `drafts/travel/headers/*.png` (120 dpi) |

| Leaf | Source page | Header | What to check |
|------|-------------|--------|---------------|
| `john-p02` | 2 | `JOHN · 1:14–28` | Verso (even): left-aligned verse range |
| `john-p03` | 3 | `JOHN · 1:29–46` | Recto (odd): right-aligned verse range |
| `john-p06` | 6 | `JOHN · 3:8–26` | Mid-book Nicodemus leaf; range follows the page |
| `john-p10` | 10 | `JOHN · 4:53–5:15` | Cross-chapter span; boxed drop 5; still in the head margin |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `headers/john-p02.png` | 148,898 | `8c776df2a053370e4006f3d9b5a03a8efc76896f267f029a1b2cf40be6ea2f0f` |
| `headers/john-p03.png` | 169,626 | `6909dcfb870db43f86d392adb9a2385e9d071afedf0a4f83ee87a1b0cf3fdb88` |
| `headers/john-p06.png` | 163,871 | `404f8a107a5e782547652ec8a2539e3fe2f307b9ca66cfbfb99ed740705af8e1` |
| `headers/john-p10.png` | 160,243 | `84ed427d6786d0368da48e31a0d47667f5772dbb3e80cf145acf2a7d4511360c` |

## Poetry QA (2026-09-08)

`make travel-poetry-qa` compiles Genesis + Psalms and extracts Psalm 1 and
Psalm 119 ALEPH. Verse lines (`#poetry`) are **ragged-right**; `\q1` sits
on the measure and `\q2` steps 0.18 in. Body prose stays justified. `\b`
stanza pauses stay one extra baseline (21 pt) on the grid.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-poetry-qa-grid-proof.pdf` |
| Regen | `make travel-poetry-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-08 |
| Pages | 2 (native 4.75 × 7 in leaves) |
| Size | 48,582 bytes |
| SHA-256 | `767ad2fe1ec6635a1534d60815cab9f93406f2af738d7a9fb38cb4fd3a4a8e13` |
| PNGs | `drafts/travel/poetry/*.png` (120 dpi) |

| Leaf | Source page | What to check |
|------|-------------|---------------|
| `psalm-1` | 96 | q1 on the measure; q2 +0.18 in; `\b` gaps after vv. 3 and 5 |
| `psalm-119` | 254 | ALEPH couplets with the same step; no Hebrew tofu |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `poetry/psalm-1.png` | 97,747 | `cb47ce7d6c06a8c3bb9a06f38f2b49cd1703ed3149ec41e65769294bacbf455b` |
| `poetry/psalm-119.png` | 125,567 | `b5042777cd9f120fb6f6c41cde3888c607773956cd1f1cae6d0859c70961d181` |

## Hyphenation QA (2026-09-07)

`make travel-hyphenation-qa` compiles Genesis + Psalms + John and extracts
three stress leaves. The travel preamble now uses `lang: "en"`,
`hyphenate: true`, and hyphenation cost **80%** (was 120%). USFM `\nd`
divine names render as `#divine` (`hyphenate: false` + smallcaps).

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-hyphenation-qa-grid-proof.pdf` |
| Regen | `make travel-hyphenation-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-07 |
| Pages | 3 (native 4.75 × 7 in leaves) |
| Size | 70,209 bytes |
| SHA-256 | `49ffa72caf8532833de43b65ec7bb17067c752ecb3a40b51c8be9bd67d5b1f52` |
| PNGs | `drafts/travel/hyphenation/*.png` (120 dpi) |

| Leaf | Source page | Hyphen breaks | What to check |
|------|-------------|---------------|---------------|
| `john-prose` | 300 (John 4) | 2 | `salva-` / `speak-` in dense Samaritan-woman prose |
| `psalm-119` | 254 | 0 | Poetry + ALEPH; no tofu; LORD unhyphenated |
| `genesis-1` | 1 | 0 | Title/drop open; early notes |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `hyphenation/john-prose.png` | 176,428 | `96a95c9613121d9fac7f0e127fc9ad84686cbd34e0ad270c97b19ce62fe53ac0` |
| `hyphenation/psalm-119.png` | 125,274 | `e28e73343403103e960068d5680e8c07e405ee0bc474ab53d2a2fd0dcc6444c2` |
| `hyphenation/genesis-1.png` | 104,081 | `bef78cd1dc51babe2d9188e9752682f44646bf923e7f90db540ed636c5f2cb41` |

John-only probe at the old 120% cost had **2** line-end hyphens in 49 pages;
80% yields about **11**. 50% jumped to 34 and started chopping short stems
(`bap-`, `tes-`). 80% is the travel setting.

## Compact sampler (2026-09-06)

`make travel-hotspot-sampler` builds a committed multi-leaf PDF from a
targeted book compile (Genesis, Psalms, Obadiah, 1 John, Revelation) —
not the 2299-page file. Source Serif 4 stand-in. Not Milo.

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
