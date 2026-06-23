# BSB TTS Demo Snippets

This folder contains local TTS demo notes for rendering one BSB chapter from the
verse-level JSONL source at:

https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s

The default chapter is Psalm 23. The script writes the original chapter text and
a manifest with normalized `speech_text`, then can render local audio with one
or more installed engines.

Generated audio, manifests, and player assets go under `examples/tts/output/`,
which is ignored.

## Prepare Text Only

```bash
python3 scripts/generate_tts_demo.py
```

Change the chapter without editing code:

```bash
python3 scripts/generate_tts_demo.py --book John --chapter 3
```

Limit heavier engines to a short excerpt:

```bash
python3 scripts/generate_tts_demo.py --max-verses 2 --engine chatterbox
```

Render a slower Kokoro pass with verse-level pauses:

```bash
python3 scripts/generate_tts_demo.py \
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
python3 scripts/generate_tts_demo.py \
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
python3 scripts/generate_tts_demo.py \
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

Open `examples/tts/output/listen.html` to review pre-rendered BSB TTS assets.
The player loads `examples/tts/output/assets.json`, plays the selected audio
immediately, shows the exact text used for generation, and highlights the
current transcript segment during playback. Punctuation-aware assets can keep
hidden timing segments for semicolon pauses while displaying whole verses in the
visible transcript.

Rebuild the prebuilt asset manifest after rendering new files:

```bash
examples/tts/.venv/bin/python scripts/build_tts_asset_manifest.py
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
python scripts/prebuild_mlx_tts_assets.py \
    --model mlx-community/Kokoro-82M-bf16 \
    --voice af_heart \
    --voice bm_george
examples/tts/.venv/bin/python scripts/build_tts_asset_manifest.py
```

Use `mlx-community/Kokoro-82M-8bit` or `mlx-community/Kokoro-82M-4bit` for
lower memory and faster iteration; keep `bf16` for max quality.

## Local Model Options

Kokoro is the quickest high-quality local baseline. It is small enough to test
without a large GPU.

```bash
brew install espeak-ng
python3 -m pip install kokoro soundfile
python3 scripts/generate_tts_demo.py --engine kokoro
```

On Apple Silicon, Kokoro's upstream docs recommend enabling MPS fallback:

```bash
PYTORCH_ENABLE_MPS_FALLBACK=1 python3 scripts/generate_tts_demo.py --engine kokoro
```

Chatterbox is a stronger local quality/voice-cloning candidate. Use a separate
Python 3.11 environment if dependency resolution gets tight.

```bash
python3 -m pip install chatterbox-tts
PYTORCH_ENABLE_MPS_FALLBACK=1 python3 scripts/generate_tts_demo.py \
    --engine chatterbox \
    --device mps
```

With a permitted local reference voice clip:

```bash
python3 scripts/generate_tts_demo.py \
    --engine chatterbox \
    --device mps \
    --audio-prompt-path path/to/your-voice-reference.wav
```

Dia is a larger, more experimental dialogue-oriented local model. It is best
suited to a CUDA GPU and may not be practical on CPU.

```bash
python3 -m pip install git+https://github.com/nari-labs/dia.git
python3 scripts/generate_tts_demo.py --engine dia --device cuda
```

For a dependency-free smoke test on macOS only:

```bash
python3 scripts/generate_tts_demo.py --engine say
```

Render multiple engines against the same chapter:

```bash
python3 scripts/generate_tts_demo.py \
    --engine kokoro \
    --engine chatterbox \
    --device mps
```

Keep demo audio out of commits unless there is an explicit release reason and
license/voice rights are documented.
