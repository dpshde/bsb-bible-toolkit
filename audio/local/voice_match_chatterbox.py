#!/usr/bin/env python3
"""Render a short Chatterbox A/B grid against an ElevenLabs-style reference clip.

Reuses chapter loading and speech text builders from generate_demo.py.
Writes labeled WAVs plus comparison.json under output/audio/local/voice-match/.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from audio.local.generate_demo import (  # noqa: E402
    _patch_torch_load_for_device,
    build_speech_text,
    chatterbox_output_stem,
    load_chapter,
    require_dependency,
    write_demo_files,
)
from audio.paths import LOCAL_AUDIO_DIR  # noqa: E402

DEFAULT_REF = LOCAL_AUDIO_DIR / "voice-match" / "ref-bill-phil1.wav"
DEFAULT_OUT = LOCAL_AUDIO_DIR / "voice-match"

# Narration-oriented grid: default voice + clone variants around Bill pacing.
# Project default (chosen after A/B): clone-calm (e=0.35, c=0.4).
GRID: List[Dict[str, object]] = [
    {
        "label": "default",
        "use_prompt": False,
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
    },
    {
        "label": "clone-default",
        "use_prompt": True,
        "exaggeration": 0.5,
        "cfg_weight": 0.5,
    },
    {
        "label": "clone-narration",
        "use_prompt": True,
        "exaggeration": 0.5,
        "cfg_weight": 0.3,
    },
    {
        "label": "clone-calm",  # project default in generate_demo.py
        "use_prompt": True,
        "exaggeration": 0.35,
        "cfg_weight": 0.4,
    },
    {
        "label": "clone-stable",
        "use_prompt": True,
        "exaggeration": 0.4,
        "cfg_weight": 0.5,
    },
]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a short Chatterbox voice-match grid for A/B listening."
    )
    parser.add_argument("--book", default="Psalm")
    parser.add_argument("--chapter", default="23")
    parser.add_argument(
        "--max-verses",
        type=int,
        default=2,
        help="Limit to the first N verses (default 2 for a short listen).",
    )
    parser.add_argument(
        "--audio-prompt-path",
        type=Path,
        default=DEFAULT_REF,
        help="Reference clip for zero-shot cloning (ElevenLabs sample WAV).",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--device",
        default="mps",
        help="Torch device: mps (Apple Silicon), cuda, or cpu.",
    )
    parser.add_argument(
        "--labels",
        nargs="*",
        default=[],
        help="Optional subset of grid labels to render (default: all).",
    )
    parser.add_argument(
        "--jsonl",
        default=None,
        help="BSB JSONL URL or path (defaults to generate_demo DEFAULT_JSONL).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    from audio.local.generate_demo import DEFAULT_JSONL

    args = parse_args(argv or sys.argv[1:])
    jsonl = args.jsonl or DEFAULT_JSONL
    ref_path = args.audio_prompt_path
    if not ref_path.exists():
        print(f"Missing reference clip: {ref_path}", file=sys.stderr)
        print(
            "Create one with ffmpeg, e.g.:\n"
            "  ffmpeg -y -ss 5 -t 8 \\\n"
            "    -i output/elevenlabs_audio/philippians/philippians_chapter_01.mp3 \\\n"
            "    -ac 1 -ar 24000 output/audio/local/voice-match/ref-bill-phil1.wav",
            file=sys.stderr,
        )
        return 1

    verses = load_chapter(jsonl, args.book, args.chapter)
    if args.max_verses > 0:
        verses = verses[: args.max_verses]
    if not verses:
        print(f"No verses found for {args.book} {args.chapter}", file=sys.stderr)
        return 1

    speech_text = build_speech_text(args.book, args.chapter, verses)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    paths = write_demo_files(
        args.out_dir,
        jsonl,
        args.book,
        args.chapter,
        verses,
        speech_text,
    )
    chapter_dir = paths["chapter_dir"]
    print(f"Speech text ({len(speech_text)} chars):\n{speech_text}\n")
    print(f"Chapter dir: {chapter_dir}")
    print(f"Reference: {ref_path}")
    print(f"Device: {args.device}")

    try:
        import pkg_resources  # noqa: F401
    except ImportError:
        print(
            "Missing pkg_resources (needed by resemble-perth). "
            "Install with: uv pip install --python audio/local/.venv-chatterbox/bin/python 'setuptools<81'",
            file=sys.stderr,
        )
        return 1

    torchaudio = require_dependency("torchaudio", "pip install chatterbox-tts")
    _patch_torch_load_for_device(args.device)
    from chatterbox.tts import ChatterboxTTS

    print("Loading Chatterbox model (once for the whole grid)...")
    load_started = time.time()
    model = ChatterboxTTS.from_pretrained(device=args.device)
    print(f"Model ready in {time.time() - load_started:.1f}s")

    wanted = set(args.labels) if args.labels else {c["label"] for c in GRID}
    results = []
    for config in GRID:
        label = str(config["label"])
        if label not in wanted:
            continue
        exaggeration = float(config["exaggeration"])
        cfg_weight = float(config["cfg_weight"])
        use_prompt = bool(config["use_prompt"])
        prompt = str(ref_path) if use_prompt else ""
        stem = chatterbox_output_stem(prompt, exaggeration, cfg_weight, label)
        output_path = chapter_dir / f"{stem}.wav"

        print(f"\n[{label}] exaggeration={exaggeration} cfg_weight={cfg_weight} "
              f"prompt={'yes' if use_prompt else 'no'}")
        started = time.time()
        try:
            kwargs = {
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight,
            }
            if prompt:
                kwargs["audio_prompt_path"] = prompt
            wav = model.generate(speech_text, **kwargs)
            if getattr(wav, "dim", lambda: 1)() == 1:
                wav = wav.unsqueeze(0)
            torchaudio.save(str(output_path), wav.cpu(), model.sr)
            elapsed = time.time() - started
            size_kb = output_path.stat().st_size / 1024
            print(f"  wrote {output_path.name} ({size_kb:.0f} KiB, {elapsed:.1f}s)")
            results.append(
                {
                    "label": label,
                    "path": str(output_path),
                    "audio_prompt_path": prompt or None,
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight,
                    "seconds": round(elapsed, 2),
                    "ok": True,
                }
            )
        except Exception as exc:  # noqa: BLE001 — surface each cell failure, continue grid
            elapsed = time.time() - started
            print(f"  FAILED after {elapsed:.1f}s: {exc}", file=sys.stderr)
            results.append(
                {
                    "label": label,
                    "path": str(output_path),
                    "audio_prompt_path": prompt or None,
                    "exaggeration": exaggeration,
                    "cfg_weight": cfg_weight,
                    "seconds": round(elapsed, 2),
                    "ok": False,
                    "error": str(exc),
                }
            )

    comparison = {
        "book": args.book,
        "chapter": str(args.chapter),
        "max_verses": args.max_verses,
        "speech_text": speech_text,
        "reference": str(ref_path),
        "device": args.device,
        "elevenlabs_ear_ref_note": (
            "Timbre reference is the ElevenLabs Bill clone prompt. "
            "Text is Psalm 23 vv1-2; for text-aligned EL comparison, "
            "regenerate the same passage with audio/production/generate.py."
        ),
        "results": results,
    }
    comparison_path = args.out_dir / "comparison.json"
    comparison_path.write_text(
        json.dumps(comparison, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote comparison: {comparison_path}")

    ok = sum(1 for r in results if r.get("ok"))
    fail = len(results) - ok
    print(f"Done: {ok} ok, {fail} failed")
    return 0 if fail == 0 and ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
