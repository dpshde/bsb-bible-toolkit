#!/usr/bin/env python3
"""Verify generated BSB PDF draft artifacts."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import fitz


EXPECTED_PRIMARY_FONTS = {"Lexend-Bold", "Lexend-Light", "Lexend-Medium", "Lexend-Regular"}
EXPECTED_PRIMARY_COLORS = {0, 526344, 1315860, 5723991}
EXPECTED_PRIMARY_SIZE = 82768562
EXPECTED_PRIMARY_SHA256 = "355ce252702d9be98fea587d52487502f8424b24556e57f41c0b99f8a325c1b2"
EXPECTED_PRIMARY_SEMANTIC_SHA256 = "db33a516822ddfa9a4ac07024379b724396e1ccc5974bc86414d244ebc11b7ea"
EXPECTED_SINGLE_FONTS = {"Lexend-Bold", "Lexend-Light", "Lexend-Medium", "Lexend-Regular"}
EXPECTED_SINGLE_COLORS = {0, 1315860, 1710618}
EXPECTED_SINGLE_SIZE = 28040115
EXPECTED_SINGLE_SHA256 = "449060adedf4a55be72ebdd2b290301ff4a25931e4efb4976af0ab43defaa9f3"
EXPECTED_SINGLE_SEMANTIC_SHA256 = "955de20677f83db66c92e65e8c7a443aad9e05e30338081163a9f73a76e99121"
EXPECTED_SINGLE_LINKS = 84750
EXPECTED_SINGLE_ROUTE_LINKS = 82629


def parse_rect(value: str):
    width, height = value.lower().split("x", 1)
    return float(width), float(height)


def inspect_pdf(path: Path):
    fonts = set()
    colors = set()
    links = 0
    route_links = 0
    with fitz.open(path) as doc:
        pages = len(doc)
        rect = doc[0].rect if pages else None
        for page in doc:
            page_links = page.get_links()
            links += len(page_links)
            route_links += sum(
                1
                for link in page_links
                if str(link.get("uri", "")).startswith("https://route.bible/")
            )
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        if span["text"].strip():
                            fonts.add(span["font"])
                            colors.add(span.get("color"))
    info = {
        "pages": pages,
        "rect": rect,
        "links": links,
        "route_links": route_links,
        "fonts": fonts,
        "colors": colors,
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }
    info["semantic_sha256"] = semantic_sha256(info)
    return info


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_sha256(info: dict):
    payload = {
        "pages": info["pages"],
        "rect": [round(info["rect"].width, 2), round(info["rect"].height, 2)],
        "links": info["links"],
        "route_links": info["route_links"],
        "fonts": sorted(info["fonts"]),
        "colors": sorted(info["colors"]),
        "size": info["size"],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def expect_equal(errors, label, field, actual, expected):
    if actual != expected:
        errors.append(f"{label}: expected {field} {expected!r}, got {actual!r}")


def expect_rect(errors, label, actual, expected):
    width, height = expected
    if actual is None or round(actual.width, 2) != width or round(actual.height, 2) != height:
        errors.append(f"{label}: expected rect {width:g}x{height:g}, got {actual}")


def verify_artifact(
    label,
    path,
    expected_pages,
    expected_rect,
    expected_route_links,
    expected_total_links,
    expected_fonts,
    expected_colors,
    expected_size,
    expected_sha256,
    expected_semantic_sha256,
    strict_fingerprints=False,
):
    if not path.exists():
        return [f"{label}: missing {path}"], None

    info = inspect_pdf(path)
    errors = []
    expect_equal(errors, label, "pages", info["pages"], expected_pages)
    expect_rect(errors, label, info["rect"], expected_rect)
    expect_equal(errors, label, "route links", info["route_links"], expected_route_links)
    expect_equal(errors, label, "total links", info["links"], expected_total_links)
    expect_equal(errors, label, "fonts", info["fonts"], expected_fonts)
    expect_equal(errors, label, "colors", info["colors"], expected_colors)
    expect_equal(errors, label, "size", info["size"], expected_size)
    expect_equal(errors, label, "semantic sha256", info["semantic_sha256"], expected_semantic_sha256)
    if strict_fingerprints:
        expect_equal(errors, label, "sha256", info["sha256"], expected_sha256)
    return errors, info


def print_info(label, path, info):
    print(f"{label}: {path}")
    print(f"  pages: {info['pages']}")
    print(f"  rect: {info['rect']}")
    print(f"  links: {info['links']}")
    print(f"  route_links: {info['route_links']}")
    print(f"  fonts: {', '.join(sorted(info['fonts']))}")
    print(f"  colors: {', '.join(str(color) for color in sorted(info['colors']))}")
    print(f"  size: {info['size']}")
    print(f"  sha256: {info['sha256']}")
    print(f"  semantic_sha256: {info['semantic_sha256']}")


def main():
    parser = argparse.ArgumentParser(description="Verify generated BSB PDF artifacts")
    parser.add_argument("--primary", type=Path, default=Path("drafts/primary/bsb-primary-draft.pdf"))
    parser.add_argument("--single", type=Path, default=Path("drafts/primary/bsb-single-column-draft.pdf"))
    parser.add_argument("--primary-pages", type=int, default=1120)
    parser.add_argument("--primary-rect", type=parse_rect, default=parse_rect("432x648"))
    parser.add_argument("--primary-route-links", type=int, default=4798)
    parser.add_argument("--primary-links", type=int, default=4798)
    parser.add_argument("--single-pages", type=int, default=2251)
    parser.add_argument("--single-rect", type=parse_rect, default=parse_rect("504x756"))
    parser.add_argument("--single-route-links", type=int, default=EXPECTED_SINGLE_ROUTE_LINKS)
    parser.add_argument("--single-links", type=int, default=EXPECTED_SINGLE_LINKS)
    parser.add_argument("--strict-fingerprints", action="store_true", help="Require expected SHA-256 hashes to match")
    args = parser.parse_args()

    checks = [
        (
            "primary",
            args.primary,
            args.primary_pages,
            args.primary_rect,
            args.primary_route_links,
            args.primary_links,
            EXPECTED_PRIMARY_FONTS,
            EXPECTED_PRIMARY_COLORS,
            EXPECTED_PRIMARY_SIZE,
            EXPECTED_PRIMARY_SHA256,
            EXPECTED_PRIMARY_SEMANTIC_SHA256,
        ),
        (
            "single-column",
            args.single,
            args.single_pages,
            args.single_rect,
            args.single_route_links,
            args.single_links,
            EXPECTED_SINGLE_FONTS,
            EXPECTED_SINGLE_COLORS,
            EXPECTED_SINGLE_SIZE,
            EXPECTED_SINGLE_SHA256,
            EXPECTED_SINGLE_SEMANTIC_SHA256,
        ),
    ]

    all_errors = []
    for check in checks:
        errors, info = verify_artifact(*check, strict_fingerprints=args.strict_fingerprints)
        all_errors.extend(errors)
        if info:
            print_info(check[0], check[1], info)

    if all_errors:
        for error in all_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)

    print("Verification passed.")


if __name__ == "__main__":
    main()
