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
with extra separation above the footer. Its title page is labeled
`Primary Fixed-Layout Draft`.

## Single-Column Variant

| Item | Value |
|------|-------|
| Source | `source/engbsb_usfm.zip` (download: `https://bereanbible.com/bsb_usfm.zip`) |
| Command | `PYTHONPATH=src python -m bsb_pdf_toolkit.generate_reflow_pdf drafts/primary/source/engbsb_usfm.zip drafts/primary/bsb-single-column-draft.pdf --font-dir fonts --columns 1` |
| Output | `bsb-single-column-draft.pdf` |
| Page size | `504x756` |
| Typography | Lexend Regular body, Medium verse/section structure, Bold book titles |

This is an exploratory reflowed artifact, not an official-layout match. It
includes generated title, publication, table-of-contents, and preface pages.
The title page is labeled `Single-Column Draft`. The table of contents and
preface scripture citations use internal PDF links.

Current single-column layout knobs are exposed as CLI flags so typography can be
tuned without editing code:

| Option | Current |
|--------|---------|
| `--single-margin-x` | `50` |
| `--single-body-size` | `10.5` |
| `--single-body-leading` | `15.6` |
| `--single-book-title-font` | `Lexend-Bold` |
| `--single-book-title-size` | `34` |
| `--single-book-title-space-above` | `72` |
| `--single-book-title-gap` | `110` |
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
| `bsb-primary-draft.pdf` | `1120` | `432x648` | `4798` | Lexend Bold/Light/Medium/Regular |
| `bsb-single-column-draft.pdf` | `2265` | `504x756` | `87144` route / `89360` total | Lexend Bold/Light/Medium/Regular |

## Current Artifact Fingerprints

| Artifact | Size | SHA-256 |
|----------|------|---------|
| `bsb-primary-draft.pdf` | `82768562` bytes | `355ce252702d9be98fea587d52487502f8424b24556e57f41c0b99f8a325c1b2` |
| `bsb-single-column-draft.pdf` | `28184613` bytes | `e1374deee63b352e8452e9e09be0bf65a87e03aa1ce350606bfe7c9cb6c71442` |

## Current Semantic Fingerprints

| Artifact | Semantic SHA-256 |
|----------|------------------|
| `bsb-primary-draft.pdf` | `db33a516822ddfa9a4ac07024379b724396e1ccc5974bc86414d244ebc11b7ea` |
| `bsb-single-column-draft.pdf` | `088c4f186474cd372182977d4a220f676c2fc46dd5e178971058df3ba5c2b264` |
