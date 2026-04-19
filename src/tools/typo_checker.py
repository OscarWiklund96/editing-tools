"""Detect common typographical errors such as double spaces, repeated words, etc."""

import re
from .models import Finding

TOOL = "typo_checker"


def _excerpt(line: str, col: int, width: int = 60) -> str:
    """Return a ~60-char snippet centred around col (1-indexed)."""
    start = max(0, col - 1 - width // 2)
    end = min(len(line), start + width)
    return line[start:end]


def check(text: str) -> list[Finding]:
    """Return a list of detected typo issues in the given text."""
    findings: list[Finding] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # 1. Double spaces
        for m in re.finditer(r" {2,}", line):
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Dubbelt mellanslag",
                    excerpt=_excerpt(line, col),
                )
            )

        # 2. Space before punctuation
        for m in re.finditer(r" +([,.:;!?])", line):
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Mellanslag före skiljetecken",
                    excerpt=_excerpt(line, col),
                )
            )

        # 3. Missing space after punctuation (punctuation immediately followed by a letter)
        for m in re.finditer(r"[,.:;!?](?=[^\s])", line):
            # Allow e.g. decimal numbers like "3.14" — skip if both sides are digits
            char_before = line[m.start() - 1] if m.start() > 0 else ""
            next_char = line[m.end()] if m.end() < len(line) else ""
            if m.group() == "." and char_before.isdigit() and next_char.isdigit():
                continue
            if not next_char.isalpha():
                continue
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Saknat mellanslag efter skiljetecken",
                    excerpt=_excerpt(line, col),
                )
            )

        # 4. Incorrect (straight) quotation marks
        for m in re.finditer(r'["\']', line):
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Felaktigt citattecken (rakt)",
                    excerpt=_excerpt(line, col),
                )
            )

        # 5. Hyphen used as dash (single hyphen surrounded by spaces)
        for m in re.finditer(r" - ", line):
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Bindestreck används som tankstreck",
                    excerpt=_excerpt(line, col),
                )
            )

        # 6. Repeated consecutive words (case-insensitive)
        for m in re.finditer(r"\b(\w+)\s+\1\b", line, flags=re.IGNORECASE):
            word = m.group(1)
            col = m.start() + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description=f"Upprepat ord: '{word}'",
                    excerpt=_excerpt(line, col),
                )
            )

    return findings
