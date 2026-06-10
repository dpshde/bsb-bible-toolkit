---
name: USFM verse-1 destinations
description: Why some chapters (especially Psalms with \d markers) never register a verse 1 PDF destination, and the fix.
---

## The Problem

Some USFM chapters use a `\d` (descriptive title) marker that embeds `\v 1` on the same line:

```
\d \v 1 A Psalm of David.
```

The USFM parser does not recognise `\d`, so the entire line (including the embedded `\v 1`) is dropped. As a result, verse 1 of those chapters is never parsed into a paragraph, and `add_verse_destination("PSA.110", 1, ...)` is never called.

Heading cross-references in other books (e.g. Genesis 14, Hebrews 5) link to `file:PSA.110#1`. When ReportLab tries to serialise those links at `canvas.save()`, it raises:

```
ValueError: format not resolved, probably missing URL scheme or undefined destination target for 'file:PSA.110#1'
```

This caused PDF generation to fail entirely (exit 1) when using the USFM zip as input.

## The Fix

In the chapter render loop, immediately after registering the chapter-level destination, register a verse-1 fallback at the same page position:

```python
writer.add_destination(f"file:{chapter['source']}")
writer.add_destination(f"file:{chapter['source']}#1")   # fallback
```

**Why this works:** If a dropcap or explicit `\v 1` line is rendered later for this chapter, `bookmarkPage` is called again for the same name — ReportLab uses the *last* binding, so the exact verse position wins. For chapters where verse 1 is never explicitly parsed (Psalms `\d` chapters), the fallback stays and points to the chapter top.

## Scope

Only verse 1 is affected this way. Verses 2+ always appear as explicit `\v N` markers in separate USFM lines and are parsed correctly.
