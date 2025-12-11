#!/bin/bash
# Script to check for type errors in Python files

echo "======================================================================"
echo "Type Checking Script"
echo "======================================================================"
echo ""

# Check if basedpyright is available
if command -v basedpyright &> /dev/null; then
    echo "✅ Found basedpyright"
    echo ""
    echo "Checking fetch_api_cache.py..."
    basedpyright fetch_api_cache.py
    echo ""
    echo "Checking sort_cache_data.py..."
    basedpyright sort_cache_data.py
    echo ""
    echo "Checking download_language_content.py..."
    basedpyright download_language_content.py
    echo ""
    echo "Checking export_story_data.py..."
    basedpyright export_story_data.py
elif command -v pyright &> /dev/null; then
    echo "✅ Found pyright"
    echo ""
    echo "Checking fetch_api_cache.py..."
    pyright fetch_api_cache.py
    echo ""
    echo "Checking sort_cache_data.py..."
    pyright sort_cache_data.py
    echo ""
    echo "Checking download_language_content.py..."
    pyright download_language_content.py
    echo ""
    echo "Checking export_story_data.py..."
    pyright export_story_data.py
elif python3 -m mypy --version &> /dev/null; then
    echo "✅ Found mypy"
    echo ""
    echo "Checking fetch_api_cache.py..."
    python3 -m mypy fetch_api_cache.py --ignore-missing-imports
    echo ""
    echo "Checking sort_cache_data.py..."
    python3 -m mypy sort_cache_data.py --ignore-missing-imports
    echo ""
    echo "Checking download_language_content.py..."
    python3 -m mypy download_language_content.py --ignore-missing-imports
    echo ""
    echo "Checking export_story_data.py..."
    python3 -m mypy export_story_data.py --ignore-missing-imports
else
    echo "❌ No type checker found!"
    echo ""
    echo "Please install one of:"
    echo "  - basedpyright:  npm install -g basedpyright"
    echo "  - pyright:       npm install -g pyright"
    echo "  - mypy:          pip install mypy"
    echo ""
    echo "Running basic checks instead..."
    python3 -m py_compile fetch_api_cache.py && echo "✅ fetch_api_cache.py compiles"
    python3 -m py_compile sort_cache_data.py && echo "✅ sort_cache_data.py compiles"
    python3 -m py_compile download_language_content.py && echo "✅ download_language_content.py compiles"
    python3 -m py_compile export_story_data.py && echo "✅ export_story_data.py compiles"
fi

echo ""
echo "======================================================================"
echo "Done!"
echo "======================================================================"
