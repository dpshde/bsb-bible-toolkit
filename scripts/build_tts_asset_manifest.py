#!/usr/bin/env python3
"""Build a static manifest for pre-rendered BSB TTS demo assets."""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Sequence

import soundfile as sf


PUNCTUATION_PAUSE_MS = {
    ",": 45,
    '"': 70,
    "'": 70,
    ";": 70,
    "-": 150,
    ":": 190,
    ".": 320,
    "?": 320,
    "!": 320,
}

PSALM_23_SEMICOLON_SEGMENTS = [
    ("Title", "Title", "Psalm 23."),
    ("Ps.23.1", "Ps.23.1a", "The Lord is my shepherd;"),
    ("Ps.23.1", "Ps.23.1b", "I shall not want."),
    ("Ps.23.2", "Ps.23.2a", "He makes me lie down in green pastures;"),
    ("Ps.23.2", "Ps.23.2b", "He leads me beside quiet waters."),
    ("Ps.23.3", "Ps.23.3a", "He restores my soul;"),
    ("Ps.23.3", "Ps.23.3b", "He guides me in the paths of righteousness for the sake of His name."),
    (
        "Ps.23.4",
        "Ps.23.4",
        "Even though I walk through the valley of the shadow of death, I will fear no evil, "
        "for You are with me; Your rod and Your staff, they comfort me.",
    ),
    (
        "Ps.23.5",
        "Ps.23.5a",
        "You prepare a table before me in the presence of my enemies. You anoint my head with oil;",
    ),
    ("Ps.23.5", "Ps.23.5b", "my cup overflows."),
    ("Ps.23.6", "Ps.23.6a", "Surely goodness and mercy will follow me all the days of my life,"),
    ("Ps.23.6", "Ps.23.6b", "and I will dwell in the house of the Lord forever."),
]

PSALM_23_VERSE_SEGMENTS = [
    ("Title", "Psalm 23."),
    ("Ps.23.1", "The Lord is my shepherd; I shall not want."),
    ("Ps.23.2", "He makes me lie down in green pastures; He leads me beside quiet waters."),
    (
        "Ps.23.3",
        "He restores my soul; He guides me in the paths of righteousness for the sake of His name.",
    ),
    (
        "Ps.23.4",
        "Even though I walk through the valley of the shadow of death, I will fear no evil, "
        "for You are with me; Your rod and Your staff, they comfort me.",
    ),
    (
        "Ps.23.5",
        "You prepare a table before me in the presence of my enemies. You anoint my head with oil; "
        "my cup overflows.",
    ),
    (
        "Ps.23.6",
        "Surely goodness and mercy will follow me all the days of my life, and I will dwell "
        "in the house of the Lord forever.",
    ),
]


def normalize_segment_def(part: Sequence[str]) -> Sequence[str]:
    if len(part) == 2:
        ref, text = part
        return ref, ref, text
    if len(part) == 3:
        return part
    raise ValueError(f"Unexpected segment definition: {part}")


def split_progressive_punctuation(text: str) -> List[str]:
    chunks = []
    cursor = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in PUNCTUATION_PAUSE_MS:
            end = index + 1
            while end < len(text) and text[end] in {"'", '"'}:
                end += 1
            chunk = text[cursor:end].strip()
            if chunk:
                chunks.append(chunk)
            cursor = end
        index += 1

    tail = text[cursor:].strip()
    if tail:
        chunks.append(tail)
    return chunks


def progressive_segments(segment_defs: Sequence[Sequence[str]]) -> List[Sequence[str]]:
    segments = []
    for part in segment_defs:
        display_ref, _, text = normalize_segment_def(part)
        chunks = split_progressive_punctuation(text)
        for index, chunk in enumerate(chunks):
            timing_ref = display_ref if len(chunks) == 1 else f"{display_ref}.{index + 1}"
            segments.append((display_ref, timing_ref, chunk))
    return segments

ASSETS = [
    {
        "id": "psalm-23-af-heart-punctuation",
        "label": "Psalm 23 - af_heart - progressive punctuation",
        "file": "psalm-23/kokoro-af-heart-punctuation-paused.wav",
        "voice": "af_heart",
        "settings": {
            "engine": "kokoro",
            "speed": 0.86,
            "punctuationPauseMs": PUNCTUATION_PAUSE_MS,
        },
        "segments": progressive_segments(PSALM_23_VERSE_SEGMENTS),
        "minSilenceMs": 40,
    },
    {
        "id": "psalm-23-bm-george-punctuation",
        "label": "Psalm 23 - bm_george - progressive punctuation",
        "file": "psalm-23/kokoro-bm-george-punctuation-paused.wav",
        "voice": "bm_george",
        "settings": {
            "engine": "kokoro",
            "speed": 0.86,
            "punctuationPauseMs": PUNCTUATION_PAUSE_MS,
        },
        "segments": progressive_segments(PSALM_23_VERSE_SEGMENTS),
        "minSilenceMs": 40,
    },
    {
        "id": "psalm-23-af-heart-semicolon",
        "label": "Psalm 23 - af_heart - semicolon pauses",
        "file": "psalm-23/kokoro-af-heart-semicolon-paused.wav",
        "voice": "af_heart",
        "settings": {"engine": "kokoro", "speed": 0.86, "versePauseMs": 350, "semicolonPauseMs": 350},
        "segments": PSALM_23_SEMICOLON_SEGMENTS,
    },
    {
        "id": "psalm-23-bm-george-semicolon",
        "label": "Psalm 23 - bm_george - semicolon pauses",
        "file": "psalm-23/kokoro-bm-george-semicolon-paused.wav",
        "voice": "bm_george",
        "settings": {"engine": "kokoro", "speed": 0.86, "versePauseMs": 350, "semicolonPauseMs": 350},
        "segments": PSALM_23_SEMICOLON_SEGMENTS,
    },
    {
        "id": "psalm-23-af-heart-balanced",
        "label": "Psalm 23 - af_heart - verse pauses",
        "file": "psalm-23/kokoro-af-heart-balanced-paused.wav",
        "voice": "af_heart",
        "settings": {"engine": "kokoro", "speed": 0.86, "versePauseMs": 450},
        "segments": PSALM_23_VERSE_SEGMENTS,
    },
    {
        "id": "psalm-23-bm-george-balanced",
        "label": "Psalm 23 - bm_george - verse pauses",
        "file": "psalm-23/kokoro-bm-george-balanced-paused.wav",
        "voice": "bm_george",
        "settings": {"engine": "kokoro", "speed": 0.86, "versePauseMs": 450},
        "segments": PSALM_23_VERSE_SEGMENTS,
    },
]


def detect_silence_schedule(
    path: Path, segment_defs: Sequence[Sequence[str]], min_silence_ms: int = 240
) -> List[Dict[str, object]]:
    import numpy as np

    audio, sample_rate = sf.read(str(path), always_2d=False)
    silent = np.abs(audio) < 1e-8
    min_silence = int(sample_rate * min_silence_ms / 1000)
    runs = []
    index = 0
    while index < len(silent):
        if silent[index]:
            end = index
            while end < len(silent) and silent[end]:
                end += 1
            if end - index >= min_silence:
                runs.append((index / sample_rate, end / sample_rate))
            index = end
        else:
            index += 1

    starts = []
    ends = []
    cursor = 0.0
    for start, end in runs:
        starts.append(cursor)
        ends.append(start)
        cursor = end
    starts.append(cursor)
    ends.append(len(audio) / sample_rate)

    if len(starts) != len(segment_defs):
        raise ValueError(f"{path} has {len(starts)} segments, expected {len(segment_defs)}")

    return [
        {
            "displayRef": normalize_segment_def(part)[0],
            "ref": normalize_segment_def(part)[1],
            "text": normalize_segment_def(part)[2],
            "start": round(start, 3),
            "end": round(end, 3),
        }
        for part, start, end in zip(segment_defs, starts, ends)
    ]


def display_segments(segment_defs: Sequence[Sequence[str]]) -> List[Dict[str, str]]:
    display = []
    by_ref = {}
    for part in segment_defs:
        display_ref, _, text = normalize_segment_def(part)
        if display_ref not in by_ref:
            row = {"ref": display_ref, "text": text}
            by_ref[display_ref] = row
            display.append(row)
        elif text and text[0].islower():
            by_ref[display_ref]["text"] = f"{by_ref[display_ref]['text']} {text}"
        else:
            by_ref[display_ref]["text"] = f"{by_ref[display_ref]['text']} {text}"
    return display


def build_manifest(output_dir: Path) -> Dict[str, object]:
    assets = []
    for asset in ASSETS:
        audio_path = output_dir / asset["file"]
        info = sf.info(str(audio_path))
        assets.append(
            {
                "id": asset["id"],
                "passage": "Psalm 23",
                "range": "Psalm 23:1-6",
                "voice": asset["voice"],
                "label": asset["label"],
                "file": asset["file"],
                "duration": round(info.duration, 3),
                "settings": asset["settings"],
                "displaySegments": display_segments(asset["segments"]),
                "segments": detect_silence_schedule(
                    audio_path, asset["segments"], asset.get("minSilenceMs", 240)
                ),
            }
        )
    return {"version": 1, "assets": assets}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build pre-rendered TTS asset manifest")
    parser.add_argument("--output-dir", type=Path, default=Path("examples/tts/output"))
    parser.add_argument("--manifest", default="assets.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args.output_dir)
    path = args.output_dir / args.manifest
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
