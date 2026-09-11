# Random-page visual QA (2026-09-11)

Seeded sample of the committed 66-book travel grid-proof. Source Serif 4
stand-in. **Not** FF Milo Serif Text.

```bash
make travel-random-qa
```

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-bible-grid-proof.pdf` (2,365 pages) |
| Seed | `20260911` |
| Engine | Typst 0.14.2, 120 dpi PNG, native 4.75 × 7 in |
| Forced hotspots | Genesis 1 (p.1), Psalm 119 (p.1145), Revelation 22 last leaf (p.2365) |

Machine scan: no page carries `Berean Standard Bible`, `Travel print sample`,
`GRID PROOF`, or `NOT FINAL FACE`. No leftover `Next:` and no `|OSIS` /
`|1CH` footnote tails.

## Requested re-rasters

| Leaf | Page | PNG |
|------|------|-----|
| Genesis 1 opener | 1 | [`genesis-1-opener-p0001.png`](genesis-1-opener-p0001.png) |
| Matthew 1 opener | 1836 | [`matthew-1-opener-p1836.png`](matthew-1-opener-p1836.png) |
| Psalm 119 ALEPH / Lamp title | 1145 | [`psalm-119-aleph-p1145.png`](psalm-119-aleph-p1145.png) |
| Philemon opener | 2273 | [`philemon-opener-p2273.png`](philemon-opener-p2273.png) |

## Sample (pass/fail)

| # | Page | Role | Book / range | Result | Notes |
|---|------|------|--------------|--------|-------|
| 1 | 1 | opener (OT, hotspot) | Genesis 1 · `Genesis` | Pass | Title has air above/below; no branding; “The Creation” with drop 1. |
| 2 | 286 | mid prose | Numbers | Pass | Seeded mid-chapter prose leaf. |
| 3 | 365 | mid prose | Deuteronomy | Pass | Seeded mid-chapter prose leaf. |
| 4 | 869 | mid prose | Ezra | Pass | Seeded mid-chapter prose leaf. |
| 5 | 1017 | poetry | Psalm | Pass | Poetry indent; section stays with the next verse. |
| 6 | 1040 | uniform | Psalm | Pass | Parallelism indent. |
| 7 | 1145 | poetry (hotspot) | Psalm 118:26–119:9 | Pass | Lamp title clears 118:29 and stays with ALEPH + drop 119. |
| 8 | 1564 | opener (OT) | Lamentations 1 | Pass | Book name only; air around the title; section + drop 1. |
| 9 | 1732 | mid prose | Hosea | Pass | Seeded mid-chapter prose leaf. |
| 10 | 1836 | opener (NT) | Matthew 1:1–8 | Pass | Title air; no `Next:`; notes say “see 1 Chronicles 2:9–10” with no `|1CH`. |
| 11 | 2011 | uniform | Luke | Pass | Seeded uniform leaf. |
| 12 | 2094 | mid prose | Acts | Pass | Seeded mid-chapter prose leaf. |
| 13 | 2263 | opener (NT) | 2 Timothy 1 | Pass | Title air; greeting stays with drop 1. |
| 14 | 2273 | tiny book | Philemon 1:1–15 | Pass | Title air; opening fits; not exploded. |
| 15 | 2343 | uniform | Revelation | Pass | Seeded uniform leaf. |
| 16 | 2365 | ending (hotspot) | Revelation 22 | Pass | Last leaf of the 2,365-page canon. |

Hard-fail checks (orphan header, book-page branding, leftover metadata,
grid/watermark, collisions, `Next:`, `|OSIS`): **none on this seed**.

## PNG hashes

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `01-opener-genesis-p0001.png` | 102,684 | `7dca9cf6f0b536dc2fdc84c962128360fdab208497a644ff486bd7739072773d` |
| `02-prose-numbers-p0286.png` | 113,801 | `276a8975bf59ae7de9aeee008c4882b5d3848ebc49a2dbe5d9c8e787e49c3c72` |
| `03-prose-deuteronomy-p0365.png` | 85,531 | `3c86ad2a974d66fe146a19cdbb398347e2854c5f81d6e9ecf36d371f94a523ea` |
| `04-prose-ezra-p0869.png` | 129,485 | `2f0d5343a3158d0050708f25a1b0bad9cbe260f5428f62a92f78188443fe4196` |
| `05-poetry-psalm-p1017.png` | 95,785 | `deca51ef64686d06760c75790b8cbbd84e492dd89470bcc6366848eabd9a984a` |
| `06-uniform-psalm-p1040.png` | 102,162 | `eb0e7468ac7c90839cef689660a33b21049e86f447dffb4f7bf4235bcba4e219` |
| `07-poetry-psalm-p1145.png` | 117,084 | `fcc2a3a7af56c3baa1696b98442093b025611d4094f28fef33c4d31a7eec490e` |
| `08-opener-lamentations-p1564.png` | 75,840 | `29fb327a31d819b61bd5388ead4f23fa5c2f3a8542b93e801f0d6d18c151e8d9` |
| `09-prose-hosea-p1732.png` | 113,586 | `ce1b421d9acce608fa5dd3bdace2397b0c6dc24330416332153e5cbd7adcc516` |
| `10-opener-matthew-p1836.png` | 87,534 | `3a2b506ef535299184ea3dca123f807be74937378f55c06f65f6212988c7a223` |
| `11-uniform-luke-p2011.png` | 141,472 | `02a3882f34acb21b52277ddf18a4caa57f0ad685d6ec9c4728bf2a52d6bf3378` |
| `12-prose-acts-p2094.png` | 130,892 | `0ff27c91bfc513916539640cc930db9aca1a9077351c2d963ef8426e04753eb6` |
| `13-opener-2-timothy-p2263.png` | 119,247 | `b838815acb7bf40dcff0047c9a25a7f4a6966e859c3b3857fa35a847837b2c2d` |
| `14-tiny-philemon-p2273.png` | 120,269 | `8ddf9c05775f1274c1473cd4a49800ee2b8f092bc986347769cd589acd9d6455` |
| `15-uniform-revelation-p2343.png` | 122,584 | `410f226239d854523ee18f2c5b9e65da8b29c8620a0c46df12ff8bc68ce547b4` |
| `16-ending-revelation-p2365.png` | 72,873 | `27da33c82c5328c53e9b4b0b2020ea9c1a5975b45c246847c0bd1a3484db665b` |
| `genesis-1-opener-p0001.png` | 102,684 | `7dca9cf6f0b536dc2fdc84c962128360fdab208497a644ff486bd7739072773d` |
| `matthew-1-opener-p1836.png` | 87,534 | `3a2b506ef535299184ea3dca123f807be74937378f55c06f65f6212988c7a223` |
| `psalm-119-aleph-p1145.png` | 117,084 | `fcc2a3a7af56c3baa1696b98442093b025611d4094f28fef33c4d31a7eec490e` |
| `philemon-opener-p2273.png` | 120,269 | `8ddf9c05775f1274c1473cd4a49800ee2b8f092bc986347769cd589acd9d6455` |
