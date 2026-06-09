#!/usr/bin/env python3
"""
Generate professional Typst source from BSB USFM, then compile it when Typst is installed.

The script keeps USFM as the structural source of truth: headings, reference ranges,
paragraphs, poetry, footnotes, and verse numbers are converted into Typst markup.
"""

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

from .add_route_links import build_url
from .customize_epub import OSIS_BOOKS
from .download_bsb import BOOK_NAMES
from .generate_reflow_pdf import USFM_TO_BOOK, usfm_ref_to_route


BOOK_ORDER = {name: num for num, name in BOOK_NAMES.items()}
NEW_TESTAMENT_START = BOOK_ORDER["Matthew"]


def usfm_code_from_name(name):
    stem = PurePosixPath(name).stem.upper()
    match = re.search(r"([1-3]?[A-Z]{2,3})(?:ENGBSB)?$", stem)
    return match.group(1) if match else stem


def typst_escape(text):
    text = text.replace("\\", "\\\\")
    text = text.replace("[", "\\[").replace("]", "\\]")
    for char in ("#", "$", "%"):
        text = text.replace(char, f"\\{char}")
    return text


def typst_string(text):
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def clean_spaces(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+([,.;:!?)])", r"\1", text)
    return text


def plain_ref_text(text):
    return re.sub(r"\\ref\s+([^\\]+?)\\ref\*", r"\1", text)


def escaped_chunk(text):
    if not text:
        return ""
    leading = " " if text[0].isspace() else ""
    trailing = " " if text[-1].isspace() else ""
    value = clean_spaces(plain_ref_text(text))
    if not value:
        return leading or trailing
    return leading + typst_escape(value) + trailing


def parse_ref_runs(text):
    runs = []
    pos = 0
    pattern = re.compile(r"\\ref\s+([^|\\]+)\|([^\\]+)\\ref\*")
    for match in pattern.finditer(text):
        if match.start() > pos:
            runs.append(escaped_chunk(text[pos:match.start()]))
        display, target = match.groups()
        url = usfm_ref_to_route(target)
        display = typst_escape(clean_spaces(display))
        next_char = text[match.end() : match.end() + 1]
        suffix = ""
        end = match.end()
        if url and next_char == ";":
            suffix = "#[;]"
            end += 1
        elif url and next_char == "(":
            suffix = " "
        runs.append(f"#link({typst_string(url)})[{display}]{suffix}" if url else display)
        pos = end
    if pos < len(text):
        runs.append(escaped_chunk(text[pos:]))
    return "".join(runs)


def strip_text_markers(text):
    text = re.sub(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*", r"\1", text)
    text = re.sub(r"\\(?!ref\b|f\b|f\*)[a-z0-9]+\*?\s*", "", text)
    text = text.replace("\\+", "")
    return text


def footnote_content(raw):
    raw = raw.strip()
    raw = re.sub(r"^\+\s*", "", raw)
    raw = re.sub(r"\\fr\s+", "", raw)
    raw = re.sub(r"\\ft\s+", " ", raw)
    raw = re.sub(r"\\fqa\s+", " ", raw)
    raw = re.sub(r"\\fq\s+", " ", raw)
    raw = re.sub(r"\\fk\s+", " ", raw)
    raw = re.sub(r"\\(?!ref\b)[a-z0-9]+\*?", " ", raw)
    return parse_ref_runs(clean_spaces(raw))


def inline_content(raw):
    out = []
    pos = 0
    note_pattern = re.compile(r"\\f\s+(.*?)\\f\*", re.S)
    for match in note_pattern.finditer(raw):
        if match.start() > pos:
            out.append(parse_ref_runs(strip_text_markers(raw[pos:match.start()])))
        suffix = " " if raw[match.end() : match.end() + 1] == "(" else ""
        out.append(f"#footnote[{footnote_content(match.group(1))}]{suffix}")
        pos = match.end()
    if pos < len(raw):
        out.append(parse_ref_runs(strip_text_markers(raw[pos:])))
    text = "".join(out)
    return text


def verse_segments(raw, osis, chapter):
    parts = re.split(r"\\v\s+(\d+)\s*", raw)
    segments = []
    prefix = inline_content(parts[0]) if parts and parts[0].strip() else ""
    if prefix:
        segments.append((None, None, prefix))
    for idx in range(1, len(parts), 2):
        verse = int(parts[idx])
        body = inline_content(parts[idx + 1] if idx + 1 < len(parts) else "")
        segments.append((verse, build_url(osis, chapter, verse, verse), body))
    return segments


def paragraph_markup(para, osis, chapter):
    marker = para["marker"]
    raw = para["raw"]
    segments = verse_segments(raw, osis, chapter)
    pieces = []
    first_segment = True
    for verse, url, body in segments:
        if verse is None:
            if body:
                pieces.append(body)
            continue
        if first_segment and verse == 1:
            pieces.append(f"#drop({typst_string(url)}, {typst_string(str(chapter))})[{body}]")
        else:
            pieces.append(f"#verse({typst_string(url)}, {typst_string(str(verse))})[{body}]")
        first_segment = False

    content = " ".join(piece for piece in pieces if piece).strip()
    if not content:
        return ""
    if marker.startswith("q"):
        level = int(marker[1:] or "1") if marker[1:].isdigit() else 1
        return f"#poetry({level})[{content}]"
    if marker in {"li1", "li2"}:
        level = 1 if marker == "li1" else 2
        return f"#poetry({level})[{content}]"
    return f"#para[{content}]"


def parse_usfm_zip(usfm_zip):
    books = []
    with zipfile.ZipFile(usfm_zip) as zf:
        names = [name for name in zf.namelist() if name.lower().endswith(".usfm")]
        names.sort(key=lambda name: BOOK_ORDER.get(USFM_TO_BOOK.get(usfm_code_from_name(name), ""), 999))
        for name in names:
            code = usfm_code_from_name(name)
            book = USFM_TO_BOOK.get(code)
            if not book:
                continue
            osis = OSIS_BOOKS[book]
            chapters = []
            current = None
            pending = None

            def flush():
                nonlocal pending
                if pending and current is not None:
                    pending["raw"] = clean_spaces(" ".join(pending["raw"]))
                    if pending["raw"] or pending["kind"] == "blank":
                        current["paras"].append(pending)
                pending = None

            for raw_line in zf.read(name).decode("utf-8-sig", errors="replace").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                match = re.match(r"^\\([a-z0-9]+)\s*(.*)$", line)
                if not match:
                    if pending:
                        pending["raw"].append(line)
                    continue
                marker, rest = match.groups()
                if marker == "c":
                    flush()
                    current = {"chapter": int(rest), "paras": []}
                    chapters.append(current)
                elif current is None:
                    continue
                elif marker in {"s1", "s2", "s3"}:
                    flush()
                    pending = {"kind": "heading", "marker": marker, "raw": [rest], "refs": ""}
                elif marker == "r":
                    flush()
                    if current["paras"] and current["paras"][-1]["kind"] == "heading":
                        current["paras"][-1]["refs"] = rest
                elif marker in {"p", "m", "pmo", "pm", "pi", "q1", "q2", "q3", "qc", "li1", "li2"}:
                    flush()
                    pending = {"kind": "body", "marker": marker, "raw": [rest], "refs": ""}
                elif marker == "v":
                    if pending is None or pending["kind"] != "body":
                        flush()
                        pending = {"kind": "body", "marker": "p", "raw": [], "refs": ""}
                    pending["raw"].append(f"\\v {rest}")
                elif marker == "b":
                    flush()
                    current["paras"].append({"kind": "blank", "marker": marker, "raw": "", "refs": ""})
                elif pending:
                    pending["raw"].append(rest)
            flush()
            books.append({"book": book, "osis": osis, "chapters": chapters})
    return books


def heading_ranges(chapter, osis):
    heading_indices = [idx for idx, para in enumerate(chapter["paras"]) if para["kind"] == "heading"]
    for pos, idx in enumerate(heading_indices):
        next_idx = heading_indices[pos + 1] if pos + 1 < len(heading_indices) else len(chapter["paras"])
        verses = []
        for para in chapter["paras"][idx + 1 : next_idx]:
            if para["kind"] == "body":
                verses.extend(int(v) for v in re.findall(r"\\v\s+(\d+)", para["raw"]))
        if not verses:
            start = end = 1
        else:
            start, end = verses[0], verses[-1]
        para = chapter["paras"][idx]
        para["url"] = build_url(osis, chapter["chapter"], start, end)


def typst_preamble():
    return r'''#set page(width: 7in, height: 10.5in, margin: (x: 0.5in, y: 0.55in), columns: 2)
#set text(font: "Lexend", size: 9.1pt, fill: black, lang: "en", hyphenate: false)
#set par(leading: 0.78em, justify: false)
#show link: it => {
  set text(fill: black)
  it
}

#let book-title(name) = {
  align(center)[#text(size: 32pt, weight: 800)[#name]]
  v(2.1em)
}

#let para(body) = block(below: 0.38em)[#body]
#let poetry(level, body) = block(inset: (left: 0.18in * level), below: 0.44em)[#body]
#let vnum(n) = text(weight: 800)[#n]
#let verse(url, n, body) = link(url)[#vnum(n)#h(0.28em)#body]
#let drop(url, n, body) = block(below: 0.35em)[
  #grid(columns: (2.0em, 1fr), column-gutter: 0.45em, align: top)[
    #link(url)[#text(size: 30pt, weight: 800)[#n]]
  ][
    #link(url)[#body]
  ]
]
#let section(title, url, refs: none) = block(above: 1.04em, below: 0.42em)[
  #link(url)[#text(weight: 800)[#title]]
  #if refs != none [ #text(size: 8pt, weight: 600)[#refs]]
]
'''


def filter_books(books, testament):
    if testament == "all":
        return books
    if testament == "nt":
        return [book for book in books if BOOK_ORDER[book["book"]] >= NEW_TESTAMENT_START]
    if testament == "ot":
        return [book for book in books if BOOK_ORDER[book["book"]] < NEW_TESTAMENT_START]
    raise ValueError(f"Unknown testament: {testament}")


def generate_typst(usfm_zip, output_typ, testament="all"):
    books = parse_usfm_zip(usfm_zip)
    books = filter_books(books, testament)
    lines = [typst_preamble()]
    for book_index, book in enumerate(books):
        if book_index:
            lines.append("#pagebreak()")
        lines.append(f"#book-title({typst_string(book['book'])})")
        for chapter in book["chapters"]:
            heading_ranges(chapter, book["osis"])
            if chapter["chapter"] != 1:
                lines.append("#v(0.8em)")
            for para in chapter["paras"]:
                if para["kind"] == "heading":
                    refs = parse_ref_runs(para.get("refs", "")) if para.get("refs") else ""
                    refs_arg = f", refs: [{refs}]" if refs else ""
                    heading_url = para.get("url") or f"https://route.bible/{book['osis']}.{chapter['chapter']}"
                    lines.append(
                        f"#section({typst_string(clean_spaces(para['raw']))}, "
                        f"{typst_string(heading_url)}"
                        f"{refs_arg})"
                    )
                elif para["kind"] == "blank":
                    lines.append("#v(0.24em)")
                else:
                    markup = paragraph_markup(para, book["osis"], chapter["chapter"])
                    if markup:
                        lines.append(markup)
        lines.append("")
    output_typ.write_text("\n\n".join(lines), encoding="utf-8")


def compile_typst(input_typ, output_pdf, font_dir):
    cmd = [
        "typst",
        "compile",
        "--font-path",
        str(font_dir),
        str(input_typ),
        str(output_pdf),
    ]
    return subprocess.run(cmd, check=False)


def main():
    parser = argparse.ArgumentParser(description="Generate Typst/PDF from BSB USFM")
    parser.add_argument("input_usfm_zip", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--typst-out", type=Path, default=Path("bsb-lexend-route.typ"))
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"))
    parser.add_argument("--testament", choices=("all", "ot", "nt"), default="all")
    parser.add_argument("--no-compile", action="store_true")
    args = parser.parse_args()

    generate_typst(args.input_usfm_zip, args.typst_out, args.testament)
    print(f"Wrote Typst source: {args.typst_out}")

    if args.no_compile:
        return
    result = compile_typst(args.typst_out, args.output_pdf, args.font_dir)
    if result.returncode != 0:
        print("Typst compile failed. Source was still generated.", file=sys.stderr)
        sys.exit(result.returncode)
    print(f"Wrote PDF: {args.output_pdf}")


if __name__ == "__main__":
    main()
