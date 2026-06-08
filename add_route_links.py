#!/usr/bin/env python3
"""
Add https://route.bible/<OSIS>.<CHAPTER> links to every BSB section heading.

Detects book titles, chapter numbers, and section headings by font heuristics,
then maps each heading to the correct chapter OSIS reference.
"""
import argparse
import sys
from pathlib import Path
import fitz  # pymupdf

BASE_URL = "https://route.bible/{osis}.{chapter}"

# Map BSB book names to OSIS abbreviations
BOOK_TO_OSIS = {
    "Genesis": "Gen",
    "Exodus": "Exod",
    "Leviticus": "Lev",
    "Numbers": "Num",
    "Deuteronomy": "Deut",
    "Joshua": "Josh",
    "Judges": "Judg",
    "Ruth": "Ruth",
    "1 Samuel": "1Sam",
    "2 Samuel": "2Sam",
    "1 Kings": "1Kgs",
    "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr",
    "2 Chronicles": "2Chr",
    "Ezra": "Ezra",
    "Nehemiah": "Neh",
    "Esther": "Esth",
    "Job": "Job",
    "Psalms": "Ps",
    "Proverbs": "Prov",
    "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song",
    "Isaiah": "Isa",
    "Jeremiah": "Jer",
    "Lamentations": "Lam",
    "Ezekiel": "Ezek",
    "Daniel": "Dan",
    "Hosea": "Hos",
    "Joel": "Joel",
    "Amos": "Amos",
    "Obadiah": "Obad",
    "Jonah": "Jonah",
    "Micah": "Mic",
    "Nahum": "Nah",
    "Habakkuk": "Hab",
    "Zephaniah": "Zeph",
    "Haggai": "Hag",
    "Zechariah": "Zech",
    "Malachi": "Mal",
    "Matthew": "Matt",
    "Mark": "Mark",
    "Luke": "Luke",
    "John": "John",
    "Acts": "Acts",
    "Romans": "Rom",
    "1 Corinthians": "1Cor",
    "2 Corinthians": "2Cor",
    "Galatians": "Gal",
    "Ephesians": "Eph",
    "Philippians": "Phil",
    "Colossians": "Col",
    "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess",
    "1 Timothy": "1Tim",
    "2 Timothy": "2Tim",
    "Titus": "Titus",
    "Philemon": "Phlm",
    "Hebrews": "Heb",
    "James": "Jas",
    "1 Peter": "1Pet",
    "2 Peter": "2Pet",
    "1 John": "1John",
    "2 John": "2John",
    "3 John": "3John",
    "Jude": "Jude",
    "Revelation": "Rev",
}


def is_book_title_span(span: dict) -> bool:
    text = span.get("text", "").strip()
    if not text:
        return False
    font = span.get("font", "")
    size = span.get("size", 0.0)
    if not (28.0 <= size <= 35.0):
        return False
    if "Cambria-Bold" not in font:
        return False
    if text not in BOOK_TO_OSIS:
        return False
    return True


def is_chapter_number_block(block: dict) -> tuple[bool, int, float]:
    """Check if a block is a chapter number. Returns (is_chapter, chapter_num, x)."""
    if "lines" not in block:
        return False, 0, 0.0
    for line in block["lines"]:
        for span in line["spans"]:
            text = span.get("text", "").strip()
            font = span.get("font", "")
            size = span.get("size", 0.0)
            if not (20.0 <= size <= 26.0):
                continue
            if "Cambria-Bold" not in font:
                continue
            if not text.isdigit():
                continue
            return True, int(text), float(block["bbox"][0])
    return False, 0, 0.0


def is_heading_block(block: dict) -> bool:
    if "lines" not in block:
        return False
    for line in block["lines"]:
        for span in line["spans"]:
            text = span.get("text", "").strip()
            font = span.get("font", "")
            size = span.get("size", 0.0)
            if not (8.5 <= size <= 9.5):
                continue
            if "Cambria-Bold" not in font and "Cambria-Italic" not in font:
                continue
            if "|" in text:
                continue
            if len(text) <= 2:
                continue
            return True
    return False


def get_heading_text(block: dict) -> str:
    text = ""
    if "lines" not in block:
        return ""
    for line in block["lines"]:
        for span in line["spans"]:
            text += span.get("text", "")
    return text.strip()


def add_links_to_pdf(input_path: Path, output_path: Path):
    doc = fitz.open(input_path)
    total_links = 0
    current_book = None
    current_chapter = None

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        # Detect book title
        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    if is_book_title_span(span):
                        current_book = span["text"].strip()
                        current_chapter = None
                        print(f"  Book: {current_book}")
                        break

        # Detect chapter number(s) on this page
        chapter_numbers = []
        for block in blocks:
            is_chapter, chapter_num, x = is_chapter_number_block(block)
            if is_chapter:
                y = float(block["bbox"][1])
                chapter_numbers.append((y, x, chapter_num))

        # Sort by reading order (top to bottom, left to right)
        chapter_numbers.sort(key=lambda t: (t[0], t[1]))
        page_chapter = chapter_numbers[0] if chapter_numbers else None

        # Determine previous chapter for this page
        prev_chapter = current_chapter

        if page_chapter:
            _, chapter_x, new_chapter = page_chapter

            # For each heading, determine its chapter
            for block in blocks:
                if not is_heading_block(block):
                    continue

                heading_x = float(block["bbox"][0])
                heading_text = get_heading_text(block)

                if heading_x >= chapter_x:
                    chapter = new_chapter
                else:
                    chapter = prev_chapter if prev_chapter is not None else 1

                if current_book is None:
                    continue

                osis = BOOK_TO_OSIS.get(current_book)
                if osis is None:
                    continue

                url = BASE_URL.format(osis=osis, chapter=chapter)
                bbox = fitz.Rect(block["bbox"])
                lnk = {
                    "kind": fitz.LINK_URI,
                    "from": bbox,
                    "uri": url,
                }
                page.insert_link(lnk)
                total_links += 1

            # Update current chapter to the new chapter
            current_chapter = new_chapter

        else:
            # No chapter number on this page — all headings belong to current chapter
            if current_chapter is None or current_book is None:
                continue

            osis = BOOK_TO_OSIS.get(current_book)
            if osis is None:
                continue

            for block in blocks:
                if not is_heading_block(block):
                    continue

                bbox = fitz.Rect(block["bbox"])
                url = BASE_URL.format(osis=osis, chapter=current_chapter)
                lnk = {
                    "kind": fitz.LINK_URI,
                    "from": bbox,
                    "uri": url,
                }
                page.insert_link(lnk)
                total_links += 1

    doc.save(output_path)
    doc.close()
    print(f"Added {total_links} links to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Add route.bible OSIS chapter links to all BSB section headings"
    )
    parser.add_argument("--input", type=Path, required=True, help="Input BSB PDF")
    parser.add_argument("--output", type=Path, required=True, help="Output PDF")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    add_links_to_pdf(args.input, args.output)


if __name__ == "__main__":
    main()
