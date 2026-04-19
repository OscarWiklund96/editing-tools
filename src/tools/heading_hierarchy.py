"""Heading Hierarchy – validates heading/numbering hierarchy."""

import re

from .models import Finding

TOOL_NAME = "heading_hierarchy"

_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.?\s")


def check(text: str) -> list[Finding]:
    """Validate that numbered headings follow a consistent hierarchy."""
    lines = text.split("\n")
    findings: list[Finding] = []

    headings: list[tuple[int, list[int]]] = []  # (line_index, number_parts)

    for i, line in enumerate(lines):
        m = _NUMBERED_HEADING.match(line.strip())
        if m:
            parts = [int(x) for x in m.group(1).split(".")]
            headings.append((i, parts))

    if not headings:
        return findings

    prev_parts: list[int] | None = None

    for line_idx, parts in headings:
        level = len(parts)

        if prev_parts is not None:
            prev_level = len(prev_parts)

            # Check for skipped hierarchy levels (e.g., 1 -> 1.1.1)
            if level > prev_level + 1:
                findings.append(
                    Finding(
                        tool=TOOL_NAME,
                        line_number=line_idx + 1,
                        column=0,
                        description=(
                            f"Hierarkinivå hoppas över: från nivå {prev_level} "
                            f"till nivå {level}"
                        ),
                        excerpt=lines[line_idx].strip()[:60],
                    )
                )

            # Check sequential numbering at the same or deeper level
            if level == prev_level:
                # Same level: last number should increment by 1 or reset
                # Check if they share the same parent
                if parts[:-1] == prev_parts[:-1]:
                    expected = prev_parts[-1] + 1
                    if parts[-1] != expected and parts[-1] != 1:
                        findings.append(
                            Finding(
                                tool=TOOL_NAME,
                                line_number=line_idx + 1,
                                column=0,
                                description=(
                                    f"Numrering hoppar: förväntade "
                                    f"{'.'.join(str(x) for x in parts[:-1] + [expected])}, "
                                    f"hittade {'.'.join(str(x) for x in parts)}"
                                ),
                                excerpt=lines[line_idx].strip()[:60],
                            )
                        )
            elif level == prev_level + 1:
                # Going deeper: last number should be 1
                if parts[-1] != 1:
                    findings.append(
                        Finding(
                            tool=TOOL_NAME,
                            line_number=line_idx + 1,
                            column=0,
                            description=(
                                f"Undernumrering börjar inte på 1: "
                                f"hittade {'.'.join(str(x) for x in parts)}"
                            ),
                            excerpt=lines[line_idx].strip()[:60],
                        )
                    )
            elif level < prev_level:
                # Going up: check continuity with previous heading at same level
                # Find the last heading at this level with same parent
                for prev_line_idx, prev_p in reversed(
                    headings[: headings.index((line_idx, parts))]
                ):
                    if len(prev_p) == level and prev_p[:-1] == parts[:-1]:
                        expected = prev_p[-1] + 1
                        if parts[-1] != expected:
                            findings.append(
                                Finding(
                                    tool=TOOL_NAME,
                                    line_number=line_idx + 1,
                                    column=0,
                                    description=(
                                        f"Numrering hoppar: förväntade "
                                        f"{'.'.join(str(x) for x in parts[:-1] + [expected])}, "
                                        f"hittade {'.'.join(str(x) for x in parts)}"
                                    ),
                                    excerpt=lines[line_idx].strip()[:60],
                                )
                            )
                        break

        prev_parts = parts

    return findings
