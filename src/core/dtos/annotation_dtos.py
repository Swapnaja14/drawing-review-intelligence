from dataclasses import dataclass, field
from typing import List

@dataclass
class BoundingBoxDTO:
    x0: float
    y0: float
    x1: float
    y1: float
    page_number: int
    confidence: float
    label: str

@dataclass
class AnnotationResultDTO:
    drawing_id: str
    page_number: int
    regions: List[BoundingBoxDTO]
    detection_method: str
    processing_time_ms: float

@dataclass
class DocumentAnnotationDTO:
    file_name: str
    total_pages: int
    page_results: List[AnnotationResultDTO]
    total_regions: int
