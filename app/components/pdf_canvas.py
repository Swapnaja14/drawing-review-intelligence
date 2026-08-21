"""
pdf_canvas.py — PDF page rendering and annotation canvas utilities.

Provides:
    make_page_pixmap(width, height, comments=None) -> QPixmap
        Renders a simulated engineering drawing page with title block,
        grid lines, and comment bounding boxes.

    BBoxItem(QGraphicsRectItem)
        Hover-highlighted bounding-box overlay for an annotated comment
        on a QGraphicsScene canvas.
"""
# ARCHITECTURE WARNING:
# This module previously imported mock_data at module level and used
# md.COMMENTS[:5] inside make_page_pixmap(). This has been refactored so
# make_page_pixmap() accepts an optional 'comments' parameter.
#
# When comment_viewer_screen.py and review_screen.py are integrated with
# database-sourced comments, callers must pass real comment data (normalised
# display dicts from AppController.normalise_comment()) or an empty list.
#
# BOUNDING BOX NOTE:
# The mock_data Comment.bbox format is (x, y, width, height) normalised 0-1.
# The database CommentModel stores (bbox_x0, bbox_y0, bbox_x1, bbox_y1) in
# absolute PDF point coordinates.
# These are NOT interchangeable. See docs/AGENT_INTEGRATION_GUIDELINES.md
# WARNING-001 and WARNING-009 for the conversion formula.
#
# This warning is for all development agents — do not silently mix coordinate
# systems when passing comments to make_page_pixmap() or BBoxItem.
from __future__ import annotations
from typing import List, Any, Optional
from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import (
    QPixmap, QPainter, QPen, QBrush, QColor, QFont,
)

from app import mock_data as md


# ── Status-to-colour mapping ──────────────────────────────────────────────────

_BOX_COLORS: dict[str, tuple[str, float]] = {
    "Approved": ("#4ADE80", 0.25),
    "Pending":  ("#FBBF24", 0.25),
    "Flagged":  ("#F87171", 0.30),
    "Rejected": ("#F87171", 0.20),
}


# ── Page pixmap factory ───────────────────────────────────────────────────────

def make_page_pixmap(
    width: int = 700,
    height: int = 900,
    comments: Optional[List[Any]] = None,
) -> QPixmap:
    """
    Render a simulated engineering drawing page.

    Draws a white sheet with:
    - A grey title block at the bottom.
    - A double-line drawing border.
    - Light grid lines.
    - Coloured comment bounding boxes.
    - Title block text (drawing number, title, scale, date).

    Parameters
    ----------
    width, height:
        Pixel dimensions of the generated pixmap (default 700 × 900).
    comments:
        Optional list of comment objects/dicts to render as bounding boxes.
        Each item must expose .status and .bbox (mock objects) OR be a
        normalised display dict with keys "status" and "bbox"
        (x_norm, y_norm, w_norm, h_norm in 0-1 range).
        If None, falls back to md.COMMENTS[:5] for backward compatibility
        during development. Pass an empty list [] to render no bounding boxes.

    Returns
    -------
    QPixmap
        Ready-to-use pixmap for display in a QGraphicsView or QListWidget.
    """
    pm = QPixmap(width, height)
    pm.fill(QColor("#FFFFFF"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Title block
    p.setPen(QPen(QColor("#CCCCCC"), 1))
    p.setBrush(QColor("#F5F6F8"))
    p.drawRect(0, height - 100, width, 100)

    # Drawing border
    p.setPen(QPen(QColor("#999999"), 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(20, 20, width - 40, height - 40)

    # Grid lines
    p.setPen(QPen(QColor("#888888"), 1))
    for y_off in range(80, height - 120, 40):
        p.drawLine(40, y_off, width - 40, y_off)
    for x_off in range(80, width - 40, 60):
        p.drawLine(x_off, 40, x_off, height - 120)

    # Comment bounding boxes
    # ARCHITECTURE NOTE:
    # comments=None falls back to md.COMMENTS[:5] for backward compatibility.
    # When screens are integrated with the database, pass normalised display
    # dicts (from AppController.normalise_comment()) so that the canvas
    # and the comment list panel show the same data source.
    # Normalised bbox format: (x_norm, y_norm, w_norm, h_norm) in range 0-1.
    render_comments = comments if comments is not None else md.COMMENTS[:5]

    for c in render_comments:
        # Support both mock dataclass objects and normalised display dicts
        if isinstance(c, dict):
            status = c.get("status", "Pending")
            bbox   = c.get("bbox", (0, 0, 0, 0))
        else:
            status = c.status
            bbox   = c.bbox

        x     = int(bbox[0] * width)
        y     = int(bbox[1] * height)
        w     = int(bbox[2] * width)
        h_box = int(bbox[3] * height)
        color = {
            "Approved": QColor("#4ADE80"),
            "Pending":  QColor("#FBBF24"),
            "Flagged":  QColor("#F87171"),
            "Rejected": QColor("#F87171"),
        }.get(status, QColor("#3E9BFF"))
        color.setAlphaF(0.25)
        p.setBrush(color)
        color2 = QColor(color)
        color2.setAlphaF(0.9)
        p.setPen(QPen(color2, 1.5))
        p.drawRect(x, y, w, h_box)

    # Title block text
    p.setPen(QPen(QColor("#333333"), 1))
    p.setFont(QFont("Cascadia Code", 8))
    p.drawText(
        30, height - 80,
        "Drawing No: UCC-E-101   Rev: A   Project: UCC Site-4 Expansion",
    )
    p.drawText(
        30, height - 60,
        "Title: Piping & Instrumentation Diagram — Unit 4-A",
    )
    p.drawText(
        30, height - 40,
        "Scale: 1:50   Sheet: 1 of 3   Date: 2026-07-28",
    )
    p.end()
    return pm


# ── BBoxItem ──────────────────────────────────────────────────────────────────

class BBoxItem(QGraphicsRectItem):
    """
    Hoverable, coloured bounding-box overlay for a comment annotation.

    Colour is keyed to the comment's status.  The border thickens on
    hover to provide visual feedback.

    Parameters
    ----------
    comment:
        A ``mock_data.Comment`` (or any object with ``.id``,
        ``.status``, ``.ocr_text`` attributes).
    rect:
        Scene-coordinate bounding rectangle.
    """

    def __init__(self, comment, rect: QRectF, parent=None):
        super().__init__(rect, parent)
        self.comment = comment

        col_hex, alpha = _BOX_COLORS.get(comment.status, ("#3E9BFF", 0.25))
        fill = QColor(col_hex)
        fill.setAlphaF(alpha)
        border = QColor(col_hex)
        border.setAlphaF(0.9)

        self.setData(0, comment.id)
        self.setBrush(QBrush(fill))
        self.setPen(QPen(border, 1.5))
        self.setToolTip(f"{comment.id}: {comment.ocr_text[:60]}")
        self.setAcceptHoverEvents(True)

    def hoverEnterEvent(self, e) -> None:
        pen = self.pen()
        pen.setWidth(3)
        self.setPen(pen)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e) -> None:
        pen = self.pen()
        pen.setWidth(1.5)
        self.setPen(pen)
        super().hoverLeaveEvent(e)
