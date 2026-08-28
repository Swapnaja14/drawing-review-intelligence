import time
import uuid
import fitz  # PyMuPDF
from pathlib import Path
from typing import List

from src.core.dtos.ocr_dtos import OCRBlockDTO, OCRPageResultDTO, OCRDocumentResultDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class OCRIntegrationService:
    def __init__(self):
        try:
            # Placeholder for HybridOCRService import
            # from src.services.hybrid_ocr_service import HybridOCRService
            self._hybrid_available = False
        except ImportError:
            self._hybrid_available = False
            
    def process_page(self, pdf_path: Path, page_number: int, dpi: int = 300) -> OCRPageResultDTO:
        logger.info(f"Processing OCR for {pdf_path}, page {page_number}")
        
        if self._hybrid_available:
            # Here we would call HybridOCRService
            # result = self._hybrid_ocr_service.process(pdf_path, page_number)
            pass
            
        # Fallback to PyMuPDF
        return self._pymupdf_fallback(pdf_path, page_number)

    def process_document(self, pdf_path: Path) -> OCRDocumentResultDTO:
        logger.info(f"Processing document OCR for {pdf_path}")
        page_results = []
        total_blocks = 0
        overall_confidence = 0.0
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            doc.close()
            
            for page_num in range(total_pages):
                result = self.process_page(pdf_path, page_num)
                page_results.append(result)
                total_blocks += result.total_blocks
                
            if total_blocks > 0:
                overall_confidence = sum(r.avg_confidence * r.total_blocks for r in page_results) / total_blocks
                
        except Exception as e:
            logger.error(f"Error in OCR document processing {pdf_path}: {e}")
            total_pages = 0
            
        return OCRDocumentResultDTO(
            file_name=pdf_path.name,
            total_pages=total_pages,
            page_results=page_results,
            total_blocks=total_blocks,
            overall_confidence=overall_confidence
        )

    def _pymupdf_fallback(self, pdf_path: Path, page_number: int) -> OCRPageResultDTO:
        start_time = time.time()
        blocks_dtos = []
        
        try:
            doc = fitz.open(pdf_path)
            if 0 <= page_number < len(doc):
                page = doc[page_number]
                blocks = page.get_text('dict').get('blocks', [])
                
                for block in blocks:
                    if block['type'] == 0:  # Text block
                        text = ""
                        for line in block.get('lines', []):
                            for span in line.get('spans', []):
                                text += span.get('text', ' ') + " "
                        
                        text = text.strip()
                        
                        # Filter noise
                        if len(text) < 3 or text.isspace() or text.isdigit():
                            continue
                            
                        bbox = block['bbox']
                        confidence = self._normalize_confidence(0.95, "pymupdf")
                        
                        blocks_dtos.append(OCRBlockDTO(
                            text=text,
                            confidence=confidence,
                            bbox=(float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])),
                            page_number=page_number,
                            text_type='printed',
                            block_id=str(uuid.uuid4())
                        ))
            doc.close()
        except Exception as e:
            logger.error(f"Error in PyMuPDF fallback for {pdf_path}: {e}")

        processing_time = (time.time() - start_time) * 1000
        avg_conf = sum(b.confidence for b in blocks_dtos) / len(blocks_dtos) if blocks_dtos else 0.0
        
        return OCRPageResultDTO(
            page_number=page_number,
            blocks=blocks_dtos,
            total_blocks=len(blocks_dtos),
            avg_confidence=avg_conf,
            processing_time_ms=processing_time
        )

    def _normalize_confidence(self, raw_score: float, source: str) -> float:
        if source == 'tesseract':
            return max(0.0, min(1.0, raw_score / 100.0))
        elif source == 'trocr':
            return max(0.0, min(1.0, raw_score))
        elif source == 'pymupdf':
            return 0.95
        return max(0.0, min(1.0, raw_score))
