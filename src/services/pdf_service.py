"""
src/services/pdf_service.py
Application Service for PDF operations orchestrating IPDFLoader implementations.
"""

from pathlib import Path
from typing import List, Dict, Any
from src.core.interfaces.pdf_loader import IPDFLoader
from src.core.dtos.pdf_dtos import PDFDocumentDTO, RenderedPageDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger("PDFService")


class PDFService:
    """
    Application Service managing PDF processing workflows.
    High-level controllers and UI call this service, which delegates
    to the injected IPDFLoader implementation.
    """

    def __init__(self, pdf_loader: IPDFLoader) -> None:
        """
        Constructor injecting IPDFLoader implementation (Dependency Injection).

        Args:
            pdf_loader: Concrete implementation of IPDFLoader.
        """
        self._loader = pdf_loader

    def process_pdf_document(self, file_path: Path) -> PDFDocumentDTO:
        """
        Loads document, validates structure, and logs metadata summary.

        Args:
            file_path: Path to the drawing PDF file.

        Returns:
            PDFDocumentDTO: Document metadata container.
        """
        logger.info(f"Processing PDF document request for: {file_path}")
        document = self._loader.load_document(file_path)
        logger.info(f"Successfully processed PDF '{document.file_name}' (ID/Hash: {document.file_hash_sha256[:8]})")
        return document

    def get_page_render(self, file_path: Path, page_number: int, dpi: int = 300) -> RenderedPageDTO:
        """
        Retrieves high-resolution rendered image for UI display or OCR preprocessing.

        Args:
            file_path: Path to the drawing PDF.
            page_number: 1-indexed page number.
            dpi: Resolution dots per inch.

        Returns:
            RenderedPageDTO: Rendered page buffer DTO.
        """
        return self._loader.render_page_image(file_path, page_number, dpi=dpi)

    def extract_native_text(self, file_path: Path, page_number: int) -> List[Dict[str, Any]]:
        """
        Extracts native text blocks with bounding box positions.

        Args:
            file_path: Path to drawing PDF.
            page_number: 1-indexed page number.

        Returns:
            List[Dict[str, Any]]: Extracted text blocks.
        """
        return self._loader.extract_page_text_blocks(file_path, page_number)
