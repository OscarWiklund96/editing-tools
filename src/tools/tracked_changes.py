"""Apply typo fixes to a DOCX file using OOXML tracked changes (revision marks)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from docx import Document
from lxml import etree

from .typo_checker import _fix_line

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _qn(tag: str) -> str:
    """Expand 'w:foo' to full Clark notation."""
    prefix, local = tag.split(":")
    return f"{{{W}}}{local}"


def fix_docx_tracked(
    src_path: str, dst_path: str, author: str = "Editing Tools"
) -> list[dict]:
    """Apply typo fixes as tracked changes. Returns list of changes."""
    doc = Document(src_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rev_id = 1
    changes: list[dict] = []

    for para_idx, para in enumerate(doc.paragraphs):
        for run in list(para.runs):
            original_text = run.text
            if not original_text:
                continue
            fixed_text = _fix_line(original_text)
            if fixed_text == original_text:
                continue

            para_elem = run._element.getparent()
            run_elem = run._element
            idx = list(para_elem).index(run_elem)

            # Copy run properties
            rpr = run_elem.find(_qn("w:rPr"))

            # Build w:del element
            del_elem = etree.Element(_qn("w:del"))
            del_elem.set(_qn("w:id"), str(rev_id))
            del_elem.set(_qn("w:author"), author)
            del_elem.set(_qn("w:date"), now)
            del_run = etree.SubElement(del_elem, _qn("w:r"))
            if rpr is not None:
                del_run.insert(0, deepcopy(rpr))
            del_text = etree.SubElement(del_run, _qn("w:delText"))
            del_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            del_text.text = original_text

            # Build w:ins element
            ins_elem = etree.Element(_qn("w:ins"))
            ins_elem.set(_qn("w:id"), str(rev_id + 1))
            ins_elem.set(_qn("w:author"), author)
            ins_elem.set(_qn("w:date"), now)
            ins_run = etree.SubElement(ins_elem, _qn("w:r"))
            if rpr is not None:
                ins_run.insert(0, deepcopy(rpr))
            ins_text = etree.SubElement(ins_run, _qn("w:t"))
            ins_text.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            ins_text.text = fixed_text

            # Replace original run with del + ins
            para_elem.remove(run_elem)
            para_elem.insert(idx, ins_elem)
            para_elem.insert(idx, del_elem)

            rev_id += 2
            changes.append(
                {
                    "paragraph": para_idx + 1,
                    "before": original_text,
                    "after": fixed_text,
                }
            )

    doc.save(dst_path)
    return changes
