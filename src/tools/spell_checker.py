"""Check spelling using pyspellchecker (en/de/fr/es/etc) and spylls for Swedish.

Swedish (sv) uses spylls with bundled LibreOffice Hunspell dictionaries.
Other languages use pyspellchecker.
"""

import os
import re
import sys

from .models import Finding

PYSPELLCHECKER_LANGUAGES = {"en", "es", "fr", "it", "pt", "de", "ru"}


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


def check(text: str, lang: str = "sv") -> list[Finding]:
    """Return a list of Finding objects for misspelled words in the given text."""
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

    findings: list[Finding] = []
    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        tokens = re.finditer(r"[A-Za-zÀ-öø-ÿåäöÅÄÖ]+(?:'[A-Za-zÀ-öø-ÿåäöÅÄÖ]+)*", line)

        for match in tokens:
            word = match.group()
            col = match.start() + 1

            if len(word) == 1:
                continue
            if word.isupper():
                continue

            if use_spylls:
                if dictionary.lookup(word):
                    continue
            else:
                if not spell.unknown([word]):
                    continue

            # Build excerpt
            start = max(0, col - 1 - 30)
            end = min(len(line), col - 1 + len(word) + 30)
            excerpt = line[start:end].strip()

            if use_spylls:
                suggestions = list(dictionary.suggest(word))[:3]
                if suggestions:
                    top_suggestions = ", ".join(suggestions)
                    description = f"Okänt ord: '{word}'. Förslag: {top_suggestions}"
                else:
                    description = f"Okänt ord: '{word}'. Inga förslag."
            else:
                candidates = spell.candidates(word)
                if candidates:
                    top_suggestions = ", ".join(sorted(candidates)[:3])
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

    return findings
