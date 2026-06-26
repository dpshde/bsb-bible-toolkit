#!/usr/bin/env python3
"""Generate Bible audiobook audio via ElevenLabs TTS API.

One API call per chapter. The model handles pacing and prosody naturally.
Chapters over 5000 characters are split at sentence boundaries.

Features:
  - Per-book output folders
  - Checkpointing (resume after interruption)
  - Dry-run mode for cost estimation

Requirements:
  - pip install requests

Usage:
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Philippians
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Philippians --dry-run
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --all
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

import requests

DEFAULT_JSONL = os.path.expanduser("~/Downloads/bsb.jsonl")
DEFAULT_VOICE_ID = "pqHfZKP75CvOlQylNhV4"
DEFAULT_MODEL_ID = "eleven_flash_v2_5"
DEFAULT_OUT_DIR = Path("output/elevenlabs_audio")
TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
MAX_CHARS_PER_REQUEST = 4900
RATE_LIMIT_DELAY = 0.3
MAX_RETRIES = 3


def load_bible(jsonl_path):
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
            bible[book][chapter].append(v)
    return bible


def slugify(value):
    return value.lower().replace(" ", "_").replace(".", "").replace(",", "").replace("-", "_")


def get_headers(api_key):
    return {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }


def split_long_text(text, max_chars=MAX_CHARS_PER_REQUEST):
    """Split text at sentence boundaries if it exceeds max_chars."""
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current = ""
    for sent in sentences:
        if len(current) + len(sent) + 1 > max_chars:
            if current:
                chunks.append(current.strip())
            current = sent
        else:
            current += " " + sent if current else sent
    if current.strip():
        chunks.append(current.strip())
    return chunks


def generate_tts(api_key, voice_id, model_id, text, output_path):
    """Generate TTS audio and save as MP3."""
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.post(
                TTS_URL.format(voice_id=voice_id),
                headers=get_headers(api_key),
                json=payload,
                timeout=120,
            )
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return True
            elif res.status_code == 429:
                wait = int(res.headers.get("Retry-After", 5))
                print(f"      rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"      API error {res.status_code}: {res.text[:200]}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
        except requests.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"      retry {attempt + 1}: {e}")
                time.sleep(2 ** attempt)
    return False


def generate_chapter(api_key, voice_id, model_id, book_name, chapter_num,
                     verses, out_dir, dry_run):
    """Generate audio for a single chapter."""
    book_slug = slugify(book_name)
    chapter_slug = f"chapter_{chapter_num:02d}"
    chapter_dir = out_dir / book_slug
    chapter_dir.mkdir(parents=True, exist_ok=True)

    mp3_path = chapter_dir / f"{book_slug}_{chapter_slug}.mp3"
    checkpoint_path = chapter_dir / f".checkpoint_{chapter_slug}.json"
    checkpoint = load_checkpoint(checkpoint_path)

    chapter_title = f"{book_name} - Chapter {chapter_num}"

    if checkpoint.get("complete") and mp3_path.exists():
        print(f"  {chapter_title} - already done")
        return True

    # Build full chapter text: header + verses
    verse_texts = [v["text"] for v in verses]
    full_text = " ".join(verse_texts)

    if dry_run:
        print(f"  {chapter_title} - DRY RUN ({len(verses)} verses, {len(full_text)} chars)")
        return True

    print(f"  {chapter_title} - generating ({len(verses)} verses, {len(full_text)} chars)...")

    # Generate header separately for a clean pause after the title
    header_text = f"{book_name}. Chapter {chapter_num}."
    header_file = chapter_dir / f".{chapter_slug}_header.mp3"

    if not (checkpoint.get("header") and header_file.exists()):
        if not generate_tts(api_key, voice_id, model_id, header_text, header_file):
            print(f"    header: FAILED")
            return False
        checkpoint["header"] = True
        save_checkpoint(checkpoint_path, checkpoint)
        time.sleep(RATE_LIMIT_DELAY)

    chunks = split_long_text(full_text)
    if len(chunks) > 1:
        print(f"    splitting into {len(chunks)} parts...")

    chunk_files = []
    for ci, chunk in enumerate(chunks):
        chunk_key = f"chunk_{ci}"
        chunk_file = chapter_dir / f".{chapter_slug}_part_{ci:02d}.mp3"

        if checkpoint.get(chunk_key) and chunk_file.exists():
            chunk_files.append(chunk_file)
            continue

        if not generate_tts(api_key, voice_id, model_id, chunk, chunk_file):
            print(f"    part {ci}: FAILED")
            return False

        chunk_files.append(chunk_file)
        checkpoint[chunk_key] = True
        save_checkpoint(checkpoint_path, checkpoint)
        time.sleep(RATE_LIMIT_DELAY)

    # Final assembly: header + silence + body chunks
    import subprocess

    # Generate 1.5s silence file
    silence_file = chapter_dir / f".{chapter_slug}_silence.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
         "-t", "1.5", "-q:a", "9", str(silence_file)],
        capture_output=True, check=True,
    )

    all_parts = [header_file, silence_file] + chunk_files

    all_parts = [header_file, silence_file] + chunk_files
    concat_mp3s(all_parts, mp3_path)

    # Clean up temp files
    silence_file.unlink(missing_ok=True)
    for cf in chunk_files:
        cf.unlink(missing_ok=True)

    checkpoint["complete"] = True
    save_checkpoint(checkpoint_path, checkpoint)

    size_mb = mp3_path.stat().st_size / (1024 * 1024)
    print(f"    done: {mp3_path.name} ({size_mb:.1f} MB)")
    return True


def concat_mp3s(parts, output_path):
    """Concatenate MP3 files using ffmpeg."""
    list_file = output_path.with_suffix(".concat.txt")
    with open(list_file, "w") as f:
        for pf in parts:
            f.write(f"file '{pf.resolve()}'\n")
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(output_path)],
        capture_output=True, check=True,
    )
    list_file.unlink(missing_ok=True)


def load_checkpoint(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_checkpoint(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def generate_book(api_key, voice_id, model_id, book_name, chapters,
                  out_dir, dry_run):
    total_verses = sum(len(v) for v in chapters.values())
    total_chars = sum(
        len(v["text"]) for ch_verses in chapters.values() for v in ch_verses
    )
    print(f"\n{book_name}: {len(chapters)} chapters, {total_verses} verses, {total_chars:,} chars")

    for ch_num in sorted(chapters.keys()):
        if not generate_chapter(
            api_key, voice_id, model_id, book_name, ch_num,
            chapters[ch_num], out_dir, dry_run
        ):
            print(f"  FAILED at {book_name} chapter {ch_num}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate Bible audiobook audio via ElevenLabs TTS"
    )
    parser.add_argument("--api-key", required=True, help="ElevenLabs API key")
    parser.add_argument("--jsonl", default=DEFAULT_JSONL, help="Path to BSB JSONL file")
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID, help="Voice ID")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="TTS model ID")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--book", help="Generate a single book (e.g. 'Philippians')")
    parser.add_argument("--all", action="store_true", help="Generate the entire Bible")
    parser.add_argument("--dry-run", action="store_true", help="Show cost estimate")
    args = parser.parse_args()

    if not args.book and not args.all:
        parser.error("Specify --book <name> or --all")

    print(f"Loading Bible from {args.jsonl}...")
    bible = load_bible(args.jsonl)
    print(f"Loaded {len(bible)} books")

    out_dir = Path(args.out_dir)

    if args.book:
        if args.book not in bible:
            parser.error(f"Book '{args.book}' not found. Available: {', '.join(sorted(bible.keys()))}")
        generate_book(args.api_key, args.voice_id, args.model_id, args.book,
                      bible[args.book], out_dir, args.dry_run)
    elif args.all:
        for book_name in sorted(bible.keys()):
            if not generate_book(args.api_key, args.voice_id, args.model_id, book_name,
                                 bible[book_name], out_dir, args.dry_run):
                print(f"\nStopped at {book_name}")
                break

    print("\nDone!")


if __name__ == "__main__":
    main()
