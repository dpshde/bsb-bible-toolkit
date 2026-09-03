#!/usr/bin/env python3
"""Build small facing-spread QA sheets from a travel grid-proof PDF.

Verso (even) sits on the left; recto (odd) on the right. Each source page
keeps its 4.75 × 7 in trim. Spreads are 2-up at 9.5 × 7 in.

Default John pairs: 2–3, 4–5, and the chapter-5 open at 10–11.

This is a metrics/grid-proof helper. It never touches fonts/milo/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import fitz
from PIL import Image

from .generate_travel_pdf import GRID_PROOF_WATERMARK, SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = REPO_ROOT / "drafts" / "travel" / "bsb-travel-john-grid-proof.pdf"
DEFAULT_PDF = REPO_ROOT / "drafts" / "travel" / "bsb-travel-john-spreads-grid-proof.pdf"
DEFAULT_PNG_DIR = REPO_ROOT / "drafts" / "travel" / "spreads"
DEFAULT_PAIRS = ((2, 3), (4, 5), (10, 11))
PNG_DPI = 120
BODY_SIZE_MIN = 8.0
BODY_SIZE_MAX = 9.2
LINE_MATCH_TOLERANCE_PT = 0.75


def parse_pairs(value: str) -> tuple[tuple[int, int], ...]:
    """Parse ``2-3,4-5,10-11`` into 1-based verso/recto pairs."""
    pairs = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "-" not in item:
            raise ValueError(f"pair {item!r} must look like 2-3")
        left, right = item.split("-", 1)
        verso, recto = int(left), int(right)
        if verso < 1 or recto < 1:
            raise ValueError(f"pair {item!r} uses 1-based page numbers")
        if verso % 2 != 0 or recto % 2 != 1 or recto != verso + 1:
            raise ValueError(f"pair {item!r} must be facing verso–recto (even–odd)")
        pairs.append((verso, recto))
    if not pairs:
        raise ValueError("at least one facing pair is required")
    return tuple(pairs)


def pair_slug(verso: int, recto: int) -> str:
    return f"{verso:02d}-{recto:02d}"


def compose_spread_pdf(
    source: Path,
    output: Path,
    pairs: tuple[tuple[int, int], ...] = DEFAULT_PAIRS,
) -> list[tuple[int, int]]:
    """Place each facing pair 2-up: verso left, recto right, native trim."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src:
        page_count = len(src)
        for verso, recto in pairs:
            if verso > page_count or recto > page_count:
                raise ValueError(
                    f"{source} has {page_count} pages; cannot build {verso}–{recto}"
                )
        trim = src[0].rect
        out = fitz.open()
        for verso, recto in pairs:
            spread = out.new_page(width=trim.width * 2, height=trim.height)
            spread.show_pdf_page(fitz.Rect(0, 0, trim.width, trim.height), src, verso - 1)
            spread.show_pdf_page(
                fitz.Rect(trim.width, 0, trim.width * 2, trim.height),
                src,
                recto - 1,
            )
        out.save(output, deflate=True, garbage=4)
        out.close()
    return list(pairs)


def render_spread_pngs(
    spread_pdf: Path,
    png_dir: Path,
    pairs: tuple[tuple[int, int], ...],
    *,
    dpi: int = PNG_DPI,
) -> list[Path]:
    """Rasterize each 2-up page. 120 dpi stays small enough to commit."""
    png_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with fitz.open(spread_pdf) as doc:
        if len(doc) != len(pairs):
            raise ValueError(
                f"{spread_pdf} has {len(doc)} pages but {len(pairs)} pairs were requested"
            )
        for index, (verso, recto) in enumerate(pairs):
            pix = doc[index].get_pixmap(dpi=dpi, alpha=False)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            path = png_dir / f"john-spread-{pair_slug(verso, recto)}.png"
            image.save(path, format="PNG", optimize=True)
            written.append(path)
    return written


def body_baseline_ys(page: fitz.Page) -> list[float]:
    """Bottom of body-size spans — approximate baselines, skip notes/heads/drops."""
    ys = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                size = float(span.get("size") or 0)
                if BODY_SIZE_MIN <= size <= BODY_SIZE_MAX:
                    ys.append(float(span["bbox"][3]))
    return ys


def unique_snapped(ys: list[float], quantum: float = 0.25) -> list[float]:
    return sorted({round(y / quantum) * quantum for y in ys})


def remainder_set(
    ys: list[float],
    baseline_pt: float = SPEC.baseline_pt,
    quantum: float = 0.25,
) -> set[float]:
    return {round((y % baseline_pt) / quantum) * quantum for y in unique_snapped(ys, quantum)}


def line_match_report(
    verso_ys: list[float],
    recto_ys: list[float],
    *,
    baseline_pt: float = SPEC.baseline_pt,
    tolerance_pt: float = LINE_MATCH_TOLERANCE_PT,
) -> dict:
    """Do verso and recto body lines share the same 10.5 pt y lattice?"""
    if not verso_ys or not recto_ys:
        raise ValueError("no body baselines")
    verso_unique = unique_snapped(verso_ys)
    recto_unique = unique_snapped(recto_ys)
    shared = [
        y
        for y in verso_unique
        if any(abs(y - other) <= tolerance_pt for other in recto_unique)
    ]
    verso_rems = remainder_set(verso_ys, baseline_pt)
    recto_rems = remainder_set(recto_ys, baseline_pt)
    rem_overlap = verso_rems & recto_rems
    phase_delta = 0.0
    if verso_rems and recto_rems and not rem_overlap:
        phase_delta = min(abs(v - r) for v in verso_rems for r in recto_rems)
        phase_delta = min(phase_delta, baseline_pt - phase_delta)
    passed = len(shared) >= 8 and (bool(rem_overlap) or phase_delta <= tolerance_pt)
    return {
        "verso_count": len(verso_ys),
        "recto_count": len(recto_ys),
        "verso_unique": len(verso_unique),
        "recto_unique": len(recto_unique),
        "shared_ys": len(shared),
        "phase_delta_pt": round(phase_delta, 3),
        "remainder_overlap": sorted(rem_overlap),
        "pass": passed,
    }


def measure_source_pairs(
    source: Path,
    pairs: tuple[tuple[int, int], ...] = DEFAULT_PAIRS,
) -> list[dict]:
    reports = []
    with fitz.open(source) as doc:
        for verso, recto in pairs:
            report = line_match_report(
                body_baseline_ys(doc[verso - 1]),
                body_baseline_ys(doc[recto - 1]),
            )
            report["pair"] = f"{verso}–{recto}"
            reports.append(report)
    return reports


def format_line_match(reports: list[dict]) -> str:
    lines = ["Facing-page line-match (body 8.5 pt on the 10.5 pt grid):"]
    for report in reports:
        status = "pass" if report["pass"] else "fail"
        lines.append(
            f"  {report['pair']}: {status}; "
            f"{report['shared_ys']} shared body y-slots "
            f"(verso {report['verso_unique']} unique / {report['verso_count']} spans, "
            f"recto {report['recto_unique']} unique / {report['recto_count']} spans); "
            f"phase Δ {report['phase_delta_pt']} pt"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compose 2-up facing spreads from a travel grid-proof PDF "
            "(verso left, recto right). Not the loved face."
        )
    )
    parser.add_argument("input_pdf", type=Path, nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("output_pdf", type=Path, nargs="?", default=DEFAULT_PDF)
    parser.add_argument(
        "--pairs",
        default="2-3,4-5,10-11",
        help="Facing verso-recto pairs (default: 2-3,4-5,10-11)",
    )
    parser.add_argument("--png-dir", type=Path, default=DEFAULT_PNG_DIR)
    parser.add_argument("--dpi", type=int, default=PNG_DPI)
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)

    try:
        pairs = parse_pairs(args.pairs)
    except ValueError as exc:
        parser.error(str(exc))

    if not args.input_pdf.is_file():
        print(f"Missing grid-proof PDF: {args.input_pdf}", file=sys.stderr)
        return 1

    compose_spread_pdf(args.input_pdf, args.output_pdf, pairs)
    print(f"Wrote spread PDF: {args.output_pdf} ({len(pairs)} openings)")
    if not args.no_png:
        pngs = render_spread_pngs(args.output_pdf, args.png_dir, pairs, dpi=args.dpi)
        for path in pngs:
            print(f"Wrote {path} ({path.stat().st_size} bytes)")

    reports = measure_source_pairs(args.input_pdf, pairs)
    print(format_line_match(reports), file=sys.stderr)
    print(GRID_PROOF_WATERMARK, file=sys.stderr)
    return 0 if all(report["pass"] for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
