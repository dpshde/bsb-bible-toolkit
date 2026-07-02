#!/usr/bin/env python3
"""Generate a 365-day Bible reading plan from the BSB JSON API.

The plan walks every chapter of every book in canonical order and chunks the
1,189 chapters into 365 roughly-equal readings. Output is printed as JSON to
stdout (pipe to a file or another program).

    python3 reading_plan.py                  # use local wrangler dev
    python3 reading_plan.py --base https://bsb.workers.dev > plan.json
    python3 reading_plan.py --days 260       # fewer, longer readings

The plan is pure metadata (book + chapter ranges). Verse text is fetched from
the API at read time, so the plan itself is tiny and can be embedded in apps.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE = "http://localhost:8787"
DEFAULT_DAYS = 365


def get_json(base: str, path: str) -> object:
    url = base.rstrip("/") + "/" + path.lstrip("/")
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach {url}. Is the Worker running? ({exc.reason})"
        ) from exc


def fetch_book_catalog(base: str) -> list[dict]:
    books = get_json(base, "/v1/books")
    if not isinstance(books, list):
        raise RuntimeError("Unexpected /v1/books response (expected an array)")
    return books


def build_chapter_list(books: list[dict]) -> list[dict]:
    """Return a flat list of {osis, book, chapter} in canonical order."""
    chapters: list[dict] = []
    for book in books:
        osis = book["osis"]
        name = book["name"]
        for ch in range(1, int(book["chapters"]) + 1):
            chapters.append({"osis": osis, "book": name, "chapter": ch})
    return chapters


def chunk(seq: list, groups: int) -> list[list]:
    """Split a sequence into `groups` contiguous chunks of roughly equal size."""
    if groups <= 0:
        raise ValueError("groups must be positive")
    n = len(seq)
    base, extra = divmod(n, groups)
    out: list[list] = []
    start = 0
    for i in range(groups):
        size = base + (1 if i < extra else 0)
        out.append(seq[start : start + size])
        start += size
    return out


def build_reading_plan(books: list[dict], days: int) -> list[dict]:
    chapters = build_chapter_list(books)
    if days > len(chapters):
        raise ValueError(
            f"days ({days}) exceeds total chapter count ({len(chapters)})"
        )
    chunks = chunk(chapters, days)
    plan: list[dict] = []
    for day_index, chunk_chapters in enumerate(chunks, start=1):
        first = chunk_chapters[0]
        last = chunk_chapters[-1]
        # Group contiguous chapters from the same book into a range label.
        if first["osis"] == last["osis"] and len(chunk_chapters) > 1:
            label = f"{first['book']} {first['chapter']}-{last['chapter']}"
        elif len(chunk_chapters) == 1:
            label = f"{first['book']} {first['chapter']}"
        else:
            label = f"{first['book']} {first['chapter']} - {last['book']} {last['chapter']}"
        plan.append(
            {
                "day": day_index,
                "label": label,
                "chapters": chunk_chapters,
            }
        )
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a 365-day BSB reading plan")
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=DEFAULT_DAYS,
        help=f"Number of reading days (default: {DEFAULT_DAYS})",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print the JSON output",
    )
    args = parser.parse_args(argv)

    try:
        books = fetch_book_catalog(args.base)
        plan = build_reading_plan(books, args.days)
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    indent = 2 if args.pretty else None
    json.dump(plan, sys.stdout, indent=indent)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
