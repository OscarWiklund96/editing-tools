#!/usr/bin/env bash
set -e
echo "Building editing-tools for macOS..."
pyinstaller --onefile --windowed --name "Editing Tools" src/main.py
echo "Done! Find the app in dist/"
