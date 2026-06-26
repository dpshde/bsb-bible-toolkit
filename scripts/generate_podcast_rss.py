#!/usr/bin/env python3
"""Generate a podcast RSS feed for the BSB Bible Audio.

Single podcast with 66 seasons (one per book), chapters as episodes.
Scans the ElevenLabs audio output directory and generates a valid
RSS 2.0 + iTunes podcast namespace XML feed.

The MP3s must be hosted at a publicly accessible URL (Arweave, R2, etc).
Use --base-url to set the prefix; the script assumes the path structure
matches the local layout: <base-url>/<book_slug>/<filename>.mp3

Requirements:
  - ffprobe (from ffmpeg) for duration detection

Usage:
  # Generate feed from all available audio
  python scripts/generate_podcast_rss.py \
      --base-url https://arweave.net/bsb-audio \
      --output output/rss/podcast.xml

  # Dry run (list what would be included)
  python scripts/generate_podcast_rss.py --base-url https://example.com --dry-run

  # Include only specific books
  python scripts/generate_podcast_rss.py \
      --base-url https://example.com --books Philippians Mark
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO / "output" / "elevenlabs_audio"
DEFAULT_JSONL = os.path.expanduser("~/Downloads/bsb.jsonl")

PODCAST_TITLE = "The BSB Bible Audio"
PODCAST_DESC = (
    "The complete Berean Standard Bible, read aloud chapter by chapter. "
    "Organized by book as seasons, chapters as episodes. "
    "Public Domain. Narrated using AI text-to-speech."
)
PODCAST_AUTHOR = "BSB Bible Toolkit"
PODCAST_EMAIL = "dpshde@gmail.com"
PODCAST_LANG = "en"
PODCAST_CATEGORY = "Religion &amp; Spirituality"
PODCAST_SUBCATEGORY = "Christianity"

# Canonical 66-book Bible order (season numbers).
BIBLE_BOOKS = [
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther", "Job", "Psalm", "Proverbs",
    "Ecclesiastes", "Song Of Solomon", "Isaiah", "Jeremiah",
    "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah",
    "Haggai", "Zechariah", "Malachi",
    "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews",
    "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John",
    "Jude", "Revelation",
]

SEASON_MAP = {book: i + 1 for i, book in enumerate(BIBLE_BOOKS)}


def slugify(book):
    return book.lower().replace(" ", "_")


def find_chapter_audio(book, audio_dir):
    """Return list of (chapter_num, path) for a book, sorted by chapter."""
    d = audio_dir / slugify(book)
    if not d.exists():
        return []
    results = []
    for p in sorted(d.glob("*chapter_*.mp3")):
        if p.name.startswith("."):
            continue
        # Extract chapter number from filename like "philippians_chapter_01.mp3"
        import re
        m = re.search(r"chapter_(\d+)", p.name)
        if m:
            results.append((int(m.group(1)), p))
    return results


def audio_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return int(float(out.stdout.strip()))


def file_size(path):
    return path.stat().st_size


def rfc822_date():
    return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")


def generate_feed(episodes, base_url, image_url, author, output_path):
    """Generate the RSS XML from a list of episode dicts."""
    pub_date = rfc822_date()
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        '<rss version="2.0" '
        'xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" '
        'xmlns:content="http://purl.org/rss/1.0/modules/content/">'
    )
    lines.append("  <channel>")
    lines.append(f"    <title>{escape(PODCAST_TITLE)}</title>")
    lines.append(f"    <link>{escape(base_url)}</link>")
    lines.append(f"    <description>{escape(PODCAST_DESC)}</description>")
    lines.append(f"    <language>{PODCAST_LANG}</language>")
    lines.append(f"    <lastBuildDate>{pub_date}</lastBuildDate>")
    lines.append(f"    <itunes:author>{escape(author)}</itunes:author>")
    lines.append(f"    <itunes:summary>{escape(PODCAST_DESC)}</itunes:summary>")
    if image_url:
        lines.append(f'    <itunes:image href="{escape(image_url)}" />')
        lines.append(f"    <image>")
        lines.append(f"      <url>{escape(image_url)}</url>")
        lines.append(f"      <title>{escape(PODCAST_TITLE)}</title>")
        lines.append(f"      <link>{escape(base_url)}</link>")
        lines.append(f"    </image>")
    lines.append(f"    <itunes:category text=\"{PODCAST_CATEGORY}\">")
    lines.append(f'      <itunes:category text="{PODCAST_SUBCATEGORY}" />')
    lines.append(f"    </itunes:category>")
    lines.append(f"    <itunes:type>serial</itunes:type>")
    lines.append(f"    <itunes:explicit>false</itunes:explicit>")
    lines.append(
        f"    <itunes:owner>"
        f"<itunes:name>{escape(author)}</itunes:name>"
        f"<itunes:email>{escape(PODCAST_EMAIL)}</itunes:email>"
        f"</itunes:owner>"
    )

    for ep in episodes:
        lines.append("    <item>")
        lines.append(f"      <title>{escape(ep['title'])}</title>")
        lines.append(f"      <description>{escape(ep['description'])}</description>")
        lines.append(
            f'      <enclosure url="{escape(ep["url"])}" '
            f'length="{ep["size"]}" type="audio/mpeg" />'
        )
        lines.append(f'      <guid isPermaLink="true">{escape(ep["url"])}</guid>')
        lines.append(f"      <pubDate>{ep['pub_date']}</pubDate>")
        lines.append(f"      <itunes:duration>{ep['duration']}</itunes:duration>")
        lines.append(f"      <itunes:season>{ep['season']}</itunes:season>")
        lines.append(f"      <itunes:episode>{ep['episode']}</itunes:episode>")
        lines.append(f"      <itunes:episodeType>full</itunes:episodeType>")
        lines.append(f"      <itunes:explicit>false</itunes:explicit>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def main():
    ap = argparse.ArgumentParser(description="Generate podcast RSS feed for BSB Bible Audio")
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR),
                    help="Directory containing per-book audio folders")
    ap.add_argument("--base-url", default=None,
                    help="Public URL prefix where MP3s are hosted (e.g. https://arweave.net/bsb-audio). "
                         "URLs become <base-url>/<book_slug>/<filename>")
    ap.add_argument("--github-releases", default=None,
                    help="GitHub repo for per-book releases (e.g. dpshde/bsb-bible-toolkit). "
                         "URLs become https://github.com/<repo>/releases/download/bsb-audio-<book>/<filename>")
    ap.add_argument("--image", default=None,
                    help="URL to podcast cover art (3000x3000 PNG recommended)")
    ap.add_argument("--author", default=PODCAST_AUTHOR)
    ap.add_argument("--output", default="output/rss/podcast.xml")
    ap.add_argument("--books", nargs="*", default=None,
                    help="Only include these books (default: all with audio)")
    ap.add_argument("--dry-run", action="store_true",
                    help="List episodes without writing the feed")
    args = ap.parse_args()

    audio_dir = Path(args.audio_dir)
    base_url = args.base_url.rstrip("/") if args.base_url else None
    gh_repo = args.github_releases

    if not base_url and not gh_repo:
        sys.exit("Specify --base-url or --github-releases for MP3 hosting URLs.")

    # Determine which books to include.
    book_list = args.books if args.books else BIBLE_BOOKS

    # Validate season mapping.
    for book in book_list:
        if book not in SEASON_MAP:
            sys.exit(f"Unknown book: {book}. Check spelling against BIBLE_BOOKS.")

    # Scan for audio and build episode list.
    episodes = []
    total_size = 0
    total_duration = 0

    for book in book_list:
        season = SEASON_MAP[book]
        chapters = find_chapter_audio(book, audio_dir)
        if not chapters:
            continue

        print(f"  {book} (Season {season}): {len(chapters)} chapters")

        for ch_num, audio_path in chapters:
            duration = audio_duration(audio_path)
            size = file_size(audio_path)
            total_size += size
            total_duration += duration

            if gh_repo:
                url = (f"https://github.com/{gh_repo}/releases/download/"
                       f"bsb-audio-{slugify(book)}/{audio_path.name}")
            else:
                rel_path = f"{slugify(book)}/{audio_path.name}"
                url = f"{base_url}/{rel_path}"
            title = f"{book} - Chapter {ch_num}"
            description = (
                f"The Berean Standard Bible - {book} Chapter {ch_num}. "
                f"Public Domain. Read aloud using AI text-to-speech."
            )
            # Stagger pub dates by 1 minute so order is preserved.
            pub_date = datetime(2025, 1, 1, 0, ch_num, tzinfo=timezone.utc)
            # Add season offset so later seasons have later dates.
            pub_date = pub_date.replace(month=min(12, season))

            episodes.append({
                "title": title,
                "description": description,
                "url": url,
                "size": size,
                "duration": duration,
                "season": season,
                "episode": ch_num,
                "pub_date": pub_date.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            })

    if not episodes:
        sys.exit("No audio files found. Generate audio first with generate_elevenlabs_audio.py.")

    print(f"\nTotal: {len(episodes)} episodes")
    print(f"Total size: {total_size / 1024 / 1024:.1f} MB")
    print(f"Total duration: {total_duration // 60} min ({total_duration // 3600}h {(total_duration % 3600) // 60}m)")

    if args.dry_run:
        print("\nDry run - no feed written. First 5 episodes:")
        for ep in episodes[:5]:
            print(f"  S{ep['season']}E{ep['episode']}: {ep['title']} "
                  f"({ep['duration']}s, {ep['size'] // 1024}KB) -> {ep['url']}")
        return

    link_url = base_url or (f"https://github.com/{gh_repo}" if gh_repo else "")
    output_path = Path(args.output)
    generate_feed(episodes, link_url, args.image, args.author, output_path)
    print(f"\nRSS feed -> {output_path} ({output_path.stat().st_size} bytes)")
    print(f"\nSubmit this URL to:")
    print(f"  YouTube Studio > Podcasts > New > RSS URL")
    print(f"  Spotify: podcasters.spotify.com > Submit RSS")
    print(f"  Apple:   podcastsconnect.apple.com > Add Show")


if __name__ == "__main__":
    main()
