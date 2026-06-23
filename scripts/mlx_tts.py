#!/usr/bin/env python3
"""MLX-accelerated BSB TTS CLI with checkpointing and progressive output.

Subcommands:
  generate   Render a passage (book/chapter or free text) for one or more voices.
  resume     Finish any incomplete checkpoints in an output directory.
  voices     List known Kokoro voices (offline static list, or probe mlx-audio).
  manifest   Write an assets.json-compatible segment manifest for listen.html.

Checkpointing:
  Each voice render writes `<out>/<book>-<chapter>/.checkpoint-<voice>.json`
  listing per-segment completion. Re-running `generate` (default) or `resume`
  picks up at the first unfinished segment. Use --fresh to discard checkpoints.

Progressive output:
  Each completed segment is appended to the destination WAV immediately, so the
  file grows segment-by-segment and can be auditioned mid-run. Optional
  --play-as-you-go pipes each new chunk to `afplay` on macOS.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

DEFAULT_JSONL = "https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s"
DEFAULT_MODEL = "mlx-community/Kokoro-82M-bf16"
DEFAULT_OUT_DIR = Path("examples/tts/output")

KOKORO_VOICES = (
    "af_heart", "af_bella", "af_nicole", "af_sky", "af_sarah",
    "am_adam", "am_michael", "am_george", "bm_george", "bm_fable",
)

QUANT_MAP = {
    "bf16": "mlx-community/Kokoro-82M-bf16",
    "8bit": "mlx-community/Kokoro-82M-8bit",
    "4bit": "mlx-community/Kokoro-82M-4bit",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def read_jsonl(source: str) -> Iterable[Dict[str, object]]:
    if source.startswith(("http://", "https://")):
        from urllib.request import urlopen

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


# Text normalization applied before TTS to smooth Kokoro's phonemizer quirks.
SPEECH_NORMALIZATIONS = (
    ("\u2014", "-"),
    ("\u2013", "-"),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2018", "'"),
    ("\u2019", "'"),
)


def normalize_for_speech(text: str) -> str:
    """Normalize text for smoother TTS prosody."""
    for source, target in SPEECH_NORMALIZATIONS:
        text = text.replace(source, target)
    return text


def load_chapter(source: str, book: str, chapter: str) -> List[Dict[str, object]]:
    verses = [
        row
        for row in read_jsonl(source)
        if str(row.get("book", "")).casefold() == book.casefold()
        and str(row.get("chapter", "")) == str(chapter)
    ]
    verses.sort(key=lambda row: int(str(row.get("verseNum", "0"))))
    return verses


def split_punctuation(text: str, pause_ms_map: Dict[str, int]) -> List[Dict[str, object]]:
    chunks: List[Dict[str, object]] = []
    cursor = 0
    index = 0
    while index < len(text):
        char = text[index]
        pause_ms = pause_ms_map.get(char)
        if pause_ms is not None:
            end = index + 1
            while end < len(text) and text[end] in {"'", '"'}:
                pause_ms = max(pause_ms, pause_ms_map.get(text[end], 0))
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


def build_segments(
    book: str,
    chapter: str,
    verses: Sequence[Dict[str, object]],
    pause_ms_map: Dict[str, int],
    text: Optional[str] = None,
    verse_end_pause_ms: Optional[int] = None,
) -> List[Dict[str, object]]:
    if text is not None:
        rows = [{"displayRef": "Title", "baseRef": "Title", "text": normalize_for_speech(text)}]
    else:
        rows = [{"displayRef": "Title", "baseRef": "Title", "text": normalize_for_speech(f"{book} {chapter}.")}]
        rows.extend(
            {
                "displayRef": str(v["ref"]),
                "baseRef": str(v["ref"]),
                "text": normalize_for_speech(str(v["text"])),
            }
            for v in verses
        )

    segments: List[Dict[str, object]] = []
    for row in rows:
        # Render each verse as a single segment - let Kokoro's prosody handle
        # internal punctuation naturally instead of splitting into chunks.
        segments.append(
            {
                "displayRef": str(row["displayRef"]),
                "ref": str(row["baseRef"]),
                "text": str(row["text"]),
                "pause_ms": 0,
            }
        )

    # Override verse-boundary pauses: the last segment of each verse gets
    # a controlled pause instead of whatever the terminal punctuation maps to.
    if verse_end_pause_ms is not None:
        prev_ref = None
        for i, seg in enumerate(segments):
            ref = str(seg["displayRef"])
            if prev_ref is not None and ref != prev_ref:
                # This is the first segment of a new verse, so the previous
                # segment (last of the previous verse) gets the verse-end pause.
                segments[i - 1]["pause_ms"] = verse_end_pause_ms
            prev_ref = ref

    if segments:
        segments[-1]["pause_ms"] = 0
    return segments


def ensure_mlx_audio(python_bin: str) -> None:
    try:
        subprocess.run(
            [python_bin, "-c", "import mlx_audio"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            "mlx-audio is not installed in the selected Python environment. "
            "Install with: uv pip install mlx-audio \"misaki[en]\""
        ) from exc


def run_mlx_generate(
    python_bin: str,
    model: str,
    text: str,
    voice: str,
    output_dir: Path,
    lang_code: str = "a",
    max_chars: int = 300,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_prefix = str(output_dir / "seg")

    chunks = _split_long_text(text, max_chars)

    wav_index = 0
    for chunk in chunks:
        part_prefix = f"{file_prefix}_{wav_index}" if len(chunks) > 1 else file_prefix
        part_prefix_glob = f"{part_prefix}*.wav"
        result = subprocess.run(
            [
                python_bin,
                "-m",
                "mlx_audio.tts.generate",
                "--model",
                model,
                "--text",
                chunk,
                "--voice",
                voice,
                "--lang_code",
                lang_code,
                "--file_prefix",
                part_prefix,
                "--join_audio",
            ],
            capture_output=True,
            text=True,
        )
        # mlx-audio may exit 0 even on internal errors, so check if a WAV was written.
        part_wavs = sorted(output_dir.glob(f"{Path(part_prefix).name}*.wav"))
        crashed = result.returncode != 0 or len(part_wavs) == 0
        if crashed:
            # mlx-audio has a known shape mismatch bug triggered by specific
            # phoneme counts, not text length. Retry with progressively smaller
            # word-level splits until each sub-chunk succeeds.
            sub_chunks = _split_long_text(chunk, 40)
            if len(sub_chunks) <= 1:
                sub_chunks = chunk.split()

            sub_texts: List[str] = []
            current = ""
            for word in sub_chunks:
                candidate = f"{current} {word}".strip()
                if len(candidate) <= 40:
                    current = candidate
                else:
                    if current:
                        sub_texts.append(current)
                    current = word
            if current:
                sub_texts.append(current)

            for sub in sub_texts:
                sub_prefix = f"{part_prefix}_sub{wav_index}_{len(sub)}"
                sub_result = subprocess.run(
                    [
                        python_bin,
                        "-m",
                        "mlx_audio.tts.generate",
                        "--model",
                        model,
                        "--text",
                        sub,
                        "--voice",
                        voice,
                        "--lang_code",
                        lang_code,
                        "--file_prefix",
                        sub_prefix,
                        "--join_audio",
                    ],
                    capture_output=True,
                    text=True,
                )
                if sub_result.returncode != 0:
                    raise RuntimeError(f"mlx-audio failed on sub-chunk ({len(sub)} chars): {sub!r}")
        wav_index += 1

    wavs = sorted(output_dir.glob("*.wav"), key=lambda path: path.stat().st_mtime)
    if not wavs:
        raise RuntimeError(f"mlx-audio did not write a WAV file in {output_dir}")

    # If multiple chunks were generated, join them.
    if len(wavs) > 1:
        import numpy as np
        import soundfile as sf

        combined = []
        sr = None
        for wav in sorted(wavs):
            audio, sample_rate = sf.read(str(wav), always_2d=False)
            sr = sr or sample_rate
            combined.append(audio)
            wav.unlink()
        joined = np.concatenate(combined)
        joined_path = output_dir / "seg_joined.wav"
        sf.write(str(joined_path), joined, sr)
        return joined_path

    return wavs[0]


def _split_long_text(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    for sentence in re.split(r"(?<=[;,.])\s+", text):
        if not sentence.strip():
            continue
        if len(sentence) <= max_chars:
            chunks.append(sentence.strip())
        else:
            words = sentence.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        chunks.append(current)
                    current = word
            if current:
                chunks.append(current)
    return chunks or [text]


def checkpoint_path(out_dir: Path, chapter_dir: str, voice: str) -> Path:
    return out_dir / chapter_dir / f".checkpoint-{slugify(voice)}.json"


def load_checkpoint(path: Path, total: int) -> Dict[str, Any]:
    if not path.exists():
        return {"segments": [False] * total, "sample_rate": None, "completed": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"segments": [False] * total, "sample_rate": None, "completed": []}
    flags = data.get("segments", [])
    if len(flags) != total:
        flags = [False] * total
    data["segments"] = flags
    data.setdefault("sample_rate", None)
    data.setdefault("completed", [])
    return data


def save_checkpoint(path: Path, state: Dict[str, Any]) -> None:
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def append_segment_audio(
    output_wav: Path,
    segment_wav: Path,
    pause_ms: int,
    sample_rate: Optional[int],
) -> Optional[int]:
    import numpy as np
    import soundfile as sf

    audio, sr = sf.read(str(segment_wav), always_2d=False)
    if sample_rate is None:
        sample_rate = sr
        sf.write(str(output_wav), audio, sr)
    else:
        if sr != sample_rate:
            raise RuntimeError(f"Sample rate changed from {sample_rate} to {sr}")
        existing, _ = sf.read(str(output_wav), always_2d=False)
        pause = np.zeros(int(sample_rate * pause_ms / 1000), dtype=audio.dtype) if pause_ms > 0 else None
        combined = np.concatenate([x for x in (existing, pause, audio) if x is not None])
        sf.write(str(output_wav), combined, sample_rate)
    return sample_rate


def play_async(path: Path) -> None:
    player = shutil.which("afplay")
    if not player:
        return
    subprocess.Popen([player, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h{mins:02d}m"


def _generate_in_memory(
    model,
    text: str,
    voice: str,
    lang_code: str,
    max_chars: int = 300,
) -> tuple:
    """Generate audio in-process, retrying with progressively smaller splits on crash."""
    import numpy as np

    chunks = _split_long_text(text, max_chars)
    audio_parts = []

    for chunk in chunks:
        audio = _try_generate(model, chunk, voice, lang_code)
        if audio is not None:
            audio_parts.append(audio)

    if not audio_parts:
        raise RuntimeError("mlx-audio produced no audio for any chunk")
    return np.concatenate(audio_parts), 24000


def _try_generate(model, text: str, voice: str, lang_code: str, depth: int = 0) -> Optional["np.ndarray"]:
    """Try to generate audio, splitting on failure. Returns None if all attempts fail."""
    import numpy as np

    # Try the full text first
    try:
        audio = _generate_chunk(model, text, voice, lang_code)
        if audio is not None and len(audio) > 0:
            return audio
    except Exception:
        pass

    if depth >= 4:
        return None

    # Split at clause boundaries: semicolons, commas, periods
    split_points = [";", ",", ".", ":", " and ", " for ", " but "]
    for sep in split_points:
        if sep in text:
            parts = [p.strip() for p in text.split(sep) if p.strip()]
            if len(parts) > 1:
                results = []
                for part in parts:
                    sub = _try_generate(model, part, voice, lang_code, depth + 1)
                    if sub is not None:
                        results.append(sub)
                if results:
                    return np.concatenate(results)

    # Last resort: word-level splitting
    words = text.split()
    if len(words) <= 1:
        return None
    mid = len(words) // 2
    left = _try_generate(model, " ".join(words[:mid]), voice, lang_code, depth + 1)
    right = _try_generate(model, " ".join(words[mid:]), voice, lang_code, depth + 1)
    parts = [a for a in [left, right] if a is not None]
    if parts:
        return np.concatenate(parts)

    return None


def _trim_silence(audio, threshold: float = 0.005, sample_rate: int = 24000, min_keep_ms: int = 20):
    """Trim leading and trailing near-silence from audio, keeping a small buffer."""
    import numpy as np

    if audio is None or len(audio) == 0:
        return audio

    abs_audio = np.abs(audio)
    min_keep = int(sample_rate * min_keep_ms / 1000)

    # Find first non-silent sample
    start = 0
    for i in range(len(abs_audio)):
        if abs_audio[i] >= threshold:
            start = max(0, i - min_keep)
            break

    # Find last non-silent sample
    end = len(audio)
    for i in range(len(abs_audio) - 1, -1, -1):
        if abs_audio[i] >= threshold:
            end = min(len(audio), i + min_keep)
            break

    if start >= end:
        return audio

    return audio[start:end]


def _generate_chunk(model, text: str, voice: str, lang_code: str):
    """Generate audio for a single text chunk using the loaded model."""
    import mlx.core as mx

    audio_out = None
    for chunk in model.generate(text=text, voice=voice, lang_code=lang_code):
        a = chunk.audio
        if hasattr(a, "detach"):
            a = a.detach()
        if hasattr(a, "to_numpy"):
            a = a.to_numpy()
        elif hasattr(a, "numpy"):
            a = a.numpy()
        else:
            import numpy as np
            a = np.array(a)
        if audio_out is None:
            audio_out = a
        else:
            import numpy as np
            audio_out = np.concatenate([audio_out, a])

    # Trim Kokoro's leading/trailing silence (~350-460ms padding per call)
    return _trim_silence(audio_out)


def render_voice_progressive(
    args: argparse.Namespace,
    voice: str,
    segments: Sequence[Dict[str, object]],
    chapter_dir_name: str,
    ckpt_state: Dict[str, Any],
) -> Path:
    import numpy as np
    import soundfile as sf

    output_wav = args.out_dir / chapter_dir_name / f"mlx-{slugify(voice)}-punctuation-paused.wav"
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    ckpt_file = checkpoint_path(args.out_dir, chapter_dir_name, voice)
    sample_rate: Optional[int] = ckpt_state.get("sample_rate") or 24000
    completed_indices: List[int] = list(ckpt_state.get("completed", []))

    total = len(segments)
    done = sum(ckpt_state["segments"])
    print(
        f"[{voice}] {done}/{total} segments already complete",
        file=sys.stderr, flush=True,
    )

    # Load the model ONCE and keep it in memory for all segments.
    print(f"[{voice}] loading model {args.model}...", file=sys.stderr, flush=True)
    from mlx_audio.tts.utils import load_model
    model = load_model(args.model)
    # Warm up the model with a short text.
    _generate_chunk(model, "warmup", voice, args.lang_code)
    print(f"[{voice}] model ready", file=sys.stderr, flush=True)

    seg_times: List[float] = []
    run_start = time.monotonic()

    for index, segment in enumerate(segments):
        if ckpt_state["segments"][index]:
            continue

        seg_start = time.monotonic()
        try:
            audio, sr = _generate_in_memory(
                model,
                str(segment["text"]),
                voice,
                args.lang_code,
            )

            pause_ms = int(segment.get("pause_ms", 0)) if index < len(segments) - 1 else 0
            # Append directly to the output WAV without reading the whole file.
            if not output_wav.exists():
                sf.write(str(output_wav), audio, sr)
                sample_rate = sr
            else:
                existing, _ = sf.read(str(output_wav), always_2d=False)
                pause = np.zeros(int(sr * pause_ms / 1000), dtype=audio.dtype) if pause_ms > 0 else None
                combined = np.concatenate([x for x in (existing, pause, audio) if x is not None])
                sf.write(str(output_wav), combined, sr)

            if args.play_as_you_go:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_wav:
                    sf.write(tmp_wav.name, audio, sr)
                    play_async(Path(tmp_wav.name))
        except Exception as exc:
            preview = str(segment["text"])[:60]
            print(
                f"[{voice}] SKIP {index + 1}/{total} {preview}... ({exc})",
                file=sys.stderr, flush=True,
            )
            seg_elapsed = time.monotonic() - seg_start
            seg_times.append(seg_elapsed)
            ckpt_state["segments"][index] = True
            completed_indices.append(index)
            ckpt_state["completed"] = completed_indices
            ckpt_state["sample_rate"] = sample_rate
            save_checkpoint(ckpt_file, ckpt_state)
            continue

        seg_elapsed = time.monotonic() - seg_start
        seg_times.append(seg_elapsed)

        ckpt_state["segments"][index] = True
        ckpt_state["sample_rate"] = sample_rate
        completed_indices.append(index)
        ckpt_state["completed"] = completed_indices
        ckpt_state["last_seg_seconds"] = round(seg_elapsed, 2)
        save_checkpoint(ckpt_file, ckpt_state)

        try:
            duration = sf.info(str(output_wav)).duration
        except Exception:
            duration = 0.0

        done_now = sum(ckpt_state["segments"])
        left_now = total - done_now
        avg_seg = sum(seg_times) / len(seg_times)
        eta_seconds = avg_seg * left_now
        elapsed = time.monotonic() - run_start
        preview = str(segment["text"])[:60]
        print(
            f"[{voice}] +{done_now}/{total} {preview}... "
            f"audio={duration:.1f}s "
            f"seg={seg_elapsed:.1f}s "
            f"avg={avg_seg:.1f}s "
            f"elapsed={format_duration(elapsed)} "
            f"ETA={format_duration(eta_seconds)} "
            f"({left_now} left)",
            file=sys.stderr, flush=True,
        )

    if all(ckpt_state["segments"]):
        ckpt_file.unlink(missing_ok=True)
        total_elapsed = time.monotonic() - run_start
        try:
            final_duration = sf.info(str(output_wav)).duration
        except Exception:
            final_duration = 0.0
        print(
            f"[{voice}] done: {total} segments, "
            f"audio={final_duration:.1f}s, "
            f"rendered in {format_duration(total_elapsed)}",
            file=sys.stderr, flush=True,
        )
    return output_wav


def write_segment_manifest(
    out_dir: Path,
    chapter_dir_name: str,
    model: str,
    book: str,
    chapter: str,
    segments: Sequence[Dict[str, object]],
    pause_ms_map: Dict[str, int],
) -> Path:
    path = out_dir / chapter_dir_name / "mlx-punctuation-segments.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "model": model,
        "book": book,
        "chapter": str(chapter),
        "punctuationPauseMs": pause_ms_map,
        "segments": list(segments),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


# Intelligent rendering order: Gospels first, then Epistles, rest of NT,
# Creation/Torah, Wisdom, Poetry, and the rest of the OT.
SEQUENCE_ORDER = [
    # Gospels
    "Matthew", "Mark", "Luke", "John",
    # Acts
    "Acts",
    # Pauline Epistles
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon",
    # General Epistles
    "Hebrews", "James", "1 Peter", "2 Peter",
    "1 John", "2 John", "3 John", "Jude",
    # Revelation
    "Revelation",
    # Torah / Creation
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
    # Wisdom
    "Job", "Ecclesiastes", "Song Of Solomon",
    # Poetry
    "Psalms", "Psalm", "Proverbs", "Lamentations",
    # Historical OT
    "Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Kings", "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra",
    "Nehemiah", "Esther",
    # Major Prophets
    "Isaiah", "Jeremiah", "Ezekiel", "Daniel",
    # Minor Prophets
    "Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah",
    "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi",
]


def _load_jsonl_index(source: str) -> Dict[str, List[str]]:
    """Return {book: [chapter, ...]} from a JSONL source, sorted."""
    index: Dict[str, set] = {}
    for row in read_jsonl(source):
        book = str(row.get("book", ""))
        chapter = str(row.get("chapter", ""))
        index.setdefault(book, set()).add(chapter)
    return {book: sorted(chs, key=lambda c: int(c) if c.isdigit() else c) for book, chs in sorted(index.items())}


def _sort_by_sequence(books: List[str]) -> List[str]:
    """Sort book names by SEQUENCE_ORDER, unknown books last alphabetically."""
    priority = {name: i for i, name in enumerate(SEQUENCE_ORDER)}
    return sorted(books, key=lambda b: (priority.get(b, 999), b))


def _resolve_chapter_list(args: argparse.Namespace) -> List[tuple]:
    """Return [(book, chapter), ...] based on batch flags."""
    if args.sequence:
        index = _load_jsonl_index(args.jsonl)
        chapters = []
        for book in _sort_by_sequence(list(index.keys())):
            for ch in index[book]:
                chapters.append((book, ch))
        return chapters

    if args.all:
        index = _load_jsonl_index(args.jsonl)
        chapters = []
        for book, chs in index.items():
            for ch in chs:
                chapters.append((book, ch))
        return chapters

    if args.books:
        index = _load_jsonl_index(args.jsonl)
        wanted = [b.strip() for b in args.books.split(",")]
        chapters = []
        for book in wanted:
            if book in index:
                for ch in index[book]:
                    chapters.append((book, ch))
            else:
                print(f"Warning: book '{book}' not found in JSONL", file=sys.stderr, flush=True)
        return chapters

    if args.range:
        # Format: "Psalm 1-5" or "John 3-4, Romans 1-2"
        chapters = []
        for part in args.range.split(","):
            part = part.strip()
            if not part:
                continue
            tokens = part.split()
            if len(tokens) != 2:
                print(f"Warning: ignoring range '{part}' (expected 'Book N-M')", file=sys.stderr, flush=True)
                continue
            book, ch_range = tokens
            if "-" in ch_range:
                start, end = ch_range.split("-", 1)
                for ch in range(int(start), int(end) + 1):
                    chapters.append((book, str(ch)))
            else:
                chapters.append((book, ch_range))
        return chapters

    return [(args.book, args.chapter)]


def _render_chapter_with_model(
    args: argparse.Namespace,
    model,
    voice: str,
    book: str,
    chapter: str,
    segments: Sequence[Dict[str, object]],
    chapter_dir_name: str,
    ckpt_state: Dict[str, Any],
) -> Path:
    """Render one chapter using an already-loaded model."""
    import numpy as np
    import soundfile as sf

    output_wav = args.out_dir / chapter_dir_name / f"mlx-{slugify(voice)}-punctuation-paused.wav"
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    ckpt_file = checkpoint_path(args.out_dir, chapter_dir_name, voice)
    sample_rate: Optional[int] = ckpt_state.get("sample_rate") or 24000
    completed_indices: List[int] = list(ckpt_state.get("completed", []))
    total = len(segments)

    seg_times: List[float] = []

    for index, segment in enumerate(segments):
        if ckpt_state["segments"][index]:
            continue

        seg_start = time.monotonic()
        try:
            audio, sr = _generate_in_memory(
                model,
                str(segment["text"]),
                voice,
                args.lang_code,
            )

            pause_ms = int(segment.get("pause_ms", 0)) if index < len(segments) - 1 else 0
            if not output_wav.exists():
                sf.write(str(output_wav), audio, sr)
                sample_rate = sr
            else:
                existing, _ = sf.read(str(output_wav), always_2d=False)
                pause = np.zeros(int(sr * pause_ms / 1000), dtype=audio.dtype) if pause_ms > 0 else None
                combined = np.concatenate([x for x in (existing, pause, audio) if x is not None])
                sf.write(str(output_wav), combined, sr)
        except Exception as exc:
            preview = str(segment["text"])[:60]
            print(
                f"[{voice}] SKIP {chapter_dir_name} {index + 1}/{total} {preview}... ({exc})",
                file=sys.stderr, flush=True,
            )
            seg_elapsed = time.monotonic() - seg_start
            seg_times.append(seg_elapsed)
            ckpt_state["segments"][index] = True
            completed_indices.append(index)
            ckpt_state["completed"] = completed_indices
            ckpt_state["sample_rate"] = sample_rate
            save_checkpoint(ckpt_file, ckpt_state)
            continue

        seg_elapsed = time.monotonic() - seg_start
        seg_times.append(seg_elapsed)

        ckpt_state["segments"][index] = True
        ckpt_state["sample_rate"] = sample_rate
        completed_indices.append(index)
        ckpt_state["completed"] = completed_indices
        ckpt_state["last_seg_seconds"] = round(seg_elapsed, 2)
        save_checkpoint(ckpt_file, ckpt_state)

    if all(ckpt_state["segments"]):
        ckpt_file.unlink(missing_ok=True)

    return output_wav


def parse_replace_pairs(pairs: Sequence[str]) -> List[tuple]:
    """Parse --replace flags like 'LORD:Lord' or 'Selah:' into [(find, replace), ...]."""
    result = []
    for pair in pairs:
        if ":" not in pair:
            print(f"Warning: ignoring replacement '{pair}' (expected 'find:replace')", file=sys.stderr, flush=True)
            continue
        find, replace = pair.split(":", 1)
        result.append((find.strip(), replace.strip()))
    return result


def apply_replacements(text: str, replacements: Sequence[tuple]) -> str:
    for find, replace in replacements:
        text = text.replace(find, replace)
    return text


def cmd_replace(args: argparse.Namespace) -> int:
    """Re-render specific chapters with optional text substitutions."""
    if args.quantize and not args.model_overridden:
        args.model = QUANT_MAP.get(args.quantize, args.model)
    elif not args.model:
        args.model = DEFAULT_MODEL

    if not shutil.which(args.python_bin):
        print(f"Python executable not found: {args.python_bin}", file=sys.stderr, flush=True)
        return 1

    try:
        ensure_mlx_audio(args.python_bin)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 1

    # Parse chapter list from --chapters "John 3,Psalm 23,Matthew 5"
    chapter_targets = []
    for part in args.chapters.split(","):
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        if len(tokens) != 2:
            print(f"Warning: ignoring '{part}' (expected 'Book Chapter')", file=sys.stderr, flush=True)
            continue
        chapter_targets.append((tokens[0], tokens[1]))

    if not chapter_targets:
        print("No chapters specified. Use --chapters 'John 3,Psalm 23'", file=sys.stderr, flush=True)
        return 1

    replacements = parse_replace_pairs(args.replace or [])

    pause_ms_map = build_pause_map(args)

    print(f"REPLACE: {len(chapter_targets)} chapter(s) x {len(args.voice)} voice(s)", file=sys.stderr, flush=True)
    if replacements:
        print(f"Replacements: {replacements}", file=sys.stderr, flush=True)

    # Load model once.
    print(f"Loading model {args.model}...", file=sys.stderr, flush=True)
    from mlx_audio.tts.utils import load_model
    model = load_model(args.model)
    for voice in args.voice:
        _generate_chunk(model, "warmup", voice, args.lang_code)
    print("Model ready", file=sys.stderr, flush=True)

    batch_start = time.monotonic()
    done_count = 0
    total_targets = len(chapter_targets) * len(args.voice)

    for book, chapter in chapter_targets:
        verses = load_chapter(args.jsonl, book, chapter)
        if not verses:
            print(f"SKIP {book} {chapter}: no verses found", file=sys.stderr, flush=True)
            continue

        # Apply text replacements to verse text before building segments.
        if replacements:
            for verse in verses:
                verse["text"] = apply_replacements(str(verse["text"]), replacements)

        segments = build_segments(book, chapter, verses, pause_ms_map, verse_end_pause_ms=args.p_verse_end)
        chapter_dir_name = f"{slugify(book)}-{chapter}"

        for voice in args.voice:
            # Force fresh: delete old checkpoint and WAV for this chapter-voice.
            ckpt_file = checkpoint_path(args.out_dir, chapter_dir_name, voice)
            ckpt_file.unlink(missing_ok=True)
            old_wav = args.out_dir / chapter_dir_name / f"mlx-{slugify(voice)}-punctuation-paused.wav"
            old_wav.unlink(missing_ok=True)

            ckpt_state = load_checkpoint(ckpt_file, len(segments))
            output_wav = _render_chapter_with_model(
                args, model, voice, book, chapter, segments, chapter_dir_name, ckpt_state,
            )

            try:
                import soundfile as sf
                dur = sf.info(str(output_wav)).duration
            except Exception:
                dur = 0.0

            done_count += 1
            elapsed = time.monotonic() - batch_start
            remaining = total_targets - done_count
            avg = elapsed / done_count if done_count else 0
            eta = avg * remaining
            print(
                f"REPLACE +{done_count}/{total_targets} "
                f"{book} {chapter} [{voice}] {dur:.1f}s audio "
                f"elapsed={format_duration(elapsed)} "
                f"ETA={format_duration(eta)}",
                file=sys.stderr, flush=True,
            )

        if not args.skip_manifest:
            write_segment_manifest(
                args.out_dir, chapter_dir_name, args.model,
                book, chapter, segments, pause_ms_map,
            )

    total_elapsed = time.monotonic() - batch_start
    print(f"REPLACE done: {done_count} render(s), {format_duration(total_elapsed)}", file=sys.stderr, flush=True)
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    if args.quantize and not args.model_overridden:
        args.model = QUANT_MAP.get(args.quantize, args.model)
    elif not args.model:
        args.model = DEFAULT_MODEL

    if not shutil.which(args.python_bin):
        print(f"Python executable not found: {args.python_bin}", file=sys.stderr, flush=True)
        return 1

    try:
        ensure_mlx_audio(args.python_bin)
    except RuntimeError as exc:
        if args.skip_missing_cli:
            print(str(exc))
            return 0
        print(str(exc), file=sys.stderr, flush=True)
        return 1

    chapter_list = _resolve_chapter_list(args)
    if not chapter_list:
        print("No chapters to render", file=sys.stderr, flush=True)
        return 1

    pause_ms_map = build_pause_map(args)
    total_chapters = len(chapter_list)
    print(
        f"BATCH: {total_chapters} chapter(s) x {len(args.voice)} voice(s)",
        file=sys.stderr, flush=True,
    )

    # Load model ONCE for the entire batch.
    print(f"Loading model {args.model}...", file=sys.stderr, flush=True)
    from mlx_audio.tts.utils import load_model
    model = load_model(args.model)
    # Warm up per voice.
    for voice in args.voice:
        _generate_chunk(model, "warmup", voice, args.lang_code)
    print("Model ready", file=sys.stderr, flush=True)

    batch_start = time.monotonic()
    chapters_done = 0
    total_segs_done = 0

    for ci, (book, chapter) in enumerate(chapter_list):
        verses = load_chapter(args.jsonl, book, chapter)
        if args.max_verses > 0:
            verses = verses[: args.max_verses]
        if not verses:
            print(f"SKIP {book} {chapter}: no verses", file=sys.stderr, flush=True)
            continue

        segments = build_segments(book, chapter, verses, pause_ms_map, verse_end_pause_ms=args.p_verse_end)
        chapter_dir_name = f"{slugify(book)}-{chapter}"
        chapter_segs = len(segments)

        for voice in args.voice:
            ckpt_file = checkpoint_path(args.out_dir, chapter_dir_name, voice)
            if args.fresh:
                ckpt_file.unlink(missing_ok=True)
                (args.out_dir / chapter_dir_name / f"mlx-{slugify(voice)}-punctuation-paused.wav").unlink(missing_ok=True)
            ckpt_state = load_checkpoint(ckpt_file, chapter_segs)

            output_wav = _render_chapter_with_model(
                args, model, voice, book, chapter, segments, chapter_dir_name, ckpt_state,
            )

            try:
                import soundfile as sf
                dur = sf.info(str(output_wav)).duration
            except Exception:
                dur = 0.0

            total_segs_done += sum(ckpt_state["segments"])
            chapters_done += 1
            elapsed = time.monotonic() - batch_start
            remaining = total_chapters * len(args.voice) - chapters_done
            avg_per_chapter = elapsed / chapters_done if chapters_done else 0
            eta = avg_per_chapter * remaining
            print(
                f"BATCH +{chapters_done}/{total_chapters * len(args.voice)} "
                f"{book} {chapter} [{voice}] {dur:.1f}s audio "
                f"elapsed={format_duration(elapsed)} "
                f"ETA={format_duration(eta)}",
                file=sys.stderr, flush=True,
            )

        if not args.skip_manifest:
            write_segment_manifest(
                args.out_dir,
                chapter_dir_name,
                args.model,
                book,
                chapter,
                segments,
                pause_ms_map,
            )

    total_elapsed = time.monotonic() - batch_start
    print(
        f"BATCH done: {chapters_done} render(s), "
        f"{total_segs_done} segments, "
        f"{format_duration(total_elapsed)}",
        file=sys.stderr, flush=True,
    )
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    if args.quantize and not args.model_overridden:
        model = QUANT_MAP.get(args.quantize, args.model)
        args.model = model
    elif not args.model:
        args.model = DEFAULT_MODEL

    if not shutil.which(args.python_bin):
        print(f"Python executable not found: {args.python_bin}", file=sys.stderr, flush=True)
        return 1

    try:
        ensure_mlx_audio(args.python_bin)
    except RuntimeError as exc:
        if args.skip_missing_cli:
            print(str(exc))
            return 0
        print(str(exc), file=sys.stderr, flush=True)
        return 1

    pause_ms_map = build_pause_map(args)

    if args.text:
        segments = build_segments("", "", [], pause_ms_map, text=args.text, verse_end_pause_ms=args.p_verse_end)
        chapter_dir_name = slugify(args.text[:40]) or "text"
    else:
        verses = load_chapter(args.jsonl, args.book, args.chapter)
        if args.max_verses > 0:
            verses = verses[: args.max_verses]
        if not verses:
            print(f"No verses found for {args.book} {args.chapter}", file=sys.stderr, flush=True)
            return 1
        segments = build_segments(args.book, args.chapter, verses, pause_ms_map, verse_end_pause_ms=args.p_verse_end)
        chapter_dir_name = f"{slugify(args.book)}-{args.chapter}"

    print(f"Built {len(segments)} segments for {chapter_dir_name}", file=sys.stderr, flush=True)

    for voice in args.voice:
        ckpt_file = checkpoint_path(args.out_dir, chapter_dir_name, voice)
        if args.fresh:
            ckpt_file.unlink(missing_ok=True)
            (args.out_dir / chapter_dir_name / f"mlx-{slugify(voice)}-punctuation-paused.wav").unlink(
                missing_ok=True
            )
        ckpt_state = load_checkpoint(ckpt_file, len(segments))
        output_wav = render_voice_progressive(args, voice, segments, chapter_dir_name, ckpt_state)
        print(f"Wrote {output_wav}")

    if not args.skip_manifest and not args.text:
        manifest_path = write_segment_manifest(
            args.out_dir,
            chapter_dir_name,
            args.model,
            args.book,
            args.chapter,
            segments,
            pause_ms_map,
        )
        print(f"Wrote {manifest_path}")

    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    if not args.out_dir.exists():
        print(f"Output directory not found: {args.out_dir}", file=sys.stderr, flush=True)
        return 1

    try:
        ensure_mlx_audio(args.python_bin)
    except RuntimeError as exc:
        if args.skip_missing_cli:
            print(str(exc))
            return 0
        print(str(exc), file=sys.stderr, flush=True)
        return 1

    pause_ms_map = build_pause_map(args)
    found = 0
    for ckpt_file in sorted(args.out_dir.rglob(".checkpoint-*.json")):
        found += 1
        try:
            state = json.loads(ckpt_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"Skipping corrupt checkpoint: {ckpt_file}", file=sys.stderr, flush=True)
            continue

        chapter_dir = ckpt_file.parent.name
        voice = ckpt_file.stem.replace(".checkpoint-", "", 1).replace("-", "_", 1)

        manifest_path = ckpt_file.parent / "mlx-punctuation-segments.json"
        if not manifest_path.exists():
            print(f"No manifest alongside {ckpt_file}, cannot resume", file=sys.stderr, flush=True)
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        segments = manifest.get("segments", [])
        total = len(segments)
        if len(state.get("segments", [])) != total:
            state["segments"] = [False] * total
        if all(state["segments"]):
            print(f"[{voice}] already complete in {chapter_dir}", file=sys.stderr, flush=True)
            ckpt_file.unlink(missing_ok=True)
            continue

        resume_args = argparse.Namespace(**vars(args))
        resume_args.model = manifest.get("model", DEFAULT_MODEL)
        resume_args.voice = [voice]
        resume_args.text = None
        resume_args.book = manifest.get("book", "")
        resume_args.chapter = manifest.get("chapter", "")
        resume_args.max_verses = 0
        resume_args.fresh = False
        resume_args.skip_manifest = True

        output_wav = render_voice_progressive(
            resume_args, voice, segments, chapter_dir, state
        )
        print(f"Wrote {output_wav}")

    if found == 0:
        print("No checkpoints found in output directory.", file=sys.stderr, flush=True)
        return 1
    return 0


def cmd_voices(args: argparse.Namespace) -> int:
    if args.probe:
        try:
            result = subprocess.run(
                [args.python_bin, "-m", "mlx_audio.tts.generate", "--help"],
                check=True,
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            return 0
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"Probe failed: {exc}", file=sys.stderr, flush=True)
            return 1
    print("Known Kokoro voices:")
    for voice in KOKORO_VOICES:
        print(f"  {voice}")
    return 0


def cmd_manifest(args: argparse.Namespace) -> int:
    if not args.book or not args.chapter:
        print("--book and --chapter are required for manifest generation", file=sys.stderr, flush=True)
        return 1

    verses = load_chapter(args.jsonl, args.book, args.chapter)
    if not verses:
        print(f"No verses found for {args.book} {args.chapter}", file=sys.stderr, flush=True)
        return 1

    pause_ms_map = build_pause_map(args)
    segments = build_segments(args.book, args.chapter, verses, pause_ms_map, verse_end_pause_ms=args.p_verse_end)
    chapter_dir_name = f"{slugify(args.book)}-{args.chapter}"
    path = write_segment_manifest(
        args.out_dir,
        chapter_dir_name,
        args.model,
        args.book,
        args.chapter,
        segments,
        pause_ms_map,
    )
    print(f"Wrote {path}")
    return 0


def build_pause_map(args: argparse.Namespace) -> Dict[str, int]:
    from collections import OrderedDict

    return OrderedDict(
        [
            (",", args.p_comma),
            ('"', args.p_quote),
            ("'", args.p_quote),
            (";", args.p_semicolon),
            ("-", args.p_dash),
            (":", args.p_colon),
            (".", args.p_terminal),
            ("?", args.p_terminal),
            ("!", args.p_terminal),
        ]
    )


def add_pause_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--p-comma", type=int, default=45)
    parser.add_argument("--p-quote", type=int, default=70)
    parser.add_argument("--p-semicolon", type=int, default=70)
    parser.add_argument("--p-dash", type=int, default=150)
    parser.add_argument("--p-colon", type=int, default=190)
    parser.add_argument("--p-terminal", type=int, default=320)
    parser.add_argument(
        "--p-verse-end",
        type=int,
        default=700,
        help="Pause at verse boundaries (default 700ms, overrides terminal punctuation).",
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default="", help="MLX Kokoro model ID")
    parser.add_argument(
        "--quantize",
        choices=("bf16", "8bit", "4bit"),
        help="Auto-select model ID by quantization tier (overrides --model unless --model is explicit).",
    )
    parser.add_argument(
        "--python-bin",
        default=sys.executable,
        help="Python interpreter that has mlx-audio installed.",
    )
    parser.add_argument(
        "--skip-missing-cli",
        action="store_true",
        help="Exit 0 with a message instead of erroring when mlx-audio is missing.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Directory for generated WAV files and checkpoints.",
    )
    parser.add_argument("--lang-code", default="a", help="Kokoro language code (a = en).")
    add_pause_args(parser)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MLX-accelerated BSB TTS CLI with checkpointing and progressive output."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Render a passage for one or more voices.")
    add_common_args(gen)
    gen.add_argument("--jsonl", default=DEFAULT_JSONL)
    gen.add_argument("--book", default="Psalm")
    gen.add_argument("--chapter", default="23")
    gen.add_argument("--max-verses", type=int, default=0)
    gen.add_argument("--voice", action="append", default=None)
    gen.add_argument("--text", default="", help="Free text to render instead of a chapter.")
    gen.add_argument(
        "--play-as-you-go",
        action="store_true",
        help="Pipe each new segment to afplay after it lands.",
    )
    gen.add_argument(
        "--fresh",
        action="store_true",
        help="Discard existing checkpoints and output WAVs before rendering.",
    )
    gen.add_argument("--skip-manifest", action="store_true")
    gen.set_defaults(func=cmd_generate)

    bat = sub.add_parser("batch", help="Render multiple chapters with one model load.")
    add_common_args(bat)
    bat.add_argument("--jsonl", default=DEFAULT_JSONL)
    bat.add_argument("--voice", action="append", default=None)
    bat.add_argument("--max-verses", type=int, default=0)
    bat.add_argument(
        "--range",
        default="",
        help="Chapter range, e.g. 'Psalm 1-5' or 'John 3-4, Romans 1-2'.",
    )
    bat.add_argument(
        "--books",
        default="",
        help="Comma-separated book names to render entirely, e.g. 'Psalm,Proverbs'.",
    )
    bat.add_argument(
        "--all",
        action="store_true",
        help="Render the entire Bible (all 66 books, 1189 chapters).",
    )
    bat.add_argument(
        "--sequence",
        action="store_true",
        help="Render the entire Bible in reading order: Gospels, Epistles, NT, Torah, Wisdom, Poetry, OT.",
    )
    bat.add_argument(
        "--fresh",
        action="store_true",
        help="Discard existing checkpoints and output WAVs before rendering.",
    )
    bat.add_argument("--skip-manifest", action="store_true")
    bat.set_defaults(func=cmd_batch)

    rep = sub.add_parser("replace", help="Re-render specific chapters with optional text substitutions.")
    add_common_args(rep)
    rep.add_argument("--jsonl", default=DEFAULT_JSONL)
    rep.add_argument("--voice", action="append", default=None)
    rep.add_argument(
        "--chapters",
        required=True,
        help="Comma-separated chapters to re-render, e.g. 'John 3,Psalm 23,Matthew 5'.",
    )
    rep.add_argument(
        "--replace",
        action="append",
        default=None,
        help="Text substitution as 'find:replace'. Repeat for multiple. e.g. --replace 'LORD:Lord' --replace 'Selah:'",
    )
    rep.add_argument("--skip-manifest", action="store_true")
    rep.set_defaults(func=cmd_replace)

    res = sub.add_parser("resume", help="Finish incomplete checkpoints.")
    add_common_args(res)
    res.set_defaults(func=cmd_resume)

    voi = sub.add_parser("voices", help="List known Kokoro voices.")
    voi.add_argument("--python-bin", default=sys.executable)
    voi.add_argument("--probe", action="store_true", help="Print mlx_audio generate --help output.")
    voi.set_defaults(func=cmd_voices)

    man = sub.add_parser("manifest", help="Write segment manifest for listen.html.")
    man.add_argument("--jsonl", default=DEFAULT_JSONL)
    man.add_argument("--book", default="Psalm")
    man.add_argument("--chapter", default="23")
    man.add_argument("--model", default=DEFAULT_MODEL)
    man.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    add_pause_args(man)
    man.set_defaults(func=cmd_manifest)

    parsed = parser.parse_args(argv)
    parsed.model_overridden = bool(getattr(parsed, "model", ""))
    if not hasattr(parsed, "model"):
        parsed.model = ""
    if hasattr(parsed, "voice") and not parsed.voice:
        parsed.voice = ["af_heart", "bm_george"]
    return parsed


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
