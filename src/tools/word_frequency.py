"""Analyze word frequency distribution in text."""

import re
from collections import Counter

SWEDISH_STOP_WORDS = {
    "och",
    "att",
    "det",
    "är",
    "en",
    "ett",
    "på",
    "av",
    "för",
    "med",
    "som",
    "till",
    "han",
    "hon",
    "de",
    "vi",
    "men",
    "om",
    "så",
    "kan",
    "har",
    "inte",
    "var",
    "sig",
    "denna",
    "dessa",
    "den",
    "när",
    "där",
    "eller",
}

ENGLISH_STOP_WORDS = {
    "the",
    "and",
    "to",
    "of",
    "a",
    "in",
    "is",
    "it",
    "that",
    "was",
    "he",
    "she",
    "they",
    "we",
    "but",
    "for",
    "with",
    "as",
    "at",
    "be",
    "this",
    "have",
    "from",
    "or",
    "not",
}

STOP_WORDS = SWEDISH_STOP_WORDS | ENGLISH_STOP_WORDS


def analyze(text: str) -> dict:
    """Return a dict with word frequency statistics for the given text."""
    # Normalize to lowercase and strip punctuation
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    tokens = cleaned.split()

    # Filter: minimum 2 chars, not purely numeric, not a stop word
    words = [
        w for w in tokens if len(w) >= 2 and not w.isdigit() and w not in STOP_WORDS
    ]

    total_words = len(words)
    counter = Counter(words)
    unique_words = len(counter)
    top_words = counter.most_common()
    avg_word_length = (
        sum(len(w) for w in words) / total_words if total_words > 0 else 0.0
    )

    return {
        "total_words": total_words,
        "unique_words": unique_words,
        "top_words": top_words,
        "avg_word_length": round(avg_word_length, 2),
    }
