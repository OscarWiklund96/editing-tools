"""Detect common typographical errors such as double spaces, repeated words, etc."""

import re

from docx import Document

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


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------


def _fix_line(line: str) -> str:
    """Apply all fixable typo corrections to a single line of text."""

    # 1. Double spaces → single space
    line = re.sub(r" {2,}", " ", line)

    # 2. Space before punctuation → remove
    line = re.sub(r" +([,.:;!?])", r"\1", line)

    # 3. Missing space after punctuation → add space
    #    Skip: decimal numbers (3.14), ellipsis (...), URLs/paths
    def _add_space_after_punct(m: re.Match) -> str:
        start = m.start()
        full = m.string
        punct = m.group(1)
        letter = m.group(2)
        # decimal number: digit before dot/comma and digit after
        if punct in ".," and start > 0 and full[start - 1].isdigit():
            return m.group(0)
        # ellipsis: dot preceded or followed by dot
        if punct == ".":
            if start > 0 and full[start - 1] == ".":
                return m.group(0)
            if start + 1 < len(full) and full[start + 1] == ".":
                return m.group(0)
        # URL/path heuristic: :// or dot between non-space sequences (e.g. www.example)
        if (
            punct == ":"
            and start + 2 < len(full)
            and full[start + 1 : start + 3] == "//"
        ):
            return m.group(0)
        if punct == "." and start > 0 and not full[start - 1].isspace():
            # Check if this looks like a domain/path: non-space on both sides with no space nearby
            before_word = start > 0 and full[start - 1].isalnum()
            after_word = letter.isalpha()
            # Heuristic: if surrounded by alnum and no space within 3 chars before, likely URL/path
            if before_word and after_word:
                # Look for URL-like context (no spaces in surrounding token)
                token_start = start
                while token_start > 0 and not full[token_start - 1].isspace():
                    token_start -= 1
                token = full[token_start:start]
                if "/" in token or "www" in token.lower() or "@" in token:
                    return m.group(0)
        return punct + " " + letter

    line = re.sub(r"([,.:;!?])([A-Za-zÀ-ÿ])", _add_space_after_punct, line)

    # 4. Straight quotes → Swedish typographic quotes
    # Double quotes: alternating " and "
    new_line = []
    dq_open = True
    sq_open = True
    for ch in line:
        if ch == '"':
            new_line.append("\u201d" if not dq_open else "\u201c")
            dq_open = not dq_open
        elif ch == "'":
            new_line.append("\u2019" if not sq_open else "\u2018")
            sq_open = not sq_open
        else:
            new_line.append(ch)
    line = "".join(new_line)

    # 5. Hyphen as dash → em dash (Swedish style with spaces)
    line = line.replace(" - ", " \u2013 ")

    # 6. Repeated consecutive words → remove duplicate
    line = re.sub(r"\b(\w+)\s+\1\b", r"\1", line, flags=re.IGNORECASE)

    return line


def fix(text: str) -> dict:
    """Apply all fixable typo corrections and return the fixed text with change log.

    Returns:
        {
            "fixed_text": str,
            "changes": [{"line": int, "description": str, "before": str, "after": str}, ...]
        }
    """
    lines = text.splitlines()
    changes: list[dict] = []

    for idx, original in enumerate(lines):
        line = _fix_line(original)

        if line != original:
            changes.append(
                {
                    "line": idx + 1,
                    "description": "Automatisk korrigering",
                    "before": original,
                    "after": line,
                }
            )
            lines[idx] = line

    return {
        "fixed_text": "\n".join(lines),
        "changes": changes,
    }


def fix_docx(src_path: str, dst_path: str) -> list[dict]:
    """Apply typo fixes to a DOCX file, preserving formatting.

    Returns list of changes: [{"paragraph": int, "before": str, "after": str}, ...]
    """
    doc = Document(src_path)
    changes: list[dict] = []

    for para_idx, para in enumerate(doc.paragraphs):
        original_text = para.text
        # Apply fixes to each run independently to preserve formatting
        any_run_changed = False
        for run in para.runs:
            original_run = run.text
            fixed_run = _fix_line(original_run)
            if fixed_run != original_run:
                run.text = fixed_run
                any_run_changed = True

        if any_run_changed:
            changes.append(
                {
                    "paragraph": para_idx + 1,
                    "before": original_text,
                    "after": para.text,
                }
            )

    doc.save(dst_path)
    return changes
