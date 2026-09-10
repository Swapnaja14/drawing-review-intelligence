"""
src/infrastructure/storage/models.py
SQLAlchemy 2.x ORM Models for the UCC Analyzer SQLite database.

Tables:
    users              — reviewer/engineer accounts
    categories         — comment classification categories
    projects           — engineering projects
    drawings           — uploaded PDF drawing files (metadata only, no binary data)
    pages              — individual pages extracted from drawings
    comments           — review comments extracted from pages
    comment_audit_log  — persistent audit/version history for comment changes (Week 7)
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    ForeignKey, Text, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship


# ---------------------------------------------------------------------------
# Declarative base (SQLAlchemy 2.x style)
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class UserModel(Base):
    """Engineers and reviewers who create or approve comments."""

    __tablename__ = "users"

    id           = Column(String(50),  primary_key=True)
    username     = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(150), nullable=True)
    email        = Column(String(254), nullable=True, unique=True)
    role         = Column(String(50),  nullable=False, default="Reviewer")
    # e.g. "Reviewer", "Lead Engineer", "Admin"
    is_active    = Column(Boolean,     nullable=False, default=True)
    created_at   = Column(DateTime,    nullable=False, default=datetime.utcnow)

    # Authentication fields (used by AuthService for PBKDF2 sign-in)
    password_hash = Column(String(255), nullable=True)
    salt          = Column(String(64),  nullable=True)
    last_login    = Column(DateTime,    nullable=True)

    # Relationships
    comments = relationship(
        "CommentModel",
        back_populates="user",
        foreign_keys="CommentModel.user_id",
    )

    __table_args__ = (
        Index("ix_users_username", "username"),
    )


# ---------------------------------------------------------------------------
# categories
# ---------------------------------------------------------------------------

class CategoryModel(Base):
    """Taxonomy of comment classification categories."""

    __tablename__ = "categories"

    id          = Column(String(50),  primary_key=True)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(Text,        nullable=True)
    color_hex   = Column(String(7),   nullable=True)   # e.g. "#FBBF24"
    created_at  = Column(DateTime,    nullable=False, default=datetime.utcnow)

    # Relationships
    comments = relationship("CommentModel", back_populates="category_rel")

    __table_args__ = (
        Index("ix_categories_name", "name"),
    )


# ---------------------------------------------------------------------------
# projects
# ---------------------------------------------------------------------------

class ProjectModel(Base):
    """Top-level engineering project containers."""

    __tablename__ = "projects"

    id            = Column(String(50),  primary_key=True)
    name          = Column(String(255), nullable=False)
    description   = Column(Text,        nullable=True)
    status        = Column(String(50),  nullable=False, default="Active")
    # "Active" | "Complete" | "On Hold"
    progress      = Column(Integer,     nullable=False, default=0)   # 0-100
    lead_engineer = Column(String(100), nullable=True)
    created_at    = Column(DateTime,    nullable=False, default=datetime.utcnow)
    updated_at    = Column(DateTime,    nullable=False,
                           default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drawings = relationship(
        "DrawingModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_projects_status", "status"),
    )


# ---------------------------------------------------------------------------
# drawings
# ---------------------------------------------------------------------------

class DrawingModel(Base):
    """
    Metadata for an uploaded PDF drawing.
    Binary PDF content is NEVER stored here — only file path and hashes.

    Column notes
    ------------
    drawing_number : Engineering drawing identifier (e.g. "UCC-E-101").
                     Extracted from PDF metadata "Subject" field, "Title"
                     field (when it looks like a number), or the filename stem.
                     Advisory only — may be empty. NOT a primary/foreign key.
                     See PyMuPDFAdapter._extract_drawing_number() for rules.

    creation_date  : PDF-internal creation timestamp ("YYYY-MM-DD HH:MM:SS").
                     NULL when the PDF does not carry this metadata.
                     Do NOT populate with file-system mtime as a substitute.

    modification_date : PDF-internal last-modified timestamp.
                        NULL when absent from PDF metadata.

    ocr_status     : Processing status for OCR pipeline.
                     Values: "pending" | "completed" | "failed".
                     Set by the workflow engine after OCR completes.
                     NULL for drawings that pre-date the OCR pipeline.

    INTEGRATION WARNING:
    drawing_number is NOT the database primary key (id).
    Never use drawing_number as a foreign-key drawing_id.
    The canonical drawing ID is DrawingModel.id ("DWG-XXXXXXXX").
    """

    __tablename__ = "drawings"

    id                = Column(String(50),  primary_key=True)
    project_id        = Column(String(50),
                               ForeignKey("projects.id", ondelete="SET NULL"),
                               nullable=True)
    file_path         = Column(Text,        nullable=False)
    file_name         = Column(String(255), nullable=False)
    file_size_bytes   = Column(Integer,     nullable=False)
    file_hash_sha256  = Column(String(64),  nullable=False)
    total_pages       = Column(Integer,     nullable=False)
    is_scanned        = Column(Boolean,     nullable=False, default=False)
    title             = Column(String(255), nullable=True)
    author            = Column(String(255), nullable=True)
    # Week 4 additions — all nullable so existing rows are unaffected
    drawing_number    = Column(String(100), nullable=True)
    creation_date     = Column(String(19),  nullable=True)   # "YYYY-MM-DD HH:MM:SS"
    modification_date = Column(String(19),  nullable=True)   # "YYYY-MM-DD HH:MM:SS"
    ocr_status        = Column(String(50),  nullable=True,   default="pending")
    uploaded_at       = Column(DateTime,    nullable=False, default=datetime.utcnow)

    # Relationships
    project  = relationship("ProjectModel", back_populates="drawings")
    pages    = relationship(
        "PageModel",
        back_populates="drawing",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "CommentModel",
        back_populates="drawing",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Fast duplicate-detection by hash
        Index("ix_drawings_file_hash", "file_hash_sha256"),
        Index("ix_drawings_project_id", "project_id"),
    )


# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------

class PageModel(Base):
    """Metadata for a single page within a drawing PDF."""

    __tablename__ = "pages"

    id                   = Column(String(50), primary_key=True)
    drawing_id           = Column(String(50),
                                  ForeignKey("drawings.id", ondelete="CASCADE"),
                                  nullable=False)
    page_number          = Column(Integer,    nullable=False)
    width_pt             = Column(Float,      nullable=False)
    height_pt            = Column(Float,      nullable=False)
    aspect_ratio         = Column(Float,      nullable=False)
    has_native_text      = Column(Boolean,    nullable=False, default=False)
    text_character_count = Column(Integer,    nullable=False, default=0)
    orientation_deg      = Column(Integer,    nullable=False, default=0)

    # Relationships
    drawing  = relationship("DrawingModel", back_populates="pages")
    comments = relationship(
        "CommentModel",
        back_populates="page",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_pages_drawing_id", "drawing_id"),
    )


# ---------------------------------------------------------------------------
# comments
# ---------------------------------------------------------------------------

class CommentModel(Base):
    """
    A review comment extracted from a drawing page.

    Relationships:
        page     — the page the comment was extracted from
        drawing  — denormalised short-cut for direct drawing queries
        category_rel — classification category
        user     — reviewer who last actioned the comment (nullable)
    """

    __tablename__ = "comments"

    id                   = Column(String(50), primary_key=True)
    drawing_id           = Column(String(50),
                                  ForeignKey("drawings.id", ondelete="CASCADE"),
                                  nullable=False)
    page_id              = Column(String(50),
                                  ForeignKey("pages.id", ondelete="SET NULL"),
                                  nullable=True)
    category_id          = Column(String(50),
                                  ForeignKey("categories.id", ondelete="SET NULL"),
                                  nullable=True)
    user_id              = Column(String(50),
                                  ForeignKey("users.id", ondelete="SET NULL"),
                                  nullable=True)
    page_number          = Column(Integer,    nullable=False)
    raw_text             = Column(Text,       nullable=False)
    cleaned_text         = Column(Text,       nullable=True, default="")
    category_name        = Column(String(100),nullable=True, default="Uncategorized")
    # Denormalised label for fast reads; canonical FK is category_id
    confidence           = Column(Float,      nullable=False, default=0.0)
    # Model tracking & confidence metrics (Week 10)
    classification_method     = Column(String(50),  nullable=True)
    model_name                = Column(String(100), nullable=True)
    model_version             = Column(String(50),  nullable=True)
    classification_confidence = Column(Float,       nullable=True)
    detection_confidence      = Column(Float,       nullable=True)
    requires_human_review     = Column(Boolean,     nullable=False, default=False)
    classification_timestamp  = Column(DateTime,    nullable=True)

    status               = Column(String(50), nullable=False, default="Pending")
    # "Pending" | "Approved" | "Rejected" | "Flagged"
    bbox_x0              = Column(Float,      nullable=False, default=0.0)
    bbox_y0              = Column(Float,      nullable=False, default=0.0)
    bbox_x1              = Column(Float,      nullable=False, default=0.0)
    bbox_y1              = Column(Float,      nullable=False, default=0.0)
    label                = Column(String(50), nullable=True, default="comment_red")
    is_verified_by_human = Column(Boolean,    nullable=False, default=False)
    created_at           = Column(DateTime,   nullable=False, default=datetime.utcnow)
    updated_at           = Column(DateTime,   nullable=False,
                                  default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    drawing      = relationship("DrawingModel",  back_populates="comments",
                                foreign_keys=[drawing_id])
    page         = relationship("PageModel",     back_populates="comments",
                                foreign_keys=[page_id])
    category_rel = relationship("CategoryModel", back_populates="comments",
                                foreign_keys=[category_id])
    user         = relationship("UserModel",     back_populates="comments",
                                foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_comments_drawing_id",  "drawing_id"),
        Index("ix_comments_status",      "status"),
        Index("ix_comments_category_id", "category_id"),
        Index("ix_comments_user_id",     "user_id"),
        Index("ix_comments_is_verified", "is_verified_by_human"),
        Index("ix_comments_drawing_verified", "drawing_id", "is_verified_by_human"),
    )


# ---------------------------------------------------------------------------
# comment_audit_log  (Week 7)
# ---------------------------------------------------------------------------

class CommentAuditLogModel(Base):
    """
    Persistent audit / version history for all human-initiated changes to
    comment records.

    DESIGN RATIONALE:
    A separate audit-log table is used (rather than adding history columns to
    comments) because:
    - A comment may have many history entries; one-per-row in CommentModel
      would require unbounded columns or repeated rows.
    - The existing VerificationService already models exactly this pattern via
      AuditLogEntryDTO — this table persists it.
    - 'ON DELETE SET NULL' on comment_id preserves audit history even if the
      comment itself is later deleted, satisfying audit requirements.

    ACTION VOCABULARY  (matches AuditAction constants in audit_dtos.py):
        "approve"         — human reviewer approved
        "reject"          — human reviewer rejected
        "flag"            — flagged for further review
        "edit_text"       — OCR/cleaned text edited by human
        "edit_category"   — category reassigned
        "bulk_approve"    — system bulk-approved

    FIELD NOTES:
    - old_value / new_value: TEXT — stores the previous and new content of
      the changed field as a plain string.  For status changes these are the
      status strings; for text edits these are the full text strings.
    - changed_by_user_id: FK to users.id, nullable — NULL when the action
      is system-initiated (e.g. bulk workflow).
    - field_changed: identifies which CommentModel field was modified so that
      callers can filter history by field (e.g. "raw_text", "status").

    INTEGRATION NOTE:
    This table is written by CommentAuditLogRepository (in repository.py).
    UI screens must never INSERT to this table directly.
    All writes go through VerificationService → AppController.
    """

    __tablename__ = "comment_audit_log"

    id                  = Column(String(50),  primary_key=True)
    comment_id          = Column(
        String(50),
        ForeignKey("comments.id", ondelete="SET NULL"),
        nullable=True,          # nullable so history survives comment deletion
    )
    action              = Column(String(50),  nullable=False)
    # e.g. "approve" | "reject" | "flag" | "edit_text" | "edit_category"
    field_changed       = Column(String(50),  nullable=True)
    # e.g. "raw_text" | "cleaned_text" | "status" | "category_name"
    old_value           = Column(Text,        nullable=True)
    new_value           = Column(Text,        nullable=True)
    changed_by_user_id  = Column(
        String(50),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    changed_at          = Column(DateTime,    nullable=False, default=datetime.utcnow)
    notes               = Column(Text,        nullable=True)

    # Relationships (back-populate not required for audit; kept for optional joins)
    comment = relationship(
        "CommentModel",
        foreign_keys=[comment_id],
        backref="audit_entries",
        passive_deletes=True,
    )
    changed_by = relationship(
        "UserModel",
        foreign_keys=[changed_by_user_id],
        passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_audit_comment_id",   "comment_id"),
        Index("ix_audit_changed_at",   "changed_at"),
        Index("ix_audit_action",       "action"),
    )
