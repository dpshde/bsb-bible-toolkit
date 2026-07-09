# BSB Local Audio (Kokoro, Chatterbox, demos)

Offline TTS for rendering BSB chapters from the verse-level JSONL source at:

https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s

The default chapter is Psalm 23. Scripts write the original chapter text and a
manifest with normalized `speech_text`, then can render local audio with one or
more installed engines.

Generated audio, manifests, and player assets go under `output/audio/local/`,
which is gitignored. Optional per-engine venvs live in `audio/local/.venv*/`.

## Prepare Text Only

```bash
python3 audio/local/generate_demo.py
```

Change the chapter without editing code:

```bash
python3 audio/local/generate_demo.py --book John --chapter 3
```

Limit heavier engines to a short excerpt:

```bash
python3 audio/local/generate_demo.py --max-verses 2 --engine chatterbox
```

Render a slower Kokoro pass with verse-level pauses:

```bash
python3 audio/local/generate_demo.py \
    --engine kokoro \
    --kokoro-voice af_heart \
    --speed 0.86 \
    --punctuation-pauses \
    --output-tag punctuation-paused
```

The progressive punctuation pause ladder is:

| Punctuation | Pause |
|-------------|-------|
| `,` | 45 ms |
| `'` / `"` | 70 ms |
| `;` | 70 ms |
| `-` | 150 ms |
| `:` | 190 ms |
| `.` / `?` / `!` | 320 ms |

For semicolon-only experimentation:

```bash
python3 audio/local/generate_demo.py \
    --engine kokoro \
    --kokoro-voice af_heart \
    --speed 0.86 \
    --verse-pauses \
    --semicolon-pauses \
    --pause-ms 350 \
    --output-tag semicolon-paused
```

For verse pauses only:

```bash
python3 audio/local/generate_demo.py \
    --engine kokoro \
    --kokoro-voice af_heart \
    --speed 0.86 \
    --verse-pauses \
    --pause-ms 450 \
    --output-tag balanced-paused
```

The spoken text normalizes `LORD` to `Lord` so local TTS engines pronounce it as
a word instead of spelling the letters. The original verse text is preserved in
the generated manifest.

## Prebuilt Browser Player

Open `output/audio/local/listen.html` to review pre-rendered BSB TTS assets.
The player loads `output/audio/local/assets.json`, plays the selected audio
immediately, shows the exact text used for generation, and highlights the
current transcript segment during playback. Punctuation-aware assets can keep
hidden timing segments for semicolon pauses while displaying whole verses in the
visible transcript.

Rebuild the prebuilt asset manifest after rendering new files:

```bash
audio/local/.venv/bin/python audio/local/build_manifest.py
```

Browser-side Kokoro generation is possible with `kokoro-js`, but in practice the
model download and generation latency are too slow for this demo workflow. Use
prebuilt audio for a responsive reader experience.

## MLX Prebuild Path

For Apple Silicon prebuilds, prefer `mlx-audio`: it keeps generation local,
avoids PyTorch, and supports quantized Kokoro variants.

```bash
uv pip install mlx-audio "misaki[en]"
brew install ffmpeg
```

Smoke test:

```bash
python -m mlx_audio.tts.generate \
    --model mlx-community/Kokoro-82M-bf16 \
    --text "MLX-accelerated Kokoro is ready for local BSB audio." \
    --voice af_heart \
    --play \
    --lang_code a
```

Prebuild Psalm 23 assets with the progressive punctuation ladder:

```bash
python audio/local/prebuild_assets.py \
    --model mlx-community/Kokoro-82M-bf16 \
    --voice af_heart \
    --voice bm_george
audio/local/.venv/bin/python audio/local/build_manifest.py
```

Use `mlx-community/Kokoro-82M-8bit` or `mlx-community/Kokoro-82M-4bit` for
lower memory and faster iteration; keep `bf16` for max quality.

## Local Model Options

Kokoro is the quickest high-quality local baseline. It is small enough to test
without a large GPU.

```bash
brew install espeak-ng
python3 -m pip install kokoro soundfile
python3 audio/local/generate_demo.py --engine kokoro
```

On Apple Silicon, Kokoro's upstream docs recommend enabling MPS fallback:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python3 audio/local/generate_demo.py --engine kokoro
```

### Chatterbox (MLX or PyTorch)

Chatterbox is the stronger local quality / voice-cloning path. Prefer **MLX**
on Apple Silicon for multi-chapter or full-Bible runs. Use **PyTorch** for
short demos, the voice-match grid, or when `mlx-audio` is unavailable.

**Default voice profile is `clone-calm`** (best A/B match to production
ElevenLabs Bill): `exaggeration=0.35`, `cfg_weight=0.4`, cloning from
`output/audio/local/voice-match/ref-bill-phil1.wav`.

| Script | Backend | Role |
|--------|---------|------|
| `generate_demo.py --engine chatterbox` | **PyTorch only** | Short chapter / excerpt WAVs |
| `voice_match_chatterbox.py` | **PyTorch only** | A/B grid against Bill reference |
| `generate_chatterbox.py` | **MLX (default)** or PyTorch | Checkpointed book / NT / full Bible → MP3 |

#### Prerequisites

1. **`ffmpeg`** on `PATH` (ref-clip extract, WAV concat, MP3 encode).
2. **Python 3.11** venvs (separate installs; do not mix stacks in one env).
3. **Local BSB JSONL** for `generate_chatterbox.py` (file path only; no URL
   fetch). Default: `~/Downloads/bsb.jsonl`. Override with `--jsonl /path/to/bsb.jsonl`.
   Demo and voice-match scripts can use the Arweave URL above when a local file
   is not present.
4. **Voice reference WAV** for clone-calm (or pass `--audio-prompt-path ""` for
   the model default voice).
5. **Hugging Face model download** on first run (weights cached under HF home).
6. Disk under `output/audio/local/chatterbox/` for chapter MP3s, hidden
   `.checkpoint_*.json` / `.parts_*` resume files, and optional `logs/`.

Where to get JSONL: download or copy a verse-level BSB JSONL to a local path
(production tooling often uses `~/Downloads/bsb.jsonl`). The same verse schema
as the Arweave demo source is expected (`book`, `chapter`, `verseNum`, text).

#### One-time setup

```bash
# PyTorch Chatterbox (demos + voice-match + --backend torch)
uv venv audio/local/.venv-chatterbox --python 3.11
uv pip install --python audio/local/.venv-chatterbox/bin/python chatterbox-tts
# resemble-perth still imports pkg_resources; pin setuptools below 81
uv pip install --python audio/local/.venv-chatterbox/bin/python 'setuptools<81'

# MLX Chatterbox (preferred for batch / NT)
uv venv audio/local/.venv-mlx --python 3.11
uv pip install --python audio/local/.venv-mlx/bin/python mlx-audio soundfile
# mlx-lm currently needs transformers 4.x (5.x breaks AutoTokenizer.register)
uv pip install --python audio/local/.venv-mlx/bin/python 'transformers>=4.49,<5'

# Bill reference clip (once; needs a production Philippians ch.1 MP3 or any mono WAV)
mkdir -p output/audio/local/voice-match
ffmpeg -y -ss 5 -t 8 \
  -i output/elevenlabs_audio/philippians/philippians_chapter_01.mp3 \
  -ac 1 -ar 24000 \
  output/audio/local/voice-match/ref-bill-phil1.wav
```

If you do not have the ElevenLabs Philippians file, point
`--audio-prompt-path` at any short mono reference WAV (roughly 6–10s works well),
or use the built-in voice with `--audio-prompt-path ""`.

#### Smoke-test matrix

```bash
# 1) Inventory only (no model) — confirms JSONL + book list
audio/local/.venv-mlx/bin/python audio/local/generate_chatterbox.py \
  --nt --dry-run

# 2) MLX: one short book (or first chapter of a longer book)
audio/local/.venv-mlx/bin/python audio/local/generate_chatterbox.py \
  --book "2 John" --backend mlx
# longer book, first chapter only:
audio/local/.venv-mlx/bin/python audio/local/generate_chatterbox.py \
  --book Philippians --backend mlx --max-chapters 1

# 3) PyTorch: short demo excerpt (generate_demo is torch-only for chatterbox)
PYTORCH_ENABLE_MPS_FALLBACK=1 audio/local/.venv-chatterbox/bin/python \
  audio/local/generate_demo.py \
  --engine chatterbox \
  --device mps \
  --max-verses 2

# 4) PyTorch: one book via the batch script
PYTORCH_ENABLE_MPS_FALLBACK=1 audio/local/.venv-chatterbox/bin/python \
  audio/local/generate_chatterbox.py \
  --book Philippians --backend torch --device mps --max-chapters 1
```

#### Full New Testament / Bible (batch)

Defaults for `generate_chatterbox.py`: **MLX** backend,
`mlx-community/chatterbox-fp16`, clone-calm knobs, local JSONL path above.
Optional faster model: `--model mlx-community/chatterbox-turbo-fp16` (re-check
voice match first).

```bash
mkdir -p output/audio/local/chatterbox/logs

# MLX NT (preferred on Apple Silicon)
caffeinate -dims nohup \
  audio/local/.venv-mlx/bin/python -u \
  audio/local/generate_chatterbox.py --nt --backend mlx \
  > output/audio/local/chatterbox/logs/nt-mlx.log 2>&1 &
tail -f output/audio/local/chatterbox/logs/nt-mlx.log

# PyTorch / MPS fallback (slower; same clone-calm defaults)
caffeinate -dims nohup \
  env PYTORCH_ENABLE_MPS_FALLBACK=1 \
  audio/local/.venv-chatterbox/bin/python -u \
  audio/local/generate_chatterbox.py --nt --backend torch --device mps \
  > output/audio/local/chatterbox/logs/nt-torch.log 2>&1 &
```

Other useful flags:

| Flag | Purpose |
|------|---------|
| `--book Philippians` | Single book (case-insensitive match) |
| `--nt` / `--all` | Full New Testament or entire Bible |
| `--jsonl PATH` | Local BSB JSONL (required path; default `~/Downloads/bsb.jsonl`) |
| `--max-chapters N` | Limit chapters per book (smoke tests) |
| `--max-chars N` | Chunk size (default 320; stay under model token cap) |
| `--dry-run` | Inventory chapters/chunks without loading weights |
| `--audio-prompt-path PATH` or `""` | Clone reference, or empty for built-in voice |
| `--exaggeration` / `--cfg-weight` | Override clone-calm knobs |

Checkpointed MP3s land under `output/audio/local/chatterbox/<book_slug>/`.
Re-run the same command to **resume**; completed chapters (checkpoint + MP3)
are skipped. Partial chapter parts live in hidden `.parts_*` directories beside
the MP3s.

Override knobs or the reference clip on demos when needed:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 audio/local/.venv-chatterbox/bin/python \
  audio/local/generate_demo.py \
  --engine chatterbox \
  --device mps \
  --audio-prompt-path path/to/other-reference.wav \
  --exaggeration 0.5 \
  --cfg-weight 0.3
```

#### Voice-match grid (ElevenLabs Bill target)

Chatterbox has no named voice catalog. Speaker identity comes from zero-shot
cloning (`--audio-prompt-path`) plus `exaggeration` and `cfg_weight`. After a
short A/B against production Bill (`pqHfZKP75CvOlQylNhV4`), **clone-calm**
(`e=0.35`, `c=0.4`) was chosen as the project default above.

This helper is **PyTorch only** (same `.venv-chatterbox` env as demos):

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 audio/local/.venv-chatterbox/bin/python \
  audio/local/voice_match_chatterbox.py --device mps
```

Outputs land under `output/audio/local/voice-match/` with labeled WAVs and a
`comparison.json` manifest.

Dia is a larger, more experimental dialogue-oriented local model. It is best
suited to a CUDA GPU and may not be practical on CPU.

```bash
python3 -m pip install git+https://github.com/nari-labs/dia.git
python3 audio/local/generate_demo.py --engine dia --device cuda
```

For a dependency-free smoke test on macOS only:

```bash
python3 audio/local/generate_demo.py --engine say
```

Render multiple engines against the same chapter:

```bash
python3 audio/local/generate_demo.py \
    --engine kokoro \
    --engine chatterbox \
    --device mps
```

Keep demo audio out of commits unless there is an explicit release reason and
license/voice rights are documented.
