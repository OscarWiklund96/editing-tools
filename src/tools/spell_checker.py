"""Check spelling using pyspellchecker. Defaults to Swedish."""

import re
from spellchecker import SpellChecker
from .models import Finding

SUPPORTED_LANGUAGES = {"sv", "en"}


def check(text: str, lang: str = "sv") -> list[Finding]:
    """Return a list of Finding objects for misspelled words in the given text."""
    if lang not in SUPPORTED_LANGUAGES:
        supported = ", ".join(sorted(SUPPORTED_LANGUAGES))
        raise ValueError(
            f"Unsupported language: '{lang}'. Supported languages are: {supported}"
        )

    spell = SpellChecker(language=lang)
    findings: list[Finding] = []

    lines = text.splitlines()

    for line_number, line in enumerate(lines, start=1):
        # Tokenize: match words including internal apostrophes (e.g. "don't")
        tokens = re.finditer(r"[A-Za-zÀ-öø-ÿ]+(?:'[A-Za-zÀ-öø-ÿ]+)*", line)

        for match in tokens:
            word = match.group()
            col = match.start() + 1  # 1-indexed

            # Skip single characters
            if len(word) == 1:
                continue

            # Skip ALL CAPS (likely acronyms)
            if word.isupper():
                continue

            misspelled = spell.unknown([word])
            if not misspelled:
                continue

            # Build excerpt (~60 chars centred on the word)
            start = max(0, col - 1 - 30)
            end = min(len(line), col - 1 + len(word) + 30)
            excerpt = line[start:end].strip()

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
