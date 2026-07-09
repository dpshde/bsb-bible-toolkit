# BSB Audio

Two parallel pipelines for turning BSB JSONL into listenable Scripture.

## Production (ElevenLabs)

Cloud TTS for the public audiobook: generate chapter MP3s, upload to YouTube,
and publish an RSS feed for podcast apps.

| Step | Script |
|------|--------|
| Generate audio | [`production/generate.py`](production/generate.py) |
| Upload to YouTube | [`production/upload_youtube.py`](production/upload_youtube.py) |
| Generate RSS | [`production/generate_rss.py`](production/generate_rss.py) |
| ElevenLabs Studio upload | [`production/upload_elevenlabs.py`](production/upload_elevenlabs.py) |

Output: `output/audio/production/<book>/`

See [`production/PLAN.md`](production/PLAN.md) for the full distribution plan.

```bash
python audio/production/generate.py --api-key sk_... --book Philippians
python audio/production/upload_youtube.py --book Philippians --all
python audio/production/generate_rss.py \
    --github-releases dpshde/bsb-bible-toolkit \
    --books Philippians
```

## Local (Kokoro, Chatterbox, demos)

Offline TTS for voice experiments, chapter demos, and listen.html review. No
API keys required. Kokoro is the quick baseline; Chatterbox is the
higher-quality clone path (MLX preferred on Apple Silicon, PyTorch fallback).

| Script | Purpose |
|--------|---------|
| [`local/mlx_tts.py`](local/mlx_tts.py) | Checkpointed Kokoro chapter rendering (mlx-audio) |
| [`local/generate_demo.py`](local/generate_demo.py) | Multi-engine demo snippets (Chatterbox = PyTorch) |
| [`local/generate_chatterbox.py`](local/generate_chatterbox.py) | Checkpointed Chatterbox book/NT/Bible (MLX or torch, clone-calm) |
| [`local/voice_match_chatterbox.py`](local/voice_match_chatterbox.py) | Chatterbox A/B grid vs Bill reference (PyTorch) |
| [`local/prebuild_assets.py`](local/prebuild_assets.py) | Batch WAV prebuild |
| [`local/build_manifest.py`](local/build_manifest.py) | `assets.json` for the player |
| [`local/tui/`](local/tui/) | Terminal UI for `mlx_tts.py` |

Output: `output/audio/local/`

See [`local/README.md`](local/README.md) for engine setup, Chatterbox MLX vs
PyTorch recipes, JSONL prerequisites, and pause tuning.

```bash
python audio/local/mlx_tts.py generate --book Psalm --chapter 23 --voices af_heart
python audio/local/generate_demo.py --book John --chapter 3
# Chatterbox batch (needs local JSONL + .venv-mlx; see local/README.md)
audio/local/.venv-mlx/bin/python audio/local/generate_chatterbox.py \
  --book "2 John" --backend mlx
```

## Shared paths

Path constants live in [`paths.py`](paths.py). Demo tools can read the Arweave
JSONL URL; `generate_chatterbox.py` and production scripts expect a **local**
JSONL file path (default often `~/Downloads/bsb.jsonl`).

## Legacy entry points

Thin wrappers under `scripts/` still work and forward to these modules for older
docs and bookmarks.