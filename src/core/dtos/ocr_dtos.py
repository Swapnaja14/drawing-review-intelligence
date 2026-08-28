from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class OCRBlockDTO:
    text: str
    confidence: float
    bbox: Tuple[float, float, float, float]
    page_number: int
    text_type: str
    block_id: str

@dataclass
class OCRPageResultDTO:
    page_number: int
    blocks: List[OCRBlockDTO]
    total_blocks: int
    avg_confidence: float
    processing_time_ms: float

@dataclass
class OCRDocumentResultDTO:
    file_name: str
    total_pages: int
    page_results: List[OCRPageResultDTO]
    total_blocks: int
    overall_confidence: float
