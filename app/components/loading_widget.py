"""
loading_widget.py — Animated loading / progress spinner.

Provides:
    LoadingSpinner(QWidget)
        Centred indeterminate progress bar with an optional status message.
        Can be used as an overlay or an inline placeholder while data loads.
"""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class LoadingSpinner(QWidget):
    """
    Centred loading indicator with an optional message label.

    Uses an indeterminate QProgressBar (range 0, 0) with the application's
    accent gradient, and a SubCaption label below it.

    Parameters
    ----------
    message:
        Status text displayed under the spinner (default ``"Loading…"``).
    """

    def __init__(self, message: str = "Loading…", parent=None):
        super().__init__(parent)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(16)

        # Indeterminate spinner bar
        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedHeight(4)
        bar.setFixedWidth(240)
        bar.setStyleSheet(
            "QProgressBar { background:#3A3C42; border-radius:2px; }"
            "QProgressBar::chunk {"
            "  background: qlineargradient("
            "    x1:0,y1:0,x2:1,y2:0,"
            "    stop:0 #3E9BFF, stop:1 #8B9CFF"
            "  );"
            "  border-radius:2px;"
            "}"
        )
        lay.addWidget(bar, 0, Qt.AlignmentFlag.AlignCenter)

        # Status message
        self._msg_lbl = QLabel(message)
        self._msg_lbl.setFont(QFont("Segoe UI Variable", 13))
        self._msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg_lbl.setObjectName("SubCaption")
        lay.addWidget(self._msg_lbl)

    def set_message(self, text: str) -> None:
        """Update the message shown below the spinner."""
        self._msg_lbl.setText(text)
