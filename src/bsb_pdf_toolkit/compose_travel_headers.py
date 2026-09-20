"""Extract a running-header QA sheet from compiled John (grid proof).

Compiles John on the live travel densify compose, then copies leaves that
exercise SPEC §5 running matter: title (no chrome), verso left / recto
right, same-chapter ``BOOK · ch:first–last``, and a cross-chapter span.
Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .compose_travel_hotspots import (
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    normalize_pdf_text,
    render_hotspot_pngs,
)
from .generate_travel_pdf import DEFAULT_GRID_FONT_DIR, DEFAULT_USFM, GRID_PROOF_WATERMARK

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "headers-john-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "headers-john-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-running-headers-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "headers"
PNG_DPI = 120

HEADER_QA_BOOKS = ("John",)
HEADER_REQUIRED_SLUGS = ("john-title", "john-verso", "john-recto", "john-cross")

# Compact travel grammar: JOHN · 4:17–38 or JOHN · 3:31–4:2 or JOHN · 4
HEADER_LINE_RE = re.compile(
    r"^(?P<book>[A-Z][A-Z0-9 ]{0,24}?)\s*[·.]\s*(?P<start_ch>\d+)"
    r"(?::(?P<start_v>\d+)(?:[–-](?:(?P<end_ch>\d+):)?(?P<end_v>\d+))?)?$"
)
HEADER_RANGE_RE = re.compile(
    r"JOHN\s*[·.]\s*\d+:\d+(?:[–-]\d+(?::\d+)?)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class HeaderInfo:
    book: str
    display: str
    kind: str
    start_ch: int | None = None
    start_v: int | None = None
    end_ch: int | None = None
    end_v: int | None = None


def parse_page_header(text: str) -> HeaderInfo:
    """Read the running head from the first few extracted lines."""
    seen = 0
    for line in (text or "").splitlines():
        stripped = normalize_pdf_text(line)
        if not stripped:
            continue
        seen += 1
        match = HEADER_LINE_RE.fullmatch(stripped)
        if match:
            return _info_from_match(match)
        if seen >= 3:
            break
    return HeaderInfo(book="", display="", kind="none")


def _info_from_match(match: re.Match[str]) -> HeaderInfo:
    book = match.group("book").strip()
    start_ch = int(match.group("start_ch"))
    start_v = match.group("start_v")
    if start_v is None:
        return HeaderInfo(
            book=book,
            display=f"{book} · {start_ch}",
            kind="chapter-only",
            start_ch=start_ch,
        )
    start_v_n = int(start_v)
    end_ch = int(match.group("end_ch")) if match.group("end_ch") else start_ch
    end_v = int(match.group("end_v")) if match.group("end_v") else start_v_n
    if end_ch != start_ch:
        display = f"{book} · {start_ch}:{start_v_n}–{end_ch}:{end_v}"
        kind = "cross-chapter"
    elif end_v != start_v_n:
        display = f"{book} · {start_ch}:{start_v_n}–{end_v}"
        kind = "same-chapter"
    else:
        display = f"{book} · {start_ch}:{start_v_n}"
        kind = "same-chapter"
    return HeaderInfo(
        book=book,
        display=display,
        kind=kind,
        start_ch=start_ch,
        start_v=start_v_n,
        end_ch=end_ch,
        end_v=end_v,
    )


def page_has_verse_header(text: str) -> bool:
    """True when extracted page text includes a book + chapter:verse running head."""
    return parse_page_header(text).kind in {"same-chapter", "cross-chapter"}


def page_folio(text: str) -> str | None:
    """Return the trailing folio digits when the last extracted line is a page number."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if lines and lines[-1].isdigit():
        return lines[-1]
    return None


def select_header_pages(
    page_texts: list[str],
) -> list[tuple[str, int, HeaderInfo]]:
    """Pick title / verso / recto / cross-chapter leaves from a compiled John."""
    if not page_texts:
        raise ValueError("source PDF has no pages")
    parsed = [(index, parse_page_header(text)) for index, text in enumerate(page_texts, start=1)]
    chosen: dict[str, tuple[int, HeaderInfo]] = {}
    used: set[int] = set()

    def take(slug: str, predicate) -> None:
        if slug in chosen:
            return
        for page_no, info in parsed:
            if page_no in used:
                continue
            if predicate(page_no, info):
                chosen[slug] = (page_no, info)
                used.add(page_no)
                return

    take("john-title", lambda page_no, info: page_no == 1 and info.kind == "none")
    take("john-verso", lambda page_no, info: page_no % 2 == 0 and info.kind == "same-chapter")
    take("john-recto", lambda page_no, info: page_no % 2 == 1 and page_no > 1 and info.kind == "same-chapter")
    take("john-cross", lambda page_no, info: info.kind == "cross-chapter")
    take("john-chapter-only", lambda page_no, info: info.kind == "chapter-only")

    missing = [slug for slug in HEADER_REQUIRED_SLUGS if slug not in chosen]
    if missing:
        raise ValueError(f"could not find header QA leaves: {missing}")
    items = [(slug, page_no, info) for slug, (page_no, info) in chosen.items()]
    items.sort(key=lambda item: item[1])
    return items


def validate_header_selection(
    chosen: list[tuple[str, int, HeaderInfo]],
    page_texts: list[str],
) -> None:
    """Require the SPEC §5 leaf set and matching headers on each source page."""
    slugs = {slug for slug, _, _ in chosen}
    missing = [slug for slug in HEADER_REQUIRED_SLUGS if slug not in slugs]
    if missing:
        raise ValueError(f"header QA missing required leaves: {missing}")
    count = len(page_texts)
    for slug, page_no, info in chosen:
        if page_no < 1 or page_no > count:
            raise ValueError(f"John PDF has {count} pages; cannot take {page_no}")
        parsed = parse_page_header(page_texts[page_no - 1])
        if parsed.kind != info.kind or parsed.display != info.display:
            raise ValueError(f"{slug}: header mismatch on page {page_no}")
        folio = page_folio(page_texts[page_no - 1])
        if slug == "john-title":
            if parsed.kind != "none":
                raise ValueError(f"{slug}: title leaf should have no running head")
            if folio == "1":
                raise ValueError(f"{slug}: title leaf should have no folio")
            continue
        if slug == "john-verso" and (page_no % 2 != 0 or parsed.kind != "same-chapter"):
            raise ValueError(f"{slug}: need an even same-chapter leaf, got page {page_no} {parsed.display}")
        if slug == "john-recto" and (page_no % 2 != 1 or parsed.kind != "same-chapter"):
            raise ValueError(f"{slug}: need an odd same-chapter leaf, got page {page_no} {parsed.display}")
        if slug == "john-cross" and parsed.kind != "cross-chapter":
            raise ValueError(f"{slug}: page {page_no} is not a cross-chapter range")
        if slug == "john-chapter-only" and parsed.kind != "chapter-only":
            raise ValueError(f"{slug}: page {page_no} is not a chapter-only fallback")
        if folio != str(page_no):
            raise ValueError(f"{slug}: page {page_no} is missing a centered folio")


def format_selection(chosen: list[tuple[str, int, HeaderInfo]]) -> str:
    lines = ["Running-header QA leaves (source page → leaf):"]
    for slug, page_no, info in chosen:
        label = info.display or "(no running head)"
        lines.append(f"  {slug}: source p.{page_no}  {label} ({info.kind})")
    return "\n".join(lines)


def prune_header_pngs(png_dir: Path, slugs: list[str]) -> list[Path]:
    """Remove leftover header previews that are not in the current leaf set."""
    keep = {f"{slug}.png" for slug in slugs}
    removed: list[Path] = []
    if not png_dir.is_dir():
        return removed
    for path in sorted(png_dir.glob("*.png")):
        if path.name not in keep:
            path.unlink()
            removed.append(path)
    return removed


def typst_uses_densify(typst_text: str) -> bool:
    """True when the Typst source carries the live densify knobs."""
    text = typst_text or ""
    return (
        "para-indent = 0.35in" in text
        and "hyphenation: 80%" in text
        and "body-leading-gap = 1.0pt" in text
    )


def validate_header_typst(typst_text: str) -> None:
    if not typst_uses_densify(typst_text):
        raise ValueError("Typst source does not use the live densify compose")
    if "#let format-run-head(" not in typst_text or "query(<run-verse>)" not in typst_text:
        raise ValueError("Typst source does not emit running-header verse ranges")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile John and extract running-header QA leaves. "
            "GRID PROOF — NOT FINAL FACE. Not the loved face."
        )
    )
    parser.add_argument("--usfm", type=Path, default=DEFAULT_USFM)
    parser.add_argument("--source-pdf", type=Path, default=DEFAULT_WORK_PDF)
    parser.add_argument("--typst-out", type=Path, default=DEFAULT_WORK_TYP)
    parser.add_argument("--font-dir", type=Path, default=DEFAULT_GRID_FONT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    parser.add_argument("--no-compile", action="store_true")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)

    if args.no_compile:
        if not args.source_pdf.is_file():
            print(f"Missing header source PDF: {args.source_pdf}", file=sys.stderr)
            return 1
    else:
        if not args.usfm.is_file():
            print(f"Missing USFM archive: {args.usfm}", file=sys.stderr)
            return 1
        code = compile_hotspot_books(
            args.usfm,
            args.source_pdf,
            args.typst_out,
            args.font_dir,
            books=HEADER_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_header_pages(page_texts)
        validate_header_selection(chosen, page_texts)
        if args.typst_out.is_file():
            validate_header_typst(args.typst_out.read_text(encoding="utf-8"))
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no, _ in chosen]
    slugs = [slug for slug, _, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(
        f"Wrote running-header QA PDF: {args.output} "
        f"({len(pages)} leaves; source pages {', '.join(str(page) for page in pages)})"
    )
    print(format_selection(chosen))
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
        for path in prune_header_pngs(args.png_dir, slugs):
            print(f"Removed leftover {path}")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
