"""
classification_screen.py — Classification screen.

Provides:
    ClassificationPage(QWidget)
        Category summary cards, search / filter toolbar, sortable table
        with category + confidence delegates, and a slide-in inspector drawer.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QPushButton, QComboBox,
                                QLineEdit, QHeaderView, QAbstractItemView,
                                QSizePolicy)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex

from app import mock_data as md
from app.components.chips import CategoryBadge
from app.components.drawer import InspectorDrawer
from app.components.comment_table import ConfidenceDelegate, CategoryDelegate
from app.components.statistics_cards import CategorySummaryCard
from app.components.search_bar import SearchBar

_CATEGORY_ICONS = {
    "Dimensional":   ("📐", "#3E9BFF"),
    "Structural":    ("🏗",  "#A78BFA"),
    "Electrical":    ("⚡",  "#FBBF24"),
    "Material":      ("🧱",  "#2DD4BF"),
    "Documentation": ("📄",  "#A6A9B1"),
    "Other":         ("❓",  "#94A3B8"),
    "Mechanical":    ("⚙",   "#FB923C"),
}


class ClassificationPage(QWidget):
    """
    Classification — category summary cards, comment table with badges,
    and a slide-in inspector drawer.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Main content ──────────────────────────────────────────
        main   = QWidget()
        root   = QVBoxLayout(main)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # Category summary cards
        cat_row = QHBoxLayout()
        cat_row.setSpacing(12)
        for cat, count in md.CATEGORY_COUNTS.items():
            icon_text, color = _CATEGORY_ICONS.get(cat, ("●", "#A6A9B1"))
            card = CategorySummaryCard(icon_text, count, cat, color)
            cat_row.addWidget(card, 1)
        root.addLayout(cat_row)

        # Toolbar
        tb = QHBoxLayout()
        tb.setSpacing(12)

        search = SearchBar(
            placeholder="  🔍  Search comments, categories…",
            fixed_width=300,
        )
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
        search.search_changed.connect(self._proxy.setFilterFixedString)

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

    # ── Model / drawer helpers ────────────────────────────────────

    def _build_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(
            ["Comment", "Category", "Confidence", "Status"]
        )
        for c in md.COMMENTS:
            text_item = QStandardItem(c.ocr_text[:80])
            text_item.setData(c.id, Qt.ItemDataRole.UserRole)
            cat_item  = QStandardItem(c.category)
            conf_item = QStandardItem()
            conf_item.setData(c.confidence, Qt.ItemDataRole.UserRole)
            st_item   = QStandardItem(c.status)
            for item in [text_item, cat_item, conf_item, st_item]:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
            model.appendRow([text_item, cat_item, conf_item, st_item])
        return model

    def _open_drawer(self, index: QModelIndex) -> None:
        row = self._proxy.mapToSource(index).row()
        c   = md.COMMENTS[row]

        lay = self._drawer.content_layout
        while lay.count():
            child = lay.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._drawer.set_title(f"Inspector — {c.id}")

        def _row(key: str, val: str) -> None:
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
        full_text.setStyleSheet(
            "color:#F2F3F5; font-size:13px; padding:8px;"
            " background:#2D2F34; border-radius:6px;"
        )
        lay.addWidget(full_text)

        cat_lbl = QLabel("Category")
        cat_lbl.setObjectName("FormLabel")
        lay.addWidget(cat_lbl)
        lay.addWidget(CategoryBadge(c.category))

        cat_override = QComboBox()
        cat_override.addItems(md.CATEGORIES)
        cat_override.setCurrentText(c.category)
        cat_override.setFixedHeight(36)
        lay.addWidget(cat_override)

        conf_lbl = QLabel(f"Confidence: {int(c.confidence * 100)}%")
        conf_lbl.setObjectName("SubCaption")
        lay.addWidget(conf_lbl)

        self._drawer.open_drawer()
