"""
MainWindow — application shell: sidebar + topbar + stacked pages.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                                QStackedWidget, QStatusBar, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.components.sidebar import SidebarNav
from app.components.topbar import TopBar
from app.screens.dashboard       import DashboardPage
from app.screens.upload          import UploadPage
from app.screens.pdf_viewer      import PdfViewerPage
from app.screens.comment_highlight import CommentHighlightPage
from app.screens.ocr_results     import OcrResultsPage
from app.screens.classification  import ClassificationPage
from app.screens.human_review    import HumanReviewPage
from app.screens.analytics       import AnalyticsPage
from app.screens.export          import ExportPage
from app.screens.settings        import SettingsPage

_PAGE_TITLES = [
    "Dashboard",
    "Upload Drawing",
    "PDF Viewer",
    "Comment Highlight Viewer",
    "OCR Results",
    "Classification",
    "Human Review",
    "Dashboard Analytics",
    "Export",
    "Settings",
]


class MainWindow(QMainWindow):
    def __init__(self, theme_manager=None):
        super().__init__()
        self._theme = theme_manager
        self.setWindowTitle("UCC AI Drawing Review Comment Analyzer")
        self.showMaximized()

        # ── Central widget ────────────────────────────────────────
        central = QWidget()
        self.setCentralWidget(central)

        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        # Sidebar
        self._sidebar = SidebarNav()
        self._sidebar.nav_changed.connect(self._navigate)
        h_layout.addWidget(self._sidebar)

        # Content area
        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        v_layout = QVBoxLayout(content_area)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(0)

        # Top bar
        self._topbar = TopBar()
        self._topbar.theme_toggled.connect(self._on_theme_toggle)
        v_layout.addWidget(self._topbar)

        # Stacked pages
        self._stack = QStackedWidget()
        self._pages = [
            DashboardPage(),
            UploadPage(),
            PdfViewerPage(),
            CommentHighlightPage(),
            OcrResultsPage(),
            ClassificationPage(),
            HumanReviewPage(),
            AnalyticsPage(),
            ExportPage(),
            SettingsPage(theme_manager=self._theme),
        ]
        for page in self._pages:
            self._stack.addWidget(page)
        v_layout.addWidget(self._stack, 1)

        h_layout.addWidget(content_area, 1)

        # ── Status bar ────────────────────────────────────────────
        status = QStatusBar()
        self.setStatusBar(status)
        status.addWidget(QLabel("  Ready"))
        status.addPermanentWidget(
            QLabel("UCC Analyzer v1.0.0  ·  Python 3.12  ·  PySide6  ")
        )

    def _navigate(self, idx: int):
        self._stack.setCurrentIndex(idx)
        self._topbar.set_breadcrumb(_PAGE_TITLES[idx])
        # Give keyboard focus to pages that need it (e.g. Human Review)
        self._pages[idx].setFocus()

    def _on_theme_toggle(self):
        if self._theme:
            self._theme.toggle()
