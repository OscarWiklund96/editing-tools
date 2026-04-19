"""Factory for selecting the correct parser based on file extension."""

import os
from typing import Callable

from . import docx_parser, pdf_parser, txt_parser

_PARSERS: dict[str, Callable[[str], str]] = {
    ".pdf": pdf_parser.extract_text,
    ".docx": docx_parser.extract_text,
    ".txt": txt_parser.extract_text,
}


def get_parser(filepath: str) -> Callable[[str], str]:
    """Return the correct extract_text function based on file extension.

    Raises ValueError for unsupported extensions.
    """
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    if ext not in _PARSERS:
        supported = ", ".join(sorted(_PARSERS))
        raise ValueError(f"Unsupported file type '{ext}'. Supported types: {supported}")
    return _PARSERS[ext]
