#!/usr/bin/env python3
"""Seeded random-page visual QA for the 66-book travel grid-proof.

Picks a reproducible mix of book openers, mid-chapter prose, poetry,
tiny books, a book ending, and uniform pages. Rasters native 4.75 × 7
leaves. Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image

from .generate_travel_pdf import DEFAULT_BIBLE_GRID_PDF, GRID_PROOF_WATERMARK, SAMPLE_SUBTITLE

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "qa-random"
PNG_DPI = 120
RANDOM_QA_SEED = 20260911
NT_FIRST_BOOK = "Matthew"
TINY_BOOKS = frozenset(
    {
        "Obadiah",
        "Jonah",
        "Haggai",
        "Philemon",
        "2 John",
        "3 John",
        "Jude",
        "2 Thessalonians",
        "Titus",
    }
)
POETRY_BOOKS = frozenset(
    {
        "Job",
        "Psalm",
        "Proverbs",
        "Ecclesiastes",
        "Song of Solomon",
        "Isaiah",
        "Jeremiah",
        "Lamentations",
    }
)
PROSE_BOOKS_EXCLUDE = TINY_BOOKS | POETRY_BOOKS


@dataclass(frozen=True)
class BookRange:
    name: str
    start: int
    end: int

    @property
    def pages(self) -> int:
        return self.end - self.start + 1


@dataclass(frozen=True)
class SampleLeaf:
    slug: str
    page: int
    role: str
    book: str
    label: str


def book_ranges_from_toc(toc: list, page_count: int) -> list[BookRange]:
    """Level-1 TOC rows become inclusive 1-based page ranges."""
    books = [entry for entry in toc or [] if entry and entry[0] == 1]
    ranges: list[BookRange] = []
    for index, entry in enumerate(books):
        start = int(entry[2])
        end = int(books[index + 1][2]) - 1 if index + 1 < len(books) else page_count
        ranges.append(BookRange(name=str(entry[1]), start=start, end=end))
    return ranges


def chapter_label(toc: list, page: int, book: str) -> str:
    """Best Book ch.N label for a 1-based page from the outline."""
    chapter = None
    current_book = None
    for level, title, dest in toc or []:
        if dest > page:
            break
        if level == 1:
            current_book = title
            chapter = None
        elif level == 2 and current_book == book:
            chapter = title
    if chapter:
        return f"{book} {chapter}"
    return book


def book_for_page(ranges: list[BookRange], page: int) -> BookRange | None:
    for item in ranges:
        if item.start <= page <= item.end:
            return item
    return None


def _take(rng: random.Random, pool: list[int], count: int, chosen: set[int]) -> list[int]:
    available = [page for page in pool if page not in chosen]
    if not available:
        return []
    if len(available) <= count:
        picked = list(available)
    else:
        picked = rng.sample(available, count)
    chosen.update(picked)
    return picked


def select_random_qa_leaves(
    ranges: list[BookRange],
    toc: list,
    *,
    seed: int = RANDOM_QA_SEED,
    page_count: int | None = None,
) -> list[SampleLeaf]:
    """Pick ~16 reproducible pages. Genesis 1, Ps 119, and Rev 22 are forced."""
    if not ranges:
        raise ValueError("no book ranges")
    last_page = page_count or ranges[-1].end
    rng = random.Random(seed)
    chosen: set[int] = set()
    planned: list[tuple[str, int, str]] = []

    nt_start = next((row.start for row in ranges if row.name == NT_FIRST_BOOK), last_page + 1)
    openers = [item.start for item in ranges if item.name not in TINY_BOOKS]
    ot_openers = [
        item.start
        for item in ranges
        if item.start < nt_start and item.name not in TINY_BOOKS
    ]
    nt_openers = [
        item.start
        for item in ranges
        if item.start >= nt_start and item.name not in TINY_BOOKS
    ]
    genesis = next((item.start for item in ranges if item.name == "Genesis"), openers[0])
    chosen.add(genesis)
    planned.append(("opener", genesis, "forced Genesis 1"))
    ot_extra = _take(rng, [p for p in ot_openers if p != genesis], 1, chosen)
    nt_extra = _take(rng, nt_openers, 2, chosen)
    for page in ot_extra + nt_extra:
        planned.append(("opener", page, "random book opener"))
    # Fill to 4 openers if a side was short.
    while sum(1 for role, _, _ in planned if role == "opener") < 4:
        extra = _take(rng, openers, 1, chosen)
        if not extra:
            break
        planned.append(("opener", extra[0], "random book opener"))

    psalm = next((item for item in ranges if item.name == "Psalm"), None)
    psalm_119 = None
    in_psalm = False
    for level, title, dest in toc or []:
        if level == 1:
            in_psalm = title in {"Psalm", "Psalms"}
        elif in_psalm and level == 2 and str(title) == "119":
            psalm_119 = dest
            break
    if psalm_119:
        chosen.add(psalm_119)
        planned.append(("poetry", psalm_119, "forced Psalm 119"))
    elif psalm:
        chosen.add(psalm.start)
        planned.append(("poetry", psalm.start, "forced Psalm 1"))
    poetry_pool = []
    for item in ranges:
        if item.name not in POETRY_BOOKS:
            continue
        interior = list(range(item.start + 1, item.end + 1))
        poetry_pool.extend(interior)
    for page in _take(rng, poetry_pool, 1, chosen):
        planned.append(("poetry", page, "random poetry"))

    prose_pool = []
    for item in ranges:
        if item.name in PROSE_BOOKS_EXCLUDE:
            continue
        # Mid-chapter: skip opener and last leaf of the book.
        lo = item.start + 1
        hi = item.end - 1
        if lo <= hi:
            prose_pool.extend(range(lo, hi + 1))
    for page in _take(rng, prose_pool, 4, chosen):
        planned.append(("prose", page, "random mid-chapter prose"))

    tiny_pool = [item.start for item in ranges if item.name in TINY_BOOKS]
    for page in _take(rng, tiny_pool, 1, chosen):
        planned.append(("tiny", page, "tiny book opener"))

    chosen.add(last_page)
    planned.append(("ending", last_page, "forced last page / Rev 22"))

    uniform_pool = list(range(1, last_page + 1))
    for page in _take(rng, uniform_pool, 2, chosen):
        planned.append(("uniform", page, "uniform-random"))

    # Two extra leaves so the sheet is ~16 after forced hotspots.
    leftover_prose = _take(rng, prose_pool, 1, chosen)
    if leftover_prose:
        planned.append(("prose", leftover_prose[0], "extra mid-chapter prose"))
    leftover_uniform = _take(rng, uniform_pool, 1, chosen)
    if leftover_uniform:
        planned.append(("uniform", leftover_uniform[0], "extra uniform-random"))

    planned.sort(key=lambda item: item[1])
    leaves: list[SampleLeaf] = []
    for index, (role, page, note) in enumerate(planned, start=1):
        book = book_for_page(ranges, page)
        name = book.name if book else "Unknown"
        label = f"{chapter_label(toc, page, name)} · {note}"
        slug = f"{index:02d}-{role}-{name.lower().replace(' ', '-')}-p{page:04d}"
        leaves.append(SampleLeaf(slug=slug, page=page, role=role, book=name, label=label))
    return leaves


def render_random_qa_pngs(
    source: Path,
    png_dir: Path,
    leaves: list[SampleLeaf],
    *,
    dpi: int = PNG_DPI,
) -> list[Path]:
    png_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(source) as doc:
        for leaf in leaves:
            if leaf.page < 1 or leaf.page > doc.page_count:
                raise ValueError(f"{source} has {doc.page_count} pages; cannot take {leaf.page}")
            pix = doc[leaf.page - 1].get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            path = png_dir / f"{leaf.slug}.png"
            image.save(path, format="PNG", optimize=True)
            written.append(path)
    return written


BRANDING_NEEDLES = (
    "Berean Standard Bible",
    SAMPLE_SUBTITLE,
    "Stand-in face",
    GRID_PROOF_WATERMARK,
    "NOT FINAL FACE",
)


def page_chrome_failures(text: str) -> list[str]:
    """Machine flags for branding / watermark strings. Visual QA still required."""
    hits = []
    for needle in BRANDING_NEEDLES:
        if needle and needle in (text or ""):
            hits.append(needle)
    return hits


def format_selection(leaves: list[SampleLeaf]) -> str:
    lines = ["Random QA leaves (seeded):"]
    for leaf in leaves:
        lines.append(f"  p.{leaf.page:<5} {leaf.role:<8} {leaf.book:<20} {leaf.slug}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Raster a seeded random-page QA sheet from the 66-book travel PDF."
    )
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_BIBLE_GRID_PDF)
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--seed", type=int, default=RANDOM_QA_SEED)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    args = parser.parse_args(argv)
    if not args.source_pdf.is_file():
        print(f"Missing full-Bible PDF: {args.source_pdf}", file=sys.stderr)
        return 1
    with fitz.open(args.source_pdf) as doc:
        toc = doc.get_toc()
        page_count = doc.page_count
    ranges = book_ranges_from_toc(toc, page_count)
    leaves = select_random_qa_leaves(ranges, toc, seed=args.seed, page_count=page_count)
    paths = render_random_qa_pngs(args.source_pdf, args.png_dir, leaves, dpi=args.dpi)
    print(format_selection(leaves))
    for path in paths:
        print(f"Wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
