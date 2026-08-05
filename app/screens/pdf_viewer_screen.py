"""
pdf_viewer_screen.py — PDF Viewer screen.

Provides:
    PdfViewerPage(QWidget)
        Simulated canvas, zoom / page controls via PdfToolbar, drawing
        metadata panel, and thumbnail strip.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QGraphicsView, QGraphicsScene,
                                QListWidget, QListWidgetItem,
                                QSizePolicy, QAbstractItemView)
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter

from app.components.pdf_toolbar    import PdfToolbar
from app.components.pdf_canvas     import make_page_pixmap
from app.components.metadata_panel import DrawingMetadataPanel


class PdfViewerPage(QWidget):
    """
    PDF Viewer — simulated canvas with toolbar, metadata panel,
    and thumbnail strip.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom         = 1.0
        self._current_page = 1
        self._total_pages  = 3

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────
        self._toolbar = PdfToolbar(total_pages=self._total_pages)
        self._toolbar.zoom_in_requested.connect(self._do_zoom_in)
        self._toolbar.zoom_out_requested.connect(self._do_zoom_out)
        self._toolbar.fit_width_requested.connect(self._fit_width)
        self._toolbar.rotate_requested.connect(self._rotate)
        self._toolbar.prev_page_requested.connect(self._prev_page)
        self._toolbar.next_page_requested.connect(self._next_page)
        self._toolbar.page_changed.connect(self._goto_page)
        root.addWidget(self._toolbar)

        # ── Viewer split ──────────────────────────────────────────
        viewer_row = QHBoxLayout()
        viewer_row.setSpacing(0)
        viewer_row.setContentsMargins(0, 0, 0, 0)

        # Canvas
        self._scene = QGraphicsScene()
        self._view  = QGraphicsView(self._scene)
        self._view.setRenderHints(
            QPainter.RenderHint.Antialiasing |
            QPainter.RenderHint.SmoothPixmapTransform
        )
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._pm_item = None
        self._load_page(1)
        viewer_row.addWidget(self._view, 3)

        # Metadata panel
        self._meta_panel = DrawingMetadataPanel()
        viewer_row.addWidget(self._meta_panel)

        root.addLayout(viewer_row, 1)

        # ── Thumbnail strip ───────────────────────────────────────
        self._thumb_strip = self._build_thumbnail_strip()
        root.addWidget(self._thumb_strip)

    # ── Page / zoom helpers ───────────────────────────────────────

    def _load_page(self, page_num: int) -> None:
        self._scene.clear()
        pm = make_page_pixmap()
        self._pm_item = self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self._apply_zoom()

    def _apply_zoom(self) -> None:
        self._view.resetTransform()
        self._view.scale(self._zoom, self._zoom)
        self._toolbar.set_zoom_label(int(self._zoom * 100))

    def _do_zoom_in(self) -> None:
        self._zoom = min(4.0, self._zoom + 0.2)
        self._apply_zoom()

    def _do_zoom_out(self) -> None:
        self._zoom = max(0.2, self._zoom - 0.2)
        self._apply_zoom()

    def _fit_width(self) -> None:
        if self._pm_item:
            w  = self._pm_item.pixmap().width()
            vw = self._view.viewport().width()
            self._zoom = vw / w * 0.95
            self._apply_zoom()

    def _rotate(self) -> None:
        self._view.rotate(90)

    def _prev_page(self) -> None:
        self._current_page = max(1, self._current_page - 1)
        self._sync_page()

    def _next_page(self) -> None:
        self._current_page = min(self._total_pages, self._current_page + 1)
        self._sync_page()

    def _goto_page(self, page: int) -> None:
        self._current_page = page
        self._load_page(self._current_page)
        self._thumb_strip.setCurrentRow(self._current_page - 1)

    def _sync_page(self) -> None:
        self._toolbar.set_current_page(self._current_page)
        self._thumb_strip.setCurrentRow(self._current_page - 1)
        self._load_page(self._current_page)

    # ── Thumbnail strip builder ───────────────────────────────────

    def _build_thumbnail_strip(self) -> QListWidget:
        lst = QListWidget()
        lst.setFlow(QListWidget.Flow.LeftToRight)
        lst.setFixedHeight(100)
        lst.setIconSize(QSize(64, 80))
        lst.setViewMode(QListWidget.ViewMode.IconMode)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lst.setStyleSheet(
            "QListWidget { border-top: 1px solid #3A3C42; border-radius:0;"
            " background:#26272B; }"
            "QListWidget::item { border:2px solid transparent;"
            " border-radius:4px; margin:4px; }"
            "QListWidget::item:selected { border-color:#3E9BFF; }"
        )
        lst.currentRowChanged.connect(
            lambda r: self._toolbar.set_current_page(r + 1)
        )

        for i in range(self._total_pages):
            pm   = make_page_pixmap(70, 88)
            item = QListWidgetItem(f"  {i + 1}")
            item.setIcon(pm)   # type: ignore[arg-type]
            lst.addItem(item)
        lst.setCurrentRow(0)
        return lst
