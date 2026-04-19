"""Check spelling using pyspellchecker (en/de/fr/es/etc) and spylls for Swedish.

Swedish (sv) uses spylls with bundled LibreOffice Hunspell dictionaries.
Other languages use pyspellchecker.
"""

import os
import re
import sys

from .models import Finding

PYSPELLCHECKER_LANGUAGES = {"en", "es", "fr", "it", "pt", "de", "ru"}

MAX_SUGGESTION_WORDS = 50


def _get_sv_dictionary():
    """Load the Swedish spylls dictionary from bundled files."""
    from spylls.hunspell import Dictionary

    # Support PyInstaller bundle
    if hasattr(sys, "_MEIPASS"):
        base = os.path.join(sys._MEIPASS, "dicts", "sv_SE")
    else:
        base = os.path.join(os.path.dirname(__file__), "..", "..", "dicts", "sv_SE")

    path = os.path.join(base, "sv_SE")
    return Dictionary.from_files(path)


def check(
    text: str, lang: str = "sv", progress_callback=None, status_callback=None
) -> dict:
    """Return a dict with grouped misspellings and a full findings list."""
    use_spylls = lang == "sv"

    if not use_spylls and lang not in PYSPELLCHECKER_LANGUAGES:
        supported = ", ".join(sorted(PYSPELLCHECKER_LANGUAGES | {"sv"}))
        raise ValueError(
            f"Unsupported language: '{lang}'. Supported languages are: {supported}"
        )

    if use_spylls:
        dictionary = _get_sv_dictionary()
    else:
        from spellchecker import SpellChecker

        spell = SpellChecker(language=lang)

    lines = text.splitlines()
    total_lines = len(lines)

    # ------------------------------------------------------------------
    # Pass 1: Fast scan — lookups only, collect misspelled occurrences
    # ------------------------------------------------------------------
    if status_callback:
        status_callback("Kontrollerar stavning...")

    lookup_cache: dict[str, bool] = {}
    # Each entry: (line_number, col, word, excerpt)
    misspelled_occurrences: list[tuple[int, int, str, str]] = []

    for line_number, line in enumerate(lines, start=1):
        if progress_callback and line_number % 10 == 0:
            progress_callback(line_number / total_lines * 0.8)

        tokens = re.finditer(r"[A-Za-zÀ-öø-ÿåäöÅÄÖ]+(?:'[A-Za-zÀ-öø-ÿåäöÅÄÖ]+)*", line)

        for match in tokens:
            word = match.group()
            col = match.start() + 1

            if len(word) == 1:
                continue
            if word.isupper():
                continue

            # Check cache (try lowercase key)
            cache_key = word.lower()
            if cache_key in lookup_cache:
                is_correct = lookup_cache[cache_key]
            else:
                if use_spylls:
                    # Try original case first, then lowercase
                    is_correct = dictionary.lookup(word) or (
                        word != cache_key and dictionary.lookup(cache_key)
                    )
                else:
                    is_correct = not spell.unknown([word])
                lookup_cache[cache_key] = is_correct

            if is_correct:
                continue

            # Build excerpt
            start = max(0, col - 1 - 30)
            end = min(len(line), col - 1 + len(word) + 30)
            excerpt = line[start:end].strip()

            misspelled_occurrences.append((line_number, col, word, excerpt))

    if progress_callback:
        progress_callback(0.8)

    # ------------------------------------------------------------------
    # Pass 2: Generate suggestions for unique misspelled words
    # ------------------------------------------------------------------
    if status_callback:
        status_callback("Genererar förslag...")

    unique_words = list({w.lower() for _, _, w, _ in misspelled_occurrences})
    suggestions_cache: dict[str, list[str]] = {}

    capped = unique_words[:MAX_SUGGESTION_WORDS]
    total_unique = len(capped)

    for i, uword in enumerate(capped):
        if progress_callback and total_unique > 0:
            progress_callback(0.8 + (i / total_unique) * 0.2)

        if use_spylls:
            suggestions_cache[uword] = list(dictionary.suggest(uword))[:3]
        else:
            candidates = spell.candidates(uword)
            suggestions_cache[uword] = sorted(candidates)[:3] if candidates else []

    # Words beyond the cap get no suggestions
    for uword in unique_words[MAX_SUGGESTION_WORDS:]:
        suggestions_cache[uword] = []

    if progress_callback:
        progress_callback(1.0)

    # ------------------------------------------------------------------
    # Pass 3: Build grouped list and findings from occurrences
    # ------------------------------------------------------------------
    from collections import defaultdict

    grouped_map: dict[str, dict] = {}
    order: dict[str, int] = {}

    for line_number, col, word, excerpt in misspelled_occurrences:
        key = word.lower()
        if key not in grouped_map:
            grouped_map[key] = {
                "word": key,
                "count": 0,
                "suggestions": suggestions_cache.get(key, []),
                "lines": [],
            }
            order[key] = len(order)
        grouped_map[key]["count"] += 1
        grouped_map[key]["lines"].append(line_number)

    grouped = sorted(grouped_map.values(), key=lambda g: g["count"], reverse=True)

    findings: list[Finding] = []

    for line_number, col, word, excerpt in misspelled_occurrences:
        suggestions = suggestions_cache.get(word.lower(), [])
        if suggestions:
            top_suggestions = ", ".join(suggestions)
            description = f"Okänt ord: '{word}'. Förslag: {top_suggestions}"
        else:
            description = f"Okänt ord: '{word}'. Inga förslag."

        findings.append(
            Finding(
                tool="spell_checker",
                line_number=line_number,
                column=col,
                description=description,
                excerpt=excerpt,
            )
        )

    return {"grouped": grouped, "findings": findings}
