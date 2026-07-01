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

## Local (MLX / Kokoro)

Offline TTS on Apple Silicon for voice experiments, chapter demos, and
listen.html review. No API keys required.

| Script | Purpose |
|--------|---------|
| [`local/mlx_tts.py`](local/mlx_tts.py) | Checkpointed chapter rendering |
| [`local/generate_demo.py`](local/generate_demo.py) | Multi-engine demo snippets |
| [`local/prebuild_assets.py`](local/prebuild_assets.py) | Batch WAV prebuild |
| [`local/build_manifest.py`](local/build_manifest.py) | `assets.json` for the player |
| [`local/tui/`](local/tui/) | Terminal UI for `mlx_tts.py` |

Output: `output/audio/local/`

See [`local/README.md`](local/README.md) for engine setup and pause tuning.

```bash
python audio/local/mlx_tts.py generate --book Psalm --chapter 23 --voices af_heart
python audio/local/generate_demo.py --book John --chapter 3
```

## Shared paths

Path constants live in [`paths.py`](paths.py). Both pipelines read the same BSB
JSONL verse source (local file or Arweave URL).

## Legacy entry points

Thin wrappers under `scripts/` still work and forward to these modules for older
docs and bookmarks.