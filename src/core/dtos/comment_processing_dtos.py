from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class CorrectionDTO:
    original: str
    corrected: str
    correction_type: str

@dataclass
class CleanedCommentDTO:
    original_text: str
    cleaned_text: str
    corrections: List[CorrectionDTO] = field(default_factory=list)
    similarity_score: float = 1.0
    sub_actions: List[str] = field(default_factory=list)
    reviewer_initials: Optional[str] = None
    action_verb: Optional[str] = None
    priority_level: str = "MEDIUM"
    engineering_terms_found: List[str] = field(default_factory=list)
    is_duplicate_of: Optional[str] = None

@dataclass
class TextCleaningResultDTO:
    drawing_id: str
    total_comments: int
    cleaned_comments: List[CleanedCommentDTO]
    duplicates_removed: int
    processing_time_ms: float
