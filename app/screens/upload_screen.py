"""
upload_screen.py — Redesigned Upload Drawing screen.

Provides:
    UploadPage(QWidget)
        Polished enterprise drop zone, horizontal uploaded file cards with tooltips,
        real-time pipeline progress indicators, and post-processing completion view.
"""
from __future__ import annotations
import os
import time
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QProgressBar, QFrame,
                                QToolButton, QSizePolicy, QMenu, QScrollArea)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont

from app.components.upload_widget import DropZone
from app.components.dialogs import open_pdf_file


class UploadPage(QWidget):
    """
    Upload screen — drag-and-drop a PDF drawing or browse for one.
    Integrates with AppController & ProcessingWorkflowEngine backend.
    """

    open_viewer_requested = Signal()

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._filepath: str | None = None
        self._controller = controller
        self._start_time: float | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(40, 32, 40, 40)
        root.setSpacing(24)
        root.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # ── Header ───────────────────────────────────────────────
        hdr_box = QVBoxLayout()
        hdr_box.setSpacing(4)
        title = QLabel("Upload Engineering Drawing")
        title.setFont(QFont("Inter", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #F3F4F6;")
        hdr_box.addWidget(title)

        subtitle = QLabel("Upload scanned or native digital PDF drawings to detect comments, run OCR, and classify issues.")
        subtitle.setObjectName("PageSubtitle")
        hdr_box.addWidget(subtitle)
        root.addLayout(hdr_box)

        # ── Centered Drop Zone ────────────────────────────────────
        self._drop = DropZone()
        self._drop.setMinimumHeight(280)
        self._drop.setMaximumWidth(780)
        self._drop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._drop.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 2px dashed #CBD5E1; border-radius: 16px; }"
            "QFrame:hover { border-color: #2563EB; background: #EFF6FF; }"
        )
        self._drop.file_dropped.connect(self._on_file)

        inner = QVBoxLayout(self._drop)
        inner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.setContentsMargins(32, 32, 32, 32)
        inner.setSpacing(14)

        icon = QLabel("☁")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("color: #2563EB;")
        inner.addWidget(icon)

        instr = QLabel("Drag & drop a PDF drawing here")
        instr.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        instr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        instr.setStyleSheet("color: #0F172A;")
        inner.addWidget(instr)

        sub = QLabel("Supports single & multi-sheet engineering PDF drawings up to 500 MB")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("SubCaption")
        inner.addWidget(sub)

        inner.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("  Browse PDF File  ")
        browse_btn.setObjectName("PrimaryBtn")
        browse_btn.setFixedHeight(46)
        browse_btn.setMinimumWidth(200)
        browse_btn.clicked.connect(self._browse)
        btn_row.addWidget(browse_btn)

        recent_btn = QPushButton("Recent Drawings ▾")
        recent_btn.setObjectName("SecondaryBtn")
        recent_btn.setFixedHeight(46)
        recent_btn.setMinimumWidth(160)
        recent_btn.clicked.connect(self._show_recent)
        btn_row.addWidget(recent_btn)

        inner.addLayout(btn_row)
        root.addWidget(self._drop, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── Selected File Card (Horizontal) ───────────────────────
        self._file_card = QFrame()
        self._file_card.setObjectName("Card")
        self._file_card.setMaximumWidth(780)
        self._file_card.setStyleSheet(
            "#Card { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; }"
        )
        self._file_card.hide()

        fc_lay = QHBoxLayout(self._file_card)
        fc_lay.setContentsMargins(20, 16, 20, 16)
        fc_lay.setSpacing(16)

        self._file_icon = QLabel("📄")
        self._file_icon.setFont(QFont("Segoe UI Emoji", 28))
        fc_lay.addWidget(self._file_icon)

        meta = QVBoxLayout()
        meta.setSpacing(4)
        self._fname = QLabel("filename.pdf")
        self._fname.setFont(QFont("Cascadia Code", 13, QFont.Weight.Bold))
        self._fname.setStyleSheet("color: #0F172A;")
        meta.addWidget(self._fname)

        self._fmeta = QLabel("— · — pages")
        self._fmeta.setObjectName("SubCaption")
        meta.addWidget(self._fmeta)
        fc_lay.addLayout(meta, 1)

        self._status_chip = QLabel("READY")
        self._status_chip.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self._status_chip.setStyleSheet(
            "color: #059669; background: rgba(5, 150, 105, 0.10); border-radius: 6px; padding: 4px 10px;"
        )
        fc_lay.addWidget(self._status_chip)

        remove_btn = QToolButton()
        remove_btn.setText("✕")
        remove_btn.setFixedSize(32, 32)
        remove_btn.setToolTip("Remove selected drawing")
        remove_btn.setStyleSheet(
            "QToolButton { background: transparent; color: #64748B; font-size: 14px; border-radius: 6px; }"
            "QToolButton:hover { background: rgba(220, 38, 38, 0.10); color: #DC2626; }"
        )
        remove_btn.clicked.connect(self._clear_file)
        fc_lay.addWidget(remove_btn)

        root.addWidget(self._file_card, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── Processing & Status Section ───────────────────────────
        self._proc_container = QFrame()
        self._proc_container.setMaximumWidth(780)
        self._proc_container.setStyleSheet(
            "background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px;"
        )
        self._proc_container.hide()

        proc_lay = QVBoxLayout(self._proc_container)
        proc_lay.setContentsMargins(24, 20, 24, 20)
        proc_lay.setSpacing(12)

        proc_top = QHBoxLayout()
        self._step_title = QLabel("AI Pipeline Active")
        self._step_title.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._step_title.setStyleSheet("color: #F3F4F6;")
        proc_top.addWidget(self._step_title)
        proc_top.addStretch()

        self._pct_lbl = QLabel("0%")
        self._pct_lbl.setFont(QFont("Inter", 14, QFont.Weight.Bold))
        self._pct_lbl.setStyleSheet("color: #3B82F6;")
        proc_top.addWidget(self._pct_lbl)
        proc_lay.addLayout(proc_top)

        self._prog = QProgressBar()
        self._prog.setRange(0, 100)
        self._prog.setValue(0)
        self._prog.setFixedHeight(10)
        proc_lay.addWidget(self._prog)

        self._status_lbl = QLabel("Initializing document loader...")
        self._status_lbl.setObjectName("SubCaption")
        proc_lay.addWidget(self._status_lbl)

        root.addWidget(self._proc_container, 0, Qt.AlignmentFlag.AlignHCenter)

        # ── Start / Action Button ─────────────────────────────────
        self._start_btn = QPushButton("  Start AI Processing Workflow  ")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setFixedHeight(48)
        self._start_btn.setMinimumWidth(280)
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._start)
        root.addWidget(self._start_btn, 0, Qt.AlignmentFlag.AlignHCenter)

        root.addStretch()
        scroll.setWidget(container)

        page_lay = QVBoxLayout(self)
        page_lay.setContentsMargins(0, 0, 0, 0)
        page_lay.addWidget(scroll)

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
        recent_drawings = [
            ("5-3552-12_COMBINE.pdf", "dataset/raw_drawings/5-3552-12_COMBINE.pdf"),
            ("UCC-E-101.pdf", "dataset/raw_drawings/UCC-E-101.pdf"),
            ("LNG-T-501.pdf", "dataset/raw_drawings/LNG-T-501.pdf"),
        ]
        for name, p in recent_drawings:
            action = menu.addAction(f"📄  {name}")
            if os.path.exists(p):
                action.triggered.connect(lambda checked=False, target=p: self._on_file(target))
        menu.exec(self.mapToGlobal(self._drop.geometry().bottomLeft()))

    def _on_file(self, path: str) -> None:
        self._filepath = path
        name = os.path.basename(path)

        self._start_btn.setText("  Start AI Processing Workflow  ")
        self._start_btn.setObjectName("PrimaryBtn")
        self._start_btn.setStyle(self._start_btn.style())
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
        self._fname.setToolTip(path)
        self._fmeta.setText(f"{size_str}  ·  Validated for Processing")
        self._status_chip.setText("READY")
        self._status_chip.setStyleSheet(
            "color: #10B981; background: rgba(16, 185, 129, 0.15); border-radius: 6px; padding: 4px 10px;"
        )
        self._file_card.show()
        self._start_btn.setEnabled(True)

    def _clear_file(self) -> None:
        self._filepath = None
        self._file_card.hide()
        self._proc_container.hide()
        self._prog.setValue(0)
        self._pct_lbl.setText("0%")
        self._start_btn.setText("  Start AI Processing Workflow  ")
        try:
            self._start_btn.clicked.disconnect()
        except Exception:
            pass
        self._start_btn.clicked.connect(self._start)
        self._start_btn.setEnabled(False)

    def _start(self) -> None:
        if not self._filepath:
            return

        self._start_time = time.time()
        self._proc_container.show()
        self._prog.setValue(10)
        self._pct_lbl.setText("10%")
        self._step_title.setText("Processing Pipeline Active...")
        self._status_lbl.setText("Running color segmentation & OCR extraction...")
        self._start_btn.setText("Processing Pipeline Active...")
        self._start_btn.setEnabled(False)

        if self._controller:
            self._controller.start_processing_workflow(self._filepath)
        else:
            self._prog.setValue(100)
            self._pct_lbl.setText("100%")

    def _on_workflow_step(self, step_snapshot) -> None:
        pct = step_snapshot.progress_percentage
        self._prog.setValue(pct)
        self._pct_lbl.setText(f"{pct}%")
        self._step_title.setText(f"Step: {step_snapshot.step_name}")
        self._status_lbl.setText(step_snapshot.message)

    def _on_workflow_completed(self, result_dto) -> None:
        self._prog.setValue(100)
        self._pct_lbl.setText("100%")
        duration = result_dto.processing_duration_seconds
        self._step_title.setText("✓ Workflow Successfully Completed")
        self._status_lbl.setText(f"Finished in {duration}s · Annotations & OCR comments saved to database.")

        self._status_chip.setText("COMPLETED")
        self._status_chip.setStyleSheet(
            "color: #3B82F6; background: rgba(59, 130, 246, 0.15); border-radius: 6px; padding: 4px 10px;"
        )

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
        self._prog.setValue(0)
        self._step_title.setText("❌ Processing Failed")
        self._status_lbl.setText(error_msg)
        self._start_btn.setText("Retry Processing")
        self._start_btn.setEnabled(True)
