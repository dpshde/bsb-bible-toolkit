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
