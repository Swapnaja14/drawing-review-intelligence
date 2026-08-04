"""3.7 Classification Screen — summary cards, toolbar, table with category badges, inspector drawer."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QPushButton, QComboBox,
                                QLineEdit, QHeaderView, QAbstractItemView,
                                QStyledItemDelegate, QStyleOptionViewItem,
                                QSizePolicy)
from PySide6.QtGui import (QFont, QStandardItemModel, QStandardItem,
                            QColor, QPainter)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QRect

from app import mock_data as md
from app.components.chips import CategoryBadge, StatusChip
from app.components.drawer import InspectorDrawer
from app.screens.ocr_results import ConfidenceDelegate

_CATEGORY_ICONS = {
    "Dimensional": ("📐", "#3E9BFF"),
    "Structural":  ("🏗", "#A78BFA"),
    "Electrical":  ("⚡", "#FBBF24"),
    "Material":    ("🧱", "#2DD4BF"),
    "Documentation":("📄", "#A6A9B1"),
    "Other":       ("❓", "#94A3B8"),
    "Mechanical":  ("⚙", "#FB923C"),
}

_CAT_BG = {
    "Dimensional":   ("#3E9BFF", "#0d2540"),
    "Structural":    ("#A78BFA", "#2a1a4d"),
    "Electrical":    ("#FBBF24", "#3d2e0a"),
    "Material":      ("#2DD4BF", "#0a2d2a"),
    "Documentation": ("#A6A9B1", "#2d2f34"),
    "Other":         ("#94A3B8", "#252b35"),
    "Mechanical":    ("#FB923C", "#3d1f0a"),
}


class CategoryDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        cat = index.data()
        if not cat:
            super().paint(painter, option, index)
            return
        if option.state & 0x0001:
            painter.fillRect(option.rect, QColor("#3E9BFF22"))
        text_c, bg_c = _CAT_BG.get(cat, ("#A6A9B1", "#2d2f34"))
        pill_w = min(120, option.rect.width() - 16)
        pill_h = 22
        x = option.rect.x() + 8
        y = option.rect.y() + (option.rect.height() - pill_h) // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(x, y, pill_w, pill_h, 4, 4)
        painter.setPen(QColor(text_c))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(QRect(x, y, pill_w, pill_h),
                         Qt.AlignmentFlag.AlignCenter, cat.upper())


class ClassificationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Main content ──────────────────────────────────────────
        main = QWidget()
        root = QVBoxLayout(main)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Summary cards
        cat_row = QHBoxLayout()
        cat_row.setSpacing(12)
        for cat, count in md.CATEGORY_COUNTS.items():
            icon_text, color = _CATEGORY_ICONS.get(cat, ("●", "#A6A9B1"))
            card = self._make_summary_card(icon_text, count, cat, color)
            cat_row.addWidget(card, 1)
        root.addLayout(cat_row)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(12)
        search = QLineEdit()
        search.setPlaceholderText("  🔍  Search comments, categories…")
        search.setFixedHeight(36)
        search.setFixedWidth(300)
        tb.addWidget(search)
        tb.addStretch()

        cat_filt = QComboBox()
        cat_filt.addItems(["All Categories"] + list(md.CATEGORY_COUNTS.keys()))
        cat_filt.setFixedHeight(36)
        tb.addWidget(cat_filt)

        st_filt = QComboBox()
        st_filt.addItems(["All Status", "Pending", "Approved", "Rejected", "Flagged"])
        st_filt.setFixedHeight(36)
        tb.addWidget(st_filt)
        root.addLayout(tb)

        # Table
        table_card = QFrame()
        table_card.setObjectName("Card")
        tc_lay = QVBoxLayout(table_card)
        tc_lay.setContentsMargins(0, 0, 0, 0)

        self._model = self._build_model()
        self._proxy = QSortFilterProxyModel()
        self._proxy.setSourceModel(self._model)
        self._proxy.setFilterKeyColumn(-1)
        self._proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        search.textChanged.connect(self._proxy.setFilterFixedString)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setItemDelegateForColumn(1, CategoryDelegate(self._table))
        self._table.setItemDelegateForColumn(2, ConfidenceDelegate(self._table))
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(1, 150)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 130)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 120)
        hdr.setStretchLastSection(False)
        self._table.clicked.connect(self._open_drawer)
        tc_lay.addWidget(self._table)
        root.addWidget(table_card, 1)

        outer.addWidget(main, 1)

        # ── Inspector drawer ──────────────────────────────────────
        self._drawer = InspectorDrawer("Comment Inspector")
        outer.addWidget(self._drawer)

    def _make_summary_card(self, icon: str, count: int, label: str, color: str) -> QFrame:
        f = QFrame()
        f.setObjectName("Card")
        f.setMinimumWidth(100)
        lay = QVBoxLayout(f)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 20))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        cnt_lbl = QLabel(str(count))
        cnt_lbl.setFont(QFont("Segoe UI Variable", 20, QFont.Weight.Bold))
        cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cnt_lbl.setStyleSheet(f"color:{color};")
        lay.addWidget(cnt_lbl)

        lab = QLabel(label)
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lab.setObjectName("SubCaption")
        lab.setWordWrap(True)
        lay.addWidget(lab)
        return f

    def _build_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(
            ["Comment", "Category", "Confidence", "Status"]
        )
        for c in md.COMMENTS:
            text_item = QStandardItem(c.ocr_text[:80])
            cat_item  = QStandardItem(c.category)
            conf_item = QStandardItem()
            conf_item.setData(c.confidence, Qt.ItemDataRole.UserRole)
            st_item   = QStandardItem(c.status)
            # store full comment id for drawer
            text_item.setData(c.id, Qt.ItemDataRole.UserRole)
            for item in [text_item, cat_item, conf_item, st_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            model.appendRow([text_item, cat_item, conf_item, st_item])
        return model

    def _open_drawer(self, index: QModelIndex):
        row = self._proxy.mapToSource(index).row()
        c = md.COMMENTS[row]

        # Clear and rebuild drawer content
        lay = self._drawer.content_layout
        while lay.count():
            child = lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._drawer.set_title(f"Inspector — {c.id}")

        def _row(key: str, val: str):
            k = QLabel(key)
            k.setObjectName("FormLabel")
            lay.addWidget(k)
            v = QLabel(val)
            v.setFont(QFont("Cascadia Code", 12))
            v.setWordWrap(True)
            lay.addWidget(v)

        _row("Drawing", c.drawing_no)
        _row("Project", c.project_id)

        full_text = QLabel(c.ocr_text)
        full_text.setWordWrap(True)
        full_text.setStyleSheet("color:#F2F3F5; font-size:13px; padding:8px; "
                                "background:#2D2F34; border-radius:6px;")
        lay.addWidget(full_text)

        cat_lbl = QLabel("Category")
        cat_lbl.setObjectName("FormLabel")
        lay.addWidget(cat_lbl)
        badge = CategoryBadge(c.category)
        lay.addWidget(badge)

        cat_override = QComboBox()
        cat_override.addItems(md.CATEGORIES)
        cat_override.setCurrentText(c.category)
        cat_override.setFixedHeight(36)
        lay.addWidget(cat_override)

        conf_lbl = QLabel(f"Confidence: {int(c.confidence*100)}%")
        conf_lbl.setObjectName("SubCaption")
        lay.addWidget(conf_lbl)

        self._drawer.open_drawer()
