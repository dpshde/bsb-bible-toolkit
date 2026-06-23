#!/usr/bin/env python3
"""Prebuild BSB TTS WAV assets with the mlx-audio CLI."""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.request import urlopen


DEFAULT_JSONL = "https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s"
DEFAULT_MODEL = "mlx-community/Kokoro-82M-bf16"
DEFAULT_OUT_DIR = Path("examples/tts/output")

PUNCTUATION_PAUSE_MS = {
    ",": 45,
    '"': 70,
    "'": 70,
    ";": 110,
    "-": 150,
    ":": 190,
    ".": 320,
    "?": 320,
    "!": 320,
}

REPLACEMENTS = (
    ("LORD", "Lord"),
    ("\u2014", "-"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2018", "'"),
    ("\u2019", "'"),
)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def read_jsonl(source: str) -> Iterable[Dict[str, object]]:
    if source.startswith(("http://", "https://")):
        with urlopen(source, timeout=120) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if line:
                    yield json.loads(line)
        return

    with Path(source).open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def load_chapter(source: str, book: str, chapter: str) -> List[Dict[str, object]]:
    verses = [
        row
        for row in read_jsonl(source)
        if str(row.get("book", "")).casefold() == book.casefold()
        and str(row.get("chapter", "")) == str(chapter)
    ]
    verses.sort(key=lambda row: int(str(row.get("verseNum", "0"))))
    return verses


def normalize_text(text: str) -> str:
    for source, target in REPLACEMENTS:
        text = text.replace(source, target)
    return re.sub(r"\s+", " ", text).strip()


def split_punctuation(text: str) -> List[Dict[str, object]]:
    chunks = []
    cursor = 0
    index = 0
    while index < len(text):
        char = text[index]
        pause_ms = PUNCTUATION_PAUSE_MS.get(char)
        if pause_ms is not None:
            end = index + 1
            while end < len(text) and text[end] in {"'", '"'}:
                pause_ms = max(pause_ms, PUNCTUATION_PAUSE_MS[text[end]])
                end += 1
            chunk = text[cursor:end].strip()
            if chunk:
                chunks.append({"text": chunk, "pause_ms": pause_ms})
            cursor = end
        index += 1

    tail = text[cursor:].strip()
    if tail:
        chunks.append({"text": tail, "pause_ms": 0})
    return chunks


def build_segments(book: str, chapter: str, verses: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    rows = [{"displayRef": "Title", "baseRef": "Title", "text": f"{book} {chapter}."}]
    rows.extend(
        {
            "displayRef": str(verse["ref"]),
            "baseRef": str(verse["ref"]),
            "text": str(verse["text"]),
        }
        for verse in verses
    )

    segments = []
    for row in rows:
        chunks = split_punctuation(normalize_text(str(row["text"])))
        for index, chunk in enumerate(chunks):
            timing_ref = row["baseRef"]
            if len(chunks) > 1 and timing_ref != "Title":
                timing_ref = f"{timing_ref}.{index + 1}"
            segments.append(
                {
                    "displayRef": row["displayRef"],
                    "ref": timing_ref,
                    "text": chunk["text"],
                    "pause_ms": chunk["pause_ms"],
                }
            )
    if segments:
        segments[-1]["pause_ms"] = 0
    return segments


def run_mlx_generate(
    python_bin: str,
    model: str,
    text: str,
    voice: str,
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = str(output_dir / "seg")
    subprocess.run(
        [
            python_bin,
            "-m",
            "mlx_audio.tts.generate",
            "--model",
            model,
            "--text",
            text,
            "--voice",
            voice,
            "--lang_code",
            "a",
            "--file_prefix",
            file_prefix,
            "--join_audio",
        ],
        check=True,
    )
    wavs = sorted(output_dir.glob("*.wav"), key=lambda path: path.stat().st_mtime)
    if not wavs:
        raise RuntimeError(f"mlx-audio did not write a WAV file in {output_dir}")
    return wavs[-1]


def prebuild_voice(args: argparse.Namespace, voice: str, segments: Sequence[Dict[str, object]]) -> Path:
    import numpy as np
    import soundfile as sf

    audio_chunks = []
    sample_rate = None
    with tempfile.TemporaryDirectory(prefix="bsb-mlx-tts-") as tmp:
        tmp_dir = Path(tmp)
        for index, segment in enumerate(segments, start=1):
            segment_dir = tmp_dir / f"{index:03d}"
            wav_path = run_mlx_generate(
                args.python_bin,
                args.model,
                str(segment["text"]),
                voice,
                segment_dir,
            )
            audio, sr = sf.read(str(wav_path), always_2d=False)
            sample_rate = sample_rate or sr
            if sr != sample_rate:
                raise RuntimeError(f"Sample rate changed from {sample_rate} to {sr}")
            audio_chunks.append(audio)
            pause_ms = int(segment.get("pause_ms", 0))
            if pause_ms > 0 and index < len(segments):
                audio_chunks.append(np.zeros(int(sample_rate * pause_ms / 1000), dtype=audio.dtype))

    output_path = args.out_dir / f"{slugify(args.book)}-{args.chapter}" / f"mlx-{voice}-punctuation-paused.wav"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), np.concatenate(audio_chunks), sample_rate)
    return output_path


def write_segment_manifest(args: argparse.Namespace, segments: Sequence[Dict[str, object]]) -> None:
    path = args.out_dir / f"{slugify(args.book)}-{args.chapter}" / "mlx-punctuation-segments.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": args.model,
        "book": args.book,
        "chapter": str(args.chapter),
        "punctuationPauseMs": PUNCTUATION_PAUSE_MS,
        "segments": list(segments),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prebuild BSB TTS assets with mlx-audio")
    parser.add_argument("--jsonl", default=DEFAULT_JSONL)
    parser.add_argument("--book", default="Psalm")
    parser.add_argument("--chapter", default="23")
    parser.add_argument("--voice", action="append", default=["af_heart", "bm_george"])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--python-bin", default=sys.executable)
    parser.add_argument("--skip-missing-cli", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not shutil.which(args.python_bin):
        print(f"Python executable not found: {args.python_bin}", file=sys.stderr)
        return 1

    try:
        subprocess.run(
            [args.python_bin, "-c", "import mlx_audio"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        message = "mlx-audio is not installed in the selected Python environment"
        if args.skip_missing_cli:
            print(message)
            return 0
        print(message, file=sys.stderr)
        return 1

    verses = load_chapter(args.jsonl, args.book, args.chapter)
    if not verses:
        print(f"No verses found for {args.book} {args.chapter}", file=sys.stderr)
        return 1

    segments = build_segments(args.book, args.chapter, verses)
    write_segment_manifest(args, segments)
    for voice in args.voice:
        path = prebuild_voice(args, voice, segments)
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
