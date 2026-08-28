import pytest
import fitz
from pathlib import Path

from src.services.ocr_integration_service import OCRIntegrationService

@pytest.fixture
def sample_pdf_for_ocr(tmp_path):
    pdf_path = tmp_path / "ocr_test.pdf"
    doc = fitz.open()
    
    # Page 0
    page1 = doc.new_page()
    page1.insert_text(fitz.Point(50, 50), "Hello world text")
    page1.insert_text(fitz.Point(50, 100), "123")  # Numbers only, should filter
    page1.insert_text(fitz.Point(50, 150), "hi")   # < 3 chars, should filter
    
    # Page 1
    page2 = doc.new_page()
    page2.insert_text(fitz.Point(50, 50), "Another page text")
    
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_pymupdf_fallback_extracts_text(sample_pdf_for_ocr):
    service = OCRIntegrationService()
    result = service.process_page(sample_pdf_for_ocr, 0)
    
    assert result.page_number == 0
    assert result.total_blocks > 0
    
    texts = [b.text for b in result.blocks]
    assert any("Hello world text" in t for t in texts)

def test_noise_filtering_removes_short_text(sample_pdf_for_ocr):
    service = OCRIntegrationService()
    result = service.process_page(sample_pdf_for_ocr, 0)
    
    texts = [b.text for b in result.blocks]
    assert not any("123" == t.strip() for t in texts)
    assert not any("hi" == t.strip() for t in texts)

def test_confidence_normalization():
    service = OCRIntegrationService()
    
    assert service._normalize_confidence(85.0, "tesseract") == 0.85
    assert service._normalize_confidence(110.0, "tesseract") == 1.0
    assert service._normalize_confidence(0.92, "trocr") == 0.92
    assert service._normalize_confidence(0.5, "pymupdf") == 0.95

def test_document_processing_all_pages(sample_pdf_for_ocr):
    service = OCRIntegrationService()
    doc_result = service.process_document(sample_pdf_for_ocr)
    
    assert doc_result.total_pages == 2
    assert len(doc_result.page_results) == 2
    assert doc_result.total_blocks > 0
    assert doc_result.overall_confidence == 0.95

def test_ocr_block_dto_fields(sample_pdf_for_ocr):
    service = OCRIntegrationService()
    result = service.process_page(sample_pdf_for_ocr, 0)
    
    if result.blocks:
        block = result.blocks[0]
        assert hasattr(block, "text")
        assert hasattr(block, "confidence")
        assert hasattr(block, "bbox")
        assert hasattr(block, "page_number")
        assert hasattr(block, "text_type")
        assert hasattr(block, "block_id")
