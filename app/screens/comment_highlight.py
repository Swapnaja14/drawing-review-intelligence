"""3.5 Comment Highlight Viewer — annotated canvas + comment list panel."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame,
                                QLabel, QListWidget, QListWidgetItem,
                                QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                                QSizePolicy, QScrollArea)
from PySide6.QtCore import Qt, QRectF, QTimer, Signal, QSize
from PySide6.QtGui import (QFont, QColor, QPen, QBrush, QPainter,
                            QPixmap, QLinearGradient)

from app import mock_data as md
from app.screens.pdf_viewer import _make_page_pixmap
from app.components.chips import StatusChip, CategoryBadge


_BOX_COLORS = {
    "Approved": ("#4ADE80", 0.25),
    "Pending":  ("#FBBF24", 0.25),
    "Flagged":  ("#F87171", 0.30),
    "Rejected": ("#F87171", 0.20),
}


class _BBoxItem(QGraphicsRectItem):
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

    def hoverEnterEvent(self, e):
        pen = self.pen()
        pen.setWidth(3)
        self.setPen(pen)
        super().hoverEnterEvent(e)

    def hoverLeaveEvent(self, e):
        pen = self.pen()
        pen.setWidth(1.5)
        self.setPen(pen)
        super().hoverLeaveEvent(e)


class CommentHighlightPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._comments = md.COMMENTS
        self._selected_id: str | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Annotated canvas ──────────────────────────────────────
        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHints(QPainter.RenderHint.Antialiasing |
                                   QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet("background: #2D2F34; border-bottom: 1px solid #3A3C42;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        count_lbl = QLabel(f"🔍  {len(self._comments)} comments found")
        count_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Weight.DemiBold))
        hdr_lay.addWidget(count_lbl)
        panel_lay.addWidget(hdr)

        # List
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

    def _load_canvas(self):
        self._scene.clear()
        pm = _make_page_pixmap(740, 960)
        self._scene.addPixmap(pm)
        self._box_items: dict[str, _BBoxItem] = {}
        for c in self._comments:
            x = c.bbox[0] * 740
            y = c.bbox[1] * 960
            w = c.bbox[2] * 740
            h = c.bbox[3] * 960
            item = _BBoxItem(c, QRectF(x, y, w, h))
            self._scene.addItem(item)
            self._box_items[c.id] = item

    def _populate_list(self):
        self._list.clear()
        for c in self._comments:
            widget = self._make_comment_card(c)
            item = QListWidgetItem()
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

        # ID + drawing
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
        excerpt = QLabel(c.ocr_text[:70] + ("…" if len(c.ocr_text) > 70 else ""))
        excerpt.setFont(QFont("Segoe UI", 12))
        excerpt.setWordWrap(True)
        lay.addWidget(excerpt)

        # Chips row
        chips_row = QHBoxLayout()
        cat_badge = CategoryBadge(c.category)
        chips_row.addWidget(cat_badge)
        chips_row.addStretch()
        st_chip = StatusChip(c.status)
        chips_row.addWidget(st_chip)
        conf = QLabel(f"{int(c.confidence*100)}%")
        conf.setStyleSheet(
            f"color: {'#4ADE80' if c.confidence>=0.9 else '#FBBF24' if c.confidence>=0.7 else '#F87171'};"
            f"font-weight:700; font-size:12px;"
        )
        chips_row.addWidget(conf)
        lay.addLayout(chips_row)
        return card

    def _on_list_select(self, row: int):
        if 0 <= row < len(self._comments):
            cid = self._comments[row].id
            self._highlight_box(cid)

    def _highlight_box(self, cid: str):
        for bid, item in self._box_items.items():
            pen = item.pen()
            pen.setWidth(3 if bid == cid else 1.5)
            item.setPen(pen)
        if cid in self._box_items:
            rect = self._box_items[cid].sceneBoundingRect()
            self._view.fitInView(rect.adjusted(-80, -80, 80, 80),
                                  Qt.AspectRatioMode.KeepAspectRatio)
