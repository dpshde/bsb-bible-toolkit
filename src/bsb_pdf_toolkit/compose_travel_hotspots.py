#!/usr/bin/env python3
"""Build a compact committed hotspot sampler from targeted travel books.

Compiles a thin multi-book grid-proof (not the 66-book file), then extracts
the QA leaves listed in drafts/travel/HOTSPOTS.md. Source Serif OFL stand-in
only. Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from .generate_travel_pdf import (
    DEFAULT_GRID_FONT_DIR,
    DEFAULT_USFM,
    GRID_PROOF_WATERMARK,
    main as travel_main,
)
from .generate_typst_pdf import parse_usfm_zip

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "hotspot-books-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "hotspot-books-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-hotspot-sampler-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "hotspots"
PNG_DPI = 120

# Canon-order targeted books. Psalms is the heavy one (Psalm 119 sits late).
HOTSPOT_BOOKS = ("Genesis", "Psalms", "Obadiah", "1 John", "Revelation")


@dataclass(frozen=True)
class BookFace:
    book: str
    title: str
    heading: str


@dataclass(frozen=True)
class HotspotSpec:
    slug: str
    label: str
    book: str
    pick: str  # first | last | contains
    needles: tuple[str, ...] = ()
    require: tuple[str, ...] = ()
    forbid: tuple[str, ...] = ()


# Page content matters more than full-canon page numbers.
DEFAULT_HOTSPOTS = (
    HotspotSpec(
        slug="genesis-1",
        label="Genesis 1 open",
        book="Genesis",
        pick="first",
        require=("In the beginning",),
    ),
    HotspotSpec(
        slug="psalm-1",
        label="Psalm 1 poetry",
        book="Psalms",
        pick="first",
        require=("Blessed is the man",),
    ),
    HotspotSpec(
        slug="psalm-119",
        label="Psalm 119 ALEPH",
        book="Psalms",
        pick="contains",
        needles=("ALEPH",),
        require=("ALEPH",),
        forbid=("א",),
    ),
    HotspotSpec(
        slug="obadiah",
        label="Obadiah open",
        book="Obadiah",
        pick="first",
        require=("Obadiah",),
    ),
    HotspotSpec(
        slug="1-john-3",
        label="1 John 3 notes",
        book="1 John",
        pick="contains",
        needles=("Behold what manner of love",),
        require=("children of God",),
    ),
    HotspotSpec(
        slug="revelation-22",
        label="Revelation 22 close",
        book="Revelation",
        pick="last",
        require=("Amen",),
    ),
)


def normalize_pdf_text(text: str) -> str:
    """Collapse extracted PDF text for heading / needle search."""
    folded = (
        (text or "")
        .replace("\u00ad", "")
        .replace("•", "·")
        .replace("∙", "·")
        .replace("—", "-")
        .replace("–", "-")
    )
    return " ".join(folded.split())


def heading_marker(heading: str) -> str:
    return f"{heading.upper()} ·"


def book_catalog(usfm_zip: Path, books: tuple[str, ...] = HOTSPOT_BOOKS) -> list[BookFace]:
    parsed = parse_usfm_zip(usfm_zip, book_names=list(books))
    got = {item["book"]: item for item in parsed}
    missing = [name for name in books if name not in got]
    if missing:
        raise ValueError(f"USFM did not yield hotspot books: {missing}")
    return [
        BookFace(
            book=name,
            title=(got[name].get("title") or name),
            heading=(got[name].get("heading") or name),
        )
        for name in books
    ]


def detect_page_book(text: str, catalog: list[BookFace], *, fallback: str | None) -> str | None:
    """Prefer running heads (``PSALM · 119``); keep the previous book otherwise."""
    upper = normalize_pdf_text(text).upper()
    for face in sorted(catalog, key=lambda item: len(item.heading), reverse=True):
        if heading_marker(face.heading) in upper:
            return face.book
    return fallback


def book_ranges(
    page_texts: list[str],
    catalog: list[BookFace],
) -> dict[str, tuple[int, int]]:
    """1-based inclusive page ranges per book, in compile order."""
    if not page_texts:
        raise ValueError("source PDF has no pages")
    assigned: list[str] = []
    current = catalog[0].book
    for index, text in enumerate(page_texts):
        fallback = current if index else catalog[0].book
        current = detect_page_book(text, catalog, fallback=fallback) or fallback
        assigned.append(current)
    ranges: dict[str, tuple[int, int]] = {}
    start = 1
    current = assigned[0]
    for index, book in enumerate(assigned[1:], start=2):
        if book != current:
            ranges[current] = (start, index - 1)
            current = book
            start = index
    ranges[current] = (start, len(assigned))
    missing = [face.book for face in catalog if face.book not in ranges]
    if missing:
        raise ValueError(f"could not locate book ranges for {missing}")
    return ranges


def page_has_needles(text: str, needles: tuple[str, ...]) -> bool:
    folded = normalize_pdf_text(text)
    return all(needle.casefold() in folded.casefold() for needle in needles)


def pick_page(
    spec: HotspotSpec,
    page_texts: list[str],
    ranges: dict[str, tuple[int, int]],
) -> int:
    if spec.book not in ranges:
        raise ValueError(f"{spec.slug}: book {spec.book!r} is not in the source PDF")
    start, end = ranges[spec.book]
    if spec.pick == "first":
        return start
    if spec.pick == "last":
        return end
    if spec.pick == "contains":
        if not spec.needles:
            raise ValueError(f"{spec.slug}: contains pick needs needles")
        for page_no in range(start, end + 1):
            if page_has_needles(page_texts[page_no - 1], spec.needles):
                return page_no
        raise ValueError(f"{spec.slug}: no page in {spec.book} contains {spec.needles!r}")
    raise ValueError(f"{spec.slug}: unknown pick {spec.pick!r}")


def validate_leaf(spec: HotspotSpec, text: str) -> None:
    folded = normalize_pdf_text(text)
    missing = [item for item in spec.require if item.casefold() not in folded.casefold()]
    if missing:
        raise ValueError(f"{spec.slug}: missing required text {missing}")
    present = [item for item in spec.forbid if item in text]
    if present:
        raise ValueError(f"{spec.slug}: forbidden text present {present}")


def select_hotspot_pages(
    page_texts: list[str],
    catalog: list[BookFace],
    specs: tuple[HotspotSpec, ...] = DEFAULT_HOTSPOTS,
) -> list[tuple[HotspotSpec, int]]:
    ranges = book_ranges(page_texts, catalog)
    chosen = []
    for spec in specs:
        page_no = pick_page(spec, page_texts, ranges)
        validate_leaf(spec, page_texts[page_no - 1])
        chosen.append((spec, page_no))
    return chosen


def extract_sampler_pdf(
    source: Path,
    output: Path,
    pages: list[int],
) -> Path:
    """Copy selected 1-based pages at native 4.75 × 7 in trim."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src:
        count = len(src)
        for page_no in pages:
            if page_no < 1 or page_no > count:
                raise ValueError(f"{source} has {count} pages; cannot take {page_no}")
        out = fitz.open()
        for page_no in pages:
            out.insert_pdf(src, from_page=page_no - 1, to_page=page_no - 1)
        out.save(output, deflate=True, garbage=4)
        out.close()
    return output


def render_hotspot_pngs(
    sampler_pdf: Path,
    png_dir: Path,
    slugs: list[str],
    *,
    dpi: int = PNG_DPI,
) -> list[Path]:
    png_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(sampler_pdf) as doc:
        if len(doc) != len(slugs):
            raise ValueError(
                f"{sampler_pdf} has {len(doc)} pages but {len(slugs)} slugs were given"
            )
        for index, slug in enumerate(slugs):
            pix = doc[index].get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            path = png_dir / f"{slug}.png"
            image.save(path, format="PNG", optimize=True)
            written.append(path)
    return written


def compile_hotspot_books(
    usfm_zip: Path,
    work_pdf: Path,
    work_typ: Path,
    font_dir: Path,
    books: tuple[str, ...] = HOTSPOT_BOOKS,
) -> int:
    argv = [
        str(usfm_zip),
        str(work_pdf),
        "--typst-out",
        str(work_typ),
        "--font-dir",
        str(font_dir),
        "--grid-proof",
    ]
    for book in books:
        argv.extend(["--book", book])
    return travel_main(argv)


def load_page_texts(pdf_path: Path) -> list[str]:
    with fitz.open(pdf_path) as doc:
        return [page.get_text("text") for page in doc]


def format_selection(chosen: list[tuple[HotspotSpec, int]]) -> str:
    lines = ["Hotspot sampler leaves (source page → leaf):"]
    for spec, page_no in chosen:
        lines.append(f"  {spec.slug}: source p.{page_no}  {spec.label} ({spec.book})")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile targeted travel books and extract a compact hotspot "
            "sampler. GRID PROOF — NOT FINAL FACE. Not the loved face."
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
            print(f"Missing hotspot source PDF: {args.source_pdf}", file=sys.stderr)
            return 1
    else:
        if not args.usfm.is_file():
            print(f"Missing USFM archive: {args.usfm}", file=sys.stderr)
            return 1
        code = compile_hotspot_books(
            args.usfm, args.source_pdf, args.typst_out, args.font_dir
        )
        if code != 0:
            return code

    try:
        if args.usfm.is_file():
            catalog = book_catalog(args.usfm)
        else:
            catalog = [
                BookFace(book=name, title=name, heading=name)
                for name in HOTSPOT_BOOKS
            ]
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_hotspot_pages(page_texts, catalog)
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no in chosen]
    slugs = [spec.slug for spec, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(f"Wrote sampler PDF: {args.output} ({len(pages)} leaves)")
    print(format_selection(chosen))
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
