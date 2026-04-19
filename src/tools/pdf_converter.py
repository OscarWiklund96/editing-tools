"""Convert PDF files to DOCX format."""

from __future__ import annotations


def convert_pdf_to_docx(
    src_path: str,
    dst_path: str,
    progress_callback=None,
) -> dict:
    """Convert a PDF file to DOCX.

    Args:
        src_path: Path to source PDF file
        dst_path: Path for output DOCX file
        progress_callback: Optional callback(float) for progress 0.0-1.0

    Returns:
        {"pages": int, "status": "ok"} on success
    """
    # Try pdf2docx first
    try:
        from pdf2docx import Converter

        cv = Converter(src_path)
        cv.convert(dst_path)
        pages = len(cv.fitz_doc) if hasattr(cv, "fitz_doc") else 0
        cv.close()
        return {"pages": pages, "status": "ok"}
    except ImportError:
        pass  # Fall back to manual approach

    # Fallback: PyMuPDF extraction + python-docx creation
    import fitz
    from docx import Document
    from docx.shared import Pt

    pdf = fitz.open(src_path)
    doc = Document()
    total_pages = len(pdf)

    for page_num in range(total_pages):
        page = pdf[page_num]
        blocks = page.get_text("blocks")

        for block in blocks:
            if block[6] == 0:  # Text block (not image)
                text = block[4].strip()
                if text:
                    para = doc.add_paragraph(text)
                    for run in para.runs:
                        run.font.size = Pt(11)

        if page_num < total_pages - 1:
            doc.add_page_break()

        if progress_callback:
            progress_callback((page_num + 1) / total_pages)

    pdf.close()
    doc.save(dst_path)
    return {"pages": total_pages, "status": "ok"}
