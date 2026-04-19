"""Page Reference Checker – finds potentially broken page/section references."""

import re

from .models import Finding

TOOL_NAME = "page_reference_checker"

# Swedish reference patterns
_PATTERNS = [
    re.compile(r"se\s+sidan?\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+sid\.\s*(\S+)", re.IGNORECASE),
    re.compile(r"på\s+sidan?\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+avsnitt\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+kapitel\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+tabell\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+figur\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+även\s+avsnitt\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+även\s+sidan?\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+även\s+kapitel\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+även\s+tabell\s+(\S+)", re.IGNORECASE),
    re.compile(r"se\s+även\s+figur\s+(\S+)", re.IGNORECASE),
    # English patterns
    re.compile(r"see\s+page\s+(\S+)", re.IGNORECASE),
    re.compile(r"see\s+section\s+(\S+)", re.IGNORECASE),
    re.compile(r"see\s+chapter\s+(\S+)", re.IGNORECASE),
    re.compile(r"see\s+table\s+(\S+)", re.IGNORECASE),
    re.compile(r"see\s+figure\s+(\S+)", re.IGNORECASE),
]


def check(text: str) -> list[Finding]:
    """Find all page/section references for manual verification."""
    lines = text.split("\n")
    findings: list[Finding] = []

    for i, line in enumerate(lines):
        for pattern in _PATTERNS:
            for m in pattern.finditer(line):
                ref_target = m.group(1).rstrip(".,;:)")
                findings.append(
                    Finding(
                        tool=TOOL_NAME,
                        line_number=i + 1,
                        column=m.start() + 1,
                        description=(
                            f'Referens hittad: "{m.group(0).rstrip(".,;:)")}"'
                            f" — verifiera att målet ({ref_target}) stämmer"
                        ),
                        excerpt=line.strip()[:60],
                    )
                )

    findings.sort(key=lambda f: (f.line_number, f.column))
    return findings
