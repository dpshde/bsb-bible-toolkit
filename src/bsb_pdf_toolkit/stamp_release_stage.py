"""Stamp draft or release status labels onto generated BSB PDFs."""

import argparse
from pathlib import Path

import fitz


def stamp_label(
    pdf_path: Path,
    font_dir: Path,
    old_labels: list[str],
    new_label: str,
    font_size: float,
    fallback_baseline: float,
) -> None:
    doc = fitz.open(pdf_path)
    page = doc[0]
    rects = []
    for old_label in old_labels:
        rects = page.search_for(old_label)
        if rects:
            break

    if rects:
        rect = rects[0] + (-3, -2, 3, 3)
        baseline = rect.y1 - 3
    else:
        text_width = 220
        center_x = page.rect.width / 2
        rect = fitz.Rect(center_x - text_width / 2, fallback_baseline - font_size - 3, center_x + text_width / 2, fallback_baseline + 4)
        baseline = fallback_baseline

    page.add_redact_annot(rect, fill=(1, 1, 1))
    page.apply_redactions()

    font_path = font_dir / "Lexend-Bold.ttf"
    font_name = "LexendBoldReleaseStage"
    page.insert_font(fontname=font_name, fontfile=str(font_path))
    font = fitz.Font(fontfile=str(font_path))
    text_width = font.text_length(new_label, fontsize=font_size)
    x = (page.rect.width - text_width) / 2
    page.insert_text((x, baseline), new_label, fontsize=font_size, fontname=font_name, color=(0.08, 0.08, 0.08))
    doc.saveIncr()
    doc.close()


def stamp_primary(pdf_path: Path, font_dir: Path, release_stage: str) -> None:
    stamp_label(
        pdf_path,
        font_dir,
        ["Primary Fixed-Layout Draft", "Primary Layout Draft", "Primary Layout Version"],
        f"Primary Layout {release_stage}",
        11,
        388,
    )


def stamp_single_column(pdf_path: Path, font_dir: Path, release_stage: str) -> None:
    stamp_label(
        pdf_path,
        font_dir,
        ["Single-Column Draft", "Single Column Draft", "Single Column Version"],
        f"Single Column {release_stage}",
        12,
        349,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Stamp release-stage labels onto BSB PDF title pages")
    parser.add_argument("--primary", type=Path)
    parser.add_argument("--single-column", type=Path)
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"))
    parser.add_argument("--release-stage", default="Version")
    args = parser.parse_args()

    if not args.primary and not args.single_column:
        parser.error("at least one of --primary or --single-column is required")

    if args.primary:
        stamp_primary(args.primary, args.font_dir, args.release_stage)
    if args.single_column:
        stamp_single_column(args.single_column, args.font_dir, args.release_stage)


if __name__ == "__main__":
    main()
