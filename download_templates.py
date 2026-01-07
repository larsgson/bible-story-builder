#!/usr/bin/env python3
"""
Download template timing data.

Scans templates, downloads timing data for all languages with timing
for the chapters referenced in templates.
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

TEMPLATE_DIR = Path("templates")


def log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}")


def get_template_ids() -> List[str]:
    if not TEMPLATE_DIR.exists():
        return []
    return sorted([d.name for d in TEMPLATE_DIR.iterdir() if d.is_dir()])


def load_template_refs(template_id: str) -> Dict[str, Set[int]]:
    """Load Bible refs from template .md files, return {BOOK: {chapters}}.

    Supports both flat and hierarchical template structures:
    - Flat: templates/OBS/01.md, templates/OBS/02.md
    - Hierarchical: templates/OBS/01-Beginning/01.md, templates/OBS/02-Patriarchs/04-Abraham/04.md

    Only processes numbered .md files (story content), ignores index.md (navigation).
    """
    path = TEMPLATE_DIR / template_id
    if not path.exists():
        return {}

    pattern = re.compile(r"<<<REF:\s*([A-Z0-9]+)\s+(\d+):[^>]+>>>")
    book_chapters = defaultdict(set)

    # Use recursive glob to find all .md files (supports hierarchical structure)
    for md_file in path.rglob("*.md"):
        # Only process numbered files (story content), skip index.md and other non-story files
        if not md_file.stem.isdigit():
            continue

        try:
            content = md_file.read_text()
            for book, chapter in pattern.findall(content):
                book_chapters[book.upper()].add(int(chapter))
        except Exception as e:
            log(f"Error reading {md_file}: {e}", "WARN")

    return dict(book_chapters)


def download_timing(template_id: str, book_set: str) -> bool:
    """Download timing data using download_language_content.py."""
    cmd = [
        "./venv/bin/python3",
        "download_language_content.py",
        "--book-set",
        book_set,
        "--template",
        template_id,
        "--content-types",
        "timing",
    ]

    log(f"Downloading {book_set} for template {template_id}...")
    try:
        # Stream output instead of capturing to avoid memory issues with large batches
        result = subprocess.run(cmd, timeout=3600)

        if result.returncode != 0:
            log(f"Download failed (exit {result.returncode})", "ERROR")
            return False
        return True
    except subprocess.TimeoutExpired:
        log(f"Download timed out after 3600 seconds", "ERROR")
        return False
    except Exception as e:
        log(f"Download error: {e}", "ERROR")
        return False


def main():
    log("=" * 70)
    log("Template Timing Data Download")
    log("=" * 70)

    templates = get_template_ids()
    if not templates:
        log("No templates found", "ERROR")
        sys.exit(1)

    log(f"Found {len(templates)} template(s): {', '.join(templates)}")

    for template_id in templates:
        log(f"\n{'=' * 70}")
        log(f"Processing template: {template_id}")
        log("=" * 70)

        # Load template refs
        refs = load_template_refs(template_id)
        if not refs:
            log("No refs found, skipping", "WARN")
            continue

        total_chapters = sum(len(chs) for chs in refs.values())
        log(f"Template has {total_chapters} chapters across {len(refs)} books")

        # Download for both NT and OT
        success_count = 0
        for book_set in ["TIMING_NT", "TIMING_OT"]:
            if download_timing(template_id, book_set):
                success_count += 1
            else:
                log(f"Failed to download {book_set}", "ERROR")

        if success_count > 0:
            log(f"\n✓ Downloaded timing data for template {template_id}", "INFO")
        else:
            log(f"\n✗ No timing data downloaded for template {template_id}", "ERROR")

    log("\n" + "=" * 70)
    log("Download complete")
    log("=" * 70)


if __name__ == "__main__":
    main()
