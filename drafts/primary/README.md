# Primary BSB Draft

This directory is the active prototyping area for the current BSB PDF draft.
Generated PDFs, source archives, and rendered QA images are intentionally
ignored by git; this manifest records the current reproducible state.

## Primary Fixed-Layout Draft

| Item | Value |
|------|-------|
| Source | `source/bsb-book-9.pdf` from `https://bereanbible.com/bsb-book-9.pdf` |
| Entry point | `python design_bsb.py` |
| Output | `bsb-primary-draft.pdf` |
| Intermediate | `work/bsb-route-links.pdf` |
| Font profile | `calm` |
| Font scale | `0.86` |
| Footer scale | `0.80` |
| Footer shift | `9.0` |
| Body gray | `0.08` |
| Footer gray | `0.34` |
| Structural gray | `0.03` |

The primary draft preserves the official fixed layout, adds route.bible links,
and redraws text with Lexend Light/Regular/Medium at a slightly airier scale,
with extra separation above the footer.

## Single-Column Variant

| Item | Value |
|------|-------|
| Source | `source/engbsb_usfm.zip` |
| Command | `PYTHONPATH=src python -m bsb_pdf_toolkit.generate_reflow_pdf drafts/primary/source/engbsb_usfm.zip drafts/primary/bsb-single-column-draft.pdf --font-dir fonts --columns 1` |
| Output | `bsb-single-column-draft.pdf` |
| Page size | `504x756` |
| Typography | Lexend Light body, Medium verse/section structure, Black book titles |

This is an exploratory reflowed artifact, not an official-layout match.

Current single-column layout knobs are exposed as CLI flags so typography can be
tuned without editing code:

| Option | Current |
|--------|---------|
| `--single-margin-x` | `78` |
| `--single-body-size` | `10.0` |
| `--single-body-leading` | `14.8` |
| `--single-book-title-font` | `Lexend-Bold` |
| `--single-book-title-size` | `34` |
| `--single-book-title-gap` | `52` |
| `--single-section-heading-size` | `11.2` |
| `--single-dropcap-size` | `36` |
| `--single-dropcap-padding` | `10` |
| `--single-dropcap-protected-lines` | `2` |
| `--single-verse-size` | `6.2` |
| `--single-verse-baseline-shift` | `2.7` |

## QA Commands

Run all current QA checks through the primary flow:

```bash
python design_bsb.py --qa-only --verify --compare
```

`--qa-only` must be paired with `--verify`, `--compare`, or both.

Run the structural verifier:

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.verify_artifacts
```

The verifier checks page counts, page geometry, route-link totals, Lexend font
sets, expected text color tones, byte sizes, and stable semantic fingerprints.
It reports raw PDF SHA-256 hashes by default; use `--strict-fingerprints` to
require exact raw hash matches.

Generate visual comparison sheets:

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.compare_renders
```

The comparison sheets are written to:

| Path | Purpose |
|------|---------|
| `work/primary-reference-comparison-sheet.png` | Official source pages beside the current primary draft |
| `work/single-column-comparison-sheet.png` | Single-column sample page |

## Current Verified Counts

| Artifact | Pages | Page Size | Route Links | Fonts |
|----------|-------|-----------|-------------|-------|
| `bsb-primary-draft.pdf` | `1120` | `432x648` | `4798` | Lexend Light/Medium/Regular |
| `bsb-single-column-draft.pdf` | `2261` | `504x756` | `87144` route / `89283` total | Lexend Bold/Light/Medium/Regular |

## Current Artifact Fingerprints

| Artifact | Size | SHA-256 |
|----------|------|---------|
| `bsb-primary-draft.pdf` | `82649804` bytes | `385556dcbe966cbb43fa34d9691d5dbb41a8c9fd986d9b18269c2aaaab218925` |
| `bsb-single-column-draft.pdf` | `28153195` bytes | `b3b317bc0c3bcaa6bdfac47abaaeffa011cb1010c1e87cb66fcc588d4d8ffd2d` |

## Current Semantic Fingerprints

| Artifact | Semantic SHA-256 |
|----------|------------------|
| `bsb-primary-draft.pdf` | `ce68d5c465ec51f9bad1518d504e208809f1a8a0aa2e6fe96c25256fa04df42a` |
| `bsb-single-column-draft.pdf` | `51fb7ce1887ea9655840c3aecd163068f085aa7f396da4b7531ff2194ac9fd1d` |
