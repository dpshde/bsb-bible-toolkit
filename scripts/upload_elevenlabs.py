#!/usr/bin/env python3
"""Upload BSB Bible chapters to ElevenLabs Studio via API.

Reads the BSB JSONL file, groups verses by chapter, creates Studio chapters,
and fills each with verse-by-verse content using the ElevenLabs API.

Auth: Use --token (Firebase bearer token from browser) since the Studio API
requires account whitelisting for xi-api-key access. Get the token via:
  playwriter -s 1 -e 'const t = await page.evaluate(() => { for (let i = 0; i < localStorage.length; i++) { const key = localStorage.key(i); if (key.includes("authUser")) return JSON.parse(localStorage.getItem(key))?.stsTokenManager?.accessToken; } }); console.log(t)'

Features:
  - Bearer token auth (from browser session)
  - Checkpointing (resume after interruption)
  - Rate limiting with retries
  - Dry-run mode for preview

Usage:
  python scripts/upload_elevenlabs.py --token eyJ... --book Jonah
  python scripts/upload_elevenlabs.py --token eyJ... --book Proverbs --dry-run
  python scripts/upload_elevenlabs.py --token eyJ... --all
"""

import argparse
import json
import os
import sys
import time

import requests

DEFAULT_JSONL = os.path.expanduser("~/Downloads/bsb.jsonl")
DEFAULT_PROJECT_ID = "LrEufPZiaSjAcM6TGvFt"
DEFAULT_VOICE_ID = "pqHfZKP75CvOlQylNhV4"
API_BASE = "https://api.elevenlabs.io/v1/studio"
CHECKPOINT_FILE = os.path.expanduser("~/.cache/elevenlabs_upload_checkpoint.json")
RATE_LIMIT_DELAY = 0.5
MAX_RETRIES = 3

TOKEN = None


def headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}",
    }


def load_bible(jsonl_path):
    """Load BSB JSONL and group verses by book -> chapter."""
    bible = {}
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            v = json.loads(line)
            book = v["book"]
            chapter = int(v["chapter"])
            if book not in bible:
                bible[book] = {}
            if chapter not in bible[book]:
                bible[book][chapter] = []
            bible[book][chapter].append(v["text"])
    return bible


def list_chapters(project_id):
    res = requests.get(
        f"{API_BASE}/projects/{project_id}/chapters", headers=headers()
    )
    res.raise_for_status()
    return {ch["name"]: ch["chapter_id"] for ch in res.json()["chapters"]}


def create_chapter(project_id, name):
    res = requests.post(
        f"{API_BASE}/projects/{project_id}/chapters",
        headers=headers(),
        json={"name": name},
    )
    res.raise_for_status()
    return res.json()["chapter"]["chapter_id"]


def update_chapter_content(project_id, chapter_id, verses, voice_id):
    blocks = [
        {"nodes": [{"type": "tts_node", "text": text, "voice_id": voice_id}]}
        for text in verses
    ]
    res = requests.post(
        f"{API_BASE}/projects/{project_id}/chapters/{chapter_id}",
        headers=headers(),
        json={"content": {"blocks": blocks}},
    )
    res.raise_for_status()
    return len(res.json()["chapter"]["content"]["blocks"])


def upload_chapter(project_id, chapter_name, verses, voice_id, existing):
    if chapter_name in existing:
        chapter_id = existing[chapter_name]
    else:
        chapter_id = create_chapter(project_id, chapter_name)
        existing[chapter_name] = chapter_id
        time.sleep(RATE_LIMIT_DELAY)
    return update_chapter_content(project_id, chapter_id, verses, voice_id)


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {}


def save_checkpoint(data):
    os.makedirs(os.path.dirname(CHECKPOINT_FILE), exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def upload_book(project_id, book_name, chapters, voice_id, existing, dry_run=False):
    checkpoint = load_checkpoint()
    total_verses = sum(len(v) for v in chapters.values())
    print(f"\n{book_name}: {len(chapters)} chapters, {total_verses} verses")

    for ch_num in sorted(chapters.keys()):
        verses = chapters[ch_num]
        chapter_name = f"{book_name} - Chapter {ch_num}"
        checkpoint_key = f"{project_id}:{chapter_name}"

        if checkpoint.get(checkpoint_key):
            print(f"  {chapter_name} - skipped (checkpoint)")
            continue

        if dry_run:
            print(f"  {chapter_name} - DRY RUN ({len(verses)} verses)")
            continue

        for attempt in range(MAX_RETRIES):
            try:
                block_count = upload_chapter(
                    project_id, chapter_name, verses, voice_id, existing
                )
                print(f"  {chapter_name} - {block_count} blocks OK")
                checkpoint[checkpoint_key] = True
                save_checkpoint(checkpoint)
                break
            except requests.RequestException as e:
                if attempt < MAX_RETRIES - 1:
                    wait = 2 ** attempt
                    print(f"  {chapter_name} - retry {attempt + 1} in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  {chapter_name} - FAILED: {e}")
                    raise

        time.sleep(RATE_LIMIT_DELAY)


def main():
    global TOKEN
    parser = argparse.ArgumentParser(
        description="Upload BSB Bible chapters to ElevenLabs Studio"
    )
    parser.add_argument(
        "--token", required=True, help="Firebase bearer token from browser session"
    )
    parser.add_argument(
        "--jsonl", default=DEFAULT_JSONL, help="Path to BSB JSONL file"
    )
    parser.add_argument(
        "--project-id", default=DEFAULT_PROJECT_ID, help="Studio project ID"
    )
    parser.add_argument(
        "--voice-id", default=DEFAULT_VOICE_ID, help="Voice ID for TTS nodes"
    )
    parser.add_argument("--book", help="Upload a single book (e.g. 'Jonah')")
    parser.add_argument("--all", action="store_true", help="Upload the entire Bible")
    parser.add_argument("--dry-run", action="store_true", help="Preview without uploading")
    parser.add_argument(
        "--reset-checkpoint", action="store_true", help="Clear checkpoint data"
    )
    args = parser.parse_args()

    if not args.book and not args.all:
        parser.error("Specify --book <name> or --all")

    TOKEN = args.token

    if args.reset_checkpoint:
        if os.path.exists(CHECKPOINT_FILE):
            os.remove(CHECKPOINT_FILE)
        print("Checkpoint cleared.")

    print(f"Loading Bible from {args.jsonl}...")
    bible = load_bible(args.jsonl)
    print(f"Loaded {len(bible)} books")

    existing = {} if args.dry_run else list_chapters(args.project_id)
    print(f"Found {len(existing)} existing chapters in project {args.project_id}")

    if args.book:
        if args.book not in bible:
            available = ", ".join(sorted(bible.keys()))
            parser.error(f"Book '{args.book}' not found. Available: {available}")
        upload_book(
            args.project_id, args.book, bible[args.book], args.voice_id, existing, args.dry_run
        )
    elif args.all:
        for book_name in sorted(bible.keys()):
            upload_book(
                args.project_id, book_name, bible[book_name], args.voice_id, existing, args.dry_run
            )

    print("\nDone!")


if __name__ == "__main__":
    main()
