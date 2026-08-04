"""3.8 Human Verification Screen — splitter: PDF canvas left, review panel right."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QTextEdit, QComboBox,
                                QProgressBar, QSplitter, QSizePolicy,
                                QGraphicsView, QGraphicsScene)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtGui import QFont, QColor, QPainter, QKeyEvent

from app import mock_data as md
from app.components.chips import StatusChip, CategoryBadge
from app.screens.pdf_viewer import _make_page_pixmap


class HumanReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._comments = [c for c in md.COMMENTS]
        self._idx = 0
        self._statuses = {c.id: c.status for c in self._comments}
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Splitter ──────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)

        # Left — PDF canvas
        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHints(QPainter.RenderHint.Antialiasing |
                                   QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._load_canvas()
        splitter.addWidget(self._view)

        # Right — review panel
        self._panel = self._build_review_panel()
        splitter.addWidget(self._panel)
        splitter.setStretchFactor(0, 55)
        splitter.setStretchFactor(1, 45)

        root.addWidget(splitter)
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
        self._prog_lbl = QLabel("Comment 1 of 20")
        self._prog_lbl.setFont(QFont("Segoe UI Variable", 14, QFont.Weight.DemiBold))
        prog_hdr.addWidget(self._prog_lbl)
        prog_hdr.addStretch()
        lay.addLayout(prog_hdr)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, len(self._comments))
        self._prog_bar.setValue(1)
        self._prog_bar.setFixedHeight(4)
        self._prog_bar.setStyleSheet(
            "QProgressBar { background:#3A3C42; border-radius:2px; }"
            "QProgressBar::chunk { background: #3E9BFF; border-radius:2px; }"
        )
        lay.addWidget(self._prog_bar)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
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

        # Keyboard hint
        hint = QLabel("Keyboard: A = Approve  ·  R = Reject  ·  ← / → = Prev / Next")
        hint.setObjectName("SubCaption")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(hint)

        lay.addStretch()
        return panel

    # ── Data helpers ──────────────────────────────────────────────

    def _load_canvas(self):
        self._scene.clear()
        pm = _make_page_pixmap(640, 820)
        self._scene.addPixmap(pm)

    def _load_comment(self):
        if not self._comments:
            return
        c = self._comments[self._idx]
        total = len(self._comments)

        self._prog_lbl.setText(f"Comment {self._idx+1} of {total}")
        self._prog_bar.setValue(self._idx + 1)
        self._comment_id_lbl.setText(f"{c.id}  ·  {c.drawing_no}  ·  pg {c.page}")
        self._ocr_edit.setPlainText(c.ocr_text)
        self._cat_combo.setCurrentText(c.category)
        self._cat_badge.set_category(c.category)
        conf_pct = int(c.confidence * 100)
        self._conf_lbl.setText(f"Confidence: {conf_pct}%")
        st = self._statuses.get(c.id, c.status)
        self._status_chip.set_status(st)
        self._prev_btn.setEnabled(self._idx > 0)
        self._next_btn.setEnabled(self._idx < total - 1)

    def _flash_card(self, color: str):
        orig = self._edit_card.styleSheet()
        self._edit_card.setStyleSheet(
            f"#Card {{ border:2px solid {color}; border-radius:8px; }}"
        )
        QTimer.singleShot(350, lambda: self._edit_card.setStyleSheet(orig))

    def _set_status(self, status: str):
        c = self._comments[self._idx]
        self._statuses[c.id] = status
        self._status_chip.set_status(status)

    def _approve(self):
        self._set_status("Approved")
        self._flash_card("#4ADE80")
        QTimer.singleShot(400, self._next)

    def _reject(self):
        self._set_status("Rejected")
        self._flash_card("#F87171")
        QTimer.singleShot(400, self._next)

    def _toggle_edit(self):
        ro = self._ocr_edit.isReadOnly()
        self._ocr_edit.setReadOnly(not ro)
        self._edit_btn.setText("💾  Save" if ro else "✎  Edit")

    def _prev(self):
        if self._idx > 0:
            self._idx -= 1
            self._load_comment()

    def _next(self):
        if self._idx < len(self._comments) - 1:
            self._idx += 1
            self._load_comment()

    def keyPressEvent(self, e: QKeyEvent):
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
