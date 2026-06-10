# BSB Bible PDF Toolkit

A Python CLI toolkit for generating custom PDFs and EPUBs from the Berean Standard Bible (BSB) source files.

## Project Overview

This is a pure Python command-line tool — there is no web frontend or server. It downloads BSB source PDFs, applies custom typography (Lexend font), adds route.bible annotations, and produces print-ready PDF/EPUB outputs.

## Setup

Dependencies are managed with pip:

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

```bash
# Build the primary PDF draft
python design_bsb.py

# Download fresh source and rebuild
python design_bsb.py --refresh-source

# Use a local BSB PDF
python design_bsb.py --source path/to/bsb-book-9.pdf

# QA only (verify + compare without rebuilding)
python design_bsb.py --qa-only --verify --compare
```

## CLI Commands (after install)

| Command | Description |
|---------|-------------|
| `bsb-design` | Main design/build entry point |
| `bsb-download` | Download BSB source PDF |
| `bsb-extract` | Extract BSB content |
| `bsb-add-route-links` | Annotate with route.bible links |
| `bsb-change-font` | Change fonts in PDF |
| `bsb-customize-pdf` | Customize BSB PDF |
| `bsb-customize-epub` | Customize BSB EPUB |
| `bsb-reflow-pdf` | Generate reflow PDF |
| `bsb-typst-pdf` | Generate Typst PDF |
| `bsb-compare-renders` | Compare render outputs |
| `bsb-verify-artifacts` | Verify generated artifacts |

## Project Layout

| Path | Purpose |
|------|---------|
| `design_bsb.py` | Entry point for the draft workflow |
| `src/bsb_pdf_toolkit/` | Python package with generators and utilities |
| `fonts/` | Lexend font assets |
| `drafts/primary/` | Draft outputs and QA records |

## User Preferences

- After any single-column layout change, always regenerate the single-column draft and run `python smoke_test.py`, then present the resulting PDF — without being asked.
