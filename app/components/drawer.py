"""
InspectorDrawer — slide-in panel from right (QPropertyAnimation on width).
"""
from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QFont
try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


class InspectorDrawer(QFrame):
    EXPANDED_W = 320
    COLLAPSED_W = 0

    def __init__(self, title: str = "Inspector", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMaximumWidth(self.COLLAPSED_W)
        self._open = False

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header row
        hdr = QHBoxLayout()
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.DemiBold))
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setObjectName("GhostBtn")
        close_btn.setFixedSize(28, 28)
        close_btn.clicked.connect(self.close_drawer)
        hdr.addWidget(close_btn)
        root.addLayout(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        # Content area — callers add widgets here
        self._content = QVBoxLayout()
        self._content.setSpacing(12)
        root.addLayout(self._content)
        root.addStretch()

        # Animation
        self._anim = QPropertyAnimation(self, b"maximumWidth")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content

    def set_title(self, title: str):
        self._title_lbl.setText(title)

    def open_drawer(self):
        if self._open:
            return
        self._open = True
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(self.EXPANDED_W)
        self._anim.start()

    def close_drawer(self):
        if not self._open:
            return
        self._open = False
        self._anim.setStartValue(self.maximumWidth())
        self._anim.setEndValue(0)
        self._anim.start()

    def toggle(self):
        if self._open:
            self.close_drawer()
        else:
            self.open_drawer()
