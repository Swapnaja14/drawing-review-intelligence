"""
End-to-End Pipeline Integration Test Suite.

Verifies the complete integration cycle of drawing review intelligence:
Database Schema -> Comment Repository -> Workflow Engine -> Verification Service -> Analytics Service -> Export Service.

Author: satyajeetvirkar22 <satyajeetvirkar22@gmail.com>
"""

import pytest
import os
import tempfile
from datetime import datetime
from sqlalchemy import create_engine
from src.infrastructure.storage.models import Base
from src.infrastructure.storage.repository import (
    DatabaseEngine,
    CommentRepository,
    ProjectRepository,
)
from src.infrastructure.storage.models import Base, DrawingModel
from src.services.verification_service import VerificationService
from src.services.analytics_service import AnalyticsService
from src.services.export_service import ExportService, ExportConfigDTO, ExportFormat
from src.core.domain.engineering_taxonomy import expand_engineering_abbreviations, calculate_severity_score
from src.core.domain.drawing_rules import DrawingRuleEngine


@pytest.fixture
def test_db_engine(tmp_path):
    """Provides a fresh SQLite DatabaseEngine for integration tests."""
    db_path = tmp_path / "integ_test.db"
    engine = DatabaseEngine(db_path=db_path)
    return engine


def test_full_drawing_review_lifecycle(test_db_engine):
    """Tests complete drawing review lifecycle end-to-end."""
    # 1. Initialize Repositories and Services
    comment_repo = CommentRepository(test_db_engine)
    project_repo = ProjectRepository(test_db_engine)

    verification_service = VerificationService(comment_repo)
    analytics_service = AnalyticsService(test_db_engine)
    export_service = ExportService(comment_repo, project_repo)
    rule_engine = DrawingRuleEngine()

    # 2. Register Drawing in database session
    drawing_id = "DWG-INTEG-2026-001"
    with test_db_engine.get_session() as session:
        dwg = DrawingModel(
            id=drawing_id,
            file_path="/drawings/C-101-SITE-GRADING-PLAN.pdf",
            file_name="C-101-SITE-GRADING-PLAN.pdf",
            file_size_bytes=1024500,
            file_hash_sha256="abc123hash456",
            title="CIVIL SITE GRADING PLAN",
            drawing_number="C-101",
            total_pages=2,
        )
        session.add(dwg)
        session.commit()

    # 3. Ingest Extracted Comments
    c1_dict = comment_repo.save_comment(
        drawing_id=drawing_id,
        page_number=1,
        raw_text="VERIFY P&ID AND CHECK HSS WELDING IN BOM -JDM",
        bbox=(50.0, 100.0, 200.0, 150.0),
        confidence=0.92,
        status="Pending",
        category_name="general",
    )
    c1_id = c1_dict["id"] if isinstance(c1_dict, dict) else c1_dict

    c2_dict = comment_repo.save_comment(
        drawing_id=drawing_id,
        page_number=1,
        raw_text="MIN CLR 345'-11 3/4\" TYPICAL FOR 8\" SCH 40 PIPE",
        bbox=(300.0, 100.0, 450.0, 150.0),
        confidence=0.88,
        status="Pending",
        category_name="dimensional",
    )
    c2_id = c2_dict["id"] if isinstance(c2_dict, dict) else c2_dict

    comments = comment_repo.get_comments_for_drawing(drawing_id)
    assert len(comments) == 2

    # 4. Perform Domain Abbreviation Expansion & Severity Scoring
    for c in comments:
        expanded_text, terms = expand_engineering_abbreviations(c.get("raw_text", ""))
        severity = calculate_severity_score(
            priority_level=c.get("priority_level", "LOW"),
            confidence=c.get("confidence", 0.5),
            term_count=len(terms),
        )
        assert severity > 0.0

    # 5. Evaluate Drawing Compliance before verification
    report_before = rule_engine.evaluate_compliance(drawing_id, comments)
    assert report_before.is_ready_for_release is False
    assert report_before.pending_count == 2

    # 6. Perform Human Verification (Approve / Reject)
    assert verification_service.approve_comment(c1_id, reviewer_id="ENGINEER_A")
    assert verification_service.reject_comment(c2_id, reviewer_id="ENGINEER_A")

    # Verify status updates
    updated_comments = comment_repo.get_comments_for_drawing(drawing_id)
    approved_cnt = sum(1 for c in updated_comments if c["status"] == "Approved")
    rejected_cnt = sum(1 for c in updated_comments if c["status"] == "Rejected")
    assert approved_cnt == 1
    assert rejected_cnt == 1

    # 7. Evaluate Drawing Compliance after verification
    report_after = rule_engine.evaluate_compliance(drawing_id, updated_comments)
    assert report_after.is_ready_for_release is True
    assert report_after.pending_count == 0

    # 8. Generate Analytics Summary
    summary = analytics_service.get_global_kpis()
    assert summary.total_comments == 2

    # 9. Test Excel & CSV Export Service
    with tempfile.TemporaryDirectory() as tmp_dir:
        excel_path = os.path.join(tmp_dir, "export_test.xlsx")
        csv_path = os.path.join(tmp_dir, "export_test.csv")

        excel_config = ExportConfigDTO(
            drawing_id=drawing_id,
            output_path=excel_path,
            format=ExportFormat.EXCEL,
        )
        excel_result = export_service.export_drawing_comments(excel_config)
        assert excel_result.success is True
        assert os.path.exists(excel_path)

        csv_config = ExportConfigDTO(
            drawing_id=drawing_id,
            output_path=csv_path,
            format=ExportFormat.CSV,
        )
        csv_result = export_service.export_drawing_comments(csv_config)
        assert csv_result.success is True
        assert os.path.exists(csv_path)
