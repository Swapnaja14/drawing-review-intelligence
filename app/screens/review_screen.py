"""
review_screen.py — Human Verification screen.

Provides:
    HumanReviewPage(QWidget)
        Splitter: PDF canvas on the left, review panel on the right.
        Supports keyboard shortcuts: A = Approve, R = Reject, ←/→ = Prev/Next.

ARCHITECTURE NOTE:
This screen loads comments through AppController.get_comments_for_drawing()
and persists human-review actions (approve, reject, text edit) through
AppController.update_comment_status() and AppController.update_comment_text().

UI code in this file must NOT:
  - import or instantiate CommentRepository directly
  - execute SQLAlchemy queries
  - access SQLite

If no controller is provided (controller=None), the screen falls back to
app/mock_data.py COMMENTS for development/preview purposes. This fallback
must be replaced with live database data once a PDF has been loaded through
the normal upload flow.

MOCK DATA FALLBACK:
The mock_data fallback remains intentional during Week 3 development so the
application does not crash when the database contains no comments yet.
Once the OCR/AI pipeline populates the database, the fallback can be removed.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QTextEdit, QComboBox,
                                QProgressBar, QSplitter, QSizePolicy,
                                QGraphicsView, QGraphicsScene, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal, QRectF
from PySide6.QtGui import QFont, QPainter, QKeyEvent, QPixmap, QPen, QBrush, QColor

from app import mock_data as md
from app.components.chips import StatusChip, CategoryBadge
from app.components.pdf_canvas import make_page_pixmap, draw_bounding_boxes, BBoxItem

# Agreed status vocabulary — do not use any other values
_VALID_STATUSES = ("Pending", "Approved", "Rejected", "Flagged")


class _CommentAdapter:
    """Lightweight adapter that wraps comment dicts for BBoxItem compatibility."""
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


def _get(c: Union[Dict[str, Any], Any], field: str, default: Any = "") -> Any:
    """Access a field from either a normalised display dict or a mock dataclass."""
    if isinstance(c, dict):
        return c.get(field, default)
    return getattr(c, field, default)


class HumanReviewPage(QWidget):
    """
    Human Verification — PDF canvas + review panel with Approve / Reject /
    Edit actions and keyboard navigation.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller

        # Load comments: prefer database, fall back to mock data
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments: List[Any] = db_comments if db_comments else list(md.COMMENTS)
        else:
            self._comments = list(md.COMMENTS)

        self._idx     = 0
        self._box_items: Dict[str, BBoxItem] = {}
        self._current_canvas_page: Optional[int] = None

        # In-memory status cache: updated immediately on action, persisted via controller
        self._statuses: Dict[str, str] = {
            _get(c, "id"): _get(c, "status", "Pending")
            for c in self._comments
        }
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Splitter ──────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Left — PDF canvas (simulated; real page rendering via PdfViewerPage)
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
        splitter.addWidget(self._view)

        # Right — review panel
        self._panel = self._build_review_panel()
        splitter.addWidget(self._panel)
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        root.addWidget(splitter)
        self._load_comment()

    def reload_comments(self) -> None:
        """
        Reload comments from the database for the currently loaded drawing.

        Call this method after uploading a new PDF or after the OCR pipeline
        populates comments, so the review screen reflects the latest data.
        """
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments = db_comments if db_comments else []
            self._idx = 0
            self._statuses = {
                c["id"]: c["status"] for c in self._comments
            }
            if hasattr(self, "_prog_bar"):
                self._prog_bar.setRange(0, max(1, len(self._comments)))
            self._load_canvas()
            self._load_comment()

    # ── Panel builder ─────────────────────────────────────────────

    def _build_review_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #FFFFFF; border-left: 1px solid #E2E8F0; }")

        panel = QFrame()
        panel.setObjectName("ReviewPanel")
        panel.setStyleSheet("#ReviewPanel { background: #FFFFFF; border: none; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)

        # Progress header
        prog_hdr = QHBoxLayout()
        self._prog_lbl = QLabel("Comment 1 of 0")
        self._prog_lbl.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        self._prog_lbl.setStyleSheet("color: #0F172A;")
        prog_hdr.addWidget(self._prog_lbl)
        prog_hdr.addStretch()
        lay.addLayout(prog_hdr)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, max(len(self._comments), 1))
        self._prog_bar.setValue(1)
        self._prog_bar.setFixedHeight(8)
        self._prog_bar.setStyleSheet(
            "QProgressBar { background: #E2E8F0; border-radius: 4px; }"
            "QProgressBar::chunk { background: #2563EB; border-radius: 4px; }"
        )
        lay.addWidget(self._prog_bar)

        # Comment edit card
        self._edit_card = QFrame()
        self._edit_card.setObjectName("Card")
        self._edit_card.setStyleSheet(
            "#Card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        edit_lay = QVBoxLayout(self._edit_card)
        edit_lay.setContentsMargins(20, 18, 20, 18)
        edit_lay.setSpacing(12)

        # Top ID and Drawing reference
        self._comment_id_lbl = QLabel("")
        self._comment_id_lbl.setFont(QFont("Cascadia Code", 13, QFont.Weight.Bold))
        self._comment_id_lbl.setStyleSheet("color: #0F172A;")
        edit_lay.addWidget(self._comment_id_lbl)

        # OCR Text section
        ocr_lbl = QLabel("OCR DETECTED TEXT")
        ocr_lbl.setObjectName("FormLabel")
        edit_lay.addWidget(ocr_lbl)

        self._ocr_edit = QTextEdit()
        self._ocr_edit.setMinimumHeight(105)
        self._ocr_edit.setReadOnly(True)
        self._ocr_edit.setFont(QFont("Cascadia Code", 13))
        self._ocr_edit.setStyleSheet(
            "QTextEdit { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; color: #0F172A; padding: 10px; }"
        )
        edit_lay.addWidget(self._ocr_edit)

        # Category section
        cat_lbl = QLabel("ENGINEERING CATEGORY")
        cat_lbl.setObjectName("FormLabel")
        edit_lay.addWidget(cat_lbl)

        cat_row = QHBoxLayout()
        cat_row.setSpacing(10)
        self._cat_combo = QComboBox()
        self._cat_combo.addItems(md.CATEGORIES)
        self._cat_combo.setFixedHeight(40)
        self._cat_combo.currentTextChanged.connect(self._on_category_changed)
        cat_row.addWidget(self._cat_combo, 1)

        self._cat_badge = CategoryBadge("")
        cat_row.addWidget(self._cat_badge)
        edit_lay.addLayout(cat_row)

        # Confidence section
        conf_hdr = QLabel("DETECTION CONFIDENCE")
        conf_hdr.setObjectName("FormLabel")
        edit_lay.addWidget(conf_hdr)

        conf_row = QHBoxLayout()
        conf_row.setSpacing(12)
        self._conf_bar = QProgressBar()
        self._conf_bar.setRange(0, 100)
        self._conf_bar.setValue(90)
        self._conf_bar.setFixedHeight(8)
        self._conf_bar.setStyleSheet(
            "QProgressBar { background: #E2E8F0; border-radius: 4px; }"
            "QProgressBar::chunk { background: #059669; border-radius: 4px; }"
        )
        conf_row.addWidget(self._conf_bar, 1)

        self._conf_lbl = QLabel("—")
        self._conf_lbl.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        self._conf_lbl.setStyleSheet("color: #059669;")
        conf_row.addWidget(self._conf_lbl)
        edit_lay.addLayout(conf_row)

        lay.addWidget(self._edit_card)

        # Status indicator row
        status_card = QFrame()
        status_card.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 6px;")
        status_lay = QHBoxLayout(status_card)
        status_lay.setContentsMargins(14, 8, 14, 8)
        status_lbl = QLabel("CURRENT REVIEW STATUS:")
        status_lbl.setObjectName("FormLabel")
        status_lay.addWidget(status_lbl)
        status_lay.addSpacing(8)
        self._status_chip = StatusChip("Pending")
        status_lay.addWidget(self._status_chip)
        status_lay.addStretch()
        lay.addWidget(status_card)

        # Audit history collapsible panel
        self._audit_card = QFrame()
        self._audit_card.setObjectName("Card")
        self._audit_card.setStyleSheet(
            "#Card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; }"
        )
        audit_lay = QVBoxLayout(self._audit_card)
        audit_lay.setContentsMargins(16, 12, 16, 12)
        audit_lay.setSpacing(8)

        audit_hdr_row = QHBoxLayout()
        self._audit_toggle_btn = QPushButton("▼  Audit History (0)")
        self._audit_toggle_btn.setObjectName("GhostBtn")
        self._audit_toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._audit_toggle_btn.setStyleSheet(
            "QPushButton { text-align: left; font-weight: 600; font-size: 13px; color: #475569; padding: 0px; border: none; }"
        )
        self._audit_toggle_btn.clicked.connect(self._toggle_audit_panel)
        audit_hdr_row.addWidget(self._audit_toggle_btn)
        audit_hdr_row.addStretch()
        audit_lay.addLayout(audit_hdr_row)

        self._audit_container = QWidget()
        self._audit_items_lay = QVBoxLayout(self._audit_container)
        self._audit_items_lay.setContentsMargins(0, 4, 0, 0)
        self._audit_items_lay.setSpacing(6)

        self._audit_scroll = QScrollArea()
        self._audit_scroll.setWidgetResizable(True)
        self._audit_scroll.setWidget(self._audit_container)
        self._audit_scroll.setMaximumHeight(130)
        self._audit_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QWidget { background: transparent; }"
        )
        audit_lay.addWidget(self._audit_scroll)
        lay.addWidget(self._audit_card)

        # Action bar — 2 clean rows for comfortable click targets
        actions_box = QVBoxLayout()
        actions_box.setSpacing(10)

        # Row 1: Navigation & Edit
        nav_row = QHBoxLayout()
        nav_row.setSpacing(10)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setObjectName("SecondaryBtn")
        self._prev_btn.setMinimumHeight(44)
        self._prev_btn.clicked.connect(self._prev)
        nav_row.addWidget(self._prev_btn, 1)

        self._edit_btn = QPushButton("✎  Edit Text")
        self._edit_btn.setObjectName("SecondaryBtn")
        self._edit_btn.setMinimumHeight(44)
        self._edit_btn.clicked.connect(self._toggle_edit)
        nav_row.addWidget(self._edit_btn, 1)

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setObjectName("SecondaryBtn")
        self._next_btn.setMinimumHeight(44)
        self._next_btn.clicked.connect(self._next)
        nav_row.addWidget(self._next_btn, 1)

        actions_box.addLayout(nav_row)

        # Row 2: Verification Outcomes (Reject, Flag, Approve)
        decision_row = QHBoxLayout()
        decision_row.setSpacing(10)

        self._reject_btn = QPushButton("✕  Reject")
        self._reject_btn.setObjectName("DangerBtn")
        self._reject_btn.setMinimumHeight(46)
        self._reject_btn.clicked.connect(self._reject)
        decision_row.addWidget(self._reject_btn, 1)

        self._flag_btn = QPushButton("⚐  Flag")
        self._flag_btn.setMinimumHeight(46)
        self._flag_btn.setStyleSheet(
            "QPushButton { background: rgba(245, 158, 11, 0.15); color: #F59E0B;"
            "border: 1px solid #F59E0B; border-radius: 10px; font-weight: 600; font-size: 14px; }"
            "QPushButton:hover { background: #F59E0B; color: #FFFFFF; }"
        )
        self._flag_btn.clicked.connect(self._flag)
        decision_row.addWidget(self._flag_btn, 1)

        self._approve_btn = QPushButton("✓  Approve Comment")
        self._approve_btn.setObjectName("SuccessBtn")
        self._approve_btn.setMinimumHeight(46)
        self._approve_btn.clicked.connect(self._approve)
        decision_row.addWidget(self._approve_btn, 2)

        actions_box.addLayout(decision_row)
        lay.addLayout(actions_box)

        hint = QLabel(
            "Keyboard Shortcuts: A = Approve  ·  R = Reject  ·  F = Flag  ·  ← / → = Prev / Next"
        )
        hint.setObjectName("SubCaption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #6B7280; font-size: 12px; padding-top: 4px;")
        lay.addWidget(hint)

        lay.addStretch()
        scroll.setWidget(panel)
        return scroll

    # ── Canvas / comment helpers ──────────────────────────────────

    def _on_category_changed(self, new_cat: str) -> None:
        if not new_cat:
            return
        self._cat_badge.set_category(new_cat)
        if self._comments and self._idx < len(self._comments):
            c = self._comments[self._idx]
            if isinstance(c, dict):
                c["category"] = new_cat
            else:
                setattr(c, "category", new_cat)

    def _on_box_clicked(self, cid: str) -> None:
        """Handle user clicking directly on a bounding box on the canvas."""
        for idx, c in enumerate(self._comments):
            if _get(c, "id") == cid:
                self._idx = idx
                self._load_comment()
                break

    def _load_canvas(self) -> None:
        self._scene.clear()
        self._box_items = {}

        if not self._comments:
            pm = make_page_pixmap(640, 820, comments=[])
            self._scene.addPixmap(pm)
            self._scene.setSceneRect(QRectF(pm.rect()))
            self._current_canvas_page = 1
            return

        current_comment = self._comments[self._idx] if self._idx < len(self._comments) else self._comments[0]
        page_num = _get(current_comment, "page", 1)
        self._current_canvas_page = page_num

        page_comments = [
            c for c in self._comments
            if _get(c, "page", 1) == page_num
        ]

        if self._controller and self._controller.current_document:
            try:
                rendered_dto = self._controller.pdf_service.get_page_render(
                    self._controller.current_document.file_path, page_num, dpi=150
                )
                pm = QPixmap()
                pm.loadFromData(rendered_dto.image_bytes)
            except Exception:
                pm = make_page_pixmap(640, 820, comments=[])
        else:
            pm = make_page_pixmap(640, 820, comments=[])

        self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))

        width = pm.width()
        height = pm.height()

        for c in page_comments:
            bbox   = _get(c, "bbox", (0, 0, 0, 0))
            cid    = _get(c, "id", "")
            
            x = bbox[0] * width
            y = bbox[1] * height
            w = bbox[2] * width
            h = bbox[3] * height

            adapter = _CommentAdapter(c)
            item = BBoxItem(adapter, QRectF(x, y, w, h), on_click=self._on_box_clicked)
            self._scene.addItem(item)
            self._box_items[cid] = item

    def _highlight_current_box(self) -> None:
        """Visually highlight the active comment box and pan/zoom directly onto it."""
        if not self._comments or self._idx >= len(self._comments):
            return

        c = self._comments[self._idx]
        cid = _get(c, "id", "")
        page_num = _get(c, "page", 1)

        # Reload canvas if comment is on a different page or boxes not yet built
        if self._current_canvas_page != page_num or cid not in self._box_items:
            self._load_canvas()

        # Update visual styles across all boxes on the active page
        for bid, item in self._box_items.items():
            if bid == cid:
                # Active highlight: vibrant cyan/blue glowing border with high z-index
                active_pen = QPen(QColor("#00E5FF"), 3.5)
                active_pen.setStyle(Qt.PenStyle.SolidLine)
                item.setPen(active_pen)
                fill_color = QColor("#00E5FF")
                fill_color.setAlphaF(0.35)
                item.setBrush(QBrush(fill_color))
                item.setZValue(10)
            else:
                # Inactive boxes: standard subtle styling
                label = _get(item.comment, "label", "")
                status = _get(item.comment, "status", "Pending")
                if "blue" in str(label).lower() or str(label) in ("comment_blue", "native_blue_markup"):
                    col_hex = "#3B82F6"
                elif "yellow" in str(label).lower():
                    col_hex = "#FBBF24"
                elif "green" in str(label).lower():
                    col_hex = "#10B981"
                elif status == "Approved":
                    col_hex = "#4ADE80"
                else:
                    col_hex = "#EF4444"

                normal_pen = QPen(QColor(col_hex), 1.5)
                normal_pen.setStyle(Qt.PenStyle.SolidLine)
                item.setPen(normal_pen)
                fill_color = QColor(col_hex)
                fill_color.setAlphaF(0.15)
                item.setBrush(QBrush(fill_color))
                item.setZValue(1)

        # Auto-pan & zoom into the active bounding box
        if cid in self._box_items:
            rect = self._box_items[cid].sceneBoundingRect()
            if not rect.isEmpty() and rect.width() > 0 and rect.height() > 0:
                target_rect = rect.adjusted(-120, -120, 120, 120)
                self._view.fitInView(target_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def _load_comment(self) -> None:
        if not self._comments:
            self._prog_lbl.setText("No comments available")
            return

        c     = self._comments[self._idx]
        total = len(self._comments)
        cid   = _get(c, "id", "")

        self._prog_lbl.setText(f"Comment {self._idx + 1} of {total}")
        self._prog_bar.setValue(self._idx + 1)

        drawing_ref = _get(c, "drawing_no", _get(c, "drawing_id", ""))
        page_ref    = _get(c, "page", 1)
        self._comment_id_lbl.setText(f"{cid}  ·  {drawing_ref}  ·  pg {page_ref}")

        self._ocr_edit.setPlainText(_get(c, "ocr_text", ""))
        category = _get(c, "category", "Dimensional")
        self._cat_combo.setCurrentText(category)
        self._cat_badge.set_category(category)

        confidence = _get(c, "confidence", 0.0)
        self._conf_lbl.setText(f"{int(confidence * 100)}%")
        if hasattr(self, "_conf_bar"):
            self._conf_bar.setValue(int(confidence * 100))
        self._status_chip.set_status(self._statuses.get(cid, _get(c, "status", "Pending")))

        self._prev_btn.setEnabled(self._idx > 0)
        self._next_btn.setEnabled(self._idx < total - 1)

        self._load_audit_trail(cid)
        self._highlight_current_box()

    def _flash_card(self, color: str) -> None:
        orig = self._edit_card.styleSheet()
        self._edit_card.setStyleSheet(
            f"#Card {{ border:2px solid {color}; border-radius:8px; }}"
        )
        QTimer.singleShot(350, lambda: self._edit_card.setStyleSheet(orig))

    def _toggle_audit_panel(self) -> None:
        is_visible = self._audit_scroll.isVisible()
        self._audit_scroll.setVisible(not is_visible)
        count_text = self._audit_toggle_btn.text().split("Audit History")[-1]
        prefix = "▶" if is_visible else "▼"
        self._audit_toggle_btn.setText(f"{prefix}  Audit History{count_text}")

    def _build_audit_row(self, entry: Any) -> QWidget:
        row_frame = QFrame()
        row_frame.setStyleSheet(
            "QFrame { background: #26272B; border: 1px solid #3A3C42; border-radius: 6px; }"
        )
        row_lay = QHBoxLayout(row_frame)
        row_lay.setContentsMargins(8, 5, 8, 5)
        row_lay.setSpacing(8)

        raw_action = str(_get(entry, "action", "action"))
        action_name = raw_action.upper()
        badge_styles = {
            "APPROVE": ("#4ADE80", "#1a3d26"),
            "REJECT": ("#F87171", "#3d1a1a"),
            "FLAG": ("#FBBF24", "#3d2e0a"),
            "EDIT_TEXT": ("#3E9BFF", "#0d2540"),
            "EDIT_CATEGORY": ("#A78BFA", "#2a1a4d"),
            "BULK_APPROVE": ("#2DD4BF", "#0a2d2a"),
        }
        fg, bg = badge_styles.get(action_name, ("#A6A9B1", "#3A3C42"))
        action_lbl = QLabel(action_name)
        action_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        action_lbl.setStyleSheet(
            f"color: {fg}; background-color: {bg}; border-radius: 3px; padding: 2px 6px;"
        )
        row_lay.addWidget(action_lbl)

        user_id = _get(entry, "changed_by_user_id", "") or _get(entry, "reviewer_id", "") or "anonymous"
        user_lbl = QLabel(f"by {user_id}")
        user_lbl.setFont(QFont("Segoe UI Variable", 11, QFont.Weight.DemiBold))
        user_lbl.setStyleSheet("color: #F2F3F5;")
        row_lay.addWidget(user_lbl)

        details = _get(entry, "details", "") or _get(entry, "notes", "")
        if not details:
            old_v = _get(entry, "old_value", "")
            new_v = _get(entry, "new_value", "")
            if old_v or new_v:
                details = f"{old_v} → {new_v}"
        if details:
            detail_lbl = QLabel(str(details))
            detail_lbl.setFont(QFont("Segoe UI Variable", 11))
            detail_lbl.setStyleSheet("color: #A6A9B1;")
            detail_lbl.setWordWrap(True)
            row_lay.addWidget(detail_lbl)

        row_lay.addStretch()

        ts = _get(entry, "timestamp", "")
        if hasattr(ts, "strftime"):
            ts_str = ts.strftime("%H:%M:%S")
        else:
            ts_str = str(ts)
        ts_lbl = QLabel(ts_str)
        ts_lbl.setFont(QFont("Cascadia Code", 10))
        ts_lbl.setStyleSheet("color: #717680;")
        row_lay.addWidget(ts_lbl)

        return row_frame

    def _load_audit_trail(self, cid: str) -> None:
        """Fetch and render the audit history for the specified comment."""
        while self._audit_items_lay.count() > 0:
            item = self._audit_items_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not cid:
            self._audit_toggle_btn.setText("▼  Audit History (0)")
            empty_lbl = QLabel("No comment selected.")
            empty_lbl.setFont(QFont("Segoe UI", 11))
            empty_lbl.setStyleSheet("color: #717680; padding: 2px 4px;")
            self._audit_items_lay.addWidget(empty_lbl)
            return

        entries: List[Any] = []
        if self._controller and hasattr(self._controller, "get_audit_trail"):
            try:
                entries = self._controller.get_audit_trail(cid) or []
            except Exception:
                entries = []

        count = len(entries)
        prefix = "▼" if self._audit_scroll.isVisible() else "▶"
        self._audit_toggle_btn.setText(f"{prefix}  Audit History ({count})")

        if not entries:
            empty_lbl = QLabel("No audit history recorded yet.")
            empty_lbl.setFont(QFont("Segoe UI", 11))
            empty_lbl.setStyleSheet("color: #717680; padding: 2px 4px;")
            self._audit_items_lay.addWidget(empty_lbl)
        else:
            for entry in reversed(entries):
                self._audit_items_lay.addWidget(self._build_audit_row(entry))

    def _set_status(self, status: str) -> None:
        """Update status in memory and persist to database via controller."""
        if not self._comments:
            return
        c   = self._comments[self._idx]
        cid = _get(c, "id", "")
        self._statuses[cid] = status
        self._status_chip.set_status(status)

        # INTEGRATION NOTE:
        # Status is persisted through AppController → CommentRepository.
        # Only statuses from the agreed vocabulary are accepted:
        # "Pending", "Approved", "Rejected", "Flagged"
        if self._controller and cid and not cid.startswith("C-"):
            # cid starting with "C-" indicates mock data — do not persist
            self._controller.update_comment_status(cid, status)
            self._load_audit_trail(cid)

    # ── Action slots ──────────────────────────────────────────────

    def _approve(self) -> None:
        self._set_status("Approved")
        self._flash_card("#4ADE80")
        QTimer.singleShot(400, self._next)

    def _reject(self) -> None:
        self._set_status("Rejected")
        self._flash_card("#F87171")
        QTimer.singleShot(400, self._next)

    def _flag(self) -> None:
        self._set_status("Flagged")
        self._flash_card("#FBBF24")
        QTimer.singleShot(400, self._next)

    def _toggle_edit(self) -> None:
        ro = self._ocr_edit.isReadOnly()
        if ro:
            # Switching to edit mode
            self._ocr_edit.setReadOnly(False)
            self._edit_btn.setText("💾  Save")
        else:
            # Switching back to read-only = user intends to save
            self._ocr_edit.setReadOnly(True)
            self._edit_btn.setText("✎  Edit")

            # INTEGRATION NOTE:
            # Persist the edited OCR text through AppController.
            # Only persists for real database comments (not mock data).
            if self._comments:
                c   = self._comments[self._idx]
                cid = _get(c, "id", "")
                if self._controller and cid and not cid.startswith("C-"):
                    self._controller.update_comment_text(
                        cid, self._ocr_edit.toPlainText()
                    )
                    self._load_audit_trail(cid)

    def _prev(self) -> None:
        if self._idx > 0:
            self._idx -= 1
            self._load_comment()

    def _next(self) -> None:
        if self._idx < len(self._comments) - 1:
            self._idx += 1
            self._load_comment()

    # ── Keyboard navigation ───────────────────────────────────────

    def keyPressEvent(self, e: QKeyEvent) -> None:
        key = e.key()
        if key == Qt.Key.Key_A:
            self._approve()
        elif key == Qt.Key.Key_R:
            self._reject()
        elif key == Qt.Key.Key_F:
            self._flag()
        elif key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(e)
