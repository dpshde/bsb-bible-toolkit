# Random-page visual QA (2026-09-11)

Seeded sample of the committed 66-book travel grid-proof. Source Serif 4
stand-in. **Not** FF Milo Serif Text.

```bash
make travel-random-qa
```

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-bible-grid-proof.pdf` (2,264 pages) |
| Seed | `20260911` |
| Engine | Typst 0.14.2, 120 dpi PNG, native 4.75 × 7 in |
| Forced hotspots | Genesis 1 (p.1), Psalm 119 (p.1102), Revelation 22 last leaf (p.2264) |

Machine scan: no page carries `Berean Standard Bible`, `Travel print sample`,
`GRID PROOF`, or `NOT FINAL FACE`. Visual pass below.

## Sample (pass/fail)

| # | Page | Role | Book / range | Result | Notes |
|---|------|------|--------------|--------|-------|
| 1 | 1 | opener (OT, hotspot) | Genesis 1 · `Genesis` | Pass | Title only; no branding; “The Creation” stays with drop 1; notes a–c wrap. |
| 2 | 286 | mid prose | Numbers 28:9–24 | Pass | “The Sabbath Offerings” opens with v9 (not left on p.285). Notes wrap. |
| 3 | 365 | mid prose | Deuteronomy 32:48–33:6 | Pass | “Moses Blesses the Twelve Tribes” stays with drop 33. Poetry indent clean. |
| 4 | 873 | mid prose | Esther 2:16–3:4 | Pass | Mid-page titles stay with the next verse; drop 3 with Haman. |
| 5 | 978 | poetry | Psalm 27:11–28:5 | Pass | “The LORD Is My Strength” stays with drop 28. Ragged verse lines. |
| 6 | 1040 | uniform | Psalm 73:8–25 | Pass | Parallelism indent; single note at the foot. |
| 7 | 1102 | poetry (hotspot) | Psalm 118:23–119:7 | Pass | “Your Word Is a Lamp…” + ALEPH + drop 119 stay together. No Hebrew tofu. |
| 8 | 1112 | uniform | Psalm 119:168–120:6 | Pass | TAW stanza with v169; “In My Distress” stays with drop 120. |
| 9 | 1506 | opener (OT) | Lamentations 1:1–5 | Pass | Book name only; section + drop 1; running head present. |
| 10 | 1730 | mid prose | Habakkuk 1:10–17 | Pass | “Habakkuk’s Second Complaint” stays with v12. |
| 11 | 1771 | opener (NT) | Matthew 1:1–9 | Pass | USFM title only. Genealogy poetry. USFM `\p Next:` is a one-word source line. |
| 12 | 2011 | uniform | Acts 7:30–43 | Pass | “The Call of Moses” at the top with v30; previous leaf ends at v29. |
| 13 | 2075 | mid prose | Romans 11:1–15 | Pass | Section + drop 11 together; heavy notes wrap as one paragraph. |
| 14 | 2170 | opener (NT) | 2 Timothy 1:1–15 | Pass | Title only; greeting stays with drop 1; later heads stay with verses. |
| 15 | 2179 | tiny book | Philemon 1:1–19 | Pass | Whole greeting on one opening; not exploded. |
| 16 | 2264 | ending (hotspot) | Revelation 22:14–21 | Pass | Last leaf through “Amen.”; “Nothing May Be Added” stays with v18. |

Hard-fail checks (orphan header, book-page branding, leftover metadata,
grid/watermark, collisions): **none on this seed**.

## PNG hashes

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `01-opener-genesis-p0001.png` | 114,029 | `748b094b1055916d4a55d9775fd650b3a3c260e89133b118c072b464274422fa` |
| `02-prose-numbers-p0286.png` | 154,816 | `14dfc14dd522d5d17ebf069277b9d4c3db491e99b2862691e8ddae00bcff65c5` |
| `03-prose-deuteronomy-p0365.png` | 136,895 | `e40360bf4aea770af3c5331fe86a44b124292c704efdf326abc43f780944fe12` |
| `04-prose-esther-p0873.png` | 152,348 | `19daba4b9d706fdf0cb48ca6793c42e538240bbe15afa2fb736d18e5f2917b2e` |
| `05-poetry-psalm-p0978.png` | 98,433 | `00c72e5fc60f12c440263b47d930bb8646b973624d96b528d32a6ccddb2dc76b` |
| `06-uniform-psalm-p1040.png` | 106,334 | `0777cc10ce7aed4bd85d911de02e90e0363d8b067d4d8ca24f7fc54b30785b13` |
| `07-poetry-psalm-p1102.png` | 114,418 | `110be04857ce1a56c0ce6d916dd223bdfd00d723ec5fb2028a27ce3fdd4960ff` |
| `08-uniform-psalm-p1112.png` | 100,662 | `7359e0d077791d3713cc859de06e11b68d4d2d8874e12ae889fb0dc1593f0771` |
| `09-opener-lamentations-p1506.png` | 88,389 | `a2c4b63d3b23f5778441001dbe1d2bb9476533c3be5a9b503e09378ace8240e9` |
| `10-prose-habakkuk-p1730.png` | 98,837 | `99e4eb50ef9fd621c525b6ec8b625952a49bf3c59a9ff0110dd85fc85daeb887` |
| `11-opener-matthew-p1771.png` | 94,494 | `3c44c381fcc1088abd492aaa594228211ae0d9d30ee60bcfc374c86191d0c249` |
| `12-uniform-acts-p2011.png` | 145,051 | `644f23073305ab106241711a0cea605b1829ef42b712db0ec8c99ec952837926` |
| `13-prose-romans-p2075.png` | 144,374 | `5fa01a078705ef0dff47ced3ed66c6e8c14656fc950ca7ff1f204333d141aed7` |
| `14-opener-2-timothy-p2170.png` | 148,184 | `ca963337a98b30d1cd5060ea0bce57f9a168b4381d2118f38e798d374f83a947` |
| `15-tiny-philemon-p2179.png` | 142,738 | `908c000171b3410202cb01942af2c431a881f8ddd1ebe1e09cfa770dc4c4e112` |
| `16-ending-revelation-p2264.png` | 94,463 | `f3e8f8e2c4c96f1a4606f758fe949945679689e56f22d8e6afb2ff7757a76115` |
