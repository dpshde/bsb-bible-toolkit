# Travel Bible grid-proof hotspot QA

Metrics PDF only (no ruled background, no `GRID PROOF` / `NOT FINAL FACE`).
Stand-in face is Source Serif 4 (SIL OFL). **Not** FF Milo Serif Text.
Do not present this file as the loved face.

Compile: `make travel-bible-grid-proof`

Recompiled 2026-09-16 on the John-fixed densify compose (0.35 in later-`\p`
`#h` indent; 0.75-baseline brick gap only on long later `\p` of 4+ verses;
body leading −1.0 pt). John inside the canon is 50 pages (1997–2046),
matching the standalone John grid-proof. Seeded 16-page visual QA and the
four glance leaves: [`qa-random/README.md`](qa-random/README.md)
(`make travel-random-qa`, seed `20260911`). Older sample page numbers below
follow earlier compiles. `Next:` and `|OSIS` leaks stay gone.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-bible-grid-proof.pdf` |
| Engine | Typst 0.14.2 (per-book compile + merge; one-shot canon OOMs here) |
| Pages | 2327 |
| Bytes | 32,004,542 (~30.5 MiB) |
| SHA-256 | `14d7b0b56eaa433fe60e19e1edee499695e107ddf9612ca16d6a6ce7f42332d9` |
| John | pages 1997–2046 (50) |
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
- Genesis 16 narrative read as a wall of text. Later `\p` blocks now take a **0.35 in** first-line indent (`#h`, because Typst `first-line-indent` does not apply inside one-shot `#para` blocks), **0.75 baseline** extra space above, and a **3.50 in** measure (~58–62 cpl). Flush only immediately under a chapter drop and on USFM `\m`. Poetry and lists stay unindented. Single column kept.

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

## Facing spreads (densified John, 2026-09-14)

`make travel-john-spreads` composes a 2-up QA sheet from the committed
densified John grid-proof (50 pages). It does not recompile. Verso is
left; recto is right; each leaf stays 4.75 × 7 in. Source Serif 4
stand-in. Not Milo.

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-john-grid-proof.pdf` (50 pages, SHA-256 `181c4e42f6797d13288518fba389deb63fa53e4862da1d9ebb16809423178494`) |
| Spread PDF | `drafts/travel/bsb-travel-john-facing-spreads-densified.pdf` (4 pages, 84,566 bytes) |
| Spread SHA-256 | `ebb867616f5f0f61d0830029ffc019cf61e8d96e1921182faf68b77343406661` |
| PNGs | `drafts/travel/qa-john/john-spread-02-03.png`, `john-spread-06-07.png`, `john-spread-18-19.png`, `john-spread-24-25.png` (120 dpi) |
| Pairs | 2–3 early prose (John 1:16–49); 6–7 WOC John 3 (3:10–4:14, drop 4 on 7); 18–19 later-`\p` dialogue (7:40–8:24, drop 8 on 18); 24–25 mid-book chapter-open (drop 10, Good Shepherd) |

The older 3-opening sheet `bsb-travel-john-spreads-grid-proof.pdf`
(pairs 2–3, 4–5, 10–11) stays in-tree for history. Prefer the densified
file above.

### Verso/recto line-match

Body 8.5 pt spans sit on a shared 10.5 pt y lattice. Facing pages use the
same slot coordinates (phase Δ 0.0 pt). Shared body y-slots: **14** on 2–3,
**11** on 6–7, **8** on 18–19, **21** on 24–25. Visual check of the four
PNGs matches: text lines meet across the gutter; drop-cap squares and
footnotes do not break the body grid.

## Chapter-opener QA (densified John, 2026-09-15)

`make travel-john-chapter-openers` crops every chapter start from the
committed 50-page John grid-proof. It does not recompile. Source Serif 4
stand-in. Not Milo.

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-john-grid-proof.pdf` (50 pages) |
| Opener PDF | `drafts/travel/qa-john/bsb-travel-john-chapter-openers.pdf` (21 half-leaf crops, 171,131 bytes, SHA-256 `e9035f1d7a06e256e097a0e62e5b0349b295c003bff165fe20c93be9f60dd44a`) |
| PNGs | `drafts/travel/qa-john/john-ch01-opener.png` … `john-ch21-opener.png` (120 dpi) |
| What to check | Drop-cap square, `JOHN ·` running head (interior), first-verse flush beside the drop, 0.35 in indent after later `\s1`, air under book/section title |

No compose change this step: every chapter already has a 31.5 pt drop,
interior running heads, and later-heading indent. Mid-page opens (chs 3,
8, 9, 16, 17, 19) are cropped around the drop so they stay in frame.

Densified John grid-proof 2026-09-13 (Typst 0.14.2, 3.50 in measure,
0.35 in later-`\p` indent, 0.75-baseline gap only on long later `\p`,
body leading −1.0 pt, run-in grey notes, no ruled background, no footer
watermark): 50 pages, 2,043,507 bytes, SHA-256
`181c4e42f6797d13288518fba389deb63fa53e4862da1d9ebb16809423178494`.

## Words of Christ blue QA (2026-09-18)

`make travel-woc-qa` compiles Matthew + John on the current densify
compose (3.50 in measure, 0.35 in later-`\p` indent, 0.75-baseline gap
only on long later `\p`, body leading −1.0 pt) and extracts four native
4.75 × 7 leaves that carry spoken-Christ text. USFM `\wj` still becomes
`#woc` in cobalt `rgb(28, 56, 110)`. Verse numbers stay body ink inside
speech. Source Serif 4 stand-in. Not Milo. Run-in footnotes in grey
`rgb(76, 76, 76)`, no ruled background, no `GRID PROOF` / `NOT FINAL
FACE`. PDF outline: Matthew → 4, 5; John → 3, 14.

Densify pagination puts Matthew 3 baptism and Matthew 4 temptation on
the same leaf (`MATTHEW · 3:13–4:10`). The selector keeps baptism and
takes the Beatitudes as the second distinct Matthew leaf. John 14 still
keeps the pericope title with drop 14 and “The Way, the Truth, and the
Life”.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-woc-qa-grid-proof.pdf` |
| Regen | `make travel-woc-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-18 |
| Pages | 4 (native 4.75 × 7 in leaves) |
| Size | 98,012 bytes |
| SHA-256 | `d57cb175f4cebfe551d1f93072decfca95f6035de2bc42376829c59fd29810ee` |
| Source compile | `drafts/travel/work/woc-books-grid-proof.pdf` (gitignored; 121 pages) |
| PNGs | `drafts/travel/woc/*.png` (120 dpi) |

| Leaf | Source page | Header | What to check |
|------|-------------|--------|---------------|
| `matthew-baptism` | 6 | `MATTHEW · 3:13–4:10` | “Let it be so now”; same leaf now also has “Man shall not live on bread alone” + boxed drop 4 |
| `matthew-sermon` | 8 | `MATTHEW · 4:23–5:12` | Beatitudes in cobalt; boxed drop 5 |
| `john-loved` | 77 | `JOHN · 3:10–29` | 3:16–17 speech in cobalt; notes wrap |
| `john-farewell` | 105 | `JOHN · 13:36–14:13` | Title + drop 14 + “The Way, the Truth, and the Life” stay with their verses |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `woc/matthew-baptism.png` | 149,404 | `241c03fd8dbc4978974711f70be7cfb65de9c4dac204104024aaf172ccf60882` |
| `woc/matthew-sermon.png` | 119,497 | `338a50d5ea5339ce97dc5d9f405ba4931c02d663242d5a286dfc6436aa76d038` |
| `woc/john-loved.png` | 162,065 | `1a43e99478a7c1f3cf052f9c5505d9c568452c0f5d5b12ee5e8ca0d547b6f080` |
| `woc/john-farewell.png` | 159,098 | `654c39ad21ec14921ad2639abd9fb6af57372ba31a0cb1d9579763faf3a526c8` |

## Footnotes QA (2026-09-20)

`make travel-footnotes-qa` compiles John on the current densify
compose (3.50 in measure, 0.35 in later-`\p` indent, 0.75-baseline gap
only on long later `\p`, body leading −1.0 pt, hyphenation cost 80%)
and extracts three native 4.75 × 7 leaves for SPEC §4 translator notes.
USFM `\f` becomes alphabetic footnotes. Numbering resets at the start
of every page (`counter(footnote)` in the header). Notes run in as one
wrapping paragraph at the foot in `rgb(76, 76, 76)`; in-text letter
markers stay body ink. `\fqa` alternate readings are italic. Notes are
not moved into the side margin. Source Serif 4 stand-in. Not Milo.

John-only is enough: page 1 has run-in **a–c** plus `\fqa` italic
(*comprehended*, *tabernacled*, *Unique One*); page 2 restarts at
**a–d**; page 5 is a later `\fqa` leaf (*born from above*).

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-footnotes-qa-grid-proof.pdf` |
| Regen | `make travel-footnotes-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-20 |
| Pages | 3 (native 4.75 × 7 in leaves) |
| Size | 78,453 bytes |
| SHA-256 | `a213788d5693f6ac83bc74dac0fcfe24447ce365bece076bd5e8c6f4850f06f6` |
| Source compile | `drafts/travel/work/footnotes-john-grid-proof.pdf` (gitignored; 50 pages) |
| PNGs | `drafts/travel/footnotes/*.png` (120 dpi) |

| Leaf | Source page | Notes | What to check |
|------|-------------|-------|---------------|
| `john-multi` | 1 | a–c | Run-in foot block (not stacked lines); in-text *a*/*b*/*c*; `\fqa` italic *comprehended* / *tabernacled* / *Unique One*; grey note ink; notes at the foot, not the side |
| `john-reset` | 2 | a–d | Marker `a` again after page 1; run-in a–d; in-text letters stay body ink; folio 2 |
| `john-fqa` | 5 | a–c | Later `\fqa` italic *born from above*; drop 3; notes still a wrapping foot paragraph |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `footnotes/john-multi.png` | 111,414 | `e77aca4cbfb530048a488d1f5c9a35c173eab1914d0bef811538777400d08b9e` |
| `footnotes/john-reset.png` | 146,190 | `af5aed4eac6be62926f68c0ca2cdb351eb869c698bd680c8d0e8afd02dcf7a35` |
| `footnotes/john-fqa.png` | 161,760 | `f87e0e157415039f70a9c6814e23ed783ea0ee9ae8b064bb97ab1d5e18afa27b` |

## Running-header QA (2026-09-19)

`make travel-running-headers-qa` compiles John on the current densify
compose (3.50 in measure, 0.35 in later-`\p` indent, 0.75-baseline gap
only on long later `\p`, body leading −1.0 pt, hyphenation cost 80%)
and extracts four native 4.75 × 7 leaves for SPEC §5 running matter.
Same-chapter ranges omit the repeated chapter (`JOHN · 1:16–33`).
A page that crosses chapters uses `JOHN · 1:50–2:15`. Page 1 still has
no header or folio. Verso left / recto right. Folio centered in the
foot. Heads stay in the 0.50 in head margin, not the 42-line text
block. John has no chapter-only fallback leaf in this pagination
(`JOHN · <chapter>` with no verse marks). Source Serif 4 stand-in.
Not Milo.

The selector no longer hard-codes 2026-09-09 pages 2, 3, 6, 10.
Densify pagination moved the first cross-chapter span to page 4
(page 10 is now same-chapter `JOHN · 5:1–19`).

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-running-headers-qa-grid-proof.pdf` |
| Regen | `make travel-running-headers-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-19 |
| Pages | 4 (native 4.75 × 7 in leaves) |
| Size | 92,538 bytes |
| SHA-256 | `ebe49aed3abc6e5dc76c1e9ea89f0c00223f12275250add9f38e3804094bd5ed` |
| Source compile | `drafts/travel/work/headers-john-grid-proof.pdf` (gitignored; 50 pages) |
| PNGs | `drafts/travel/headers/*.png` (120 dpi) |

| Leaf | Source page | Header | What to check |
|------|-------------|--------|---------------|
| `john-title` | 1 | *(none)* | Title page: no running head, no folio |
| `john-verso` | 2 | `JOHN · 1:16–33` | Verso (even): left-aligned same-chapter range; folio 2 |
| `john-recto` | 3 | `JOHN · 1:34–49` | Recto (odd): right-aligned same-chapter range; folio 3 |
| `john-cross` | 4 | `JOHN · 1:50–2:15` | Cross-chapter span; boxed drop 2; still in the head margin; folio 4 |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `headers/john-title.png` | 111,414 | `e77aca4cbfb530048a488d1f5c9a35c173eab1914d0bef811538777400d08b9e` |
| `headers/john-verso.png` | 146,190 | `af5aed4eac6be62926f68c0ca2cdb351eb869c698bd680c8d0e8afd02dcf7a35` |
| `headers/john-recto.png` | 157,369 | `8c9e42118b94d50e37f45e007581e15cb6a10f44adcbb99b997edbca77c5d8a2` |
| `headers/john-cross.png` | 152,697 | `c2d5914ccea1ca293abb04eb86c08c5eb99022a0a87d1f8dc7337a2c5ea3e0b5` |

## Poetry QA (2026-09-23)

`make travel-poetry-qa` compiles Genesis + Psalms on the current densify
compose (3.50 in measure, 0.35 in later-`\p` indent, 0.75-baseline gap
only on long later `\p`, body leading −1.0 pt, hyphenation cost 80%) and
extracts Psalm 1 and Psalm 119 ALEPH as native 4.75 × 7 stress leaves.
Verse lines (`#poetry`) are **ragged-right**; `\q1` sits on the measure
and `\q2` steps 0.18 in. Body prose stays justified. `\b` stanza pauses
stay one extra baseline (21 pt) on the grid. The composer fails closed
unless the Typst source keeps those densify + SPEC §3 poetry knobs.
Source Serif 4 stand-in. Not Milo.

Densify pagination keeps the same source pages as the 2026-09-08 pack,
but each leaf now carries a verse-range running head and more of the
neighboring material (Psalm 1 into 2:1; ALEPH preceded by Psalm 118
close).

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-poetry-qa-grid-proof.pdf` |
| Regen | `make travel-poetry-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-23 |
| Pages | 2 (native 4.75 × 7 in leaves) |
| Size | 46,103 bytes |
| SHA-256 | `8e115eff65a1ec673b7ec1c0b9aba69138170d1cd0446dd2bb71e68aa259ba94` |
| Links | 55 |
| Source compile | `drafts/travel/work/poetry-books-grid-proof.pdf` (gitignored; 293 pages) |
| PNGs | `drafts/travel/poetry/*.png` (120 dpi) |

| Leaf | Source page | What to check |
|------|-------------|---------------|
| `psalm-1` | 96 | Header `PSALM · 1:1–2:1`; q1 on the measure; q2 +0.18 in; `\b` gaps after vv. 3 and 5; folio prints 96 |
| `psalm-119` | 254 | Header `PSALM · 119:3–19`; Psalm 118 close then ALEPH + boxed drop 119; couplet step; no Hebrew tofu; folio prints 254 |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `poetry/psalm-1.png` | 69,834 | `0fe913e9bdb28d343a8be2255838296d847e6e10d99198a553a0e606d11ba358` |
| `poetry/psalm-119.png` | 96,777 | `1ba03173b44869a68fa8485bc59062470aa2b874a0c532eedbde690e89107ec7` |

## Hyphenation QA (2026-09-21)

`make travel-hyphenation-qa` compiles Genesis + Psalms + John on the
current densify compose (3.50 in measure, 0.35 in later-`\p` indent,
0.75-baseline gap only on long later `\p`, body leading −1.0 pt) and
extracts three native 4.75 × 7 stress leaves for SPEC §3. Language
`en`, `hyphenate: true`, hyphenation cost **80%** of Typst default.
Body is justified with optimized linebreaks and SPEC justification
limits (word space 80–150%; tracking −0.005 em to +0.01 em). USFM
`\nd` renders as `#divine` (`hyphenate: false` + smallcaps) so LORD /
GOD do not break. Source Serif 4 stand-in. Not Milo.

The John selector skips the title page and takes the densest remaining
prose leaf. Densify pagination moved that leaf from the old John 4
Samaritan-woman page to John 3:10–29 (Nicodemus / 3:16), the same
interior span as the WOC `john-loved` leaf.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-hyphenation-qa-grid-proof.pdf` |
| Regen | `make travel-hyphenation-qa` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-21 |
| Pages | 3 (native 4.75 × 7 in leaves) |
| Size | 73,684 bytes |
| SHA-256 | `faeb10afcb46fdd4eb97ae7626799a56d3ad9460ccda919f1d884a2680cfda9a` |
| Links | 158 |
| Source compile | `drafts/travel/work/hyphenation-books-grid-proof.pdf` (gitignored; 343 pages) |
| PNGs | `drafts/travel/hyphenation/*.png` (120 dpi) |

| Leaf | Source page | Hyphen breaks | What to check |
|------|-------------|---------------|---------------|
| `john-prose` | 299 | 3 | 3.50 in justified prose; `be-lieve`, `bap-tized`, `bride-groom`; header `JOHN · 3:10–29`; folio prints 298 |
| `psalm-119` | 254 | 0 | Poetry leaf: Ps 118:25–29 LORD lines stay whole; ALEPH + boxed drop 119; no Hebrew tofu; no divine-name breaks |
| `genesis-1` | 1 | 1 | Title + drop 1 + notes a–c; one end-of-page `ac-` (`according`); `God` unhyphenated |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `hyphenation/john-prose.png` | 162,227 | `62008a08cec17e557ea70e1c2db2deda780ed622bc2c1098cf93f515dc322ca1` |
| `hyphenation/psalm-119.png` | 97,334 | `00fffeb4d78d19158a0be6efc1956c5a6b2d0637d41c2818d5273801b373a3ba` |
| `hyphenation/genesis-1.png` | 96,271 | `9adb47940c08f7e30cd3c997bf7fc3c903182d3bbce6a908f6e895e77ab8385e` |

John-only probe at the old 120% cost had **2** line-end hyphens in 49 pages;
80% was about **11** before densify. On this 3.50 in densify compile the
John 3 leaf still hyphenates (`be-`, `bride-`) and also shows a short
stem (`bap-`). Genesis 1 ends with `ac-`. 50% previously jumped to 34
and chopped `bap-` / `tes-` more often. 80% remains the travel setting.

## Compact sampler (2026-09-17)

`make travel-hotspot-sampler` builds a committed multi-leaf PDF from a
targeted book compile (Genesis, Psalms, Obadiah, 1 John, Revelation) —
not the 2,327-page file. Recompiled 2026-09-17 on the John-fixed
densify compose (0.35 in later-`\p` `#h` indent; 0.75-baseline brick
gap only on long later `\p` of 4+ verses; body leading −1.0 pt;
3.50 in measure), matching the 2026-09-16 full-canon recompile.
Source Serif 4 stand-in. Not Milo. No ruled background; footnotes
run in.

| Item | Value |
|------|-------|
| File | `drafts/travel/bsb-travel-hotspot-sampler-grid-proof.pdf` |
| Regen | `make travel-hotspot-sampler` |
| Engine | Typst 0.14.2 |
| Compiled | 2026-09-17 |
| Pages | 6 (native 4.75 × 7 in leaves) |
| Size | 93,370 bytes |
| SHA-256 | `a37cb173e6458e5aa5a04a178ef98981c576463021c93631bc2f150141fab808` |
| Source compile | `drafts/travel/work/hotspot-books-grid-proof.pdf` (336 pages, gitignored) |
| PNGs | `drafts/travel/hotspots/*.png` (120 dpi) |

| Leaf | Source page | What to check |
|------|-------------|---------------|
| `genesis-1` | 1 | Title + boxed drop 1 + footnotes a–c |
| `psalm-1` | 96 | `q1`/`q2` indent; BOOK I; drop 1 |
| `psalm-119` | 254 | ALEPH Latin label + boxed drop 119; no Hebrew tofu |
| `obadiah` | 294 | Title + body on one opening; not exploded |
| `1-john-3` | 300 | Ch. 3 open + notes a–e; letters stay short |
| `revelation-22` | 336 | 22:14–21 including Amen |

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `hotspots/genesis-1.png` | 96,271 | `9adb47940c08f7e30cd3c997bf7fc3c903182d3bbce6a908f6e895e77ab8385e` |
| `hotspots/psalm-1.png` | 70,169 | `199956d62dfb02568f44512d0353b72e42f630103eb94875dca5094a144ad606` |
| `hotspots/psalm-119.png` | 97,334 | `00fffeb4d78d19158a0be6efc1956c5a6b2d0637d41c2818d5273801b373a3ba` |
| `hotspots/obadiah.png` | 81,969 | `3b10abcddc449326a133804de4e93e6e9b8c5d8114f47d911701fb9ab43628a6` |
| `hotspots/1-john-3.png` | 158,266 | `d606ef8b67fb068a402e0dbb75c0998e0579386985003db8614d007a0b478b35` |
| `hotspots/revelation-22.png` | 94,227 | `ca150351266d1526061b7f4bc7ab6ad7c60b9e8aba82dc92e0de65ccd765e5ce` |

## Known leftovers (not chased)

- Loved-face Milo compile is unchanged and still fail-closed without `fonts/milo/`.
- Typst can fail to converge if a footnote sits exactly at a page break when the counter resets (upstream issue). If a compile warns, re-check that page; do not widen the page spec to paper over it.
