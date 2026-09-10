"""
src/infrastructure/pdf/pdf_metadata_utils.py
Pure-Python utility functions for PDF metadata extraction.

These helpers have NO dependency on fitz/PyMuPDF so they can be imported and
tested in environments where PyMuPDF is not installed (e.g. CI, unit tests).

The PyMuPDFAdapter imports and re-exports these functions so all callers go
through the same code path regardless of which module they import from.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches trailing revision suffixes on filename stems:
#   _RevA, _Rev2, _R01, -RevB, _v2, _v1.0
_REVISION_SUFFIX_RE = re.compile(
    r'[_\-\s]+(rev[a-z0-9]*|r\d+|v\d+[\.\d]*)$',
    re.IGNORECASE,
)

# A string that looks like a drawing number: no spaces, starts
# alphanumeric, contains hyphens/underscores, reasonable length
_DRAWING_NUMBER_PATTERN_RE = re.compile(
    r'^[A-Z0-9][A-Z0-9\-_\.]{2,}$',
    re.IGNORECASE,
)

# PyMuPDF PDF date format: "D:YYYYMMDDHHmmSS±HH'mm'" (time portion optional)
_PDF_DATE_RE = re.compile(
    r"D:(\d{4})(\d{2})(\d{2})"     # YYYYMMDD — required
    r"(\d{2})?(\d{2})?(\d{2})?",   # HHmmSS   — optional
)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def parse_pdf_date(raw: Optional[str]) -> Optional[str]:
    """
    Convert a PDF D: date string to "YYYY-MM-DD HH:MM:SS".

    Returns None if the input is absent, empty, or cannot be parsed.

    Does NOT fall back to the current time or file-system mtime.
    The caller must store None when the PDF does not carry a date field.

    Examples
    --------
    >>> parse_pdf_date("D:20260715143022+00'00'")
    '2026-07-15 14:30:22'
    >>> parse_pdf_date("D:20260715")
    '2026-07-15 00:00:00'
    >>> parse_pdf_date(None)
    None
    """
    if not raw:
        return None
    m = _PDF_DATE_RE.search(raw)
    if not m:
        return None
    year, month, day = m.group(1), m.group(2), m.group(3)
    hour   = m.group(4) or "00"
    minute = m.group(5) or "00"
    second = m.group(6) or "00"
    try:
        dt = datetime(
            int(year), int(month), int(day),
            int(hour), int(minute), int(second),
        )
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def extract_drawing_number(metadata: dict, file_path: Path) -> str:
    """
    Extract the engineering drawing number using a three-priority rule.

    Priority 1 — PDF metadata "subject" field (most reliable).
    Priority 2 — PDF metadata "title" field, only if it matches the
                 pattern of a drawing number (no spaces, starts alphanumeric,
                 contains hyphens/underscores/digits).
    Priority 3 — Filename stem with common revision suffixes stripped
                 (e.g. "_RevA", "_Rev1", "_R01", "_v2").

    Returns an empty string when none of the above produces a value.

    IMPORTANT:
    The returned value is advisory and may need user confirmation.
    It is NOT a database primary key and must NEVER be used as drawing_id.

    Examples
    --------
    >>> extract_drawing_number({"subject": "UCC-E-101"}, Path("x.pdf"))
    'UCC-E-101'
    >>> extract_drawing_number({}, Path("UCC-E-101_RevA.pdf"))
    'UCC-E-101'
    """
    # Priority 1: PDF Subject field
    subject = (metadata.get("subject") or "").strip()
    if subject:
        return subject

    # Priority 2: PDF Title field — only when it looks like a drawing number
    title = (metadata.get("title") or "").strip()
    if title and " " not in title and _DRAWING_NUMBER_PATTERN_RE.match(title):
        return title

    # Priority 3: Filename stem with revision suffix stripped
    stem    = file_path.stem.strip()
    cleaned = _REVISION_SUFFIX_RE.sub("", stem).strip()
    if cleaned:
        return cleaned

    return ""
