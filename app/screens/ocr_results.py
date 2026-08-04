"""3.6 OCR Result Screen — editable table with confidence bars, status chips, pagination."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QPushButton, QComboBox,
                                QLineEdit, QHeaderView, QAbstractItemView,
                                QStyledItemDelegate, QStyleOptionViewItem,
                                QApplication, QSizePolicy, QProgressBar)
from PySide6.QtGui import (QFont, QStandardItemModel, QStandardItem,
                            QColor, QPainter, QBrush)
from PySide6.QtCore import Qt, QSortFilterProxyModel, QModelIndex, QRect

from app import mock_data as md
from app.components.chips import StatusChip
from app.components.confidence_bar import ConfidenceBar


# ── Confidence cell delegate ──────────────────────────────────────────────────

class ConfidenceDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        val = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(val, float):
            super().paint(painter, option, index)
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if option.state & 0x0001:  # selected
            painter.fillRect(option.rect, QColor("#3E9BFF22"))

        # Background track
        bar_rect = QRect(option.rect.x() + 8, option.rect.y() + 18,
                         option.rect.width() - 16, 8)
        painter.setBrush(QColor("#3A3C42"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Filled portion
        fill_w = int(bar_rect.width() * val)
        if fill_w > 0:
            fill_c = "#4ADE80" if val >= 0.9 else "#FBBF24" if val >= 0.7 else "#F87171"
            painter.setBrush(QColor(fill_c))
            painter.drawRoundedRect(
                QRect(bar_rect.x(), bar_rect.y(), fill_w, bar_rect.height()), 4, 4
            )

        # Percentage text
        painter.setPen(QColor("#F2F3F5"))
        painter.setFont(QFont("Cascadia Code", 11))
        painter.drawText(option.rect, Qt.AlignmentFlag.AlignCenter,
                         f"{int(val*100)}%")


# ── Status chip delegate ──────────────────────────────────────────────────────

class StatusDelegate(QStyledItemDelegate):
    _STATUS_COLORS = {
        "Pending":  ("#A6A9B1", "#3A3C42"),
        "Approved": ("#4ADE80", "#1a3d26"),
        "Rejected": ("#F87171", "#3d1a1a"),
        "Flagged":  ("#FBBF24", "#3d2e0a"),
    }

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        status = index.data()
        if not status:
            super().paint(painter, option, index)
            return
        if option.state & 0x0001:
            painter.fillRect(option.rect, QColor("#3E9BFF22"))
        text_c, bg_c = self._STATUS_COLORS.get(status, ("#A6A9B1", "#3A3C42"))
        pill_w, pill_h = 80, 22
        x = option.rect.x() + (option.rect.width() - pill_w) // 2
        y = option.rect.y() + (option.rect.height() - pill_h) // 2
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(x, y, pill_w, pill_h, 4, 4)
        painter.setPen(QColor(text_c))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(QRect(x, y, pill_w, pill_h),
                         Qt.AlignmentFlag.AlignCenter, status.upper())


# ── OCR Results Page ──────────────────────────────────────────────────────────

class OcrResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._page = 0
        self._page_size = 10

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Toolbar ───────────────────────────────────────────────
        tb = QHBoxLayout()
        tb.setSpacing(12)

        search = QLineEdit()
        search.setPlaceholderText("  🔍  Search OCR text, drawing number…")
        search.setFixedHeight(36)
        search.setFixedWidth(320)
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
        search.textChanged.connect(self._proxy.setFilterFixedString)

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

    def _build_model(self) -> QStandardItemModel:
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(
            ["Comment ID", "OCR Text", "Confidence", "Status"]
        )
        for c in md.COMMENTS:
            id_item = QStandardItem(c.id)
            id_item.setFont(QFont("Cascadia Code", 12))
            text_item = QStandardItem(c.ocr_text)
            text_item.setEditable(True)

            conf_item = QStandardItem()
            conf_item.setData(c.confidence, Qt.ItemDataRole.UserRole)
            conf_item.setEditable(False)

            status_item = QStandardItem(c.status)
            status_item.setEditable(False)

            for item in [id_item, text_item, conf_item, status_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)
            model.appendRow([id_item, text_item, conf_item, status_item])
        return model
