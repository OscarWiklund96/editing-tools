"""Extract text content from plain text files."""

import re


def extract_text(filepath: str) -> str:
    """Read and return all text from the given TXT file.

    Tries UTF-8 first; falls back to latin-1 (common for Swedish files).
    """
    text = _read_file(filepath)
    # Normalise Windows/old-Mac line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return _normalise_whitespace(text)


def _read_file(filepath: str) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(filepath, encoding=encoding) as fh:
                return fh.read()
        except UnicodeDecodeError:
            continue
        except OSError as e:
            raise RuntimeError(f"Could not read file '{filepath}': {e}") from e
    # Should not be reached because latin-1 decodes any byte sequence.
    raise RuntimeError(f"Could not decode file '{filepath}' with UTF-8 or latin-1.")


def _normalise_whitespace(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()
