# Editing Tools

A simple desktop app for proofreading and analyzing text documents (PDF, DOCX, TXT). Focused on Swedish with English support.

## Features

- **Typo checker** — detect double spaces, repeated words, and other common typos
- **Newline checker** — find inconsistent or excessive line breaks
- **Spell checker** — spell-check with Swedish as default language (English supported)
- **Word frequency analysis** — see which words appear most often in a document

## Supported Formats

- PDF
- DOCX
- TXT

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## Building

Build a standalone macOS app with PyInstaller:

```bash
./build.sh
```

## Usage

After building, double-click the app in `dist/` to launch.
