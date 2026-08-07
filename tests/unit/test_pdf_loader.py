"""
tests/unit/test_pdf_loader.py
Unit test suite for IPDFLoader, PyMuPDFAdapter, PDFService, and Database repository.
"""

import pytest
from pathlib import Path
import fitz  # PyMuPDF

from src.infrastructure.pdf.pymupdf_adapter import PyMuPDFAdapter
from src.services.pdf_service import PDFService
from src.infrastructure.storage.repository import DatabaseEngine, DrawingRepository
from src.core.exceptions.pdf_exceptions import (
    PDFNotFoundError,
    CorruptedPDFError,
    InvalidPageError
)


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    """Fixture generating a valid 2-page sample engineering drawing PDF for testing."""
    pdf_file = tmp_path / "sample_drawing.pdf"
    doc = fitz.open()

    # Page 1: Native Text Page
    page1 = doc.new_page(width=841.89, height=595.28)  # A4 Landscape in points
    page1.insert_text((50, 50), "DRAWING NO: UCC-DWG-101", fontsize=14)
    page1.insert_text((50, 100), "REVISION 2 - RECHECK BOLT CLEARANCE M10", fontsize=12)

    # Page 2: Second Page
    page2 = doc.new_page(width=841.89, height=595.28)
    page2.insert_text((50, 50), "PAGE 2 NOTES AND SPECIFICATIONS", fontsize=12)

    doc.save(pdf_file)
    doc.close()
    return pdf_file


def test_load_document_success(sample_pdf_path: Path):
    """Verifies successful PDF loading and metadata extraction."""
    adapter = PyMuPDFAdapter()
    service = PDFService(pdf_loader=adapter)

    doc_dto = service.process_pdf_document(sample_pdf_path)

    assert doc_dto.file_name == "sample_drawing.pdf"
    assert doc_dto.total_pages == 2
    assert doc_dto.is_encrypted is False
    assert doc_dto.is_scanned is False
    assert len(doc_dto.pages) == 2
    assert doc_dto.pages[0].has_native_text is True


def test_file_not_found():
    """Verifies PDFNotFoundError is raised for non-existent file path."""
    adapter = PyMuPDFAdapter()
    non_existent = Path("non_existent_file.pdf")

    with pytest.raises(PDFNotFoundError):
        adapter.load_document(non_existent)


def test_invalid_page_render(sample_pdf_path: Path):
    """Verifies InvalidPageError is raised when requesting invalid page index."""
    adapter = PyMuPDFAdapter()

    with pytest.raises(InvalidPageError):
        adapter.render_page_image(sample_pdf_path, page_number=99, dpi=150)


def test_render_page_image_success(sample_pdf_path: Path):
    """Verifies rendering a page image returns valid PNG byte stream."""
    adapter = PyMuPDFAdapter()
    rendered = adapter.render_page_image(sample_pdf_path, page_number=1, dpi=150)

    assert rendered.page_number == 1
    assert rendered.dpi == 150
    assert rendered.width_px > 0
    assert rendered.height_px > 0
    assert rendered.image_bytes.startswith(b"\x89PNG")


def test_extract_native_text_blocks(sample_pdf_path: Path):
    """Verifies extraction of native text blocks with bounding box positions."""
    adapter = PyMuPDFAdapter()
    blocks = adapter.extract_page_text_blocks(sample_pdf_path, page_number=1)

    assert len(blocks) >= 1
    first_block = blocks[0]
    assert "UCC-DWG-101" in first_block["text"]
    assert len(first_block["bbox"]) == 4


def test_database_save_drawing(sample_pdf_path: Path, tmp_path: Path):
    """Verifies saving PDF document metadata to SQLite database."""
    db_file = tmp_path / "test_drawing.db"
    db_engine = DatabaseEngine(db_path=db_file)
    repo = DrawingRepository(db_engine)

    adapter = PyMuPDFAdapter()
    doc_dto = adapter.load_document(sample_pdf_path)

    drawing_record = repo.save_drawing_from_dto(doc_dto)
    assert drawing_record["file_name"] == "sample_drawing.pdf"
    assert drawing_record["total_pages"] == 2
