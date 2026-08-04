"""
TopBar — search field, notification button, theme toggle, user avatar.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QToolButton,
                                QPushButton, QLabel, QMenu, QFrame)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QIcon, QAction
try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


class TopBar(QWidget):
    search_changed = Signal(str)
    theme_toggled  = Signal()
    notification_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBar")
        self.setFixedHeight(56)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)

        # ── Breadcrumb / page title ──────────────────────────────
        self._breadcrumb = QLabel("Dashboard")
        self._breadcrumb.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.DemiBold))
        self._breadcrumb.setStyleSheet("color: #F2F3F5;")
        lay.addWidget(self._breadcrumb)
        lay.addStretch()

        # ── Search field ─────────────────────────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("  🔍  Search projects, drawings, comments…")
        self._search.setFixedWidth(320)
        self._search.setFixedHeight(36)
        self._search.textChanged.connect(self.search_changed)
        lay.addWidget(self._search)

        # ── Notification button ──────────────────────────────────
        notif = QToolButton()
        notif.setFixedSize(36, 36)
        notif.setToolTip("Notifications")
        if _HAS_QTA:
            try:
                notif.setIcon(qta.icon("fa5s.bell", color="#A6A9B1"))
                notif.setIconSize(QSize(18, 18))
            except Exception:
                notif.setText("🔔")
        else:
            notif.setText("🔔")
        notif.clicked.connect(self.notification_clicked)
        lay.addWidget(notif)

        # ── Theme toggle ─────────────────────────────────────────
        self._theme_btn = QPushButton("☀  Light")
        self._theme_btn.setObjectName("SecondaryBtn")
        self._theme_btn.setFixedHeight(32)
        self._theme_btn.setCheckable(True)
        self._theme_btn.clicked.connect(self._on_theme_click)
        lay.addWidget(self._theme_btn)

        # ── User avatar ──────────────────────────────────────────
        avatar = QToolButton()
        avatar.setFixedSize(36, 36)
        avatar.setStyleSheet(
            "QToolButton { background:#3E9BFF; border-radius:18px;"
            "color:#fff; font-weight:700; font-size:13px; }"
        )
        avatar.setText("AM")
        menu = QMenu(avatar)
        menu.addAction(QAction("Profile", self))
        menu.addAction(QAction("Sign Out", self))
        avatar.setMenu(menu)
        avatar.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        lay.addWidget(avatar)

    def set_breadcrumb(self, text: str):
        self._breadcrumb.setText(text)

    def _on_theme_click(self, checked: bool):
        self._theme_btn.setText("🌙  Dark" if checked else "☀  Light")
        self.theme_toggled.emit()
