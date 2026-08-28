from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

class AuditAction:
    APPROVE = 'approve'
    REJECT = 'reject'
    FLAG = 'flag'
    EDIT_TEXT = 'edit_text'
    EDIT_CATEGORY = 'edit_category'
    BULK_APPROVE = 'bulk_approve'

@dataclass
class AuditLogEntryDTO:
    comment_id: str
    action: str
    reviewer_id: str
    old_value: str
    new_value: str
    timestamp: datetime
    notes: str = ''

    @property
    def changed_by_user_id(self) -> str:
        return self.reviewer_id

    @property
    def details(self) -> str:
        if self.notes:
            return self.notes
        if self.old_value or self.new_value:
            return f"{self.old_value} → {self.new_value}"
        return ""

@dataclass
class VerificationSummaryDTO:
    total_comments: int
    approved: int
    rejected: int
    flagged: int
    pending: int
    approval_rate: float
    verified_by_human_count: int

@dataclass
class BulkActionResultDTO:
    total_processed: int
    successful: int
    failed: int
    skipped: int
    failed_ids: List[str]
