#!/usr/bin/env python3
"""
Customize a BSB EPUB: change fonts, optionally add route.bible links to headings.

This script extracts the EPUB, modifies CSS to use Lexend fonts, embeds the
font files, and re-packages the EPUB. Because EPUB is HTML-based, text reflows
naturally when the font changes — no layout breakage.

Usage:
    python customize_epub.py bsb.epub bsb-custom.epub --font-dir fonts/
    python customize_epub.py bsb.epub bsb-custom.epub --font-dir fonts/ --add-links
"""

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
import re

# OSIS book mapping for link generation
OSIS_BOOKS = {
    "Genesis": "Gen", "Exodus": "Exod", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deut", "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth",
    "1 Samuel": "1Sam", "2 Samuel": "2Sam", "1 Kings": "1Kgs", "2 Kings": "2Kgs",
    "1 Chronicles": "1Chr", "2 Chronicles": "2Chr", "Ezra": "Ezra", "Nehemiah": "Neh",
    "Esther": "Esth", "Job": "Job", "Psalms": "Ps", "Proverbs": "Prov",
    "Ecclesiastes": "Eccl", "Song of Solomon": "Song", "Isaiah": "Isa", "Jeremiah": "Jer",
    "Lamentations": "Lam", "Ezekiel": "Ezek", "Daniel": "Dan", "Hosea": "Hos",
    "Joel": "Joel", "Amos": "Amos", "Obadiah": "Obad", "Jonah": "Jonah",
    "Micah": "Mic", "Nahum": "Nah", "Habakkuk": "Hab", "Zephaniah": "Zeph",
    "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal", "Matthew": "Matt",
    "Mark": "Mark", "Luke": "Luke", "John": "John", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1Cor", "2 Corinthians": "2Cor", "Galatians": "Gal",
    "Ephesians": "Eph", "Philippians": "Phil", "Colossians": "Col", "1 Thessalonians": "1Thess",
    "2 Thessalonians": "2Thess", "1 Timothy": "1Tim", "2 Timothy": "2Tim", "Titus": "Titus",
    "Philemon": "Phlm", "Hebrews": "Heb", "James": "Jas", "1 Peter": "1Pet",
    "2 Peter": "2Pet", "1 John": "1John", "2 John": "2John", "3 John": "3John",
    "Jude": "Jude", "Revelation": "Rev",
}


def extract_epub(epub_path: Path, work_dir: Path):
    """Extract EPUB to working directory."""
    work_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(epub_path, "r") as zf:
        zf.extractall(work_dir)
    return work_dir


def find_css_files(work_dir: Path):
    """Find all CSS files in the EPUB."""
    return list(work_dir.rglob("*.css"))


def find_html_files(work_dir: Path):
    """Find all HTML/XHTML files in the EPUB."""
    return list(work_dir.rglob("*.htm")) + list(work_dir.rglob("*.html")) + list(work_dir.rglob("*.xhtml"))


def find_content_opf(work_dir: Path):
    """Find the content.opf file."""
    candidates = list(work_dir.rglob("content.opf"))
    if candidates:
        return candidates[0]
    # Fallback: look for any .opf file
    candidates = list(work_dir.rglob("*.opf"))
    if candidates:
        return candidates[0]
    return None


def add_fonts_to_epub(work_dir: Path, font_dir: Path, content_opf: Path):
    """Copy font files into EPUB and register them in content.opf."""
    # Find the OEBPS/Text directory or create a fonts directory
    text_dirs = list(work_dir.rglob("OEBPS/Text"))
    if text_dirs:
        base_dir = text_dirs[0].parent
    else:
        # Fallback: find where HTML files are
        html_files = find_html_files(work_dir)
        if html_files:
            base_dir = html_files[0].parent
        else:
            base_dir = work_dir
    
    fonts_dir = base_dir / "Fonts"
    fonts_dir.mkdir(exist_ok=True)
    
    # Copy font files
    font_files = list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf"))
    copied = []
    for font_file in font_files:
        dest = fonts_dir / font_file.name
        shutil.copy2(font_file, dest)
        copied.append(dest)
    
    # Update content.opf manifest
    if content_opf and content_opf.exists():
        opf_text = content_opf.read_text(encoding="utf-8")
        
        # Find the manifest section
        manifest_match = re.search(r"(<manifest>.*?</manifest>)", opf_text, re.DOTALL)
        if manifest_match:
            manifest = manifest_match.group(1)
            # Add font items
            font_items = []
            for font_file in copied:
                # Get relative path from content.opf
                try:
                    rel_path = font_file.relative_to(content_opf.parent)
                except ValueError:
                    rel_path = font_file.name
                rel_path_str = str(rel_path).replace("\\", "/")
                font_id = f"font-{font_file.stem}"
                item = f'    <item id="{font_id}" href="{rel_path_str}" media-type="application/x-font-ttf"/>'
                if font_id not in opf_text:
                    font_items.append(item)
            
            if font_items:
                # Insert before </manifest>
                new_manifest = manifest.replace("</manifest>", "\n".join(font_items) + "\n  </manifest>")
                opf_text = opf_text.replace(manifest, new_manifest)
                content_opf.write_text(opf_text, encoding="utf-8")
                print(f"Added {len(font_items)} fonts to content.opf")
    
    return copied


def get_css_font_path(fonts_dir: Path, css_file: Path):
    """Get the relative path from a CSS file to the fonts directory."""
    try:
        rel = fonts_dir.relative_to(css_file.parent)
        return str(rel).replace("\\", "/") + "/"
    except ValueError:
        # fonts_dir is not under css_file.parent
        # Try to find relative path from CSS to fonts
        # Use a common ancestor approach
        css_parts = list(css_file.parent.parts)
        fonts_parts = list(fonts_dir.parts)
        
        # Find common prefix
        common_len = 0
        for i, (c, f) in enumerate(zip(css_parts, fonts_parts)):
            if c == f:
                common_len = i + 1
            else:
                break
        
        up_levels = len(css_parts) - common_len
        down_path = "/".join(fonts_parts[common_len:])
        
        prefix = "../" * up_levels if up_levels else "./"
        return prefix + down_path + "/" if down_path else prefix


def modify_css(css_files: list, work_dir: Path, font_dir: Path):
    """Modify CSS files to use Lexend fonts."""
    # Find the fonts directory
    fonts_dirs = list(work_dir.rglob("Fonts"))
    fonts_dir = fonts_dirs[0] if fonts_dirs else None
    
    for css_file in css_files:
        css_text = css_file.read_text(encoding="utf-8")
        
        # Add @font-face declarations at the top
        font_faces = []
        font_files = list(font_dir.glob("*.ttf")) + list(font_dir.glob("*.otf")) if fonts_dir else []
        
        if fonts_dir:
            font_path_prefix = get_css_font_path(fonts_dir, css_file)
            
            for font_file in font_files:
                font_name = font_file.stem
                font_faces.append(
                    f"""@font-face {{
    font-family: "Lexend";
    src: url("{font_path_prefix}{font_file.name}");
    font-weight: {font_weight_from_name(font_name)};
    font-style: normal;
}}
"""
                )
        
        # Modify existing font-family declarations
        # Replace common font families with Lexend
        css_text = re.sub(
            r'font-family:\s*[^;]*(?:Cambria|Verdana|Arial|Helvetica|Tahoma)[^;]*;',
            'font-family: "Lexend", sans-serif;',
            css_text,
            flags=re.IGNORECASE,
        )
        
        # Also replace generic sans-serif and serif references that point to the old fonts
        css_text = re.sub(
            r'font-family:\s*"[^"]*"\s*,\s*sans-serif;',
            'font-family: "Lexend", sans-serif;',
            css_text,
        )
        
        # Add font-face declarations at the top
        if font_faces:
            css_text = "\n".join(font_faces) + "\n" + css_text
        
        css_file.write_text(css_text, encoding="utf-8")
        print(f"Updated CSS: {css_file}")


def font_weight_from_name(font_name: str) -> str:
    """Map font filename to CSS font-weight."""
    name_lower = font_name.lower()
    if "thin" in name_lower:
        return "100"
    elif "light" in name_lower:
        return "300"
    elif "regular" in name_lower:
        return "400"
    elif "medium" in name_lower:
        return "500"
    elif "semibold" in name_lower:
        return "600"
    elif "bold" in name_lower:
        return "700"
    elif "extrabold" in name_lower or "extra-bold" in name_lower:
        return "800"
    elif "black" in name_lower:
        return "900"
    return "400"


def add_links_to_html(html_files: list, work_dir: Path):
    """Add route.bible links to section headings in HTML files."""
    # Track current book/chapter for link generation
    current_book = None
    current_chapter = None
    
    for html_file in sorted(html_files):
        text = html_file.read_text(encoding="utf-8")
        
        # Try to identify book/chapter from title
        title_match = re.search(r'<title>([^<]*)</title>', text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).strip()
            # Parse title like "Numbers 7 BSB" or "Genesis 1 BSB"
            parts = title.replace("BSB", "").strip().rsplit(" ", 1)
            if len(parts) == 2:
                try:
                    chapter = int(parts[1])
                    book_name = parts[0]
                    current_book = OSIS_BOOKS.get(book_name, book_name)
                    current_chapter = chapter
                except ValueError:
                    pass
        
        # Find headings and add links
        if current_book and current_chapter:
            # Match <p class="hdg">...</p> or similar heading classes
            def replace_heading(match):
                heading_text = match.group(1)
                # Create a simple chapter-level link
                osis_ref = f"{current_book}.{current_chapter}"
                url = f"https://route.bible/{osis_ref}"
                return f'<p class="hdg"><a href="{url}">{heading_text}</a></p>'
            
            text = re.sub(
                r'<p class="hdg">([^<]+)</p>',
                replace_heading,
                text,
                flags=re.IGNORECASE,
            )
        
        html_file.write_text(text, encoding="utf-8")


def repackage_epub(work_dir: Path, output_path: Path):
    """Re-package the modified files into an EPUB."""
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write mimetype first (uncompressed, as per EPUB spec)
        mimetype_path = work_dir / "mimetype"
        if mimetype_path.exists():
            zf.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        
        # Write all other files
        for file_path in work_dir.rglob("*"):
            if file_path.is_file() and file_path.name != "mimetype":
                arcname = file_path.relative_to(work_dir)
                zf.write(file_path, arcname)
    
    print(f"Re-packaged EPUB: {output_path}")


def customize_epub(
    input_path: Path,
    output_path: Path,
    font_dir: Path,
    add_links: bool = False,
):
    """Main EPUB customization workflow."""
    work_dir = Path("/tmp/epub_work")
    
    # Clean up previous work
    if work_dir.exists():
        shutil.rmtree(work_dir)
    
    print(f"Extracting {input_path}...")
    extract_epub(input_path, work_dir)
    
    # Find key files
    css_files = find_css_files(work_dir)
    html_files = find_html_files(work_dir)
    content_opf = find_content_opf(work_dir)
    
    print(f"Found {len(css_files)} CSS files, {len(html_files)} HTML files")
    
    # Add fonts to EPUB
    print("Adding fonts to EPUB...")
    add_fonts_to_epub(work_dir, font_dir, content_opf)
    
    # Modify CSS
    print("Modifying CSS...")
    modify_css(css_files, work_dir, font_dir)
    
    # Optionally add links
    if add_links:
        print("Adding route.bible links...")
        add_links_to_html(html_files, work_dir)
    
    # Re-package
    print("Re-packaging...")
    repackage_epub(work_dir, output_path)
    
    # Clean up
    shutil.rmtree(work_dir)
    
    print(f"Done. Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Customize BSB EPUB with Lexend fonts")
    parser.add_argument("input", type=Path, help="Input EPUB file")
    parser.add_argument("output", type=Path, help="Output EPUB file")
    parser.add_argument("--font-dir", type=Path, default=Path("fonts"), help="Directory containing font files")
    parser.add_argument("--add-links", action="store_true", help="Add route.bible links to headings")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    if not args.font_dir.exists():
        print(f"Error: font directory not found: {args.font_dir}", file=sys.stderr)
        sys.exit(1)

    customize_epub(
        input_path=args.input,
        output_path=args.output,
        font_dir=args.font_dir,
        add_links=args.add_links,
    )


if __name__ == "__main__":
    main()
