"""
src/infrastructure/pdf/pymupdf_adapter.py
PyMuPDF (fitz) implementation of IPDFLoader interface.

ARCHITECTURE NOTE:
This is the ONLY file that imports fitz (PyMuPDF). All PDF extraction logic
belongs here. The service and repository layers must never import fitz directly.

DRAWING NUMBER EXTRACTION RULE:
  Priority 1 — PDF metadata "Subject" field (most reliable for named drawings).
  Priority 2 — PDF metadata "Title" field when it looks like a drawing number
               (contains hyphens/underscores, short, no spaces).
  Priority 3 — Filename stem with extension stripped and common revision
               suffixes removed (e.g. "_RevA", "_Rev1", "_R1" at end of stem).
  If none of the above produces a non-empty value, drawing_number = "".

  IMPORTANT: This is a best-effort extraction. The caller (repository / UI)
  must treat drawing_number as advisory and allow the user to override it.
  Do NOT use drawing_number as a database primary key or foreign key.

DATE EXTRACTION RULE:
  PyMuPDF exposes creation/modification dates as strings in PDF D: format:
      "D:YYYYMMDDHHmmSSOHH'mm'" (e.g. "D:20260715143022+00'00'")
  This adapter normalises them to "YYYY-MM-DD HH:MM:SS" for storage.
  If parsing fails or the field is absent, None is returned.
  Do NOT substitute the file-system mtime when PDF metadata is absent.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF

from src.core.interfaces.pdf_loader import IPDFLoader
from src.core.dtos.pdf_dtos import PDFDocumentDTO, PageMetadataDTO, RenderedPageDTO
from src.core.exceptions.pdf_exceptions import (
    PDFNotFoundError,
    CorruptedPDFError,
    EncryptedPDFError,
    InvalidPageError,
    PDFProcessingError,
)
from src.infrastructure.pdf.pdf_metadata_utils import (
    parse_pdf_date,
    extract_drawing_number,
)
from src.infrastructure.logging.logger import get_logger

logger = get_logger("PyMuPDFAdapter")

# ---------------------------------------------------------------------------
# Back-compat aliases (tests and callers that import these names directly
# from this module continue to work)
# ---------------------------------------------------------------------------
_parse_pdf_date        = parse_pdf_date
_extract_drawing_number = extract_drawing_number

# ---------------------------------------------------------------------------
# Regex for stripping revision suffixes — kept here for documentation
# proximity to the adapter, but the actual implementation is in
# pdf_metadata_utils.py which has no fitz dependency.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# PyMuPDFAdapter
# ---------------------------------------------------------------------------

class PyMuPDFAdapter(IPDFLoader):
    """
    Concrete adapter wrapping PyMuPDF engine for drawing operations.

    This class is responsible for all interactions with fitz (PyMuPDF).
    No other module should import fitz.
    """

    def load_document(self, file_path: Path) -> PDFDocumentDTO:
        """
        Load a PDF and extract document + per-page metadata.

        Extracted fields
        ----------------
        DrawingModel-bound: file_name, file_size_bytes, file_hash_sha256,
            total_pages, is_scanned, title, author, drawing_number,
            creation_date, modification_date
        PageModel-bound (per page): page_number, width_pt, height_pt,
            aspect_ratio, has_native_text, text_character_count, orientation_deg
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists() or not file_path.is_file():
            logger.error(f"File not found: {file_path}")
            raise PDFNotFoundError(f"PDF file does not exist: {file_path}")

        try:
            doc = fitz.open(file_path)
        except fitz.FileDataError as e:
            logger.error(f"Corrupted PDF file {file_path}: {e}")
            raise CorruptedPDFError(
                f"Failed to open corrupted PDF file: {file_path}"
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error opening PDF {file_path}: {e}")
            raise PDFProcessingError(f"Unexpected error loading PDF: {e}") from e

        try:
            if doc.is_encrypted:
                logger.warning(f"Encrypted PDF detected: {file_path}")
                raise EncryptedPDFError(
                    f"PDF is encrypted or password-protected: {file_path}"
                )

            file_bytes    = file_path.read_bytes()
            sha256_hash   = hashlib.sha256(file_bytes).hexdigest()
            file_size     = len(file_bytes)
            metadata      = doc.metadata or {}

            # ── Per-page extraction ───────────────────────────────
            pages_metadata: List[PageMetadataDTO] = []
            scanned_page_count = 0

            for i, page in enumerate(doc):
                page_num     = i + 1
                rect         = page.rect
                width_pt     = rect.width
                height_pt    = rect.height
                aspect_ratio = width_pt / height_pt if height_pt > 0 else 1.0

                text_content      = page.get_text("text").strip()
                char_count        = len(text_content)
                has_native_text   = char_count > 20   # threshold for native text

                if not has_native_text:
                    scanned_page_count += 1

                pages_metadata.append(
                    PageMetadataDTO(
                        page_number=page_num,
                        width_pt=width_pt,
                        height_pt=height_pt,
                        aspect_ratio=aspect_ratio,
                        has_native_text=has_native_text,
                        text_character_count=char_count,
                        orientation_deg=page.rotation,
                    )
                )

            total_pages = len(doc)
            is_scanned  = (
                (scanned_page_count / total_pages > 0.5) if total_pages > 0 else True
            )

            # ── Document-level metadata ───────────────────────────
            drawing_number    = _extract_drawing_number(metadata, file_path)
            creation_date     = _parse_pdf_date(metadata.get("creationDate"))
            modification_date = _parse_pdf_date(metadata.get("modDate"))

            logger.info(
                f"Loaded PDF '{file_path.name}' "
                f"({total_pages} pages, scanned={is_scanned}, "
                f"drawing_number='{drawing_number}', "
                f"creation_date={creation_date})"
            )

            return PDFDocumentDTO(
                file_path=file_path,
                file_name=file_path.name,
                file_size_bytes=file_size,
                file_hash_sha256=sha256_hash,
                total_pages=total_pages,
                is_encrypted=False,
                is_scanned=is_scanned,
                title=metadata.get("title") or None,
                author=metadata.get("author") or None,
                drawing_number=drawing_number,
                creation_date=creation_date,
                modification_date=modification_date,
                pages=pages_metadata,
            )
        finally:
            doc.close()

    def render_page_image(
        self, file_path: Path, page_number: int, dpi: int = 300
    ) -> RenderedPageDTO:
        """Render a page at target DPI and return the image as bytes (PNG)."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise PDFNotFoundError(f"File not found: {file_path}")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise CorruptedPDFError(
                f"Failed to open PDF for rendering: {e}"
            ) from e

        try:
            if page_number < 1 or page_number > len(doc):
                raise InvalidPageError(
                    f"Page number {page_number} out of bounds (1-{len(doc)})"
                )

            page = doc.load_page(page_number - 1)
            zoom = dpi / 72.0
            mat  = fitz.Matrix(zoom, zoom)
            pix  = page.get_pixmap(matrix=mat, alpha=False)

            image_bytes = pix.tobytes("png")
            logger.info(
                f"Rendered page {page_number} of '{file_path.name}' "
                f"at {dpi} DPI ({pix.width}x{pix.height} px)"
            )
            return RenderedPageDTO(
                page_number=page_number,
                width_px=pix.width,
                height_px=pix.height,
                dpi=dpi,
                image_bytes=image_bytes,
                format="PNG",
            )
        finally:
            doc.close()

    def extract_page_text_blocks(
        self, file_path: Path, page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Extract native text blocks with bounding boxes.

        Returns
        -------
        List of dicts with keys:
            "bbox"     : (x0, y0, x1, y1) in absolute PDF point coordinates
            "text"     : stripped text content of the block
            "block_no" : block index within the page

        INTEGRATION NOTE:
        bbox is in (x0, y0, x1, y1) absolute PDF point coordinates.
        1 point = 1/72 inch. Origin is top-left.
        Do NOT treat these as normalised (0–1) coordinates.
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise PDFNotFoundError(f"File not found: {file_path}")

        try:
            doc = fitz.open(file_path)
        except Exception as e:
            raise CorruptedPDFError(f"Failed to open PDF: {e}") from e

        try:
            if page_number < 1 or page_number > len(doc):
                raise InvalidPageError(
                    f"Page number {page_number} out of range (1-{len(doc)})"
                )

            page   = doc.load_page(page_number - 1)
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)

            extracted = []
            for b in blocks:
                if len(b) >= 5 and b[4].strip():
                    extracted.append({
                        "bbox":     (float(b[0]), float(b[1]), float(b[2]), float(b[3])),
                        "text":     b[4].strip(),
                        "block_no": b[5] if len(b) > 5 else 0,
                    })
            return extracted
        finally:
            doc.close()
