from datetime import datetime
from typing import List, Optional

from src.core.dtos.audit_dtos import (
    AuditAction,
    AuditLogEntryDTO,
    VerificationSummaryDTO,
    BulkActionResultDTO
)
from src.infrastructure.storage.repository import CommentRepository, CommentAuditLogRepository
from src.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class VerificationService:
    def __init__(self, comment_repo: CommentRepository):
        self.comment_repo = comment_repo
        self._audit_log: List[AuditLogEntryDTO] = []
        db = getattr(comment_repo, "_db", None)
        self.audit_repo = CommentAuditLogRepository(db) if db else None

    def _log_audit(
        self,
        comment_id: str,
        action: str,
        reviewer_id: str,
        old_value: str,
        new_value: str,
        field_changed: str = "status",
        notes: str = ""
    ) -> None:
        entry = AuditLogEntryDTO(
            comment_id=comment_id,
            action=action,
            reviewer_id=reviewer_id,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now(),
            notes=notes
        )
        self._audit_log.append(entry)

        if self.audit_repo:
            try:
                self.audit_repo.log_action(
                    comment_id=comment_id,
                    action=action,
                    field_changed=field_changed,
                    old_value=str(old_value) if old_value is not None else "",
                    new_value=str(new_value) if new_value is not None else "",
                    changed_by_user_id=reviewer_id or None,
                    notes=notes
                )
            except Exception as e:
                logger.error(f"Failed to log audit change for comment {comment_id}: {e}")

    def approve_comment(self, comment_id: str, reviewer_id: str = '', notes: str = '') -> bool:
        old_status = "Pending"
        if hasattr(self.comment_repo, "get_comment_status"):
            try:
                old_status = self.comment_repo.get_comment_status(comment_id) or "Pending"
            except Exception:
                old_status = "Pending"
        success = self.comment_repo.update_comment_status(comment_id, 'Approved', True)
        if success:
            self._log_audit(comment_id, AuditAction.APPROVE, reviewer_id, old_status, 'Approved', field_changed='status', notes=notes)
        return success

    def reject_comment(self, comment_id: str, reviewer_id: str = '', notes: str = '') -> bool:
        old_status = "Pending"
        if hasattr(self.comment_repo, "get_comment_status"):
            try:
                old_status = self.comment_repo.get_comment_status(comment_id) or "Pending"
            except Exception:
                old_status = "Pending"
        success = self.comment_repo.update_comment_status(comment_id, 'Rejected', True)
        if success:
            self._log_audit(comment_id, AuditAction.REJECT, reviewer_id, old_status, 'Rejected', field_changed='status', notes=notes)
        return success

    def flag_comment(self, comment_id: str, reviewer_id: str = '', notes: str = '') -> bool:
        old_status = "Pending"
        if hasattr(self.comment_repo, "get_comment_status"):
            try:
                old_status = self.comment_repo.get_comment_status(comment_id) or "Pending"
            except Exception:
                old_status = "Pending"
        success = self.comment_repo.update_comment_status(comment_id, 'Flagged', True)
        if success:
            self._log_audit(comment_id, AuditAction.FLAG, reviewer_id, old_status, 'Flagged', field_changed='status', notes=notes)
        return success

    def edit_comment_text(self, comment_id: str, new_text: str, reviewer_id: str = '') -> bool:
        old_text = ""
        db = getattr(self.comment_repo, "_db", None)
        if db:
            try:
                from src.infrastructure.storage.models import CommentModel
                with db.get_session() as session:
                    row = session.get(CommentModel, comment_id)
                    if row:
                        old_text = row.cleaned_text or row.raw_text or ""
            except Exception:
                pass

        success = self.comment_repo.update_comment_text(comment_id, new_text)
        if success:
            self._log_audit(comment_id, AuditAction.EDIT_TEXT, reviewer_id, old_text, new_text, field_changed='cleaned_text', notes='')
            return True
        return False

    def approve_all_high_confidence(self, drawing_id: str, threshold: float = 0.85, reviewer_id: str = 'system') -> BulkActionResultDTO:
        comments = self.comment_repo.get_comments_for_drawing(drawing_id)
        result = BulkActionResultDTO(
            total_processed=0,
            successful=0,
            failed=0,
            skipped=0,
            failed_ids=[]
        )
        for comment in comments:
            if comment.get('confidence', 0.0) >= threshold and comment.get('status') == 'Pending':
                result.total_processed += 1
                success = self.approve_comment(comment['id'], reviewer_id, 'Bulk approved')
                if success:
                    result.successful += 1
                else:
                    result.failed += 1
                    result.failed_ids.append(comment['id'])
            else:
                result.skipped += 1
        return result

    def get_verification_summary(self, drawing_id: str) -> VerificationSummaryDTO:
        comments = self.comment_repo.get_comments_for_drawing(drawing_id)
        total = len(comments)
        approved = 0
        rejected = 0
        flagged = 0
        pending = 0
        verified = 0

        for comment in comments:
            status = comment.get('status', 'Pending')
            if status == 'Approved':
                approved += 1
            elif status == 'Rejected':
                rejected += 1
            elif status == 'Flagged':
                flagged += 1
            elif status == 'Pending':
                pending += 1
            
            if comment.get('is_verified_by_human') or comment.get('verified_by_human', False):
                verified += 1
                
        approval_rate = approved / total if total > 0 else 0.0

        return VerificationSummaryDTO(
            total_comments=total,
            approved=approved,
            rejected=rejected,
            flagged=flagged,
            pending=pending,
            approval_rate=approval_rate,
            verified_by_human_count=verified
        )

    def get_audit_log(self, comment_id: Optional[str] = None) -> List[AuditLogEntryDTO]:
        if self.audit_repo:
            if comment_id:
                entries = self.audit_repo.get_history_for_comment(comment_id)
            else:
                entries = self.audit_repo.get_recent_actions(limit=500)
            dtos = []
            for e in entries:
                raw_ts = e.get("changed_at")
                if isinstance(raw_ts, str):
                    try:
                        ts = datetime.fromisoformat(raw_ts)
                    except ValueError:
                        ts = datetime.now()
                elif isinstance(raw_ts, datetime):
                    ts = raw_ts
                else:
                    ts = datetime.now()

                dtos.append(
                    AuditLogEntryDTO(
                        comment_id=e.get("comment_id") or "",
                        action=e.get("action") or "",
                        reviewer_id=e.get("changed_by_user_id") or "",
                        old_value=e.get("old_value") or "",
                        new_value=e.get("new_value") or "",
                        timestamp=ts,
                        notes=e.get("notes") or ""
                    )
                )
            return dtos

        if comment_id:
            return [entry for entry in self._audit_log if entry.comment_id == comment_id]
        return self._audit_log

    def get_audit_history(self, comment_id: Optional[str] = None) -> List[AuditLogEntryDTO]:
        return self.get_audit_log(comment_id)

