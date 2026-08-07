"""
Components package — reusable PySide6 widget library.

All widgets follow the application theme (QSS object-names) and are
designed to be composed into any screen without modification.

Public surface (importable via ``from app.components import …``):
    Navigation   : SidebarNav, TopBar
    Toolbar      : make_toolbar_btn, ToolbarSeparator, PdfToolbar
    Upload       : DropZone
    PDF / Canvas : make_page_pixmap, BBoxItem, DrawingMetadataPanel
    Tables       : ConfidenceDelegate, StatusDelegate, CategoryDelegate
    KPI / Stats  : KpiCard, CategorySummaryCard
    Chips        : StatusChip, CategoryBadge
    Charts       : build_pareto_chart, build_monthly_chart,
                   build_category_pie, no_chart_label
    Drawer       : InspectorDrawer
    Overlays     : ToastNotification, EmptyState
    Data display : ConfidenceBar
    Input        : SearchBar, FilterComboBar
    Feedback     : LoadingSpinner, AppStatusBar
    Dialogs      : show_confirm, show_error, show_info,
                   open_pdf_file, open_folder
"""

# Navigation
from app.components.sidebar         import SidebarNav
from app.components.topbar          import TopBar

# Toolbar utilities
from app.components.toolbar         import make_toolbar_btn, ToolbarSeparator
from app.components.pdf_toolbar     import PdfToolbar

# Upload
from app.components.upload_widget   import DropZone

# PDF / Canvas
from app.components.pdf_canvas      import make_page_pixmap, BBoxItem
from app.components.metadata_panel  import DrawingMetadataPanel

# Table delegates
from app.components.comment_table   import (ConfidenceDelegate,
                                             StatusDelegate,
                                             CategoryDelegate)

# KPI / Statistics cards
from app.components.kpi_card        import KpiCard
from app.components.statistics_cards import CategorySummaryCard

# Status / category chips
from app.components.chips           import StatusChip, CategoryBadge

# Charts
from app.components.charts          import (build_pareto_chart,
                                             build_monthly_chart,
                                             build_category_pie,
                                             no_chart_label)

# Slide-in drawer
from app.components.drawer          import InspectorDrawer

# Overlay widgets
from app.components.overlays        import ToastNotification, EmptyState

# Data-display widgets
from app.components.confidence_bar  import ConfidenceBar

# Input widgets
from app.components.search_bar      import SearchBar
from app.components.filter_panel    import FilterComboBar

# Feedback widgets
from app.components.loading_widget  import LoadingSpinner
from app.components.status_bar      import AppStatusBar

# Dialog helpers
from app.components.dialogs         import (show_confirm, show_error,
                                             show_info, open_pdf_file,
                                             open_folder)

__all__ = [
    # Navigation
    "SidebarNav", "TopBar",
    # Toolbar
    "make_toolbar_btn", "ToolbarSeparator", "PdfToolbar",
    # Upload
    "DropZone",
    # PDF / Canvas
    "make_page_pixmap", "BBoxItem", "DrawingMetadataPanel",
    # Tables
    "ConfidenceDelegate", "StatusDelegate", "CategoryDelegate",
    # KPI / Stats
    "KpiCard", "CategorySummaryCard",
    # Chips
    "StatusChip", "CategoryBadge",
    # Charts
    "build_pareto_chart", "build_monthly_chart",
    "build_category_pie", "no_chart_label",
    # Drawer
    "InspectorDrawer",
    # Overlays
    "ToastNotification", "EmptyState",
    # Data display
    "ConfidenceBar",
    # Input
    "SearchBar", "FilterComboBar",
    # Feedback
    "LoadingSpinner", "AppStatusBar",
    # Dialogs
    "show_confirm", "show_error", "show_info", "open_pdf_file", "open_folder",
]
