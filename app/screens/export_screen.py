"""
export_screen.py — Export screen.

Provides:
    ExportPage(QWidget)
        Format selector cards (Excel / PDF / CSV), scope radio buttons,
        simulated export progress bar, and an export history table.
"""
from __future__ import annotations
from datetime import date as _date
from pathlib import Path
from typing import Optional, Any

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QRadioButton, QButtonGroup,
                                QProgressBar, QTableView, QHeaderView,
                                QAbstractItemView, QFileDialog, QMessageBox)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, QTimer

from src.core.dtos.export_dtos import ExportConfigDTO, ExportFormat
from app import mock_data as md



# ── Format card ───────────────────────────────────────────────────────────────

_FORMATS = [
    ("📊", "Excel", ".xlsx", "Full data with charts and formatting", "#4ADE80"),
    ("📜", "JSON",  ".json", "Structured machine-readable format",   "#60A5FA"),
    ("📋", "CSV",   ".csv",  "Raw data for further analysis",        "#FBBF24"),
]



class _FormatCard(QFrame):
    """Selectable export-format card."""

    def __init__(self, icon: str, name: str, ext: str,
                 desc: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumHeight(140)
        self.setMinimumWidth(180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False
        self._color    = color

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
        self._dot.setStyleSheet(f"color: {color}; font-size:20px;")
        self._dot.hide()
        lay.addWidget(self._dot)

    def set_selected(self, v: bool) -> None:
        self._selected = v
        if v:
            self.setStyleSheet(
                f"#Card {{ border:2px solid {self._color};"
                f" border-radius:8px;"
                f" background-color: {self._color}18; }}"
            )
            self._dot.show()
        else:
            self.setStyleSheet("")
            self._dot.hide()

    def mousePressEvent(self, e) -> None:
        self.set_selected(True)
        super().mousePressEvent(e)


# ── ExportPage ────────────────────────────────────────────────────────────────

class ExportPage(QWidget):
    """
    Export — format cards, scope options, progress bar,
    and an export history table.
    """

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller       = controller
        self._selected_format  = "Excel"
        self._format_cards: list[_FormatCard] = []
        self._progress         = 0

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
        hist_hdr.setStyleSheet(
            "padding-left:16px; border-bottom:1px solid #3A3C42;"
        )
        hist_lay.addWidget(hist_hdr)

        self._hist_table = self._build_history_table()
        hist_lay.addWidget(self._hist_table)
        root.addWidget(hist_card, 1)



    # ── Helpers ───────────────────────────────────────────────────

    def _make_select_handler(self, card: _FormatCard, name: str):
        def handler(e):
            for c in self._format_cards:
                c.set_selected(False)
            card.set_selected(True)
            self._selected_format = name
        return handler

    def _get_format_details(self) -> tuple[str, str, str]:
        """Returns (format_code, file_filter, file_extension)."""
        fmt = self._selected_format
        if fmt == "JSON":
            return (ExportFormat.JSON, "JSON Files (*.json);;All Files (*)", ".json")
        elif fmt == "CSV":
            return (ExportFormat.CSV, "CSV Files (*.csv);;All Files (*)", ".csv")
        else:
            return (ExportFormat.EXCEL, "Excel Files (*.xlsx);;All Files (*)", ".xlsx")

    def _format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _start_export(self) -> None:
        fmt_code, filter_str, ext = self._get_format_details()
        today_str = _date.today().isoformat()

        drawing_no = "Comments"
        if self._controller and getattr(self._controller, "current_document", None):
            doc = self._controller.current_document
            if hasattr(doc, "file_name") and doc.file_name:
                drawing_no = doc.file_name.rsplit(".", 1)[0]

        default_filename = f"{drawing_no}_Export_{today_str}{ext}"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {self._selected_format} File",
            default_filename,
            filter_str,
        )

        if not file_path:
            return

        out_path = Path(file_path)

        if self._controller is None:
            QMessageBox.critical(
                self,
                "Export Error",
                "Backend controller is not connected.",
            )
            return

        self._export_btn.setEnabled(False)
        self._prog_bar.show()
        self._prog_bar.setValue(50)

        try:
            drawing_id = getattr(self._controller, "current_drawing_id", None) or None
            config = ExportConfigDTO(
                output_path=out_path,
                format=fmt_code,
                drawing_id=drawing_id,
            )

            result = self._controller.export_data(config)
            self._prog_bar.setValue(100)

            if result and getattr(result, "success", False):
                self._export_btn.setText("✓  Exported!")
                self._prepend_history(
                    result.output_path,
                    self._selected_format,
                    getattr(result, "file_size_bytes", 0),
                )
                QTimer.singleShot(
                    2500, lambda: self._export_btn.setText("  ↑  Export Now")
                )
                QTimer.singleShot(
                    2500, lambda: self._export_btn.setEnabled(True)
                )
                self._prog_bar.hide()

                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Successfully exported {result.total_rows} row(s) to:\n{result.output_path}",
                )
            else:
                err_msg = getattr(result, "error_message", "") if result else "Unknown error"
                self._export_btn.setText("  ↑  Export Now")
                self._export_btn.setEnabled(True)
                self._prog_bar.hide()
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export data to:\n{out_path}\n\nError: {err_msg}",
                )
        except Exception as e:
            self._export_btn.setText("  ↑  Export Now")
            self._export_btn.setEnabled(True)
            self._prog_bar.hide()
            QMessageBox.critical(
                self,
                "Export Failed",
                f"An error occurred during export:\n{str(e)}",
            )


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
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
            self._hist_model.appendRow(row)

        table.setModel(self._hist_model)
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _prepend_history(self, output_path: Path | str, format_name: str, size_bytes: int = 0) -> None:
        today = _date.today().isoformat()
        file_name = Path(output_path).name
        size_str = self._format_size(size_bytes) if size_bytes > 0 else "—"
        row = [
            QStandardItem(file_name),
            QStandardItem(format_name),
            QStandardItem(today),
            QStandardItem(size_str),
        ]
        for item in row:
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
            )
            item.setForeground(QColor("#4ADE80"))
        self._hist_model.insertRow(0, row)

