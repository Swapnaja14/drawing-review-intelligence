"""
upload_widget.py — Drag-and-drop PDF upload zone.

Provides:
    DropZone(QFrame)
        Renders a dashed drop target; emits ``file_dropped(str)`` when
        a valid ``.pdf`` file is released onto it.
"""
from __future__ import annotations
from PySide6.QtWidgets import QFrame
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPainter, QPen, QColor


class DropZone(QFrame):
    """
    Drag-and-drop zone that accepts PDF files.

    The border transitions from a neutral dashed line to an accent-blue
    highlight while the user drags a file over the widget.

    Signals
    -------
    file_dropped : str
        Emitted with the local file-system path of the dropped PDF.
    """

    file_dropped = Signal(str)

    _DASH_COLOR_IDLE   = "#3A3C42"
    _DASH_COLOR_ACTIVE = "#3E9BFF"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(300)
        self._active = False

    # ── Drag helpers ──────────────────────────────────────────────

    def _set_active(self, v: bool) -> None:
        self._active = v
        self.update()

    # ── Qt overrides ──────────────────────────────────────────────

    def dragEnterEvent(self, e: QDragEnterEvent) -> None:
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._set_active(True)

    def dragLeaveEvent(self, e) -> None:
        self._set_active(False)

    def dropEvent(self, e: QDropEvent) -> None:
        self._set_active(False)
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path.lower().endswith(".pdf"):
                self.file_dropped.emit(path)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        color_hex = (
            self._DASH_COLOR_ACTIVE if self._active else self._DASH_COLOR_IDLE
        )
        pen = QPen(QColor(color_hex))
        pen.setWidth(2)
        pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        bg = QColor("#3E9BFF" if self._active else "#26272B")
        bg.setAlphaF(0.06 if self._active else 0.0)
        p.setBrush(bg)
        p.drawRoundedRect(2, 2, self.width() - 4, self.height() - 4, 10, 10)
        p.end()
