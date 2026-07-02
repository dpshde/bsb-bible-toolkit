#!/usr/bin/env python3
"""BSB JSON API quickstart.

Fetch a verse, a chapter, and a passage from the BSB JSON API and print the
results. Uses only the Python standard library so it runs anywhere without
extra dependencies. Run it directly:

    python3 python_quickstart.py

You can override the API base URL with the `--base` argument (defaults to the
local wrangler dev server on port 8787). Pass `--base https://bsb.workers.dev`
to hit the deployed Worker.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request


DEFAULT_BASE = "http://localhost:8787"


def get_json(base: str, path: str, params: dict | None = None) -> object:
    """Perform a GET request and return the parsed JSON response."""
    query = ""
    if params:
        query = "?" + urllib.parse.urlencode(params, doseq=True)
    url = base.rstrip("/") + "/" + path.lstrip("/") + query
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Could not reach {url}. Is the Worker running? ({exc.reason})"
        ) from exc


def show_verse(base: str, osis_ref: str) -> None:
    verse = get_json(base, f"/v1/verse/{osis_ref}")
    print(f"=== Verse {osis_ref} ===")
    print(f"{verse['book']} {verse['chapter']}:{verse['verse']}")
    print(verse["text"])
    footnotes = verse.get("footnotes", [])
    if footnotes:
        print(f"Footnotes ({len(footnotes)}):")
        for fn in footnotes:
            note = fn.get("note") or fn.get("text") or ""
            marker = fn.get("marker", "")
            print(f"  [{marker}] {note}")
    crossrefs = verse.get("crossReferences", [])
    if crossrefs:
        print(f"Cross-references ({len(crossrefs)}):")
        for xr in crossrefs[:5]:
            print(f"  -> {xr.get('target')} ({xr.get('source')})")
        if len(crossrefs) > 5:
            print(f"  ...and {len(crossrefs) - 5} more")
    print()


def show_chapter(base: str, osis: str, chapter: int) -> None:
    data = get_json(base, f"/v1/chapter/{osis}/{chapter}")
    verses = data.get("verses", [])
    print(f"=== {osis} chapter {chapter} ({len(verses)} verses) ===")
    for v in verses[:3]:
        print(f"  {v['verse']}. {v['text']}")
    if len(verses) > 3:
        print(f"  ...and {len(verses) - 3} more verses")
    print()


def show_passage(base: str, ref: str) -> None:
    encoded = urllib.parse.quote(ref, safe="")
    data = get_json(base, f"/v1/passage/{encoded}")
    verses = data.get("verses", [])
    print(f"=== Passage: {ref} ({len(verses)} verses) ===")
    for v in verses:
        print(f"  {v['bookOsis']} {v['chapter']}:{v['verse']} - {v['text']}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="BSB JSON API quickstart")
    parser.add_argument(
        "--base",
        default=DEFAULT_BASE,
        help=f"API base URL (default: {DEFAULT_BASE})",
    )
    args = parser.parse_args(argv)

    print(f"Using API base: {args.base}\n")

    try:
        show_verse(args.base, "JHN.3.16")
        show_chapter(args.base, "GEN", 1)
        show_passage(args.base, "John 3:16-18")
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
