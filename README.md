# Bible Story Builder

Build multilingual Bible stories in minutes - perfect for literacy programs, oral storytelling, and translation projects.
- by downloading text, audio, and timing data from the Digital Bible Platform API.

## Highlights
- 🌍 2000+ languages supported
- 📖 Custom story definitions
- 🎵 Audio, text, and timing data
- 🗂️ Organized output structure
- 🔄 Multiple Bible versions per language
- 📱 Coming soon: Web app generation
- Active development (roadmap to v2.0)

### Target Audiences
1. **Bible translators** - Get content in multiple versions
2. **Literacy programs** - Simple stories for new readers
3. **Oral storytellers** - Narrative passages with audio
4. **Ministry leaders** - Multilingual teaching materials
5. **App developers** - Ready-to-use Bible content

## Overview

Bible Story Builder helps you create Bible stories in multiple languages by:
1. Defining which Bible passages make up your story
2. Selecting which languages you want
3. Downloading the content automatically
4. (Coming soon) Generating a ready-to-use web app

Perfect for Bible translation projects, literacy programs, oral Bible storytelling, and multilingual ministry.

## Quick Start

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

### 1. Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key environment variable
export DBP_API_KEY="your_key_here"
```

Get your API key from [https://www.biblebrain.com/](https://www.biblebrain.com/)

### 2. Define Your Story

Edit `config/story-set.conf` to define your Bible story:

```
Creation_Story
GEN:1-3,GEN:6-9

Jesus_Life
MAT:1-2,LUK:2:1-20,JHN:1:1-14
```

### 3. Define Your Languages

Edit `config/regions.conf` to specify which languages:

```
Africa
swa,yor,amh,som,hau

Asia
hin,ben,tam,tel,vie
```

### 4. Fetch and Build

```bash
# Fetch Bible catalog from API
python3 fetch_api_cache.py

# Organize metadata
python3 sort_cache_data.py

# Download your story in multiple languages
python3 download_language_content.py --region Africa --books Creation_Story
```

## Story Building Workflow

### Step 1: Define Story Content

Create story sets in `config/story-set.conf`:

```
# Old Testament Stories
OT_STORIES
GEN:1-11,EXO:1-20,JOS:1-6,JDG:6-7,RUT:1-4,1SA:16-17,2SA:11-12

# New Testament Stories  
NT_STORIES
MAT:1-2,MAT:5-7,MAT:26-28,LUK:2,LUK:15,JHN:1,JHN:3,JHN:11,ACT:1-2,ACT:9

# Creation to Christ
CREATION_TO_CHRIST
GEN:1-3,GEN:6-9,GEN:12,GEN:22,EXO:12,EXO:20,MAT:1-2,LUK:2,JHN:3,MAT:26-28,ACT:1-2

# Single book stories
RUTH_STORY
RUT:1-4

JONAH_STORY
JON:1-4
```

### Step 2: Define Target Languages

Create regions in `config/regions.conf`:

```
# Geographic regions
West_Africa
yor,hau,ibo,ewe,twi

East_Africa
swa,som,orm,amh,tir

# Language families
Bantu_Languages
swa,zul,xho,lin,lug

# Ministry focus
Primary_Languages
eng,spa,fra,por,ara,hin,zho
```

### Step 3: Download Story Content

```bash
# Download specific story for specific region
python3 download_language_content.py --region West_Africa --books Creation_Story

# Download multiple stories
python3 download_language_content.py --region East_Africa --books OT_STORIES,NT_STORIES

# Download for all languages in a region
python3 download_language_content.py --region Bantu_Languages --books CREATION_TO_CHRIST
```

### Step 4: Access Your Story Content

Content is organized by language and Bible version:

```
downloads/BB/{language}/{bible_version}/{book}/
├── {book}_{chapter}_{format}.mp3     # Audio
├── {book}_{chapter}_{format}.txt     # Text
└── {book}_{chapter}_{format}_timing.json  # Timing data
```

Example for Swahili Creation story:
```
downloads/BB/swa/SWAHAU/GEN/
├── GEN_001_SWAHAU2N2DA.mp3
├── GEN_001_SWAHAU2TP.txt
├── GEN_002_SWAHAU2N2DA.mp3
├── GEN_002_SWAHAU2TP.txt
└── ...
```

## Common Story Building Scenarios

### Scenario 1: Literacy Program
```bash
# Define simple stories for new readers
# config/story-set.conf:
Beginner_Stories
RUT:1-4,JON:1-4,PSA:23,PSA:117

# Download for your language
python3 download_language_content.py swa --books Beginner_Stories
```

### Scenario 2: Oral Bible Storytelling
```bash
# Focus on narrative passages
# config/story-set.conf:
Storytelling_Set
GEN:1-3,GEN:6-9,GEN:37-50,EXO:1-15,JOS:2,JDG:6-7,RUT:1-4,1SA:17

# Download audio for multiple languages
python3 download_language_content.py --region Africa --books Storytelling_Set
```

### Scenario 3: Jesus Film Project
```bash
# Gospel stories with audio and timing for video sync
# config/story-set.conf:
Jesus_Film
MAT:1-2,LUK:1-2,JHN:1-3,MAT:5-7,LUK:15,JHN:11,MAT:26-28,LUK:24,ACT:1-2

# Download with timing data
python3 download_language_content.py --book-set TIMING_NT --books Jesus_Film
```

### Scenario 4: Multi-language Bible App
```bash
# Full Bible story arc for app
python3 download_language_content.py --region Primary_Languages --books CREATION_TO_CHRIST
```

## Output Structure

```
downloads/BB/
└── {language_iso}/
    └── {bible_version}/
        └── {book}/
            ├── {book}_{chapter}_{fileset}.mp3
            ├── {book}_{chapter}_{fileset}.txt
            └── {book}_{chapter}_{fileset}_timing.json

sorted/BB/
├── {language}_language_info.json    # Language metadata
└── {language}_metadata.json         # Available Bible versions

download_log/
└── {language}_errors.json           # Error logs (if any)
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

Easter_Story  
MAT:26-27,LUK:24,JHN:20
```

### config/regions.conf

Define language groups:

```
Region_Name
iso,iso,iso

Example:
Southeast_Asia
vie,tha,mya,khm,lao

Pacific_Islands
fij,ton,smo,haw,mao
```

## Book Codes Reference

**Old Testament**: GEN, EXO, LEV, NUM, DEU, JOS, JDG, RUT, 1SA, 2SA, 1KI, 2KI, 1CH, 2CH, EZR, NEH, EST, JOB, PSA, PRO, ECC, SNG, ISA, JER, LAM, EZK, DAN, HOS, JOL, AMO, OBA, JON, MIC, NAM, HAB, ZEP, HAG, ZEC, MAL

**New Testament**: MAT, MRK, LUK, JHN, ACT, ROM, 1CO, 2CO, GAL, EPH, PHP, COL, 1TH, 2TH, 1TI, 2TI, TIT, PHM, HEB, JAS, 1PE, 2PE, 1JN, 2JN, 3JN, JUD, REV

## Advanced Features

### Filter by Bible Version Quality

```bash
# Only languages with audio+text synchronization
python3 download_language_content.py --book-set SYNC_NT --region Africa --books Jesus_Film

# Only languages with timing data (for audio sync)
python3 download_language_content.py --book-set TIMING_FULL --books Creation_Story
```

### Force Re-download

```bash
python3 download_language_content.py eng --books Creation_Story --force
```

### Batch Processing

Create a file with language codes (one per line):

```
# languages.txt
eng
spa
fra
por
```

Download:
```bash
python3 download_language_content.py --batch languages.txt --books Creation_Story
```

## Error Handling

Download errors are logged with detailed information in `download_log/{language}_errors.json`.

View errors:
```bash
# Check specific language
cat download_log/eng_errors.json | python3 -m json.tool

# Count languages with errors
ls download_log/*_errors.json | wc -l

# Search for specific error types
grep -r "audio_download_failed" download_log/
```

Most errors are "content not available" (API doesn't have the content), not download failures.

See [ERROR_LOGGING_QUICKREF.md](ERROR_LOGGING_QUICKREF.md) for details.

## Roadmap

### Coming Soon: Web App Generation

Bible Story Builder will generate ready-to-use web apps from your stories:

- **Template-based**: Define layout in markdown templates
- **Multilingual**: Automatic language switching
- **Audio sync**: Text highlights as audio plays
- **Responsive**: Works on phones, tablets, and desktops
- **Offline-capable**: Progressive Web App support

See [ROADMAP.md](ROADMAP.md) for details.

## Troubleshooting

### No content downloaded
- Verify API key is set correctly
- Check that language has available content in metadata
- Check story set and region names match configuration files

### Download errors
- Check `download_log/{iso}_errors.json` for details
- Most errors are "content not available" (API limitation)
- Actual download failures are rare (< 1%)

### Missing story set or region
- Verify names in config files match exactly
- Story set names are case-sensitive
- Region names can have spaces or underscores

### Need fresh data
```bash
# Re-fetch API catalog
python3 fetch_api_cache.py

# Re-organize metadata
python3 sort_cache_data.py
```

## Documentation

- [QUICKSTART.md](QUICKSTART.md) - Getting started guide
- [ERROR_LOGGING_QUICKREF.md](ERROR_LOGGING_QUICKREF.md) - Error logging reference
- [ROADMAP.md](ROADMAP.md) - Future features and plans

## Requirements

- Python 3.7+
- `requests>=2.31.0`
- `python-dotenv>=1.0.0`
- Digital Bible Platform API key (get from [BibleBrain.com](https://www.biblebrain.com/))

Install:
```bash
pip install -r requirements.txt
```

## Project Statistics

- **Languages**: 2000+
- **Bible Versions**: 12,000+ filesets
- **Audio Formats**: MP3, Opus
- **Text Formats**: Plain text, USX, JSON
- **Success Rate**: 99.4%
- **License**: MIT

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Credits

Bible content from [Digital Bible Platform](https://www.biblebrain.com/) / Faith Comes By Hearing.

## Support

For issues, questions, or contributions, please visit the GitHub repository.
