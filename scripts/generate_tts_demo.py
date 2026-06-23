#!/usr/bin/env python3
"""Generate one-chapter BSB TTS demo inputs and optional local audio renders."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence
from urllib.request import urlopen


DEFAULT_JSONL = "https://arweave.net/B6yeNb3lk_VkiIp-fTWVh13TlM94LjLK6kC63BPXa8s"
DEFAULT_BOOK = "Psalm"
DEFAULT_CHAPTER = "23"
DEFAULT_OUT_DIR = Path("examples/tts/output")

PRONUNCIATION_REPLACEMENTS = (
    ("LORD", "Lord"),
    ("\u2014", ", "),
    ("\u201c", '"'),
    ("\u201d", '"'),
    ("\u2018", "'"),
    ("\u2019", "'"),
)

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
    wanted_book = book.casefold()
    wanted_chapter = str(chapter)
    verses = [
        row
        for row in read_jsonl(source)
        if str(row.get("book", "")).casefold() == wanted_book
        and str(row.get("chapter", "")) == wanted_chapter
    ]
    verses.sort(key=lambda row: int(str(row.get("verseNum", "0"))))
    return verses


def normalize_for_speech(text: str, semicolon_pauses: bool = False) -> str:
    for source, target in PRONUNCIATION_REPLACEMENTS:
        text = text.replace(source, target)
    if semicolon_pauses:
        text = re.sub(r";\s*", ";\n", text)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_progressive_punctuation(text: str) -> List[Dict[str, object]]:
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


def build_progressive_speech_segments(
    book: str,
    chapter: str,
    verses: Sequence[Dict[str, object]],
) -> List[Dict[str, object]]:
    lines = [{"ref": "Title", "text": f"{book} {chapter}."}]
    lines.extend({"ref": str(verse["ref"]), "text": str(verse["text"])} for verse in verses)

    segments = []
    for line in lines:
        text = normalize_for_speech(line["text"])
        for chunk_index, chunk in enumerate(split_progressive_punctuation(text)):
            ref = line["ref"]
            timing_ref = ref
            if len(split_progressive_punctuation(text)) > 1 and ref != "Title":
                timing_ref = f"{ref}.{chunk_index + 1}"
            segments.append(
                {
                    "displayRef": ref,
                    "ref": timing_ref,
                    "text": chunk["text"],
                    "pause_ms": chunk["pause_ms"],
                }
            )
    if segments:
        segments[-1]["pause_ms"] = 0
    return segments


def build_speech_text(
    book: str,
    chapter: str,
    verses: Sequence[Dict[str, object]],
    verse_pauses: bool = False,
    semicolon_pauses: bool = False,
) -> str:
    if verse_pauses:
        lines = [f"{book} {chapter}."]
        lines.extend(str(verse["text"]).strip() for verse in verses)
        return "\n".join(
            normalize_for_speech(line, semicolon_pauses) for line in lines
        )

    verse_text = " ".join(str(verse["text"]).strip() for verse in verses)
    return normalize_for_speech(
        f"{book} {chapter}. {verse_text}", semicolon_pauses
    )


def write_demo_files(
    out_dir: Path,
    source: str,
    book: str,
    chapter: str,
    verses: Sequence[Dict[str, object]],
    speech_text: str,
    speech_segments: Optional[Sequence[Dict[str, object]]] = None,
) -> Dict[str, Path]:
    chapter_slug = f"{slugify(book)}-{chapter}"
    chapter_dir = out_dir / chapter_slug
    chapter_dir.mkdir(parents=True, exist_ok=True)

    chapter_text_path = chapter_dir / f"{chapter_slug}.txt"
    manifest_path = chapter_dir / "manifest.json"

    original_lines = [f"{book} {chapter}"]
    original_lines.extend(
        f"{verse['verseNum']}. {str(verse['text']).strip()}" for verse in verses
    )
    chapter_text_path.write_text("\n".join(original_lines) + "\n", encoding="utf-8")

    manifest = {
        "source": source,
        "book": book,
        "chapter": str(chapter),
        "verse_count": len(verses),
        "refs": [verse["ref"] for verse in verses],
        "speech_text": speech_text,
        "speech_segments": list(speech_segments or []),
        "verses": verses,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return {"chapter_dir": chapter_dir, "text": chapter_text_path, "manifest": manifest_path}


def require_dependency(import_name: str, install_hint: str) -> object:
    try:
        return __import__(import_name)
    except ImportError as exc:
        raise RuntimeError(f"Missing {import_name}. Install it with: {install_hint}") from exc


def render_with_kokoro(
    text: str, output_path: Path, voice: str, speed: float, pause_ms: int
) -> None:
    kokoro = require_dependency("kokoro", "python3 -m pip install kokoro soundfile")
    numpy = require_dependency("numpy", "python3 -m pip install numpy")
    soundfile = require_dependency("soundfile", "python3 -m pip install soundfile")

    pipeline = kokoro.KPipeline(lang_code="a")
    generator = pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+")
    chunks = []
    for _, _, audio in generator:
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        chunks.append(audio)

    with soundfile.SoundFile(
        str(output_path), mode="w", samplerate=24000, channels=1
    ) as output:
        silence = numpy.zeros(int(24000 * pause_ms / 1000), dtype="float32")
        for index, audio in enumerate(chunks):
            output.write(audio)
            if pause_ms > 0 and index < len(chunks) - 1:
                output.write(silence)


def render_with_kokoro_segments(
    segments: Sequence[Dict[str, object]], output_path: Path, voice: str, speed: float
) -> None:
    kokoro = require_dependency("kokoro", "python3 -m pip install kokoro soundfile")
    numpy = require_dependency("numpy", "python3 -m pip install numpy")
    soundfile = require_dependency("soundfile", "python3 -m pip install soundfile")

    text = "\n".join(str(segment["text"]) for segment in segments)
    pipeline = kokoro.KPipeline(lang_code="a")
    generator = pipeline(text, voice=voice, speed=speed, split_pattern=r"\n+")
    chunks = []
    for _, _, audio in generator:
        if hasattr(audio, "detach"):
            audio = audio.detach().cpu().numpy()
        chunks.append(audio)

    if len(chunks) != len(segments):
        raise RuntimeError(f"Kokoro returned {len(chunks)} chunks for {len(segments)} segments")

    with soundfile.SoundFile(
        str(output_path), mode="w", samplerate=24000, channels=1
    ) as output:
        for index, audio in enumerate(chunks):
            output.write(audio)
            pause_ms = int(segments[index].get("pause_ms", 0))
            if pause_ms > 0 and index < len(chunks) - 1:
                output.write(numpy.zeros(int(24000 * pause_ms / 1000), dtype="float32"))


def render_with_chatterbox(
    text: str,
    output_path: Path,
    device: str,
    audio_prompt_path: str,
) -> None:
    require_dependency("torch", "python3 -m pip install chatterbox-tts")
    torchaudio = require_dependency("torchaudio", "python3 -m pip install chatterbox-tts")
    from chatterbox.tts import ChatterboxTTS

    model = ChatterboxTTS.from_pretrained(device=device)
    kwargs = {}
    if audio_prompt_path:
        kwargs["audio_prompt_path"] = audio_prompt_path
    wav = model.generate(text, **kwargs)
    if getattr(wav, "dim", lambda: 1)() == 1:
        wav = wav.unsqueeze(0)
    torchaudio.save(str(output_path), wav.cpu(), model.sr)


def render_with_dia(text: str, output_path: Path, device: str) -> None:
    from dia.model import Dia

    compute_dtype = "float16" if device != "cpu" else "float32"
    model = Dia.from_pretrained("nari-labs/Dia-1.6B-0626", compute_dtype=compute_dtype)
    dia_text = f"[S1] {text} [S1]"
    output = model.generate(
        dia_text,
        use_torch_compile=False,
        verbose=True,
        cfg_scale=3.0,
        temperature=1.8,
        top_p=0.90,
        cfg_filter_top_k=50,
    )
    model.save_audio(str(output_path), output)


def render_with_macos_say(text: str, output_path: Path, voice: str) -> None:
    subprocess.run(["say", "-v", voice, "-o", str(output_path), text], check=True)


def tag_suffix(output_tag: str) -> str:
    return f"-{slugify(output_tag)}" if output_tag else ""


def render_engines(
    args: argparse.Namespace,
    chapter_dir: Path,
    speech_text: str,
    speech_segments: Optional[Sequence[Dict[str, object]]] = None,
) -> None:
    engine_names = args.engine or ["text"]
    suffix = tag_suffix(args.output_tag)
    for engine in engine_names:
        if engine == "text":
            continue

        if engine == "kokoro":
            output_path = chapter_dir / f"kokoro-{slugify(args.kokoro_voice)}{suffix}.wav"
            if speech_segments:
                render_with_kokoro_segments(
                    speech_segments, output_path, args.kokoro_voice, args.speed
                )
            else:
                render_with_kokoro(
                    speech_text,
                    output_path,
                    args.kokoro_voice,
                    args.speed,
                    args.pause_ms,
                )
        elif engine == "chatterbox":
            output_path = chapter_dir / f"chatterbox{suffix}.wav"
            render_with_chatterbox(
                speech_text, output_path, args.device, args.audio_prompt_path
            )
        elif engine == "dia":
            output_path = chapter_dir / f"dia{suffix}.mp3"
            render_with_dia(speech_text, output_path, args.device)
        elif engine == "say":
            output_path = chapter_dir / f"macos-say-{slugify(args.say_voice)}{suffix}.aiff"
            render_with_macos_say(speech_text, output_path, args.say_voice)
        else:
            raise ValueError(f"Unsupported engine: {engine}")

        print(f"Rendered {engine}: {output_path}")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build one-chapter BSB TTS demo files and optional local audio."
    )
    parser.add_argument("--jsonl", default=DEFAULT_JSONL, help="BSB JSONL URL or file path")
    parser.add_argument("--book", default=DEFAULT_BOOK, help="Book name in the JSONL")
    parser.add_argument("--chapter", default=DEFAULT_CHAPTER, help="Chapter number")
    parser.add_argument(
        "--max-verses",
        type=int,
        default=0,
        help="Limit rendering to the first N verses of the selected chapter.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument(
        "--engine",
        action="append",
        choices=("text", "kokoro", "chatterbox", "dia", "say"),
        help="Render engine. Repeat for multiple engines. Default writes text only.",
    )
    parser.add_argument("--device", default="cpu", help="Torch device for local models")
    parser.add_argument("--speed", type=float, default=0.92, help="Kokoro speech speed")
    parser.add_argument(
        "--verse-pauses",
        action="store_true",
        help="Put each verse on its own TTS segment for more natural pauses.",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=0,
        help="Silence to insert between Kokoro segments when text has line breaks.",
    )
    parser.add_argument(
        "--semicolon-pauses",
        action="store_true",
        help="Split semicolon clauses into separate TTS segments.",
    )
    parser.add_argument(
        "--punctuation-pauses",
        action="store_true",
        help="Split punctuation into progressive pause groups.",
    )
    parser.add_argument(
        "--output-tag",
        default="",
        help="Suffix generated audio filenames, e.g. slow-paused.",
    )
    parser.add_argument("--kokoro-voice", default="am_adam")
    parser.add_argument("--say-voice", default="Daniel")
    parser.add_argument(
        "--audio-prompt-path",
        default="",
        help="Optional local reference voice clip for Chatterbox.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    verses = load_chapter(args.jsonl, args.book, args.chapter)
    if args.max_verses > 0:
        verses = verses[: args.max_verses]
    if not verses:
        print(f"No verses found for {args.book} {args.chapter}", file=sys.stderr)
        return 1

    speech_segments = None
    if args.punctuation_pauses:
        speech_segments = build_progressive_speech_segments(args.book, args.chapter, verses)
        speech_text = "\n".join(str(segment["text"]) for segment in speech_segments)
    else:
        speech_text = build_speech_text(
            args.book,
            args.chapter,
            verses,
            args.verse_pauses,
            args.semicolon_pauses,
        )
    paths = write_demo_files(
        args.out_dir,
        args.jsonl,
        args.book,
        args.chapter,
        verses,
        speech_text,
        speech_segments,
    )
    print(f"Wrote text: {paths['text']}")
    print(f"Wrote manifest: {paths['manifest']}")
    render_engines(args, paths["chapter_dir"], speech_text, speech_segments)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
