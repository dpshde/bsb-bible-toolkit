"""Shared filesystem paths for BSB audio tooling."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PRODUCTION_AUDIO_DIR = REPO_ROOT / "output" / "audio" / "production"
LOCAL_AUDIO_DIR = REPO_ROOT / "output" / "audio" / "local"
YOUTUBE_VIDEO_DIR = REPO_ROOT / "output" / "youtube_videos"
RSS_OUTPUT_DIR = REPO_ROOT / "output" / "rss"

AUDIO_EMBLEM = REPO_ROOT / "assets" / "bsb-audio-emblem.jpg"
SECRETS_DIR = REPO_ROOT / ".secrets"
YOUTUBE_CLIENT_SECRET = SECRETS_DIR / "client_secret.json"
YOUTUBE_TOKEN = SECRETS_DIR / "youtube_token.json"

DEFAULT_JSONL_URL = (
    "https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s"
)