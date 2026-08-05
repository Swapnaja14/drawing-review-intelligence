"""
ocr_results_screen.py — OCR Results screen.

Provides:
    OcrResultsPage(QWidget)
        Editable table of OCR-extracted comment text with confidence bars,
        status chips, a search bar, status filter, and pagination controls.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QPushButton, QComboBox,
                                QLineEdit, QHeaderView, QAbstractItemView,
                                QSizePolicy)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, QSortFilterProxyModel

from app import mock_data as md
from app.components.comment_table import ConfidenceDelegate, StatusDelegate
from app.components.search_bar import SearchBar


class OcrResultsPage(QWidget):
    """
    OCR Results — editable table with confidence bars, status chips,
    search, filter, and pagination.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._page      = 0
        self._page_size = 10

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(12)

        search = SearchBar(
            placeholder="  🔍  Search OCR text, drawing number…",
            fixed_width=320,
        )
        tb.addWidget(search)
        tb.addStretch()

        filt = QComboBox()
        filt.addItems(["All Status", "Pending", "Approved", "Rejected", "Flagged"])
        filt.setFixedHeight(36)
        filt.setFixedWidth(160)
        tb.addWidget(filt)

        export_btn = QPushButton("  ↑  Export")
        export_btn.setObjectName("SecondaryBtn")
        export_btn.setFixedHeight(36)
        tb.addWidget(export_btn)

        root.addLayout(tb)

        # ── Table ─────────────────────────────────────────────────
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
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setItemDelegateForColumn(2, ConfidenceDelegate(self._table))
        self._table.setItemDelegateForColumn(3, StatusDelegate(self._table))

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(2, 130)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(3, 120)

        tc_lay.addWidget(self._table)
        root.addWidget(table_card, 1)

        # ── Pagination ────────────────────────────────────────────
        pag = QHBoxLayout()
        pag.setSpacing(8)

        rpp_lbl = QLabel("Rows per page:")
        rpp_lbl.setObjectName("SubCaption")
        pag.addWidget(rpp_lbl)

        rpp = QComboBox()
        rpp.addItems(["10", "25", "50"])
        rpp.setFixedHeight(32)
        rpp.setFixedWidth(70)
        pag.addWidget(rpp)

        pag.addStretch()

        self._pg_lbl = QLabel(f"1–10 of {len(md.COMMENTS)}")
        self._pg_lbl.setObjectName("SubCaption")
        pag.addWidget(self._pg_lbl)

        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("SecondaryBtn")
        prev_btn.setFixedSize(32, 32)
        pag.addWidget(prev_btn)

        next_btn = QPushButton("›")
        next_btn.setObjectName("SecondaryBtn")
        next_btn.setFixedSize(32, 32)
        pag.addWidget(next_btn)

        root.addLayout(pag)

    # ── Model builder ─────────────────────────────────────────────

    def _build_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(
            ["Comment ID", "OCR Text", "Confidence", "Status"]
        )
        for c in md.COMMENTS:
            id_item   = QStandardItem(c.id)
            id_item.setFont(QFont("Cascadia Code", 12))
            text_item = QStandardItem(c.ocr_text)
            text_item.setEditable(True)

            conf_item = QStandardItem()
            conf_item.setData(c.confidence, Qt.ItemDataRole.UserRole)
            conf_item.setEditable(False)

            status_item = QStandardItem(c.status)
            status_item.setEditable(False)

            for item in [id_item, text_item, conf_item, status_item]:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
            model.appendRow([id_item, text_item, conf_item, status_item])
        return model
