---
name: Smoke test preference
description: User wants the smoke test run automatically after every single-column layout change.
---

## Rule

After **any** change that affects the single-column layout (typography, spacing, margins, font, keep-with-next logic, etc.):

1. Regenerate the single-column draft:
   ```bash
   PYTHONPATH=src python -m bsb_pdf_toolkit.generate_reflow_pdf \
     drafts/primary/source/engbsb_usfm.zip \
     drafts/primary/bsb-single-column-draft.pdf \
     --font-dir fonts --columns 1
   ```
2. Run the smoke test:
   ```bash
   python smoke_test.py
   ```
3. Present `drafts/primary/work/smoke-test.pdf` to the user with `present_asset`.

**Why:** The full draft is ~2,200 pages and takes 10+ minutes. The smoke test stitches 13 representative pages in seconds, letting the user visually confirm changes without waiting for a full build.
