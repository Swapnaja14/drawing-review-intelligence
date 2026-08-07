"""
src/core/interfaces/pdf_loader.py
Abstract Interface contract for PDF Loading & Rendering implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any
from src.core.dtos.pdf_dtos import PDFDocumentDTO, RenderedPageDTO, PageMetadataDTO


class IPDFLoader(ABC):
    """
    Interface contract for PDF document operations.
    Enforces Dependency Inversion so higher-level business logic
    never directly couples to third-party engines like PyMuPDF.
    """

    @abstractmethod
    def load_document(self, file_path: Path) -> PDFDocumentDTO:
        """
        Loads a PDF document, validates integrity, and extracts document & page metadata.

        Args:
            file_path: Path to the PDF file on disk.

        Returns:
            PDFDocumentDTO: Immutable document DTO containing metadata.

        Raises:
            PDFNotFoundError: If file does not exist.
            CorruptedPDFError: If PDF format is damaged.
            EncryptedPDFError: If PDF is password protected.
        """
        pass

    @abstractmethod
    def render_page_image(self, file_path: Path, page_number: int, dpi: int = 300) -> RenderedPageDTO:
        """
        Renders a specific page of a PDF document to a high-resolution image buffer.

        Args:
            file_path: Path to the PDF file.
            page_number: 1-indexed page number.
            dpi: Resolution dots per inch (default 300 for OCR).

        Returns:
            RenderedPageDTO: Rendered page image buffer DTO.

        Raises:
            InvalidPageError: If page_number is out of bounds.
        """
        pass

    @abstractmethod
    def extract_page_text_blocks(self, file_path: Path, page_number: int) -> List[Dict[str, Any]]:
        """
        Extracts native text blocks with precise bounding box coordinates from a digital PDF.

        Args:
            file_path: Path to the PDF file.
            page_number: 1-indexed page number.

        Returns:
            List[Dict[str, Any]]: Bounding box coordinates and extracted text blocks.
        """
        pass
