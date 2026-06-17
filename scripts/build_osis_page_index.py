#!/usr/bin/env python3
"""Build OSIS -> PDF page index from route.bible links embedded in a BSB PDF."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import fitz

ROUTE_BIBLE_URI = re.compile(
    r"https://route\.bible/([A-Za-z0-9]+)\.(\d+)(?:\.(\d+))?"
)


EDITION_DEFAULTS = {
    "single-column": {
        "id": "crafted-bsb-single-column",
        "pdf": "BSB - Single Column.pdf",
    },
    "primary-fixed-layout": {
        "id": "crafted-bsb-primary-fixed-layout",
        "pdf": "BSB - Primary Layout.pdf",
    },
}


def build_index(pdf_path: Path, edition: str) -> dict:
    doc = fitz.open(pdf_path)
    chapters: dict[str, dict] = {}
    verses: dict[str, dict] = {}

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_num = page_index + 1
        page_height = page.rect.height

        for link in page.get_links():
            uri = link.get("uri", "")
            match = ROUTE_BIBLE_URI.fullmatch(uri)
            if not match:
                continue

            book, chapter_str, verse_str = match.group(1), match.group(2), match.group(3)
            chapter_key = f"{book}.{int(chapter_str)}"
            rect = link.get("from")
            y_frac = round(rect.y0 / page_height, 4) if rect else None

            existing_chapter = chapters.get(chapter_key)
            if existing_chapter is None or page_num < existing_chapter["page"]:
                chapters[chapter_key] = {"page": page_num}

            if verse_str:
                verse_key = f"{book}.{int(chapter_str)}.{int(verse_str)}"
                existing_verse = verses.get(verse_key)
                if existing_verse is None or page_num < existing_verse["page"]:
                    entry = {"page": page_num}
                    if y_frac is not None:
                        entry["y"] = y_frac
                    verses[verse_key] = entry
                elif page_num == existing_verse["page"] and y_frac is not None:
                    if existing_verse.get("y") is None or y_frac < existing_verse["y"]:
                        existing_verse["y"] = y_frac

    page_count = len(doc)
    doc.close()

    meta = EDITION_DEFAULTS.get(
        edition,
        {"id": f"crafted-bsb-{edition}", "pdf": pdf_path.name},
    )
    return {
        "asset": edition,
        "edition": meta["id"],
        "pdf": meta["pdf"],
        "pageCount": page_count,
        "chapters": chapters,
        "verses": verses,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path, help="BSB PDF to index")
    parser.add_argument(
        "--edition",
        default="single-column",
        choices=sorted(EDITION_DEFAULTS),
        help="Crafted BSB asset slug used by the web reader",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("single-column/osis-page-index.json"),
        help="Output JSON path",
    )
    args = parser.parse_args()

    index = build_index(args.pdf, args.edition)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"  pages: {index['pageCount']}")
    print(f"  chapters: {len(index['chapters'])}")
    print(f"  verses: {len(index['verses'])}")


if __name__ == "__main__":
    main()