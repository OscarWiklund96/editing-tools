"""Chapter Balance – analyzes chapter/section lengths for balance."""

from __future__ import annotations

import re
import statistics

from .models import Finding

TOOL_NAME = "chapter_balance"

# Patterns that indicate a chapter/section heading
_NUMBERED_HEADING = re.compile(r"^(\d+(\.\d+)*\.?\s+|Kapitel\s+\d+)", re.IGNORECASE)


def _is_heading(line: str, next_line: str | None) -> bool:
    """Determine if a line is a chapter/section heading."""
    stripped = line.strip()
    if not stripped:
        return False

    # Numbered heading: "1.", "1.1", "Kapitel 1"
    if _NUMBERED_HEADING.match(stripped):
        return True

    # ALL CAPS line (at least 3 chars, and min 3 words or ≤60 chars)
    if len(stripped) >= 3 and stripped == stripped.upper() and stripped[0].isalpha():
        word_count = len(stripped.split())
        if word_count >= 3 or len(stripped) <= 60:
            return True

    return False


def check(text: str) -> dict:
    """Analyze chapter balance.

    Returns a dict with:
        - chapters: list of dicts with name, line_number, word_count
        - findings: list of Finding objects for imbalanced chapters
    """
    lines = text.split("\n")
    chapters: list[dict] = []

    # Detect chapter boundaries
    for i, line in enumerate(lines):
        next_line = lines[i + 1] if i + 1 < len(lines) else None
        if _is_heading(line, next_line):
            chapters.append(
                {
                    "name": line.strip(),
                    "line_number": i + 1,
                    "word_count": 0,
                }
            )

    if not chapters:
        return {"chapters": [], "findings": []}

    # Calculate word counts per chapter
    for idx, chapter in enumerate(chapters):
        start = chapter["line_number"]  # 1-indexed, heading line
        end = (
            chapters[idx + 1]["line_number"] - 1
            if idx + 1 < len(chapters)
            else len(lines)
        )
        # Count words in lines after the heading up to next chapter
        body_lines = lines[
            start:end
        ]  # start is already past heading (0-indexed = line_number)
        word_count = sum(len(line.split()) for line in body_lines)
        chapter["word_count"] = word_count

    # Find imbalanced chapters
    findings: list[Finding] = []
    word_counts = [ch["word_count"] for ch in chapters if ch["word_count"] > 0]

    if len(word_counts) >= 2:
        median = statistics.median(word_counts)
        if median > 0:
            for ch in chapters:
                wc = ch["word_count"]
                if wc > median * 2:
                    findings.append(
                        Finding(
                            tool=TOOL_NAME,
                            line_number=ch["line_number"],
                            column=0,
                            description=(
                                f'Kapitlet "{ch["name"]}" är ovanligt långt '
                                f"({wc} ord, median {int(median)} ord)"
                            ),
                            excerpt=ch["name"][:60],
                        )
                    )
                elif wc < median * 0.5 and wc > 0:
                    findings.append(
                        Finding(
                            tool=TOOL_NAME,
                            line_number=ch["line_number"],
                            column=0,
                            description=(
                                f'Kapitlet "{ch["name"]}" är ovanligt kort '
                                f"({wc} ord, median {int(median)} ord)"
                            ),
                            excerpt=ch["name"][:60],
                        )
                    )

    return {"chapters": chapters, "findings": findings}
