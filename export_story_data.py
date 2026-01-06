#!/usr/bin/env python3
"""
Export Bible story data by scanning the downloads directory structure.

This script:
1. Scans downloads/{canon}/{category}/{iso}/{distinct_id}/ for all downloaded files
2. Recategorizes based on what actually exists (not what was intended)
3. Creates export/{canon}/{actual_category}/{iso}/{distinct_id}/bible-data.json
4. Uses "failed" category for entries with no successful downloads
5. Marks status as "available" (files exist) or "failed" (no files, but in error log)

Categories determined by actual content:
- with-timecode: Has audio + text + timing
- audio-with-timecode: Has audio + timing (no text)
- syncable: Has audio + text (no timing)
- text-only: Has text only
- audio-only: Has audio only
- failed: No successful downloads (only error log entries)

Usage:
    python export_story_data.py
"""

import json
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Directories
DOWNLOADS_DIR = Path("downloads/BB")
DOWNLOAD_LOG_DIR = Path("download_log")
EXPORT_DIR = Path("export/ALL-langs")  # Human-readable exports with whitespace
WORKSPACE_DIR = Path("workspace")  # Compact format for zipping
SORTED_DIR = Path("sorted")

# Fixed timestamp for reproducible builds (avoids changing zip files when content is identical)
FIXED_TIMESTAMP = "2026-01-01T00:00:00Z"

# Category constants
CATEGORY_WITH_TIMECODE = "with-timecode"
CATEGORY_AUDIO_WITH_TIMECODE = "audio-with-timecode"
CATEGORY_SYNCABLE = "syncable"
CATEGORY_TEXT_ONLY = "text-only"
CATEGORY_AUDIO_ONLY = "audio-only"
CATEGORY_FAILED = "failed"

ALL_CATEGORIES = [
    CATEGORY_WITH_TIMECODE,
    CATEGORY_AUDIO_WITH_TIMECODE,
    CATEGORY_SYNCABLE,
    CATEGORY_TEXT_ONLY,
    CATEGORY_AUDIO_ONLY,
]


def load_error_log(iso: str, canon: str) -> dict:
    """
    Load error log for a specific language and canon.

    Returns dict mapping distinct_id -> {fileset_id: [errors]}
    """
    error_log_path = (
        DOWNLOAD_LOG_DIR / canon.lower() / iso / f"{canon.lower()}-{iso}-error.json"
    )

    if not error_log_path.exists():
        return {}

    try:
        with open(error_log_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load error log {error_log_path}: {e}")
        return {}

    # Organize errors by distinct_id and fileset
    errors_by_distinct_id = defaultdict(lambda: defaultdict(list))

    for error_entry in data.get("errors", []):
        book = error_entry.get("book", "?")
        chapter = error_entry.get("chapter", "?")

        # Process all error types
        for error_list_key in ["audio_errors", "text_errors", "timing_errors"]:
            for err in error_entry.get(error_list_key, []):
                distinct_id = err.get("distinct_id", "?")
                fileset_id = err.get("fileset", "?")
                error_type = err.get("error_type", "?")

                errors_by_distinct_id[distinct_id][fileset_id].append(
                    {
                        "book": book,
                        "chapter": chapter,
                        "error_type": error_type,
                    }
                )

    return errors_by_distinct_id


def get_fileset_type(fileset_id: str):
    """
    Determine the type of a fileset based on its ID pattern.

    Returns: "audio", "text", or "timing"
    """
    fileset_lower = fileset_id.lower()

    # Audio patterns: ends with DA (drama), SA (audio), or contains audio indicators
    if (
        any(x in fileset_id for x in ["1DA", "2DA", "1SA", "2SA"])
        or "audio" in fileset_lower
    ):
        return "audio"

    # Text patterns: ends with ET or contains text indicators
    if "_ET" in fileset_id or "text" in fileset_lower:
        return "text"

    # Timing files are typically JSON with timing suffix
    if "timing" in fileset_lower:
        return "timing"

    # Default based on file extension will be handled when processing files
    return "text"  # Default assumption


def clean_file_path(file_path: str, fileset_id: str) -> str:
    """
    Clean file path by removing redundant book/chapter prefix only.
    Keep the full filename after the BOOK_CCC_ prefix.

    Example:
        Input: "REV/REV_015_AAAMLTN1DA.mp3", fileset_id: "AAAMLTN1DA"
        Output: "AAAMLTN1DA.mp3"

        Input: "REV/REV_015_AAAMLTN_ET.txt", fileset_id: "AAAMLTN"
        Output: "AAAMLTN_ET.txt"

        Input: "REV/REV_015_AAAMLTN1DA_timing.json", fileset_id: "AAAMLTN1DA_timing"
        Output: "AAAMLTN1DA_timing.json"
    """
    # Get the filename from the path
    path_obj = Path(file_path)
    filename = path_obj.name

    # Remove the book/chapter prefix pattern (e.g., "REV_015_")
    # This pattern is: BOOK_CCC_ where BOOK is 3 letters and CCC is 3 digits
    parts = filename.split("_")
    if len(parts) >= 3:
        # Reconstruct without the first two parts (BOOK and CCC)
        filename = "_".join(parts[2:])

    return filename


def collect_files_for_distinct_id(distinct_id_path: Path) -> dict:
    """
    Collect all downloaded files under a distinct_id directory.

    Returns dict: {fileset_id: {"type": type, "files": [relative_paths]}}
    Timing files are collected for analysis but not included in output.
    """
    filesets: dict[str, dict[str, list | str]] = defaultdict(
        lambda: {"files": [], "type": ""}
    )

    # Walk through all files under this distinct_id
    for file_path in distinct_id_path.rglob("*"):
        if not file_path.is_file():
            continue

        # Get relative path from distinct_id directory
        relative_path = file_path.relative_to(distinct_id_path)

        # Extract fileset_id from filename
        # Pattern: BOOK_CCC_FILESETID.ext or BOOK_CCC_FILESETID_timing.json
        filename = file_path.name
        parts = filename.split("_")

        if len(parts) < 3:
            continue

        # Fileset ID is typically the 3rd part (after BOOK_CCC_)
        if filename.endswith("_timing.json"):
            # Timing file: BOOK_CCC_FILESETID_timing.json
            # Use the audio fileset_id + "_timing" suffix for separation
            base_fileset_id = parts[2] if len(parts) >= 4 else parts[-2]
            fileset_id = f"{base_fileset_id}_timing"
            file_type = "timing"
        else:
            # Regular file: BOOK_CCC_FILESETID.ext
            # Fileset ID includes all parts after BOOK_CCC (parts 2 onwards)
            # Example: REV_015_ENGNLTN_ET.txt -> ENGNLTN_ET
            if len(parts) >= 3:
                # Join all parts from index 2 onwards, then remove extension
                remaining = "_".join(parts[2:])
                fileset_id = remaining.rsplit(".", 1)[0]
            else:
                continue

            # Determine type from extension
            if file_path.suffix == ".mp3":
                file_type = "audio"
            elif file_path.suffix == ".txt":
                file_type = "text"
            elif file_path.suffix == ".json":
                file_type = "timing"
            else:
                file_type = get_fileset_type(fileset_id)

        # Clean the file path before adding
        cleaned_path = clean_file_path(str(relative_path), fileset_id)
        files = filesets[fileset_id]["files"]
        if isinstance(files, list):
            files.append(cleaned_path)

        if not filesets[fileset_id]["type"]:
            filesets[fileset_id]["type"] = file_type

    return dict(filesets)


def determine_actual_category(filesets_by_type: dict[str, dict]) -> str:
    """
    Determine the actual category based on what content exists.

    Returns: One of the category constants defined at module level.
    """
    # In compact format, filesets are just arrays, so check if non-empty
    has_audio = bool([fs for fs in filesets_by_type["audio"].values() if fs])
    has_text = bool([fs for fs in filesets_by_type["text"].values() if fs])
    has_timing = bool([fs for fs in filesets_by_type["timing"].values() if fs])

    # No successful downloads at all
    if not has_audio and not has_text and not has_timing:
        return CATEGORY_FAILED

    # Determine category based on what exists
    if has_audio and has_text and has_timing:
        return CATEGORY_WITH_TIMECODE
    elif has_audio and has_timing and not has_text:
        return CATEGORY_AUDIO_WITH_TIMECODE
    elif has_audio and has_text:
        return CATEGORY_SYNCABLE
    elif has_text:
        # Text only, or text + timing (timing without audio is not useful)
        return CATEGORY_TEXT_ONLY
    elif has_audio:
        return CATEGORY_AUDIO_ONLY
    else:
        # Edge case: only timing without any content
        return CATEGORY_FAILED


def strip_fileset_prefix(fileset_id: str, file_path: str) -> str:
    """
    Strip fileset ID prefix from file path if it matches.
    Always keep the character immediately after the ID.
    Returns empty string if stripping would result in empty string.

    Example:
        fileset_id: "ENGESVN2DA"
        file_path: "ENGESVN2DA-01-Matthew-001.mp3"
        returns: "-01-Matthew-001.mp3"
    """
    if file_path.startswith(fileset_id):
        # Remove the ID but keep everything after (including next character)
        result = file_path[len(fileset_id) :]
        # Don't return empty string - keep original if nothing left
        return result if result else file_path
    return file_path


def export_language_data(
    canon: str,
    original_category: str,
    iso: str,
    distinct_id: str,
    distinct_id_path: Path,
) -> str:
    """
    Export data for a specific canon/category/iso/distinct_id combination.
    Recategorizes based on actual content.
    """
    # Collect downloaded files
    downloaded_filesets = collect_files_for_distinct_id(distinct_id_path)

    # Load error log for this language/canon
    errors_by_distinct_id = load_error_log(iso, canon)
    errors_for_this_distinct_id = errors_by_distinct_id.get(distinct_id, {})

    # Organize filesets by type (compact format: only file arrays)
    # Timing is collected for category determination but not output
    filesets_by_type = {"audio": {}, "text": {}, "timing": {}}

    # Add downloaded filesets
    for fileset_id, fileset_data in downloaded_filesets.items():
        file_type = fileset_data["type"]
        if not file_type:
            continue

        files_list = fileset_data["files"]
        # Compact format: just the file list
        filesets_by_type[file_type][fileset_id] = sorted(files_list)

    # For failed filesets, we'll use empty arrays
    for fileset_id, errors in errors_for_this_distinct_id.items():
        # Determine type from fileset_id
        file_type = get_fileset_type(fileset_id)

        # Only add if not already present (no downloads)
        if fileset_id not in filesets_by_type[file_type]:
            # Compact format: empty array for failed
            filesets_by_type[file_type][fileset_id] = []

    # Determine actual category based on what exists
    actual_category = determine_actual_category(filesets_by_type)

    # Log recategorization if changed
    if actual_category != original_category:
        print(f"  Recategorized: {original_category} → {actual_category}")

    # Create export data structure with optimized format:
    # - Use short keys: "a" for audio, "t" for text
    # - Single string value combining stripped fileset ID with file extension
    # - Format: "N1DA.mp3" (fileset_id minus distinct_id, plus file extension)
    # - Metadata is encoded in directory path: export/{canon}/{category}/{iso}/{distinct_id}
    # - Exclude timing data as it's redundant (can be derived from audio ID)

    # Collect audio filesets (skip empty ones)
    audio_filesets = {
        fileset_id: files
        for fileset_id, files in filesets_by_type["audio"].items()
        if files
    }

    # Collect text filesets (skip empty ones)
    text_filesets = {
        fileset_id: files
        for fileset_id, files in filesets_by_type["text"].items()
        if files
    }

    # ERROR if multiple filesets detected
    if len(audio_filesets) > 1:
        fileset_ids = ", ".join(audio_filesets.keys())
        raise ValueError(
            f"Multiple audio filesets detected for {iso}/{distinct_id}: {fileset_ids}. "
            f"Expected exactly 0 or 1 audio fileset."
        )

    if len(text_filesets) > 1:
        fileset_ids = ", ".join(text_filesets.keys())
        raise ValueError(
            f"Multiple text filesets detected for {iso}/{distinct_id}: {fileset_ids}. "
            f"Expected exactly 0 or 1 text fileset."
        )

    # Extract single fileset data (or empty string if none)
    # Format: stripped_fileset_id + file_extension
    # Example: "ENGKJVN1DA" - "ENGKJV" = "N1DA", + ".mp3" = "N1DA.mp3"
    audio_value = ""
    if audio_filesets:
        fileset_id, files = next(iter(audio_filesets.items()))
        # Strip distinct_id from fileset_id
        stripped_fileset = (
            fileset_id[len(distinct_id) :]
            if fileset_id.startswith(distinct_id)
            else fileset_id
        )
        # Get the file path and strip the fileset_id prefix from it
        file_path = files[0] if files else ""
        file_ext = strip_fileset_prefix(fileset_id, file_path)
        # Combine: stripped fileset ID + file extension
        audio_value = stripped_fileset + file_ext

    text_value = ""
    if text_filesets:
        fileset_id, files = next(iter(text_filesets.items()))
        # Strip distinct_id from fileset_id
        stripped_fileset = (
            fileset_id[len(distinct_id) :]
            if fileset_id.startswith(distinct_id)
            else fileset_id
        )
        # Get the file path and strip the fileset_id prefix from it
        file_path = files[0] if files else ""
        file_ext = strip_fileset_prefix(fileset_id, file_path)
        # Combine: stripped fileset ID + file extension
        text_value = stripped_fileset + file_ext

    # Simplified format: single string values
    # Omit keys with empty string values
    export_data = {}
    if audio_value:
        export_data["a"] = audio_value
    if text_value:
        export_data["t"] = text_value

    # Create export directory using actual category (human-readable format)
    export_path = EXPORT_DIR / canon.lower() / actual_category / iso / distinct_id
    export_path.mkdir(parents=True, exist_ok=True)

    # Write JSON file with nice formatting for human readability
    output_file = export_path / "data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    # Also write compact version to workspace for zipping
    workspace_path = WORKSPACE_DIR / canon.lower() / actual_category / iso / distinct_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    workspace_file = workspace_path / "data.json"
    with open(workspace_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, separators=(",", ":"), ensure_ascii=False)

    print(f"  → {output_file}")

    return actual_category


def scan_and_export() -> None:
    """
    Scan downloads directory and export data for all found combinations.
    """
    if not DOWNLOADS_DIR.exists():
        print(f"Error: Downloads directory not found: {DOWNLOADS_DIR}")
        return

    print("Scanning downloads directory...")
    print(f"  {DOWNLOADS_DIR}\n")

    # Track statistics
    total_exported = 0
    by_canon = defaultdict(int)
    by_actual_category = defaultdict(int)
    by_original_category = defaultdict(int)
    recategorized_count = 0

    # Scan downloads/{canon}/{category}/{iso}/{distinct_id}/
    for canon_dir in sorted(DOWNLOADS_DIR.iterdir()):
        if not canon_dir.is_dir():
            continue

        canon = canon_dir.name.upper()

        for category_dir in sorted(canon_dir.iterdir()):
            if not category_dir.is_dir():
                continue

            original_category = category_dir.name

            for iso_dir in sorted(category_dir.iterdir()):
                if not iso_dir.is_dir():
                    continue

                iso = iso_dir.name

                for distinct_id_dir in sorted(iso_dir.iterdir()):
                    if not distinct_id_dir.is_dir():
                        continue

                    distinct_id = distinct_id_dir.name

                    # Verify distinct_id is 6 letters
                    if len(distinct_id) != 6:
                        print(
                            f"Warning: distinct_id '{distinct_id}' is not 6 letters, skipping"
                        )
                        continue

                    # Export this combination (returns actual category)
                    actual_category = export_language_data(
                        canon, original_category, iso, distinct_id, distinct_id_dir
                    )

                    total_exported += 1
                    by_canon[canon] += 1
                    by_actual_category[actual_category] += 1
                    by_original_category[original_category] += 1

                    if actual_category != original_category:
                        recategorized_count += 1

    # Print summary
    print("\n" + "=" * 80)
    print("EXPORT SUMMARY")
    print("=" * 80)
    print(f"\nTotal exports: {total_exported}")
    print(
        f"Recategorized: {recategorized_count} ({recategorized_count / total_exported * 100:.1f}%)"
    )

    if by_canon:
        print("\nBy canon:")
        for canon, count in sorted(by_canon.items()):
            print(f"  {canon:10s}: {count:4d} exports")

    if by_actual_category:
        print("\nBy actual category (after recategorization):")
        for category, count in sorted(by_actual_category.items()):
            print(f"  {category:20s}: {count:4d} exports")

    if recategorized_count > 0:
        print("\nOriginal categories (before recategorization):")
        for category, count in sorted(by_original_category.items()):
            print(f"  {category:20s}: {count:4d} exports")

    print("\n" + "=" * 80)


def load_language_names_from_sorted() -> dict[str, dict[str, str]]:
    """
    Load language names from sorted metadata.json files.
    This reads from the sorted directory created by sort_cache_data.py.

    Returns:
        dict: {iso: {"name": "English name", "autonym": "Vernacular name"}}
    """
    language_names = {}

    if not SORTED_DIR.exists():
        print(f"Warning: Sorted directory not found: {SORTED_DIR}")
        return language_names

    # Scan sorted directory for metadata.json files
    for canon_dir in SORTED_DIR.iterdir():
        if not canon_dir.is_dir():
            continue

        for iso_dir in canon_dir.iterdir():
            if not iso_dir.is_dir():
                continue

            iso = iso_dir.name

            # Skip if we already have this language
            if iso in language_names:
                continue

            # Look for any metadata.json file in this iso directory
            metadata_files = list(iso_dir.glob("*/metadata.json"))
            if metadata_files:
                try:
                    with open(metadata_files[0], "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                        # Extract language info
                        lang_info = metadata.get("language", {})
                        if lang_info and "iso" in lang_info:
                            language_names[iso] = {
                                "name": lang_info.get("name", ""),
                                "autonym": lang_info.get("autonym", ""),
                            }
                except (json.JSONDecodeError, IOError):
                    # Skip files that can't be read
                    pass

    return language_names


def generate_summary_to_dir(
    target_dir: Path, source_dir: Path, use_compact: bool = False
) -> tuple[Path, set, dict]:
    """
    Generate a summary.json file in the specified directory.

    Args:
        target_dir: Directory where summary.json will be written
        source_dir: Directory to scan for language data
        use_compact: If True, use compact JSON format (no whitespace)
    """
    # Load language names from sorted metadata
    language_names = load_language_names_from_sorted()

    # Collect all languages by canon and category (unique by ISO, no distinct_ids)
    canons_data = {}

    # Scan the source directory structure
    base_export = source_dir

    for canon_dir in sorted(base_export.iterdir()):
        if not canon_dir.is_dir():
            continue

        canon = canon_dir.name.lower()

        # Initialize canon entry
        if canon not in canons_data:
            canons_data[canon] = {}
            for category in ALL_CATEGORIES:
                canons_data[canon][category] = {}

        for category_dir in sorted(canon_dir.iterdir()):
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            # Skip "failed" category - we don't include failed in summaries or zips
            if category == "failed":
                continue

            # Skip unknown categories (e.g., old category names during migration)
            if category not in canons_data[canon]:
                print(
                    f"  Warning: Skipping unknown category '{category}' in {canon_dir.name}"
                )
                continue

            for iso_dir in sorted(category_dir.iterdir()):
                if not iso_dir.is_dir():
                    continue

                iso = iso_dir.name

                # Only add each ISO once per canon/category
                if iso not in canons_data[canon][category]:
                    # Get language names
                    lang_info = language_names.get(iso, {})
                    language_name = lang_info.get("name", "")
                    vernacular_name = lang_info.get("autonym", "")

                    # If no language name found, use ISO code with note
                    if not language_name:
                        language_name = f"{iso.upper()} (English name not cached)"

                    # If no vernacular name, use note
                    if not vernacular_name:
                        vernacular_name = f"{iso.upper()} (vernacular name not cached)"

                    # Add to category with compact format
                    # Omit "v" if it's the same as "n"
                    lang_entry = {"n": language_name}
                    if vernacular_name != language_name:
                        lang_entry["v"] = vernacular_name
                    canons_data[canon][category][iso] = lang_entry

    # Count total unique languages across all canons and categories
    all_isos = set()
    for canon_data in canons_data.values():
        for iso_dict in canon_data.values():
            all_isos.update(iso_dict.keys())

    # Create summary structure
    summary = {
        "metadata": {
            "generated_at": FIXED_TIMESTAMP,
            "total_languages": len(all_isos),
        },
        "canons": canons_data,
    }

    # Write summary file
    target_dir.mkdir(parents=True, exist_ok=True)
    # Use ALL-langs.json for human-readable, summary.json for compact
    filename = "ALL-langs.json" if not use_compact else "summary.json"
    summary_file = target_dir / filename

    if use_compact:
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, separators=(",", ":"), ensure_ascii=False)
    else:
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary_file, all_isos, canons_data


def generate_manifest(target_dir: Path) -> Path:
    """
    Generate manifest.json that indexes all data.json files.

    Structure matches build-manifest.mjs output:
    {
      "metadata": {
        "generatedAt": "ISO timestamp",
        "totalFiles": count
      },
      "files": {
        "testament": {
          "category": {
            "langCode": ["distinctId1", "distinctId2", ...]
          }
        }
      }
    }

    Args:
        target_dir: Directory to scan and write manifest.json

    Returns:
        Path to the generated manifest.json file
    """
    # Collect all data.json files
    manifest_data = {
        "metadata": {
            "generatedAt": FIXED_TIMESTAMP,
            "totalFiles": 0,
        },
        "files": {},
    }

    file_count = 0

    # Walk through testament/category/langCode/distinctId/data.json structure
    for testament_dir in sorted(target_dir.iterdir()):
        if not testament_dir.is_dir():
            continue

        testament = testament_dir.name

        # Skip non-testament directories
        if testament not in ["nt", "ot"]:
            continue

        if testament not in manifest_data["files"]:
            manifest_data["files"][testament] = {}

        for category_dir in sorted(testament_dir.iterdir()):
            if not category_dir.is_dir():
                continue

            category = category_dir.name

            # Skip failed category
            if category == "failed":
                continue

            if category not in manifest_data["files"][testament]:
                manifest_data["files"][testament][category] = {}

            for lang_dir in sorted(category_dir.iterdir()):
                if not lang_dir.is_dir():
                    continue

                lang_code = lang_dir.name

                if lang_code not in manifest_data["files"][testament][category]:
                    manifest_data["files"][testament][category][lang_code] = []

                for distinct_id_dir in sorted(lang_dir.iterdir()):
                    if not distinct_id_dir.is_dir():
                        continue

                    distinct_id = distinct_id_dir.name

                    # Check if data.json exists
                    data_file = distinct_id_dir / "data.json"
                    if data_file.exists():
                        manifest_data["files"][testament][category][lang_code].append(
                            distinct_id
                        )
                        file_count += 1

    # Update total count
    manifest_data["metadata"]["totalFiles"] = file_count

    # Write manifest.json in compact format
    manifest_file = target_dir / "manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, separators=(",", ":"), ensure_ascii=False)

    return manifest_file


def generate_summary() -> None:
    """
    Generate summary.json files:
    1. Human-readable version in export/ALL-langs/
    2. Compact version in workspace/
    """
    print("\n" + "=" * 80)
    print("GENERATING SUMMARIES")
    print("=" * 80)

    # Load language names from sorted metadata
    language_names = load_language_names_from_sorted()
    print(f"\nLoaded {len(language_names)} language names from sorted metadata")

    # Generate human-readable summary as export/ALL-langs.json (scanning export/ALL-langs/)
    print("\nGenerating human-readable summary as export/ALL-langs.json...")
    summary_file_readable, all_isos, canons_data = generate_summary_to_dir(
        Path("export"), EXPORT_DIR, use_compact=False
    )
    print("✓ Readable summary: " + str(summary_file_readable))

    # Generate compact summary in workspace/ (scanning workspace/)
    print(f"\nGenerating compact summary in {WORKSPACE_DIR}...")
    summary_file_compact, _, _ = generate_summary_to_dir(
        WORKSPACE_DIR, WORKSPACE_DIR, use_compact=True
    )
    print("✓ Compact summary: " + str(summary_file_compact))

    # Copy workspace summary.json to export/ALL-langs-compact.json
    print("\nCopying compact summary to export/ALL-langs-compact.json...")
    compact_export_file = Path("export") / "ALL-langs-compact.json"
    import shutil

    shutil.copy2(summary_file_compact, compact_export_file)
    print("✓ Compact export: " + str(compact_export_file))

    # Generate mini summary as export/ALL-langs-mini.json (ISO codes only, compact format)
    print("\nGenerating mini summary as export/ALL-langs-mini.json...")
    mini_summary = {
        "metadata": {
            "generated_at": FIXED_TIMESTAMP,
            "total_languages": len(all_isos),
        },
        "canons": {},
    }

    # Build mini structure with ISO codes only (no language names)
    for canon, categories in canons_data.items():
        mini_summary["canons"][canon] = {}
        for category, languages in categories.items():
            # Just list of ISO codes (no names)
            iso_list = sorted(languages.keys())
            if iso_list:  # Only include category if it has languages
                mini_summary["canons"][canon][category] = iso_list

    mini_file = Path("export") / "ALL-langs-mini.json"
    with open(mini_file, "w", encoding="utf-8") as f:
        json.dump(mini_summary, f, separators=(",", ":"), ensure_ascii=False)
    print("✓ Mini summary: " + str(mini_file))

    print("\nSummary statistics:")
    print(f"  Total unique languages: {len(all_isos)}")

    # Count languages with/without names per canon
    for canon in sorted(canons_data.keys()):
        canon_data = canons_data[canon]
        total_entries = sum(len(iso_dict) for iso_dict in canon_data.values())
        langs_with_names = sum(
            1
            for iso_dict in canon_data.values()
            for entry in iso_dict.values()
            if not entry["n"].endswith("(English name not cached)")
        )
        langs_without_names = total_entries - langs_with_names

        print(f"\n  Canon: {canon.upper()}")
        print(f"    Languages with names: {langs_with_names}")
        print(f"    Languages without names: {langs_without_names}")

        for category in ALL_CATEGORIES:
            count = len(canon_data.get(category, {}))
            print(f"    {category:20s}: {count:4d} languages")

    # Generate manifest.json in workspace
    print("\nGenerating manifest.json in workspace...")
    manifest_file = generate_manifest(WORKSPACE_DIR)
    print("✓ Manifest file: " + str(manifest_file))

    # Read and display manifest stats
    with open(manifest_file) as f:
        manifest_data = json.load(f)
    total_files = manifest_data["metadata"]["totalFiles"]
    print(f"  Total data.json files indexed: {total_files}")

    print("\n" + "=" * 80)


def create_export_archive() -> None:
    """
    Create a zip archive from the workspace directory (compact format).
    Store the archive as export/ALL-langs-data.zip
    Only includes: nt/, ot/ folders, summary.json, and manifest.json
    """
    print("\n" + "=" * 80)
    print("CREATING EXPORT ARCHIVE")
    print("=" * 80)

    if not WORKSPACE_DIR.exists():
        print(f"Error: Workspace directory not found: {WORKSPACE_DIR}")
        return

    # Archive will be placed in export/
    archive_path = EXPORT_DIR.parent / "ALL-langs-data.zip"

    # Remove existing archive if it exists
    if archive_path.exists():
        archive_path.unlink()
        print(f"\nRemoved existing archive: {archive_path}")

    print(f"\nCreating archive: {archive_path}")
    print(f"Source directory: {WORKSPACE_DIR}")

    file_count = 0
    skipped_failed = 0
    skipped_other = 0
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in workspace directory
        for file_path in WORKSPACE_DIR.rglob("*"):
            if file_path.is_file():
                # Create archive path relative to workspace directory
                arcname = file_path.relative_to(WORKSPACE_DIR)
                parts = arcname.parts

                # Skip files in "failed" category
                if parts and parts[0] == CATEGORY_FAILED:
                    skipped_failed += 1
                    continue

                # Only include nt/, ot/ folders, summary.json, and manifest.json
                if parts and parts[0] not in [
                    "nt",
                    "ot",
                    "summary.json",
                    "manifest.json",
                ]:
                    # Check if this is summary.json or manifest.json at root level
                    if not (
                        len(parts) == 1
                        and parts[0] in ["summary.json", "manifest.json"]
                    ):
                        skipped_other += 1
                        continue

                # Use fixed timestamp to avoid changing zip when content is identical
                zip_info = zipfile.ZipInfo(str(arcname))
                zip_info.date_time = (2026, 1, 1, 0, 0, 0)
                zip_info.compress_type = zipfile.ZIP_DEFLATED

                with open(file_path, "rb") as f:
                    zipf.writestr(zip_info, f.read())

                file_count += 1

                # Print progress every 100 files
                if file_count % 100 == 0:
                    print(f"  Archived {file_count} files...")

    # Get archive size
    archive_size = archive_path.stat().st_size
    size_mb = archive_size / (1024 * 1024)

    print("\n✓ Archive created successfully")
    print(f"  Total files archived: {file_count}")
    print(f"  Skipped (failed): {skipped_failed}")
    print(f"  Skipped (other): {skipped_other}")
    print(f"  Archive size: {size_mb:.2f} MB")
    print(f"  Archive path: {archive_path.absolute()}")
    print("\n" + "=" * 80)


def parse_regions_config() -> dict[str, dict]:
    """
    Parse the regions.conf file to extract region definitions.

    Now handles metadata lines:
    - @trade: trade/bridge languages
    - @regional: regional lingua francas
    - @educational: educational languages
    - @literacy: primary literacy languages

    Returns:
        dict: {region_id: {"name": str, "languages": [iso_codes], "trade": [iso_codes],
                           "regional": [iso_codes], "educational": [iso_codes], "literacy": [iso_codes]}}
    """
    config_path = Path("config/regions.conf")

    if not config_path.exists():
        print(f"Warning: {config_path} not found. Skipping region zips.")
        return {}

    regions = {}
    current_region = None
    current_languages = []
    current_metadata = {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    # If we have a current region, save it
                    if current_region and current_languages:
                        regions[current_region] = {
                            "name": current_region,
                            "languages": current_languages,
                            **current_metadata,
                        }
                        current_region = None
                        current_languages = []
                        current_metadata = {}
                    continue

                # Check for metadata lines (@trade, @regional, @educational, @literacy)
                if line.startswith("@"):
                    if ":" in line:
                        metadata_type, metadata_value = line.split(":", 1)
                        metadata_type = metadata_type[1:].strip()  # Remove @ prefix
                        metadata_langs = [
                            lang.strip()
                            for lang in metadata_value.split(",")
                            if lang.strip()
                        ]
                        current_metadata[metadata_type] = metadata_langs
                    continue

                # Check if this is a region name (no commas, not all lowercase, not metadata)
                if "," not in line and not line.islower() and not line.startswith("@"):
                    # Save previous region if exists
                    if current_region and current_languages:
                        regions[current_region] = {
                            "name": current_region,
                            "languages": current_languages,
                            **current_metadata,
                        }

                    # Start new region
                    current_region = line
                    current_languages = []
                    current_metadata = {}
                else:
                    # This is a language list line
                    if current_region:
                        # Split by comma and clean up
                        langs = [
                            lang.strip() for lang in line.split(",") if lang.strip()
                        ]
                        current_languages.extend(langs)

        # Don't forget the last region
        if current_region and current_languages:
            regions[current_region] = {
                "name": current_region,
                "languages": current_languages,
                **current_metadata,
            }
    except (IOError, OSError) as e:
        print(f"Error reading regions config: {e}")
        return {}

    return regions


def generate_regions_metadata() -> tuple[Path, dict] | None:
    """
    Generate regions.json metadata file in workspace directory.

    Creates a standalone regions metadata file with:
    - Region definitions
    - Trade languages
    - Regional lingua francas
    - Educational languages
    - Literacy languages
    - Language lists
    """
    print("\n" + "=" * 80)
    print("GENERATING REGIONS METADATA")
    print("=" * 80)

    # Parse regions config
    print("\nParsing regions configuration...")
    regions = parse_regions_config()

    if not regions:
        print("No regions found in config. Skipping regions metadata generation.")
        return

    print(f"Found {len(regions)} regions in config/regions.conf")

    # Build optimized metadata structure
    # Format: {"region_id": {"l": [...], "trade": [...], "regional": [...], ...}}
    regions_metadata = {}

    # Convert regions to optimized format
    for region_name, region_data in sorted(regions.items()):
        region_id = sanitize_filename(region_name)

        # Build optimized entry with "l" for languages
        metadata_entry = {
            "l": region_data["languages"],
        }

        # Add optional metadata fields (directly at entry level, not nested)
        metadata_types = ["trade", "regional", "educational", "literacy"]
        for metadata_type in metadata_types:
            if metadata_type in region_data:
                metadata_entry[metadata_type] = region_data[metadata_type]

        regions_metadata[region_id] = metadata_entry

    # Write compact version to workspace/regions.json
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    regions_file = WORKSPACE_DIR / "regions.json"

    with open(regions_file, "w", encoding="utf-8") as f:
        json.dump(regions_metadata, f, separators=(",", ":"), ensure_ascii=False)

    print(f"\n✓ Regions metadata written to: {regions_file} (compact)")
    print(f"  Total regions: {len(regions_metadata)}")

    # Write non-compacted version to export/regions.json
    export_regions_json = EXPORT_DIR.parent / "regions.json"
    with open(export_regions_json, "w", encoding="utf-8") as f:
        json.dump(regions_metadata, f, indent=2, ensure_ascii=False)
    print(f"✓ Regions metadata written to: {export_regions_json} (readable)")

    # Create regions.zip in export directory with compact format
    export_regions_zip = EXPORT_DIR.parent / "regions.zip"
    with zipfile.ZipFile(export_regions_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "regions.json",
            json.dumps(regions_metadata, separators=(",", ":"), ensure_ascii=False),
        )
    print(f"✓ Regions metadata zipped to: {export_regions_zip} (compact)")
    print(f"{'=' * 80}")

    return regions_file, regions_metadata


def sanitize_filename(name: str) -> str:
    """Convert region name to safe filename."""
    # Replace spaces and special chars with underscore
    safe_name = name.replace(" ", "_")
    safe_name = safe_name.replace(":", "")
    safe_name = safe_name.replace("/", "_")
    # Remove any other problematic characters
    safe_name = "".join(c for c in safe_name if c.isalnum() or c in "_-")
    return safe_name


def extract_iso_from_path(path: str) -> str:
    """
    Extract ISO code from zip entry path.
    Path format: nt/category/iso/distinct_id/bible-data.json
    """
    parts = path.split("/")
    return parts[2] if len(parts) >= 3 else ""


def filter_summary_by_isos(summary: dict, iso_codes: set[str]) -> dict:
    """
    Filter summary.json to only include specified ISO codes.
    Also excludes "failed" category.

    Args:
        summary: The full summary dict
        iso_codes: Set of ISO codes to keep

    Returns:
        Filtered summary dict
    """
    filtered = {"metadata": summary["metadata"].copy(), "canons": {}}

    # Update total languages count
    filtered["metadata"]["total_languages"] = len(iso_codes)

    # Filter each canon
    for canon, categories in summary["canons"].items():
        filtered["canons"][canon] = {}

        for category, languages in categories.items():
            # Skip failed category
            if category == CATEGORY_FAILED:
                continue

            filtered_langs = {
                iso: lang_data
                for iso, lang_data in languages.items()
                if iso in iso_codes
            }

            if filtered_langs:  # Only include category if it has languages
                filtered["canons"][canon][category] = filtered_langs

    return filtered


def create_region_zip(
    region_id: str,
    region_name: str,
    iso_codes: list[str],
    all_summary: dict,
    region_metadata: dict | None = None,
) -> None:
    """
    Create a region-specific zip by filtering ALL-langs-data.zip.
    Uses direct zip-to-zip streaming for efficiency.

    Args:
        region_id: Safe filename for the region
        region_name: Human-readable region name
        iso_codes: List of ISO language codes for this region
        all_summary: The complete summary dict from workspace/summary.json
        region_metadata: Optional metadata dict for this region (trade, regional, etc.)
    """
    iso_set = set(iso_codes)
    all_zip_path = EXPORT_DIR.parent / "ALL-langs-data.zip"
    regions_dir = EXPORT_DIR.parent / "regions"
    regions_dir.mkdir(parents=True, exist_ok=True)
    region_zip_path = regions_dir / f"{region_id}.zip"

    if not all_zip_path.exists():
        print(f"  ✗ Skipping {region_name}: ALL-langs-data.zip not found")
        return

    print(f"  Creating {region_id}.zip ({len(iso_codes)} languages)...")

    # Filter summary
    filtered_summary = filter_summary_by_isos(all_summary, iso_set)

    # Add region metadata if provided
    if region_metadata:
        filtered_summary["region_metadata"] = region_metadata

    matched_files = 0
    skipped_files = 0

    # Direct zip-to-zip filtering
    with zipfile.ZipFile(all_zip_path, "r") as src:
        with zipfile.ZipFile(region_zip_path, "w", zipfile.ZIP_DEFLATED) as dst:
            # Add filtered summary first with fixed timestamp
            summary_json = json.dumps(
                filtered_summary, separators=(",", ":"), ensure_ascii=False
            )
            summary_info = zipfile.ZipInfo("summary.json")
            summary_info.date_time = (2026, 1, 1, 0, 0, 0)
            summary_info.compress_type = zipfile.ZIP_DEFLATED
            dst.writestr(summary_info, summary_json)

            # Stream matching files from ALL-langs-data.zip
            for entry_name in src.namelist():
                if entry_name == "summary.json":
                    continue  # We already added the filtered version

                # Skip files in "failed" category
                if f"/{CATEGORY_FAILED}/" in entry_name or entry_name.startswith(
                    f"{CATEGORY_FAILED}/"
                ):
                    skipped_files += 1
                    continue

                # Extract ISO from path
                iso = extract_iso_from_path(entry_name)

                if iso in iso_set:
                    # Stream this entry to the new zip with fixed timestamp
                    zip_info = zipfile.ZipInfo(entry_name)
                    zip_info.date_time = (2026, 1, 1, 0, 0, 0)
                    zip_info.compress_type = zipfile.ZIP_DEFLATED
                    dst.writestr(zip_info, src.read(entry_name))
                    matched_files += 1
                else:
                    skipped_files += 1

    # Get archive size
    archive_size = region_zip_path.stat().st_size
    size_kb = archive_size / 1024

    print(f"    ✓ {region_id}.zip created")
    print(f"      Files: {matched_files}, Size: {size_kb:.0f} KB")


def create_region_zips() -> None:
    """
    Create region-specific zip files by filtering ALL-langs-data.zip.
    """
    print("\n" + "=" * 80)
    print("CREATING REGION-SPECIFIC ZIPS")
    print("=" * 80)

    # Parse regions config
    print("\nParsing regions configuration...")
    regions = parse_regions_config()

    if not regions:
        print("No regions found in config. Skipping region zips.")
        return

    print(f"Found {len(regions)} regions in config/regions.conf")

    # Load regions metadata from workspace
    workspace_regions_path = WORKSPACE_DIR / "regions.json"
    regions_metadata_dict = {}
    if workspace_regions_path.exists():
        with open(workspace_regions_path, "r", encoding="utf-8") as f:
            regions_data = json.load(f)
            regions_metadata_dict = regions_data.get("regions", {})
        print(f"Loaded metadata for {len(regions_metadata_dict)} regions")

    # Load the complete summary from workspace
    workspace_summary_path = WORKSPACE_DIR / "summary.json"
    if not workspace_summary_path.exists():
        print("Error: workspace/summary.json not found. Cannot create region zips.")
        return

    print(f"\nLoading summary from {workspace_summary_path}...")
    with open(workspace_summary_path, "r", encoding="utf-8") as f:
        all_summary = json.load(f)

    print(f"Total languages in summary: {all_summary['metadata']['total_languages']}")

    # Create each region zip
    print("\nCreating region zips...")
    created_count = 0

    for region_name, region_data in sorted(regions.items()):
        region_id = sanitize_filename(region_name)
        iso_codes = region_data["languages"]

        if not iso_codes:
            print(f"  ⚠ Skipping {region_name}: No languages defined")
            continue

        # Get metadata for this region (only the metadata field)
        region_metadata = None
        if region_id in regions_metadata_dict:
            region_meta_full = regions_metadata_dict[region_id]
            if "metadata" in region_meta_full:
                region_metadata = region_meta_full["metadata"]

        try:
            create_region_zip(
                region_id, region_name, iso_codes, all_summary, region_metadata
            )
            created_count += 1
        except Exception as e:
            print(f"  ✗ Failed to create {region_id}.zip: {e}")

    # Summary
    print("\n" + "=" * 80)
    print(f"✓ Created {created_count} region zip files")
    print("  Location: export/regions/")
    print("=" * 80)


def main() -> None:
    """Main entry point."""
    print("\n" + "=" * 80)
    print("BIBLE STORY DATA EXPORT")
    print("=" * 80)
    print("\nScanning downloads and creating exports...\n")

    try:
        scan_and_export()
        generate_summary()
        generate_regions_metadata()
        create_export_archive()
        create_region_zips()
        print("\n✓ Export completed successfully\n")
    except Exception as e:
        print(f"\n✗ Export failed: {e}\n", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
