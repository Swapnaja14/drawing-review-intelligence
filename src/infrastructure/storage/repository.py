"""
src/infrastructure/storage/repository.py
SQLAlchemy 2.x session factory, engine initialisation, and repository classes.

Database file: data/ucc_database.db  (relative to the project root)
The data/ directory is created automatically if it does not exist.
No seed / mock data is inserted anywhere in this module.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.core.dtos.pdf_dtos import PDFDocumentDTO
from src.infrastructure.logging.logger import get_logger
from src.infrastructure.storage.models import (
    Base,
    CommentModel,
    CommentAuditLogModel,
    DrawingModel,
    PageModel,
    ProjectModel,
    CategoryModel,
    UserModel,
)

logger = get_logger("DatabaseRepository")

# ---------------------------------------------------------------------------
# Resolve the canonical database path once at import time.
# Works on Windows (pathlib handles separators) and Linux/macOS alike.
# ---------------------------------------------------------------------------

# __file__ is  …/src/infrastructure/storage/repository.py
# project root is four levels up
_PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]
_DEFAULT_DB_PATH: Path = _PROJECT_ROOT / "data" / "ucc_database.db"


# ---------------------------------------------------------------------------
# DatabaseEngine — engine + session factory
# ---------------------------------------------------------------------------

class DatabaseEngine:
    """
    Manages the SQLite engine and SQLAlchemy session factory.

    Parameters
    ----------
    db_path:
        Absolute or relative path to the SQLite file.
        Defaults to  <project_root>/data/ucc_database.db.
    echo:
        Pass ``True`` to log all generated SQL (useful for debugging).
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        echo: bool = False,
    ) -> None:
        # Special case: SQLite in-memory database (used in tests)
        # ":memory:" must be passed directly to SQLAlchemy as-is.
        # Do not resolve it as a filesystem path or attempt mkdir.
        _IN_MEMORY = db_path is not None and str(db_path).strip() == ":memory:"

        if _IN_MEMORY:
            self.db_path = Path(":memory:")
            db_url = "sqlite:///:memory:"
        else:
            self.db_path = Path(db_path).resolve() if db_path else _DEFAULT_DB_PATH
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{self.db_path}"

        self.engine = create_engine(
            db_url,
            echo=echo,
            connect_args={"check_same_thread": False},
        )

        # Enable WAL mode and foreign-key enforcement for every new connection
        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

        self.SessionLocal: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        self._init_db()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_session(self) -> Session:
        """Return a new SQLAlchemy Session.  Caller is responsible for closing it."""
        return self.SessionLocal()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        """Create all tables declared in models.py (idempotent) and apply migrations."""
        Base.metadata.create_all(bind=self.engine)
        self._run_migrations()
        logger.info(f"SQLite database ready at: {self.db_path}")

    def _run_migrations(self) -> None:
        """
        Ensure newly added columns exist in existing SQLite databases.

        This is a lightweight forward-only migration approach consistent with
        the existing pattern already used for the 'label' column.
        Only additive (non-destructive) ALTER TABLE statements are used.
        Existing data is never deleted or modified.

        ARCHITECTURE NOTE:
        If the project later adopts Alembic or another migration tool, these
        inline migrations should be replaced. Do not add destructive migrations
        here — use a dedicated migration tool for schema changes that remove or
        rename columns.
        """
        try:
            with self.engine.begin() as conn:
                # ── Inspect existing columns ──────────────────────
                result  = conn.execute(text("PRAGMA table_info(comments);"))
                comment_cols = {row[1] for row in result.fetchall()}

                result  = conn.execute(text("PRAGMA table_info(drawings);"))
                drawing_cols = {row[1] for row in result.fetchall()}

                # ── comments table migrations ─────────────────────
                if comment_cols and "label" not in comment_cols:
                    logger.info("Migration: adding 'label' column to 'comments'")
                    conn.execute(
                        text("ALTER TABLE comments ADD COLUMN label VARCHAR(50) DEFAULT 'comment_red';")
                    )

                # ── drawings table migrations (Week 4) ────────────
                if drawing_cols:
                    if "drawing_number" not in drawing_cols:
                        logger.info("Migration: adding 'drawing_number' column to 'drawings'")
                        conn.execute(
                            text("ALTER TABLE drawings ADD COLUMN drawing_number VARCHAR(100);")
                        )
                    if "creation_date" not in drawing_cols:
                        logger.info("Migration: adding 'creation_date' column to 'drawings'")
                        conn.execute(
                            text("ALTER TABLE drawings ADD COLUMN creation_date VARCHAR(19);")
                        )
                    if "modification_date" not in drawing_cols:
                        logger.info("Migration: adding 'modification_date' column to 'drawings'")
                        conn.execute(
                            text("ALTER TABLE drawings ADD COLUMN modification_date VARCHAR(19);")
                        )
                    if "ocr_status" not in drawing_cols:
                        logger.info("Migration: adding 'ocr_status' column to 'drawings'")
                        conn.execute(
                            text("ALTER TABLE drawings ADD COLUMN ocr_status VARCHAR(50) DEFAULT 'pending';")
                        )

                # ── comment_audit_log table (Week 7) ─────────────
                # Base.metadata.create_all() handles creation for new DBs.
                # For existing DBs that pre-date Week 7, we create explicitly.
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS comment_audit_log (
                        id                 TEXT PRIMARY KEY,
                        comment_id         TEXT REFERENCES comments(id) ON DELETE SET NULL,
                        action             TEXT NOT NULL,
                        field_changed      TEXT,
                        old_value          TEXT,
                        new_value          TEXT,
                        changed_by_user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
                        changed_at         TEXT NOT NULL,
                        notes              TEXT
                    );
                """))
                # Indexes for comment_audit_log (CREATE INDEX IF NOT EXISTS is safe)
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_audit_comment_id ON comment_audit_log(comment_id);"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_audit_changed_at ON comment_audit_log(changed_at);"
                ))
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_audit_action ON comment_audit_log(action);"
                ))

        except Exception as exc:
            logger.warning(f"Database migration check failed: {exc}")


# ---------------------------------------------------------------------------
# DrawingRepository
# ---------------------------------------------------------------------------

class DrawingRepository:
    """Persistence operations for Drawing and Page records."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def save_drawing_from_dto(
        self,
        dto: PDFDocumentDTO,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Persist a PDFDocumentDTO as a DrawingModel + PageModel records.

        If a drawing with the same SHA-256 hash already exists, metadata
        (title, author, drawing_number, dates) is refreshed and the existing
        record is returned — no duplicate drawing is inserted.

        Parameters
        ----------
        dto        : PDFDocumentDTO from the PDF adapter.
        project_id : Optional ProjectModel.id FK.  Pass the result of
                     ProjectRepository.get_or_create_default_project() when
                     no explicit project is selected by the user.

        Returns
        -------
        Dict with keys:
            id, file_name, file_path, total_pages, is_scanned, file_hash,
            project_id, drawing_number, title, author,
            creation_date, modification_date, ocr_status, uploaded_at,
            pages  — dict mapping {page_number (int): page_id (str)}

        INTEGRATION NOTE:
        The "id" value in the returned dict is the DrawingModel primary key
        ("DWG-XXXXXXXX"). This is the drawing_id that must be used for all
        subsequent CommentModel and PageModel associations.
        It is NOT the PDF filename or the drawing_number.
        """
        with self._db.get_session() as session:
            existing = (
                session.query(DrawingModel)
                .filter(DrawingModel.file_hash_sha256 == dto.file_hash_sha256)
                .first()
            )
            if existing:
                # Refresh mutable metadata on re-upload of the same file
                existing.uploaded_at       = datetime.now(timezone.utc)
                existing.title             = getattr(dto, "title", None)
                existing.author            = getattr(dto, "author", None)
                existing.drawing_number    = getattr(dto, "drawing_number", None) or None
                existing.creation_date     = getattr(dto, "creation_date", None)
                existing.modification_date = getattr(dto, "modification_date", None)
                # Refresh project link if a project is now available
                if project_id and not existing.project_id:
                    existing.project_id = project_id
                session.commit()
                logger.info(
                    f"Drawing already in DB (hash={dto.file_hash_sha256[:8]}, "
                    f"id={existing.id}) — metadata refreshed."
                )
                page_map = self._get_page_id_map(session, existing.id)
                return _drawing_to_dict(existing, page_map)

            drawing_id = f"DWG-{uuid.uuid4().hex[:8].upper()}"
            drawing = DrawingModel(
                id=drawing_id,
                project_id=project_id,
                file_path=str(dto.file_path),
                file_name=dto.file_name,
                file_size_bytes=dto.file_size_bytes,
                file_hash_sha256=dto.file_hash_sha256,
                total_pages=dto.total_pages,
                is_scanned=dto.is_scanned,
                title=getattr(dto, "title", None),
                author=getattr(dto, "author", None),
                drawing_number=getattr(dto, "drawing_number", None) or None,
                creation_date=getattr(dto, "creation_date", None),
                modification_date=getattr(dto, "modification_date", None),
                ocr_status="pending",
                uploaded_at=datetime.now(timezone.utc),
            )
            session.add(drawing)

            page_map: Dict[int, str] = {}
            for page_dto in dto.pages:
                page_id = f"PG-{uuid.uuid4().hex[:8].upper()}"
                session.add(
                    PageModel(
                        id=page_id,
                        drawing_id=drawing_id,
                        page_number=page_dto.page_number,
                        width_pt=page_dto.width_pt,
                        height_pt=page_dto.height_pt,
                        aspect_ratio=page_dto.aspect_ratio,
                        has_native_text=page_dto.has_native_text,
                        text_character_count=page_dto.text_character_count,
                        orientation_deg=page_dto.orientation_deg,
                    )
                )
                page_map[page_dto.page_number] = page_id

            session.commit()
            logger.info(
                f"Saved drawing '{dto.file_name}' → id={drawing_id}, "
                f"drawing_number='{drawing.drawing_number}', "
                f"{dto.total_pages} page(s), project_id={project_id}."
            )
            return _drawing_to_dict(drawing, page_map)

    def _get_page_id_map(
        self, session, drawing_id: str
    ) -> Dict[int, str]:
        """Return {page_number: page_id} for all pages of a drawing."""
        rows = (
            session.query(PageModel.page_number, PageModel.id)
            .filter(PageModel.drawing_id == drawing_id)
            .all()
        )
        return {row.page_number: row.id for row in rows}

    def get_page_id_by_number(
        self, drawing_id: str, page_number: int
    ) -> Optional[str]:
        """
        Return the PageModel.id ("PG-XXXXXXXX") for a specific page of a drawing.

        Parameters
        ----------
        drawing_id  : DrawingModel.id ("DWG-XXXXXXXX")
        page_number : 1-based page number

        Returns None if the drawing or page does not exist.

        INTEGRATION NOTE (Week 5):
        Use this method when saving CommentModel records to populate
        CommentModel.page_id so that comment ↔ page FK is correctly set.
        """
        with self._db.get_session() as session:
            row = (
                session.query(PageModel)
                .filter(
                    PageModel.drawing_id == drawing_id,
                    PageModel.page_number == page_number,
                )
                .first()
            )
            return row.id if row else None

    def get_recent_drawings(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recently uploaded drawings."""
        with self._db.get_session() as session:
            rows = (
                session.query(DrawingModel)
                .order_by(DrawingModel.uploaded_at.desc())
                .limit(limit)
                .all()
            )
            return [_drawing_to_dict(d) for d in rows]

    def get_drawing_by_id(self, drawing_id: str) -> Optional[Dict[str, Any]]:
        """Return a single drawing record by primary key, or None."""
        with self._db.get_session() as session:
            row = session.get(DrawingModel, drawing_id)
            return _drawing_to_dict(row) if row else None


# ---------------------------------------------------------------------------
# ProjectRepository
# ---------------------------------------------------------------------------

class ProjectRepository:
    """Persistence and query operations for Project records and KPI aggregates."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def get_all_projects(self) -> List[Dict[str, Any]]:
        """Return all projects ordered by creation date (newest first)."""
        with self._db.get_session() as session:
            rows = (
                session.query(ProjectModel)
                .order_by(ProjectModel.created_at.desc())
                .all()
            )
            return [_project_to_dict(p) for p in rows]

    def get_project_by_id(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Return a single project, or None if not found."""
        with self._db.get_session() as session:
            row = session.get(ProjectModel, project_id)
            return _project_to_dict(row) if row else None

    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        lead_engineer: Optional[str] = None,
        status: str = "Active",
    ) -> Dict[str, Any]:
        """Insert a new project and return its record."""
        with self._db.get_session() as session:
            project = ProjectModel(
                id=f"PRJ-{uuid.uuid4().hex[:8].upper()}",
                name=name,
                description=description,
                lead_engineer=lead_engineer,
                status=status,
                progress=0,
            )
            session.add(project)
            session.commit()
            logger.info(f"Created project '{name}' → id={project.id}")
            return _project_to_dict(project)

    def get_or_create_default_project(self) -> str:
        """
        Return the project_id of the single default project used when no
        explicit project is selected during a drawing upload.

        The default project is identified by the name "Default Project".
        If it does not exist it is created automatically.

        Returns
        -------
        str
            ProjectModel.id of the default project ("PRJ-XXXXXXXX").

        ARCHITECTURE NOTE:
        This method exists to satisfy the Week 4 requirement that every
        DrawingModel.project_id references a valid ProjectModel row.
        When a proper project-selection UI is implemented, callers should
        pass the user-chosen project_id directly to save_drawing_from_dto()
        instead of relying on this default.

        INTEGRATION WARNING:
        This returns a ProjectModel.id — NOT a drawing_id or drawing_number.
        Do NOT pass this value anywhere that expects DrawingModel.id.
        """
        _DEFAULT_PROJECT_NAME = "Default Project"
        with self._db.get_session() as session:
            row = (
                session.query(ProjectModel)
                .filter(ProjectModel.name == _DEFAULT_PROJECT_NAME)
                .first()
            )
            if row:
                return row.id

            project = ProjectModel(
                id=f"PRJ-{uuid.uuid4().hex[:8].upper()}",
                name=_DEFAULT_PROJECT_NAME,
                description="Automatically created default project for unassigned drawings.",
                status="Active",
                progress=0,
            )
            session.add(project)
            session.commit()
            logger.info(
                f"Created default project '{_DEFAULT_PROJECT_NAME}' → id={project.id}"
            )
            return project.id

    def get_kpis(self) -> Dict[str, Any]:
        """
        Return live KPI counts from the database.
        No hardcoded fallback values — all figures come from real rows.
        """
        with self._db.get_session() as session:
            total_projects    = session.query(ProjectModel).count()
            drawings_processed = session.query(DrawingModel).count()
            comments_detected  = session.query(CommentModel).count()

            # Accuracy: ratio of human-verified approved comments to all comments
            approved = (
                session.query(CommentModel)
                .filter(
                    CommentModel.status == "Approved",
                    CommentModel.is_verified_by_human.is_(True),
                )
                .count()
            )
            accuracy = (
                round((approved / comments_detected) * 100, 1)
                if comments_detected > 0
                else None
            )

            return {
                "total_projects":    total_projects,
                "drawings_processed": drawings_processed,
                "comments_detected":  comments_detected,
                "accuracy":          accuracy,
            }


# ---------------------------------------------------------------------------
# CategoryRepository
# ---------------------------------------------------------------------------

class CategoryRepository:
    """CRUD for comment classification categories."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def get_all_categories(self) -> List[Dict[str, Any]]:
        with self._db.get_session() as session:
            rows = session.query(CategoryModel).order_by(CategoryModel.name).all()
            return [
                {
                    "id":          c.id,
                    "name":        c.name,
                    "description": c.description,
                    "color_hex":   c.color_hex,
                }
                for c in rows
            ]

    def get_or_create_category(
        self,
        name: str,
        description: Optional[str] = None,
        color_hex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return an existing category by name, or create it."""
        with self._db.get_session() as session:
            row = (
                session.query(CategoryModel)
                .filter(CategoryModel.name == name)
                .first()
            )
            if row:
                return {"id": row.id, "name": row.name}

            cat = CategoryModel(
                id=f"CAT-{uuid.uuid4().hex[:8].upper()}",
                name=name,
                description=description,
                color_hex=color_hex,
            )
            session.add(cat)
            session.commit()
            logger.info(f"Created category '{name}' → id={cat.id}")
            return {"id": cat.id, "name": cat.name}


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

class UserRepository:
    """CRUD for user / reviewer records."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self._db.get_session() as session:
            rows = (
                session.query(UserModel)
                .filter(UserModel.is_active.is_(True))
                .order_by(UserModel.display_name)
                .all()
            )
            return [_user_to_dict(u) for u in rows]

    def get_or_create_user(
        self,
        username: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
        role: str = "Reviewer",
    ) -> Dict[str, Any]:
        """Return an existing user by username, or create them."""
        with self._db.get_session() as session:
            row = (
                session.query(UserModel)
                .filter(UserModel.username == username)
                .first()
            )
            if row:
                return _user_to_dict(row)

            user = UserModel(
                id=f"USR-{uuid.uuid4().hex[:8].upper()}",
                username=username,
                display_name=display_name or username,
                email=email,
                role=role,
            )
            session.add(user)
            session.commit()
            logger.info(f"Created user '{username}' → id={user.id}")
            return _user_to_dict(user)


# ---------------------------------------------------------------------------
# CommentRepository
# ---------------------------------------------------------------------------

class CommentRepository:
    """Persistence and query operations for Comment records."""

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def save_comment(
        self,
        drawing_id: str,
        page_number: int,
        raw_text: str,
        bbox: tuple[float, float, float, float],
        confidence: float = 0.0,
        category_id: Optional[str] = None,
        category_name: Optional[str] = "Uncategorized",
        page_id: Optional[str] = None,
        user_id: Optional[str] = None,
        cleaned_text: str = "",
        status: str = "Pending",
        label: str = "comment_red",
    ) -> Dict[str, Any]:
        """Persist a single extracted comment.

        Parameters
        ----------
        bbox:
            MUST be (x0, y0, x1, y1) in ABSOLUTE PDF POINT COORDINATES.
            1 point = 1/72 inch. Origin is top-left of page.
            x0=left, y0=top, x1=right, y1=bottom.

            Do NOT pass normalised (0-1) coordinates.
            Do NOT pass (x, y, width, height) format.

            PyMuPDF's extract_page_text_blocks() already returns (x0,y0,x1,y1)
            absolute points and is the correct source for this parameter.

            See docs/AGENT_INTEGRATION_GUIDELINES.md WARNING-009 for context.
        status:
            Must be one of: "Pending", "Approved", "Rejected", "Flagged".
            Default is "Pending" for all newly extracted comments.
        label:
            Detection label, e.g. "comment_red", "comment_blue", "native_redline".
        """
        with self._db.get_session() as session:
            comment = CommentModel(
                id=f"CMT-{uuid.uuid4().hex[:8].upper()}",
                drawing_id=drawing_id,
                page_id=page_id,
                category_id=category_id,
                user_id=user_id,
                page_number=page_number,
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                category_name=category_name,
                confidence=confidence,
                status=status,
                label=label,
                bbox_x0=bbox[0],
                bbox_y0=bbox[1],
                bbox_x1=bbox[2],
                bbox_y1=bbox[3],
            )
            session.add(comment)
            session.commit()
            return {"id": comment.id, "status": comment.status}

    def delete_comments_for_drawing(self, drawing_id: str) -> int:
        """
        Delete only PENDING (unreviewed) comments for a drawing before re-processing.

        WEEK 7 FIX:
        Previously this deleted ALL comments for a drawing, which destroyed
        human-reviewed (Approved/Rejected/Flagged) comments and their audit
        history on OCR reprocessing.

        Now only comments with status == "Pending" AND is_verified_by_human == False
        are deleted.  Human-reviewed comments are preserved.

        Returns
        -------
        int
            Number of comments deleted.
        """
        with self._db.get_session() as session:
            count = (
                session.query(CommentModel)
                .filter(
                    CommentModel.drawing_id == drawing_id,
                    CommentModel.status == "Pending",
                    CommentModel.is_verified_by_human.is_(False),
                )
                .delete(synchronize_session=False)
            )
            session.commit()
            logger.info(
                f"Deleted {count} pending unreviewed comment(s) for drawing '{drawing_id}'. "
                "Human-reviewed comments were preserved."
            )
            return count

    def get_comments_for_drawing(self, drawing_id: str) -> List[Dict[str, Any]]:
        with self._db.get_session() as session:
            rows = (
                session.query(CommentModel)
                .filter(CommentModel.drawing_id == drawing_id)
                .order_by(CommentModel.page_number, CommentModel.bbox_y0)
                .all()
            )
            return [_comment_to_dict(c) for c in rows]

    def get_comments_for_page(self, page_id: str) -> List[Dict[str, Any]]:
        with self._db.get_session() as session:
            rows = (
                session.query(CommentModel)
                .filter(CommentModel.page_id == page_id)
                .order_by(CommentModel.bbox_y0)
                .all()
            )
            return [_comment_to_dict(c) for c in rows]

    def update_comment_status(
        self,
        comment_id: str,
        status: str,
        verified_by_human: bool = True,
    ) -> bool:
        """
        Update the status of a single comment.

        Parameters
        ----------
        comment_id:
            The CommentModel primary key ("CMT-XXXXXXXX").
        status:
            Must be one of: "Pending", "Approved", "Rejected", "Flagged".
            Using any other value will store an unrecognised status that
            UI components (StatusChip, StatusDelegate) will not render
            correctly.
        verified_by_human:
            Set True when a human reviewer explicitly approves or rejects.
            Defaults to True for review-screen actions.

        Returns
        -------
        bool
            True if the record was found and updated, False if not found.

        # INTEGRATION NOTE:
        # This method is called from AppController.update_comment_status().
        # UI screens must never call this repository method directly.
        # Status vocabulary: "Pending" | "Approved" | "Rejected" | "Flagged"
        """
        _VALID_STATUSES = {"Pending", "Approved", "Rejected", "Flagged"}
        if status not in _VALID_STATUSES:
            logger.warning(
                f"update_comment_status: '{status}' is not a recognised status. "
                f"Expected one of {_VALID_STATUSES}."
            )

        with self._db.get_session() as session:
            row = session.get(CommentModel, comment_id)
            if row is None:
                logger.warning(f"update_comment_status: comment '{comment_id}' not found.")
                return False
            row.status = status
            row.is_verified_by_human = verified_by_human
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Comment '{comment_id}' status → '{status}', verified={verified_by_human}")
            return True

    def update_comment_text(self, comment_id: str, new_text: str) -> Optional[str]:
        """
        Persist a human-corrected text for a comment.

        IMPORTANT (Week 7):
        This method writes the corrected text to ``cleaned_text``, NOT to
        ``raw_text``.  ``raw_text`` represents the original OCR extraction and
        must never be overwritten by a human edit.

        Parameters
        ----------
        comment_id:
            The CommentModel primary key ("CMT-XXXXXXXX").
        new_text:
            The corrected text to store in cleaned_text.

        Returns
        -------
        Optional[str]
            The previous cleaned_text value (before the update), so the caller
            can log it as old_value in the audit log.
            Returns None if the comment was not found.

        # INTEGRATION NOTE:
        # This method is called from AppController.update_comment_text() and
        # VerificationService.edit_comment_text().
        # UI screens must never call this repository method directly.
        # raw_text is intentionally NOT modified here.
        """
        with self._db.get_session() as session:
            row = session.get(CommentModel, comment_id)
            if row is None:
                logger.warning(f"update_comment_text: comment '{comment_id}' not found.")
                return None
            old_text = row.cleaned_text or ""
            row.cleaned_text = new_text
            row.updated_at = datetime.now(timezone.utc)
            session.commit()
            logger.info(f"Comment '{comment_id}' cleaned_text updated ({len(new_text)} chars).")
            return old_text

    def get_comment_status(self, comment_id: str) -> Optional[str]:
        """
        Return the current status of a comment without loading the full record.
        Used by VerificationService to capture old_value before a status change.
        """
        with self._db.get_session() as session:
            row = session.get(CommentModel, comment_id)
            return row.status if row else None

    def get_category_counts(
        self, drawing_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Return comment counts grouped by category_name.

        Parameters
        ----------
        drawing_id:
            If provided, counts only comments for that drawing.
            If None, counts across all drawings in the database.

        Returns
        -------
        Dict[str, int]
            e.g. {"Dimensional": 42, "Structural": 18, ...}
            Returns an empty dict if no comments exist.

        # INTEGRATION NOTE:
        # Used by ClassificationPage (per-drawing counts) and AnalyticsPage
        # (all-drawing counts). Called through AppController.get_category_counts().
        # UI screens must never call this repository method directly.
        """
        with self._db.get_session() as session:
            query = session.query(
                CommentModel.category_name,
                # Use SQLAlchemy func.count for portability across DB backends
                __import__("sqlalchemy").func.count(CommentModel.id).label("cnt"),
            )
            if drawing_id is not None:
                query = query.filter(CommentModel.drawing_id == drawing_id)
            rows = query.group_by(CommentModel.category_name).all()
            return {
                (row.category_name or "Uncategorized"): row.cnt
                for row in rows
            }



# ---------------------------------------------------------------------------
# CommentAuditLogRepository  (Week 7)
# ---------------------------------------------------------------------------

class CommentAuditLogRepository:
    """
    Persistence and query operations for the comment_audit_log table.

    ARCHITECTURE NOTE:
    All audit writes must go through this repository.
    UI screens must never insert directly into comment_audit_log.
    VerificationService is the primary caller.
    """

    def __init__(self, db_engine: DatabaseEngine) -> None:
        self._db = db_engine

    def log_action(
        self,
        comment_id: str,
        action: str,
        field_changed: Optional[str] = None,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        changed_by_user_id: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Persist a single audit/history record.

        Parameters
        ----------
        comment_id : str
            CommentModel.id ("CMT-XXXXXXXX").
        action : str
            Action label — must match AuditAction constants:
            "approve" | "reject" | "flag" | "edit_text" | "edit_category"
        field_changed : str, optional
            Which CommentModel field changed, e.g. "status", "cleaned_text".
        old_value : str, optional
            Previous value. Must NOT be empty when the old value is known.
        new_value : str, optional
            New value after the change.
        changed_by_user_id : str, optional
            UserModel.id of the reviewer. None for system actions.
        notes : str
            Free-text notes.

        Returns
        -------
        dict with "id" of the created audit record.
        """
        with self._db.get_session() as session:
            entry = CommentAuditLogModel(
                id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
                comment_id=comment_id or None,
                action=action,
                field_changed=field_changed,
                old_value=old_value,
                new_value=new_value,
                changed_by_user_id=changed_by_user_id or None,
                changed_at=datetime.now(timezone.utc),
                notes=notes or None,
            )
            session.add(entry)
            session.commit()
            logger.info(
                f"Audit: comment='{comment_id}' action='{action}' "
                f"field='{field_changed}' by='{changed_by_user_id}'"
            )
            return {"id": entry.id, "action": action, "changed_at": entry.changed_at.isoformat()}

    def get_history_for_comment(
        self, comment_id: str
    ) -> List[Dict[str, Any]]:
        """
        Return all audit records for a comment, ordered oldest-first.

        Returns an empty list if the comment has no history or does not exist.
        """
        with self._db.get_session() as session:
            rows = (
                session.query(CommentAuditLogModel)
                .filter(CommentAuditLogModel.comment_id == comment_id)
                .order_by(CommentAuditLogModel.changed_at)
                .all()
            )
            return [_audit_entry_to_dict(r) for r in rows]

    def get_recent_actions(
        self,
        drawing_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Return recent audit actions, optionally scoped to a drawing.

        If drawing_id is given, only comments belonging to that drawing are
        included (via a JOIN on CommentModel).
        """
        with self._db.get_session() as session:
            query = session.query(CommentAuditLogModel).order_by(
                CommentAuditLogModel.changed_at.desc()
            )
            if drawing_id:
                query = (
                    query.join(
                        CommentModel,
                        CommentAuditLogModel.comment_id == CommentModel.id,
                    )
                    .filter(CommentModel.drawing_id == drawing_id)
                )
            rows = query.limit(limit).all()
            return [_audit_entry_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Private serialisation helpers
# ---------------------------------------------------------------------------

def _drawing_to_dict(
    d: DrawingModel,
    page_map: Optional[Dict[int, str]] = None,
) -> Dict[str, Any]:
    """
    Serialise a DrawingModel to a plain dict for use by the application layer.

    The optional page_map argument — {page_number: page_id} — is included in
    the result under the "pages" key so that the workflow engine can pass the
    correct page_id to each CommentRepository.save_comment() call.

    INTEGRATION NOTE (Week 5):
    Consumers that need to persist comments should use result["pages"][page_num]
    to obtain the PageModel.id for each page before calling save_comment().
    """
    return {
        "id":                d.id,
        "file_name":         d.file_name,
        "file_path":         d.file_path,
        "total_pages":       d.total_pages,
        "is_scanned":        d.is_scanned,
        "file_hash":         d.file_hash_sha256,
        "project_id":        d.project_id,
        "title":             d.title,
        "author":            d.author,
        "drawing_number":    getattr(d, "drawing_number", None),
        "creation_date":     getattr(d, "creation_date", None),
        "modification_date": getattr(d, "modification_date", None),
        "ocr_status":        getattr(d, "ocr_status", "pending"),
        "uploaded_at":       (
            d.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
            if d.uploaded_at else ""
        ),
        "pages":             page_map or {},
    }


def _project_to_dict(p: ProjectModel) -> Dict[str, Any]:
    return {
        "id":            p.id,
        "name":          p.name,
        "description":   p.description,
        "status":        p.status,
        "progress":      p.progress,
        "lead_engineer": p.lead_engineer,
        "created_at":    (
            p.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if p.created_at else ""
        ),
        "updated_at":    (
            p.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            if p.updated_at else ""
        ),
    }


def _user_to_dict(u: UserModel) -> Dict[str, Any]:
    return {
        "id":           u.id,
        "username":     u.username,
        "display_name": u.display_name,
        "email":        u.email,
        "role":         u.role,
        "is_active":    u.is_active,
    }


def _comment_to_dict(c: CommentModel) -> Dict[str, Any]:
    return {
        "id":                   c.id,
        "drawing_id":           c.drawing_id,
        "page_id":              c.page_id,
        "page_number":          c.page_number,
        "raw_text":             c.raw_text,
        "cleaned_text":         c.cleaned_text,
        "category_id":          c.category_id,
        "category_name":        c.category_name,
        "user_id":              c.user_id,
        "confidence":           c.confidence,
        "status":               c.status,
        "label":                getattr(c, "label", "comment_red") or "comment_red",
        "bbox":                 (c.bbox_x0, c.bbox_y0, c.bbox_x1, c.bbox_y1),
        "is_verified_by_human": c.is_verified_by_human,
        "created_at":           (
            c.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if c.created_at else ""
        ),
    }
