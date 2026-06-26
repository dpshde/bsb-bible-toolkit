#!/usr/bin/env python3
"""Generate Bible audiobook audio via ElevenLabs TTS API and package for YouTube.

Reads BSB JSONL, generates per-chapter MP3 audio using ElevenLabs TTS,
then wraps each chapter into an MP4 (with cover art) for YouTube upload.

Features:
  - Per-verse generation then ffmpeg concat (natural pacing, resumable)
  - Checkpoint per verse (resume after interruption)
  - MP3 output per chapter (for Spotify/DistroKid)
  - MP4 output per chapter (for YouTube, with cover art image)
  - ID3 metadata embedding
  - Dry-run mode for cost estimation

Requirements:
  - pip install requests
  - ffmpeg (brew install ffmpeg)
  - Cover art image (PNG/JPG) for YouTube videos

Usage:
  # Generate a single book
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Proverbs --cover cover.png

  # Estimate cost without generating
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Proverbs --dry-run

  # Generate the entire Bible
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --all --cover cover.png

  # Resume after interruption (just re-run the same command)
  python scripts/generate_elevenlabs_audio.py --api-key sk_... --book Proverbs --cover cover.png
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

DEFAULT_JSONL = os.path.expanduser("~/Downloads/bsb.jsonl")
DEFAULT_VOICE_ID = "pqHfZKP75CvOlQylNhV4"
DEFAULT_MODEL_ID = "eleven_v3"
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
    return (
        value.lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace(",", "")
        .replace("-", "_")
    )


def get_headers(api_key):
    return {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }


def generate_verse_audio(api_key, voice_id, model_id, text, output_path):
    """Generate TTS audio for a single verse, save as MP3."""
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
                timeout=60,
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


def load_checkpoint(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_checkpoint(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def concat_verse_mp3s(verse_files, output_path):
    """Concatenate verse MP3s into a single chapter MP3 using ffmpeg."""
    list_file = output_path.with_suffix(".concat.txt")
    with open(list_file, "w") as f:
        for vf in verse_files:
            f.write(f"file '{vf.resolve()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    list_file.unlink(missing_ok=True)


def add_silence_between_verses(verse_files, output_path, silence_ms=300):
    """Concat verse MP3s with a short silence between them for natural pacing."""
    if not verse_files:
        return
    if silence_ms <= 0:
        concat_verse_mp3s(verse_files, output_path)
        return

    chapter_dir = output_path.parent
    silence_path = chapter_dir / ".silence.mp3"
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
            "-t", f"{silence_ms / 1000}",
            "-q:a", "9",
            str(silence_path),
        ],
        capture_output=True,
        check=True,
    )

    interleaved = []
    for vf in verse_files:
        interleaved.append(vf)
        interleaved.append(silence_path)
    interleaved.pop()

    list_file = output_path.with_suffix(".concat.txt")
    with open(list_file, "w") as f:
        for vf in interleaved:
            f.write(f"file '{vf.resolve()}'\n")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    list_file.unlink(missing_ok=True)
    silence_path.unlink(missing_ok=True)


def create_youtube_video(mp3_path, cover_path, output_mp4, title, metadata=None):
    """Wrap an MP3 with cover art into an MP4 for YouTube."""
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(cover_path),
        "-i", str(mp3_path),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-metadata", f"title={title}",
    ]
    if metadata:
        for k, v in metadata.items():
            cmd.extend(["-metadata", f"{k}={v}"])
    cmd.append(str(output_mp4))
    subprocess.run(cmd, capture_output=True, check=True)


def embed_id3_tags(mp3_path, title, album, track_num, total_tracks):
    """Embed ID3 metadata tags in MP3."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(mp3_path),
        "-c", "copy",
        "-metadata", f"title={title}",
        "-metadata", f"album={album}",
        "-metadata", f"track={track_num}/{total_tracks}",
        "-metadata", f"artist=Crafted BSB Bible",
        "-metadata", "genre=Audiobook",
    ]
    cmd.append(str(mp3_path))
    subprocess.run(cmd, capture_output=True, check=True)


def generate_chapter(
    api_key, voice_id, model_id, book_name, chapter_num, verses,
    out_dir, cover_path, silence_ms, dry_run
):
    """Generate audio for a single chapter."""
    chapter_slug = f"chapter_{chapter_num:02d}"
    book_slug = slugify(book_name)
    chapter_dir = out_dir / book_slug / chapter_slug
    chapter_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_path = chapter_dir / ".checkpoint.json"
    checkpoint = load_checkpoint(checkpoint_path)

    chapter_title = f"{book_name} - Chapter {chapter_num}"
    album_name = f"{book_name} - BSB Audiobook"
    total_verses = len(verses)

    if checkpoint.get("chapter_complete"):
        print(f"  {chapter_title} - already done")
        return True

    if dry_run:
        char_count = sum(len(v["text"]) for v in verses)
        print(f"  {chapter_title} - DRY RUN ({total_verses} verses, {char_count} chars)")
        return True

    print(f"  {chapter_title} - generating {total_verses} verses...")
    verse_files = []

    for i, verse in enumerate(verses):
        verse_key = str(i)
        verse_file = chapter_dir / f"verse_{i:04d}.mp3"

        if checkpoint.get(verse_key):
            verse_files.append(verse_file)
            continue

        text = verse["text"]
        if len(text) > MAX_CHARS_PER_REQUEST:
            print(f"    verse {i + 1}: too long ({len(text)} chars), splitting...")
            chunks = [
                text[j:j + MAX_CHARS_PER_REQUEST]
                for j in range(0, len(text), MAX_CHARS_PER_REQUEST)
            ]
            chunk_files = []
            for ci, chunk in enumerate(chunks):
                chunk_file = chapter_dir / f"verse_{i:04d}_chunk_{ci:02d}.mp3"
                if generate_verse_audio(api_key, voice_id, model_id, chunk, chunk_file):
                    chunk_files.append(chunk_file)
                    time.sleep(RATE_LIMIT_DELAY)
                else:
                    print(f"    verse {i + 1} chunk {ci}: FAILED")
                    return False
            concat_verse_mp3s(chunk_files, verse_file)
            for cf in chunk_files:
                cf.unlink(missing_ok=True)
        else:
            if not generate_verse_audio(api_key, voice_id, model_id, text, verse_file):
                print(f"    verse {i + 1}: FAILED")
                return False
            time.sleep(RATE_LIMIT_DELAY)

        verse_files.append(verse_file)
        checkpoint[verse_key] = True
        save_checkpoint(checkpoint_path, checkpoint)

    chapter_mp3 = chapter_dir / f"{book_slug}_{chapter_slug}.mp3"
    print(f"    concatenating {len(verse_files)} verses...")
    add_silence_between_verses(verse_files, chapter_mp3, silence_ms)

    track_num = chapter_num
    total_chapters = 999
    try:
        embed_id3_tags(chapter_mp3, chapter_title, album_name, track_num, total_chapters)
    except Exception:
        pass

    if cover_path and cover_path.exists():
        video_mp4 = chapter_dir / f"{book_slug}_{chapter_slug}.mp4"
        print(f"    creating YouTube video...")
        try:
            create_youtube_video(
                chapter_mp3, cover_path, video_mp4, chapter_title,
                {"album": album_name, "artist": "Crafted BSB Bible"},
            )
        except subprocess.CalledProcessError as e:
            print(f"    WARNING: video creation failed: {e.stderr.decode()[:200] if e.stderr else 'unknown'}")

    checkpoint["chapter_complete"] = True
    save_checkpoint(checkpoint_path, checkpoint)

    size_mb = chapter_mp3.stat().st_size / (1024 * 1024)
    print(f"    done: {chapter_mp3.name} ({size_mb:.1f} MB)")
    return True


def generate_book(
    api_key, voice_id, model_id, book_name, chapters, out_dir,
    cover_path, silence_ms, dry_run
):
    """Generate all chapters for a single book."""
    total_verses = sum(len(v) for v in chapters.values())
    total_chars = sum(
        len(v["text"]) for ch_verses in chapters.values() for v in ch_verses
    )
    print(f"\n{book_name}: {len(chapters)} chapters, {total_verses} verses, {total_chars:,} chars")

    for ch_num in sorted(chapters.keys()):
        verses = chapters[ch_num]
        if not generate_chapter(
            api_key, voice_id, model_id, book_name, ch_num, verses,
            out_dir, cover_path, silence_ms, dry_run
        ):
            print(f"  FAILED at {book_name} chapter {ch_num}")
            return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate Bible audiobook audio via ElevenLabs TTS for YouTube"
    )
    parser.add_argument("--api-key", required=True, help="ElevenLabs API key")
    parser.add_argument(
        "--jsonl", default=DEFAULT_JSONL, help="Path to BSB JSONL file"
    )
    parser.add_argument(
        "--voice-id", default=DEFAULT_VOICE_ID, help="Voice ID (default: Bill)"
    )
    parser.add_argument(
        "--model-id", default=DEFAULT_MODEL_ID, help="TTS model ID"
    )
    parser.add_argument(
        "--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory"
    )
    parser.add_argument(
        "--cover", help="Cover art image (PNG/JPG) for YouTube videos"
    )
    parser.add_argument(
        "--silence-ms", type=int, default=400,
        help="Silence between verses in milliseconds (default: 400)"
    )
    parser.add_argument("--book", help="Generate a single book (e.g. 'Proverbs')")
    parser.add_argument("--all", action="store_true", help="Generate the entire Bible")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show cost estimate without generating"
    )
    args = parser.parse_args()

    if not args.book and not args.all:
        parser.error("Specify --book <name> or --all")

    print(f"Loading Bible from {args.jsonl}...")
    bible = load_bible(args.jsonl)
    print(f"Loaded {len(bible)} books")

    out_dir = Path(args.out_dir)
    cover_path = Path(args.cover) if args.cover else None

    if cover_path and not cover_path.exists():
        print(f"WARNING: cover art not found at {cover_path}, skipping video creation")
        cover_path = None

    if args.book:
        if args.book not in bible:
            available = ", ".join(sorted(bible.keys()))
            parser.error(f"Book '{args.book}' not found. Available: {available}")
        generate_book(
            args.api_key, args.voice_id, args.model_id, args.book,
            bible[args.book], out_dir, cover_path, args.silence_ms, args.dry_run
        )
    elif args.all:
        for book_name in sorted(bible.keys()):
            if not generate_book(
                args.api_key, args.voice_id, args.model_id, book_name,
                bible[book_name], out_dir, cover_path, args.silence_ms, args.dry_run
            ):
                print(f"\nStopped at {book_name}")
                break

    print("\nDone!")


if __name__ == "__main__":
    main()
