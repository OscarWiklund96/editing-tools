import re
from collections import Counter

from .models import Finding

TOOL_NAME = "repetition_detector"

ABBREVIATIONS = [
    "t.ex.",
    "bl.a.",
    "dvs.",
    "osv.",
    "m.m.",
    "m.fl.",
    "d.v.s.",
    "f.d.",
    "s.k.",
    "kl.",
    "nr.",
    "ca.",
    "st.",
    "resp.",
    "etc.",
    "fig.",
    "tab.",
    "jfr.",
    "obs.",
    "Dr.",
    "Prof.",
]


# ---------------------------------------------------------------------------
# Trigram similarity helpers
# ---------------------------------------------------------------------------


def _trigrams(s: str) -> set[str]:
    """Generate character trigrams from a string."""
    s = s.lower().strip()
    if len(s) < 3:
        return {s}
    return {s[i : i + 3] for i in range(len(s) - 2)}


def _similarity(a: str, b: str) -> float:
    """Jaccard similarity between character trigrams of two strings."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# ---------------------------------------------------------------------------
# Sentence splitting (Swedish-aware, same approach as sentence_length)
# ---------------------------------------------------------------------------


def _make_placeholder(index: int) -> str:
    return f"\x00ABBR{index}\x00"


def _find_line_number(text: str, char_index: int) -> int:
    """Return 1-indexed line number for a character position."""
    return text[:char_index].count("\n") + 1


def _split_sentences(text: str) -> list[tuple[str, int]]:
    """Split text into sentences, returning (sentence, line_number) pairs."""
    if not text or not text.strip():
        return []

    processed = text
    abbr_map: dict[str, str] = {}
    sorted_abbrs = sorted(ABBREVIATIONS, key=len, reverse=True)
    for i, abbr in enumerate(sorted_abbrs):
        placeholder = _make_placeholder(i)
        abbr_map[placeholder] = abbr
        pattern = re.escape(abbr)
        matches = list(re.finditer(pattern, processed, re.IGNORECASE))
        for m in reversed(matches):
            processed = processed[: m.start()] + placeholder + processed[m.end() :]

    # Protect decimal numbers
    decimal_map: dict[str, str] = {}
    decimal_counter = 0

    def _replace_decimal(m: re.Match) -> str:
        nonlocal decimal_counter
        key = f"\x00DEC{decimal_counter}\x00"
        decimal_map[key] = m.group(0)
        decimal_counter += 1
        return key

    processed = re.sub(r"\d+\.\d+", _replace_decimal, processed)

    # Collapse ellipsis
    processed = re.sub(r"\.{3,}", "\x00ELLIPSIS\x00", processed)

    # Split on sentence-ending punctuation
    parts = re.split(r"([.!?]+)", processed)
    raw_sentences: list[str] = []
    i = 0
    while i < len(parts):
        segment = parts[i]
        if i + 1 < len(parts) and re.fullmatch(r"[.!?]+", parts[i + 1]):
            segment += parts[i + 1]
            i += 2
        else:
            i += 1
        raw_sentences.append(segment)

    # Restore placeholders and map to line numbers
    results: list[tuple[str, int]] = []
    search_start = 0
    for sent in raw_sentences:
        restored = sent
        for placeholder, abbr in abbr_map.items():
            restored = restored.replace(placeholder, abbr)
        for placeholder, dec in decimal_map.items():
            restored = restored.replace(placeholder, dec)
        restored = restored.replace("\x00ELLIPSIS\x00", "...")
        stripped = restored.strip()
        if not stripped:
            continue

        search_key = stripped.lstrip()[:20]
        idx = text.find(search_key, search_start)
        if idx == -1:
            idx = text.find(search_key)
        line_num = _find_line_number(text, idx) if idx != -1 else 1
        results.append((stripped, line_num))
        if idx != -1:
            search_start = idx + len(search_key)

    return results


# ---------------------------------------------------------------------------
# N-gram repeated phrase detection
# ---------------------------------------------------------------------------


def _extract_ngrams(words: list[str], n: int) -> list[tuple[str, ...]]:
    """Extract n-grams from a word list."""
    return [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]


def _find_repeated_phrases(text: str) -> list[tuple[str, int, int]]:
    """Find phrases of 4+ words appearing 3+ times.

    Returns list of (phrase, count, first_char_index) sorted by first occurrence.
    """
    text_lower = text.lower()
    # Tokenize into words with positions
    word_matches = list(re.finditer(r"\S+", text_lower))
    if len(word_matches) < 4:
        return []

    words = [m.group() for m in word_matches]
    positions = [m.start() for m in word_matches]

    # Count n-grams for sizes 4, 5, 6
    ngram_counts: dict[tuple[str, ...], int] = Counter()
    ngram_first_pos: dict[tuple[str, ...], int] = {}

    for n in (4, 5, 6):
        for i in range(len(words) - n + 1):
            gram = tuple(words[i : i + n])
            ngram_counts[gram] += 1
            if gram not in ngram_first_pos:
                ngram_first_pos[gram] = positions[i]

    # Filter to those appearing 3+ times
    flagged = {gram for gram, count in ngram_counts.items() if count >= 3}

    # Remove sub-grams that are contained within a longer flagged gram
    to_remove: set[tuple[str, ...]] = set()
    flagged_list = sorted(flagged, key=len, reverse=True)
    for longer in flagged_list:
        for shorter in flagged_list:
            if shorter is longer or len(shorter) >= len(longer):
                continue
            if shorter in to_remove:
                continue
            # Check if shorter is a sub-sequence of longer
            slen = len(shorter)
            for start in range(len(longer) - slen + 1):
                if longer[start : start + slen] == shorter:
                    to_remove.add(shorter)
                    break

    flagged -= to_remove

    # Build results sorted by first occurrence
    results: list[tuple[str, int, int]] = []
    for gram in flagged:
        phrase = " ".join(gram)
        count = ngram_counts[gram]
        first_pos = ngram_first_pos[gram]
        results.append((phrase, count, first_pos))

    results.sort(key=lambda x: x[2])
    return results


# ---------------------------------------------------------------------------
# Main check function
# ---------------------------------------------------------------------------


def check(text: str, similarity_threshold: float = 0.7) -> list[Finding]:
    if not text or not text.strip():
        return []

    findings: list[Finding] = []
    sentences = _split_sentences(text)

    # --- 1. Exact duplicate sentences ---
    seen_exact: dict[str, int] = {}  # normalized sentence -> index in sentences
    for i, (sent, line_num) in enumerate(sentences):
        key = sent.lower().strip()
        if key in seen_exact:
            other_idx = seen_exact[key]
            other_line = sentences[other_idx][1]
            excerpt = sent[:60] + ("..." if len(sent) > 60 else "")
            findings.append(
                Finding(
                    tool=TOOL_NAME,
                    line_number=line_num,
                    column=0,
                    description=f"Upprepad mening (identisk med rad {other_line})",
                    excerpt=excerpt,
                )
            )
        else:
            seen_exact[key] = i

    # --- 2. Near-duplicate sentences ---
    # Only compare sentences with 5+ words
    long_sentences = [
        (i, sent, line_num)
        for i, (sent, line_num) in enumerate(sentences)
        if len(sent.split()) >= 5
    ]

    reported_near: set[tuple[int, int]] = set()
    for idx_a in range(len(long_sentences)):
        i_a, sent_a, line_a = long_sentences[idx_a]
        len_a = len(sent_a)
        key_a = sent_a.lower().strip()

        for idx_b in range(idx_a + 1, len(long_sentences)):
            i_b, sent_b, line_b = long_sentences[idx_b]
            key_b = sent_b.lower().strip()

            # Skip exact duplicates (already handled)
            if key_a == key_b:
                continue

            # Length filter: within 50% of each other
            len_b = len(sent_b)
            if len_b < len_a * 0.5 or len_b > len_a * 1.5:
                continue

            sim = _similarity(sent_a, sent_b)
            if sim >= similarity_threshold:
                pair = (min(i_a, i_b), max(i_a, i_b))
                if pair not in reported_near:
                    reported_near.add(pair)
                    excerpt = sent_b[:60] + ("..." if len(sent_b) > 60 else "")
                    findings.append(
                        Finding(
                            tool=TOOL_NAME,
                            line_number=line_b,
                            column=0,
                            description=f"Liknande mening (rad {line_a}, {sim:.0%} likhet)",
                            excerpt=excerpt,
                        )
                    )

    # --- 3. Repeated phrases (n-grams) ---
    repeated = _find_repeated_phrases(text)
    for phrase, count, first_pos in repeated:
        line_num = _find_line_number(text, first_pos)
        excerpt = phrase[:60] + ("..." if len(phrase) > 60 else "")
        findings.append(
            Finding(
                tool=TOOL_NAME,
                line_number=line_num,
                column=0,
                description=f"Upprepad fras ({count} gånger): '{phrase}'",
                excerpt=excerpt,
            )
        )

    # Sort all findings by line number
    findings.sort(key=lambda f: f.line_number)
    return findings
