#!/usr/bin/env bash
set -e
echo "🔨 Building Editing Tools using spec file..."
rm -rf build/ dist/
pyinstaller editing_tools.spec
echo "✅ Done! App bundle at: dist/Editing Tools.app"
