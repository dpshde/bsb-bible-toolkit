# John grid-proof QA leaves (2026-09-13)

Native 4.75 × 7 in rasters from the densified John travel grid-proof.
Source Serif 4 stand-in. **Not** FF Milo Serif Text.

```bash
make travel-john-grid-proof
make travel-john-spreads
```

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-john-grid-proof.pdf` (50 pages) |
| Engine | Typst 0.14.2, 120 dpi PNG |
| Compiled | 2026-09-13 |

Machine scan: no page carries `Berean Standard Bible`, `Travel print sample`,
`GRID PROOF`, or `NOT FINAL FACE`. No leftover `Next:` and no `|OSIS` tails.

## Leaves

| Leaf | Page | Size | SHA-256 | What to check |
|------|------|------|---------|---------------|
| [`01-opener-john-1.png`](01-opener-john-1.png) | 1 | 83,334 | `6f28da1dc8d3dbb2203c711e92e5a41a4a26876b14e09b49273b5ccbc8788cd8` | John 1 opener: USFM title, drop 1, flush remainder |
| [`02-prose-indent-john-1.png`](02-prose-indent-john-1.png) | 2 | 109,453 | `910b7f83a8e82f74e4f9ba7488a187ced4f550a83c812da66530c60025cc4c2c` | Mid-chapter later-\p indent (John 1:16–33) |
| [`03-woc-john-3.png`](03-woc-john-3.png) | 6 | 121,519 | `b7e4586b0812d43bd8e9904465e55a12c58b73e0cf1702c951c3b3933adadc6a` | WOC blue leaf (John 3:10–29) |

## Facing spreads (densified, 2026-09-14)

2-up openings from the same 50-page John. Verso left, recto right.
Regen: `make travel-john-spreads`. PDF:
`drafts/travel/bsb-travel-john-facing-spreads-densified.pdf`
(4 pages, 84,566 bytes, SHA-256
`ebb867616f5f0f61d0830029ffc019cf61e8d96e1921182faf68b77343406661`).

| Spread | Pages | Size | SHA-256 | What to check |
|--------|-------|------|---------|---------------|
| [`john-spread-02-03.png`](john-spread-02-03.png) | 2–3 | 329,452 | `50a8ee50cc97a5d8de66474a648e93fbf4706c7cd75ef96e92c0ca0464dec3f5` | Early prose after the title (John 1:16–49); later-`\p` indent |
| [`john-spread-06-07.png`](john-spread-06-07.png) | 6–7 | 411,516 | `e7b0c88dcec9274363d4d452b6d944710fcf53cdad5ef70f3d168e2b2a71ebb0` | WOC blue John 3:10–4:14; 3:16 cobalt; drop 4 on recto |
| [`john-spread-18-19.png`](john-spread-18-19.png) | 18–19 | 362,140 | `9cb39dd4148005697b265b47146d75ce12ee300c24762d501283bbcffc128c00` | Denser dialogue / later-`\p` indent (7:40–8:24); drop 8 |
| [`john-spread-24-25.png`](john-spread-24-25.png) | 24–25 | 380,962 | `769db8ac3fb26202cb0b566ce0132ce5712195b2e4f4c934425ac429a2545dc2` | Mid-book chapter-open: drop 10, Good Shepherd |

## Chapter openers (densified, 2026-09-15)

Half-leaf crops of every John chapter start. Mid-page opens follow the
drop, not the physical page top. Regen: `make travel-john-chapter-openers`.
Source Serif 4. Not Milo. No Typst change — John stays 50 pages.

| Item | Value |
|------|-------|
| PDF | [`bsb-travel-john-chapter-openers.pdf`](bsb-travel-john-chapter-openers.pdf) |
| Pages | 21 (chs 1–21) |
| Size | 171,131 bytes |
| SHA-256 | `e9035f1d7a06e256e097a0e62e5b0349b295c003bff165fe20c93be9f60dd44a` |

What to scan: drop-cap square, running head `JOHN · …` (interior top-of-page
opens), first verse flush beside the drop, 0.35 in indent after a later
heading, air under the book/section title.

| Leaf | Source page | Size | SHA-256 |
|------|-------------|------|---------|
| [`john-ch01-opener.png`](john-ch01-opener.png) | 1 | 49,917 | `d63c351a1b330ecb0b9e9dec2ca4c8f73cb7da73e525b8fd3109391035788fca` |
| [`john-ch02-opener.png`](john-ch02-opener.png) | 4 | 84,167 | `5f28f33e7c382faf5fda0fd307a3583ca2bc2201b6a44328f8f64c9c1f6d79c6` |
| [`john-ch03-opener.png`](john-ch03-opener.png) | 5 | 88,296 | `fa0117957afaa5e386d41de71ced50a999bf84a219053f2edfd3cd00033a8d3d` |
| [`john-ch04-opener.png`](john-ch04-opener.png) | 7 | 91,007 | `5c57d9d1d4ebecbfe461dcfbf444800456b0e2de947b2516d9295088e8646628` |
| [`john-ch05-opener.png`](john-ch05-opener.png) | 10 | 83,356 | `10e9596814e8ba29fb36a87ffae460d26830220ce6f7d6bcbeec50f0a288a9b3` |
| [`john-ch06-opener.png`](john-ch06-opener.png) | 12 | 94,145 | `52110cca6a814a6c2d23e469218e407969b5617c461e97c501a8009a1c0e9b4e` |
| [`john-ch07-opener.png`](john-ch07-opener.png) | 16 | 85,985 | `d2b634a4967b9937ec16bd31c2cabf0fbc75d6050662f05dd6a58dc79f487826` |
| [`john-ch08-opener.png`](john-ch08-opener.png) | 18 | 85,245 | `06ca5ee52dc72cfb3de1d78f5fcf9ab5078a349dcd604aba46e8880e8cc8f5ed` |
| [`john-ch09-opener.png`](john-ch09-opener.png) | 21 | 93,714 | `a875c8d891183c38018770f1487c348640925dab58c04f641c3182710b1a25f4` |
| [`john-ch10-opener.png`](john-ch10-opener.png) | 24 | 87,072 | `32df32ae524de91bb56288eb6629eda23c9b2757ed7f5f540a226d2f867c5272` |
| [`john-ch11-opener.png`](john-ch11-opener.png) | 26 | 94,988 | `796c8485da31a9fa54122c7ac63906d90a287011e434d1ede003b85ecf0f562e` |
| [`john-ch12-opener.png`](john-ch12-opener.png) | 29 | 81,470 | `c3ce7cc6440f54fee8a83eb7ff72a0675c7f8ef840627b88df649f5e9388e663` |
| [`john-ch13-opener.png`](john-ch13-opener.png) | 32 | 84,383 | `bad2b7b49c6acf7c49690c98962b2ff65f289f1463a5725bc3bc22cd1c40653a` |
| [`john-ch14-opener.png`](john-ch14-opener.png) | 34 | 78,426 | `8c44f8bf59695ed534d362c52bd11076163d61f16834fb490ddf58fc2261a0c5` |
| [`john-ch15-opener.png`](john-ch15-opener.png) | 36 | 70,258 | `d7931804ef14371b05f2895c702be7b7ac6726a194a6ac78dd601b60ed8c7645` |
| [`john-ch16-opener.png`](john-ch16-opener.png) | 37 | 78,774 | `e4c0a5ddabcb0bdec262cd59bd58c2e140771f1488dc4f6d4b10932eb5cf5ed2` |
| [`john-ch17-opener.png`](john-ch17-opener.png) | 39 | 96,278 | `397eb32ba05ac4af6d689d96b1b2873a02f352026cd1c2f3b0834f5264fc0271` |
| [`john-ch18-opener.png`](john-ch18-opener.png) | 41 | 88,136 | `25161f8a0596d1667c1f92cebc6b74eacf3864c41cf804bfa6dfa59cc425be1a` |
| [`john-ch19-opener.png`](john-ch19-opener.png) | 43 | 91,399 | `185789c217c9672a3e1888cab94991e2b7f0bca3c91bb88e2f25eafccaf26c55` |
| [`john-ch20-opener.png`](john-ch20-opener.png) | 46 | 88,819 | `e16a0c817110ff4fb07cd53772a6808d2ec7b1693526d76c18b3d1c578acd162` |
| [`john-ch21-opener.png`](john-ch21-opener.png) | 48 | 94,763 | `0b79c9230182ee82fec753dd56c2d14d9cf862af8aa7a5dfb6d406ebacb0a580` |
