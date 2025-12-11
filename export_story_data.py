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
- incomplete-timecode: Has timing but missing audio or text
- syncable: Has audio + text (no timing)
- text-only: Has text only
- audio-only: Has audio only
- failed: No successful downloads (only error log entries)

Usage:
    python export_story_data.py
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

# Directories
DOWNLOADS_DIR = Path("downloads/BB")
DOWNLOAD_LOG_DIR = Path("download_log")
EXPORT_DIR = Path("export")


def load_error_log(iso: str, canon: str):
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


def collect_files_for_distinct_id(distinct_id_path: Path):
    """
    Collect all downloaded files under a distinct_id directory.

    Returns dict: {fileset_id: {"type": type, "files": [relative_paths]}}
    Timing files are separated into their own entries with "_timing" suffix.
    """
    filesets: dict[str, dict[str, list[str] | str | None]] = defaultdict(
        lambda: {"files": [], "type": None}
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
            fileset_id_temp = parts[2].split(".")[0] if len(parts) >= 3 else None

            if not fileset_id_temp:
                continue

            fileset_id = fileset_id_temp

            # Determine type from extension
            if file_path.suffix == ".mp3":
                file_type = "audio"
            elif file_path.suffix == ".txt":
                file_type = "text"
            elif file_path.suffix == ".json":
                file_type = "timing"
            else:
                file_type = get_fileset_type(fileset_id)

        files_list = filesets[fileset_id]["files"]
        if isinstance(files_list, list):
            files_list.append(str(relative_path))
        if filesets[fileset_id]["type"] is None:
            filesets[fileset_id]["type"] = file_type

    return dict(filesets)


def determine_actual_category(filesets_by_type: dict) -> str:
    """
    Determine the actual category based on what content exists.

    Returns: "with-timecode", "incomplete-timecode", "syncable",
             "text-only", "audio-only", or "failed"
    """
    has_audio = bool(
        [
            fs
            for fs in filesets_by_type["audio"].values()
            if fs.get("status") == "available"
        ]
    )
    has_text = bool(
        [
            fs
            for fs in filesets_by_type["text"].values()
            if fs.get("status") == "available"
        ]
    )
    has_timing = bool(
        [
            fs
            for fs in filesets_by_type["timing"].values()
            if fs.get("status") == "available"
        ]
    )

    # No successful downloads at all
    if not has_audio and not has_text and not has_timing:
        return "failed"

    # Determine category based on what exists
    if has_audio and has_text and has_timing:
        return "with-timecode"
    elif has_timing and (not has_audio or not has_text):
        return "incomplete-timecode"
    elif has_audio and has_text:
        return "syncable"
    elif has_text:
        return "text-only"
    elif has_audio:
        return "audio-only"
    else:
        # Edge case: only timing (shouldn't normally happen)
        return "incomplete-timecode"


def export_language_data(
    canon: str,
    original_category: str,
    iso: str,
    distinct_id: str,
    distinct_id_path: Path,
):
    """
    Export data for a specific canon/category/iso/distinct_id combination.
    Recategorizes based on actual content.
    """
    # Collect downloaded files
    downloaded_filesets = collect_files_for_distinct_id(distinct_id_path)

    # Load error log for this language/canon
    errors_by_distinct_id = load_error_log(iso, canon)
    errors_for_this_distinct_id = errors_by_distinct_id.get(distinct_id, {})

    # Organize filesets by type
    filesets_by_type = {"audio": {}, "text": {}, "timing": {}}

    # Add downloaded filesets
    for fileset_id, fileset_data in downloaded_filesets.items():
        file_type_value = fileset_data["type"]
        # Ensure file_type is a string
        if not isinstance(file_type_value, str):
            continue
        file_type = file_type_value

        files_value = fileset_data["files"]
        files_list = files_value if isinstance(files_value, list) else []
        filesets_by_type[file_type][fileset_id] = {
            "status": "available",
            "files": sorted(files_list),
        }

    # Add failed filesets from error log (if not already in downloads)
    for fileset_id, errors in errors_for_this_distinct_id.items():
        # Determine type from fileset_id
        file_type = get_fileset_type(fileset_id)

        # Only add if not already present (no downloads)
        if fileset_id not in filesets_by_type[file_type]:
            # Get the most common error type
            error_types = [e["error_type"] for e in errors]
            most_common_error = (
                max(set(error_types), key=error_types.count)
                if error_types
                else "unknown"
            )

            filesets_by_type[file_type][fileset_id] = {
                "status": "failed",
                "error": most_common_error,
            }

    # Determine actual category based on what exists
    actual_category = determine_actual_category(filesets_by_type)

    # Log recategorization if changed
    if actual_category != original_category:
        print(f"  Recategorized: {original_category} → {actual_category}")

    # Create export data structure
    export_data = {
        "language": iso,
        "canon": canon,
        "category": actual_category,
        "original_category": original_category,
        "distinct_id": distinct_id,
        "filesets": filesets_by_type,
    }

    # Create export directory using actual category
    export_path = EXPORT_DIR / canon.lower() / actual_category / iso / distinct_id
    export_path.mkdir(parents=True, exist_ok=True)

    # Write JSON file
    output_file = export_path / "bible-data.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    print(f"  → {output_file}")

    return actual_category


def scan_and_export():
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


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("BIBLE STORY DATA EXPORT")
    print("=" * 80)
    print("\nScanning downloads and creating exports...\n")

    try:
        scan_and_export()
        print("\n✓ Export completed successfully\n")
    except Exception as e:
        print(f"\n✗ Export failed: {e}\n", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
