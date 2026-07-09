#!/usr/bin/env python3
"""Checkpointed full-Bible / New Testament render with Chatterbox (clone-calm).

Designed for long local runs on Apple Silicon:
  - Default backend is MLX (mlx-audio); PyTorch is --backend torch
  - Loads the model once and prepares the voice clone once
  - Chunks long chapters (Chatterbox max_new_tokens ~1000)
  - Resumes from per-chapter checkpoints
  - Writes final MP3s under output/audio/local/chatterbox/

Requires a local BSB JSONL path (--jsonl, default ~/Downloads/bsb.jsonl)
and ffmpeg on PATH for WAV concat + MP3 encode.

Usage:
  # MLX New Testament (preferred on Apple Silicon)
  audio/local/.venv-mlx/bin/python audio/local/generate_chatterbox.py \\
    --nt --backend mlx

  # One book, smoke-test first chapter only
  ... generate_chatterbox.py --book Philippians --max-chapters 1

  # PyTorch / MPS fallback
  PYTORCH_ENABLE_MPS_FALLBACK=1 audio/local/.venv-chatterbox/bin/python \\
    audio/local/generate_chatterbox.py --nt --backend torch --device mps

  # Dry-run inventory (no model load)
  ... generate_chatterbox.py --nt --dry-run

  # Resume (default): re-run the same command; completed chapters skip.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from audio.local.generate_demo import (  # noqa: E402
    DEFAULT_CHATTERBOX_AUDIO_PROMPT,
    DEFAULT_CHATTERBOX_CFG_WEIGHT,
    DEFAULT_CHATTERBOX_EXAGGERATION,
    PRONUNCIATION_REPLACEMENTS,
    _patch_torch_load_for_device,
    require_dependency,
)
from audio.paths import LOCAL_AUDIO_DIR  # noqa: E402

DEFAULT_JSONL = os.path.expanduser("~/Downloads/bsb.jsonl")
DEFAULT_OUT_DIR = LOCAL_AUDIO_DIR / "chatterbox"
DEFAULT_MLX_MODEL = "mlx-community/chatterbox-fp16"
DEFAULT_MLX_TURBO_MODEL = "mlx-community/chatterbox-turbo-fp16"

# Canonical NT order (matches BSB JSONL book names).
NT_BOOKS = (
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
)

# Chatterbox caps generation at max_new_tokens=1000. Stay under ~350 chars so
# speech tokens finish the full chunk rather than truncating mid-sentence.
DEFAULT_MAX_CHARS = 320


def slugify_book(value: str) -> str:
    return (
        value.lower()
        .replace(" ", "_")
        .replace(".", "")
        .replace(",", "")
        .replace("-", "_")
    )


def normalize_for_speech(text: str) -> str:
    for source, target in PRONUNCIATION_REPLACEMENTS:
        text = text.replace(source, target)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_bible(jsonl_path: str) -> Dict[str, Dict[int, List[dict]]]:
    bible: Dict[str, Dict[int, List[dict]]] = {}
    with open(jsonl_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            verse = json.loads(line)
            book = verse["book"]
            chapter = int(verse["chapter"])
            bible.setdefault(book, {}).setdefault(chapter, []).append(verse)
    for book in bible:
        for chapter in bible[book]:
            bible[book][chapter].sort(key=lambda v: int(v.get("verseNum", 0)))
    return bible


def load_checkpoint(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def split_long_text(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> List[str]:
    """Split at sentence boundaries, then word boundaries if needed."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    current = ""
    for sent in sentences:
        if not sent:
            continue
        if len(sent) > max_chars:
            if current:
                chunks.append(current.strip())
                current = ""
            words = sent.split()
            piece = ""
            for word in words:
                candidate = f"{piece} {word}".strip()
                if len(candidate) > max_chars and piece:
                    chunks.append(piece)
                    piece = word
                else:
                    piece = candidate
            if piece:
                current = piece
            continue
        candidate = f"{current} {sent}".strip() if current else sent
        if len(candidate) > max_chars and current:
            chunks.append(current.strip())
            current = sent
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks


def build_chapter_chunks(
    book_name: str,
    chapter_num: int,
    verses: Sequence[dict],
    max_chars: int,
) -> List[Tuple[str, str]]:
    """Return ordered (chunk_key, text) pairs for a chapter."""
    parts: List[Tuple[str, str]] = []
    header = normalize_for_speech(f"{book_name}. Chapter {chapter_num}.")
    parts.append(("header", header))

    body = normalize_for_speech(" ".join(str(v["text"]).strip() for v in verses))
    for index, chunk in enumerate(split_long_text(body, max_chars=max_chars)):
        parts.append((f"chunk_{index:03d}", chunk))
    return parts


def concat_wavs(parts: Sequence[Path], output_wav: Path, silence_ms: int = 400) -> None:
    """Concatenate WAV parts with a short silence between chunks via ffmpeg."""
    list_file = output_wav.with_suffix(".concat.txt")
    silence = output_wav.with_name(output_wav.stem + ".silence.wav")
    # Infer sample rate from first part (Chatterbox is typically 24k).
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(parts[0]),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    sr = probe.stdout.strip() or "24000"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=r={sr}:cl=mono",
            "-t",
            f"{silence_ms / 1000:.3f}",
            str(silence),
        ],
        capture_output=True,
        check=True,
    )

    with list_file.open("w", encoding="utf-8") as handle:
        for index, part in enumerate(parts):
            handle.write(f"file '{part.resolve()}'\n")
            if index < len(parts) - 1:
                handle.write(f"file '{silence.resolve()}'\n")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_wav),
        ],
        capture_output=True,
        check=True,
    )
    list_file.unlink(missing_ok=True)
    silence.unlink(missing_ok=True)


def wav_to_mp3(wav_path: Path, mp3_path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-qscale:a",
            "4",
            str(mp3_path),
        ],
        capture_output=True,
        check=True,
    )


class ChatterboxEngine:
    """Thin adapter over MLX (preferred) or PyTorch Chatterbox backends."""

    def __init__(
        self,
        backend: str,
        model: object,
        sample_rate: int,
        audio_prompt_path: str,
        exaggeration: float,
        cfg_weight: float,
        conds: object = None,
        torchaudio: object = None,
    ):
        self.backend = backend
        self.model = model
        self.sample_rate = sample_rate
        self.audio_prompt_path = audio_prompt_path
        self.exaggeration = exaggeration
        self.cfg_weight = cfg_weight
        self.conds = conds
        self.torchaudio = torchaudio

    def generate_to_wav(self, text: str, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if self.backend == "mlx":
            import numpy as np
            import soundfile as sf

            kwargs = {
                "exaggeration": self.exaggeration,
                "cfg_weight": self.cfg_weight,
                "verbose": False,
            }
            if self.conds is not None:
                kwargs["conds"] = self.conds
            elif self.audio_prompt_path:
                kwargs["ref_audio"] = self.audio_prompt_path

            results = list(self.model.generate(text, **kwargs))
            if not results:
                raise RuntimeError("MLX Chatterbox returned no audio")
            audio = results[0].audio
            # mx.array -> numpy
            if hasattr(audio, "tolist"):
                try:
                    import mlx.core as mx

                    mx.eval(audio)
                except Exception:
                    pass
            samples = np.array(audio, dtype=np.float32)
            if samples.ndim > 1:
                samples = samples.reshape(-1)
            sf.write(str(output_path), samples, self.sample_rate)
            return

        # PyTorch path
        wav = self.model.generate(
            text,
            exaggeration=self.exaggeration,
            cfg_weight=self.cfg_weight,
        )
        if getattr(wav, "dim", lambda: 1)() == 1:
            wav = wav.unsqueeze(0)
        self.torchaudio.save(str(output_path), wav.cpu(), self.sample_rate)


def load_engine(
    backend: str,
    device: str,
    model_id: str,
    audio_prompt_path: str,
    exaggeration: float,
    cfg_weight: float,
) -> ChatterboxEngine:
    started = time.time()
    if backend == "mlx":
        from mlx_audio.tts.utils import load_model

        print(f"Loading MLX Chatterbox: {model_id}")
        model = load_model(model_id)
        sample_rate = int(getattr(model, "sample_rate", 24000))
        conds = None
        if audio_prompt_path:
            print(f"Preparing voice clone from {audio_prompt_path}...")
            # prepare_conditionals accepts a path string
            conds = model.prepare_conditionals(
                audio_prompt_path, sample_rate, exaggeration
            )
        print(f"MLX model ready in {time.time() - started:.1f}s")
        return ChatterboxEngine(
            backend="mlx",
            model=model,
            sample_rate=sample_rate,
            audio_prompt_path=audio_prompt_path,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            conds=conds,
        )

    # PyTorch / MPS fallback (slower on Apple Silicon)
    try:
        import pkg_resources  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "Missing pkg_resources. Install: uv pip install 'setuptools<81'"
        ) from exc

    torchaudio = require_dependency("torchaudio", "pip install chatterbox-tts")
    _patch_torch_load_for_device(device)
    from chatterbox.tts import ChatterboxTTS

    print(f"Loading PyTorch Chatterbox on {device}...")
    model = ChatterboxTTS.from_pretrained(device=device)
    if audio_prompt_path:
        print(f"Preparing voice clone from {audio_prompt_path}...")
        model.prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)
    print(f"PyTorch model ready in {time.time() - started:.1f}s")
    return ChatterboxEngine(
        backend="torch",
        model=model,
        sample_rate=int(model.sr),
        audio_prompt_path=audio_prompt_path,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        torchaudio=torchaudio,
    )


def generate_chapter(
    engine: Optional[ChatterboxEngine],
    book_name: str,
    chapter_num: int,
    verses: Sequence[dict],
    out_dir: Path,
    max_chars: int,
    dry_run: bool,
) -> bool:
    book_slug = slugify_book(book_name)
    chapter_slug = f"chapter_{chapter_num:02d}"
    book_dir = out_dir / book_slug
    book_dir.mkdir(parents=True, exist_ok=True)

    mp3_path = book_dir / f"{book_slug}_{chapter_slug}.mp3"
    wav_path = book_dir / f"{book_slug}_{chapter_slug}.wav"
    checkpoint_path = book_dir / f".checkpoint_{chapter_slug}.json"
    parts_dir = book_dir / f".parts_{chapter_slug}"
    parts_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = load_checkpoint(checkpoint_path)
    if checkpoint.get("complete") and mp3_path.exists():
        print(f"  {book_name} {chapter_num} - already done")
        return True

    chunks = build_chapter_chunks(book_name, chapter_num, verses, max_chars)
    total_chars = sum(len(text) for _, text in chunks)
    title = f"{book_name} {chapter_num}"

    if dry_run:
        print(
            f"  {title} - DRY RUN ({len(verses)} verses, "
            f"{len(chunks)} chunks, {total_chars} chars)"
        )
        return True

    print(
        f"  {title} - generating ({len(verses)} verses, "
        f"{len(chunks)} chunks, {total_chars} chars)..."
    )
    chapter_started = time.time()
    part_files: List[Path] = []

    for chunk_key, text in chunks:
        part_path = parts_dir / f"{chunk_key}.wav"
        part_files.append(part_path)
        if checkpoint.get(chunk_key) and part_path.exists():
            continue
        chunk_started = time.time()
        try:
            assert engine is not None
            engine.generate_to_wav(text, part_path)
        except Exception as exc:  # noqa: BLE001
            print(f"    {chunk_key}: FAILED ({exc})")
            checkpoint["error"] = str(exc)
            checkpoint["failed_chunk"] = chunk_key
            save_checkpoint(checkpoint_path, checkpoint)
            return False
        elapsed = time.time() - chunk_started
        print(f"    {chunk_key}: ok ({len(text)} chars, {elapsed:.1f}s)")
        checkpoint[chunk_key] = True
        checkpoint["backend"] = engine.backend if engine else None
        checkpoint.pop("error", None)
        checkpoint.pop("failed_chunk", None)
        save_checkpoint(checkpoint_path, checkpoint)

    # Assemble WAV then MP3
    missing = [p for p in part_files if not p.exists()]
    if missing:
        print(f"    missing parts: {missing}")
        return False

    concat_wavs(part_files, wav_path, silence_ms=350)
    wav_to_mp3(wav_path, mp3_path)
    wav_path.unlink(missing_ok=True)

    # Clean part files after successful assembly
    for part in part_files:
        part.unlink(missing_ok=True)
    try:
        parts_dir.rmdir()
    except OSError:
        pass

    checkpoint["complete"] = True
    checkpoint["mp3"] = str(mp3_path)
    checkpoint["chunks"] = len(chunks)
    checkpoint["chars"] = total_chars
    checkpoint["seconds"] = round(time.time() - chapter_started, 1)
    save_checkpoint(checkpoint_path, checkpoint)

    size_mb = mp3_path.stat().st_size / (1024 * 1024)
    print(
        f"    done: {mp3_path.name} ({size_mb:.1f} MB, "
        f"{checkpoint['seconds']:.0f}s wall)"
    )
    return True


def generate_book(
    engine: Optional[ChatterboxEngine],
    book_name: str,
    chapters: Dict[int, List[dict]],
    out_dir: Path,
    max_chars: int,
    dry_run: bool,
    max_chapters: int = 0,
) -> bool:
    chapter_nums = sorted(chapters.keys())
    if max_chapters > 0:
        chapter_nums = chapter_nums[:max_chapters]
    total_verses = sum(len(chapters[c]) for c in chapter_nums)
    total_chars = sum(
        len(str(v["text"])) for c in chapter_nums for v in chapters[c]
    )
    print(
        f"\n{book_name}: {len(chapter_nums)} chapters, "
        f"{total_verses} verses, {total_chars:,} chars"
    )
    for ch_num in chapter_nums:
        ok = generate_chapter(
            engine,
            book_name,
            ch_num,
            chapters[ch_num],
            out_dir,
            max_chars,
            dry_run,
        )
        if not ok:
            print(f"  FAILED at {book_name} chapter {ch_num}")
            return False
    return True


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate BSB audio locally with Chatterbox (clone-calm defaults)."
    )
    parser.add_argument(
        "--jsonl",
        default=DEFAULT_JSONL,
        help=f"Path to BSB JSONL (default: {DEFAULT_JSONL})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output root (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument("--book", help="Single book name, e.g. Philippians")
    parser.add_argument(
        "--nt",
        action="store_true",
        help="Generate the full New Testament (27 books).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate the entire Bible (OT + NT).",
    )
    parser.add_argument(
        "--backend",
        choices=("mlx", "torch"),
        default="mlx",
        help="Inference backend. mlx (default) is much faster on Apple Silicon.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MLX_MODEL,
        help=(
            f"MLX model id (default: {DEFAULT_MLX_MODEL}). "
            f"Faster: {DEFAULT_MLX_TURBO_MODEL}"
        ),
    )
    parser.add_argument(
        "--device",
        default="mps",
        help="Torch device when --backend torch (mps/cpu/cuda). Ignored for mlx.",
    )
    parser.add_argument(
        "--audio-prompt-path",
        default=str(DEFAULT_CHATTERBOX_AUDIO_PROMPT),
        help="Voice clone reference WAV (default: Bill clone-calm ref).",
    )
    parser.add_argument(
        "--exaggeration",
        type=float,
        default=DEFAULT_CHATTERBOX_EXAGGERATION,
        help=f"Default {DEFAULT_CHATTERBOX_EXAGGERATION:g} (clone-calm).",
    )
    parser.add_argument(
        "--cfg-weight",
        type=float,
        default=DEFAULT_CHATTERBOX_CFG_WEIGHT,
        help=f"Default {DEFAULT_CHATTERBOX_CFG_WEIGHT:g} (clone-calm).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=DEFAULT_MAX_CHARS,
        help="Max characters per Chatterbox generate() call.",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=0,
        help="Limit chapters per book (0 = all). Useful for smoke tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inventory chapters/chunks without loading the model.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not args.book and not args.nt and not args.all:
        print("Specify --book, --nt, or --all", file=sys.stderr)
        return 2

    jsonl = Path(args.jsonl)
    if not jsonl.exists():
        print(f"JSONL not found: {jsonl}", file=sys.stderr)
        return 1

    print(f"Loading Bible from {jsonl}...")
    bible = load_bible(str(jsonl))
    print(f"Loaded {len(bible)} books")

    if args.book:
        books = [args.book]
        if args.book not in bible:
            # Case-insensitive match
            match = next(
                (b for b in bible if b.casefold() == args.book.casefold()),
                None,
            )
            if not match:
                print(
                    f"Book '{args.book}' not found. Available: "
                    + ", ".join(sorted(bible)),
                    file=sys.stderr,
                )
                return 1
            books = [match]
    elif args.nt:
        books = [b for b in NT_BOOKS if b in bible]
        missing = [b for b in NT_BOOKS if b not in bible]
        if missing:
            print(f"Warning: missing books in JSONL: {missing}", file=sys.stderr)
    else:
        # Full Bible in NT list order after OT books as they appear
        ot = [b for b in bible if b not in NT_BOOKS]
        # Preserve OT appearance order from JSONL scan order
        books = ot + [b for b in NT_BOOKS if b in bible]

    prompt = args.audio_prompt_path
    if prompt and not Path(prompt).exists() and not args.dry_run:
        print(f"Missing audio prompt: {prompt}", file=sys.stderr)
        print(
            "Create it with:\n"
            "  ffmpeg -y -ss 5 -t 8 \\\n"
            "    -i output/elevenlabs_audio/philippians/philippians_chapter_01.mp3 \\\n"
            "    -ac 1 -ar 24000 output/audio/local/voice-match/ref-bill-phil1.wav",
            file=sys.stderr,
        )
        return 1

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Output: {args.out_dir}")
    print(f"Backend: {args.backend}" + (f" ({args.model})" if args.backend == "mlx" else f" device={args.device}"))
    print(
        f"Voice: clone-calm (exaggeration={args.exaggeration}, "
        f"cfg_weight={args.cfg_weight})"
    )
    print(f"Prompt: {prompt or '(model default)'}")
    print(f"Chunk max chars: {args.max_chars}")

    engine: Optional[ChatterboxEngine] = None
    if not args.dry_run:
        engine = load_engine(
            args.backend,
            args.device,
            args.model,
            prompt,
            args.exaggeration,
            args.cfg_weight,
        )

    run_started = time.time()
    for book_name in books:
        ok = generate_book(
            engine,
            book_name,
            bible[book_name],
            args.out_dir,
            args.max_chars,
            args.dry_run,
            args.max_chapters,
        )
        if not ok:
            print(f"\nStopped at {book_name}")
            return 1

    elapsed = time.time() - run_started
    print(f"\nDone in {elapsed / 3600:.2f}h ({elapsed:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
