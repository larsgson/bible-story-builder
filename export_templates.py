#!/usr/bin/env python3
"""
Export template timing data in two steps.

Step 1: Export to workspace organized by language (process each language once)
  workspace/templates/{template_id}/{canon}/{category}/{language}/timing.json

Step 2: Copy to export organized by region (handle multi-region languages)
  export/templates/{template_id}/{canon}/{category}/{region}/{language}/timing.json
"""

import json
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

TEMPLATE_DIR = Path("templates")
WORKSPACE_DIR = Path("workspace/templates")
EXPORT_TEMPLATES_DIR = Path("export/templates")
DOWNLOADS_DIR = Path("downloads/BB")
REGIONS_CONFIG = Path("config/regions.conf")
LOG_DIR = Path("export_log")


def log(msg: str, level: str = "INFO"):
    print(f"[{level}] {msg}")


def load_regions_config() -> Tuple[Dict[str, str], Dict[str, List[str]]]:
    """
    Load region mapping from config.
    Returns:
        - iso_to_regions: {iso: [region_names]} (languages can be in multiple regions)
        - region_to_isos: {region_name: [isos]}
    """
    if not REGIONS_CONFIG.exists():
        log(f"Regions config not found: {REGIONS_CONFIG}", "ERROR")
        return {}, {}

    iso_to_regions = defaultdict(list)
    region_to_isos = defaultdict(list)
    current_region = None

    for line in REGIONS_CONFIG.read_text().splitlines():
        line = line.strip()

        # Skip comments and blank lines
        if not line or line.startswith("#"):
            continue

        # Check if line contains language codes (has comma or 3-letter codes)
        if "," in line or (len(line) == 3 and line.isalpha()):
            if current_region:
                # Parse language codes
                codes = [c.strip() for c in line.replace(",", " ").split()]
                for code in codes:
                    if len(code) == 3 and code.isalpha():
                        iso_to_regions[code].append(current_region)
                        region_to_isos[current_region].append(code)
        elif line.startswith("@"):
            # Skip metadata lines
            continue
        else:
            # This is a region name
            current_region = line

    return dict(iso_to_regions), dict(region_to_isos)


def get_template_ids() -> List[str]:
    if not TEMPLATE_DIR.exists():
        return []
    return sorted([d.name for d in TEMPLATE_DIR.iterdir() if d.is_dir()])


def load_template_refs(template_id: str) -> Dict[str, Dict[str, List[Tuple[int, str]]]]:
    """
    Load Bible refs from template .md files.
    Returns {story_number: {BOOK: [(chapter, verses)]}}

    Splits comma-separated references into individual entries.
    Example: "GEN 1:1,5-7" becomes two entries: (1, "1") and (1, "5-7")
    Example: "GEN 6:21, GEN 7:1,7" becomes (6, "21"), (7, "1"), (7, "7")
    """
    path = TEMPLATE_DIR / template_id
    if not path.exists():
        return {}

    # Match full reference including potential comma-separated parts
    pattern = re.compile(r"<<<REF:\s*([^>]+)>>>")
    story_refs = defaultdict(lambda: defaultdict(list))

    for md_file in sorted(path.glob("*.md")):
        # Extract story number from filename (e.g., "01.md" -> "01")
        story_num = md_file.stem
        if not story_num.isdigit():
            continue

        try:
            content = md_file.read_text()
            for ref_content in pattern.findall(content):
                # Split by comma to handle multiple references
                comma_parts = [part.strip() for part in ref_content.split(",")]

                current_book = None
                for part in comma_parts:
                    # Check if this part has a book code
                    book_match = re.match(r"([A-Z0-9]+)\s+(\d+):(.+)", part)
                    if book_match:
                        # Full reference with book
                        current_book = book_match.group(1).upper()
                        chapter = int(book_match.group(2))
                        verses = book_match.group(3).strip()
                    else:
                        # Just chapter:verses, use current book
                        chapter_match = re.match(r"(\d+):(.+)", part)
                        if chapter_match and current_book:
                            chapter = int(chapter_match.group(1))
                            verses = chapter_match.group(2).strip()
                        else:
                            # Just verses, assume same chapter as before
                            # This shouldn't happen with proper template format
                            continue

                    story_refs[story_num][current_book].append((chapter, verses))

        except Exception as e:
            log(f"Error reading {md_file}: {e}", "WARN")

    return dict(story_refs)


def find_timing_files() -> List[Path]:
    """Find all *_timing.json files in downloads."""
    if not DOWNLOADS_DIR.exists():
        return []
    return list(DOWNLOADS_DIR.glob("**/*_timing.json"))


def parse_timing_path(p: Path) -> Optional[Dict]:
    """Extract metadata from timing file path."""
    try:
        parts = p.parts
        idx = parts.index("BB")
        # Parse filename: BOOK_CHAPTER_FILESET_timing.json
        name = p.stem.replace("_timing", "")
        book, chapter, fileset = name.split("_", 2)

        return {
            "path": p,
            "canon": parts[idx + 1],
            "category": parts[idx + 2],
            "iso": parts[idx + 3],
            "distinct_id": parts[idx + 4],
            "book": book,
            "chapter": int(chapter),
            "fileset": fileset,
        }
    except:
        return None


def load_timing_file(path: Path) -> List[Dict]:
    """Load timing data from JSON file."""
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except Exception as e:
        log(f"Error loading {path}: {e}", "ERROR")
        return []


def extract_verse_timestamps(
    timing_data: List[Dict], verse_range: str
) -> Tuple[Optional[List[float]], List[int], Optional[str]]:
    """
    Extract timestamps for a verse range from timing data.
    Uses graceful degradation: repeats timestamps for missing verses.
    Uses smart approximation: if no verses in range but verses exist before AND after,
    use boundary verses as approximation.

    Args:
        timing_data: List of timing entries with verse_start and timestamp
        verse_range: e.g., "1", "1-2", "3-5" (NO commas - already split)

    Returns:
        Tuple of (timestamps, missing_verses, approximation_details):
        - timestamps: List with N+1 timestamps for N verses (or None if complete failure)
        - missing_verses: List of verse numbers that were missing
        - approximation_details: String describing approximation used, or None
    """
    try:
        # Build verse -> timestamp mapping
        verse_times = {}
        for entry in timing_data:
            verse = int(entry.get("verse_start", 0))
            timestamp = float(entry.get("timestamp", 0))
            verse_times[verse] = timestamp

        # Parse verse range (single verse or range with dash)
        verses_to_extract = []

        if "-" in verse_range:
            # Range like "1-2" or "5-7"
            start_v, end_v = verse_range.split("-")
            start_verse = int(start_v)
            end_verse = int(end_v)
            verses_to_extract.extend(range(start_verse, end_verse + 1))
        else:
            # Single verse like "1" or "20"
            verses_to_extract.append(int(verse_range))

        # Check if ANY verses exist in range
        available_verses = [v for v in verses_to_extract if v in verse_times]

        if not available_verses:
            # No verses in range - try smart approximation
            all_available = sorted(verse_times.keys())
            if not all_available:
                return None, verses_to_extract, None  # ERROR: no data at all

            min_requested = min(verses_to_extract)
            max_requested = max(verses_to_extract)

            # Find verses before and after the range
            before = [v for v in all_available if v < min_requested]
            after = [v for v in all_available if v > max_requested]

            # Approximate based on what's available
            if before and after:
                use_before = max(before)
                use_after = min(after)
                # Use before timestamp for all requested verses, after for boundary
                timestamps = [verse_times[use_before]] * len(verses_to_extract) + [
                    verse_times[use_after]
                ]
                approximation = f"using verses {use_before} and {use_after} as boundary approximation"
                return timestamps, verses_to_extract, approximation
            elif before:
                # Only verses before - repeat last available verse timestamp
                use_before = max(before)
                # Repeat the last available timestamp for all requested verses and boundary
                timestamps = [verse_times[use_before]] * (len(verses_to_extract) + 1)
                approximation = (
                    f"no verses after range, repeating verse {use_before} timestamp"
                )
                return timestamps, verses_to_extract, approximation
            elif after:
                # Only verses after - use timestamp 0 for start, first after verse for end
                use_after = min(after)
                # Use 0.0 for all requested verses, first after verse for boundary
                timestamps = [0.0] * len(verses_to_extract) + [verse_times[use_after]]
                approximation = (
                    f"no verses before range, using timestamp 0 and verse {use_after}"
                )
                return timestamps, verses_to_extract, approximation
            else:
                # Cannot approximate - no verses at all (shouldn't happen, checked earlier)
                return None, verses_to_extract, None  # ERROR

        # Build timestamp array with graceful degradation
        timestamps = []
        missing_verses = []
        last_available_ts = None

        for verse in verses_to_extract:
            if verse in verse_times:
                ts = verse_times[verse]
                timestamps.append(ts)
                last_available_ts = ts
            else:
                # Missing verse - repeat last available timestamp
                if last_available_ts is not None:
                    timestamps.append(last_available_ts)
                    missing_verses.append(verse)
                else:
                    # No previous timestamp available yet
                    missing_verses.append(verse)

        # Add final boundary (end of last verse)
        last_verse = verses_to_extract[-1]
        if last_verse + 1 in verse_times:
            timestamps.append(verse_times[last_verse + 1])
        elif last_available_ts is not None:
            # Repeat last available timestamp as end boundary
            timestamps.append(last_available_ts)

        return timestamps, missing_verses, None
    except Exception as e:
        return None, [], None


class ExportLogger:
    def __init__(self):
        self.logs = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    def add(
        self,
        category: str,
        iso: str,
        distinct_id: str,
        fileset: str,
        ref_key: str,
        details: str,
    ):
        """
        Add a log entry organized by category/language/fileset.

        Args:
            category: "error" or "warning"
            iso: Language code
            distinct_id: Bible version ID
            fileset: Fileset ID
            ref_key: Reference key (e.g., "GEN1:14-18")
            details: Error/warning details
        """
        self.logs[category][iso][f"{distinct_id}/{fileset}"].append(
            {"ref": ref_key, "details": details}
        )

    def save(self, template_id: str):
        if not self.logs:
            return

        LOG_DIR.mkdir(exist_ok=True)
        log_file = LOG_DIR / f"export_{template_id}.json"

        # Build structured output
        output = {
            "template_id": template_id,
            "summary": {
                "total_errors": sum(
                    len(refs)
                    for lang_data in self.logs.get("error", {}).values()
                    for refs in lang_data.values()
                ),
                "total_warnings": sum(
                    len(refs)
                    for lang_data in self.logs.get("warning", {}).values()
                    for refs in lang_data.values()
                ),
                "languages_with_errors": len(self.logs.get("error", {})),
                "languages_with_warnings": len(self.logs.get("warning", {})),
            },
            "errors": {},
            "warnings": {},
        }

        # Organize errors by language
        for iso in sorted(self.logs.get("error", {}).keys()):
            output["errors"][iso] = {}
            for fileset_key in sorted(self.logs["error"][iso].keys()):
                output["errors"][iso][fileset_key] = self.logs["error"][iso][
                    fileset_key
                ]

        # Organize warnings by language
        for iso in sorted(self.logs.get("warning", {}).keys()):
            output["warnings"][iso] = {}
            for fileset_key in sorted(self.logs["warning"][iso].keys()):
                output["warnings"][iso][fileset_key] = self.logs["warning"][iso][
                    fileset_key
                ]

        with open(log_file, "w") as f:
            json.dump(output, f, indent=2, sort_keys=False)

        log(f"Export log saved: {log_file}", "INFO")


def export_to_workspace(template_id: str) -> Tuple[bool, ExportLogger]:
    """
    Step 1: Export timing data to workspace organized by language.
    Returns (success, logger)
    """
    log(f"\n{'=' * 70}")
    log(f"Step 1: Export to workspace for template: {template_id}")
    log("=" * 70)

    # Load template references
    story_refs = load_template_refs(template_id)
    if not story_refs:
        log("No story references found", "WARN")
        return False, ExportLogger()

    total_stories = len(story_refs)
    total_refs = sum(len(books) for books in story_refs.values())
    log(f"Template has {total_stories} stories with {total_refs} book references")

    # Initialize export logger
    export_log = ExportLogger()

    # Find all timing files
    timing_files = find_timing_files()
    log(f"Found {len(timing_files)} timing files in downloads")

    # Group timing files by metadata
    timing_by_key = {}
    for timing_file in timing_files:
        meta = parse_timing_path(timing_file)
        if not meta:
            continue

        key = (
            meta["canon"],
            meta["category"],
            meta["iso"],
            meta["distinct_id"],
            meta["book"],
            meta["chapter"],
            meta["fileset"],
        )
        timing_by_key[key] = meta

    # Build workspace structure: {canon: {category: {language: {distinct_id: {fileset: {story: {ref: timing_info}}}}}}}
    # timing_info contains: timestamps, missing_verses, approximation
    workspace_data = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
            )
        )
    )

    # Track warnings separately: {canon: {category: {iso: {distinct_id: {fileset: {story: {ref: warning_info}}}}}}}
    workspace_warnings = defaultdict(
        lambda: defaultdict(
            lambda: defaultdict(
                lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
            )
        )
    )

    processed_count = 0
    missing_count = 0

    # Process each story
    for story_num in sorted(story_refs.keys()):
        books = story_refs[story_num]

        for book, chapter_verse_list in books.items():
            for chapter, verses in chapter_verse_list:
                ref_key = f"{book}{chapter}:{verses}"

                # Find all languages that have this chapter
                for key, meta in timing_by_key.items():
                    (
                        canon,
                        category,
                        iso,
                        distinct_id,
                        file_book,
                        file_chapter,
                        fileset,
                    ) = key

                    if file_book != book or file_chapter != chapter:
                        continue

                    # Load timing data
                    timing_data = load_timing_file(meta["path"])
                    if not timing_data:
                        export_log.add(
                            "Failed to Load Timing",
                            f"{iso}/{distinct_id}/{fileset} {ref_key}",
                        )
                        missing_count += 1
                        continue

                    # Extract verse timestamps with graceful degradation
                    timestamps, missing_verses, approximation = (
                        extract_verse_timestamps(timing_data, verses)
                    )
                    if timestamps is None:
                        # Complete failure - no verses available in range
                        export_log.add(
                            "error",
                            iso,
                            distinct_id,
                            fileset,
                            ref_key,
                            "no verses available in range",
                        )
                        missing_count += 1
                        continue
                    elif approximation:
                        # Smart approximation used - verses before and after (WARNING)
                        export_log.add(
                            "warning",
                            iso,
                            distinct_id,
                            fileset,
                            ref_key,
                            f"no verses in range, {approximation}",
                        )
                        # Export with approximation warning
                    elif missing_verses:
                        # Partial data - some verses missing (WARNING)
                        missing_str = ",".join(map(str, missing_verses))
                        export_log.add(
                            "warning",
                            iso,
                            distinct_id,
                            fileset,
                            ref_key,
                            f"missing verses: {missing_str}, timestamps repeated",
                        )
                        # Still export with warning

                    # Add to workspace structure
                    story_int = int(story_num)
                    if (
                        story_int
                        not in workspace_data[canon][category][iso][distinct_id][
                            fileset
                        ]
                    ):
                        workspace_data[canon][category][iso][distinct_id][fileset][
                            story_int
                        ] = {}

                    # Store timing data
                    workspace_data[canon][category][iso][distinct_id][fileset][
                        story_int
                    ][ref_key] = timestamps

                    # Store warning if there are issues
                    if approximation or missing_verses:
                        if (
                            story_int
                            not in workspace_warnings[canon][category][iso][
                                distinct_id
                            ][fileset]
                        ):
                            workspace_warnings[canon][category][iso][distinct_id][
                                fileset
                            ][story_int] = {}

                        warning_entry = {}

                        if approximation:
                            warning_entry["type"] = "approximated"
                            warning_entry["details"] = approximation

                            # Parse approximation to extract used verses
                            if "verses" in approximation and "and" in approximation:
                                # Pattern: "using verses X and Y as boundary approximation"
                                import re

                                match = re.search(
                                    r"verses\s+(\d+)\s+and\s+(\d+)", approximation
                                )
                                if match:
                                    warning_entry["used_verses"] = [
                                        int(match.group(1)),
                                        int(match.group(2)),
                                    ]
                                    warning_entry["method"] = "boundary_verses"
                            elif "repeating verse" in approximation:
                                # Pattern: "no verses after range, repeating verse X timestamp"
                                import re

                                match = re.search(
                                    r"repeating verse\s+(\d+)", approximation
                                )
                                if match:
                                    warning_entry["used_verses"] = [int(match.group(1))]
                                    warning_entry["method"] = "repeat_before"
                            elif "using timestamp 0 and verse" in approximation:
                                # Pattern: "no verses before range, using timestamp 0 and verse X"
                                import re

                                match = re.search(r"verse\s+(\d+)", approximation)
                                if match:
                                    warning_entry["used_verses"] = [int(match.group(1))]
                                    warning_entry["method"] = "use_after"

                        elif missing_verses:
                            warning_entry["type"] = "partial"
                            warning_entry["missing_verses"] = missing_verses
                            count = len(missing_verses)
                            if count == 1:
                                warning_entry["details"] = (
                                    f"verse {missing_verses[0]} missing, timestamps repeated"
                                )
                            else:
                                warning_entry["details"] = (
                                    f"{count} verses missing, timestamps repeated"
                                )

                        workspace_warnings[canon][category][iso][distinct_id][fileset][
                            story_int
                        ][ref_key] = warning_entry

                    processed_count += 1

    # Write workspace files (one per distinct_id)
    files_written = 0
    for canon, categories in workspace_data.items():
        for category, languages in categories.items():
            for iso, distinct_ids in languages.items():
                for distinct_id, filesets in distinct_ids.items():
                    output_dir = (
                        WORKSPACE_DIR
                        / template_id
                        / canon
                        / category
                        / iso
                        / distinct_id
                    )
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / "timing.json"

                    # Build output structure with optional warnings
                    output_data = filesets.copy()

                    # Add warnings section only if there are warnings for this distinct_id
                    if distinct_id in workspace_warnings[canon][category][iso]:
                        warnings = workspace_warnings[canon][category][iso][distinct_id]
                        if warnings:
                            output_data["warnings"] = warnings

                    # Write compact JSON (no indentation)
                    with open(output_file, "w") as f:
                        json.dump(output_data, f, sort_keys=True, separators=(",", ":"))

                    files_written += 1

    log(f"\nWorkspace export summary:")
    log(f"  Processed: {processed_count} references")
    log(f"  Missing: {missing_count} references")
    log(f"  Files written: {files_written}")

    return files_written > 0, export_log


def create_region_zips(
    template_id: str,
    iso_to_regions: Dict[str, List[str]],
    region_to_isos: Dict[str, List[str]],
) -> int:
    """
    Step 2: Create zip files per region from workspace data.
    Returns number of zip files created.
    """
    log(f"\n{'=' * 70}")
    log(f"Step 2: Create region zip files for template: {template_id}")
    log("=" * 70)

    workspace_template_dir = WORKSPACE_DIR / template_id
    if not workspace_template_dir.exists():
        log("No workspace data found", "ERROR")
        return 0

    # Create regions output directory
    regions_dir = EXPORT_TEMPLATES_DIR / template_id / "regions"
    regions_dir.mkdir(parents=True, exist_ok=True)

    zip_files_created = 0
    languages_without_region = set()

    # Track which languages have no region
    all_workspace_languages = set()
    for canon_dir in workspace_template_dir.iterdir():
        if not canon_dir.is_dir():
            continue
        for category_dir in canon_dir.iterdir():
            if not category_dir.is_dir():
                continue
            for lang_dir in category_dir.iterdir():
                if lang_dir.is_dir():
                    all_workspace_languages.add(lang_dir.name)

    languages_without_region = all_workspace_languages - set(iso_to_regions.keys())

    # Create one zip file per region
    for region, isos in region_to_isos.items():
        # Sanitize region name for filename
        safe_region_name = region.replace(" ", "_").replace("/", "_")
        zip_filename = regions_dir / f"{safe_region_name}.zip"

        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
            files_in_zip = 0

            # Walk through workspace and add files for languages in this region
            for canon_dir in workspace_template_dir.iterdir():
                if not canon_dir.is_dir():
                    continue
                canon = canon_dir.name

                for category_dir in canon_dir.iterdir():
                    if not category_dir.is_dir():
                        continue
                    category = category_dir.name

                    for lang_dir in category_dir.iterdir():
                        if not lang_dir.is_dir():
                            continue
                        iso = lang_dir.name

                        # Check if this language belongs to this region
                        if iso not in isos:
                            continue

                        # Add all distinct_id directories for this language
                        for distinct_id_dir in lang_dir.iterdir():
                            if not distinct_id_dir.is_dir():
                                continue
                            distinct_id = distinct_id_dir.name

                            timing_file = distinct_id_dir / "timing.json"
                            if not timing_file.exists():
                                continue

                            # Archive path within zip: canon/category/language/distinct_id/timing.json
                            arcname = (
                                f"{canon}/{category}/{iso}/{distinct_id}/timing.json"
                            )

                            # Use fixed timestamp to avoid changing zip when content is identical
                            zip_info = zipfile.ZipInfo(arcname)
                            zip_info.date_time = (2026, 1, 1, 0, 0, 0)
                            zip_info.compress_type = zipfile.ZIP_DEFLATED

                            with open(timing_file, "rb") as f:
                                zipf.writestr(zip_info, f.read())

                            files_in_zip += 1

            if files_in_zip > 0:
                zip_files_created += 1
                log(f"  Created {safe_region_name}.zip with {files_in_zip} files")

    log(f"\nRegion zip summary:")
    log(f"  Zip files created: {zip_files_created}")
    if languages_without_region:
        log(f"  Languages without region: {len(languages_without_region)}")
        for iso in sorted(list(languages_without_region)[:10]):
            log(f"    - {iso}", "WARN")
        if len(languages_without_region) > 10:
            log(f"    ... and {len(languages_without_region) - 10} more", "WARN")

    return zip_files_created


def export_pretty_timings(template_id: str) -> bool:
    """
    Export all timing data in pretty-printed format to ALL-timings directory.
    Reads from: workspace/templates/{template_id}/
    Writes to: export/templates/{template_id}/ALL-timings/
    Returns True if successful, False otherwise.
    """
    log(f"\n{'=' * 70}")
    log(f"Exporting pretty-formatted timings for template: {template_id}")
    log("=" * 70)

    workspace_template_dir = WORKSPACE_DIR / template_id
    if not workspace_template_dir.exists():
        log("No workspace data found", "ERROR")
        return False

    # Create export directory for pretty timings
    export_timings_dir = EXPORT_TEMPLATES_DIR / template_id / "ALL-timings"
    export_timings_dir.mkdir(parents=True, exist_ok=True)

    log(f"Reading from: {workspace_template_dir}")
    log(f"Writing to: {export_timings_dir}")

    file_count = 0
    # Walk through all files in workspace template directory
    for file_path in workspace_template_dir.rglob("*"):
        if file_path.is_file():
            # Create corresponding path in export directory
            relative_path = file_path.relative_to(workspace_template_dir)
            output_path = export_timings_dir / relative_path

            # Create parent directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Read compact JSON and write pretty version
            if file_path.suffix == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
            else:
                # Copy non-JSON files as-is (if any)
                import shutil

                shutil.copy2(file_path, output_path)

            file_count += 1

            # Print progress every 100 files
            if file_count % 100 == 0:
                log(f"  Processed {file_count} files...")

    log(f"\nPretty timings export complete")
    log(f"  Total files exported: {file_count}")
    log(f"  Export path: {export_timings_dir.absolute()}")

    return True


def create_all_timings_zip(template_id: str) -> bool:
    """
    Create ALL-timings.zip containing all workspace data for a template.
    Stored as: export/templates/{template_id}/ALL-timings.zip
    Returns True if successful, False otherwise.
    """
    log(f"\n{'=' * 70}")
    log(f"Creating ALL-timings.zip for template: {template_id}")
    log("=" * 70)

    workspace_template_dir = WORKSPACE_DIR / template_id
    if not workspace_template_dir.exists():
        log("No workspace data found", "ERROR")
        return False

    # Create export directory for this template
    export_template_dir = EXPORT_TEMPLATES_DIR / template_id
    export_template_dir.mkdir(parents=True, exist_ok=True)

    # Create zip file
    zip_path = export_template_dir / "ALL-timings.zip"

    # Remove existing archive if it exists
    if zip_path.exists():
        zip_path.unlink()
        log(f"Removed existing archive: {zip_path}")

    log(f"Creating archive: {zip_path}")
    log(f"Source directory: {workspace_template_dir}")

    file_count = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in workspace template directory
        for file_path in workspace_template_dir.rglob("*"):
            if file_path.is_file():
                # Create archive path relative to workspace template directory
                arcname = file_path.relative_to(workspace_template_dir)

                # Use fixed timestamp to avoid changing zip when content is identical
                zip_info = zipfile.ZipInfo(str(arcname))
                zip_info.date_time = (2026, 1, 1, 0, 0, 0)
                zip_info.compress_type = zipfile.ZIP_DEFLATED

                with open(file_path, "rb") as f:
                    zipf.writestr(zip_info, f.read())

                file_count += 1

                # Print progress every 100 files
                if file_count % 100 == 0:
                    log(f"  Archived {file_count} files...")

    # Get archive size
    archive_size = zip_path.stat().st_size
    size_mb = archive_size / (1024 * 1024)

    log(f"\nALL-timings.zip created successfully")
    log(f"  Total files archived: {file_count}")
    log(f"  Archive size: {size_mb:.2f} MB")
    log(f"  Archive path: {zip_path.absolute()}")

    return True


def main():
    log("=" * 70)
    log("Template Timing Data Export (Four-Step Process)")
    log("=" * 70)

    # Load region mappings
    iso_to_regions, region_to_isos = load_regions_config()
    if not iso_to_regions:
        log("Failed to load region mappings", "ERROR")
        sys.exit(1)

    unique_languages = len(iso_to_regions)
    total_mappings = sum(len(regions) for regions in iso_to_regions.values())
    log(f"Loaded {unique_languages} languages with {total_mappings} region mappings")

    # Check if downloads exist
    if not DOWNLOADS_DIR.exists():
        log("\nNo downloads directory found", "ERROR")
        log("Please run: python3 download_templates.py", "ERROR")
        sys.exit(1)

    # Get templates
    templates = get_template_ids()
    if not templates:
        log("No templates found", "ERROR")
        sys.exit(1)

    log(f"Found {len(templates)} template(s): {', '.join(templates)}")

    # Export each template
    success_count = 0
    for template_id in templates:
        # Step 1: Export to workspace
        success, export_log = export_to_workspace(template_id)
        if not success:
            log(f"Failed to export {template_id} to workspace", "ERROR")
            continue

        # Step 2: Export pretty-formatted ALL-timings directory
        pretty_success = export_pretty_timings(template_id)
        if not pretty_success:
            log(f"Failed to export pretty timings for {template_id}", "ERROR")
            continue

        # Step 3: Create ALL-timings.zip
        all_zip_success = create_all_timings_zip(template_id)
        if not all_zip_success:
            log(f"Failed to create ALL-timings.zip for {template_id}", "ERROR")
            continue

        # Step 4: Create region zip files
        zip_count = create_region_zips(template_id, iso_to_regions, region_to_isos)
        if zip_count == 0:
            log(f"Failed to create region zips for {template_id}", "ERROR")
            continue

        # Save export log
        export_log.save(template_id)

        success_count += 1

    log("\n" + "=" * 70)
    log(f"Export complete: {success_count}/{len(templates)} templates exported")
    log("=" * 70)


if __name__ == "__main__":
    main()
