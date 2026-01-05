# Bible Story Builder

Download Bible text, audio, and timing data from the Digital Bible Platform API - organized and ready to use.

## What It Does

Bible Story Builder downloads Bible content in 2000+ languages from the [Digital Bible Platform](https://www.biblebrain.com/):
- 📖 **Text** - Bible text in multiple formats
- 🎵 **Audio** - Narrated Bible passages
- ⏱️ **Timing** - Word-by-word synchronization data
- 🗂️ **Organized** - Automatically categorized by quality and canon

Perfect for:
- Bible translation projects
- Literacy programs  
- Oral Bible storytelling
- Multilingual ministry
- Bible app development

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

### 1. Install

```bash
pip install -r requirements.txt
```

Get your free API key from [BibleBrain.com](https://www.biblebrain.com/)

### 2. Configure

Create `.env` file:
```
BIBLE_API_KEY=your-api-key-here
```

### 3. Setup (First Time Only)

```bash
# Fetch Bible catalog from API (2-5 minutes)
python3 fetch_api_cache.py

# Organize metadata (1-2 minutes)
python3 sort_cache_data.py
```

### 4. Download Content

```bash
# Download specific language
python3 download_language_content.py eng --books GEN:1-3

# Download from all languages with timing data
python3 download_language_content.py --book-set TIMING_NT --books MAT:1-7
```

## How It Works

### Three Simple Scripts

1. **fetch_api_cache.py** - Download Bible catalog from API
2. **sort_cache_data.py** - Organize by language and canon
3. **download_language_content.py** - Download Bible content

Optional:
4. **export_story_data.py** - Export organized metadata and data files

### Canonical Structure

Content is organized by:
- **Canon**: NT (New Testament), OT (Old Testament), PARTIAL
- **Category**: with-timecode, syncable, text-only, audio-only, etc.
- **Language**: ISO 639-3 codes (eng, spa, fra, etc.)
- **Version**: 6-letter Bible version identifier

### Output Structure

```
downloads/BB/
└── {canon}/              # nt, ot, or partial
    └── {category}/       # with-timecode, syncable, etc.
        └── {iso}/        # Language code (eng, spa, etc.)
            └── {id}/     # 6-letter version ID
                └── {BOOK}/
                    ├── {BOOK}_001_{ID}.mp3
                    ├── {BOOK}_001_{ID}.txt
                    └── {BOOK}_001_{ID}_timing.json
```

## Usage

### Single Language Downloads

```bash
# Download English - Genesis 1-3
python3 download_language_content.py eng --books GEN:1-3

# Download Spanish - Psalm 23
python3 download_language_content.py spa --books PSA:23

# Download Swahili - Gospel of John
python3 download_language_content.py swa --books JHN

# Download French - Multiple books
python3 download_language_content.py fra --books GEN:1-3,EXO:1-5,MAT:1-7
```

### Batch Downloads by Quality

```bash
# All languages with NT timing data (audio + text + timing)
python3 download_language_content.py --book-set TIMING_NT --books MAT:5-7

# All languages with OT timing data
python3 download_language_content.py --book-set TIMING_OT --books GEN:1-3

# All languages with NT audio+text sync (no timing required)
python3 download_language_content.py --book-set SYNC_NT --books JHN

# All languages with OT audio+text sync
python3 download_language_content.py --book-set SYNC_OT --books PSA:23

# All languages with any NT or OT content
python3 download_language_content.py --book-set ALL --books MAT:1-2

# All languages with only partial content
python3 download_language_content.py --book-set PARTIAL --books JON
```

### Book-Set Options

- **TIMING_NT** - Languages with NT audio + text + timing 
- **TIMING_OT** - Languages with OT audio + text + timing
- **SYNC_NT** - Languages with NT audio + text (no timing)
- **SYNC_OT** - Languages with OT audio + text (no timing)
- **ALL** - Languages with any NT or OT content
- **PARTIAL** - Languages with only partial/incomplete content

### Using Story Sets

Define reusable story collections in `config/story-set.conf`:

```
Creation_Story
GEN:1-3

Christmas_Story
LUK:1:26-56,LUK:2:1-40,MAT:2:1-23

Easter_Story
MAT:26-28,LUK:24,JHN:20
```

Then use them:

```bash
python3 download_language_content.py eng --books Creation_Story
python3 download_language_content.py --book-set TIMING_NT --books Easter_Story
```

## Book Specifications

### Book Codes

**Old Testament**: GEN, EXO, LEV, NUM, DEU, JOS, JDG, RUT, 1SA, 2SA, 1KI, 2KI, 1CH, 2CH, EZR, NEH, EST, JOB, PSA, PRO, ECC, SNG, ISA, JER, LAM, EZK, DAN, HOS, JOL, AMO, OBA, JON, MIC, NAM, HAB, ZEP, HAG, ZEC, MAL

**New Testament**: MAT, MRK, LUK, JHN, ACT, ROM, 1CO, 2CO, GAL, EPH, PHP, COL, 1TH, 2TH, 1TI, 2TI, TIT, PHM, HEB, JAS, 1PE, 2PE, 1JN, 2JN, 3JN, JUD, REV

### Chapter Formats

```bash
# Entire book
--books GEN

# Single chapter
--books GEN:1

# Chapter range
--books GEN:1-3

# Multiple chapters
--books PSA:1,23,91

# Multiple books
--books GEN:1-3,EXO:1-5,MAT:1-2
```

## Content Categories

Downloaded content is automatically categorized:

- **with-timecode** - Has audio + text + timing data 
- **syncable** - Has audio + text (can be synced, no timing)
- **text-only** - Has text only
- **audio-only** - Has audio only
- **incomplete-timecode** - Has timing but missing audio or text

## Command Reference

```bash
# Single language
python3 download_language_content.py <iso> --books <book-spec>

# Batch by quality
python3 download_language_content.py --book-set <set> --books <book-spec>

# Force re-download
python3 download_language_content.py <iso> --books <book-spec> --force

# Include partial content
python3 download_language_content.py <iso> --books <book-spec> --force-partial

# Export metadata
python3 export_story_data.py
```

## Error Handling

Download errors are logged in `download_log/`:

```bash
# View errors for specific language
cat download_log/nt/eng/nt-eng-error.json | python3 -m json.tool

# Count languages with errors
ls download_log/*/* | wc -l
```

Common error types:
- **no_audio_available** - API doesn't have audio for this chapter
- **no_text_available** - API doesn't have text for this chapter
- **no_timing_available** - API doesn't have timing for this chapter
- **download_failed** - Network or API error (rare, < 1%)

Most errors are "content not available" (not in API), not actual download failures.

## Finding Languages

```bash
# List all available languages (after running sort_cache_data.py)
ls sorted/BB/nt/
ls sorted/BB/ot/

# Count available languages
ls sorted/BB/*/ | wc -l

# Check if specific language has content
ls sorted/BB/*/swa* 2>/dev/null || echo "Not found"
```

Common language codes:
- **eng** (English), **spa** (Spanish), **fra** (French), **por** (Portuguese)
- **deu** (German), **rus** (Russian), **cmn** (Mandarin Chinese), **arb** (Arabic)
- **hin** (Hindi), **ben** (Bengali), **swa** (Swahili), **ind** (Indonesian)

Full list: [ISO 639-3 Language Codes](https://iso639-3.sil.org/)

## Use Cases

### Literacy Programs

```bash
# Simple stories for new readers
python3 download_language_content.py swa --books RUT,JON,PSA:23
```

### Oral Storytelling

```bash
# Get audio for narrative passages
python3 download_language_content.py --book-set SYNC_NT --books MAT:1-2,LUK:2
```

### Bible App Development

```bash
# Content with timing for all languages
python3 download_language_content.py --book-set TIMING_NT --books JHN:1-3
```

### Translation Projects

```bash
# Compare multiple versions in same language
python3 download_language_content.py eng --books GEN:1 --force

# Get timing data for gospel stories
python3 download_language_content.py --book-set TIMING_NT --books MAT:26-28,LUK:24
```

## Exported Data

After downloading, run `export_story_data.py` to generate organized metadata:

```bash
python3 export_story_data.py
```

### Export Structure

```
export/
├── ALL-langs.json              # 147 KB - Human-readable summary
├── ALL-langs-compact.json      #  72 KB - Compact summary with names
├── ALL-langs-mini.json         #  12 KB - ISO codes only (compact)
├── ALL-langs-data.zip          # 413 KB - Complete data archive
│
├── regions.json                #  29 KB - Region metadata (readable)
├── regions.zip                 # 4.8 KB - Region metadata (compact)
│
├── ALL-langs/                  # 2,365 data.json files
│   ├── nt/{category}/{iso}/{id}/data.json
│   └── ot/{category}/{iso}/{id}/data.json
│
└── regions/                    # 147 region-specific zip files
    ├── Afghanistan.zip
    ├── Albania.zip
    └── ...
```

### Summary Files

**ALL-langs.json** - Pretty-printed summary with language names:
```json
{
  "metadata": {
    "generated_at": "2026-01-05T...",
    "total_languages": 1720
  },
  "canons": {
    "nt": {
      "with-timecode": {
        "eng": {
          "n": "English"
        }
      }
    }
  }
}
```

**ALL-langs-compact.json** - Compact version with names (51% smaller):
```json
{"metadata":{"generated_at":"...","total_languages":1720},"canons":{"nt":{"with-timecode":{"eng":{"n":"English"}}}}}
```

**ALL-langs-mini.json** - Minimal version with ISO codes only (91% smaller):
```json
{"metadata":{"generated_at":"...","total_languages":1720},"canons":{"nt":{"with-timecode":["eng","spa","fra"]}}}
```

### Data Files

**data.json** - Optimized per-language data:
```json
{
  "a": "N1DA.mp3",
  "t": "N_ET.txt"
}
```

Format:
- `"a"` - Audio file (stripped fileset ID + extension)
- `"t"` - Text file (stripped fileset ID + extension)
- Keys omitted if no data available
- Fileset ID prefix removed (distinct_id is in path)

### Region Files

**regions.json** - Region metadata:
```json
{
  "Afghanistan": {
    "l": ["bal", "bgp", "prs", "pbu"],
    "trade": ["prs", "pbu"],
    "regional": ["uzn", "tuk"]
  }
}
```

Format:
- `"l"` - Languages (ISO codes)
- Optional: `"trade"`, `"regional"`, `"educational"`, `"literacy"`

### Archives

**ALL-langs-data.zip** - Complete data archive:
- Contains all `data.json` files
- Includes `summary.json` (compact)
- Only includes: `nt/`, `ot/` folders
- Excludes: `failed/` category

**regions.zip** - Region metadata (compact):
- Same structure as `regions.json`
- Compact format (no whitespace)

**Region-specific zips** (in `regions/` directory):
- Filtered subsets of `ALL-langs-data.zip`
- One zip per region (147 total)
- Contains only languages for that region

## Project Statistics

- **Languages**: 2000+
- **Bible Versions**: 12,000+ filesets
- **Audio Formats**: MP3, Opus
- **Text Formats**: Plain text, USX, JSON
- **Timing**: Verse-level synchronization
- **Exported Files**: 2,365+ optimized data.json files
- **Export Size**: ~413 KB (compressed)

## Requirements

- Python 3.7+
- `requests>=2.31.0`
- `python-dotenv>=1.0.0`
- Digital Bible Platform API key

Install:
```bash
pip install -r requirements.txt
```

## Configuration Files

### config/story-set.conf

Define reusable story collections:

```
Story_Name
BOOK:CHAPTERS,BOOK:CHAPTERS

Example:
Christmas_Story
LUK:1:26-56,LUK:2:1-40,MAT:2:1-23
```

Multiple lines are concatenated:
```
OT_Stories
GEN:1-3,GEN:6-9
EXO:1-15
```

### .env

API key configuration:

```
BIBLE_API_KEY=your-api-key-here
```

## Directory Structure

```
bible-story-builder/
├── fetch_api_cache.py          # Fetch Bible catalog from API
├── sort_cache_data.py          # Organize metadata
├── download_language_content.py # Download Bible content
├── export_story_data.py        # Export metadata JSON
├── requirements.txt            # Python dependencies
├── .env                        # API key (create this)
├── config/
│   └── story-set.conf         # Story definitions
├── api-cache/                 # API cache (generated)
├── sorted/                    # Organized metadata (generated)
├── downloads/                 # Downloaded content (generated)
├── download_log/              # Error logs (generated)
├── export/                    # Exported data & metadata (generated)
│   ├── ALL-langs.json
│   ├── ALL-langs-compact.json
│   ├── ALL-langs-mini.json
│   ├── ALL-langs-data.zip
│   ├── regions.json
│   ├── regions.zip
│   ├── ALL-langs/
│   └── regions/
└── workspace/                 # Compact workspace data (generated)
```

## Troubleshooting

### No content downloaded

**Check API key:**
```bash
echo $BIBLE_API_KEY
```

**Verify metadata exists:**
```bash
ls sorted/BB/nt/ | head
ls sorted/BB/ot/ | head
```

**Check error logs:**
```bash
cat download_log/nt/eng/nt-eng-error.json 2>/dev/null | python3 -m json.tool
```

### Missing metadata

**Re-run setup:**
```bash
python3 fetch_api_cache.py
python3 sort_cache_data.py
```

### Story set not found

**Check spelling in config file:**
```bash
grep -A1 "^Creation" config/story-set.conf
```

Story set names are case-sensitive.

### Script hangs with --book-set ALL

**Use more specific book-sets:**
- `TIMING_NT` or `SYNC_NT` process fewer languages
- Or download specific languages individually

## Updating Content

```bash
# Fetch latest Bible catalog
python3 fetch_api_cache.py

# Re-organize metadata
python3 sort_cache_data.py

# Re-download content
python3 download_language_content.py eng --books GEN:1 --force
```

## Type Checking

Run type checks with:

```bash
./check_types.sh
```

Requires `basedpyright`, `pyright`, or `mypy`.

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Step-by-step getting started guide
- [ROADMAP.md](ROADMAP.md) - Future features and development plans
- [config/story-set.conf](config/story-set.conf) - Example story definitions

## Credits

Bible content from [Digital Bible Platform](https://www.biblebrain.com/) / Faith Comes By Hearing.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For issues or questions, please visit the GitHub repository.
