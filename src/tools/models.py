from dataclasses import dataclass


@dataclass
class Finding:
    tool: str  # name of the tool e.g. "typo_checker"
    line_number: int  # 1-indexed line number in the original text
    column: int  # 1-indexed column number (0 if not applicable)
    description: str  # human-readable description in Swedish
    excerpt: str  # surrounding text snippet showing the issue (max ~60 chars)
