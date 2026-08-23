from dataclasses import dataclass
from typing import List

@dataclass
class CorrectionDTO:
    original: str
    corrected: str
    correction_type: str

@dataclass
class CleanedCommentDTO:
    original_text: str
    cleaned_text: str
    corrections: List[CorrectionDTO]
    similarity_score: float

@dataclass
class TextCleaningResultDTO:
    drawing_id: str
    total_comments: int
    cleaned_comments: List[CleanedCommentDTO]
    duplicates_removed: int
    processing_time_ms: float
