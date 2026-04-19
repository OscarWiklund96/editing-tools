"""Detect inconsistent or excessive newline usage in text."""

from .models import Finding

TOOL = "newline_checker"


def check(text: str) -> list[Finding]:
    """Return a list of detected newline issues in the given text."""
    findings: list[Finding] = []

    # 4. Windows line endings (check raw text before splitting)
    if "\r\n" in text:
        # Report the first occurrence with its line number
        for lineno, raw_line in enumerate(text.splitlines(keepends=True), start=1):
            if raw_line.endswith("\r\n"):
                findings.append(
                    Finding(
                        tool=TOOL,
                        line_number=lineno,
                        column=0,
                        description="Windows-radbrytning (CRLF) hittades",
                        excerpt=raw_line.rstrip("\r\n")[:60],
                    )
                )
                break  # one report is enough — the issue is file-wide

    lines = text.splitlines(keepends=True)

    consecutive_blank = 0
    for lineno, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip("\r\n")

        # 1. Consecutive blank lines
        if line.strip() == "":
            consecutive_blank += 1
            if consecutive_blank >= 2:
                findings.append(
                    Finding(
                        tool=TOOL,
                        line_number=lineno,
                        column=0,
                        description="Flera tomma rader i följd",
                        excerpt="",
                    )
                )
        else:
            consecutive_blank = 0

        # 2. Trailing whitespace
        if line != line.rstrip(" \t"):
            col = len(line.rstrip(" \t")) + 1
            findings.append(
                Finding(
                    tool=TOOL,
                    line_number=lineno,
                    column=col,
                    description="Blanksteg i slutet av raden",
                    excerpt=line[:60],
                )
            )

    # 3. Missing newline at end of file
    if text and not text.endswith("\n"):
        last_lineno = len(lines)
        findings.append(
            Finding(
                tool=TOOL,
                line_number=last_lineno,
                column=0,
                description="Filen saknar radbrytning i slutet",
                excerpt=lines[-1].rstrip("\r\n")[:60] if lines else "",
            )
        )

    return findings
