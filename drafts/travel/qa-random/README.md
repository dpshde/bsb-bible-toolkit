# Random-page visual QA (2026-09-16)

Seeded sample of the committed 66-book travel grid-proof after the
John-fixed densify recompile. Source Serif 4 stand-in. **Not** FF Milo
Serif Text.

```bash
make travel-random-qa
```

| Item | Value |
|------|-------|
| Source | `drafts/travel/bsb-travel-bible-grid-proof.pdf` (2,327 pages) |
| SHA-256 | `14d7b0b56eaa433fe60e19e1edee499695e107ddf9612ca16d6a6ce7f42332d9` |
| Size | 32,004,542 bytes |
| John | pages 1997–2046 (50; ±0 vs standalone) |
| Seed | `20260911` |
| Engine | Typst 0.14.2, 120 dpi PNG, native 4.75 × 7 in |
| Forced hotspots | Genesis 1 (p.1), Psalm 119 (p.1125), Revelation 22 last leaf (p.2327) |

Machine scan of the full PDF: no page carries `Berean Standard Bible`,
`Travel print sample`, `GRID PROOF`, or `NOT FINAL FACE`. No leftover
`Next:` and no `|OSIS` / `|1CH` footnote tails.

## Glance pack (today)

| Leaf | Page | PNG |
|------|------|-----|
| Genesis 16 Hagar (later-`\p` indent obvious) | 26 | [`genesis-16-hagar-p0026.png`](genesis-16-hagar-p0026.png) |
| Mid-John prose with WOC blue (John 17:6–26) | 2036 | [`john-mid-woc-p2036.png`](john-mid-woc-p2036.png) |
| Psalm 119 ALEPH / Lamp opener | 1125 | [`psalm-119-aleph-p1125.png`](psalm-119-aleph-p1125.png) |
| Matthew 1 book opener | 1809 | [`matthew-1-opener-p1809.png`](matthew-1-opener-p1809.png) |

Later `\p` first lines on Genesis 16 sit **0.35 in** in from the verso
measure (measured 64.80 pt = 0.55 + 0.35). Verse 1 under the drop stays
flush. John 17 paints WOC `rgb(28, 56, 110)` across the High Priestly
Prayer. Psalm 119 keeps the Lamp title with ALEPH + drop 119. Matthew 1
notes say “see 1 Chronicles 2:9–10” with no `|1CH` tail.

## Seeded sample (pass/fail)

| # | Page | Role | Book / range | Result | Notes |
|---|------|------|--------------|--------|-------|
| 1 | 1 | opener (OT, hotspot) | Genesis 1 | Pass | Title air; no branding; drop 1. |
| 2 | 286 | mid prose | Numbers | Pass | Seeded mid-chapter prose leaf. |
| 3 | 365 | mid prose | Deuteronomy | Pass | Seeded mid-chapter prose leaf. |
| 4 | 871 | mid prose | Nehemiah | Pass | Seeded mid-chapter prose leaf. |
| 5 | 996 | poetry | Psalm | Pass | Poetry indent; section stays with the next verse. |
| 6 | 1040 | uniform | Psalm | Pass | Parallelism indent. |
| 7 | 1111 | uniform | Psalm | Pass | Seeded uniform leaf. |
| 8 | 1125 | poetry (hotspot) | Psalm 118:25–119:9 | Pass | Lamp title clears 118:29 and stays with ALEPH + drop 119. |
| 9 | 1541 | opener (OT) | Lamentations 1 | Pass | Book name only; air around the title; section + drop 1. |
| 10 | 1734 | mid prose | Amos | Pass | Seeded mid-chapter prose leaf. |
| 11 | 1809 | opener (NT) | Matthew 1:1–8 | Pass | Title air; no `Next:`; notes have no `|1CH`. |
| 12 | 2011 | uniform | John 6 | Pass | Interior John leaf inside the 50-page span. |
| 13 | 2091 | mid prose | Acts | Pass | Seeded mid-chapter prose leaf. |
| 14 | 2227 | opener (NT) | 2 Timothy 1 | Pass | Title air; greeting stays with drop 1. |
| 15 | 2237 | tiny book | Philemon 1 | Pass | Title air; opening fits; not exploded. |
| 16 | 2327 | ending (hotspot) | Revelation 22 | Pass | Last leaf of the 2,327-page canon. |

Hard-fail checks (orphan header, book-page branding, leftover metadata,
grid/watermark, collisions, `Next:`, `|OSIS`): **none on this seed**.

## PNG hashes

| PNG | Bytes | SHA-256 |
|-----|-------|---------|
| `01-opener-genesis-p0001.png` | 96,271 | `9adb47940c08f7e30cd3c997bf7fc3c903182d3bbce6a908f6e895e77ab8385e` |
| `02-prose-numbers-p0286.png` | 109,369 | `2a006eb37a14003b4910c7c08c300f7685e8252c6c08ffc6bbbb8caadc73351c` |
| `03-prose-deuteronomy-p0365.png` | 163,643 | `381755620bb6c6389582aa1f476b16ad20ace554239dcce9bec6b03541da9596` |
| `04-prose-nehemiah-p0871.png` | 156,366 | `3e50d2aa9c4ec3fe85b3bb271461416a723ce5c8ff96e1f5b6f5ef839f617ac9` |
| `05-poetry-psalm-p0996.png` | 94,362 | `44e46910f168762c29785be91f3ff8e55366a0dcd456bd125aaa00453dc5773d` |
| `06-uniform-psalm-p1040.png` | 103,042 | `b530579d90eb5a09eff05a37c5d1c997093a5a910a7cc66ecde1f3114275c323` |
| `07-uniform-psalm-p1111.png` | 108,561 | `a81530c426580ea9951acdfa4d04ac328e7d2df894eb9dd08eb30e8fdd12b901` |
| `08-poetry-psalm-p1125.png` | 97,375 | `44673be7da5cbc8639154c7010ed488599ea0cd2013cfd2b5e7e87da1847e9ef` |
| `09-opener-lamentations-p1541.png` | 75,737 | `30f6936808f45f41398d41eb4e16ff473741f8c3621e6fa5e87114bd18beff4e` |
| `10-prose-amos-p1734.png` | 123,677 | `3136b401f28da75cde9f6f3ef15c7783a1eeebb3953cc911ec0fcb4508fa4e40` |
| `11-opener-matthew-p1809.png` | 87,329 | `55f42eaa01cd77daa337cb32c9fda3c1bf324389310502db085998a26e7aea88` |
| `12-uniform-john-p2011.png` | 147,555 | `a8f24676a878e3a84a79ebe0b7738d8d2084afc49020b0f0e66c0296a1885d3f` |
| `13-prose-acts-p2091.png` | 122,700 | `a615c6a677637215e8572fa1be5ee1e44079b1968bb96e128291b7d454cc72d9` |
| `14-opener-2-timothy-p2227.png` | 124,513 | `1cbe7a50678abfce801c5e93d4c037be8373e7afc6575da5c305a66b4ae8249b` |
| `15-tiny-philemon-p2237.png` | 121,916 | `36f82502d6c6c988f7734e10fcb1f8e4494df299bda6cae065f6ebe435e206a7` |
| `16-ending-revelation-p2327.png` | 94,297 | `513f72c37372a63a92422bd3df347d32ba5cd2cd0887a704fbb0f47d9849520c` |
| `genesis-16-hagar-p0026.png` | 156,509 | `a1cb128a88d9c1f63e094644f05c91c6e6ad18098ff894f25e4dbd119c25c7a6` |
| `john-mid-woc-p2036.png` | 164,415 | `3f97a9e2f404d6e922db94310cd83c3232de157f8d50f06cb0ae432f2986aa91` |
| `psalm-119-aleph-p1125.png` | 97,375 | `44673be7da5cbc8639154c7010ed488599ea0cd2013cfd2b5e7e87da1847e9ef` |
| `matthew-1-opener-p1809.png` | 87,329 | `55f42eaa01cd77daa337cb32c9fda3c1bf324389310502db085998a26e7aea88` |
