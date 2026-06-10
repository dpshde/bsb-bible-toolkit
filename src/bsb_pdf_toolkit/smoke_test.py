#!/usr/bin/env python3
"""
Smoke-test sampler: stitch a small preview PDF from the first N pages
plus a handful of randomly sampled pages elsewhere in the document.
Useful for quickly eyeballing layout changes without opening a 2000-page PDF.
"""

import argparse
import random
from pathlib import Path

import fitz


DEFAULT_SINGLE = Path("drafts/primary/bsb-single-column-draft.pdf")
DEFAULT_PRIMARY = Path("drafts/primary/bsb-primary-draft.pdf")
DEFAULT_OUTPUT = Path("drafts/primary/work/smoke-test.pdf")


def sample_pages(total: int, head: int, sample: int, seed: int) -> list[int]:
    """Return 0-based page indices: first `head` pages + `sample` random others."""
    head = min(head, total)
    head_indices = list(range(head))
    rest = list(range(head, total))
    rng = random.Random(seed)
    sampled = sorted(rng.sample(rest, min(sample, len(rest))))
    return head_indices + sampled


def build_smoke_pdf(
    source: Path,
    output: Path,
    head: int,
    sample: int,
    seed: int,
) -> list[int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    with fitz.open(source) as src:
        total = len(src)
        indices = sample_pages(total, head, sample, seed)
        out = fitz.open()
        for i in indices:
            out.insert_pdf(src, from_page=i, to_page=i)
        out.save(output)
        out.close()
    return [i + 1 for i in indices]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a small smoke-test PDF from sampled pages of a draft"
    )
    parser.add_argument(
        "--pdf",
        type=Path,
        default=DEFAULT_SINGLE,
        help="Source PDF to sample (default: single-column draft)",
    )
    parser.add_argument(
        "--primary",
        action="store_true",
        help="Sample from the primary fixed-layout draft instead",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output path for the smoke-test PDF",
    )
    parser.add_argument(
        "--head",
        type=int,
        default=5,
        metavar="N",
        help="Number of pages to take from the start (default: 5)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=8,
        metavar="N",
        help="Number of random pages to sample from the remainder (default: 8)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    args = parser.parse_args()

    source = DEFAULT_PRIMARY if args.primary else args.pdf

    if not source.exists():
        raise SystemExit(f"Source PDF not found: {source}")

    pages = build_smoke_pdf(source, args.output, args.head, args.sample, args.seed)
    print(f"Sampled {len(pages)} pages from {source}: {pages}")
    print(f"Wrote: {args.output}")


if __name__ == "__main__":
    main()
