"""
comment_viewer_screen.py — Comment Highlight Viewer screen.

Provides:
    CommentHighlightPage(QWidget)
        Annotated PDF canvas on the left and a scrollable comment list
        panel on the right.  Clicking a list item pans the canvas to
        the matching bounding box.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame,
                                QLabel, QListWidget, QListWidgetItem,
                                QGraphicsView, QGraphicsScene,
                                QSizePolicy)
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QFont, QPainter

from app import mock_data as md
from app.components.pdf_canvas import make_page_pixmap, BBoxItem
from app.components.chips import StatusChip, CategoryBadge


class CommentHighlightPage(QWidget):
    """
    Comment Highlight Viewer — annotated drawing canvas with a
    synchronised comment list panel.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._comments      = list(md.COMMENTS)
        self._selected_id:  str | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Annotated canvas ──────────────────────────────────────
        self._scene = QGraphicsScene()
        self._view  = QGraphicsView(self._scene)
        self._view.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._load_canvas()
        root.addWidget(self._view, 3)

        # ── Comment list panel ────────────────────────────────────
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(340)
        panel.setStyleSheet("#Card { border-radius:0; }")
        panel_lay = QVBoxLayout(panel)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(0)

        # Panel header
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(
            "background: #2D2F34; border-bottom: 1px solid #3A3C42;"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        count_lbl = QLabel(f"🔍  {len(self._comments)} comments found")
        count_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Weight.DemiBold))
        hdr_lay.addWidget(count_lbl)
        panel_lay.addWidget(hdr)

        # Comment list
        self._list = QListWidget()
        self._list.setSpacing(4)
        self._list.setStyleSheet(
            "QListWidget { border:none; background:#26272B; padding:8px; }"
            "QListWidget::item { background:transparent; border-radius:8px; }"
            "QListWidget::item:hover { background: #2D2F34; }"
            "QListWidget::item:selected { background: #3E9BFF1A; }"
        )
        self._list.currentRowChanged.connect(self._on_list_select)
        self._populate_list()
        panel_lay.addWidget(self._list, 1)

        root.addWidget(panel)

    # ── Canvas helpers ────────────────────────────────────────────

    def _load_canvas(self) -> None:
        self._scene.clear()
        pm = make_page_pixmap(740, 960)
        self._scene.addPixmap(pm)
        self._box_items: dict[str, BBoxItem] = {}
        for c in self._comments:
            x = c.bbox[0] * 740
            y = c.bbox[1] * 960
            w = c.bbox[2] * 740
            h = c.bbox[3] * 960
            item = BBoxItem(c, QRectF(x, y, w, h))
            self._scene.addItem(item)
            self._box_items[c.id] = item

    # ── List helpers ──────────────────────────────────────────────

    def _populate_list(self) -> None:
        self._list.clear()
        for c in self._comments:
            widget = self._make_comment_card(c)
            item   = QListWidgetItem()
            item.setSizeHint(QSize(300, 90))
            item.setData(Qt.ItemDataRole.UserRole, c.id)
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _make_comment_card(self, c) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#2D2F34; border-radius:8px; padding:4px; }"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        # ID + drawing row
        id_row = QHBoxLayout()
        id_lbl = QLabel(c.id)
        id_lbl.setFont(QFont("Cascadia Code", 11))
        id_lbl.setStyleSheet("color: #A6A9B1;")
        id_row.addWidget(id_lbl)
        id_row.addStretch()
        dwg = QLabel(c.drawing_no)
        dwg.setFont(QFont("Cascadia Code", 11))
        dwg.setStyleSheet("color: #3E9BFF;")
        id_row.addWidget(dwg)
        lay.addLayout(id_row)

        # Excerpt
        excerpt = QLabel(
            c.ocr_text[:70] + ("…" if len(c.ocr_text) > 70 else "")
        )
        excerpt.setFont(QFont("Segoe UI", 12))
        excerpt.setWordWrap(True)
        lay.addWidget(excerpt)

        # Chips row
        chips_row = QHBoxLayout()
        chips_row.addWidget(CategoryBadge(c.category))
        chips_row.addStretch()
        chips_row.addWidget(StatusChip(c.status))
        conf_color = (
            "#4ADE80" if c.confidence >= 0.9
            else "#FBBF24" if c.confidence >= 0.7
            else "#F87171"
        )
        conf = QLabel(f"{int(c.confidence * 100)}%")
        conf.setStyleSheet(
            f"color:{conf_color}; font-weight:700; font-size:12px;"
        )
        chips_row.addWidget(conf)
        lay.addLayout(chips_row)
        return card

    # ── Selection handling ────────────────────────────────────────

    def _on_list_select(self, row: int) -> None:
        if 0 <= row < len(self._comments):
            self._highlight_box(self._comments[row].id)

    def _highlight_box(self, cid: str) -> None:
        for bid, item in self._box_items.items():
            pen = item.pen()
            pen.setWidth(3 if bid == cid else 1.5)
            item.setPen(pen)
        if cid in self._box_items:
            rect = self._box_items[cid].sceneBoundingRect()
            self._view.fitInView(
                rect.adjusted(-80, -80, 80, 80),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
