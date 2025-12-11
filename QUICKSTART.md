# Quick Start Guide - Bible Story Builder

Build multilingual Bible content in minutes!

## What is Bible Story Builder?

Bible Story Builder downloads Bible text, audio, and timing data from the Digital Bible Platform API. Perfect for:
- Bible translation projects
- Literacy programs
- Oral Bible storytelling
- Multilingual ministry
- Bible app development

## Prerequisites

- Python 3.7+
- Internet connection
- Digital Bible Platform API key (free from [BibleBrain.com](https://www.biblebrain.com/))

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get API Key

1. Visit [https://www.biblebrain.com/](https://www.biblebrain.com/)
2. Create a free account
3. Get your API key from your account settings

### 3. Set Environment Variable

Create a `.env` file in the project root:

```
BIBLE_API_KEY=your-api-key-here
```

Or set it in your shell:

```bash
export BIBLE_API_KEY="your-api-key-here"
```

## Your First Download (5 Minutes)

### Step 1: Fetch Bible Catalog

Download information about available Bibles (2000+ languages, 12,000+ versions):

```bash
python3 fetch_api_cache.py
```

This takes 2-5 minutes and only needs to be done once.

### Step 2: Organize Metadata

Process and organize the catalog by language and canonical structure:

```bash
python3 sort_cache_data.py
```

This takes 1-2 minutes and only needs to be done once.

### Step 3: Download Content

Download Bible content for a specific language:

```bash
# Download English - Genesis chapters 1-3
python3 download_language_content.py eng --books GEN:1-3

# Download Spanish - Psalm 23
python3 download_language_content.py spa --books PSA:23

# Download Swahili - Gospel of John
python3 download_language_content.py swa --books JHN
```

## Understanding the Output

Downloaded content is organized in this structure:

```
downloads/BB/
└── {canon}/              # NT, OT, or PARTIAL
    └── {category}/       # with-timecode, syncable, text-only, etc.
        └── {iso}/        # Language code (e.g., eng, spa)
            └── {id}/     # 6-letter Bible version ID
                └── {BOOK}/
                    ├── {BOOK}_001_{ID}.mp3          # Audio file
                    ├── {BOOK}_001_{ID}.txt          # Text file
                    └── {BOOK}_001_{ID}_timing.json  # Timing data
```

### Example: English Genesis 1-3

```
downloads/BB/
└── ot/
    └── with-timecode/
        └── eng/
            └── ENGESV/
                └── GEN/
                    ├── GEN_001_ENGESVN2DA.mp3
                    ├── GEN_001_ENGESVN2DA_timing.json
                    ├── GEN_001_ENGESVO2ET.txt
                    ├── GEN_002_ENGESVN2DA.mp3
                    ├── GEN_002_ENGESVN2DA_timing.json
                    ├── GEN_002_ENGESVO2ET.txt
                    └── ...
```

### Content Types

Each chapter may include:
- **Audio** (`.mp3`) - Narrated Bible text
- **Text** (`.txt`) - Bible text in that language  
- **Timing** (`.json`) - Word-by-word synchronization data

Categories:
- **with-timecode** - Has audio + text + timing
- **syncable** - Has audio + text (no timing)
- **text-only** - Has text only
- **audio-only** - Has audio only
- **incomplete-timecode** - Has timing but missing audio or text

## Book Specifications

### Book Codes

**Old Testament**: GEN, EXO, LEV, NUM, DEU, JOS, JDG, RUT, 1SA, 2SA, 1KI, 2KI, 1CH, 2CH, EZR, NEH, EST, JOB, PSA, PRO, ECC, SNG, ISA, JER, LAM, EZK, DAN, HOS, JOL, AMO, OBA, JON, MIC, NAM, HAB, ZEP, HAG, ZEC, MAL

**New Testament**: MAT, MRK, LUK, JHN, ACT, ROM, 1CO, 2CO, GAL, EPH, PHP, COL, 1TH, 2TH, 1TI, 2TI, TIT, PHM, HEB, JAS, 1PE, 2PE, 1JN, 2JN, 3JN, JUD, REV

### Chapter Specifications

```bash
# Entire book
python3 download_language_content.py eng --books GEN

# Single chapter
python3 download_language_content.py eng --books GEN:1

# Chapter range
python3 download_language_content.py eng --books GEN:1-3

# Multiple chapters
python3 download_language_content.py eng --books PSA:1,23,91

# Multiple books
python3 download_language_content.py eng --books GEN:1-3,EXO:1-5,MAT:1-2
```

## Using Story Sets

Story sets let you define collections of passages in `config/story-set.conf`.

### Define a Story Set

Edit `config/story-set.conf`:

```
Creation_Story
GEN:1-3

Christmas_Story
LUK:1:26-56,LUK:2:1-40,MAT:2:1-23

Easter_Story
MAT:26-28,LUK:24,JHN:20
```

### Use Story Sets

```bash
# Download using story set name
python3 download_language_content.py eng --books Creation_Story

# Download multiple story sets
python3 download_language_content.py spa --books Creation_Story,Easter_Story

# Use predefined sets (from config/story-set.conf)
python3 download_language_content.py eng --books Test
python3 download_language_content.py fra --books "OBS Intro OT+NT"
```

## Batch Downloads

Download content for multiple languages automatically.

### Download by Content Quality

```bash
# All languages with New Testament timing data (audio + text + timing)
python3 download_language_content.py --book-set TIMING_NT --books MAT:1-7

# All languages with Old Testament timing data
python3 download_language_content.py --book-set TIMING_OT --books GEN:1-3

# All languages with New Testament audio+text sync (no timing)
python3 download_language_content.py --book-set SYNC_NT --books JHN

# All languages with Old Testament audio+text sync
python3 download_language_content.py --book-set SYNC_OT --books PSA:23

# All languages with any New Testament or Old Testament content
python3 download_language_content.py --book-set ALL --books MAT:5-7

# All languages with only partial content
python3 download_language_content.py --book-set PARTIAL --books JON
```

### Book-Set Options

- **TIMING_NT** - Languages with NT audio + text + timing 
- **TIMING_OT** - Languages with OT audio + text + timing
- **SYNC_NT** - Languages with NT audio + text (syncable, no timing)
- **SYNC_OT** - Languages with OT audio + text (syncable, no timing)
- **ALL** - Languages with any NT or OT content
- **PARTIAL** - Languages with only partial/incomplete content

## Common Use Cases

### Use Case 1: Single Language, Specific Passages

```bash
# Download English - Creation story
python3 download_language_content.py eng --books GEN:1-3

# Download Spanish - Christmas story
python3 download_language_content.py spa --books LUK:2,MAT:2

# Download French - Easter story  
python3 download_language_content.py fra --books MAT:26-28,LUK:24
```

### Use Case 2: Content With Timing

```bash
# All languages with timing data for Sermon on the Mount
python3 download_language_content.py --book-set TIMING_NT --books MAT:5-7

# All languages with timing data for Psalms
python3 download_language_content.py --book-set TIMING_OT --books PSA:23,PSA:91
```

### Use Case 3: Audio + Text (No Timing Required)

```bash
# All languages with audio+text for Gospel of John
python3 download_language_content.py --book-set SYNC_NT --books JHN

# All languages with audio+text for Genesis
python3 download_language_content.py --book-set SYNC_OT --books GEN:1-11
```

### Use Case 4: Maximum Language Coverage

```bash
# Download from ALL available languages
python3 download_language_content.py --book-set ALL --books MAT:1-2

# This will attempt to download Matthew 1-2 for every language
# that has ANY New Testament content
```

### Use Case 5: Bible Story App Development

```bash
# Download key Bible stories with timing for app development
python3 download_language_content.py --book-set TIMING_NT --books "OBS Intro OT+NT"

# This gets creation story + gospel introduction with timing data
# in all languages that support it
```

## Advanced Options

### Force Re-download

```bash
# Re-download even if files already exist
python3 download_language_content.py eng --books GEN:1 --force
```

### Include Partial Content

```bash
# Include languages with incomplete content (single books, partial sets)
python3 download_language_content.py eng --books GEN --force-partial
```

### Combine Options

```bash
# Re-download with partial content allowed
python3 download_language_content.py eng --books GEN:1-50 --force --force-partial
```

## Checking Download Results

### View Downloaded Content

```bash
# List all downloaded languages
ls downloads/BB/*/

# List content for specific language
ls downloads/BB/*/*/eng/

# Count audio files downloaded
find downloads/BB -name "*.mp3" | wc -l

# Count text files downloaded
find downloads/BB -name "*.txt" | wc -l
```

### Check Error Logs

Download errors are logged in `download_log/`:

```bash
# List error logs
ls download_log/

# View specific language errors
cat download_log/nt/eng/nt-eng-error.json | python3 -m json.tool

# Count languages with errors
ls download_log/*/* | wc -l
```

Common errors:
- **no_audio_available** - API doesn't have audio for this chapter
- **no_text_available** - API doesn't have text for this chapter
- **no_timing_available** - API doesn't have timing for this chapter
- **download_failed** - Network or API error (rare)

Most errors are "content not available" (not in API), not actual failures.

## Exporting Data

After downloading, you can export organized metadata:

```bash
python3 export_story_data.py
```

This creates `export/` directory with JSON metadata files organized by:
- Canon (NT/OT/PARTIAL)
- Category (with-timecode, syncable, etc.)
- Language
- Bible version

## Updating Content

To get the latest Bible versions:

```bash
# Re-fetch catalog from API
python3 fetch_api_cache.py

# Re-organize metadata
python3 sort_cache_data.py

# Re-download content
python3 download_language_content.py eng --books GEN:1 --force
```

## Troubleshooting

### Problem: "BIBLE_API_KEY not set"

**Solution**: Create `.env` file or set environment variable:
```bash
echo "BIBLE_API_KEY=your-key-here" > .env
```

### Problem: "sorted directory not found"

**Solution**: Run the setup steps:
```bash
python3 fetch_api_cache.py
python3 sort_cache_data.py
```

### Problem: No content downloaded

**Possible causes**:
1. Language doesn't have the requested book
2. API doesn't have content for that language+book combination
3. Story set name is misspelled

**Solution**: Check metadata:
```bash
# Check if language has any content
ls sorted/BB/nt/*eng* 2>/dev/null || echo "No NT content"
ls sorted/BB/ot/*eng* 2>/dev/null || echo "No OT content"

# Check error logs
cat download_log/nt/eng/nt-eng-error.json 2>/dev/null | python3 -m json.tool
```

### Problem: Story set not found

**Solution**: Check spelling in `config/story-set.conf`:
```bash
# View available story sets
grep -v '^#' config/story-set.conf | grep -v '^$' | grep -v '^[A-Z]'
```

Story set names are case-sensitive and must match exactly.

### Problem: Script hangs or takes too long

**Cause**: `--book-set ALL` tries to process 2000+ languages

**Solution**: Use more specific book-sets:
- Use `TIMING_NT` or `SYNC_NT` for smaller language sets
- Or download specific languages individually

## Language Codes

To find language codes:

```bash
# List all available languages (after running sort_cache_data.py)
ls sorted/BB/*/

# Search for specific language
ls sorted/BB/*/ | grep -i swahili

# Count available languages
ls sorted/BB/*/ | wc -l
```

Common language codes:
- **eng** - English
- **spa** - Spanish
- **fra** - French
- **por** - Portuguese
- **deu** - German
- **cmn** - Mandarin Chinese
- **arb** - Arabic
- **hin** - Hindi
- **ben** - Bengali
- **rus** - Russian
- **swa** - Swahili
- **ind** - Indonesian

Full list: [ISO 639-3](https://iso639-3.sil.org/code_tables/639/data)

## Quick Reference

```bash
# Setup (once)
python3 fetch_api_cache.py
python3 sort_cache_data.py

# Single language
python3 download_language_content.py <iso> --books <book-spec>

# Multiple languages (by quality)
python3 download_language_content.py --book-set <set> --books <book-spec>

# Re-download
python3 download_language_content.py <iso> --books <book-spec> --force

# Export metadata
python3 export_story_data.py

# Check errors
cat download_log/<canon>/<iso>/<canon>-<iso>-error.json
```

## Next Steps

- Review [README.md](README.md) for complete documentation
- Explore example story sets in `config/story-set.conf`
- Check `sorted/BB/` for available languages
- View error logs in `download_log/` for troubleshooting

## Need Help?

1. Check error logs: `download_log/<canon>/<iso>/`
2. Verify API key is set: `echo $BIBLE_API_KEY`
3. Verify metadata exists: `ls sorted/BB/`
4. Run help: `python3 download_language_content.py --help`

Happy Bible Story building! 🎉
