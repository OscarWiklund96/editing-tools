# Editing Tools

A macOS desktop application for proofreading and analyzing Swedish text documents. Built with Python and tkinter — runs entirely offline, no API keys needed.

## Features

### Språk & grammatik
- **Stavningskontroll** — Swedish spell-checking (via spylls) + English, German, French, Spanish (via pyspellchecker)
- **Typografiska fel** — detects double spaces, repeated words, and other common typos
- **Konsistenskontroll** — flags inconsistent spelling/formatting choices within a document
- **Dialogkontroll** — checks dialogue punctuation and formatting

### Struktur & formatering
- **Radbrytningar** — finds inconsistent or excessive line breaks
- **Meningslängd** — flags sentences that are too long or too short, with histogram and stats
- **Kapitelbalans** — compares chapter lengths and flags outliers
- **Rubrikhierarki** — validates heading levels (no skipped levels)

### Analys
- **Ordfrekvens** — word frequency analysis with sorting and filtering options
- **Upprepningsdetektor** — detects repeated words/phrases in close proximity
- **Sidreferenser** — checks page references for consistency

## Supported File Formats

- PDF
- DOCX
- TXT

## Installation

Requires Python 3.13.

```bash
brew install python-tk@3.13
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run from the project root:

```bash
python -m src.main
```

## Building

Build a standalone macOS `.app` bundle:

```bash
bash build.sh
# or
bash build_spec.sh
```

The built app appears in the `dist/` directory.

## Export

Results can be exported as:
- **TXT** — plain text report
- **CSV** — structured data (findings, word frequencies, stats)
