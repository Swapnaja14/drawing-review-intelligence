"""
comment_viewer_screen.py — Comment Highlight Viewer screen.

Provides:
    CommentHighlightPage(QWidget)
        Annotated PDF canvas on the left and a scrollable comment list
        panel on the right. Clicking a list item pans the canvas to
        the matching bounding box.

ARCHITECTURE NOTE:
This screen loads comments through AppController.get_comments_for_drawing().
It must NOT import or instantiate CommentRepository directly.

BOUNDING BOX COORDINATE NOTE:
AppController.normalise_comment() converts database bbox
(x0, y0, x1, y1 in absolute PDF point coordinates) to the normalised
(x, y, w, h) format in range 0–1 that the canvas rendering expects.

This conversion uses page dimensions from PDFDocumentDTO.pages[n].
If current_document is None (e.g. no PDF has been loaded this session),
normalisation cannot be performed and the raw absolute coordinates are
returned unchanged. In that case, mock data is used as the fallback so
the screen remains functional.

MOCK DATA FALLBACK:
When no controller is provided, or the database has no comments for the
loaded drawing, the screen falls back to mock_data.COMMENTS.
Mock comment bbox format: (x, y, w, h) normalised 0–1.
DB comment bbox format after normalisation: (x, y, w, h) normalised 0–1.
Both formats are rendered identically by _load_canvas().

The fallback is intentional and must be retained until the OCR/AI pipeline
populates the database with comments including bounding box data.
"""
from __future__ import annotations
from typing import Any, Dict, List, Union

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame,
                                QLabel, QListWidget, QListWidgetItem,
                                QGraphicsView, QGraphicsScene,
                                QSizePolicy)
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QFont, QPainter, QPixmap, QPen, QBrush, QColor

from app import mock_data as md
from app.components.pdf_canvas import make_page_pixmap, BBoxItem
from app.components.chips import StatusChip, CategoryBadge


def _get(c: Union[Dict[str, Any], Any], field: str, default: Any = "") -> Any:
    """Access a field from either a normalised display dict or a mock dataclass."""
    if isinstance(c, dict):
        return c.get(field, default)
    return getattr(c, field, default)


class CommentHighlightPage(QWidget):
    """
    Comment Highlight Viewer — annotated drawing canvas with a
    synchronised comment list panel.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller

        # Load comments from DB or fall back to mock data if standalone
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments: List[Any] = db_comments if db_comments else []
        elif self._controller:
            self._comments = []
        else:
            self._comments = list(md.COMMENTS)

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
        self._count_lbl = QLabel(f"🔍  {len(self._comments)} comments found")
        self._count_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Weight.DemiBold))
        hdr_lay.addWidget(self._count_lbl)
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

    def reload_comments(self) -> None:
        """Reload canvas and list from the database after a new PDF is loaded."""
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments = db_comments if db_comments else []
            if hasattr(self, '_count_lbl'):
                self._count_lbl.setText(f"🔍  {len(self._comments)} comments found")
            self._load_canvas()
            self._populate_list()

    # ── Canvas helpers ────────────────────────────────────────────

    def _load_canvas(self) -> None:
        """
        Render the drawing canvas with comment bounding boxes.
        """
        self._scene.clear()

        # Render real PDF page if available
        if self._controller and self._controller.current_document:
            try:
                page_num = 1
                if self._comments:
                    page_num = _get(self._comments[0], "page", 1)
                rendered_dto = self._controller.pdf_service.get_page_render(
                    self._controller.current_document.file_path, page_num, dpi=150
                )
                pm = QPixmap()
                pm.loadFromData(rendered_dto.image_bytes)
            except Exception:
                pm = make_page_pixmap(740, 960, comments=[])
        else:
            pm = make_page_pixmap(740, 960, comments=[])

        self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self._box_items: dict = {}

        width = pm.width()
        height = pm.height()

        for c in self._comments:
            bbox   = _get(c, "bbox", (0, 0, 0, 0))
            cid    = _get(c, "id", "")
            status = _get(c, "status", "Pending")

            x = bbox[0] * width
            y = bbox[1] * height
            w = bbox[2] * width
            h = bbox[3] * height

            # BBoxItem expects an object with .id, .status, .ocr_text
            adapter = _CommentAdapter(c)
            item = BBoxItem(adapter, QRectF(x, y, w, h))
            self._scene.addItem(item)
            self._box_items[cid] = item

    # ── List helpers ──────────────────────────────────────────────

    def _populate_list(self) -> None:
        self._list.clear()
        for c in self._comments:
            widget = self._make_comment_card(c)
            item   = QListWidgetItem()
            item.setSizeHint(QSize(300, 90))
            item.setData(Qt.ItemDataRole.UserRole, _get(c, "id", ""))
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _make_comment_card(self, c: Union[Dict[str, Any], Any]) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background:#2D2F34; border-radius:8px; padding:4px; }"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        cid        = _get(c, "id", "")
        drawing_no = _get(c, "drawing_no", _get(c, "drawing_id", ""))
        ocr_text   = _get(c, "ocr_text", "")
        category   = _get(c, "category", "Other")
        status     = _get(c, "status", "Pending")
        confidence = _get(c, "confidence", 0.0)

        id_row = QHBoxLayout()
        id_lbl = QLabel(str(cid))
        id_lbl.setFont(QFont("Cascadia Code", 11))
        id_lbl.setStyleSheet("color: #A6A9B1;")
        id_row.addWidget(id_lbl)
        id_row.addStretch()
        dwg = QLabel(str(drawing_no))
        dwg.setFont(QFont("Cascadia Code", 11))
        dwg.setStyleSheet("color: #3E9BFF;")
        id_row.addWidget(dwg)
        lay.addLayout(id_row)

        text = str(ocr_text)
        excerpt = QLabel(text[:70] + ("…" if len(text) > 70 else ""))
        excerpt.setFont(QFont("Segoe UI", 12))
        excerpt.setWordWrap(True)
        lay.addWidget(excerpt)

        chips_row = QHBoxLayout()
        chips_row.addWidget(CategoryBadge(str(category)))
        chips_row.addStretch()
        chips_row.addWidget(StatusChip(str(status)))
        conf_f = float(confidence)
        conf_color = (
            "#4ADE80" if conf_f >= 0.9
            else "#FBBF24" if conf_f >= 0.7
            else "#F87171"
        )
        conf = QLabel(f"{int(conf_f * 100)}%")
        conf.setStyleSheet(
            f"color:{conf_color}; font-weight:700; font-size:12px;"
        )
        chips_row.addWidget(conf)
        lay.addLayout(chips_row)
        return card

    # ── Selection handling ────────────────────────────────────────

    def _on_list_select(self, row: int) -> None:
        if 0 <= row < len(self._comments):
            cid = _get(self._comments[row], "id", "")
            self._highlight_box(cid)

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


# ---------------------------------------------------------------------------
# Adapter: gives BBoxItem a consistent attribute interface for DB dicts
# ---------------------------------------------------------------------------

class _CommentAdapter:
    """
    Lightweight adapter that wraps a normalised comment dict so that
    BBoxItem (which expects .id, .status, .ocr_text attributes) can work
    with both mock dataclass objects and database display dicts.

    INTEGRATION NOTE:
    BBoxItem is a reusable component in app/components/pdf_canvas.py.
    Rather than modifying BBoxItem to handle dicts (which would couple a
    component to application data shapes), this adapter bridges the gap.
    """

    def __init__(self, comment: Union[Dict[str, Any], Any]) -> None:
        if isinstance(comment, dict):
            self.id         = comment.get("id", "")
            self.status     = comment.get("status", "Pending")
            self.ocr_text   = comment.get("ocr_text", "")
            self.label      = comment.get("label", "comment_red")
            self.confidence = comment.get("confidence", 0.0)
        else:
            self.id         = getattr(comment, "id", "")
            self.status     = getattr(comment, "status", "Pending")
            self.ocr_text   = getattr(comment, "ocr_text", "")
            self.label      = getattr(comment, "label", "comment_red")
            self.confidence = getattr(comment, "confidence", 0.0)
