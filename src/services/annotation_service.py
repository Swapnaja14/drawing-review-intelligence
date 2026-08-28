import time
import math
import fitz  # PyMuPDF
from pathlib import Path
from typing import List

from src.core.dtos.annotation_dtos import BoundingBoxDTO, AnnotationResultDTO, DocumentAnnotationDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class AnnotationDetectionService:
    def __init__(self):
        pass

    def detect_annotations_on_page(self, pdf_path: Path, page_number: int) -> AnnotationResultDTO:
        start_time = time.time()
        logger.info(f"Detecting annotations on {pdf_path}, page {page_number}")
        
        regions = []
        try:
            doc = fitz.open(pdf_path)
            if 0 <= page_number < len(doc):
                page = doc[page_number]
                
                # Extract different types of regions
                regions.extend(self._extract_native_annotations(page, page_number))
                regions.extend(self._extract_text_regions(page, page_number))
                regions.extend(self._detect_redline_regions(page, page_number))
            
            doc.close()
        except Exception as e:
            logger.error(f"Error detecting annotations on {pdf_path}: {e}")

        processing_time_ms = (time.time() - start_time) * 1000
        
        return AnnotationResultDTO(
            drawing_id=pdf_path.name,
            page_number=page_number,
            regions=regions,
            detection_method="PyMuPDF_native",
            processing_time_ms=processing_time_ms
        )

    def detect_all_pages(self, pdf_path: Path) -> DocumentAnnotationDTO:
        logger.info(f"Detecting annotations across all pages of {pdf_path}")
        page_results = []
        total_regions = 0
        total_pages = 0
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            for page_num in range(total_pages):
                result = self.detect_annotations_on_page(pdf_path, page_num)
                page_results.append(result)
                total_regions += len(result.regions)
                
        except Exception as e:
            logger.error(f"Error processing document {pdf_path}: {e}")
            
        return DocumentAnnotationDTO(
            file_name=pdf_path.name,
            total_pages=total_pages,
            page_results=page_results,
            total_regions=total_regions
        )

    def _extract_native_annotations(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        regions = []
        for annot in page.annots():
            rect = annot.rect
            annot_type = annot.type[1] if annot.type else "annotation"
            regions.append(
                BoundingBoxDTO(
                    x0=float(rect.x0),
                    y0=float(rect.y0),
                    x1=float(rect.x1),
                    y1=float(rect.y1),
                    page_number=page_num,
                    confidence=1.0,
                    label=f"annotation_{annot_type}"
                )
            )
        return regions

    def _extract_text_regions(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        regions = []
        blocks = page.get_text('dict').get('blocks', [])
        
        for block in blocks:
            if block['type'] == 0:  # Text block
                rect = fitz.Rect(block['bbox'])
                area = rect.width * rect.height
                
                # Check text content
                text_content = ""
                for line in block.get('lines', []):
                    for span in line.get('spans', []):
                        text_content += span.get('text', '')
                        
                if area >= 100 and text_content.strip():
                    regions.append(
                        BoundingBoxDTO(
                            x0=float(rect.x0),
                            y0=float(rect.y0),
                            x1=float(rect.x1),
                            y1=float(rect.y1),
                            page_number=page_num,
                            confidence=0.95,
                            label="text_block"
                        )
                    )
        return regions

    def _detect_redline_regions(self, page: fitz.Page, page_num: int) -> List[BoundingBoxDTO]:
        regions = []
        paths = page.get_drawings()
        
        for path in paths:
            # Check for red color
            is_red = False
            
            # Check stroke color
            stroke_color = path.get('color')
            if stroke_color and len(stroke_color) >= 3:
                r, g, b = stroke_color[:3]
                if r > 0.7 and g < 0.3 and b < 0.3:
                    is_red = True
                    
            # Check fill color
            fill_color = path.get('fill')
            if fill_color and len(fill_color) >= 3:
                r, g, b = fill_color[:3]
                if r > 0.7 and g < 0.3 and b < 0.3:
                    is_red = True
                    
            if is_red:
                rect = path['rect']
                # Basic grouping could be implemented here, for now treat each path bounding box
                regions.append(
                    BoundingBoxDTO(
                        x0=float(rect[0]),
                        y0=float(rect[1]),
                        x1=float(rect[2]),
                        y1=float(rect[3]),
                        page_number=page_num,
                        confidence=0.85,
                        label="redline"
                    )
                )
        return regions
