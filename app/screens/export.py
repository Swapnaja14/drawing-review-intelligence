"""3.10 Export Screen — format selector cards, scope options, progress, history table."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QRadioButton, QButtonGroup,
                                QProgressBar, QTableView, QHeaderView,
                                QAbstractItemView, QSizePolicy)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, QTimer

from app import mock_data as md


_FORMATS = [
    ("📊", "Excel", ".xlsx", "Full data with charts and formatting", "#4ADE80"),
    ("📄", "PDF",   ".pdf",  "Human-readable formatted report",      "#F87171"),
    ("📋", "CSV",   ".csv",  "Raw data for further analysis",        "#FBBF24"),
]


class _FormatCard(QFrame):
    def __init__(self, icon: str, name: str, ext: str, desc: str,
                 color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(140)
        self.setMinimumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False
        self._color = color

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 36))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        name_lbl = QLabel(name)
        name_lbl.setFont(QFont("Segoe UI Variable", 16, QFont.Weight.DemiBold))
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(name_lbl)

        ext_lbl = QLabel(ext)
        ext_lbl.setObjectName("SubCaption")
        ext_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(ext_lbl)

        desc_lbl = QLabel(desc)
        desc_lbl.setObjectName("SubCaption")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(desc_lbl)

        self._dot = QLabel("●")
        self._dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dot.setStyleSheet(f"color: {color}; font-size:20px; visibility:hidden;")
        self._dot.hide()
        lay.addWidget(self._dot)

    def set_selected(self, v: bool):
        self._selected = v
        if v:
            self.setStyleSheet(
                f"#Card {{ border:2px solid {self._color}; border-radius:8px; "
                f"background-color: {self._color}18; }}"
            )
            self._dot.show()
        else:
            self.setStyleSheet("")
            self._dot.hide()

    def mousePressEvent(self, e):
        self.set_selected(True)
        super().mousePressEvent(e)


class ExportPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_format = "Excel"
        self._format_cards: list[_FormatCard] = []
        self._progress = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(24)

        # ── Format cards ──────────────────────────────────────────
        fmt_lbl = QLabel("Select Export Format")
        fmt_lbl.setObjectName("SectionTitle")
        root.addWidget(fmt_lbl)

        fmt_row = QHBoxLayout()
        fmt_row.setSpacing(16)
        for icon, name, ext, desc, color in _FORMATS:
            card = _FormatCard(icon, name, ext, desc, color)
            card.mousePressEvent = self._make_select_handler(card, name)
            self._format_cards.append(card)
            fmt_row.addWidget(card, 1)
        self._format_cards[0].set_selected(True)
        root.addLayout(fmt_row)

        # ── Scope options ─────────────────────────────────────────
        scope_card = QFrame()
        scope_card.setObjectName("Card")
        scope_lay = QVBoxLayout(scope_card)
        scope_lay.setContentsMargins(20, 16, 20, 16)
        scope_lay.setSpacing(10)

        scope_title = QLabel("Export Scope")
        scope_title.setObjectName("CardHeader")
        scope_lay.addWidget(scope_title)

        self._scope_grp = QButtonGroup(self)
        for label in ["Current Project (PRJ-001)", "Date Range", "All Data"]:
            rb = QRadioButton(label)
            rb.setFont(QFont("Segoe UI", 13))
            self._scope_grp.addButton(rb)
            scope_lay.addWidget(rb)
        self._scope_grp.buttons()[0].setChecked(True)
        root.addWidget(scope_card)

        # ── Export action ─────────────────────────────────────────
        act_row = QHBoxLayout()
        act_row.setSpacing(16)

        self._export_btn = QPushButton("  ↑  Export Now")
        self._export_btn.setObjectName("PrimaryBtn")
        self._export_btn.setFixedHeight(44)
        self._export_btn.setFixedWidth(200)
        self._export_btn.clicked.connect(self._start_export)
        act_row.addWidget(self._export_btn)

        self._prog_bar = QProgressBar()
        self._prog_bar.setRange(0, 100)
        self._prog_bar.setFixedHeight(8)
        self._prog_bar.hide()
        act_row.addWidget(self._prog_bar, 1)
        root.addLayout(act_row)

        # ── Export history ────────────────────────────────────────
        hist_card = QFrame()
        hist_card.setObjectName("Card")
        hist_lay = QVBoxLayout(hist_card)
        hist_lay.setContentsMargins(0, 0, 0, 0)

        hist_hdr = QLabel("  Export History")
        hist_hdr.setFixedHeight(44)
        hist_hdr.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.DemiBold))
        hist_hdr.setStyleSheet("padding-left:16px; border-bottom:1px solid #3A3C42;")
        hist_lay.addWidget(hist_hdr)

        self._hist_table = self._build_history_table()
        hist_lay.addWidget(self._hist_table)
        root.addWidget(hist_card, 1)

        self._timer = QTimer()
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)

    def _make_select_handler(self, card: _FormatCard, name: str):
        def handler(e):
            for c in self._format_cards:
                c.set_selected(False)
            card.set_selected(True)
            self._selected_format = name
        return handler

    def _start_export(self):
        self._export_btn.setEnabled(False)
        self._prog_bar.show()
        self._prog_bar.setValue(0)
        self._progress = 0
        self._timer.start()

    def _tick(self):
        self._progress += 3
        self._prog_bar.setValue(min(self._progress, 100))
        if self._progress >= 100:
            self._timer.stop()
            self._export_btn.setText("✓  Exported!")
            self._prog_bar.hide()
            self._prepend_history()
            QTimer.singleShot(2500, lambda: self._export_btn.setText("  ↑  Export Now"))
            QTimer.singleShot(2500, lambda: self._export_btn.setEnabled(True))

    def _build_history_table(self) -> QTableView:
        table = QTableView()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().hide()
        table.setShowGrid(False)

        self._hist_model = QStandardItemModel(0, 4)
        self._hist_model.setHorizontalHeaderLabels(
            ["File Name", "Format", "Date", "Size"]
        )
        for h in md.EXPORT_HISTORY:
            row = [
                QStandardItem(h["name"]),
                QStandardItem(h["format"]),
                QStandardItem(h["date"]),
                QStandardItem(h["size"]),
            ]
            row[0].setFont(QFont("Cascadia Code", 12))
            for item in row:
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                      Qt.AlignmentFlag.AlignLeft)
            self._hist_model.appendRow(row)

        table.setModel(self._hist_model)
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _prepend_history(self):
        from datetime import date
        today = date.today().isoformat()
        name = f"PRJ-001_{self._selected_format}_Export_{today}"
        ext = {"Excel": ".xlsx", "PDF": ".pdf", "CSV": ".csv"}.get(
            self._selected_format, ".xlsx"
        )
        row = [
            QStandardItem(name + ext),
            QStandardItem(self._selected_format),
            QStandardItem(today),
            QStandardItem("—"),
        ]
        for item in row:
            item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter |
                                  Qt.AlignmentFlag.AlignLeft)
            item.setForeground(QColor("#4ADE80"))
        self._hist_model.insertRow(0, row)
