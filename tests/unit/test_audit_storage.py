"""
tests/unit/test_audit_storage.py
Unit tests for Persistent SQLite Audit Log Repository and Verification Service integration.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from src.infrastructure.storage.models import DrawingModel
from src.infrastructure.storage.repository import (
    DatabaseEngine,
    CommentRepository,
    AuditLogRepository,
)
from src.services.verification_service import VerificationService
from src.core.dtos.audit_dtos import AuditAction


@pytest.fixture
def test_db(tmp_path: Path):
    db_file = tmp_path / "test_audit.db"
    engine = DatabaseEngine(db_path=db_file)
    return engine


def _create_test_drawing(db_engine: DatabaseEngine, drawing_id: str):
    """Helper to insert parent DrawingModel so foreign keys succeed."""
    with db_engine.get_session() as session:
        dwg = DrawingModel(
            id=drawing_id,
            file_path=f"/test/path/{drawing_id}.pdf",
            file_name=f"{drawing_id}.pdf",
            file_size_bytes=2048,
            file_hash_sha256=f"hash_{drawing_id}",
            total_pages=1,
            is_scanned=False,
        )
        session.add(dwg)
        session.commit()


def test_audit_repo_create_and_retrieve_by_comment(test_db: DatabaseEngine):
    _create_test_drawing(test_db, "DWG-TEST-001")
    comment_repo = CommentRepository(test_db)
    audit_repo = AuditLogRepository(test_db)

    # 1. Create a comment
    c_res = comment_repo.save_comment(
        drawing_id="DWG-TEST-001",
        page_number=1,
        raw_text="Test comment for audit logging",
        bbox=(10.0, 20.0, 100.0, 50.0),
        confidence=0.95,
        status="Pending",
    )
    cid = c_res["id"]

    # 2. Add audit entry
    entry = audit_repo.create_audit_entry(
        comment_id=cid,
        action=AuditAction.APPROVE,
        reviewer_id="USR-LEAD-01",
        reviewer_name="Lead Engineer",
        old_value="Pending",
        new_value="Approved",
        notes="Verified against AISC specification.",
    )

    assert entry["comment_id"] == cid
    assert entry["action"] == AuditAction.APPROVE
    assert entry["old_value"] == "Pending"
    assert entry["new_value"] == "Approved"
    assert "AISC" in entry["notes"]

    # 3. Retrieve logs for comment
    logs = audit_repo.get_audit_logs_for_comment(cid)
    assert len(logs) == 1
    assert logs[0]["id"] == entry["id"]


def test_verification_service_persists_to_db(test_db: DatabaseEngine):
    _create_test_drawing(test_db, "DWG-TEST-002")
    comment_repo = CommentRepository(test_db)
    audit_repo = AuditLogRepository(test_db)
    verification_service = VerificationService(comment_repo, audit_repo)

    # 1. Create a comment
    c_res = comment_repo.save_comment(
        drawing_id="DWG-TEST-002",
        page_number=1,
        raw_text="Beam size discrepancy",
        bbox=(50.0, 60.0, 200.0, 90.0),
        confidence=0.80,
        status="Pending",
    )
    cid = c_res["id"]

    # 2. Perform actions through verification service
    verification_service.edit_comment_text(cid, "Beam size W14x30 discrepancy", reviewer_id="engineer1")
    verification_service.flag_comment(cid, reviewer_id="engineer1", notes="Requires site coordination")
    verification_service.approve_comment(cid, reviewer_id="lead_eng", notes="Approved after RFI review")

    # 3. Query audit logs from VerificationService (reads from SQLite)
    history = verification_service.get_audit_history(cid)
    assert len(history) == 3
    actions = [h.action for h in history]
    assert AuditAction.APPROVE in actions
    assert AuditAction.FLAG in actions
    assert AuditAction.EDIT_TEXT in actions


def test_audit_log_cascade_delete(test_db: DatabaseEngine):
    _create_test_drawing(test_db, "DWG-TEST-003")
    comment_repo = CommentRepository(test_db)
    audit_repo = AuditLogRepository(test_db)

    # 1. Create comment
    c_res = comment_repo.save_comment(
        drawing_id="DWG-TEST-003",
        page_number=1,
        raw_text="Temporary comment",
        bbox=(0.0, 0.0, 50.0, 50.0),
    )
    cid = c_res["id"]

    # 2. Add audit entry
    audit_repo.create_audit_entry(
        comment_id=cid,
        action=AuditAction.FLAG,
        reviewer_id="admin",
        old_value="Pending",
        new_value="Flagged",
    )

    logs_before = audit_repo.get_audit_logs_for_comment(cid)
    assert len(logs_before) == 1

    # 3. Delete drawing comments
    comment_repo.delete_comments_for_drawing("DWG-TEST-003")

    # 4. Verify cascade delete in SQLite
    logs_after = audit_repo.get_audit_logs_for_comment(cid)
    assert len(logs_after) == 0
