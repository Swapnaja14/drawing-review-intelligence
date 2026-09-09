"""
TopBar — 72px enterprise header with page title / branding, responsive global search,
notifications, theme toggle, and user profile avatar menu.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLineEdit, QToolButton,
                                QPushButton, QLabel, QMenu, QFrame, QSizePolicy)
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
        self.setFixedHeight(72)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(14)

        # ── Breadcrumb / page title ──────────────────────────────
        self._breadcrumb = QLabel("Dashboard")
        self._breadcrumb.setFont(QFont("Inter", 18, QFont.Weight.Bold))
        self._breadcrumb.setStyleSheet("color: #F3F4F6;")
        lay.addWidget(self._breadcrumb)

        lay.addStretch(1)

        # ── Global search field (Responsive) ─────────────────────
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search projects, drawings, comments…")
        self._search.setMinimumWidth(180)
        self._search.setMaximumWidth(340)
        self._search.setFixedHeight(40)
        self._search.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._search.setStyleSheet(
            "QLineEdit { border-radius: 10px; padding: 6px 14px; font-size: 13px; }"
        )
        self._search.textChanged.connect(self.search_changed)
        lay.addWidget(self._search)

        # ── Notification button ──────────────────────────────────
        notif = QToolButton()
        notif.setFixedSize(38, 38)
        notif.setToolTip("Notifications (3 Unread)")
        if _HAS_QTA:
            try:
                notif.setIcon(qta.icon("fa5s.bell", color="#9CA3AF"))
                notif.setIconSize(QSize(18, 18))
            except Exception:
                notif.setText("🔔")
        else:
            notif.setText("🔔")
        notif.clicked.connect(self.notification_clicked)
        lay.addWidget(notif)

        # ── Theme toggle ─────────────────────────────────────────
        self._theme_btn = QPushButton("🌙  Dark")
        self._theme_btn.setObjectName("SecondaryBtn")
        self._theme_btn.setFixedHeight(38)
        self._theme_btn.setCheckable(True)
        self._theme_btn.clicked.connect(self._on_theme_click)
        lay.addWidget(self._theme_btn)

        # ── User profile button ──────────────────────────────────
        avatar_btn = QToolButton()
        avatar_btn.setFixedHeight(38)
        avatar_btn.setText("  AM  Alex M. ▾  ")
        avatar_btn.setFont(QFont("Inter", 12, QFont.Weight.Medium))
        avatar_btn.setStyleSheet(
            "QToolButton { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;"
            "color: #0F172A; padding: 4px 12px; }"
            "QToolButton:hover { background: #F1F5F9; border-color: #2563EB; }"
        )

        menu = QMenu(avatar_btn)
        menu.addAction(QAction("Engineering Profile", self))
        menu.addAction(QAction("Project Settings", self))
        menu.addSeparator()
        menu.addAction(QAction("Sign Out", self))
        avatar_btn.setMenu(menu)
        avatar_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        lay.addWidget(avatar_btn)

    def set_breadcrumb(self, text: str):
        self._breadcrumb.setText(text)

    def _on_theme_click(self, checked: bool):
        self._theme_btn.setText("☀  Light" if checked else "🌙  Dark")
        self.theme_toggled.emit()
