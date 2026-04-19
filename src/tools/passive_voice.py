import re

from .models import Finding

S_EXCEPTIONS = {
    # Pronouns and determiners
    "hans",
    "hennes",
    "dess",
    "deras",
    "ens",
    "vars",
    # Adverbs
    "annars",
    "alltings",
    "allts",
    "knapps",
    "genast",
    "kanske",
    "alltjämt",
    "iblands",
    # Nouns commonly ending in -s
    "news",
    "kurs",
    "plus",
    "bus",
    "hus",
    "mus",
    "pris",
    "is",
    "os",
    "gas",
    "bas",
    "fas",
    "vers",
    "sons",
    "mars",
    "pers",
    "atlas",
    "campus",
    "fokus",
    "status",
    "virus",
    "bonus",
    "genus",
    "kaktus",
    "radius",
    "tempus",
    # Conjunctions / prepositions
    "sens",
    "dels",
    "tills",
    "alls",
    "bortses",
    # Common words
    "visst",
    "fors",
    "miss",
    "pass",
    "glass",
    "stress",
    "press",
    "process",
    "progress",
    "access",
    "success",
    "analysis",
    "basis",
    "crisis",
    "thesis",
    # Reflexive verbs (not passive, the -s is part of the verb)
    "finns",
    "hoppas",
    "andas",
    "trivs",
    "minns",
    "känns",
    "låts",
    "syns",
    "verkas",
    "lyckas",
    "misslyckas",
    "fattas",
    "saknas",
    "behövs",
    "krävs",
    "räcks",
    "tycks",
    "märks",
    "hörs",
    "ses",
}

# Past passive: -ades, -des, -tes
_RE_PAST_PASSIVE = re.compile(r"\b(\w+(?:ades|des|tes))\b", re.IGNORECASE)

# Supine passive: -ts (4+ chars)
_RE_SUPINE_PASSIVE = re.compile(r"\b(\w{4,}ts)\b", re.IGNORECASE)

# Present passive: -as (5+ chars)
_RE_AS_PASSIVE = re.compile(r"\b(\w{5,}as)\b", re.IGNORECASE)

# Bli-passive: bli/blir/blev/blivit/blivna + past participle
_RE_BLI_PASSIVE = re.compile(
    r"\b(bli|blir|blev|blivit|blivna)\s+(\w+(?:ad|at|d|t|en|na))\b",
    re.IGNORECASE,
)


def _is_exception(word: str) -> bool:
    """Return True if the word should not be flagged as passive."""
    lower = word.lower()
    if lower in S_EXCEPTIONS:
        return True
    # Skip very short words (3 chars or less)
    if len(lower) <= 3:
        return True
    # Skip all-caps (likely acronyms)
    if word.isupper():
        return True
    # Skip purely numeric strings
    if word.isdigit():
        return True
    return False


def _excerpt(line: str, start: int, end: int, max_len: int = 60) -> str:
    """Extract an excerpt around the match, max ~max_len characters."""
    pad = (max_len - (end - start)) // 2
    excerpt_start = max(0, start - pad)
    excerpt_end = min(len(line), end + pad)
    snippet = line[excerpt_start:excerpt_end].strip()
    if excerpt_start > 0:
        snippet = "..." + snippet
    if excerpt_end < len(line):
        snippet = snippet + "..."
    return snippet


def check(text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.split("\n")

    for line_idx, line in enumerate(lines):
        line_number = line_idx + 1

        # --- S-passive: past tense (-ades, -des, -tes) ---
        for m in _RE_PAST_PASSIVE.finditer(line):
            word = m.group(1)
            if _is_exception(word):
                continue
            col = m.start(1) + 1
            findings.append(
                Finding(
                    tool="passive_voice",
                    line_number=line_number,
                    column=col,
                    description=f"Passiv form (s-passiv): '{word}'",
                    excerpt=_excerpt(line, m.start(), m.end()),
                )
            )

        # --- S-passive: supine (-ts) ---
        for m in _RE_SUPINE_PASSIVE.finditer(line):
            word = m.group(1)
            if _is_exception(word):
                continue
            # Avoid double-reporting words already caught by past pattern
            if _RE_PAST_PASSIVE.fullmatch(word):
                continue
            col = m.start(1) + 1
            findings.append(
                Finding(
                    tool="passive_voice",
                    line_number=line_number,
                    column=col,
                    description=f"Passiv form (s-passiv): '{word}'",
                    excerpt=_excerpt(line, m.start(), m.end()),
                )
            )

        # --- S-passive: present (-as, 5+ chars) ---
        for m in _RE_AS_PASSIVE.finditer(line):
            word = m.group(1)
            if _is_exception(word):
                continue
            # Avoid double-reporting words caught by past pattern
            if _RE_PAST_PASSIVE.fullmatch(word):
                continue
            col = m.start(1) + 1
            findings.append(
                Finding(
                    tool="passive_voice",
                    line_number=line_number,
                    column=col,
                    description=f"Passiv form (s-passiv): '{word}'",
                    excerpt=_excerpt(line, m.start(), m.end()),
                )
            )

        # --- Bli-passive ---
        for m in _RE_BLI_PASSIVE.finditer(line):
            full_match = m.group(0)
            col = m.start() + 1
            findings.append(
                Finding(
                    tool="passive_voice",
                    line_number=line_number,
                    column=col,
                    description=f"Passiv form (bli-passiv): '{full_match}'",
                    excerpt=_excerpt(line, m.start(), m.end()),
                )
            )

    return findings
