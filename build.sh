#!/usr/bin/env bash
set -e

echo "🔨 Building Editing Tools for macOS..."

# Clean previous builds
rm -rf build/ dist/

# Install dependencies if venv is active
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt --quiet
fi

pyinstaller \
    --onefile \
    --windowed \
    --name "Editing Tools" \
    --add-data "src:src" \
    src/main.py

echo ""
echo "✅ Build complete!"
echo "📁 App is at: dist/Editing Tools"
echo "   Double-click to run, or: open 'dist/Editing Tools'"
