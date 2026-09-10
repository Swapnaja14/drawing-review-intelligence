"""
tests/unit/test_database_week7_13.py
Unit tests verifying Database & DevOps deliverables for Weeks 7-13:
1. Persistent CommentAuditLog via VerificationService in SQLite
2. Category FK resolution and lookup in save_comment
3. Model tracking metadata fields in CommentModel and _comment_to_dict
4. OCR reprocessing duplicate prevention for human-reviewed comments
5. ExportService Excel key mapping and non-empty columns
6. AnalyticsService SQL aggregate KPI execution
7. AppController normalise_comment priority of cleaned_text over raw_text
"""

import os
import tempfile
import pytest
from pathlib import Path
from datetime import datetime

from src.infrastructure.storage.repository import (
    DatabaseEngine,
    DrawingRepository,
    CommentRepository,
    CategoryRepository,
    CommentAuditLogRepository,
)
from src.services.verification_service import VerificationService
from src.services.analytics_service import AnalyticsService
from src.services.export_service import ExportService
from src.core.dtos.export_dtos import ExportConfigDTO, ExportFormat
from app.controllers.app_controller import AppController


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = DatabaseEngine(db_path=path)
    yield engine
    try:
        os.remove(path)
    except OSError:
        pass


from src.core.dtos.pdf_dtos import PDFDocumentDTO, PageMetadataDTO


def _make_dwg_dto(file_name: str, file_hash: str) -> PDFDocumentDTO:
    return PDFDocumentDTO(
        file_path=Path(f"/tmp/{file_name}"),
        file_name=file_name,
        file_size_bytes=1000,
        file_hash_sha256=file_hash,
        total_pages=1,
        is_encrypted=False,
        is_scanned=False,
        pages=[
            PageMetadataDTO(
                page_number=1,
                width_pt=612.0,
                height_pt=792.0,
                aspect_ratio=1.29,
                has_native_text=True,
                text_character_count=100,
                orientation_deg=0,
            )
        ]
    )


def test_comment_audit_log_persistence(temp_db):
    drawing_repo = DrawingRepository(temp_db)
    comment_repo = CommentRepository(temp_db)
    verification_service = VerificationService(comment_repo)

    dto = _make_dwg_dto("test.pdf", "abc123hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)
    drawing_id = dwg["id"]

    saved_cmt = comment_repo.save_comment(
        drawing_id=drawing_id,
        page_number=1,
        raw_text="MISSING PIPE SUPPORT",
        cleaned_text="Missing pipe support",
        bbox=(10.0, 20.0, 50.0, 60.0),
        status="Pending",
    )
    cmt_id = saved_cmt["id"]

    # Approve comment
    approved = verification_service.approve_comment(
        comment_id=cmt_id, reviewer_id="USR-123", notes="Approved by lead"
    )
    assert approved is True

    # Edit comment text
    edited = verification_service.edit_comment_text(
        comment_id=cmt_id, new_text="Missing pipe support at H-04", reviewer_id="USR-123"
    )
    assert edited is True

    # Retrieve audit history from SQLite
    history = verification_service.get_audit_history(comment_id=cmt_id)
    assert len(history) == 2
    assert history[0].action == "approve"
    assert history[0].old_value == "Pending"
    assert history[0].new_value == "Approved"
    assert history[1].action == "edit_text"
    assert history[1].old_value == "Missing pipe support"
    assert history[1].new_value == "Missing pipe support at H-04"


def test_category_fk_auto_resolution(temp_db):
    comment_repo = CommentRepository(temp_db)
    drawing_repo = DrawingRepository(temp_db)
    dto = _make_dwg_dto("dwg2.pdf", "def456hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)

    saved_cmt = comment_repo.save_comment(
        drawing_id=dwg["id"],
        page_number=1,
        raw_text="Check dimensions",
        bbox=(0.0, 0.0, 10.0, 10.0),
        category_name="Dimension",
    )

    comments = comment_repo.get_comments_for_drawing(dwg["id"])
    assert len(comments) == 1
    assert comments[0]["category_name"] == "Dimension"
    assert comments[0]["category_id"] is not None
    assert comments[0]["category_id"].startswith("CAT-")


def test_model_tracking_metadata(temp_db):
    comment_repo = CommentRepository(temp_db)
    drawing_repo = DrawingRepository(temp_db)
    dto = _make_dwg_dto("dwg3.pdf", "ghi789hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)

    now = datetime.utcnow()
    comment_repo.save_comment(
        drawing_id=dwg["id"],
        page_number=1,
        raw_text="Verify weld joint",
        bbox=(5.0, 5.0, 20.0, 20.0),
        confidence=0.88,
        category_name="Technical",
        classification_method="hybrid_nlp",
        model_name="TF-IDF + Naive Bayes",
        model_version="1.0.0",
        classification_confidence=0.92,
        detection_confidence=0.84,
        requires_human_review=False,
        classification_timestamp=now,
    )

    comments = comment_repo.get_comments_for_drawing(dwg["id"])
    assert len(comments) == 1
    c = comments[0]
    assert c["classification_method"] == "hybrid_nlp"
    assert c["model_name"] == "TF-IDF + Naive Bayes"
    assert c["model_version"] == "1.0.0"
    assert c["classification_confidence"] == 0.92
    assert c["detection_confidence"] == 0.84
    assert c["requires_human_review"] is False


def test_ocr_reprocessing_preserves_human_reviews(temp_db):
    comment_repo = CommentRepository(temp_db)
    drawing_repo = DrawingRepository(temp_db)
    dto = _make_dwg_dto("reproc.pdf", "jkl012hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)
    dwg_id = dwg["id"]

    # 1. Save unreviewed comment
    c1 = comment_repo.save_comment(
        drawing_id=dwg_id,
        page_number=1,
        raw_text="Unreviewed comment",
        bbox=(0.0, 0.0, 10.0, 10.0),
        status="Pending",
    )
    # 2. Save human-approved comment
    c2 = comment_repo.save_comment(
        drawing_id=dwg_id,
        page_number=1,
        raw_text="Human approved comment",
        bbox=(20.0, 20.0, 30.0, 30.0),
        status="Pending",
    )
    comment_repo.update_comment_status(c2["id"], "Approved", verified_by_human=True)

    # 3. Simulate OCR reprocessing (delete unreviewed)
    deleted_count = comment_repo.delete_comments_for_drawing(dwg_id)
    assert deleted_count == 1

    remaining = comment_repo.get_comments_for_drawing(dwg_id)
    assert len(remaining) == 1
    assert remaining[0]["id"] == c2["id"]
    assert remaining[0]["status"] == "Approved"


def test_excel_export_key_mapping(temp_db, tmp_path):
    comment_repo = CommentRepository(temp_db)
    drawing_repo = DrawingRepository(temp_db)
    export_service = ExportService(comment_repo, None)

    dto = _make_dwg_dto("excel.pdf", "mno345hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)
    dwg_id = dwg["id"]

    comment_repo.save_comment(
        drawing_id=dwg_id,
        page_number=1,
        raw_text="RAW OCR TEXT",
        cleaned_text="Cleaned human edit text",
        bbox=(0.0, 0.0, 10.0, 10.0),
        category_name="Drafting",
        confidence=0.95,
        status="Approved",
    )

    out_file = str(tmp_path / "export_test.xlsx")
    config = ExportConfigDTO(
        drawing_id=dwg_id,
        format=ExportFormat.EXCEL,
        output_path=out_file,
        include_confidence_scores=True,
    )

    res = export_service.export_drawing_comments(config)
    assert res.success is True
    assert res.total_rows == 1
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 0


def test_analytics_sql_aggregation(temp_db):
    analytics = AnalyticsService(temp_db)
    comment_repo = CommentRepository(temp_db)
    drawing_repo = DrawingRepository(temp_db)

    dto = _make_dwg_dto("analytics.pdf", "pqr678hash")
    dwg = drawing_repo.save_drawing_from_dto(dto)

    comment_repo.save_comment(
        drawing_id=dwg["id"],
        page_number=1,
        raw_text="High conf comment",
        bbox=(0.0, 0.0, 10.0, 10.0),
        confidence=0.90,
        status="Approved",
    )
    comment_repo.save_comment(
        drawing_id=dwg["id"],
        page_number=1,
        raw_text="Low conf comment",
        bbox=(10.0, 10.0, 20.0, 20.0),
        confidence=0.50,
        status="Pending",
    )

    kpis = analytics.get_global_kpis()
    assert kpis.total_drawings == 1
    assert kpis.total_comments == 2
    assert kpis.approved_count == 1
    assert kpis.pending_count == 1
    assert pytest.approx(kpis.avg_confidence, 0.01) == 0.70


def test_app_controller_normalise_comment():
    controller = AppController()
    db_dict = {
        "id": "CMT-001",
        "drawing_id": "DWG-100",
        "page_number": 2,
        "raw_text": "RAW OCR ERROR TEXT",
        "cleaned_text": "Cleaned corrected text",
        "category_name": "Technical",
        "confidence": 0.85,
        "status": "Approved",
        "label": "comment_red",
        "bbox": (10.0, 20.0, 30.0, 40.0),
        "user_id": "USR-01",
        "created_at": "2026-09-10 10:00:00",
        "is_verified_by_human": True,
    }

    norm = controller.normalise_comment(db_dict)
    assert norm["ocr_text"] == "Cleaned corrected text"
    assert norm["raw_text"] == "RAW OCR ERROR TEXT"
    assert norm["cleaned_text"] == "Cleaned corrected text"
    assert norm["category"] == "Technical"
    assert norm["is_verified"] is True
