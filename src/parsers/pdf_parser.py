"""Extract text content from PDF files using PyMuPDF."""

import re

import fitz  # PyMuPDF


def extract_text(filepath: str) -> str:
    """Extract and return all text from the given PDF file."""
    try:
        doc = fitz.open(filepath)
    except fitz.FileDataError as e:
        raise ValueError(
            f"Could not open PDF file '{filepath}': file is corrupt or invalid. Details: {e}"
        ) from e
    except Exception as e:
        raise ValueError(f"Could not open file '{filepath}': {e}") from e

    if doc.is_encrypted:
        doc.close()
        raise RuntimeError(
            f"PDF file '{filepath}' is password-protected. "
            "Please decrypt the file before processing."
        )

    pages: list[str] = []
    try:
        for page in doc:
            pages.append(page.get_text())
    finally:
        doc.close()

    raw = "\n\n".join(pages)
    return _normalise_whitespace(raw)


def _normalise_whitespace(text: str) -> str:
    # Collapse runs of 3+ newlines to exactly two (paragraph break).
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing spaces on every line.
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()
