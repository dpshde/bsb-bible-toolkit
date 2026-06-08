#!/usr/bin/env python3
"""
Download BSB PDF books from bereanbible.com.
"""
import argparse
import requests
import sys
from pathlib import Path

BASE_URL = "https://bereanbible.com/bsb-book-{book}.pdf"

BOOK_NAMES = {
    1: "Genesis", 2: "Exodus", 3: "Leviticus", 4: "Numbers", 5: "Deuteronomy",
    6: "Joshua", 7: "Judges", 8: "Ruth", 9: "1 Samuel", 10: "2 Samuel",
    11: "1 Kings", 12: "2 Kings", 13: "1 Chronicles", 14: "2 Chronicles",
    15: "Ezra", 16: "Nehemiah", 17: "Esther", 18: "Job", 19: "Psalms",
    20: "Proverbs", 21: "Ecclesiastes", 22: "Song of Solomon", 23: "Isaiah",
    24: "Jeremiah", 25: "Lamentations", 26: "Ezekiel", 27: "Daniel",
    28: "Hosea", 29: "Joel", 30: "Amos", 31: "Obadiah", 32: "Jonah",
    33: "Micah", 34: "Nahum", 35: "Habakkuk", 36: "Zephaniah",
    37: "Haggai", 38: "Zechariah", 39: "Malachi", 40: "Matthew",
    41: "Mark", 42: "Luke", 43: "John", 44: "Acts", 45: "Romans",
    46: "1 Corinthians", 47: "2 Corinthians", 48: "Galatians",
    49: "Ephesians", 50: "Philippians", 51: "Colossians",
    52: "1 Thessalonians", 53: "2 Thessalonians", 54: "1 Timothy",
    55: "2 Timothy", 56: "Titus", 57: "Philemon", 58: "Hebrews",
    59: "James", 60: "1 Peter", 61: "2 Peter", 62: "1 John",
    63: "2 John", 64: "3 John", 65: "Jude", 66: "Revelation",
}


def download_book(book_num: int, output_dir: Path = Path(".")) -> Path:
    url = BASE_URL.format(book=book_num)
    name = BOOK_NAMES.get(book_num, f"book-{book_num}")
    output_path = output_dir / f"bsb-book-{book_num}.pdf"

    print(f"Downloading {name} (book {book_num})...")
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)

    size_mb = output_path.stat().st_size / 1_048_576
    print(f"  Saved to {output_path} ({size_mb:.1f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Download BSB PDF books")
    parser.add_argument("--book", type=int, help="Book number (1-66)")
    parser.add_argument("--books", type=str, help="Comma-separated book numbers, e.g. 1,2,3")
    parser.add_argument("--all", action="store_true", help="Download all 66 books")
    parser.add_argument("--list", action="store_true", help="List available books")
    parser.add_argument("--output-dir", type=Path, default=Path("."), help="Output directory")
    args = parser.parse_args()

    if args.list:
        for num, name in BOOK_NAMES.items():
            print(f"  {num:2d}  {name}")
        sys.exit(0)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    books = []
    if args.all:
        books = list(range(1, 67))
    elif args.books:
        books = [int(b.strip()) for b in args.books.split(",")]
    elif args.book:
        books = [args.book]
    else:
        parser.print_help()
        sys.exit(1)

    for b in books:
        try:
            download_book(b, args.output_dir)
        except Exception as e:
            print(f"  ERROR downloading book {b}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
