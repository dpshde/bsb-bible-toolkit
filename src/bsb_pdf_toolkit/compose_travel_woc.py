#!/usr/bin/env python3
"""Extract a Words of Christ (WOC) blue QA sheet from Matthew + John.

Compiles Matthew + John (grid proof only), then copies native 4.75 × 7
leaves that carry spoken-Christ text so cobalt ``rgb(28, 56, 110)`` can
be checked. Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compose_travel_hotspots import (
    BookFace,
    HotspotSpec,
    book_catalog,
    book_ranges,
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    normalize_pdf_text,
    pick_page,
    render_hotspot_pngs,
    validate_leaf,
)
from .generate_travel_pdf import (
    DEFAULT_GRID_FONT_DIR,
    DEFAULT_USFM,
    GRID_PROOF_WATERMARK,
    SPEC,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "woc-books-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "woc-books-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-woc-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "woc"
PNG_DPI = 120

WOC_QA_BOOKS = ("Matthew", "John")
WOC_QA_MIN_LEAVES = 3
WOC_QA_MAX_LEAVES = 4
WOC_REQUIRED_SLUGS = frozenset({"matthew-baptism", "john-farewell"})

# Known BSB speech. Page picks inspect compiled text; do not invent verses.
WOC_QA_LEAVES = (
    HotspotSpec(
        slug="matthew-baptism",
        label="Matthew 3 baptism",
        book="Matthew",
        pick="contains",
        needles=("Let it be so now",),
        require=("Let it be so now",),
    ),
    HotspotSpec(
        slug="matthew-temptation",
        label="Matthew 4 temptation",
        book="Matthew",
        pick="contains",
        needles=("Man shall not live on bread alone",),
        require=("Man shall not live on bread alone",),
    ),
    HotspotSpec(
        slug="john-farewell",
        label="John 14 farewell",
        book="John",
        pick="contains",
        needles=("Do not let your hearts be troubled",),
        require=("Do not let your hearts be troubled",),
    ),
    HotspotSpec(
        slug="john-loved",
        label="John 3 loved the world",
        book="John",
        pick="contains",
        needles=("For God so loved the world",),
        require=("For God so loved the world",),
    ),
    HotspotSpec(
        slug="matthew-sermon",
        label="Matthew 5 Beatitudes",
        book="Matthew",
        pick="contains",
        needles=("Blessed are the poor in spirit",),
        require=("Blessed are the poor in spirit",),
    ),
)

KNOWN_WOC_SPEECH = tuple(
    needle for spec in WOC_QA_LEAVES for needle in spec.needles
)


def fold_woc_text(text: str) -> str:
    """Normalize extracted PDF text and close hyphenation breaks."""
    folded = normalize_pdf_text(text)
    return folded.replace("- ", "")


def page_has_woc_speech(
    text: str,
    needles: tuple[str, ...] | None = None,
) -> bool:
    """True when the leaf carries at least one known WOC speech phrase."""
    folded = fold_woc_text(text).casefold()
    check = needles or KNOWN_WOC_SPEECH
    return any(needle.casefold() in folded for needle in check)


def typst_exercises_woc(typst_text: str) -> bool:
    """True when the Typst source defines and uses the ``#woc`` cobalt path."""
    text = typst_text or ""
    rgb = f"rgb({SPEC.woc_rgb[0]}, {SPEC.woc_rgb[1]}, {SPEC.woc_rgb[2]})"
    return (
        "#let woc(" in text
        and "#woc[" in text
        and "woc-blue" in text
        and rgb in text
    )


def speech_wrapped_in_woc(typst_text: str, phrase: str) -> bool:
    """True when ``phrase`` sits after a nearby ``#woc[`` opener."""
    idx = (typst_text or "").find(phrase)
    if idx < 0:
        return False
    window = typst_text[max(0, idx - 240) : idx]
    return "#woc[" in window


def validate_woc_typst(
    typst_text: str,
    phrases: tuple[str, ...] = KNOWN_WOC_SPEECH,
) -> None:
    """Require the ``#wj`` → ``#woc`` path and known speech in Typst."""
    if not typst_exercises_woc(typst_text):
        raise ValueError("Typst source does not exercise #woc / woc-blue")
    for phrase in phrases:
        if phrase not in typst_text:
            raise ValueError(f"Typst source missing WOC speech {phrase!r}")
        if not speech_wrapped_in_woc(typst_text, phrase):
            raise ValueError(f"Typst source does not wrap {phrase!r} in #woc[")


def select_woc_pages(
    page_texts: list[str],
    catalog: list[BookFace],
    specs: tuple[HotspotSpec, ...] = WOC_QA_LEAVES,
) -> list[tuple[HotspotSpec, int]]:
    """Pick 3–4 distinct WOC leaves, keeping Matthew and John."""
    ranges = book_ranges(page_texts, catalog)
    chosen: list[tuple[HotspotSpec, int]] = []
    seen: set[int] = set()
    for spec in specs:
        try:
            page_no = pick_page(spec, page_texts, ranges)
        except ValueError:
            if spec.slug in WOC_REQUIRED_SLUGS:
                raise
            continue
        if page_no in seen:
            continue
        validate_leaf(spec, page_texts[page_no - 1])
        if not page_has_woc_speech(page_texts[page_no - 1], spec.require):
            raise ValueError(f"{spec.slug}: page {page_no} is missing WOC speech")
        chosen.append((spec, page_no))
        seen.add(page_no)
        if len(chosen) >= WOC_QA_MAX_LEAVES:
            break
    if len(chosen) < WOC_QA_MIN_LEAVES:
        raise ValueError(
            f"need at least {WOC_QA_MIN_LEAVES} distinct WOC leaves, got {len(chosen)}"
        )
    books = {spec.book for spec, _ in chosen}
    missing = [name for name in WOC_QA_BOOKS if name not in books]
    if missing:
        raise ValueError(f"WOC QA must include Matthew and John; missing {missing}")
    chosen.sort(key=lambda item: item[1])
    return chosen


def validate_woc_pages(
    chosen: list[tuple[HotspotSpec, int]],
    page_texts: list[str],
    typst_text: str | None = None,
) -> None:
    """Require WOC speech on each selected leaf, and Typst ``#woc`` when given."""
    if len(chosen) < WOC_QA_MIN_LEAVES:
        raise ValueError(
            f"need at least {WOC_QA_MIN_LEAVES} distinct WOC leaves, got {len(chosen)}"
        )
    phrases: list[str] = []
    for spec, page_no in chosen:
        if page_no < 1 or page_no > len(page_texts):
            raise ValueError(f"source PDF has {len(page_texts)} pages; cannot take {page_no}")
        validate_leaf(spec, page_texts[page_no - 1])
        if not page_has_woc_speech(page_texts[page_no - 1], spec.require):
            raise ValueError(f"{spec.slug}: page {page_no} is missing WOC speech")
        phrases.extend(spec.require)
    if typst_text is not None:
        validate_woc_typst(typst_text, tuple(phrases))


def format_selection(chosen: list[tuple[HotspotSpec, int]]) -> str:
    lines = ["WOC QA leaves (source page → leaf):"]
    for spec, page_no in chosen:
        lines.append(f"  {spec.slug}: source p.{page_no}  {spec.label} ({spec.book})")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile Matthew/John and extract Words of Christ QA leaves. "
            "GRID PROOF — NOT FINAL FACE. Not the loved face."
        )
    )
    parser.add_argument("--usfm", type=Path, default=DEFAULT_USFM)
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_WORK_PDF)
    parser.add_argument("--typst-out", type=Path, default=DEFAULT_WORK_TYP)
    parser.add_argument("--font-dir", type=Path, default=DEFAULT_GRID_FONT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)

    if args.no_compile:
        if not args.source_pdf.is_file():
            print(f"Missing WOC source PDF: {args.source_pdf}", file=sys.stderr)
            return 1
    else:
        if not args.usfm.is_file():
            print(f"Missing USFM archive: {args.usfm}", file=sys.stderr)
            return 1
        code = compile_hotspot_books(
            args.usfm,
            args.source_pdf,
            args.typst_out,
            args.font_dir,
            books=WOC_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        if args.usfm.is_file():
            catalog = book_catalog(args.usfm, books=WOC_QA_BOOKS)
        else:
            catalog = [
                BookFace(book=name, title=name, heading=name) for name in WOC_QA_BOOKS
            ]
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_woc_pages(page_texts, catalog)
        typst_text = None
        if args.typst_out.is_file():
            typst_text = args.typst_out.read_text(encoding="utf-8")
        validate_woc_pages(chosen, page_texts, typst_text)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no in chosen]
    slugs = [spec.slug for spec, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(f"Wrote WOC QA PDF: {args.output} ({len(pages)} leaves)")
    print(format_selection(chosen))
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
