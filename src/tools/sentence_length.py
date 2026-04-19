import re
import statistics

from .models import Finding

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

DISTRIBUTION_BUCKETS = [
    ("1–5", 1, 5),
    ("6–10", 6, 10),
    ("11–20", 11, 20),
    ("21–30", 21, 30),
    ("31–40", 31, 40),
    ("41–50", 41, 50),
    ("51+", 51, float("inf")),
]


def _make_placeholder(index: int) -> str:
    return f"\x00ABBR{index}\x00"


def _find_line_number(text: str, char_index: int) -> int:
    """Return 1-indexed line number for a character position."""
    return text[:char_index].count("\n") + 1


def check(text: str, max_words: int = 40, min_words: int = 3) -> dict:
    if not text or not text.strip():
        return {
            "findings": [],
            "stats": {
                "total_sentences": 0,
                "avg_words": 0.0,
                "min_words": 0,
                "max_words": 0,
                "median_words": 0.0,
                "distribution": [(b[0], 0) for b in DISTRIBUTION_BUCKETS],
            },
        }

    # --- Phase 1: Replace abbreviations with placeholders ---
    processed = text
    abbr_map: dict[str, str] = {}
    # Sort longest first so "d.v.s." is matched before "d.v."
    sorted_abbrs = sorted(ABBREVIATIONS, key=len, reverse=True)
    for i, abbr in enumerate(sorted_abbrs):
        placeholder = _make_placeholder(i)
        abbr_map[placeholder] = abbr
        # Case-insensitive replacement preserving original case
        pattern = re.escape(abbr)
        matches = list(re.finditer(pattern, processed, re.IGNORECASE))
        for m in reversed(matches):
            processed = processed[: m.start()] + placeholder + processed[m.end() :]

    # --- Phase 2: Protect decimal numbers (e.g. 3.14, 14.30) ---
    decimal_map: dict[str, str] = {}
    decimal_counter = 0

    def _replace_decimal(m: re.Match) -> str:
        nonlocal decimal_counter
        key = f"\x00DEC{decimal_counter}\x00"
        decimal_map[key] = m.group(0)
        decimal_counter += 1
        return key

    processed = re.sub(r"\d+\.\d+", _replace_decimal, processed)

    # --- Phase 3: Collapse ellipsis into a single sentinel ---
    processed = re.sub(r"\.{3,}", "\x00ELLIPSIS\x00", processed)

    # --- Phase 4: Split on sentence-ending punctuation ---
    parts = re.split(r"([.!?]+)", processed)

    # Reassemble into sentences (text + its trailing punctuation)
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

    # --- Phase 5: Restore placeholders and collect sentences ---
    sentences: list[str] = []
    for sent in raw_sentences:
        restored = sent
        for placeholder, abbr in abbr_map.items():
            restored = restored.replace(placeholder, abbr)
        for placeholder, dec in decimal_map.items():
            restored = restored.replace(placeholder, dec)
        restored = restored.replace("\x00ELLIPSIS\x00", "...")
        stripped = restored.strip()
        if stripped:
            sentences.append(stripped)

    # --- Phase 6: Map each sentence back to its line in the original text ---
    # We search for each sentence's beginning in the original text.
    sentence_data: list[
        tuple[str, int, int]
    ] = []  # (sentence, line_number, word_count)
    search_start = 0
    for sent in sentences:
        # Find the first few non-whitespace chars of the sentence in the original
        search_key = sent.lstrip()[:20]
        idx = text.find(search_key, search_start)
        if idx == -1:
            # Fallback: try from the beginning
            idx = text.find(search_key)
        line_num = _find_line_number(text, idx) if idx != -1 else 1
        words = sent.split()
        word_count = len(words)
        sentence_data.append((sent, line_num, word_count))
        if idx != -1:
            search_start = idx + len(search_key)

    # --- Phase 7: Build findings ---
    findings: list[Finding] = []
    for sent, line_num, wc in sentence_data:
        excerpt = sent[:60] + "..." if len(sent) > 60 else sent
        if wc > max_words:
            findings.append(
                Finding(
                    tool="sentence_length",
                    line_number=line_num,
                    column=0,
                    description=f"Lång mening ({wc} ord)",
                    excerpt=excerpt,
                )
            )
        elif wc < min_words:
            findings.append(
                Finding(
                    tool="sentence_length",
                    line_number=line_num,
                    column=0,
                    description=f"Kort mening ({wc} ord)",
                    excerpt=excerpt,
                )
            )

    # --- Phase 8: Compute stats ---
    word_counts = [wc for _, _, wc in sentence_data]
    total = len(word_counts)
    avg = round(sum(word_counts) / total, 1) if total else 0.0
    mn = min(word_counts) if total else 0
    mx = max(word_counts) if total else 0
    med = float(statistics.median(word_counts)) if total else 0.0

    distribution: list[tuple[str, int]] = []
    for label, lo, hi in DISTRIBUTION_BUCKETS:
        count = sum(1 for wc in word_counts if lo <= wc <= hi)
        distribution.append((label, count))

    return {
        "findings": findings,
        "stats": {
            "total_sentences": total,
            "avg_words": avg,
            "min_words": mn,
            "max_words": mx,
            "median_words": med,
            "distribution": distribution,
        },
    }
