"""3.4 PDF Viewer — simulated canvas, toolbar, metadata panel, thumbnail strip."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QGraphicsView, QGraphicsScene, QGraphicsRectItem,
                                QGraphicsTextItem, QGraphicsPixmapItem,
                                QToolButton, QLineEdit, QLabel, QListWidget,
                                QListWidgetItem, QSizePolicy, QAbstractItemView)
from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import (QFont, QColor, QPen, QBrush, QPixmap, QPainter,
                            QLinearGradient, QPainterPath)

from app import mock_data as md


def _toolbar_btn(text: str, tooltip: str = "") -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setFixedSize(36, 36)
    return btn


def _make_page_pixmap(width: int = 700, height: int = 900) -> QPixmap:
    """Simulate an engineering drawing page."""
    pm = QPixmap(width, height)
    pm.fill(QColor("#FFFFFF"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Title block bottom
    p.setPen(QPen(QColor("#CCCCCC"), 1))
    p.setBrush(QColor("#F5F6F8"))
    p.drawRect(0, height - 100, width, 100)

    # Drawing border
    p.setPen(QPen(QColor("#999999"), 2))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(20, 20, width - 40, height - 40)

    # Center annotation blocks (simulated drawing lines)
    p.setPen(QPen(QColor("#888888"), 1))
    for y_off in range(80, height - 120, 40):
        p.drawLine(40, y_off, width - 40, y_off)
    for x_off in range(80, width - 40, 60):
        p.drawLine(x_off, 40, x_off, height - 120)

    # Comment bounding boxes (colored)
    for i, c in enumerate(md.COMMENTS[:5]):
        x = int(c.bbox[0] * width)
        y = int(c.bbox[1] * height)
        w = int(c.bbox[2] * width)
        h_box = int(c.bbox[3] * height)
        color = {"Approved": QColor("#4ADE80"), "Pending": QColor("#FBBF24"),
                 "Flagged": QColor("#F87171"), "Rejected": QColor("#F87171")}.get(
                     c.status, QColor("#3E9BFF"))
        color.setAlphaF(0.25)
        p.setBrush(color)
        color2 = QColor(color)
        color2.setAlphaF(0.9)
        p.setPen(QPen(color2, 1.5))
        p.drawRect(x, y, w, h_box)

    # Title block text
    p.setPen(QPen(QColor("#333333"), 1))
    p.setFont(QFont("Cascadia Code", 8))
    p.drawText(30, height - 80, "Drawing No: UCC-E-101   Rev: A   Project: UCC Site-4 Expansion")
    p.drawText(30, height - 60, "Title: Piping & Instrumentation Diagram — Unit 4-A")
    p.drawText(30, height - 40, "Scale: 1:50   Sheet: 1 of 3   Date: 2026-07-28")
    p.end()
    return pm


class PdfViewerPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._zoom = 1.0
        self._current_page = 1
        self._total_pages = 3

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setFixedHeight(48)
        toolbar.setObjectName("Card")
        toolbar.setStyleSheet("#Card { border-radius:0; border-left:none; border-right:none; border-top:none; }")
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(16, 0, 16, 0)
        tb_lay.setSpacing(4)

        self._zoom_out = _toolbar_btn("−", "Zoom Out")
        self._zoom_out.clicked.connect(self._do_zoom_out)
        tb_lay.addWidget(self._zoom_out)

        self._zoom_lbl = QLabel("100%")
        self._zoom_lbl.setFixedWidth(52)
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zoom_lbl.setFont(QFont("Cascadia Code", 12))
        tb_lay.addWidget(self._zoom_lbl)

        self._zoom_in = _toolbar_btn("+", "Zoom In")
        self._zoom_in.clicked.connect(self._do_zoom_in)
        tb_lay.addWidget(self._zoom_in)

        tb_lay.addWidget(_sep())

        fit_btn = _toolbar_btn("⊡", "Fit Width")
        fit_btn.clicked.connect(self._fit_width)
        tb_lay.addWidget(fit_btn)

        rot_btn = _toolbar_btn("↻", "Rotate")
        rot_btn.clicked.connect(self._rotate)
        tb_lay.addWidget(rot_btn)

        tb_lay.addWidget(_sep())
        tb_lay.addStretch()

        prev_btn = _toolbar_btn("◀", "Previous Page")
        prev_btn.clicked.connect(self._prev_page)
        tb_lay.addWidget(prev_btn)

        self._page_field = QLineEdit("1")
        self._page_field.setFixedWidth(40)
        self._page_field.setFixedHeight(28)
        self._page_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_field.setFont(QFont("Cascadia Code", 12))
        tb_lay.addWidget(self._page_field)

        self._page_total = QLabel(f"of {self._total_pages}")
        self._page_total.setObjectName("SubCaption")
        tb_lay.addWidget(self._page_total)

        next_btn = _toolbar_btn("▶", "Next Page")
        next_btn.clicked.connect(self._next_page)
        tb_lay.addWidget(next_btn)

        root.addWidget(toolbar)

        # ── Viewer split ──────────────────────────────────────────
        viewer_row = QHBoxLayout()
        viewer_row.setSpacing(0)
        viewer_row.setContentsMargins(0, 0, 0, 0)

        # Canvas
        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHints(QPainter.RenderHint.Antialiasing |
                                   QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._pm_item = None
        self._load_page(1)
        viewer_row.addWidget(self._view, 3)

        # Metadata panel
        meta = self._build_meta_panel()
        viewer_row.addWidget(meta)

        root.addLayout(viewer_row, 1)

        # ── Thumbnail strip ───────────────────────────────────────
        self._thumb_strip = self._build_thumbnail_strip()
        root.addWidget(self._thumb_strip)

    # ── Page / zoom helpers ───────────────────────────────────────

    def _load_page(self, page_num: int):
        self._scene.clear()
        pm = _make_page_pixmap()
        self._pm_item = self._scene.addPixmap(pm)
        self._scene.setSceneRect(QRectF(pm.rect()))
        self._apply_zoom()

    def _apply_zoom(self):
        self._view.resetTransform()
        self._view.scale(self._zoom, self._zoom)
        self._zoom_lbl.setText(f"{int(self._zoom*100)}%")

    def _do_zoom_in(self):
        self._zoom = min(4.0, self._zoom + 0.2)
        self._apply_zoom()

    def _do_zoom_out(self):
        self._zoom = max(0.2, self._zoom - 0.2)
        self._apply_zoom()

    def _fit_width(self):
        if self._pm_item:
            w = self._pm_item.pixmap().width()
            vw = self._view.viewport().width()
            self._zoom = vw / w * 0.95
            self._apply_zoom()

    def _rotate(self):
        self._view.rotate(90)

    def _prev_page(self):
        self._current_page = max(1, self._current_page - 1)
        self._sync_page()

    def _next_page(self):
        self._current_page = min(self._total_pages, self._current_page + 1)
        self._sync_page()

    def _sync_page(self):
        self._page_field.setText(str(self._current_page))
        self._thumb_strip.setCurrentRow(self._current_page - 1)
        self._load_page(self._current_page)

    def _build_meta_panel(self) -> QFrame:
        f = QFrame()
        f.setObjectName("Card")
        f.setFixedWidth(280)
        f.setStyleSheet("#Card { border-radius:0; border-top:none; border-bottom:none; border-right:none; }")
        lay = QVBoxLayout(f)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        hdr = QLabel("Drawing Metadata")
        hdr.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.DemiBold))
        lay.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        fields = [
            ("Drawing Number", "UCC-E-101"),
            ("Drawing Title",  "P&ID Unit 4-A"),
            ("Revision",       "Rev A"),
            ("Project Name",   "UCC Site-4 Expansion"),
            ("Discipline",     "Process/Piping"),
            ("Sheet",          "1 of 3"),
            ("Scale",          "1:50"),
            ("Date",           "2026-07-28"),
        ]
        for key, val in fields:
            k = QLabel(key)
            k.setObjectName("FormLabel")
            lay.addWidget(k)
            v = QLabel(val)
            v.setFont(QFont("Cascadia Code", 12))
            v.setWordWrap(True)
            lay.addWidget(v)

        lay.addStretch()
        return f

    def _build_thumbnail_strip(self) -> QListWidget:
        lst = QListWidget()
        lst.setFlow(QListWidget.Flow.LeftToRight)
        lst.setFixedHeight(100)
        lst.setIconSize(QSize(64, 80))
        lst.setViewMode(QListWidget.ViewMode.IconMode)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        lst.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lst.setStyleSheet(
            "QListWidget { border-top: 1px solid #3A3C42; border-radius:0; background:#26272B; }"
            "QListWidget::item { border:2px solid transparent; border-radius:4px; margin:4px; }"
            "QListWidget::item:selected { border-color:#3E9BFF; }"
        )
        lst.currentRowChanged.connect(lambda r: self._page_field.setText(str(r+1)))

        for i in range(self._total_pages):
            pm = _make_page_pixmap(70, 88)
            item = QListWidgetItem(f"  {i+1}")
            item.setIcon(pm)  # type: ignore[arg-type]
            lst.addItem(item)
        lst.setCurrentRow(0)
        return lst


def _sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setStyleSheet("color: #3A3C42;")
    return f
