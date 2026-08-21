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
                                QGraphicsView, QGraphicsScene)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPainter, QKeyEvent

from app import mock_data as md
from app.components.chips import StatusChip, CategoryBadge
from app.components.pdf_canvas import make_page_pixmap

# Agreed status vocabulary — do not use any other values
_VALID_STATUSES = ("Pending", "Approved", "Rejected", "Flagged")


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
        # INTEGRATION NOTE:
        # Database comments are normalised dicts (from AppController.normalise_comment).
        # Mock data items are dataclass objects.
        # The _get() helper above handles both transparently.
        # When the controller has a current_drawing_id, real comments are loaded.
        # When the database is empty, the screen falls back to mock data so it
        # remains usable during development.
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            self._comments: List[Any] = db_comments if db_comments else list(md.COMMENTS)
        else:
            self._comments = list(md.COMMENTS)

        self._idx     = 0
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
            if db_comments:
                self._comments = db_comments
                self._idx = 0
                self._statuses = {
                    c["id"]: c["status"] for c in self._comments
                }
                self._prog_bar.setRange(0, len(self._comments))
                self._load_canvas()
                self._load_comment()

    # ── Panel builder ─────────────────────────────────────────────

    def _build_review_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("Card")
        panel.setStyleSheet("#Card { border-radius:0; }")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(14)

        # Progress header
        prog_hdr = QHBoxLayout()
        self._prog_lbl = QLabel("Comment 1 of 0")
        self._prog_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Weight.DemiBold))
        prog_hdr.addWidget(self._prog_lbl)
        prog_hdr.addStretch()
        lay.addLayout(prog_hdr)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, max(len(self._comments), 1))
        self._prog_bar.setValue(1)
        self._prog_bar.setFixedHeight(4)
        self._prog_bar.setStyleSheet(
            "QProgressBar { background:#3A3C42; border-radius:2px; }"
            "QProgressBar::chunk { background: #3E9BFF; border-radius:2px; }"
        )
        lay.addWidget(self._prog_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        # Comment edit card
        self._edit_card = QFrame()
        self._edit_card.setObjectName("Card")
        edit_lay = QVBoxLayout(self._edit_card)
        edit_lay.setContentsMargins(16, 16, 16, 16)
        edit_lay.setSpacing(10)

        self._comment_id_lbl = QLabel("")
        self._comment_id_lbl.setFont(QFont("Cascadia Code", 12))
        self._comment_id_lbl.setStyleSheet("color:#A6A9B1;")
        edit_lay.addWidget(self._comment_id_lbl)

        ocr_lbl = QLabel("OCR Text")
        ocr_lbl.setObjectName("FormLabel")
        edit_lay.addWidget(ocr_lbl)

        self._ocr_edit = QTextEdit()
        self._ocr_edit.setFixedHeight(90)
        self._ocr_edit.setReadOnly(True)
        self._ocr_edit.setFont(QFont("Cascadia Code", 12))
        edit_lay.addWidget(self._ocr_edit)

        cat_lbl = QLabel("Category")
        cat_lbl.setObjectName("FormLabel")
        edit_lay.addWidget(cat_lbl)

        self._cat_combo = QComboBox()
        self._cat_combo.addItems(md.CATEGORIES)
        self._cat_combo.setFixedHeight(36)
        edit_lay.addWidget(self._cat_combo)

        conf_row = QHBoxLayout()
        self._conf_lbl = QLabel("Confidence: —")
        self._conf_lbl.setObjectName("SubCaption")
        conf_row.addWidget(self._conf_lbl)
        conf_row.addStretch()
        self._cat_badge = CategoryBadge("")
        conf_row.addWidget(self._cat_badge)
        edit_lay.addLayout(conf_row)

        lay.addWidget(self._edit_card)

        # Status indicator
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Current Status:"))
        self._status_chip = StatusChip("Pending")
        status_row.addWidget(self._status_chip)
        status_row.addStretch()
        lay.addLayout(status_row)

        # Action bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(8)

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setObjectName("SecondaryBtn")
        self._prev_btn.setFixedHeight(36)
        self._prev_btn.clicked.connect(self._prev)
        action_bar.addWidget(self._prev_btn)

        action_bar.addStretch()

        self._reject_btn = QPushButton("✕  Reject")
        self._reject_btn.setObjectName("DangerBtn")
        self._reject_btn.setFixedHeight(36)
        self._reject_btn.clicked.connect(self._reject)
        action_bar.addWidget(self._reject_btn)

        self._edit_btn = QPushButton("✎  Edit")
        self._edit_btn.setObjectName("SecondaryBtn")
        self._edit_btn.setFixedHeight(36)
        self._edit_btn.clicked.connect(self._toggle_edit)
        action_bar.addWidget(self._edit_btn)

        self._approve_btn = QPushButton("✓  Approve")
        self._approve_btn.setObjectName("SuccessBtn")
        self._approve_btn.setFixedHeight(36)
        self._approve_btn.clicked.connect(self._approve)
        action_bar.addWidget(self._approve_btn)

        action_bar.addStretch()

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setObjectName("SecondaryBtn")
        self._next_btn.setFixedHeight(36)
        self._next_btn.clicked.connect(self._next)
        action_bar.addWidget(self._next_btn)

        lay.addLayout(action_bar)

        hint = QLabel(
            "Keyboard: A = Approve  ·  R = Reject  ·  ← / → = Prev / Next"
        )
        hint.setObjectName("SubCaption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)

        lay.addStretch()
        return panel

    # ── Canvas / comment helpers ──────────────────────────────────

    def _load_canvas(self) -> None:
        self._scene.clear()
        # Pass current page's comments (normalised) so canvas uses same data
        # as the comment panel. Falls back to mock bbox for mock data.
        page_comments = [
            c for c in self._comments
            if _get(c, "page", 1) == (
                _get(self._comments[self._idx], "page", 1)
                if self._comments else 1
            )
        ] if self._comments else []
        self._scene.addPixmap(make_page_pixmap(640, 820, comments=page_comments))

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
        self._conf_lbl.setText(f"Confidence: {int(confidence * 100)}%")
        self._status_chip.set_status(self._statuses.get(cid, _get(c, "status", "Pending")))

        self._prev_btn.setEnabled(self._idx > 0)
        self._next_btn.setEnabled(self._idx < total - 1)

    def _flash_card(self, color: str) -> None:
        orig = self._edit_card.styleSheet()
        self._edit_card.setStyleSheet(
            f"#Card {{ border:2px solid {color}; border-radius:8px; }}"
        )
        QTimer.singleShot(350, lambda: self._edit_card.setStyleSheet(orig))

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

    # ── Action slots ──────────────────────────────────────────────

    def _approve(self) -> None:
        self._set_status("Approved")
        self._flash_card("#4ADE80")
        QTimer.singleShot(400, self._next)

    def _reject(self) -> None:
        self._set_status("Rejected")
        self._flash_card("#F87171")
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

    def _prev(self) -> None:
        if self._idx > 0:
            self._idx -= 1
            self._load_canvas()
            self._load_comment()

    def _next(self) -> None:
        if self._idx < len(self._comments) - 1:
            self._idx += 1
            self._load_canvas()
            self._load_comment()

    # ── Keyboard navigation ───────────────────────────────────────

    def keyPressEvent(self, e: QKeyEvent) -> None:
        key = e.key()
        if key == Qt.Key.Key_A:
            self._approve()
        elif key == Qt.Key.Key_R:
            self._reject()
        elif key == Qt.Key.Key_Left:
            self._prev()
        elif key == Qt.Key.Key_Right:
            self._next()
        else:
            super().keyPressEvent(e)
