"""
src/infrastructure/storage/models.py
SQLAlchemy ORM Data Models for SQLite Database.
"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ProjectModel(Base):
    """Database model for Engineering Projects."""
    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)
    name = Column(String(255), nullable=False)
    drawings = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    status = Column(String(50), default="Active")  # "Active", "Complete", "On Hold"
    progress = Column(Integer, default=0)         # 0-100%
    last_modified = Column(String(50), nullable=False)
    engineer = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    drawings_list = relationship("DrawingModel", back_populates="project", cascade="all, delete-orphan")


class DrawingModel(Base):
    """Database model for Engineering Drawing PDFs."""
    __tablename__ = "drawings"

    id = Column(String(50), primary_key=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=True)
    file_path = Column(Text, nullable=False)
    file_name = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True)
    total_pages = Column(Integer, nullable=False)
    is_scanned = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("ProjectModel", back_populates="drawings_list")
    pages_list = relationship("PageModel", back_populates="drawing", cascade="all, delete-orphan")
    comments_list = relationship("CommentModel", back_populates="drawing", cascade="all, delete-orphan")


class PageModel(Base):
    """Database model for individual PDF drawing pages."""
    __tablename__ = "pages"

    id = Column(String(50), primary_key=True)
    drawing_id = Column(String(50), ForeignKey("drawings.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    width_pt = Column(Float, nullable=False)
    height_pt = Column(Float, nullable=False)
    aspect_ratio = Column(Float, nullable=False)
    has_native_text = Column(Boolean, default=False)
    text_character_count = Column(Integer, default=0)
    orientation_deg = Column(Integer, default=0)

    # Relationships
    drawing = relationship("DrawingModel", back_populates="pages_list")


class CommentModel(Base):
    """Database model for extracted drawing review comments."""
    __tablename__ = "comments"

    id = Column(String(50), primary_key=True)
    drawing_id = Column(String(50), ForeignKey("drawings.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    raw_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, default="")
    category = Column(String(100), default="Uncategorized")
    confidence = Column(Float, default=0.0)
    status = Column(String(50), default="Pending") # "Pending", "Approved", "Rejected", "Flagged"
    bbox_x0 = Column(Float, nullable=False)
    bbox_y0 = Column(Float, nullable=False)
    bbox_x1 = Column(Float, nullable=False)
    bbox_y1 = Column(Float, nullable=False)
    is_verified_by_human = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    drawing = relationship("DrawingModel", back_populates="comments_list")
