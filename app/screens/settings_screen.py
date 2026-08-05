"""
settings_screen.py — Settings screen.

Provides:
    SettingsPage(QWidget)
        Three-tab settings panel: Appearance / Application / About.
        Uses a left-side tab list and a stacked content area on the right.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QFrame,
                                QLabel, QListWidget, QListWidgetItem,
                                QStackedWidget, QComboBox, QSlider,
                                QCheckBox, QLineEdit, QToolButton,
                                QPushButton, QFormLayout, QButtonGroup)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont

from app.components.dialogs import open_folder

_TABS = ["Appearance", "Application", "About"]


# ── Segmented control ─────────────────────────────────────────────────────────

class _SegmentedControl(QWidget):
    """Horizontal group of mutually-exclusive toggle buttons."""

    def __init__(self, options: list[str], parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        for i, opt in enumerate(options):
            btn = QPushButton(opt)
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            if i == 0:
                radius_style = "border-radius: 8px 0 0 8px;"
            elif i == len(options) - 1:
                radius_style = "border-radius: 0 8px 8px 0;"
            else:
                radius_style = "border-radius: 0;"
            btn.setStyleSheet(
                f"QPushButton {{ background:#26272B; color:#A6A9B1;"
                f" border:1px solid #3A3C42; {radius_style}"
                f" padding:0 16px; font-size:13px; }}"
                f"QPushButton:checked {{ background:#3E9BFF;"
                f" color:#fff; border-color:#3E9BFF; }}"
            )
            self._group.addButton(btn, i)
            lay.addWidget(btn)
        self._group.button(0).setChecked(True)

    @property
    def group(self) -> QButtonGroup:
        return self._group


# ── SettingsPage ──────────────────────────────────────────────────────────────

class SettingsPage(QWidget):
    """
    Settings — tabbed interface for Appearance, Application, and About.
    """

    def __init__(self, theme_manager=None, parent=None):
        super().__init__(parent)
        self._theme = theme_manager

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Tab list (left) ───────────────────────────────────────
        tab_list = QListWidget()
        tab_list.setObjectName("NavList")
        tab_list.setFixedWidth(220)
        tab_list.setStyleSheet(
            "#NavList { background: #26272B; border-right:1px solid #3A3C42; }"
            "#NavList::item { height:44px; padding-left:20px; border-radius:6px;"
            " margin:4px 8px; color:#A6A9B1; }"
            "#NavList::item:selected { background:#3E9BFF2A;"
            " color:#3E9BFF; font-weight:600; }"
        )

        icons = ["🎨", "⚙", "ℹ"]
        for tab, icon in zip(_TABS, icons):
            item = QListWidgetItem(f"  {icon}   {tab}")
            item.setSizeHint(QSize(220, 44))
            tab_list.addItem(item)
        tab_list.setCurrentRow(0)

        # ── Content stack (right) ─────────────────────────────────
        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_appearance())
        self._stack.addWidget(self._build_application())
        self._stack.addWidget(self._build_about())

        tab_list.currentRowChanged.connect(self._stack.setCurrentIndex)
        root.addWidget(tab_list)
        root.addWidget(self._stack, 1)

    # ── Tab pages ─────────────────────────────────────────────────

    def _build_appearance(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(28)
        lay.addWidget(self._section_title("Appearance"))

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # Theme selector
        theme_ctrl = _SegmentedControl(["Light", "Dark", "System"])
        if self._theme and self._theme.current == "dark":
            theme_ctrl.group.button(1).setChecked(True)

        def _on_theme(id_: int) -> None:
            if self._theme:
                self._theme.apply("light" if id_ == 0 else "dark")

        theme_ctrl.group.idClicked.connect(_on_theme)
        form.addRow(self._form_label("Theme:"), theme_ctrl)

        # Language
        lang = QComboBox()
        lang.addItems(["English (US)", "Hindi", "German", "French", "Spanish"])
        lang.setFixedHeight(36)
        form.addRow(self._form_label("Language:"), lang)

        # Font size slider
        font_slider = QSlider(Qt.Orientation.Horizontal)
        font_slider.setRange(0, 2)
        font_slider.setValue(1)
        font_slider.setTickInterval(1)
        font_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        font_slider.setFixedWidth(200)
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("Small"))
        font_row.addWidget(font_slider)
        font_row.addWidget(QLabel("Large"))
        font_row.addStretch()
        form.addRow(self._form_label("Font Size:"), font_row)

        lay.addLayout(form)
        lay.addStretch()
        return page

    def _build_application(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(28)
        lay.addWidget(self._section_title("Application"))

        form = QFormLayout()
        form.setSpacing(16)
        form.setLabelAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        # Default folder
        folder_row = QHBoxLayout()
        self._folder_edit = QLineEdit("D:\\UCC\\Projects")
        self._folder_edit.setReadOnly(True)
        self._folder_edit.setFixedHeight(36)
        folder_row.addWidget(self._folder_edit, 1)
        browse = QToolButton()
        browse.setText("Browse…")
        browse.setFixedHeight(36)
        browse.clicked.connect(self._browse_folder)
        folder_row.addWidget(browse)
        form.addRow(self._form_label("Default Folder:"), folder_row)

        # Auto save
        auto_save = QCheckBox("Auto-save review progress")
        auto_save.setChecked(True)
        form.addRow(self._form_label("Auto-Save:"), auto_save)

        # Notifications
        notif = QCheckBox("Enable desktop notifications")
        notif.setChecked(True)
        form.addRow(self._form_label("Notifications:"), notif)

        # Page size
        page_size = QComboBox()
        page_size.addItems(["10", "25", "50", "100"])
        page_size.setCurrentText("25")
        page_size.setFixedHeight(36)
        page_size.setFixedWidth(100)
        form.addRow(self._form_label("Rows per Page:"), page_size)

        lay.addLayout(form)
        lay.addStretch()
        return page

    def _build_about(self) -> QWidget:
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(40, 32, 40, 32)
        lay.setSpacing(16)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        logo = QLabel("🔍")
        logo.setFont(QFont("Segoe UI", 52))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)

        name = QLabel("UCC AI Drawing Review Comment Analyzer")
        name.setFont(QFont("Segoe UI Variable", 18, QFont.Weight.Bold))
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name)

        ver = QLabel("Version 1.0.0  ·  Build 2026.08.04")
        ver.setObjectName("SubCaption")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ver)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        for key, val in [
            ("Technology Stack", "PySide6 6.7+, Python 3.12, QtCharts"),
            ("OCR Engine",       "PaddleOCR / TrOCR (backend)"),
            ("Classifier",       "DistilBERT (backend)"),
            ("License",          "MIT License — © 2026 UCC Engineering"),
        ]:
            row_lbl = QLabel(f"<b>{key}:</b>  {val}")
            row_lbl.setFont(QFont("Segoe UI", 13))
            row_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(row_lbl)

        updates_btn = QPushButton("  🔄  Check for Updates")
        updates_btn.setObjectName("SecondaryBtn")
        updates_btn.setFixedHeight(36)
        updates_btn.setFixedWidth(220)
        lay.addSpacing(8)
        lay.addWidget(updates_btn, 0, Qt.AlignmentFlag.AlignCenter)

        lay.addStretch()
        return page

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _section_title(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI Variable", 22, QFont.Weight.Bold))
        return lbl

    @staticmethod
    def _form_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FormLabel")
        return lbl

    def _browse_folder(self) -> None:
        path = open_folder(self)
        if path:
            self._folder_edit.setText(path)
