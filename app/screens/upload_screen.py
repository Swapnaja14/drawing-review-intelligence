"""
upload_screen.py — PDF upload screen.

Provides:
    UploadPage(QWidget)
        Drag-and-drop zone (DropZone), file detail card, progress bar,
        and start-processing button connected to AppController & WorkflowEngine backend.
"""
from __future__ import annotations
import os
from pathlib import Path
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
    Integrates with AppController & ProcessingWorkflowEngine backend.

    Signals
    -------
    open_viewer_requested : Signal()
        Emitted when user completes processing and clicks to view the drawing.
    """

    open_viewer_requested = Signal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._filepath: str | None = None
        self._controller = controller

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

        # ── Selected file card ────────────────────────────────────
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

        # ── Progress bar & Status message ─────────────────────────
        self._status_lbl = QLabel("")
        self._status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_lbl.setFont(QFont("Segoe UI", 12))
        self._status_lbl.setStyleSheet("color: #3E9BFF;")
        self._status_lbl.hide()
        root.addWidget(self._status_lbl)

        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedHeight(8)
        self._prog.hide()
        root.addWidget(self._prog)

        # ── Start processing button ───────────────────────────────
        self._start_btn = QPushButton("  Start Processing Workflow")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setFixedWidth(260)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start)
        root.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignCenter)

        root.addStretch()

        if self._controller:
            self._connect_controller_signals()

    def set_controller(self, controller) -> None:
        self._controller = controller
        if self._controller:
            self._connect_controller_signals()

    def _connect_controller_signals(self) -> None:
        if not self._controller:
            return
        self._controller.workflow_step_signal.connect(self._on_workflow_step)
        self._controller.workflow_completed_signal.connect(self._on_workflow_completed)
        self._controller.processing_error_signal.connect(self._on_doc_error)

    # ── Slots ─────────────────────────────────────────────────────

    def _browse(self) -> None:
        path = open_pdf_file(self)
        if path:
            self._on_file(path)

    def _show_recent(self) -> None:
        menu = QMenu(self)
        for name in ["UCC-E-101.pdf", "LNG-T-501.pdf", "RU7-P-201.pdf"]:
            menu.addAction(name)
        menu.exec(self.mapToGlobal(self._drop.geometry().bottomLeft()))

    def _on_file(self, path: str) -> None:
        self._filepath = path
        name = os.path.basename(path)

        # Re-reset button to default state
        self._start_btn.setText("  Start Processing Workflow")
        try:
            self._start_btn.clicked.disconnect()
        except Exception:
            pass
        self._start_btn.clicked.connect(self._start)

        if self._controller:
            val_res = self._controller.validate_file(path)
            if not val_res.is_valid:
                self._fname.setText(name)
                self._fmeta.setText(f"❌ {val_res.error_message}")
                self._file_card.show()
                self._start_btn.setEnabled(False)
                return
            size_str = f"{val_res.file_size_mb} MB"
        else:
            size_mb = (
                round(os.path.getsize(path) / (1024 * 1024), 2)
                if os.path.exists(path) else "?"
            )
            size_str = f"{size_mb} MB"

        self._fname.setText(name)
        self._fmeta.setText(f"{size_str}  ·  Validated for Processing")
        self._file_card.show()
        self._start_btn.setEnabled(True)

    def _clear_file(self) -> None:
        self._filepath = None
        self._file_card.hide()
        self._prog.hide()
        self._status_lbl.hide()
        self._prog.setValue(0)
        self._start_btn.setText("  Start Processing Workflow")
        try:
            self._start_btn.clicked.disconnect()
        except Exception:
            pass
        self._start_btn.clicked.connect(self._start)
        self._start_btn.setEnabled(False)

    def _start(self) -> None:
        if not self._filepath:
            return

        self._prog.show()
        self._status_lbl.show()
        self._prog.setValue(10)
        self._start_btn.setText("Processing Pipeline Active...")
        self._start_btn.setEnabled(False)

        if self._controller:
            self._controller.start_processing_workflow(self._filepath)
        else:
            self._prog.setValue(100)

    def _on_workflow_step(self, step_snapshot) -> None:
        self._prog.setValue(step_snapshot.progress_percentage)
        self._status_lbl.setText(f"{step_snapshot.step_name}: {step_snapshot.message}")

    def _on_workflow_completed(self, result_dto) -> None:
        self._prog.setValue(100)
        self._status_lbl.setText(f"✓ Workflow Complete in {result_dto.processing_duration_seconds}s!")
        self._start_btn.setText("  View PDF Drawing ➔  ")
        self._start_btn.setEnabled(True)
        try:
            self._start_btn.clicked.disconnect()
        except Exception:
            pass
        self._start_btn.clicked.connect(self._open_viewer)

    def _open_viewer(self) -> None:
        self.open_viewer_requested.emit()

    def _on_doc_error(self, error_msg: str) -> None:
        self._prog.hide()
        self._status_lbl.setText(f"❌ {error_msg}")
        self._start_btn.setText("Processing Failed")
        self._start_btn.setEnabled(True)
