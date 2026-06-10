---
name: Single-column source download
description: Where to get the USFM zip used to build the single-column draft, and its local path.
---

## Download URL

```
https://bereanbible.com/bsb_usfm.zip
```

Note: the filename on the server is `bsb_usfm.zip` (not `engbsb_usfm.zip` as the README previously stated).

## Local path

Save to `drafts/primary/source/engbsb_usfm.zip` (the local name is kept as `engbsb_usfm.zip` for consistency with the generation command).

## Regeneration command

```bash
PYTHONPATH=src python -m bsb_pdf_toolkit.generate_reflow_pdf \
  drafts/primary/source/engbsb_usfm.zip \
  drafts/primary/bsb-single-column-draft.pdf \
  --font-dir fonts --columns 1
```
