#!/usr/bin/env python3
"""
Add clickable OSIS verse-range links to BSB PDF section headings.

Each heading is linked to the exact verse range it covers (e.g.,
https://route.bible/Gen.1.1-5 instead of the full chapter).

Verse numbers are detected by their small Cambria-Bold font (~6.8pt).
Two-column reading order is reconstructed so verse ranges are accurate
across left/right column boundaries.
"""

import sys
import fitz

# ---------------------------------------------------------------------------
# Chapter verse counts for all 66 books (standard Protestant canon)
# ---------------------------------------------------------------------------
CHAPTER_VERSE_COUNTS = {
    "Gen": [31, 25, 24, 26, 32, 22, 24, 22, 29, 32, 32, 20, 18, 24, 21, 16, 27, 33, 38, 18, 34, 24, 20, 67, 34, 35, 46, 22, 35, 43, 55, 32, 20, 31, 29, 43, 36, 30, 23, 23, 57, 38, 34, 34, 28, 34, 31, 22, 33, 26],
    "Exod": [22, 25, 22, 31, 23, 30, 25, 32, 35, 29, 10, 51, 22, 31, 27, 36, 16, 27, 25, 26, 36, 31, 33, 18, 40, 37, 21, 43, 46, 38, 18, 35, 23, 35, 35, 38, 29, 31, 43, 38],
    "Lev": [17, 16, 17, 35, 26, 23, 38, 36, 24, 20, 47, 8, 59, 57, 33, 34, 16, 30, 37, 27, 24, 33, 44, 23, 55, 46, 34],
    "Num": [54, 34, 51, 49, 31, 27, 89, 26, 23, 36, 35, 16, 33, 45, 41, 50, 13, 28, 22, 29, 35, 41, 30, 25, 18, 65, 23, 31, 39, 17, 54, 42, 56, 29, 34, 13],
    "Deut": [46, 37, 29, 49, 33, 25, 26, 20, 29, 22, 32, 31, 19, 29, 23, 22, 20, 22, 21, 20, 23, 29, 26, 22, 19, 19, 26, 69, 28, 20, 30, 52, 29, 12],
    "Josh": [18, 24, 17, 24, 15, 27, 26, 35, 27, 43, 23, 24, 33, 15, 63, 10, 18, 28, 51, 9, 45, 34, 16, 33],
    "Judg": [36, 23, 31, 24, 31, 40, 25, 35, 57, 18, 40, 15, 25, 20, 20, 31, 13, 31, 30, 48, 25],
    "Ruth": [22, 23, 18, 22],
    "1Sam": [28, 36, 21, 22, 12, 21, 17, 22, 27, 27, 15, 25, 23, 52, 35, 23, 58, 30, 24, 42, 16, 23, 28, 23, 44, 25, 12, 25, 11, 31, 13],
    "2Sam": [27, 32, 39, 12, 25, 23, 29, 18, 13, 19, 27, 31, 39, 33, 37, 23, 29, 33, 43, 26, 22, 51, 39, 25],
    "1Kgs": [53, 46, 28, 34, 18, 38, 51, 66, 28, 29, 43, 33, 34, 31, 34, 34, 24, 46, 21, 43, 29, 54],
    "2Kgs": [18, 25, 27, 44, 27, 33, 20, 29, 37, 36, 21, 21, 25, 29, 38, 20, 41, 37, 37, 21, 26, 20, 37, 20, 30],
    "1Chr": [54, 55, 24, 43, 26, 81, 40, 40, 44, 14, 47, 40, 14, 17, 29, 43, 27, 17, 19, 8, 30, 19, 32, 31, 31, 32, 34, 21, 30],
    "2Chr": [17, 18, 17, 22, 14, 42, 22, 18, 31, 19, 23, 16, 22, 15, 19, 14, 19, 34, 11, 37, 20, 12, 21, 27, 28, 23, 9, 27, 36, 27, 21, 33, 25, 33, 27, 23],
    "Ezra": [11, 70, 13, 24, 17, 22, 28, 36, 15, 44],
    "Neh": [11, 20, 31, 23, 19, 19, 73, 18, 38, 39, 36, 47, 31],
    "Esth": [22, 23, 15, 17, 14, 14, 10, 17, 32, 3],
    "Job": [22, 13, 26, 21, 27, 30, 21, 22, 35, 22, 20, 25, 28, 22, 35, 22, 16, 21, 29, 29, 34, 30, 17, 25, 6, 14, 23, 28, 25, 31, 40, 22, 33, 37, 16, 33, 24, 41, 30, 24, 34, 17],
    "Ps": [6, 12, 9, 9, 13, 11, 18, 10, 21, 18, 7, 9, 6, 7, 5, 11, 15, 51, 15, 10, 14, 32, 6, 10, 22, 12, 14, 9, 11, 13, 25, 11, 22, 23, 28, 13, 40, 23, 14, 18, 14, 12, 5, 27, 18, 12, 10, 15, 21, 23, 21, 11, 7, 9, 24, 14, 12, 12, 18, 14, 9, 13, 12, 11, 14, 20, 8, 36, 37, 6, 24, 20, 28, 23, 11, 13, 21, 72, 13, 20, 17, 8, 19, 13, 14, 17, 7, 19, 53, 17, 16, 16, 5, 23, 11, 13, 12, 9, 9, 5, 8, 29, 22, 35, 45, 48, 43, 14, 31, 7, 10, 10, 9, 8, 18, 19, 2, 29, 176, 7, 8, 9, 4, 8, 5, 6, 5, 6, 8, 8, 3, 18, 3, 3, 21, 26, 9, 8, 24, 14, 10, 8, 12, 15, 21, 10, 20, 14, 9, 6],
    "Prov": [33, 22, 35, 27, 23, 35, 27, 36, 18, 32, 31, 28, 25, 35, 33, 33, 28, 24, 29, 30, 31, 29, 35, 34, 28, 28, 27, 28, 27, 33, 31],
    "Eccl": [18, 26, 22, 17, 19, 12, 29, 17, 18, 20, 10, 14],
    "Song": [17, 17, 11, 16, 16, 12, 14, 14],
    "Isa": [31, 22, 26, 6, 30, 13, 25, 23, 20, 34, 16, 6, 22, 32, 9, 14, 14, 7, 25, 6, 17, 25, 18, 23, 12, 21, 13, 29, 24, 33, 9, 20, 24, 17, 10, 22, 38, 22, 8, 31, 29, 25, 28, 28, 25, 13, 15, 22, 26, 11, 23, 15, 12, 17, 13, 12, 21, 14, 21, 22, 11, 12, 19, 12, 25, 24],
    "Jer": [19, 37, 25, 31, 31, 30, 34, 23, 25, 25, 23, 17, 27, 22, 21, 21, 27, 23, 15, 18, 14, 30, 40, 10, 38, 24, 22, 17, 32, 24, 40, 44, 26, 22, 19, 32, 21, 28, 18, 16, 18, 22, 13, 30, 5, 28, 7, 47, 39, 46, 64, 34],
    "Lam": [22, 22, 66, 22, 22],
    "Ezek": [28, 10, 27, 17, 17, 14, 27, 18, 11, 22, 25, 28, 23, 23, 8, 63, 24, 32, 14, 44, 37, 31, 49, 27, 17, 21, 36, 26, 21, 26, 18, 32, 33, 31, 15, 38, 28, 23, 29, 49, 26, 20, 27, 31, 25, 24, 23, 35],
    "Dan": [21, 49, 33, 34, 30, 29, 28, 27, 27, 21, 45, 13],
    "Hos": [11, 23, 5, 19, 15, 11, 16, 14, 17, 15, 12, 14, 16, 9],
    "Joel": [20, 32, 21],
    "Amos": [15, 16, 15, 13, 27, 14, 17, 14, 15],
    "Obad": [21],
    "Jonah": [17, 10, 10, 11],
    "Mic": [16, 13, 12, 13, 15, 16, 20],
    "Nah": [15, 13, 19],
    "Hab": [17, 20, 19],
    "Zeph": [18, 15, 20],
    "Hag": [15, 23],
    "Zech": [21, 13, 10, 14, 11, 15, 14, 23, 17, 12, 17, 14, 9, 21],
    "Mal": [14, 17, 18, 6],
    "Matt": [25, 23, 17, 25, 48, 34, 29, 34, 38, 42, 30, 50, 58, 36, 39, 28, 27, 35, 30, 34, 46, 46, 39, 51, 46, 75, 66, 20],
    "Mark": [45, 28, 35, 41, 43, 56, 37, 38, 50, 52, 33, 44, 37, 72, 47, 20],
    "Luke": [80, 52, 38, 44, 39, 49, 50, 56, 62, 42, 54, 59, 35, 35, 32, 31, 37, 43, 48, 47, 38, 71, 56, 53],
    "John": [51, 25, 36, 54, 47, 71, 53, 59, 41, 42, 57, 50, 38, 31, 27, 33, 26, 40, 42, 31, 25],
    "Acts": [26, 47, 26, 37, 42, 15, 60, 40, 43, 48, 30, 25, 52, 28, 41, 40, 34, 28, 41, 38, 40, 30, 35, 27, 27, 32, 44, 31],
    "Rom": [32, 29, 31, 25, 21, 23, 25, 39, 33, 21, 36, 21, 14, 23, 33, 27],
    "1Cor": [31, 16, 23, 21, 13, 20, 40, 13, 27, 33, 34, 31, 13, 40, 58, 24],
    "2Cor": [24, 17, 18, 18, 21, 18, 16, 24, 15, 18, 33, 21, 14],
    "Gal": [24, 21, 29, 31, 26, 18],
    "Eph": [23, 22, 21, 32, 33, 24],
    "Phil": [30, 30, 21, 23],
    "Col": [29, 23, 25, 18],
    "1Thess": [10, 20, 13, 18, 28],
    "2Thess": [12, 17, 18],
    "1Tim": [20, 15, 16, 16, 25, 21],
    "2Tim": [18, 26, 17, 22],
    "Titus": [16, 15, 15],
    "Phlm": [25],
    "Heb": [14, 18, 19, 16, 14, 20, 28, 13, 28, 39, 40, 29, 25],
    "Jas": [27, 26, 18, 17, 20],
    "1Pet": [25, 25, 22, 19, 14],
    "2Pet": [21, 22, 18],
    "1John": [10, 29, 24, 21, 21],
    "2John": [13],
    "3John": [14],
    "Jude": [25],
    "Rev": [20, 29, 22, 11, 14, 17, 17, 13, 21, 11, 19, 17, 18, 20, 8, 21, 18, 24, 21, 15, 27, 21],
}


# ---------------------------------------------------------------------------
# BSB book names → OSIS
# ---------------------------------------------------------------------------
OSIS_BOOKS = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deut", "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth",
    "1 Samuel": "1Sam", "2 Samuel": "2Sam", "1 Kings": "1Kgs", "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr", "2 Chronicles": "2Chr", "Ezra": "Ezra", "Nehemiah": "Neh",
    "Esther": "Esth", "Job": "Job", "Psalms": "Ps", "Proverbs": "Prov",
    "Ecclesiastes": "Eccl", "Song of Solomon": "Song", "Isaiah": "Isa", "Jeremiah": "Jer",
    "Lamentations": "Lam", "Ezekiel": "Ezek", "Daniel": "Dan", "Hosea": "Hos",
    "Joel": "Joel", "Amos": "Amos", "Obadiah": "Obad", "Jonah": "Jonah",
    "Micah": "Mic", "Nahum": "Nah", "Habakkuk": "Hab", "Zephaniah": "Zeph",
    "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal", "Matthew": "Matt",
    "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1Cor", "2 Corinthians": "2Cor", "Galatians": "Gal",
    "Ephesians": "Eph", "Philippians": "Phil", "Colossians": "Col", "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess", "1 Timothy": "1Tim", "2 Timothy": "2Tim", "Titus": "Titus",
    "Philemon": "Phlm", "Hebrews": "Heb", "James": "Jas", "1 Peter": "1Pet",
    "2 Peter": "2Pet", "1 John": "1John", "2 John": "2John", "3 John": "3John",
    "Jude": "Jude", "Revelation": "Rev",
}


def get_osis_book(name):
    return OSIS_BOOKS.get(name)


def get_chapter_verse_count(osis, chapter):
    """Return the number of verses in the given chapter."""
    if osis not in CHAPTER_VERSE_COUNTS:
        return None
    counts = CHAPTER_VERSE_COUNTS[osis]
    idx = chapter - 1
    if 0 <= idx < len(counts):
        return counts[idx]
    return None


# ---------------------------------------------------------------------------
# Span classification
# ---------------------------------------------------------------------------
def is_verse_number(span, page_height):
    """Detect inline verse numbers (small bold digits in main text)."""
    text = span.get("text", "").strip()
    font = span.get("font", "")
    size = span.get("size", 0)
    y = span.get("bbox", [0, 0, 0, 0])[1]

    if not text.isdigit():
        return False
    if size >= 8.5:
        return False
    if "Cambria-Bold" not in font:
        return False
    # Exclude footnote area (bottom ~45 points of page)
    if y > page_height - 45:
        return False
    return True


def is_heading(span):
    """Detect section headings (Cambria-Bold/Italic, ~9pt)."""
    text = span.get("text", "").strip()
    font = span.get("font", "")
    size = span.get("size", 0)

    if not text:
        return False
    if "|" in text:
        return False
    if size < 8.5 or size > 10.0:
        return False
    if "Cambria-Bold" not in font and "Cambria-Italic" not in font:
        return False
    
    # Exclude cross-references in Cambria-Italic that contain colons
    # or are just punctuation
    if "Cambria-Italic" in font:
        if ":" in text or text in (";", "–", "—"):
            return False
    
    return True


def is_chapter_number(span):
    """Detect chapter numbers (Cambria-Bold, ~15-30pt, single digit)."""
    text = span.get("text", "").strip()
    font = span.get("font", "")
    size = span.get("size", 0)

    if not text.isdigit():
        return False
    if size < 15.0 or size > 30.0:
        return False
    if "Cambria-Bold" not in font:
        return False
    return True


def is_book_title(span):
    """Detect book titles (Cambria-Bold, ~24-35pt)."""
    text = span.get("text", "").strip()
    font = span.get("font", "")
    size = span.get("size", 0)

    if not text:
        return False
    if size < 24.0 or size > 35.0:
        return False
    if "Cambria-Bold" not in font and "Cambria-Italic" not in font:
        return False
    return True


def extract_spans(doc):
    """
    Extract all text spans from all pages in proper two-column reading order.
    Returns a list of span dictionaries.
    """
    all_spans = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_height = page.rect.height
        page_width = page.rect.width
        split_x = page_width / 2

        blocks = page.get_text("dict")["blocks"]
        page_spans = []
        for b in blocks:
            if "lines" not in b:
                continue
            for line in b["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text:
                        continue
                    bbox = span["bbox"]
                    page_spans.append({
                        "page": page_num,
                        "text": text,
                        "font": span["font"],
                        "size": span["size"],
                        "bbox": bbox,
                        "x": bbox[0],
                        "y": bbox[1],
                        "page_height": page_height,
                        "page_width": page_width,
                        "column": 0 if bbox[0] < split_x else 1,
                    })

        # Sort by column, then by y (top to bottom), then by x
        page_spans.sort(key=lambda s: (s["column"], s["y"], s["x"]))
        all_spans.extend(page_spans)

    return all_spans


def build_event_list(spans):
    """
    Build a chronological event list from spans in reading order.
    Each event is a dict with: type, page, bbox, text, osis, chapter, verse, column.
    """
    events = []
    current_osis = None
    current_chapter = None
    current_verse = None
    chapters_seen = set()

    for span in spans:
        page_num = span["page"]
        text = span["text"]
        page_height = span["page_height"]

        if is_book_title(span):
            osis = get_osis_book(text)
            if osis:
                current_osis = osis
                current_chapter = None
                current_verse = None
                chapters_seen.clear()
                events.append({
                    "type": "book",
                    "page": page_num,
                    "bbox": span["bbox"],
                    "text": text,
                    "osis": current_osis,
                    "chapter": None,
                    "verse": None,
                    "column": span["column"],
                })

        elif is_chapter_number(span):
            chapter = int(text)
            current_chapter = chapter
            current_verse = None
            events.append({
                "type": "chapter",
                "page": page_num,
                "bbox": span["bbox"],
                "text": text,
                "osis": current_osis,
                "chapter": current_chapter,
                "verse": None,
                "column": span["column"],
            })
            
            # Look backward for headings on the same page that are in the
            # same column or a column that is read before this column.
            for j in range(len(events) - 2, -1, -1):
                prev_event = events[j]
                if prev_event["type"] != "heading":
                    continue
                if prev_event["page"] != page_num:
                    break
                if prev_event["bbox"][1] >= span["bbox"][1]:
                    continue
                if prev_event.get("column") < span["column"]:
                    # Heading is in a column that is read before this column
                    prev_event["chapter"] = chapter
                    prev_event["osis"] = current_osis
                    break
                elif prev_event.get("column") == span["column"]:
                    # Heading is in the same column and before the chapter
                    prev_event["chapter"] = chapter
                    prev_event["osis"] = current_osis
                    break

        elif is_verse_number(span, page_height):
            verse = int(text)
            current_verse = verse
            events.append({
                "type": "verse",
                "page": page_num,
                "bbox": span["bbox"],
                "text": text,
                "osis": current_osis,
                "chapter": current_chapter,
                "verse": current_verse,
                "column": span["column"],
            })

        elif is_heading(span):
            # Determine if this is the first heading in this chapter
            key = (current_osis, current_chapter)
            is_first = key not in chapters_seen
            if is_first:
                chapters_seen.add(key)

            events.append({
                "type": "heading",
                "page": page_num,
                "bbox": span["bbox"],
                "text": text,
                "osis": current_osis,
                "chapter": current_chapter,
                "verse": None,
                "column": span["column"],
                "is_first_in_chapter": is_first,
            })

    return events


def find_heading_ranges(events):
    """
    For each heading event, compute the exact OSIS verse range.
    Returns a list of (event_index, start_verse, end_verse) tuples.
    """
    results = []

    for i, event in enumerate(events):
        if event["type"] != "heading":
            continue

        osis = event["osis"]
        chapter = event["chapter"]
        if not osis or chapter is None:
            continue

        is_first = event.get("is_first_in_chapter", False)

        # Find start verse: first verse number after this heading
        start_verse = None
        for j in range(i + 1, len(events)):
            next_event = events[j]
            if next_event["type"] == "verse":
                start_verse = next_event["verse"]
                break
            elif next_event["type"] in ("chapter", "book"):
                break

        # If this is the first heading in the chapter and the first verse
        # number after it is 2, the section starts at verse 1 (the first
        # verse of a chapter is unnumbered in the BSB).
        if is_first and start_verse == 2:
            start_verse = 1

        # Find end verse: last verse number before the next heading,
        # chapter, or book in the same chapter.
        end_verse = None
        for j in range(i + 1, len(events)):
            next_event = events[j]
            if next_event["type"] == "book":
                # Reached end of this book
                break
            elif next_event["type"] == "chapter":
                # If it's the same chapter, skip it (chapter number is just a marker)
                if next_event["chapter"] == event["chapter"]:
                    continue
                # Reached a new chapter
                break
            elif next_event["type"] == "heading":
                # Found next heading in same chapter — end verse is the
                # verse number immediately before this next heading.
                for k in range(j - 1, i, -1):
                    if events[k]["type"] == "verse":
                        end_verse = events[k]["verse"]
                        break
                break

        # If no next heading found, this is the last heading in the chapter.
        # Use the chapter's total verse count.
        if end_verse is None:
            end_verse = get_chapter_verse_count(osis, chapter)

        # Sanity check
        if start_verse is None:
            start_verse = 1
        if end_verse is None:
            end_verse = start_verse

        # Ensure start <= end
        if start_verse > end_verse:
            start_verse = end_verse

        results.append((i, start_verse, end_verse))

    return results


def build_url(osis, chapter, start_verse, end_verse):
    """Build the route.bible URL for a verse range."""
    if start_verse == end_verse:
        return f"https://route.bible/{osis}.{chapter}.{start_verse}"
    return f"https://route.bible/{osis}.{chapter}.{start_verse}-{end_verse}"


def add_heading_links(doc, events, heading_ranges):
    """Add clickable verse-range links to section headings."""
    link_count = 0
    for idx, start_verse, end_verse in heading_ranges:
        event = events[idx]
        page_num = event["page"]
        bbox = event["bbox"]
        osis = event["osis"]
        chapter = event["chapter"]

        if not osis or chapter is None:
            continue

        url = build_url(osis, chapter, start_verse, end_verse)
        page = doc[page_num]
        link_rect = fitz.Rect(bbox)
        page.insert_link({
            "kind": fitz.LINK_URI,
            "from": link_rect,
            "uri": url,
        })
        link_count += 1
    return link_count


def add_chapter_links(doc, events):
    """Add clickable full-chapter links to chapter numbers and book titles."""
    link_count = 0
    for event in events:
        etype = event["type"]
        page_num = event["page"]
        bbox = event["bbox"]
        osis = event["osis"]
        chapter = event["chapter"]

        if not osis:
            continue

        page = doc[page_num]
        link_rect = fitz.Rect(bbox)

        if etype == "chapter":
            if chapter is None:
                continue
            url = f"https://route.bible/{osis}.{chapter}"
            page.insert_link({
                "kind": fitz.LINK_URI,
                "from": link_rect,
                "uri": url,
            })
            link_count += 1

        elif etype == "book":
            # Link book title to chapter 1 of that book
            url = f"https://route.bible/{osis}.1"
            page.insert_link({
                "kind": fitz.LINK_URI,
                "from": link_rect,
                "uri": url,
            })
            link_count += 1

    return link_count


def add_links(doc, events, heading_ranges):
    """Add all clickable links (headings + chapters + books)."""
    heading_links = add_heading_links(doc, events, heading_ranges)
    chapter_links = add_chapter_links(doc, events)
    return heading_links + chapter_links


def main():
    if len(sys.argv) < 3:
        print("Usage: python add_route_links.py <input.pdf> <output.pdf>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    print("Opening PDF...")
    doc = fitz.open(input_path)
    total_pages = len(doc)
    print(f"Pages: {total_pages}")

    print("Extracting text spans in reading order...")
    spans = extract_spans(doc)
    print(f"Spans extracted: {len(spans)}")

    print("Building event list...")
    events = build_event_list(spans)
    print(f"Events: {len(events)}")

    # Count headings
    heading_count = sum(1 for e in events if e["type"] == "heading")
    print(f"Headings detected: {heading_count}")

    print("Finding verse ranges for each heading...")
    heading_ranges = find_heading_ranges(events)
    print(f"Ranges computed: {len(heading_ranges)}")

    print("Adding links...")
    link_count = add_links(doc, events, heading_ranges)
    print(f"Links added: {link_count}")

    print("Saving...")
    doc.save(output_path)
    doc.close()
    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
