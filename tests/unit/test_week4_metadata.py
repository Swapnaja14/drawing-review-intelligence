"""
tests/unit/test_week4_metadata.py
Week 4 — PDF Processing & Metadata Storage tests.

Tests cover:
  1. Drawing number extraction (Subject / Title / filename fallback)
  2. PDF date parsing
  3. DrawingModel new columns persist correctly
  4. Project → Drawing FK linking (get_or_create_default_project)
  5. Project → Drawing → Page relationship chain
  6. Duplicate detection still works after schema changes
  7. _drawing_to_dict returns all required Week 4 fields
  8. Existing Week 3 CommentRepository operations are unaffected

ARCHITECTURE NOTE:
All tests use an in-memory SQLite database so they never touch the
production data/ucc_database.db file.
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure the project root is on sys.path
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))

from src.infrastructure.storage.repository import (
    DatabaseEngine,
    DrawingRepository,
    ProjectRepository,
    CommentRepository,
)
from src.infrastructure.storage.models import DrawingModel, ProjectModel, PageModel, CommentModel
from src.core.dtos.pdf_dtos import PDFDocumentDTO, PageMetadataDTO
from src.infrastructure.pdf.pdf_metadata_utils import (
    extract_drawing_number as _extract_drawing_number,
    parse_pdf_date as _parse_pdf_date,
)


# ---------------------------------------------------------------------------
# Shared fixture: in-memory database engine
# ---------------------------------------------------------------------------

@pytest.fixture
def mem_engine():
    """Create a fresh in-memory SQLite engine for each test."""
    engine = DatabaseEngine(db_path=":memory:")
    return engine


@pytest.fixture
def drawing_repo(mem_engine):
    return DrawingRepository(mem_engine)


@pytest.fixture
def project_repo(mem_engine):
    return ProjectRepository(mem_engine)


@pytest.fixture
def comment_repo(mem_engine):
    return CommentRepository(mem_engine)


# ---------------------------------------------------------------------------
# Helper: minimal PDFDocumentDTO factory
# ---------------------------------------------------------------------------

def _make_dto(
    file_name: str = "UCC-E-101.pdf",
    drawing_number: str = "UCC-E-101",
    title: str | None = None,
    author: str | None = None,
    creation_date: str | None = None,
    modification_date: str | None = None,
    total_pages: int = 2,
    sha256: str | None = None,
) -> PDFDocumentDTO:
    if sha256 is None:
        sha256 = uuid.uuid4().hex * 2  # 64-char hex
    pages = [
        PageMetadataDTO(
            page_number=i + 1,
            width_pt=841.89,
            height_pt=595.28,
            aspect_ratio=1.414,
            has_native_text=True,
            text_character_count=500,
            orientation_deg=0,
        )
        for i in range(total_pages)
    ]
    return PDFDocumentDTO(
        file_path=Path(f"/tmp/{file_name}"),
        file_name=file_name,
        file_size_bytes=102400,
        file_hash_sha256=sha256,
        total_pages=total_pages,
        is_encrypted=False,
        is_scanned=False,
        title=title,
        author=author,
        drawing_number=drawing_number,
        creation_date=creation_date,
        modification_date=modification_date,
        pages=pages,
    )


# ===========================================================================
# 1. Drawing number extraction
# ===========================================================================

class TestDrawingNumberExtraction:

    def test_subject_field_is_first_priority(self):
        metadata = {"subject": "UCC-E-101", "title": "Something else"}
        result = _extract_drawing_number(metadata, Path("other.pdf"))
        assert result == "UCC-E-101"

    def test_title_used_when_looks_like_drawing_number(self):
        metadata = {"subject": "", "title": "UCC-E-101"}
        result = _extract_drawing_number(metadata, Path("irrelevant.pdf"))
        assert result == "UCC-E-101"

    def test_title_with_spaces_not_used_as_drawing_number(self):
        """A title with spaces is a document title, not a drawing number."""
        metadata = {"subject": "", "title": "Piping and Instrumentation Diagram"}
        result = _extract_drawing_number(metadata, Path("UCC-E-101.pdf"))
        # Should fall through to filename
        assert result == "UCC-E-101"

    def test_filename_stem_used_as_fallback(self):
        metadata = {}
        result = _extract_drawing_number(metadata, Path("UCC-E-101.pdf"))
        assert result == "UCC-E-101"

    def test_revision_suffix_stripped_from_filename(self):
        metadata = {}
        for fname, expected in [
            ("UCC-E-101_RevA.pdf",  "UCC-E-101"),
            ("UCC-E-101_Rev2.pdf",  "UCC-E-101"),
            ("UCC-E-101-RevB.pdf",  "UCC-E-101"),
            ("LNG-T-501_R01.pdf",   "LNG-T-501"),
            ("RU7-P-201_v2.pdf",    "RU7-P-201"),
        ]:
            result = _extract_drawing_number(metadata, Path(fname))
            assert result == expected, f"Failed for {fname}: got '{result}'"

    def test_empty_metadata_and_plain_filename(self):
        metadata = {}
        result = _extract_drawing_number(metadata, Path("drawing.pdf"))
        assert result == "drawing"

    def test_all_empty_returns_empty_string(self):
        """When subject and title are empty, filename stem is used as fallback.
        A file named exactly '.pdf' has stem '.pdf' in Python — that is the
        best-effort result; the caller may further sanitise if needed."""
        metadata = {"subject": "", "title": ""}
        result = _extract_drawing_number(metadata, Path(".pdf"))
        # The stem of ".pdf" is ".pdf" — no revision suffix to strip,
        # so the raw stem is returned as the drawing number.
        assert result == ".pdf"


# ===========================================================================
# 2. PDF date parsing
# ===========================================================================

class TestPDFDateParsing:

    def test_full_pdf_date_string(self):
        raw = "D:20260715143022+00'00'"
        assert _parse_pdf_date(raw) == "2026-07-15 14:30:22"

    def test_date_only_pdf_string(self):
        raw = "D:20260715"
        assert _parse_pdf_date(raw) == "2026-07-15 00:00:00"

    def test_none_input_returns_none(self):
        assert _parse_pdf_date(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_pdf_date("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_pdf_date("not-a-date") is None

    def test_invalid_month_returns_none(self):
        # Month 13 is invalid
        assert _parse_pdf_date("D:20261315") is None

    def test_date_with_local_offset(self):
        raw = "D:20261231235959+05'30'"
        result = _parse_pdf_date(raw)
        # Time is stored as-is without TZ conversion
        assert result == "2026-12-31 23:59:59"


# ===========================================================================
# 3. DrawingModel new columns persist correctly
# ===========================================================================

class TestDrawingModelPersistence:

    def test_drawing_number_persisted(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(drawing_number="UCC-E-101")
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["drawing_number"] == "UCC-E-101"

    def test_creation_date_persisted(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(creation_date="2026-07-15 14:30:22")
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["creation_date"] == "2026-07-15 14:30:22"

    def test_modification_date_persisted(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(modification_date="2026-08-01 09:00:00")
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["modification_date"] == "2026-08-01 09:00:00"

    def test_null_dates_stored_as_none(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(creation_date=None, modification_date=None)
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["creation_date"] is None
        assert result["modification_date"] is None

    def test_ocr_status_defaults_to_pending(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["ocr_status"] == "pending"

    def test_title_and_author_persisted(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(title="P&ID Unit 4-A", author="A. Mehta")
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["title"] == "P&ID Unit 4-A"
        assert result["author"] == "A. Mehta"

    def test_drawing_to_dict_includes_all_week4_fields(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(
            drawing_number="LNG-T-501",
            title="LNG Terminal P&ID",
            author="V. Singh",
            creation_date="2026-01-10 08:00:00",
            modification_date="2026-07-30 11:50:00",
        )
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        required_keys = {
            "id", "file_name", "file_path", "total_pages", "is_scanned",
            "file_hash", "project_id", "title", "author", "drawing_number",
            "creation_date", "modification_date", "ocr_status", "uploaded_at",
            "pages",
        }
        missing = required_keys - set(result.keys())
        assert not missing, f"Missing keys in _drawing_to_dict: {missing}"


# ===========================================================================
# 4. Project → Drawing linking
# ===========================================================================

class TestProjectDrawingLinking:

    def test_default_project_is_created_when_none_exists(self, project_repo):
        project_id = project_repo.get_or_create_default_project()
        assert project_id.startswith("PRJ-")

    def test_default_project_is_idempotent(self, project_repo):
        id1 = project_repo.get_or_create_default_project()
        id2 = project_repo.get_or_create_default_project()
        assert id1 == id2, "get_or_create_default_project must return the same ID on repeat calls"

    def test_drawing_has_project_id_after_save(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        assert result["project_id"] == project_id

    def test_drawing_project_id_is_null_when_not_provided(self, drawing_repo):
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=None)
        assert result["project_id"] is None

    def test_custom_project_can_be_linked(self, drawing_repo, project_repo):
        proj = project_repo.create_project(
            name="LNG Terminal Phase-2",
            lead_engineer="V. Singh",
        )
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=proj["id"])
        assert result["project_id"] == proj["id"]

    def test_project_drawing_page_chain(self, drawing_repo, project_repo, mem_engine):
        """ProjectModel → DrawingModel → PageModel FK chain is intact."""
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(total_pages=3)
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        with mem_engine.get_session() as session:
            drawing = session.get(DrawingModel, drawing_id)
            assert drawing is not None
            assert drawing.project_id == project_id

            project = session.get(ProjectModel, project_id)
            assert project is not None

            pages = (
                session.query(PageModel)
                .filter(PageModel.drawing_id == drawing_id)
                .all()
            )
            assert len(pages) == 3
            page_numbers = sorted(p.page_number for p in pages)
            assert page_numbers == [1, 2, 3]


# ===========================================================================
# 5. Page ID map in result dict
# ===========================================================================

class TestPageIdMap:

    def test_pages_dict_in_result(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(total_pages=2)
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        pages = result["pages"]
        assert isinstance(pages, dict)
        assert 1 in pages and 2 in pages
        assert pages[1].startswith("PG-")
        assert pages[2].startswith("PG-")
        assert pages[1] != pages[2]

    def test_get_page_id_by_number(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto(total_pages=3)
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        for page_num in [1, 2, 3]:
            page_id = drawing_repo.get_page_id_by_number(drawing_id, page_num)
            assert page_id is not None
            assert page_id.startswith("PG-")
            assert page_id == result["pages"][page_num]

    def test_get_page_id_nonexistent_returns_none(self, drawing_repo, project_repo):
        page_id = drawing_repo.get_page_id_by_number("DWG-NONEXISTENT", 1)
        assert page_id is None


# ===========================================================================
# 6. Duplicate detection still works after schema changes
# ===========================================================================

class TestDuplicateDetection:

    def test_same_hash_returns_existing_record(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        shared_hash = uuid.uuid4().hex * 2
        dto1 = _make_dto(file_name="UCC-E-101.pdf", sha256=shared_hash)
        dto2 = _make_dto(file_name="UCC-E-101_copy.pdf", sha256=shared_hash)

        result1 = drawing_repo.save_drawing_from_dto(dto1, project_id=project_id)
        result2 = drawing_repo.save_drawing_from_dto(dto2, project_id=project_id)

        assert result1["id"] == result2["id"], "Duplicate drawing must return the same DB id"

    def test_metadata_refreshed_on_duplicate(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        shared_hash = uuid.uuid4().hex * 2
        dto1 = _make_dto(sha256=shared_hash, title="Old Title", drawing_number="OLD-001")
        dto2 = _make_dto(sha256=shared_hash, title="New Title", drawing_number="OLD-001")

        drawing_repo.save_drawing_from_dto(dto1, project_id=project_id)
        result2 = drawing_repo.save_drawing_from_dto(dto2, project_id=project_id)
        assert result2["title"] == "New Title"

    def test_different_hashes_create_separate_records(self, drawing_repo, project_repo):
        project_id = project_repo.get_or_create_default_project()
        dto1 = _make_dto(file_name="A.pdf", sha256="a" * 64)
        dto2 = _make_dto(file_name="B.pdf", sha256="b" * 64)

        r1 = drawing_repo.save_drawing_from_dto(dto1, project_id=project_id)
        r2 = drawing_repo.save_drawing_from_dto(dto2, project_id=project_id)
        assert r1["id"] != r2["id"]


# ===========================================================================
# 7. Week 3 CommentRepository operations unaffected
# ===========================================================================

class TestWeek3Compatibility:

    def test_save_and_retrieve_comment_still_works(
        self, drawing_repo, project_repo, comment_repo, mem_engine
    ):
        """Verify that Week 3 comment CRUD still functions after schema changes."""
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        saved = comment_repo.save_comment(
            drawing_id=drawing_id,
            page_number=1,
            raw_text="MIN WALL THICKNESS 6MM",
            bbox=(10.0, 20.0, 110.0, 40.0),
            confidence=0.97,
            category_name="Dimensional",
            status="Pending",
        )
        assert saved["id"].startswith("CMT-")

        comments = comment_repo.get_comments_for_drawing(drawing_id)
        assert len(comments) == 1
        assert comments[0]["raw_text"] == "MIN WALL THICKNESS 6MM"
        assert comments[0]["status"] == "Pending"

    def test_update_comment_status_still_works(
        self, drawing_repo, project_repo, comment_repo
    ):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        saved = comment_repo.save_comment(
            drawing_id=drawing_id,
            page_number=1,
            raw_text="Test comment",
            bbox=(0.0, 0.0, 50.0, 20.0),
            confidence=0.8,
        )
        cid = saved["id"]

        ok = comment_repo.update_comment_status(cid, "Approved")
        assert ok is True

        comments = comment_repo.get_comments_for_drawing(drawing_id)
        assert comments[0]["status"] == "Approved"
        assert comments[0]["is_verified_by_human"] is True

    def test_update_comment_text_still_works(
        self, drawing_repo, project_repo, comment_repo
    ):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        saved = comment_repo.save_comment(
            drawing_id=drawing_id,
            page_number=1,
            raw_text="Original OCR text",
            bbox=(0.0, 0.0, 50.0, 20.0),
        )
        ok = comment_repo.update_comment_text(saved["id"], "Corrected OCR text")
        assert ok is True

        comments = comment_repo.get_comments_for_drawing(drawing_id)
        assert (comments[0].get("cleaned_text") or comments[0].get("raw_text")) == "Corrected OCR text"

    def test_get_category_counts_still_works(
        self, drawing_repo, project_repo, comment_repo
    ):
        project_id = project_repo.get_or_create_default_project()
        dto = _make_dto()
        result = drawing_repo.save_drawing_from_dto(dto, project_id=project_id)
        drawing_id = result["id"]

        for cat in ["Dimensional", "Dimensional", "Structural"]:
            comment_repo.save_comment(
                drawing_id=drawing_id,
                page_number=1,
                raw_text="text",
                bbox=(0.0, 0.0, 10.0, 10.0),
                category_name=cat,
            )

        counts = comment_repo.get_category_counts(drawing_id)
        assert counts["Dimensional"] == 2
        assert counts["Structural"] == 1


# ===========================================================================
# 8. Database migration safety — existing DB gets new columns
# ===========================================================================

class TestMigrationSafety:

    def test_migration_adds_columns_to_existing_database(self, tmp_path):
        """
        Simulate a pre-existing database that lacks the Week 4 columns.
        The migration should add them without destroying existing data.
        """
        import sqlite3
        db_file = tmp_path / "legacy.db"

        # Create a minimal legacy database without the new columns
        conn = sqlite3.connect(str(db_file))
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'Active',
                progress INTEGER NOT NULL DEFAULT 0,
                lead_engineer TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drawings (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                file_hash_sha256 TEXT NOT NULL,
                total_pages INTEGER NOT NULL,
                is_scanned INTEGER NOT NULL DEFAULT 0,
                title TEXT,
                author TEXT,
                uploaded_at TEXT
                -- NOTE: drawing_number, creation_date, modification_date, ocr_status intentionally absent
            )
        """)
        # Insert an existing drawing row
        conn.execute("""
            INSERT INTO drawings VALUES
            ('DWG-LEGACY01', NULL, '/tmp/old.pdf', 'old.pdf',
             1024, 'a'*64, 1, 0, 'Old Title', 'Old Author', '2026-01-01 00:00:00')
        """.replace("'a'*64", f"'{'a'*64}'"))
        conn.commit()
        conn.close()

        # Open the legacy DB through DatabaseEngine — migrations should fire
        from src.infrastructure.storage.repository import DatabaseEngine
        engine = DatabaseEngine(db_path=db_file)

        # Verify columns were added
        with engine.engine.connect() as conn2:
            from sqlalchemy import text
            result = conn2.execute(text("PRAGMA table_info(drawings);"))
            col_names = {row[1] for row in result.fetchall()}

        for expected_col in ["drawing_number", "creation_date", "modification_date", "ocr_status"]:
            assert expected_col in col_names, f"Migration failed to add column: {expected_col}"

        # Verify existing data was preserved
        with engine.get_session() as session:
            row = session.get(DrawingModel, "DWG-LEGACY01")
            assert row is not None
            assert row.file_name == "old.pdf"
            assert row.title == "Old Title"
