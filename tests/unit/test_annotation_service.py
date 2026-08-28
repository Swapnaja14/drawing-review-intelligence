import pytest
import fitz
from pathlib import Path

from src.services.annotation_service import AnnotationDetectionService
from src.core.dtos.annotation_dtos import DocumentAnnotationDTO

@pytest.fixture
def sample_pdf_with_text(tmp_path):
    pdf_path = tmp_path / "test_text.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Insert text block large enough to pass area >= 100 filter
    rect = fitz.Rect(50, 50, 250, 150)
    page.insert_textbox(rect, "This is a test block with enough area.")
    
    # Add a red line to test redline detection
    p1, p2 = fitz.Point(100, 100), fitz.Point(200, 200)
    page.draw_line(p1, p2, color=(1, 0, 0), width=2)
    
    doc.save(pdf_path)
    doc.close()
    return pdf_path

@pytest.fixture
def empty_pdf(tmp_path):
    pdf_path = tmp_path / "empty.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()
    return pdf_path

def test_detect_text_regions_returns_bounding_boxes(sample_pdf_with_text):
    service = AnnotationDetectionService()
    result = service.detect_annotations_on_page(sample_pdf_with_text, 0)
    
    assert len(result.regions) > 0
    labels = [r.label for r in result.regions]
    assert "text_block" in labels
    assert "redline" in labels

def test_detect_annotations_empty_pdf(empty_pdf):
    service = AnnotationDetectionService()
    result = service.detect_annotations_on_page(empty_pdf, 0)
    assert len(result.regions) == 0

def test_document_annotation_dto_fields(sample_pdf_with_text):
    service = AnnotationDetectionService()
    doc_result = service.detect_all_pages(sample_pdf_with_text)
    
    assert isinstance(doc_result, DocumentAnnotationDTO)
    assert doc_result.file_name == "test_text.pdf"
    assert doc_result.total_pages == 1
    assert len(doc_result.page_results) == 1
    assert doc_result.total_regions > 0

def test_bounding_box_coordinates_are_absolute(sample_pdf_with_text):
    service = AnnotationDetectionService()
    result = service.detect_annotations_on_page(sample_pdf_with_text, 0)
    
    for region in result.regions:
        assert region.x1 > region.x0
        assert region.y1 > region.y0
        assert region.x0 >= 0
        assert region.y0 >= 0
        # Typical PDF page max width/height
        assert region.x1 <= 10000 
        assert region.y1 <= 10000
