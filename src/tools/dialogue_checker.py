"""Dialogue Checker – checks dialogue formatting consistency."""

import re

from .models import Finding

TOOL_NAME = "dialogue_checker"

# Dialogue marker patterns
_EM_DASH = "–"
_GUILLEMETS = re.compile(r"[«»]")
_CURLY_QUOTES = re.compile(r"[\u201c\u201d]")

# Attribution patterns (common Swedish speech tags)
_ATTRIBUTION = re.compile(
    r"\b(sa|sade|frågade|svarade|ropade|viskade|mumlade|utbrast|"
    r"förklarade|tillade|menade|undrade|konstaterade|fortsatte)\b",
    re.IGNORECASE,
)


def check(text: str) -> list[Finding]:
    """Check dialogue formatting consistency."""
    lines = text.split("\n")
    findings: list[Finding] = []

    # Track which styles are used
    style_lines: dict[str, list[int]] = {
        "em_dash": [],
        "guillemets": [],
        "curly_quotes": [],
    }

    for i, line in enumerate(lines):
        if _EM_DASH in line:
            style_lines["em_dash"].append(i)
        if _GUILLEMETS.search(line):
            style_lines["guillemets"].append(i)
        if _CURLY_QUOTES.search(line):
            style_lines["curly_quotes"].append(i)

    # Check consistency: flag if multiple styles are used
    styles_used = {k: v for k, v in style_lines.items() if v}
    if len(styles_used) > 1:
        style_names = {
            "em_dash": "tankstreck (–)",
            "guillemets": "guillemets («»)",
            "curly_quotes": "citattecken ()",
        }
        used_names = [style_names[k] for k in styles_used]
        for style, line_indices in styles_used.items():
            # Flag the minority style occurrences
            for idx in line_indices[:5]:  # limit to first 5 per style
                findings.append(
                    Finding(
                        tool=TOOL_NAME,
                        line_number=idx + 1,
                        column=0,
                        description=(
                            f"Blandade dialogmarkörer: {', '.join(used_names)} "
                            f"används i texten"
                        ),
                        excerpt=lines[idx].strip()[:60],
                    )
                )

    # Check for unclosed quotes
    for i, line in enumerate(lines):
        # Guillemets
        open_g = line.count("«")
        close_g = line.count("»")
        if open_g != close_g:
            findings.append(
                Finding(
                    tool=TOOL_NAME,
                    line_number=i + 1,
                    column=0,
                    description="Obalanserade guillemets (« »)",
                    excerpt=line.strip()[:60],
                )
            )

        # Curly quotes
        open_c = line.count("\u201c")
        close_c = line.count("\u201d")
        if open_c != close_c:
            findings.append(
                Finding(
                    tool=TOOL_NAME,
                    line_number=i + 1,
                    column=0,
                    description="Obalanserade citattecken (\u201c \u201d)",
                    excerpt=line.strip()[:60],
                )
            )

    # Check for long dialogue without attribution
    consecutive_dialogue = 0
    dialogue_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        is_dialogue = (
            stripped.startswith(_EM_DASH)
            or _GUILLEMETS.search(stripped) is not None
            or _CURLY_QUOTES.search(stripped) is not None
        )

        if is_dialogue:
            if consecutive_dialogue == 0:
                dialogue_start = i
            consecutive_dialogue += 1

            has_attribution = _ATTRIBUTION.search(stripped) is not None
            if has_attribution:
                consecutive_dialogue = 0
        else:
            if consecutive_dialogue >= 4:
                findings.append(
                    Finding(
                        tool=TOOL_NAME,
                        line_number=dialogue_start + 1,
                        column=0,
                        description=(
                            f"Lång dialogpassage utan tillskrivning "
                            f"({consecutive_dialogue} rader)"
                        ),
                        excerpt=lines[dialogue_start].strip()[:60],
                    )
                )
            consecutive_dialogue = 0

    # Check trailing dialogue at end of text
    if consecutive_dialogue >= 4:
        findings.append(
            Finding(
                tool=TOOL_NAME,
                line_number=dialogue_start + 1,
                column=0,
                description=(
                    f"Lång dialogpassage utan tillskrivning "
                    f"({consecutive_dialogue} rader)"
                ),
                excerpt=lines[dialogue_start].strip()[:60],
            )
        )

    findings.sort(key=lambda f: (f.line_number, f.column))
    return findings
