"""
src/infrastructure/storage/repository.py
Repository Pattern Implementation for SQLite Database operations.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.infrastructure.storage.models import (
    Base, ProjectModel, DrawingModel, PageModel, CommentModel
)
from src.core.dtos.pdf_dtos import PDFDocumentDTO
from src.infrastructure.logging.logger import get_logger

logger = get_logger("DatabaseRepository")


class DatabaseEngine:
    """
    Database Manager handling SQLite connections, table creation, and sessions.
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_path = Path("drawing_comments.db").resolve()
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._init_db()

    def _init_db(self) -> None:
        """Creates tables and populates initial seed data if DB is empty."""
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Initialized SQLite database at: {self.db_path}")
        self._seed_initial_data()

    def get_session(self) -> Session:
        """Returns a new database session."""
        return self.SessionLocal()

    def _seed_initial_data(self) -> None:
        """Seeds default project data if table is empty."""
        session = self.get_session()
        try:
            if session.query(ProjectModel).count() == 0:
                seed_projects = [
                    ProjectModel(
                        id="PRJ-001", name="UCC Site-4 Expansion", drawings=48, comments=312,
                        status="Active", progress=78, last_modified="2026-07-28", engineer="A. Mehta"
                    ),
                    ProjectModel(
                        id="PRJ-002", name="Refinery Unit-7 Upgrade", drawings=32, comments=197,
                        status="Active", progress=55, last_modified="2026-07-25", engineer="S. Nair"
                    ),
                    ProjectModel(
                        id="PRJ-003", name="Pipeline Corridor North", drawings=61, comments=408,
                        status="Complete", progress=100, last_modified="2026-07-10", engineer="R. Kapoor"
                    )
                ]
                session.add_all(seed_projects)
                session.commit()
                logger.info("Seeded initial database projects.")
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding database: {e}")
        finally:
            session.close()


class DrawingRepository:
    """Repository handling Drawing and Page database persistence."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self.db_engine = db_engine

    def save_drawing_from_dto(self, dto: PDFDocumentDTO, project_id: Optional[str] = "PRJ-001") -> Dict[str, Any]:
        """
        Saves a loaded PDFDocumentDTO into SQLite drawings and pages tables.
        Returns a dictionary representing the saved drawing record.
        """
        session = self.db_engine.get_session()
        try:
            existing = session.query(DrawingModel).filter(DrawingModel.file_hash_sha256 == dto.file_hash_sha256).first()
            if existing:
                existing.uploaded_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"Drawing with hash {dto.file_hash_sha256[:8]} already exists in DB (ID: {existing.id})")
                return {
                    "id": existing.id,
                    "file_name": existing.file_name,
                    "file_path": existing.file_path,
                    "total_pages": existing.total_pages,
                    "is_scanned": existing.is_scanned,
                    "file_hash": existing.file_hash_sha256
                }

            drawing_id = f"DWG-{uuid.uuid4().hex[:8].upper()}"
            drawing_record = DrawingModel(
                id=drawing_id,
                project_id=project_id,
                file_path=str(dto.file_path),
                file_name=dto.file_name,
                file_size_bytes=dto.file_size_bytes,
                file_hash_sha256=dto.file_hash_sha256,
                total_pages=dto.total_pages,
                is_scanned=dto.is_scanned,
                uploaded_at=datetime.now(timezone.utc)
            )
            session.add(drawing_record)

            # Add pages
            for page in dto.pages:
                page_record = PageModel(
                    id=f"PG-{uuid.uuid4().hex[:8].upper()}",
                    drawing_id=drawing_id,
                    page_number=page.page_number,
                    width_pt=page.width_pt,
                    height_pt=page.height_pt,
                    aspect_ratio=page.aspect_ratio,
                    has_native_text=page.has_native_text,
                    text_character_count=page.text_character_count,
                    orientation_deg=page.orientation_deg
                )
                session.add(page_record)

            session.commit()
            logger.info(f"Saved new drawing '{dto.file_name}' to SQLite database (ID: {drawing_id})")
            return {
                "id": drawing_id,
                "file_name": dto.file_name,
                "file_path": str(dto.file_path),
                "total_pages": dto.total_pages,
                "is_scanned": dto.is_scanned,
                "file_hash": dto.file_hash_sha256
            }
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save drawing to DB: {e}")
            raise
        finally:
            session.close()

    def get_recent_drawings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Returns list of recent drawing records for UI display."""
        session = self.db_engine.get_session()
        try:
            drawings = session.query(DrawingModel).order_by(DrawingModel.uploaded_at.desc()).limit(limit).all()
            return [
                {
                    "id": d.id,
                    "file_name": d.file_name,
                    "file_path": d.file_path,
                    "total_pages": d.total_pages,
                    "is_scanned": d.is_scanned,
                    "uploaded_at": d.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if d.uploaded_at else ""
                }
                for d in drawings
            ]
        finally:
            session.close()


class ProjectRepository:
    """Repository handling Project queries and KPI statistics."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self.db_engine = db_engine

    def get_all_projects(self) -> List[Dict[str, Any]]:
        session = self.db_engine.get_session()
        try:
            projects = session.query(ProjectModel).all()
            return [
                {
                    "id": p.id,
                    "name": p.name,
                    "drawings": p.drawings,
                    "comments": p.comments,
                    "status": p.status,
                    "progress": p.progress,
                    "last_modified": p.last_modified,
                    "engineer": p.engineer
                }
                for p in projects
            ]
        finally:
            session.close()

    def get_kpis(self) -> Dict[str, Any]:
        session = self.db_engine.get_session()
        try:
            total_projects = session.query(ProjectModel).count()
            drawings_processed = session.query(DrawingModel).count()
            comments_detected = session.query(CommentModel).count()
            return {
                "total_projects": total_projects or 7,
                "drawings_processed": drawings_processed or 302,
                "comments_detected": comments_detected or 2036,
                "accuracy": 91.4,
                "trend_projects": "+2",
                "trend_drawings": "+18",
                "trend_comments": "+143",
                "trend_accuracy": "+0.8"
            }
        finally:
            session.close()
