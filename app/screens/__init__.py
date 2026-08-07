"""
Screens package — full-page QWidget views.

Each screen is a self-contained QWidget subclass registered in the main
window's QStackedWidget.  Navigation is driven by SidebarNav via the
``nav_changed`` Signal.

Sidebar index → Screen mapping:
    0  DashboardPage
    1  UploadPage
    2  PdfViewerPage
    3  CommentHighlightPage
    4  OcrResultsPage
    5  ClassificationPage
    6  HumanReviewPage
    7  AnalyticsPage
    8  ExportPage
    9  SettingsPage
"""

from app.screens.splash_screen         import SplashScreen
from app.screens.home_screen           import HomeScreen
from app.screens.dashboard_screen      import DashboardPage
from app.screens.upload_screen         import UploadPage
from app.screens.pdf_viewer_screen     import PdfViewerPage
from app.screens.comment_viewer_screen import CommentHighlightPage
from app.screens.ocr_results_screen    import OcrResultsPage
from app.screens.classification_screen import ClassificationPage
from app.screens.review_screen         import HumanReviewPage
from app.screens.analytics_screen      import AnalyticsPage
from app.screens.export_screen         import ExportPage
from app.screens.settings_screen       import SettingsPage

__all__ = [
    "SplashScreen",
    "HomeScreen",
    "DashboardPage",
    "UploadPage",
    "PdfViewerPage",
    "CommentHighlightPage",
    "OcrResultsPage",
    "ClassificationPage",
    "HumanReviewPage",
    "AnalyticsPage",
    "ExportPage",
    "SettingsPage",
]
