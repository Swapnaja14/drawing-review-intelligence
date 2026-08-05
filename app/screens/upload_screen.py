"""
upload_screen.py — PDF upload screen.

Provides:
    UploadPage(QWidget)
        Drag-and-drop zone (DropZone), file detail card, progress bar,
        and start-processing button.
"""
from __future__ import annotations
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QProgressBar, QFrame,
                                QToolButton, QSizePolicy, QMenu)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from app.components.upload_widget import DropZone
from app.components.dialogs import open_pdf_file


class UploadPage(QWidget):
    """
    Upload screen — drag-and-drop a PDF drawing or browse for one.

    A simulated upload-progress bar and file-detail card are shown after
    a file is selected.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._filepath: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ── Drop zone ─────────────────────────────────────────────
        self._drop = DropZone()
        self._drop.file_dropped.connect(self._on_file)

        inner = QVBoxLayout(self._drop)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.setSpacing(16)

        icon = QLabel("☁")
        icon.setFont(QFont("Segoe UI", 52))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color:#3E9BFF;")
        inner.addWidget(icon)

        instr = QLabel("Drag & drop a PDF here")
        instr.setFont(QFont("Segoe UI Variable", 20, QFont.Weight.DemiBold))
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setStyleSheet("color:#F2F3F5;")
        inner.addWidget(instr)

        sub = QLabel("Supports PDF drawings up to 500 MB")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("SubCaption")
        inner.addWidget(sub)

        inner.addSpacing(8)

        browse_btn = QPushButton("  Browse PDF File")
        browse_btn.setObjectName("PrimaryBtn")
        browse_btn.setFixedHeight(40)
        browse_btn.setFixedWidth(200)
        browse_btn.clicked.connect(self._browse)
        inner.addWidget(browse_btn, 0, Qt.AlignmentFlag.AlignCenter)

        recent_btn = QPushButton("Recent Files ▾")
        recent_btn.setObjectName("GhostBtn")
        recent_btn.clicked.connect(self._show_recent)
        inner.addWidget(recent_btn, 0, Qt.AlignmentFlag.AlignCenter)

        root.addWidget(self._drop)

        # ── Selected file card (hidden by default) ────────────────
        self._file_card = QFrame()
        self._file_card.setObjectName("Card")
        self._file_card.hide()

        fc_lay = QHBoxLayout(self._file_card)
        fc_lay.setContentsMargins(16, 16, 16, 16)
        fc_lay.setSpacing(12)

        self._file_icon = QLabel("📄")
        self._file_icon.setFont(QFont("Segoe UI", 24))
        fc_lay.addWidget(self._file_icon)

        meta = QVBoxLayout()
        self._fname = QLabel("filename.pdf")
        self._fname.setFont(QFont("Cascadia Code", 13))
        meta.addWidget(self._fname)
        self._fmeta = QLabel("— · — pages")
        self._fmeta.setObjectName("SubCaption")
        meta.addWidget(self._fmeta)
        fc_lay.addLayout(meta, 1)

        remove_btn = QToolButton()
        remove_btn.setText("✕")
        remove_btn.setToolTip("Remove file")
        remove_btn.clicked.connect(self._clear_file)
        fc_lay.addWidget(remove_btn)

        root.addWidget(self._file_card)

        # ── Progress bar ──────────────────────────────────────────
        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedHeight(8)
        self._prog.hide()
        root.addWidget(self._prog)

        # ── Start processing button ───────────────────────────────
        self._start_btn = QPushButton("  Start Processing")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setFixedWidth(240)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start)
        root.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignCenter)

        root.addStretch()

        # Simulated progress timer
        self._timer = QTimer()
        self._timer.setInterval(60)
        self._prog_val = 0
        self._timer.timeout.connect(self._tick)

    # ── Slots ─────────────────────────────────────────────────────

    def _browse(self) -> None:
        path = open_pdf_file(self)
        if path:
            self._on_file(path)

    def _show_recent(self) -> None:
        menu = QMenu(self)
        for name in ["UCC-E-101.pdf", "LNG-T-501.pdf", "RU7-P-201.pdf",
                     "OP-M-701.pdf", "PL-N-301.pdf"]:
            menu.addAction(name)
        menu.exec(self.mapToGlobal(self._drop.geometry().bottomLeft()))

    def _on_file(self, path: str) -> None:
        self._filepath = path
        name = os.path.basename(path)
        size_mb = (
            round(os.path.getsize(path) / (1024 * 1024), 2)
            if os.path.exists(path) else "?"
        )
        self._fname.setText(name)
        self._fmeta.setText(f"{size_mb} MB  ·  simulated pages")
        self._file_card.show()
        self._start_btn.setEnabled(True)

    def _clear_file(self) -> None:
        self._filepath = None
        self._file_card.hide()
        self._prog.hide()
        self._prog.setValue(0)
        self._start_btn.setEnabled(False)

    def _start(self) -> None:
        self._prog.show()
        self._prog_val = 0
        self._timer.start()
        self._start_btn.setEnabled(False)

    def _tick(self) -> None:
        self._prog_val += 2
        self._prog.setValue(min(self._prog_val, 100))
        if self._prog_val >= 100:
            self._timer.stop()
            self._start_btn.setText("  ✓  Processing Complete")
            self._start_btn.setEnabled(False)
