#!/usr/bin/env python3
"""
Generate a readable, reflowed BSB PDF from the BSB EPUB or USFM zip.

This avoids fixed-layout PDF font surgery: text is wrapped with Lexend metrics
from the start, and section headings get clickable route.bible links.
"""

import argparse
from dataclasses import dataclass
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath

from reportlab.lib import colors
from reportlab.lib.pagesizes import portrait
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .add_route_links import build_url, get_chapter_verse_count
from .customize_epub import OSIS_BOOKS
from .download_bsb import BOOK_NAMES


PAGE_SIZE = portrait((504, 756))
BLACK = colors.black
BODY_COLOR = colors.Color(0.08, 0.08, 0.08)
CROSSREF_COLOR = colors.Color(0.10, 0.10, 0.10)
BOOK_ORDER = {name: num for num, name in BOOK_NAMES.items()}
USFM_TO_BOOK = {
    "GEN": "Genesis", "EXO": "Exodus", "LEV": "Leviticus", "NUM": "Numbers",
    "DEU": "Deuteronomy", "JOS": "Joshua", "JDG": "Judges", "RUT": "Ruth",
    "1SA": "1 Samuel", "2SA": "2 Samuel", "1KI": "1 Kings", "2KI": "2 Kings",
    "1CH": "1 Chronicles", "2CH": "2 Chronicles", "EZR": "Ezra", "NEH": "Nehemiah",
    "EST": "Esther", "JOB": "Job", "PSA": "Psalms", "PRO": "Proverbs",
    "ECC": "Ecclesiastes", "SNG": "Song of Solomon", "ISA": "Isaiah", "JER": "Jeremiah",
    "LAM": "Lamentations", "EZK": "Ezekiel", "DAN": "Daniel", "HOS": "Hosea",
    "JOL": "Joel", "AMO": "Amos", "OBA": "Obadiah", "JON": "Jonah",
    "MIC": "Micah", "NAM": "Nahum", "HAB": "Habakkuk", "ZEP": "Zephaniah",
    "HAG": "Haggai", "ZEC": "Zechariah", "MAL": "Malachi", "MAT": "Matthew",
    "MRK": "Mark", "LUK": "Luke", "JHN": "John", "ACT": "Acts",
    "ROM": "Romans", "1CO": "1 Corinthians", "2CO": "2 Corinthians", "GAL": "Galatians",
    "EPH": "Ephesians", "PHP": "Philippians", "COL": "Colossians", "1TH": "1 Thessalonians",
    "2TH": "2 Thessalonians", "1TI": "1 Timothy", "2TI": "2 Timothy", "TIT": "Titus",
    "PHM": "Philemon", "HEB": "Hebrews", "JAS": "James", "1PE": "1 Peter",
    "2PE": "2 Peter", "1JN": "1 John", "2JN": "2 John", "3JN": "3 John",
    "JUD": "Jude", "REV": "Revelation",
}
BOOK_TO_USFM = {book: code for code, book in USFM_TO_BOOK.items()}
REFERENCE_BOOK_NAMES = sorted(OSIS_BOOKS, key=len, reverse=True)
REFERENCE_BOOK_PATTERN = "|".join(re.escape(book) for book in REFERENCE_BOOK_NAMES)


@dataclass
class ReflowSettings:
    single_margin_x: float = 78
    single_margin_top: float = 58
    single_margin_bottom: float = 48
    single_book_title_font: str = "Lexend-Black"
    single_book_title_size: float = 34
    single_book_title_gap: float = 74
    single_body_size: float = 10.0
    single_body_leading: float = 14.8
    single_minor_heading_size: float = 10.4
    single_minor_heading_leading: float = 14.8
    single_section_heading_size: float = 11.2
    single_section_heading_leading: float = 15.4
    single_crossref_size: float = 10.0
    single_dropcap_size: float = 36
    single_dropcap_padding: float = 10
    single_dropcap_min_lines: int = 3
    single_dropcap_protected_lines: int = 2
    single_dropcap_baseline_shift: float = 24
    single_verse_size: float = 6.2
    single_verse_baseline_shift: float = 2.7


def usfm_code_from_name(name):
    stem = PurePosixPath(name).stem.upper()
    match = re.search(r"([1-3]?[A-Z]{2,3})(?:ENGBSB)?$", stem)
    return match.group(1) if match else stem


def register_fonts(font_dir: Path):
    fonts = {
        "Lexend": "Lexend-Regular.ttf",
        "Lexend-Light": "Lexend-Light.ttf",
        "Lexend-Thin": "Lexend-Thin.ttf",
        "Lexend-Bold": "Lexend-Bold.ttf",
        "Lexend-ExtraBold": "Lexend-ExtraBold.ttf",
        "Lexend-Black": "Lexend-Black.ttf",
        "Lexend-Medium": "Lexend-Medium.ttf",
        "Lexend-SemiBold": "Lexend-SemiBold.ttf",
    }
    for font_name, filename in fonts.items():
        font_path = font_dir / filename
        if not font_path.exists():
            raise FileNotFoundError(f"Missing font: {font_path}")
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))


def text_content(element):
    text = visible_text(element)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[A-Za-z0-9])\(", " (", text)
    text = re.sub(r"\b(\d{1,3})(?=[A-Za-z“])", r"\1 ", text)
    return text


def visible_text(element):
    classes = set(element.attrib.get("class", "").split())
    if "fn" in classes:
        return ""

    parts = [element.text or ""]
    for child in element:
        parts.append(visible_text(child))
        parts.append(child.tail or "")
    return "".join(parts)


def verse_numbers(element):
    verses = []
    for child in element.iter():
        classes = set(child.attrib.get("class", "").split())
        if "reftext" not in classes:
            continue
        text = "".join(child.itertext()).strip()
        if text.isdigit():
            verses.append(int(text))
    return verses


def normalize_text(text):
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(?<=[A-Za-z0-9])\(", " (", text)
    text = re.sub(r"\b(\d{1,3})(?=[A-Za-z“])", r"\1 ", text)
    return text


def normalize_run_text(text):
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


def usfm_ref_to_internal(target):
    match = re.match(r"^([1-3]?[A-Z]{2,3})\s+(\d+):(\d+)(?:-(\d+))?$", target.strip())
    if not match:
        return None
    code, chapter, start, _end = match.groups()
    if code not in USFM_TO_BOOK:
        return None
    return f"file:{code}.{int(chapter)}#{int(start)}"


def plain_ref_to_internal(book: str, chapter: str, start: str, end: str = None):
    code = BOOK_TO_USFM.get(book)
    if not code:
        return None
    return f"file:{code}.{int(chapter)}#{int(start)}"


def parse_plain_ref_runs(text):
    runs = []
    pos = 0
    pattern = re.compile(
        rf"\b({REFERENCE_BOOK_PATTERN})\s+(\d+):(\d+)(?:[-–](\d+))?\b"
    )
    for match in pattern.finditer(text):
        if match.start() > pos:
            runs.append({"text": normalize_run_text(text[pos:match.start()]), "target": None})
        book, chapter, start, end = match.groups()
        runs.append({
            "text": normalize_run_text(match.group(0)),
            "target": plain_ref_to_internal(book, chapter, start, end),
        })
        pos = match.end()
    if pos < len(text):
        runs.append({"text": normalize_run_text(text[pos:]), "target": None})
    return [run for run in runs if run["text"]]


def parse_usfm_ref_runs(text):
    runs = []
    pos = 0
    pattern = re.compile(r"\\ref\s+([^|\\]+)\|([^\\]+)\\ref\*")
    for match in pattern.finditer(text):
        if match.start() > pos:
            runs.extend(parse_plain_ref_runs(text[pos:match.start()]))
        display, target = match.groups()
        runs.append({"text": normalize_run_text(display), "target": usfm_ref_to_internal(target) or None})
        pos = match.end()
    if pos < len(text):
        runs.extend(parse_plain_ref_runs(text[pos:]))
    return [run for run in runs if run["text"]]


def strip_usfm_notes(text):
    text = re.sub(r"\\f\s.*?\\f\*", "", text)
    text = re.sub(r"\\x\s.*?\\x\*", "", text)
    return text


def strip_usfm_word_markers(text):
    return re.sub(r"\\w\s+([^|\\]+)(?:\|[^\\]*)?\\w\*", r"\1", text)


def clean_usfm_text(text):
    text = strip_usfm_notes(text)
    text = strip_usfm_word_markers(text)
    text = re.sub(r"\\ref\s+([^|\\]+)\|([^\\]+)\\ref\*", r"\1", text)
    text = re.sub(r"\\[a-z0-9]+\*?", "", text)
    text = normalize_text(text)
    text = re.sub(r"\b(\d{1,3})(?=[A-Za-z“])", r"\1 ", text)
    return text


def usfm_verse_numbers(text):
    return [int(match.group(1)) for match in re.finditer(r"\\v\s+(\d+)", text)]


def usfm_text_with_verses(text):
    text = re.sub(r"\\v\s+(\d+)\s*", r"\1 ", text)
    return clean_usfm_text(text)


def append_usfm_para(chapter_info, kind, text, marker=None):
    if not chapter_info or not text.strip():
        return None
    if kind == "heading":
        para = {
            "kind": "heading",
            "text": clean_usfm_text(text),
            "verses": [],
            "url": None,
            "crossrefs": [],
            "source": chapter_info["source"],
        }
    elif kind == "reference":
        refs = parse_usfm_ref_runs(text)
        if not refs:
            return None
        headings = [p for p in chapter_info["paras"] if p["kind"] == "heading"]
        if headings and not headings[-1].get("crossrefs"):
            headings[-1]["crossrefs"] = refs
            return headings[-1]
        return None
    elif kind == "blank":
        para = {"kind": "blank", "text": "", "verses": [], "url": None, "crossrefs": [], "source": chapter_info["source"]}
    else:
        para = {
            "kind": "poetry" if marker and marker.startswith("q") else "body",
            "marker": marker,
            "text": usfm_text_with_verses(text),
            "verses": usfm_verse_numbers(text),
            "url": None,
            "crossrefs": [],
            "source": chapter_info["source"],
        }
    chapter_info["paras"].append(para)
    return para


def extract_usfm_chapters(usfm_zip_path: Path):
    chapters = []
    with zipfile.ZipFile(usfm_zip_path) as zf:
        names = [name for name in zf.namelist() if name.lower().endswith(".usfm")]
        names.sort(key=lambda n: BOOK_ORDER.get(USFM_TO_BOOK.get(usfm_code_from_name(n), ""), 999))
        for name in names:
            code = usfm_code_from_name(name)
            book = USFM_TO_BOOK.get(code)
            if not book:
                continue
            osis = OSIS_BOOKS.get(book)
            current = None
            pending_kind = None
            pending_marker = None
            pending_text = []

            def flush():
                nonlocal pending_kind, pending_marker, pending_text
                if pending_kind:
                    append_usfm_para(current, pending_kind, " ".join(pending_text), pending_marker)
                pending_kind = None
                pending_marker = None
                pending_text = []

            for raw_line in zf.read(name).decode("utf-8-sig", errors="replace").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                match = re.match(r"^\\([a-z0-9]+)\s*(.*)$", line)
                if not match:
                    if pending_kind:
                        pending_text.append(line)
                    continue
                marker, rest = match.groups()

                if marker == "c":
                    flush()
                    chapter = int(rest.strip())
                    current = {
                        "book": book,
                        "book_num": BOOK_ORDER[book],
                        "osis": osis,
                        "chapter": chapter,
                        "source": f"{code}.{chapter}",
                        "paras": [],
                    }
                    chapters.append(current)
                    continue
                if current is None:
                    continue

                if marker in {"s1", "s2", "s3"}:
                    flush()
                    pending_kind = "heading"
                    pending_marker = marker
                    pending_text = [rest]
                elif marker == "r":
                    flush()
                    append_usfm_para(current, "reference", rest, marker)
                elif marker in {"p", "m", "pmo", "pm", "pi", "q1", "q2", "q3", "qc", "li1", "li2"}:
                    flush()
                    pending_kind = "body"
                    pending_marker = marker
                    pending_text = [rest]
                elif marker == "b":
                    flush()
                    append_usfm_para(current, "blank", "", marker)
                elif marker == "v":
                    if pending_kind not in {"body"}:
                        flush()
                        pending_kind = "body"
                        pending_marker = "p"
                    pending_text.append(f"\\v {rest}")
                else:
                    if pending_kind:
                        pending_text.append(rest)
            flush()

    for chapter_info in chapters:
        add_heading_ranges(chapter_info)
    return chapters


def resolve_href(source_name, href):
    if not href:
        return None
    if href.startswith(("http://", "https://", "mailto:")):
        return href
    href_path, _, fragment = href.partition("#")
    source_dir = PurePosixPath(source_name).parent
    target_path = source_dir / href_path if href_path else PurePosixPath(source_name)
    target = PurePosixPath(target_path).name
    target = re.sub(r"^\d+_(\d+\.htm)$", r"\1", target)
    if fragment:
        return f"file:{target}#{fragment}"
    return f"file:{target}"


def crossref_runs(element, source_name):
    runs = []
    for child in element:
        classes = set(child.attrib.get("class", "").split())
        if child.tag.endswith("span") and "cross" in classes:
            if child.text:
                runs.append({"text": normalize_run_text(child.text), "target": None})
            for item in child:
                text = normalize_run_text("".join(item.itertext()))
                if text:
                    target = resolve_href(source_name, item.attrib.get("href")) if item.tag.endswith("a") else None
                    runs.append({"text": text, "target": target})
                if item.tail:
                    tail = normalize_run_text(item.tail)
                    if tail:
                        runs.append({"text": tail, "target": None})
            if child.tail:
                tail = normalize_run_text(child.tail)
                if tail:
                    runs.append({"text": tail, "target": None})
    return runs


def heading_title(element):
    text = normalize_text(element.text or "")
    if text:
        return text
    full_text = text_content(element)
    return re.sub(r"\s+\(.+\)$", "", full_text).strip() or full_text


def is_minor_heading_text(text):
    if re.match(r"^\d+\s", text):
        return False
    if not text or not text[0].isupper():
        return False
    if len(text) > 55:
        return False
    if re.search(r"[.,;:?!“”]", text):
        return False
    return True


def extract_chapters(epub_path: Path):
    chapters = []
    title_re = re.compile(r"^(.*?)\s+(\d+)\s+BSB$")

    with zipfile.ZipFile(epub_path) as zf:
        for name in zf.namelist():
            if not name.lower().endswith((".htm", ".html", ".xhtml")):
                continue
            try:
                root = ET.fromstring(zf.read(name))
            except ET.ParseError:
                continue

            title_node = root.find(".//{http://www.w3.org/1999/xhtml}title")
            title = "".join(title_node.itertext()).strip() if title_node is not None else ""
            match = title_re.match(title)
            if not match:
                continue

            book, chapter_text = match.groups()
            if book == "Psalm":
                book = "Psalms"
            chapter = int(chapter_text)
            book_num = BOOK_ORDER.get(book)
            if not book_num:
                continue

            paras = []
            for p in root.findall(".//{http://www.w3.org/1999/xhtml}p"):
                value = text_content(p)
                if not value:
                    continue
                klass = p.attrib.get("class", "")
                classes = set(klass.split())
                if classes & {"cross1", "vheading"}:
                    continue
                kind = "heading" if "hdg" in klass.split() else "body"
                verses = verse_numbers(p)
                crossrefs = crossref_runs(p, name) if kind == "heading" else []
                if kind == "heading":
                    value = heading_title(p)
                if kind == "body" and not verses and is_minor_heading_text(value):
                    kind = "minor_heading"
                paras.append({
                    "kind": kind,
                    "text": value,
                    "verses": verses,
                    "url": None,
                    "crossrefs": crossrefs,
                    "source": PurePosixPath(name).name,
                })

            if paras:
                chapter_info = {
                    "book": book,
                    "book_num": book_num,
                    "osis": OSIS_BOOKS.get(book, book),
                    "chapter": chapter,
                    "source": PurePosixPath(name).name,
                    "paras": paras,
                }
                add_heading_ranges(chapter_info)
                chapters.append(chapter_info)

    chapters.sort(key=lambda c: (c["book_num"], c["chapter"]))
    return chapters


def add_heading_ranges(chapter_info):
    paras = chapter_info["paras"]
    osis = chapter_info["osis"]
    chapter = chapter_info["chapter"]
    heading_indices = [
        idx for idx, para in enumerate(paras) if para["kind"] in {"heading", "minor_heading"}
    ]

    for position, idx in enumerate(heading_indices):
        next_idx = heading_indices[position + 1] if position + 1 < len(heading_indices) else len(paras)
        start_verse = None
        end_verse = None

        for para in paras[idx + 1 : next_idx]:
            if para["verses"] and start_verse is None:
                start_verse = para["verses"][0]
            if para["verses"]:
                end_verse = para["verses"][-1]

        if start_verse is None:
            start_verse = end_verse or 1
        if end_verse is None:
            end_verse = get_chapter_verse_count(osis, chapter) or start_verse
        if start_verse > end_verse:
            start_verse = end_verse

        paras[idx]["url"] = build_url(osis, chapter, start_verse, end_verse)


class ReflowWriter:
    def __init__(self, output_path: Path, columns: int = 2, settings: ReflowSettings = None):
        if columns not in {1, 2}:
            raise ValueError("columns must be 1 or 2")
        self.settings = settings or ReflowSettings()
        self.canvas = canvas.Canvas(str(output_path), pagesize=PAGE_SIZE)
        self.page_width, self.page_height = PAGE_SIZE
        self.columns = columns
        self.margin_x = self.settings.single_margin_x if columns == 1 else 36
        self.margin_top = self.settings.single_margin_top if columns == 1 else 54
        self.margin_bottom = self.settings.single_margin_bottom if columns == 1 else 42
        self.gutter = 22 if columns == 2 else 0
        self.column_width = (self.page_width - 2 * self.margin_x - self.gutter * (columns - 1)) / columns
        self.column = 0
        self.column_top_y = self.page_height - self.margin_top
        self.y = self.column_top_y
        self.page_num = 0
        self.current_book = None
        self.started = False
        self.body_color = BODY_COLOR
        self.crossref_color = CROSSREF_COLOR
        self.black = BLACK
        self.dropcap_lines_remaining = 0
        self.dropcap_indent = 0
        self.destinations = set()

    def save(self):
        if self.started:
            self.canvas.save()

    def new_page(self):
        if self.started:
            self.canvas.showPage()
        self.started = True
        self.page_num += 1
        self.column = 0
        self.column_top_y = self.page_height - self.margin_top
        self.y = self.column_top_y
        self.dropcap_lines_remaining = 0
        self.dropcap_indent = 0
        self.canvas.setFillColor(self.black)

    def next_column(self):
        if self.column < self.columns - 1:
            self.column += 1
            self.y = self.column_top_y
            self.dropcap_lines_remaining = 0
            self.dropcap_indent = 0
        else:
            self.new_page()

    def ensure_space(self, needed):
        if self.y - needed < self.margin_bottom:
            self.next_column()

    def x(self):
        return self.margin_x + self.column * (self.column_width + self.gutter)

    def draw_book_title(self, book):
        self.new_page()
        self.current_book = book
        font = self.settings.single_book_title_font if self.columns == 1 else "Lexend"
        size = self.settings.single_book_title_size if self.columns == 1 else 31
        self.canvas.setFillColor(self.black)
        self.canvas.setFont(font, size)
        width = pdfmetrics.stringWidth(book, font, size)
        self.canvas.drawString((self.page_width - width) / 2, self.y - 8, book)
        self.y -= self.settings.single_book_title_gap if self.columns == 1 else 64
        self.column_top_y = self.y

    def draw_chapter_title(self, book, chapter, osis):
        gap = 18 if self.y < self.column_top_y - 1 else 0
        self.ensure_space(gap + 30)
        self.y -= gap
        url = f"https://route.bible/{osis}.{chapter}"
        text = f"{book} {chapter}"
        font = "Lexend-Medium"
        size = 12
        self.canvas.setFillColor(self.black)
        self.canvas.setFont(font, size)
        x = self.x()
        y = self.y
        self.canvas.drawString(x, y, text)
        self.canvas.linkURL(url, (x, y - 2, x + pdfmetrics.stringWidth(text, font, size), y + size), relative=0)
        self.y -= 22

    def add_destination(self, name, top=None):
        if name:
            if top is None:
                self.canvas.bookmarkPage(name)
            else:
                self.canvas.bookmarkPage(name, fit="FitH", top=top)
            self.destinations.add(name)

    def add_verse_destination(self, source, verse, y, size):
        name = f"file:{source}#{verse}"
        top = min(self.page_height, y + size + 4)
        self.add_destination(name, top=top)

    def wrap(self, text, font, size, width):
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if pdfmetrics.stringWidth(candidate, font, size) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines

    def draw_paragraph(self, para, osis, chapter, initial_verse=None, keep_after_override=None):
        text = para["text"]
        kind = para["kind"]
        url = para["url"]
        if kind == "heading":
            self.dropcap_lines_remaining = 0
            self.dropcap_indent = 0
            self.draw_section_heading(
                text,
                para.get("crossrefs", []),
                url or f"https://route.bible/{osis}.{chapter}",
                keep_after=keep_after_override,
            )
            return
        elif kind == "blank":
            self.dropcap_lines_remaining = 0
            self.dropcap_indent = 0
            self.ensure_space(8)
            self.y -= 8
            return
        elif kind == "minor_heading":
            self.dropcap_lines_remaining = 0
            self.dropcap_indent = 0
            font = "Lexend-Medium"
            size = self.settings.single_minor_heading_size if self.columns == 1 else 9.2
            leading = self.settings.single_minor_heading_leading if self.columns == 1 else 11.8
            before = 7 if self.columns == 1 else 5
            after = 2 if self.columns == 1 else 1
            keep_after = keep_after_override if keep_after_override is not None else 32
            url = url or f"https://route.bible/{osis}.{chapter}"
        elif kind in {"body", "poetry"}:
            font = "Lexend-Light"
            size = self.settings.single_body_size if self.columns == 1 else 8.9
            leading = self.settings.single_body_leading if self.columns == 1 else 11.4
            before = 1.5 if kind == "body" else 1
            after = 5.5 if self.columns == 1 and kind == "body" else 4 if kind == "body" else 2
            url = None
            if para.get("verses") and para["verses"][0] == 1 and text.startswith("1 "):
                self.draw_dropcap_paragraph(para, font, size, leading, before, after, osis, chapter)
                return
            if kind == "poetry":
                self.draw_poetry_paragraph(para, font, size, leading, before, after, osis, chapter, initial_verse)
                return
            runs = self.body_runs(text, para.get("verses", []), font, size, osis, chapter, initial_verse)
            if self.dropcap_lines_remaining:
                protected_lines = min(self.dropcap_lines_remaining, self.settings.single_dropcap_protected_lines)
                line_specs = [
                    {"width": self.column_width - self.dropcap_indent, "indent": self.dropcap_indent}
                    for _ in range(protected_lines)
                ]
                line_specs.extend(
                    {"width": self.column_width, "indent": 0}
                    for _ in range(max(0, self.dropcap_lines_remaining - protected_lines))
                )
                line_specs.append({"width": self.column_width, "indent": 0})
                lines = self.wrap_styled_runs_variable(runs, line_specs)
                effective_before = 0
            else:
                lines = [(line_runs, 0) for line_runs in self.wrap_styled_runs(runs, self.column_width)]
                effective_before = before
            needed = effective_before + leading * len(lines) + after
            self.ensure_space(needed)
            self.y -= effective_before

            for line_runs, indent_x in lines:
                cursor_x = self.x() + indent_x
                link_start = None
                link_end = None
                link_url = None
                for run in line_runs:
                    if run.get("verse_num") is not None:
                        self.add_verse_destination(para["source"], run["verse_num"], self.y + run.get("baseline_shift", 0), run["size"])
                    self.draw_run(cursor_x, self.y, run)
                    width = pdfmetrics.stringWidth(run["text"], run["font"], run["size"])
                    link_start, link_end, link_url = self.update_line_link(
                        link_start,
                        link_end,
                        link_url,
                        run.get("link_url"),
                        cursor_x,
                        cursor_x + width,
                        self.y,
                        run["size"],
                    )
                    cursor_x += width
                self.flush_line_link(link_start, link_end, link_url, self.y, size)
                self.y -= leading
                if self.dropcap_lines_remaining:
                    self.dropcap_lines_remaining -= 1
                    if not self.dropcap_lines_remaining:
                        self.dropcap_indent = 0

            self.y -= after
            return
        else:
            return

        lines = self.wrap(text, font, size, self.column_width)
        needed = before + leading * len(lines) + after + (keep_after if kind == "minor_heading" else 0)
        self.ensure_space(needed)
        self.y -= before

        link_top = self.y + size
        link_left = self.x()
        link_right = self.x()
        link_bottom = self.y - leading * max(len(lines) - 1, 0) - 2

        self.canvas.setFont(font, size)
        self.canvas.setFillColor(self.black)
        for line in lines:
            self.canvas.drawString(self.x(), self.y, line)
            link_right = max(link_right, self.x() + pdfmetrics.stringWidth(line, font, size))
            self.y -= leading

        if url:
            self.canvas.linkURL(url, (link_left, link_bottom, link_right, link_top), relative=0)

        self.y -= after

    def draw_dropcap_paragraph(self, para, body_font, body_size, leading, before, after, osis, chapter):
        text = para["text"][2:].strip()
        chapter_text = str(chapter)
        chapter_url = f"https://route.bible/{osis}.{chapter}"
        drop_font = "Lexend-Medium"
        drop_size = self.settings.single_dropcap_size if self.columns == 1 else 30
        drop_width = pdfmetrics.stringWidth(chapter_text, drop_font, drop_size)
        indent = drop_width + self.settings.single_dropcap_padding if self.columns == 1 else drop_width + 7
        line_specs = [
            {"width": self.column_width - indent, "indent": indent},
            {"width": self.column_width - indent, "indent": indent},
            {"width": self.column_width - indent, "indent": indent},
            {"width": self.column_width, "indent": 0},
        ]
        lines = self.wrap_styled_runs_variable(
            self.body_runs(text, [], body_font, body_size, osis, chapter, 1, superscript_verses=False),
            line_specs,
        )
        min_drop_lines = self.settings.single_dropcap_min_lines if self.columns == 1 else 3
        drop_line_count = max(len(lines), min_drop_lines)
        needed = before + max(drop_size, leading * drop_line_count) + after
        self.ensure_space(needed)
        self.y -= before

        self.canvas.setFont(drop_font, drop_size)
        self.canvas.setFillColor(self.black)
        drop_x = self.x()
        drop_y = self.y - (self.settings.single_dropcap_baseline_shift if self.columns == 1 else 18)
        self.add_verse_destination(para["source"], 1, drop_y, drop_size)
        self.canvas.drawString(drop_x, drop_y, chapter_text)
        self.canvas.linkURL(
            chapter_url,
            (drop_x, drop_y - 2, drop_x + drop_width, drop_y + drop_size),
            relative=0,
        )
        for line_runs, indent_x in lines:
            cursor_x = self.x() + indent_x
            link_start = None
            link_end = None
            link_url = None
            for run in line_runs:
                self.draw_run(cursor_x, self.y, run)
                width = pdfmetrics.stringWidth(run["text"], run["font"], run["size"])
                link_start, link_end, link_url = self.update_line_link(
                    link_start,
                    link_end,
                    link_url,
                    run.get("link_url"),
                    cursor_x,
                    cursor_x + width,
                    self.y,
                    run["size"],
                )
                cursor_x += width
            self.flush_line_link(link_start, link_end, link_url, self.y, body_size)
            self.y -= leading

        remaining = drop_line_count - len(lines)
        if remaining > 0:
            self.dropcap_lines_remaining = remaining
            self.dropcap_indent = indent
        else:
            self.dropcap_lines_remaining = 0
            self.dropcap_indent = 0
            self.y -= after

    def draw_poetry_paragraph(self, para, body_font, body_size, leading, before, after, osis, chapter, initial_verse):
        marker = para.get("marker") or "q1"
        base_indent = {"q1": 14, "q2": 28, "q3": 42, "qc": 20}.get(marker, 14)
        runs = self.body_runs(para["text"], para.get("verses", []), body_font, body_size, osis, chapter, initial_verse)
        if self.dropcap_lines_remaining:
            protected_lines = min(self.dropcap_lines_remaining, self.settings.single_dropcap_protected_lines)
            line_specs = [
                {
                    "width": self.column_width - max(base_indent, self.dropcap_indent),
                    "indent": max(base_indent, self.dropcap_indent),
                }
                for _ in range(protected_lines)
            ]
            line_specs.extend(
                {"width": self.column_width - base_indent, "indent": base_indent}
                for _ in range(max(0, self.dropcap_lines_remaining - protected_lines))
            )
            line_specs.append({"width": self.column_width - base_indent, "indent": base_indent})
            lines = self.wrap_styled_runs_variable(runs, line_specs)
            effective_before = 0
        else:
            lines = [
                (line_runs, base_indent)
                for line_runs in self.wrap_styled_runs(runs, self.column_width - base_indent)
            ]
            effective_before = before

        needed = effective_before + leading * len(lines) + after
        self.ensure_space(needed)
        self.y -= effective_before

        for line_runs, indent_x in lines:
            cursor_x = self.x() + indent_x
            link_start = None
            link_end = None
            link_url = None
            for run in line_runs:
                if run.get("verse_num") is not None:
                    self.add_verse_destination(para["source"], run["verse_num"], self.y + run.get("baseline_shift", 0), run["size"])
                self.draw_run(cursor_x, self.y, run)
                width = pdfmetrics.stringWidth(run["text"], run["font"], run["size"])
                link_start, link_end, link_url = self.update_line_link(
                    link_start,
                    link_end,
                    link_url,
                    run.get("link_url"),
                    cursor_x,
                    cursor_x + width,
                    self.y,
                    run["size"],
                )
                cursor_x += width
            self.flush_line_link(link_start, link_end, link_url, self.y, body_size)
            self.y -= leading
            if self.dropcap_lines_remaining:
                self.dropcap_lines_remaining -= 1
                if not self.dropcap_lines_remaining:
                    self.dropcap_indent = 0

        self.y -= after

    def update_line_link(self, start, end, current_url, next_url, x1, x2, y, size):
        if not next_url:
            self.flush_line_link(start, end, current_url, y, size)
            return None, None, None
        if current_url is None:
            return x1, x2, next_url
        if current_url == next_url:
            return start, x2, current_url
        self.flush_line_link(start, end, current_url, y, size)
        return x1, x2, next_url

    def flush_line_link(self, start, end, url, y, size):
        if start is None or end is None or not url:
            return
        self.canvas.linkURL(url, (start, y - 2, end, y + size), relative=0)

    def draw_run(self, x, y, run):
        self.canvas.setFillColor(run.get("color", self.body_color))
        self.canvas.setFont(run["font"], run["size"])
        self.canvas.drawString(x, y + run.get("baseline_shift", 0), run["text"])

    def estimate_paragraph_intro_height(self, para, osis, chapter, initial_verse=None):
        kind = para["kind"]
        text = para["text"]
        if kind not in {"body", "poetry"}:
            return 0

        body_font = "Lexend-Light"
        body_size = self.settings.single_body_size if self.columns == 1 else 8.9
        leading = self.settings.single_body_leading if self.columns == 1 else 11.4
        if kind == "body":
            before = 1.5
            after = 5.5 if self.columns == 1 else 4
        else:
            before = 1
            after = 2

        if para.get("verses") and para["verses"][0] == 1 and text.startswith("1 "):
            drop_font = "Lexend-Medium"
            drop_size = self.settings.single_dropcap_size if self.columns == 1 else 30
            chapter_text = str(chapter)
            drop_width = pdfmetrics.stringWidth(chapter_text, drop_font, drop_size)
            indent = drop_width + self.settings.single_dropcap_padding if self.columns == 1 else drop_width + 7
            line_specs = [
                {"width": self.column_width - indent, "indent": indent},
                {"width": self.column_width - indent, "indent": indent},
                {"width": self.column_width - indent, "indent": indent},
                {"width": self.column_width, "indent": 0},
            ]
            lines = self.wrap_styled_runs_variable(
                self.body_runs(text[2:].strip(), [], body_font, body_size, osis, chapter, 1, superscript_verses=False),
                line_specs,
            )
            min_drop_lines = self.settings.single_dropcap_min_lines if self.columns == 1 else 3
            drop_line_count = max(len(lines), min_drop_lines)
            return before + max(drop_size, leading * drop_line_count) + after

        if kind == "poetry":
            marker = para.get("marker") or "q1"
            base_indent = {"q1": 14, "q2": 28, "q3": 42, "qc": 20}.get(marker, 14)
            runs = self.body_runs(text, para.get("verses", []), body_font, body_size, osis, chapter, initial_verse)
            lines = self.wrap_styled_runs(runs, self.column_width - base_indent)
        else:
            runs = self.body_runs(text, para.get("verses", []), body_font, body_size, osis, chapter, initial_verse)
            lines = self.wrap_styled_runs(runs, self.column_width)

        intro_lines = min(len(lines), 2)
        return before + leading * intro_lines + after

    def draw_section_heading(self, text, crossrefs, url, keep_after=None):
        title_font = "Lexend-Medium"
        title_size = self.settings.single_section_heading_size if self.columns == 1 else 9.8
        title_leading = self.settings.single_section_heading_leading if self.columns == 1 else 12.8
        crossref_font = "Lexend"
        crossref_size = self.settings.single_crossref_size if self.columns == 1 else 8.7
        heading_runs = self.heading_runs(text, crossrefs, url, title_font, title_size, crossref_font, crossref_size)
        heading_lines = self.wrap_styled_runs(heading_runs, self.column_width)
        before = 10 if self.columns == 1 else 7
        after = 5 if self.columns == 1 else 4
        if keep_after is None:
            keep_after = 32
        needed = before + title_leading * len(heading_lines) + after + keep_after
        self.ensure_space(needed)
        self.y -= before

        for line_runs in heading_lines:
            cursor_x = self.x()
            link_start = None
            link_end = None
            link_target = None
            link_kind = None
            for run in line_runs:
                text = run["text"]
                target = run.get("target")
                link_url = run.get("link_url")
                width = pdfmetrics.stringWidth(text, run["font"], run["size"])
                self.canvas.setFillColor(run.get("color", self.black))
                self.canvas.setFont(run["font"], run["size"])
                self.canvas.drawString(cursor_x, self.y, text)
                next_target = target or link_url
                next_kind = "rect" if target and target.startswith("file:") else "url" if next_target else None
                link_start, link_end, link_target, link_kind = self.update_heading_link(
                    link_start,
                    link_end,
                    link_target,
                    link_kind,
                    next_target,
                    next_kind,
                    cursor_x,
                    cursor_x + width,
                    self.y,
                    run["size"],
                )
                cursor_x += width
            self.flush_heading_link(link_start, link_end, link_target, link_kind, self.y, title_size)
            self.y -= title_leading

        self.y -= after

    def update_heading_link(self, start, end, current_target, current_kind, next_target, next_kind, x1, x2, y, size):
        if not next_target:
            self.flush_heading_link(start, end, current_target, current_kind, y, size)
            return None, None, None, None
        if current_target is None:
            return x1, x2, next_target, next_kind
        if current_target == next_target and current_kind == next_kind:
            return start, x2, current_target, current_kind
        self.flush_heading_link(start, end, current_target, current_kind, y, size)
        return x1, x2, next_target, next_kind

    def flush_heading_link(self, start, end, target, kind, y, size):
        if start is None or end is None or not target:
            return
        rect = (start, y - 2, end, y + size)
        if kind == "rect":
            self.canvas.linkRect("", target, rect, relative=0)
        else:
            self.canvas.linkURL(target, rect, relative=0)

    def heading_runs(self, title, crossrefs, url, title_font, title_size, crossref_font, crossref_size):
        runs = []
        for token in self.run_tokens({"text": title, "target": None}):
            runs.append({
                "text": token["text"],
                "font": title_font,
                "size": title_size,
                "link_url": url,
                "color": self.black,
            })

        if crossrefs:
            runs.append({
                "text": " ",
                "font": title_font,
                "size": title_size,
                "color": self.black,
            })
            for run in crossrefs:
                for token in self.run_tokens(run):
                    runs.append({
                        "text": token["text"],
                        "font": crossref_font,
                        "size": crossref_size,
                        "target": token.get("target"),
                        "color": self.crossref_color,
                    })
        return runs

    def wrap_runs(self, runs, font, size, width):
        if not runs:
            return []

        lines = []
        current = []
        current_width = 0
        for run in runs:
            for token in self.run_tokens(run):
                token_width = pdfmetrics.stringWidth(token["text"], font, size)
                if current and current_width + token_width > width:
                    lines.append(current)
                    current = []
                    current_width = 0
                current.append(token)
                current_width += token_width
        if current:
            lines.append(current)
        return lines

    def wrap_styled_runs_variable(self, runs, line_specs):
        lines = []
        current = []
        current_width = 0
        line_index = 0
        width = line_specs[0]["width"]
        i = 0
        while i < len(runs):
            run = runs[i]
            unit = [run]
            token_width = pdfmetrics.stringWidth(run["text"], run["font"], run["size"])
            if run.get("keep_with_next") and i + 1 < len(runs):
                next_run = runs[i + 1]
                unit.append(next_run)
                token_width += pdfmetrics.stringWidth(next_run["text"], next_run["font"], next_run["size"])

            if current and current_width + token_width > width:
                indent = line_specs[min(line_index, len(line_specs) - 1)]["indent"]
                lines.append((current, indent))
                current = []
                current_width = 0
                line_index += 1
                width = line_specs[min(line_index, len(line_specs) - 1)]["width"]

            current.extend(unit)
            current_width += token_width
            i += len(unit)

        if current:
            indent = line_specs[min(line_index, len(line_specs) - 1)]["indent"]
            lines.append((current, indent))
        return lines

    def body_runs(self, text, verses, body_font, body_size, osis, chapter, initial_verse=None, superscript_verses=True):
        verse_set = {str(verse) for verse in verses}
        runs = []
        current_url = build_url(osis, chapter, initial_verse, initial_verse) if initial_verse else None
        for token in self.run_tokens({"text": text, "target": None}):
            parts = self.split_verse_token(token["text"], verse_set)
            for part_text, verse_num in parts:
                is_verse = verse_num is not None
                if is_verse:
                    current_url = build_url(osis, chapter, verse_num, verse_num)
                use_superscript = is_verse and superscript_verses and self.columns == 1
                verse_size = self.settings.single_verse_size if use_superscript else body_size
                runs.append({
                    "text": part_text,
                    "font": "Lexend-Medium" if is_verse else body_font,
                    "size": verse_size if is_verse else body_size,
                    "baseline_shift": self.settings.single_verse_baseline_shift if use_superscript else 0,
                    "verse_num": verse_num if is_verse else None,
                    "keep_with_next": is_verse,
                    "link_url": current_url,
                    "color": self.black if is_verse else self.body_color,
                })
        return runs

    def wrap_styled_runs(self, runs, width):
        lines = []
        current = []
        current_width = 0
        i = 0
        while i < len(runs):
            run = runs[i]
            unit = [run]
            token_width = pdfmetrics.stringWidth(run["text"], run["font"], run["size"])
            if run.get("keep_with_next") and i + 1 < len(runs):
                next_run = runs[i + 1]
                unit.append(next_run)
                token_width += pdfmetrics.stringWidth(next_run["text"], next_run["font"], next_run["size"])

            if current and current_width + token_width > width:
                lines.append(current)
                current = []
                current_width = 0
            current.extend(unit)
            current_width += token_width
            i += len(unit)

        if current:
            lines.append(current)
        return lines

    @staticmethod
    def split_verse_token(token, verse_set):
        match = re.match(r"^(\d{1,3})(\s*)$", token)
        if match and match.group(1) in verse_set:
            return [(token, int(match.group(1)))]

        match = re.match(r"^(\d{1,3})(\S.*)$", token)
        if match and match.group(1) in verse_set:
            return [(f"{match.group(1)} ", int(match.group(1))), (match.group(2), None)]

        return [(token, None)]

    @staticmethod
    def run_tokens(run):
        parts = re.findall(r"\S+\s*", run["text"])
        return [{"text": part, "target": run.get("target")} for part in parts if part]

def extract_input_chapters(input_path: Path):
    if input_path.suffix.lower() == ".zip":
        return extract_usfm_chapters(input_path)
    return extract_chapters(input_path)


def next_verse_paragraph(chapters, chapter_index, para_index):
    for next_chapter_index in range(chapter_index, len(chapters)):
        chapter = chapters[next_chapter_index]
        start_index = para_index + 1 if next_chapter_index == chapter_index else 0
        for next_para in chapter["paras"][start_index:]:
            if next_para["kind"] in {"body", "poetry"} and next_para.get("verses"):
                return chapter, next_para
            if next_para["kind"] in {"heading", "minor_heading"}:
                return None, None
    return None, None


def generate(input_path: Path, output_pdf: Path, font_dir: Path, columns: int = 2, settings: ReflowSettings = None):
    register_fonts(font_dir)
    chapters = extract_input_chapters(input_path)
    if not chapters:
        raise RuntimeError(f"No chapters found in {input_path}")

    writer = ReflowWriter(output_pdf, columns=columns, settings=settings)
    last_book = None
    for chapter_index, chapter in enumerate(chapters):
        if chapter["book"] != last_book:
            writer.draw_book_title(chapter["book"])
            last_book = chapter["book"]
        writer.add_destination(f"file:{chapter['source']}")
        if chapter["chapter"] != 1 and writer.y < writer.column_top_y - 1:
            writer.ensure_space(50)
            writer.y -= 18
        current_verse = None
        for para_index, para in enumerate(chapter["paras"]):
            keep_after = None
            if para["kind"] in {"heading", "minor_heading"}:
                next_chapter, next_para = next_verse_paragraph(chapters, chapter_index, para_index)
                if next_para:
                    keep_after = writer.estimate_paragraph_intro_height(
                        next_para,
                        next_chapter["osis"],
                        next_chapter["chapter"],
                    )
                    if next_chapter is not chapter and next_chapter["chapter"] != 1:
                        keep_after += 18
            writer.draw_paragraph(para, chapter["osis"], chapter["chapter"], current_verse, keep_after)
            if para["kind"] in {"body", "poetry"} and para.get("verses"):
                current_verse = para["verses"][-1]
    writer.save()


def main():
    parser = argparse.ArgumentParser(description="Generate a reflowed Lexend BSB PDF from EPUB or USFM zip")
    parser.add_argument("input_path", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"))
    parser.add_argument("--columns", type=int, choices=(1, 2), default=2)
    parser.add_argument("--single-margin-x", type=float, default=78)
    parser.add_argument("--single-margin-top", type=float, default=58)
    parser.add_argument("--single-margin-bottom", type=float, default=48)
    parser.add_argument("--single-book-title-font", default="Lexend-Black")
    parser.add_argument("--single-book-title-size", type=float, default=34)
    parser.add_argument("--single-book-title-gap", type=float, default=74)
    parser.add_argument("--single-body-size", type=float, default=10.0)
    parser.add_argument("--single-body-leading", type=float, default=14.8)
    parser.add_argument("--single-minor-heading-size", type=float, default=10.4)
    parser.add_argument("--single-minor-heading-leading", type=float, default=14.8)
    parser.add_argument("--single-section-heading-size", type=float, default=11.2)
    parser.add_argument("--single-section-heading-leading", type=float, default=15.4)
    parser.add_argument("--single-crossref-size", type=float, default=10.0)
    parser.add_argument("--single-dropcap-size", type=float, default=36)
    parser.add_argument("--single-dropcap-padding", type=float, default=10)
    parser.add_argument("--single-dropcap-min-lines", type=int, default=3)
    parser.add_argument("--single-dropcap-protected-lines", type=int, default=2)
    parser.add_argument("--single-dropcap-baseline-shift", type=float, default=24)
    parser.add_argument("--single-verse-size", type=float, default=6.2)
    parser.add_argument("--single-verse-baseline-shift", type=float, default=2.7)
    args = parser.parse_args()

    settings = ReflowSettings(
        single_margin_x=args.single_margin_x,
        single_margin_top=args.single_margin_top,
        single_margin_bottom=args.single_margin_bottom,
        single_book_title_font=args.single_book_title_font,
        single_book_title_size=args.single_book_title_size,
        single_book_title_gap=args.single_book_title_gap,
        single_body_size=args.single_body_size,
        single_body_leading=args.single_body_leading,
        single_minor_heading_size=args.single_minor_heading_size,
        single_minor_heading_leading=args.single_minor_heading_leading,
        single_section_heading_size=args.single_section_heading_size,
        single_section_heading_leading=args.single_section_heading_leading,
        single_crossref_size=args.single_crossref_size,
        single_dropcap_size=args.single_dropcap_size,
        single_dropcap_padding=args.single_dropcap_padding,
        single_dropcap_min_lines=args.single_dropcap_min_lines,
        single_dropcap_protected_lines=args.single_dropcap_protected_lines,
        single_dropcap_baseline_shift=args.single_dropcap_baseline_shift,
        single_verse_size=args.single_verse_size,
        single_verse_baseline_shift=args.single_verse_baseline_shift,
    )

    try:
        generate(args.input_path, args.output_pdf, args.font_dir, columns=args.columns, settings=settings)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
