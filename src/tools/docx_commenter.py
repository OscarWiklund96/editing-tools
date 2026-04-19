"""Add review comments to a DOCX file based on findings."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from docx import Document
from docx.opc.part import Part
from docx.opc.packuri import PackURI
from lxml import etree

NSMAP = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = NSMAP["w"]

MAX_COMMENTS = 100

# Relationship type for comments part
COMMENTS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
)
COMMENTS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
)


def _qn(tag: str) -> str:
    """Expand 'w:foo' to full Clark notation."""
    prefix, local = tag.split(":")
    return f"{{{NSMAP[prefix]}}}{local}"


def _build_line_to_para(doc: Document) -> dict[int, object]:
    """Map 1-indexed line numbers (as produced by docx_parser) to paragraph XML elements.

    The parser logic is:
    1. Build parts list: non-empty paragraph text or "" for empty paragraphs
    2. Collapse consecutive empties
    3. ``"\\n".join(lines)`` then ``split("\\n\\n")`` — so consecutive non-empty
       paragraphs form ONE block (separated by ``\\n``), while empty paragraphs
       create ``\\n\\n`` block boundaries
    4. Filter empty blocks, rejoin with ``"\\n\\n"``
    5. Normalise whitespace

    We replicate this exactly to map line numbers back to paragraph elements.
    """
    # First pass: build parts with paragraph element references
    parts: list[tuple[str, object | None]] = []

    for para in doc.paragraphs:
        text = para.text
        if text.strip():
            parts.append((text, para._element))
        else:
            parts.append(("", None))

    # Second pass: collapse consecutive empties (same as parser)
    collapsed: list[tuple[str, object | None]] = []
    prev_empty = False
    for text, elem in parts:
        if text == "":
            if not prev_empty:
                collapsed.append(("", None))
            prev_empty = True
        else:
            collapsed.append((text, elem))
            prev_empty = False

    # Third pass: group consecutive non-empty entries into blocks.
    # The parser does "\n".join then split("\n\n"), which means consecutive
    # non-empty entries (no empty between them) merge into one block.
    # Empty entries create block boundaries.
    blocks: list[list[tuple[str, object | None]]] = []
    current_block: list[tuple[str, object | None]] = []

    for text, elem in collapsed:
        if text == "":
            if current_block:
                blocks.append(current_block)
                current_block = []
        else:
            current_block.append((text, elem))
    if current_block:
        blocks.append(current_block)

    # Fourth pass: assign line numbers.
    # Blocks are separated by "\n\n" (blank line) in the final text.
    # Within a block, paragraphs are separated by "\n" (single newline).
    line_to_para: dict[int, object] = {}
    current_line = 1

    for block_idx, block in enumerate(blocks):
        for para_idx, (text, elem) in enumerate(block):
            text_lines = text.splitlines() or [""]
            for offset in range(len(text_lines)):
                if elem is not None:
                    line_to_para[current_line + offset] = elem
            current_line += len(text_lines)
            # Within a block, paragraphs are on consecutive lines (no blank line)
        # Between blocks, the "\n\n" join adds a blank line
        if block_idx < len(blocks) - 1:
            current_line += 1  # blank line between blocks

    return line_to_para


def add_comments(
    src_path: str,
    dst_path: str,
    findings: list,
    author: str = "Editing Tools",
) -> int:
    """Add review comments to a DOCX based on findings.

    Returns the number of comments actually added.
    """
    if not src_path.lower().endswith(".docx"):
        raise ValueError(f"Source file is not a .docx: {src_path}")

    doc = Document(src_path)
    line_to_para = _build_line_to_para(doc)

    # Deduplicate: one comment per (line_number, description)
    seen: set[tuple[int, str]] = set()
    unique_findings: list = []
    for f in findings:
        key = (f.line_number, f.description)
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)

    # Filter to findings we can map and cap
    mappable = [
        (f, line_to_para[f.line_number])
        for f in unique_findings
        if f.line_number in line_to_para
    ]
    mappable = mappable[:MAX_COMMENTS]

    if not mappable:
        # Nothing to add – just save a copy
        doc.save(dst_path)
        return 0

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Build <w:comments> XML
    comments_elem = etree.Element(_qn("w:comments"), nsmap={"w": W})

    for comment_id, (finding, para_elem) in enumerate(mappable):
        # Build comment text
        desc = finding.description
        if finding.excerpt:
            desc += f' — "{finding.excerpt}"'

        comment = etree.SubElement(comments_elem, _qn("w:comment"))
        comment.set(_qn("w:id"), str(comment_id))
        comment.set(_qn("w:author"), author)
        comment.set(_qn("w:date"), now)

        cp = etree.SubElement(comment, _qn("w:p"))
        cr = etree.SubElement(cp, _qn("w:r"))
        ct = etree.SubElement(cr, _qn("w:t"))
        ct.text = desc

        # Insert commentRangeStart at beginning of paragraph
        range_start = etree.Element(_qn("w:commentRangeStart"))
        range_start.set(_qn("w:id"), str(comment_id))
        para_elem.insert(0, range_start)

        # Append commentRangeEnd + commentReference run at end
        range_end = etree.SubElement(para_elem, _qn("w:commentRangeEnd"))
        range_end.set(_qn("w:id"), str(comment_id))

        ref_run = etree.SubElement(para_elem, _qn("w:r"))
        ref_rpr = etree.SubElement(ref_run, _qn("w:rPr"))
        ref_style = etree.SubElement(ref_rpr, _qn("w:rStyle"))
        ref_style.set(_qn("w:val"), "CommentReference")
        ref_ref = etree.SubElement(ref_run, _qn("w:commentReference"))
        ref_ref.set(_qn("w:id"), str(comment_id))

    # Serialize comments XML
    comments_xml = etree.tostring(
        comments_elem, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    # Create the comments part and attach to the document
    doc_part = doc.part
    comments_part = Part(
        PackURI("/word/comments.xml"),
        COMMENTS_CONTENT_TYPE,
        comments_xml,
        doc_part.package,
    )
    doc_part.relate_to(comments_part, COMMENTS_REL_TYPE)

    doc.save(dst_path)
    return len(mappable)
