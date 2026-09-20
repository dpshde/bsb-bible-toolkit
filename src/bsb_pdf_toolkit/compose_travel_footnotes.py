"""Extract a footnotes QA sheet from compiled John (grid proof).

Compiles John on the live travel densify compose, then copies leaves that
exercise SPEC §4 translator notes: alphabetic markers, per-page reset,
run-in grey notes at the foot, in-text body markers, and ``\\fqa`` italic.
Never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .compose_travel_headers import typst_uses_densify
from .compose_travel_hotspots import (
    compile_hotspot_books,
    extract_sampler_pdf,
    load_page_texts,
    render_hotspot_pngs,
)
from .generate_travel_pdf import DEFAULT_GRID_FONT_DIR, DEFAULT_USFM, GRID_PROOF_WATERMARK, SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORK_PDF = REPO_ROOT / "drafts" / "travel" / "work" / "footnotes-john-grid-proof.pdf"
DEFAULT_WORK_TYP = REPO_ROOT / "drafts" / "travel" / "work" / "footnotes-john-grid-proof.typ"
DEFAULT_OUTPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-footnotes-qa-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "footnotes"
PNG_DPI = 120

FOOTNOTE_QA_BOOKS = ("John",)
FOOTNOTE_REQUIRED_SLUGS = ("john-multi", "john-reset")

# A run-in listing starts at the foot with marker ``a`` plus a capital/open-paren.
LISTING_START_RE = re.compile(r"^a\s+[A-Z(]")
# Lone alphabetic tokens in the listing (``a Or … b Greek …``).
MARKER_TOKEN_RE = re.compile(r"(?:(?<=^)|(?<=\s))([a-z])(?=\s)")
# In-text letter after punctuation: ``us.b``, ``side,b``, ``God.a”``.
INLINE_AFTER_PUNCT_RE = re.compile(r"[.,;:!?]([a-z])(?=[\s\"”’')\]]|$)")

# Distinctive John ``\fqa`` glosses that survive PDF extraction.
KNOWN_FQA_PHRASES = (
    "comprehended",
    "tabernacled among us",
    "Unique One",
    "born from above",
    "only begotten",
)


@dataclass(frozen=True)
class FootnoteInfo:
    markers: tuple[str, ...]
    listing: str
    has_fqa: bool
    has_inline: bool
    kind: str

    @property
    def display(self) -> str:
        if not self.markers:
            return "(no notes)"
        if len(self.markers) == 1:
            return self.markers[0]
        return f"{self.markers[0]}–{self.markers[-1]}"


def extract_footnote_listing(text: str) -> str:
    """Return the run-in footnote paragraph from the end of extracted page text."""
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    if lines and lines[-1].isdigit():
        lines = lines[:-1]
    for index in range(len(lines) - 1, -1, -1):
        if LISTING_START_RE.match(lines[index]):
            return " ".join(lines[index:])
    return ""


def listing_markers(listing: str) -> tuple[str, ...]:
    """Alphabetic markers in order from a run-in listing, starting at ``a``."""
    tokens = MARKER_TOKEN_RE.findall(listing or "")
    seq: list[str] = []
    expected = "a"
    for token in tokens:
        if token == expected:
            seq.append(token)
            if token == "z":
                break
            expected = chr(ord(token) + 1)
    return tuple(seq)


def page_footnote_markers(text: str) -> tuple[str, ...]:
    """Letter markers from the page's run-in footnote block."""
    return listing_markers(extract_footnote_listing(text))


def page_has_fqa_reading(
    text: str,
    phrases: tuple[str, ...] = KNOWN_FQA_PHRASES,
) -> bool:
    """True when extracted text carries a known John ``\\fqa`` gloss."""
    listing = extract_footnote_listing(text)
    haystack = listing or (text or "")
    folded = haystack.casefold()
    return any(phrase.casefold() in folded for phrase in phrases)


def page_has_inline_markers(text: str) -> bool:
    """True when a body letter marker sits after punctuation (not the foot listing)."""
    listing = extract_footnote_listing(text)
    body = text or ""
    if listing:
        idx = body.rfind(listing)
        if idx >= 0:
            body = body[:idx]
    return INLINE_AFTER_PUNCT_RE.search(body) is not None


def markers_reset_across_pages(first: str, second: str) -> bool:
    """True when both pages start their listing at ``a`` (per-page reset)."""
    first_marks = page_footnote_markers(first)
    second_marks = page_footnote_markers(second)
    return bool(first_marks and second_marks and first_marks[0] == "a" and second_marks[0] == "a")


def parse_page_footnotes(text: str, kind: str = "") -> FootnoteInfo:
    listing = extract_footnote_listing(text)
    markers = listing_markers(listing)
    return FootnoteInfo(
        markers=markers,
        listing=listing,
        has_fqa=page_has_fqa_reading(text),
        has_inline=page_has_inline_markers(text),
        kind=kind,
    )


def select_footnote_pages(
    page_texts: list[str],
) -> list[tuple[str, int, FootnoteInfo]]:
    """Pick multi-note, page-reset, and optional ``\\fqa`` leaves from John."""
    if not page_texts:
        raise ValueError("source PDF has no pages")
    parsed = [parse_page_footnotes(text) for text in page_texts]
    chosen: dict[str, tuple[int, FootnoteInfo]] = {}
    used: set[int] = set()

    def take(slug: str, predicate) -> None:
        if slug in chosen:
            return
        for index, info in enumerate(parsed, start=1):
            if index in used:
                continue
            if predicate(index, info):
                chosen[slug] = (index, FootnoteInfo(
                    markers=info.markers,
                    listing=info.listing,
                    has_fqa=info.has_fqa,
                    has_inline=info.has_inline,
                    kind=slug.removeprefix("john-"),
                ))
                used.add(index)
                return

    take("john-multi", lambda _page_no, info: len(info.markers) >= 2)
    multi_page = chosen["john-multi"][0] if "john-multi" in chosen else 0
    take(
        "john-reset",
        lambda page_no, info: page_no > multi_page and bool(info.markers) and info.markers[0] == "a",
    )
    take("john-fqa", lambda _page_no, info: info.has_fqa)

    missing = [slug for slug in FOOTNOTE_REQUIRED_SLUGS if slug not in chosen]
    if missing:
        raise ValueError(f"could not find footnote QA leaves: {missing}")
    items = [(slug, page_no, info) for slug, (page_no, info) in chosen.items()]
    items.sort(key=lambda item: item[1])
    return items


def validate_footnote_selection(
    chosen: list[tuple[str, int, FootnoteInfo]],
    page_texts: list[str],
) -> None:
    """Require the SPEC §4 leaf set: multi-note run-in and a later ``a`` reset."""
    slugs = {slug for slug, _, _ in chosen}
    missing = [slug for slug in FOOTNOTE_REQUIRED_SLUGS if slug not in slugs]
    if missing:
        raise ValueError(f"footnote QA missing required leaves: {missing}")
    count = len(page_texts)
    by_slug = {slug: (page_no, info) for slug, page_no, info in chosen}
    for slug, page_no, info in chosen:
        if page_no < 1 or page_no > count:
            raise ValueError(f"John PDF has {count} pages; cannot take {page_no}")
        parsed = parse_page_footnotes(page_texts[page_no - 1], kind=info.kind)
        if parsed.markers != info.markers:
            raise ValueError(f"{slug}: marker mismatch on page {page_no}")
        if slug == "john-multi" and len(parsed.markers) < 2:
            raise ValueError(f"{slug}: need a run-in block with 2+ notes, got {info.display}")
        if slug == "john-reset" and (not parsed.markers or parsed.markers[0] != "a"):
            raise ValueError(f"{slug}: page {page_no} does not restart at a")
        if slug == "john-fqa" and not parsed.has_fqa:
            raise ValueError(f"{slug}: page {page_no} is missing a \\fqa reading")
    multi_page, _ = by_slug["john-multi"]
    reset_page, _ = by_slug["john-reset"]
    if reset_page <= multi_page:
        raise ValueError("john-reset must be a later page than john-multi")
    if not markers_reset_across_pages(page_texts[multi_page - 1], page_texts[reset_page - 1]):
        raise ValueError("selected leaves do not show a per-page marker reset to a")
    if not any(info.has_fqa for _, _, info in chosen):
        raise ValueError("footnote QA leaves are missing a \\fqa italic reading")
    if not any(info.has_inline for _, _, info in chosen):
        raise ValueError("footnote QA leaves are missing in-text letter markers")


def validate_footnote_typst(typst_text: str) -> None:
    """Require densify knobs plus SPEC §4 footnote compose."""
    if not typst_uses_densify(typst_text):
        raise ValueError("Typst source does not use the live densify compose")
    text = typst_text or ""
    if "counter(footnote).update(0)" not in text:
        raise ValueError("Typst source does not reset counter(footnote) per page")
    if '#set footnote(numbering: "a")' not in text:
        raise ValueError("Typst source does not use alphabetic footnote markers")
    fr, fg, fb = SPEC.footnote_ink_rgb
    if f"footnote-ink = rgb({fr}, {fg}, {fb})" not in text:
        raise ValueError("Typst source does not use footnote-ink rgb(76, 76, 76)")
    if ".join([#h(0.7em)])" not in text:
        raise ValueError("Typst source does not run footnotes in as one paragraph")
    if "#footnote[" not in text:
        raise ValueError("Typst source does not emit #footnote from USFM \\f")
    if "#emph[" not in text:
        raise ValueError("Typst source does not italicize \\fqa readings")


def format_selection(chosen: list[tuple[str, int, FootnoteInfo]]) -> str:
    lines = ["Footnote QA leaves (source page → leaf):"]
    for slug, page_no, info in chosen:
        extras = []
        if info.has_fqa:
            extras.append("fqa italic")
        if info.has_inline:
            extras.append("in-text markers")
        extra = f"; {', '.join(extras)}" if extras else ""
        lines.append(
            f"  {slug}: source p.{page_no}  notes {info.display} ({info.kind}{extra})"
        )
    return "\n".join(lines)


def prune_footnote_pngs(png_dir: Path, slugs: list[str]) -> list[Path]:
    """Remove leftover footnote previews that are not in the current leaf set."""
    keep = {f"{slug}.png" for slug in slugs}
    removed: list[Path] = []
    if not png_dir.is_dir():
        return removed
    for path in sorted(png_dir.glob("*.png")):
        if path.name not in keep:
            path.unlink()
            removed.append(path)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compile John and extract footnote QA leaves. "
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
            print(f"Missing footnote source PDF: {args.source_pdf}", file=sys.stderr)
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
            books=FOOTNOTE_QA_BOOKS,
        )
        if code != 0:
            return code

    try:
        page_texts = load_page_texts(args.source_pdf)
        chosen = select_footnote_pages(page_texts)
        validate_footnote_selection(chosen, page_texts)
        if args.typst_out.is_file():
            validate_footnote_typst(args.typst_out.read_text(encoding="utf-8"))
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    pages = [page_no for _, page_no, _ in chosen]
    slugs = [slug for slug, _, _ in chosen]
    extract_sampler_pdf(args.source_pdf, args.output, pages)
    print(
        f"Wrote footnote QA PDF: {args.output} "
        f"({len(pages)} leaves; source pages {', '.join(str(page) for page in pages)})"
    )
    print(format_selection(chosen))
    if not args.no_png:
        pngs = render_hotspot_pngs(args.output, args.png_dir, slugs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")
        for path in prune_footnote_pngs(args.png_dir, slugs):
            print(f"Removed leftover {path}")
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
