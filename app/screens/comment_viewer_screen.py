"""
comment_viewer_screen.py — Redesigned Comment Highlight Viewer screen.

Provides:
    CommentHighlightPage(QWidget)
        Annotated drawing canvas with zoom controls on the left,
        and an independently scrollable, filterable comment list panel on the right.
"""
from __future__ import annotations
from typing import Any, Dict, List, Union

from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame,
                                QLabel, QListWidget, QListWidgetItem,
                                QGraphicsView, QGraphicsScene, QPushButton,
                                QSizePolicy, QScrollArea, QToolButton)
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
    synchronised, filterable comment review panel.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._active_filter = "All"
        self._filtered_comments: List[Any] = []

        # Load comments from DB or fall back to mock data
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments: List[Any] = db_comments if db_comments else list(md.COMMENTS)
        else:
            self._comments = list(md.COMMENTS)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left side: Canvas with floating zoom controls ────────
        canvas_container = QWidget()
        canvas_lay = QVBoxLayout(canvas_container)
        canvas_lay.setContentsMargins(0, 0, 0, 0)
        canvas_lay.setSpacing(0)

        # Canvas toolbar
        c_toolbar = QFrame()
        c_toolbar.setFixedHeight(48)
        c_toolbar.setStyleSheet(
            "background: #1E2235; border-bottom: 1px solid #2E3654;"
        )
        t_lay = QHBoxLayout(c_toolbar)
        t_lay.setContentsMargins(16, 0, 16, 0)
        t_lay.setSpacing(8)

        t_title = QLabel("Drawing Annotation View")
        t_title.setFont(QFont("Inter", 13, QFont.Weight.DemiBold))
        t_title.setStyleSheet("color: #94A3B8;")
        t_lay.addWidget(t_title)
        t_lay.addStretch()

        zoom_in = QToolButton()
        zoom_in.setText("  + Zoom In  ")
        zoom_in.clicked.connect(self._zoom_in)
        t_lay.addWidget(zoom_in)

        zoom_out = QToolButton()
        zoom_out.setText("  − Zoom Out  ")
        zoom_out.clicked.connect(self._zoom_out)
        t_lay.addWidget(zoom_out)

        fit_btn = QToolButton()
        fit_btn.setText("  ⊡ Fit View  ")
        fit_btn.clicked.connect(self._fit_view)
        t_lay.addWidget(fit_btn)

        canvas_lay.addWidget(c_toolbar)

        # Annotated canvas
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
        canvas_lay.addWidget(self._view, 1)

        self._load_canvas()
        root.addWidget(canvas_container, 1)

        # ── Right side: 390px Comment review panel ────────────────
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setFixedWidth(390)
        panel.setStyleSheet(
            "#Card { border-radius:0; border-top:none; border-bottom:none; border-right:none; background:#1E2235; border-left: 1px solid #2E3654; }"
        )
        panel_lay = QVBoxLayout(panel)
        panel_lay.setContentsMargins(0, 0, 0, 0)
        panel_lay.setSpacing(0)

        # Panel Header
        hdr = QFrame()
        hdr.setFixedHeight(60)
        hdr.setStyleSheet(
            "background: #222634; border-bottom: 1px solid #2E3654;"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(18, 0, 18, 0)
        self._count_lbl = QLabel(f"🔍  {len(self._comments)} Comments Detected")
        self._count_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._count_lbl.setStyleSheet("color: #E2E8F0;")
        hdr_lay.addWidget(self._count_lbl)
        panel_lay.addWidget(hdr)

        # Filter Chips Toolbar
        filter_bar = QFrame()
        filter_bar.setStyleSheet(
            "background: #1E2235; border-bottom: 1px solid #2E3654;"
        )
        fb_lay = QHBoxLayout(filter_bar)
        fb_lay.setContentsMargins(12, 10, 12, 10)
        fb_lay.setSpacing(6)

        self._filter_btns: Dict[str, QPushButton] = {}
        for ftag in ["All", "Pending", "Approved", "Flagged", "Technical"]:
            btn = QPushButton(ftag)
            btn.setCheckable(True)
            btn.setChecked(ftag == "All")
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { background: #222634; color: #94A3B8; border: 1px solid #2E3654;"
                "border-radius: 6px; padding: 2px 10px; font-size: 12px; font-weight: 600; }"
                "QPushButton:hover { color: #E2E8F0; border-color: #3B82F6; }"
                "QPushButton:checked { background: #3B82F6; color: #FFFFFF; border-color: #3B82F6; }"
            )
            btn.clicked.connect(self._make_filter_handler(ftag))
            self._filter_btns[ftag] = btn
            fb_lay.addWidget(btn)

        panel_lay.addWidget(filter_bar)

        # Independently scrollable comment list
        self._list = QListWidget()
        self._list.setSpacing(10)
        self._list.setStyleSheet(
            "QListWidget { border:none; background: #1E2235; padding: 12px; }"
            "QListWidget::item { background: transparent; border-radius: 10px; padding: 0px; margin-bottom: 6px; }"
            "QListWidget::item:hover { background: #222634; }"
            "QListWidget::item:selected { background: rgba(59, 130, 246, 0.18); }"
        )
        self._list.currentRowChanged.connect(self._on_list_select)
        panel_lay.addWidget(self._list, 1)

        self._apply_filter("All")
        root.addWidget(panel)

    def _make_filter_handler(self, tag: str):
        def handler():
            for t, b in self._filter_btns.items():
                b.setChecked(t == tag)
            self._apply_filter(tag)
        return handler

    def _apply_filter(self, tag: str) -> None:
        self._active_filter = tag
        if tag == "All":
            self._filtered_comments = list(self._comments)
        elif tag in ("Pending", "Approved", "Rejected", "Flagged"):
            self._filtered_comments = [
                c for c in self._comments if _get(c, "status", "Pending") == tag
            ]
        elif tag == "Technical":
            self._filtered_comments = [
                c for c in self._comments if _get(c, "category", "") == "Technical"
            ]
        else:
            self._filtered_comments = list(self._comments)

        self._count_lbl.setText(f"🔍  {len(self._filtered_comments)} Comments ({tag})")
        self._populate_list()

    def reload_comments(self) -> None:
        """Reload canvas and list from the database after a new PDF is loaded."""
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments = db_comments if db_comments else []
            self._apply_filter(self._active_filter)
            self._load_canvas()

    # ── Canvas helpers ────────────────────────────────────────────

    def _load_canvas(self) -> None:
        self._scene.clear()

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
                pm = make_page_pixmap(780, 1000, comments=[])
        else:
            pm = make_page_pixmap(780, 1000, comments=[])

        self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self._box_items: dict = {}

        from app.theme import CURRENT_THEME
        if CURRENT_THEME == 'dark':
            dim = self._scene.addRect(self._scene.sceneRect())
            dim.setBrush(QColor(0, 0, 0, 160))
            dim.setPen(Qt.PenStyle.NoPen)
            dim.setZValue(0.5)

        width = pm.width()
        height = pm.height()

        for c in self._comments:
            bbox   = _get(c, "bbox", (0, 0, 0, 0))
            cid    = _get(c, "id", "")

            x = bbox[0] * width
            y = bbox[1] * height
            w = bbox[2] * width
            h = bbox[3] * height

            adapter = _CommentAdapter(c)
            item = BBoxItem(adapter, QRectF(x, y, w, h))
            self._scene.addItem(item)
            self._box_items[cid] = item

    def _zoom_in(self):
        self._view.scale(1.2, 1.2)

    def _zoom_out(self):
        self._view.scale(0.83, 0.83)

    def _fit_view(self):
        if not self._scene.items():
            return
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # ── List helpers ──────────────────────────────────────────────

    def _populate_list(self) -> None:
        self._list.clear()
        for c in self._filtered_comments:
            widget = self._make_comment_card(c)
            item   = QListWidgetItem()
            item.setSizeHint(QSize(360, 138))
            item.setData(Qt.ItemDataRole.UserRole, _get(c, "id", ""))
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _make_comment_card(self, c: Union[Dict[str, Any], Any]) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        card.setStyleSheet(
            "QFrame#Card { background: #222634; border: 1px solid #2E3654; border-radius: 10px; }"
            "QFrame#Card:hover { border-color: #3B82F6; background: #2A2F42; }"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        cid        = _get(c, "id", "")
        drawing_no = _get(c, "drawing_no", _get(c, "drawing_id", ""))
        page_no    = _get(c, "page", 1)
        ocr_text   = _get(c, "ocr_text", "")
        category   = _get(c, "category", "Other")
        status     = _get(c, "status", "Pending")
        confidence = _get(c, "confidence", 0.0)

        # Top row: Comment ID + Drawing Name + Page
        id_row = QHBoxLayout()
        id_row.setSpacing(6)

        id_lbl = QLabel(str(cid))
        id_lbl.setFont(QFont("Cascadia Code", 12, QFont.Weight.Bold))
        id_lbl.setStyleSheet("color: #F3F4F6; background: transparent;")
        id_row.addWidget(id_lbl)

        id_row.addStretch()

        dwg = QLabel(f"📄 {str(drawing_no)} · p.{page_no}")
        dwg.setFont(QFont("Inter", 11, QFont.Weight.Medium))
        dwg.setStyleSheet(
            "color: #60A5FA; background: rgba(59, 130, 246, 0.12);"
            "border-radius: 4px; padding: 2px 6px;"
        )
        id_row.addWidget(dwg)
        lay.addLayout(id_row)

        # Middle: OCR Text excerpt (multiline, clear font, no overlap)
        text = str(ocr_text).strip()
        display_text = text if text else "No OCR text recorded for this annotation."
        excerpt = QLabel(display_text[:95] + ("…" if len(display_text) > 95 else ""))
        excerpt.setFont(QFont("Inter", 13))
        excerpt.setStyleSheet("color: #D1D5DB; background: transparent; line-height: 1.3;")
        excerpt.setWordWrap(True)
        lay.addWidget(excerpt)

        # Bottom row: Category badge + Status chip + Confidence percentage
        chips_row = QHBoxLayout()
        chips_row.setSpacing(8)

        chips_row.addWidget(CategoryBadge(str(category)))
        chips_row.addStretch()
        chips_row.addWidget(StatusChip(str(status)))

        conf_f = float(confidence)
        conf_color = (
            "#10B981" if conf_f >= 0.9
            else "#F59E0B" if conf_f >= 0.7
            else "#EF4444"
        )
        conf = QLabel(f"{int(conf_f * 100)}%")
        conf.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        conf.setStyleSheet(
            f"color: {conf_color}; background: {conf_color}22;"
            f"border: 1px solid {conf_color}55; border-radius: 4px; padding: 2px 6px;"
        )
        chips_row.addWidget(conf)
        lay.addLayout(chips_row)

        return card

    # ── Selection handling ────────────────────────────────────────

    def _on_list_select(self, row: int) -> None:
        if 0 <= row < len(self._filtered_comments):
            cid = _get(self._filtered_comments[row], "id", "")
            self._highlight_box(cid)

    def _highlight_box(self, cid: str) -> None:
        for bid, item in self._box_items.items():
            pen = item.pen()
            pen.setWidth(4 if bid == cid else 1.5)
            item.setPen(pen)
        if cid in self._box_items:
            rect = self._box_items[cid].sceneBoundingRect()
            self._view.fitInView(
                rect.adjusted(-90, -90, 90, 90),
                Qt.AspectRatioMode.KeepAspectRatio,
            )


class _CommentAdapter:
    """Adapter bridging dict and object access for BBoxItem."""
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

