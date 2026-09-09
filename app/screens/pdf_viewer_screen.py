"""
pdf_viewer_screen.py — PDF Viewer screen.

Provides:
    PdfViewerPage(QWidget)
        Renders real PDF pages using PyMuPDF backend via AppController,
        zoom / page controls via PdfToolbar, metadata panel, and thumbnail strip.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any, List
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                QGraphicsView, QGraphicsScene,
                                QListWidget, QListWidgetItem,
                                QSizePolicy)
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QPainter, QPixmap, QIcon

from app import mock_data as md
from app.components.pdf_toolbar    import PdfToolbar
from app.components.pdf_canvas     import make_page_pixmap, draw_bounding_boxes, draw_annotation_regions
from app.components.metadata_panel import DrawingMetadataPanel
from src.core.dtos.pdf_dtos import PDFDocumentDTO


class PdfViewerPage(QWidget):
    """
    PDF Viewer screen displaying real PDF drawing pages rendered via PyMuPDF backend.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._doc_dto: PDFDocumentDTO | None = None
        self._annotation_result = None  # NEW: Store annotation detection result
        self._show_annotations = False  # NEW: Toggle for annotation visualization
        self._zoom         = 1.0
        self._current_page = 1
        self._total_pages  = 1

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
        self._toolbar.show_annotations_toggled.connect(self._toggle_annotations)  # NEW
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
        viewer_row.addWidget(self._view, 4)

        # Metadata panel
        self._meta_panel = DrawingMetadataPanel(fixed_width=310)
        viewer_row.addWidget(self._meta_panel)

        root.addLayout(viewer_row, 1)

        # ── Thumbnail strip ───────────────────────────────────────
        self._thumb_strip = self._build_thumbnail_strip()
        root.addWidget(self._thumb_strip)

    def set_document(self, doc_dto: PDFDocumentDTO) -> None:
        """Sets the active PDFDocumentDTO and updates page count, metadata, & canvas."""
        self._doc_dto = doc_dto
        self._total_pages = doc_dto.total_pages
        self._current_page = 1
        
        # Try to get annotation results from workflow if available
        if self._controller and hasattr(self._controller, 'annotation_service'):
            try:
                print(f"Running annotation detection on {doc_dto.file_name}...")
                # Run annotation detection on the PDF
                # Use COLOR method WITHOUT template filtering for maximum coverage
                # COLOR method works best for scanned drawings with colored annotations/markup
                self._annotation_result = self._controller.annotation_service.detect_all_pages(
                    doc_dto.file_path,
                    method='hybrid',  # HYBRID finds native PDF markups, text blocks, and colored segmentation
                    filter_template_regions=False  # DON'T filter - we want ALL detected regions
                )
                print(f"✓ Detected {self._annotation_result.total_regions} annotation regions across {self._annotation_result.total_pages} pages")
                
                # Show breakdown by page
                for page_result in self._annotation_result.page_results:
                    print(f"  Page {page_result.page_number + 1}: {len(page_result.regions)} regions")
                
            except Exception as e:
                print(f"⚠ Could not run annotation detection: {e}")
                import traceback
                traceback.print_exc()
                self._annotation_result = None
        else:
            print("⚠ Annotation service not available")
            self._annotation_result = None
        
        # Update toolbar page count
        self._toolbar.set_total_pages(self._total_pages)
        self._toolbar.set_current_page(1)

        # Update right-side metadata panel with real drawing properties
        fields = [
            ("File Name", doc_dto.file_name),
            ("File Size", f"{round(doc_dto.file_size_bytes / (1024*1024), 2)} MB"),
            ("Total Pages", str(doc_dto.total_pages)),
            ("Format", "Scanned Image" if doc_dto.is_scanned else "Native Digital Vector"),
            ("Title", doc_dto.title or "Engineering Drawing"),
            ("Author", doc_dto.author or "CAD System"),
            ("File Digest", f"{doc_dto.file_hash_sha256[:12]}..."),
        ]
        
        # Add annotation count if available
        if self._annotation_result:
            fields.append(("Detected Regions", f"{self._annotation_result.total_regions} annotation boxes"))
            fields.append(("Detection Method", "Color Segmentation (HSV)"))
            fields.append(("Coverage", "All colored markup and annotations"))
        else:
            fields.append(("Detected Regions", "Click 🔍 to enable annotation detection"))
        
        self._meta_panel.update_fields(fields)

        # Sync thumbnails & render page 1
        self._sync_thumbnails()
        self._load_page(1)

    def reload_comments(self) -> None:
        """Reload page and thumbnails when comments are loaded/updated."""
        self._load_page(self._current_page)
        self._sync_thumbnails()

    # ── Page / zoom helpers ───────────────────────────────────────

    def _get_page_comments(self, page_num: int) -> List[Any]:
        """Fetch normalised comments for the specified 1-based page number."""
        all_comments: List[Any] = []
        if self._controller and self._controller.current_drawing_id:
            db_comments = self._controller.get_comments_for_drawing(
                self._controller.current_drawing_id
            )
            if db_comments:
                all_comments = db_comments
            else:
                all_comments = []
        else:
            all_comments = []

        page_comments = []
        for c in all_comments:
            c_page = c.get("page", 1) if isinstance(c, dict) else getattr(c, "page", 1)
            if c_page == page_num:
                page_comments.append(c)
        return page_comments

    def _load_page(self, page_num: int) -> None:
        self._scene.clear()
        
        # Get page comments (for comment bounding boxes - yellow/green)
        page_comments = self._get_page_comments(page_num)
        
        if self._doc_dto and self._controller:
            try:
                # Render real page using PyMuPDF backend adapter
                rendered_dto = self._controller.pdf_service.get_page_render(
                    self._doc_dto.file_path, page_num, dpi=150
                )
                pm = QPixmap()
                pm.loadFromData(rendered_dto.image_bytes)
                
                # ONLY draw comment bounding boxes if annotations toggle is OFF
                # (comments are different from detected annotation regions)
                if not self._show_annotations:
                    draw_bounding_boxes(pm, page_comments)
                
                # Draw REAL annotation regions if toggle is ON
                if self._show_annotations and self._annotation_result:
                    # Get page dimensions from doc_dto
                    page_idx = page_num - 1
                    if 0 <= page_idx < len(self._doc_dto.pages):
                        page_meta = self._doc_dto.pages[page_idx]
                        page_width_pt = page_meta.width_pt
                        page_height_pt = page_meta.height_pt
                        
                        # Get regions for this specific page
                        page_regions = []
                        for page_result in self._annotation_result.page_results:
                            # Match by page number (0-based in annotation_result)
                            if page_result.page_number == page_idx:
                                page_regions = page_result.regions
                                break
                        
                        if page_regions:
                            print(f"Drawing {len(page_regions)} annotation regions on page {page_num}")
                            draw_annotation_regions(pm, page_regions, page_width_pt, page_height_pt)
                        else:
                            print(f"No annotation regions found for page {page_num}")
                
            except Exception as e:
                print(f"Error loading page: {e}")
                pm = make_page_pixmap(comments=page_comments)
        else:
            pm = make_page_pixmap(comments=page_comments)

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
            self._zoom = vw / w * 0.95 if w > 0 else 1.0
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
        if hasattr(self, '_thumb_strip') and self._thumb_strip.count() >= self._current_page:
            self._thumb_strip.setCurrentRow(self._current_page - 1)

    def _sync_page(self) -> None:
        self._toolbar.set_current_page(self._current_page)
        if self._thumb_strip.count() >= self._current_page:
            self._thumb_strip.setCurrentRow(self._current_page - 1)
        self._load_page(self._current_page)

    def _toggle_annotations(self, enabled: bool) -> None:
        """Toggle annotation region visualization on/off."""
        self._show_annotations = enabled
        self._load_page(self._current_page)  # Redraw current page
        # Note: thumbnails not redrawn to avoid performance hit

    # ── Thumbnail strip ───────────────────────────────────────────

    def _build_thumbnail_strip(self) -> QListWidget:
        lst = QListWidget()
        lst.setFlow(QListWidget.Flow.LeftToRight)
        lst.setFixedHeight(110)
        lst.setIconSize(QSize(64, 80))
        lst.setViewMode(QListWidget.ViewMode.IconMode)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lst.setObjectName("ActivityList"); lst.setStyleSheet("/* migrated */" 
            "QListWidget { border-top: 1px solid #E2E8F0; border-radius: 0;"
            " background: #FFFFFF; padding: 4px; }"
            "QListWidget::item { border: 2px solid transparent;"
            " border-radius: 6px; margin: 4px; color: #475569; font-size: 11px; font-weight: 600; }"
            "QListWidget::item:hover { background: #F1F5F9; border-color: #E2E8F0; }"
            "QListWidget::item:selected { border-color: #2563EB; background: rgba(37, 99, 235, 0.08); color: #2563EB; }"
        )
        lst.currentRowChanged.connect(
            lambda r: self._goto_page(r + 1) if r >= 0 else None
        )
        self._populate_thumbs(lst)
        return lst

    def _populate_thumbs(self, lst: QListWidget) -> None:
        lst.clear()
        for i in range(self._total_pages):
            page_comments = self._get_page_comments(i + 1)
            if self._doc_dto and self._controller:
                try:
                    r_dto = self._controller.pdf_service.get_page_render(
                        self._doc_dto.file_path, i + 1, dpi=30
                    )
                    pm = QPixmap()
                    pm.loadFromData(r_dto.image_bytes)
                    draw_bounding_boxes(pm, page_comments)
                except Exception:
                    pm = make_page_pixmap(70, 88, comments=page_comments)
            else:
                pm = make_page_pixmap(70, 88, comments=page_comments)

            item = QListWidgetItem(f" Page {i + 1}")
            item.setIcon(QIcon(pm))
            lst.addItem(item)
        if lst.count() > 0:
            lst.setCurrentRow(0)

    def _sync_thumbnails(self) -> None:
        self._populate_thumbs(self._thumb_strip)
