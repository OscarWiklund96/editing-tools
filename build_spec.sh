#!/usr/bin/env bash
set -e
echo "🔨 Building Editing Tools using spec file..."
rm -rf build/ dist/

# Use venv python/pyinstaller
source .venv/bin/activate

pyinstaller editing_tools.spec
echo ""
echo "✅ Done!"
echo "📁 App bundle at: dist/Editing Tools.app"
echo "   To zip for sharing: cd dist && zip -r 'Editing Tools.zip' 'Editing Tools.app'"
