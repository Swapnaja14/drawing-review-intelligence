"""
src/core/dtos/pdf_dtos.py
Data Transfer Objects (DTOs) for PDF document processing.
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path


@dataclass(frozen=True)
class PageMetadataDTO:
    """Immutable metadata for a single PDF page."""
    page_number: int            # 1-indexed page number
    width_pt: float             # Page width in points (72 pt = 1 inch)
    height_pt: float            # Page height in points
    aspect_ratio: float
    has_native_text: bool       # True if page contains native searchable text layer
    text_character_count: int   # Number of native characters detected
    orientation_deg: int        # Rotation angle (0, 90, 180, 270)


@dataclass(frozen=True)
class PDFDocumentDTO:
    """Immutable metadata for an entire PDF engineering drawing file."""
    file_path: Path
    file_name: str
    file_size_bytes: int
    file_hash_sha256: str
    total_pages: int
    is_encrypted: bool
    is_scanned: bool            # True if majority of pages lack native text
    title: Optional[str] = None
    author: Optional[str] = None
    pages: List[PageMetadataDTO] = field(default_factory=list)


@dataclass(frozen=True)
class RenderedPageDTO:
    """Container holding a rendered page image buffer and display parameters."""
    page_number: int
    width_px: int
    height_px: int
    dpi: int
    image_bytes: bytes          # Raw PNG or JPEG byte stream
    format: str = "PNG"
