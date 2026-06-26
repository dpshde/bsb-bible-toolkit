#!/usr/bin/env python3
"""Upload Bible audiobook chapters to YouTube via the Data API.

Creates an MP4 (static image + audio) with ffmpeg, then uploads via
resumable upload.  Supports playlists (one per book = podcast season).

Requirements:
  pip install google-auth-oauthlib google-api-python-client

Usage:
  # Upload single chapter
  python scripts/upload_youtube.py --book Philippians --chapter 1

  # Upload all chapters of a book
  python scripts/upload_youtube.py --book Philippians --all

  # Dry run (show what would be uploaded)
  python scripts/upload_youtube.py --book Philippians --all --dry-run
"""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

REPO = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO / "output" / "elevenlabs_audio"
VIDEO_DIR = REPO / "output" / "youtube_videos"
SECRET_PATH = REPO / ".secrets" / "client_secret.json"
TOKEN_PATH = REPO / ".secrets" / "youtube_token.json"

STATIC_IMAGE = os.path.expanduser(
    "~/Downloads/grok-image-6690b34c-2de7-4cdd-9eac-39222f359ceb.jpg"
)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

RETRYABLE_ERRORS = (409, 429, 500, 502, 503, 504)


PODCAST_DESC = (
    "The Berean Standard Bible (BSB) - a modern, public-domain translation "
    "read aloud, chapter by chapter.\n\n"
    "The BSB proves that world-class Bible translation doesn't need to be "
    "commercialized. No copyright locks. No licensing fees. No paywalls. "
    "Just Scripture, freely given to the world.\n\n"
    "\"Freely you received, freely give.\" - Matthew 10:8\n\n"
    "This audiobook exists because access to God's Word shouldn't come with "
    "a price tag. The BSB is CC0 / public domain - you can read it, share it, "
    "adapt it, and build with it without asking permission.\n\n"
    "Learn more about the case for freely-given ministry: sellingjesus.org\n"
    "Read the BSB: berean.bible\n"
    "License: Public Domain (CC0)\n\n"
    "#bible #audiobible #bsb #scripture #publicdomain"
)

VIDEO_DESC = (
    "The Berean Standard Bible (BSB) - a modern, public-domain translation "
    "that doesn't try to sell you Jesus. It just gives you Scripture.\n\n"
    "\"Freely you received, freely give.\" - Matthew 10:8\n\n"
    "No copyright locks. No paywalls. No licensing fees. The BSB is CC0 / "
    "public domain - freely given, freely shared.\n\n"
    "Learn more: sellingjesus.org\n"
    "Read along: berean.bible\n"
    "License: Public Domain (CC0)\n\n"
    "{book} Chapter {chapter}, read aloud with AI text-to-speech.\n\n"
    "#bible #audiobible #bsb #scripture #publicdomain"
)


def get_youtube_service():
    if not SECRET_PATH.exists():
        sys.exit(f"Missing {SECRET_PATH}. Place client_secret.json there.")
    if TOKEN_PATH.exists():
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(SECRET_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(creds.to_json())
    return build("youtube", "v3", credentials=creds)


def find_audio(book, chapter):
    book_lower = book.lower()
    d = AUDIO_DIR / book_lower
    for pattern in [
        f"{book_lower}_chapter_{chapter:02d}.mp3",
        f"{book_lower}_chapter_{chapter:02d}_flash.mp3",
    ]:
        p = d / pattern
        if p.exists():
            return p
    for p in d.glob(f"*chapter_{chapter:02d}*.mp3"):
        if not p.name.startswith("."):
            return p
    return None


def make_video(audio_path, image_path, out_path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", "scale=1920:1080:flags=lanczos,unsharp=5:5:0.8:5:5:0.0",
        "-c:v", "libx264", "-tune", "stillimage",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-r", "1",
        str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def get_or_create_playlist(yt, book):
    safe_title = f"{book} - BSB Bible Audio"
    resp = (
        yt.playlists()
        .list(part="snippet,id", mine=True, maxResults=50)
        .execute()
    )
    for item in resp.get("items", []):
        if item["snippet"]["title"] == safe_title:
            return item["id"]

    book_desc = PODCAST_DESC.replace("{book}", book)
    body = {
        "snippet": {
            "title": safe_title,
            "description": book_desc,
        },
        "status": {"privacyStatus": "public"},
    }
    resp = yt.playlists().insert(part="snippet,status", body=body).execute()
    return resp["id"]


def add_to_playlist(yt, video_id, playlist_id):
    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    yt.playlistItems().insert(part="snippet", body=body).execute()


def upload_video(yt, video_path, book, chapter, playlist_id=None):
    title = f"{book} {chapter} - BSB Bible Audio"
    body = {
        "snippet": {
            "title": title,
            "description": VIDEO_DESC.format(book=book, chapter=chapter),
            "tags": ["bible", "audiobook", "bsb", "scripture", "publicdomain", book.lower()],
            "categoryId": "22",
        },
        "status": {"privacyStatus": "public"},
    }
    media = MediaFileUpload(str(video_path), chunksize=8 * 1024 * 1024, resumable=True)
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"  Uploading {video_path.name} ...")
    response = None
    attempt = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status and status.total_size:
                pct = int(status.progress() * 100)
                print(f"\r  {pct}%", end="", flush=True)
        except Exception as e:
            attempt += 1
            if attempt > 5:
                raise
            wait = 2 ** attempt
            print(f"\n  Retrying in {wait}s ...")
            time.sleep(wait)
    print(" done.")

    video_id = response["id"]
    print(f"  Video: https://www.youtube.com/watch?v={video_id}")

    if playlist_id:
        add_to_playlist(yt, video_id, playlist_id)
        print(f"  Added to playlist.")

    return video_id


def main():
    ap = argparse.ArgumentParser(description="Upload Bible chapters to YouTube")
    ap.add_argument("--book", required=True)
    ap.add_argument("--chapter", type=int)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-playlist", action="store_true")
    ap.add_argument("--image", default=STATIC_IMAGE, help="Static image for the video")
    args = ap.parse_args()

    chapters = []
    if args.all:
        d = AUDIO_DIR / args.book.lower()
        if not d.exists():
            sys.exit(f"No audio dir: {d}")
        seen = set()
        for p in sorted(d.glob("*chapter_*.mp3")):
            if p.name.startswith("."):
                continue
            m = re.search(r"chapter_(\d+)", p.name)
            if m:
                ch = int(m.group(1))
                if ch not in seen:
                    seen.add(ch)
                    chapters.append(ch)
    elif args.chapter:
        chapters = [args.chapter]
    else:
        sys.exit("Specify --chapter N or --all")

    print(f"Book: {args.book}")
    print(f"Chapters: {chapters}")

    if args.dry_run:
        for ch in chapters:
            audio = find_audio(args.book, ch)
            print(f"  Ch{ch}: {audio}")
        return

    yt = get_youtube_service()
    playlist_id = None if args.no_playlist else get_or_create_playlist(yt, args.book)
    if playlist_id:
        print(f"Playlist: {playlist_id}")

    for ch in chapters:
        audio = find_audio(args.book, ch)
        if not audio:
            print(f"  Ch{ch}: no audio found, skipping")
            continue

        video_path = VIDEO_DIR / args.book.lower() / f"ch{ch:02d}.mp4"

        if not video_path.exists():
            print(f"  Building MP4 for chapter {ch} ...")
            make_video(audio, args.image, video_path)

        upload_video(yt, video_path, args.book, ch, playlist_id)


if __name__ == "__main__":
    main()
