"""3.2 Home Dashboard — KPI cards, recent projects table, activity feed, processing status."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QListWidget, QListWidgetItem,
                                QPushButton, QProgressBar, QHeaderView, QSizePolicy,
                                QAbstractItemView)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem, QColor
from PySide6.QtCore import Qt, Signal, QSize

from app.components.kpi_card import KpiCard
from app.components.chips import StatusChip
from app import mock_data as md

try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


# ── Helper ────────────────────────────────────────────────────────────────────

def _card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("Card")
    return f


def _h2(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI Variable", 17, QFont.Weight.DemiBold))
    lbl.setObjectName("CardHeader")
    return lbl


# ── Dashboard Page ────────────────────────────────────────────────────────────

class DashboardPage(QWidget):
    open_project = Signal(str)   # emits project id

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # ── KPI row ───────────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        kpis = [
            ("fa5s.folder-open", str(md.KPI["total_projects"]),    "Total Projects",       md.KPI["trend_projects"],  "#3E9BFF"),
            ("fa5s.file-alt",    str(md.KPI["drawings_processed"]),"Drawings Processed",   md.KPI["trend_drawings"],  "#8B9CFF"),
            ("fa5s.comments",    str(md.KPI["comments_detected"]), "Comments Detected",    md.KPI["trend_comments"],  "#FBBF24"),
            ("fa5s.check-circle",f'{md.KPI["accuracy"]}%',         "OCR Accuracy",         md.KPI["trend_accuracy"],  "#4ADE80"),
        ]
        for icon, val, lbl, trend, color in kpis:
            card = KpiCard(icon, val, lbl, trend, color)
            card.setMinimumHeight(130)
            kpi_row.addWidget(card, 1)
        root.addLayout(kpi_row)

        # ── Main split ────────────────────────────────────────────
        split = QHBoxLayout()
        split.setSpacing(16)

        # Recent projects (left, stretch 2)
        proj_card = _card()
        proj_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        proj_lay = QVBoxLayout(proj_card)
        proj_lay.setContentsMargins(16, 16, 16, 16)
        proj_lay.setSpacing(12)

        proj_hdr = QHBoxLayout()
        proj_hdr.addWidget(_h2("Recent Projects"))
        proj_hdr.addStretch()
        view_all = QPushButton("View All →")
        view_all.setObjectName("GhostBtn")
        proj_hdr.addWidget(view_all)
        proj_lay.addLayout(proj_hdr)

        self._proj_table = self._build_projects_table()
        proj_lay.addWidget(self._proj_table)
        split.addWidget(proj_card, 2)

        # Right column (stretch 1)
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # Activity feed
        act_card = _card()
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(16, 16, 16, 16)
        act_lay.setSpacing(8)
        act_lay.addWidget(_h2("Recent Activity"))
        act_list = self._build_activity_list()
        act_lay.addWidget(act_list, 1)
        right_col.addWidget(act_card, 1)

        # Processing status
        proc_card = _card()
        proc_lay = QVBoxLayout(proc_card)
        proc_lay.setContentsMargins(16, 16, 16, 16)
        proc_lay.setSpacing(10)
        proc_lay.addWidget(_h2("Processing Status"))
        for job in md.JOBS:
            proc_lay.addLayout(self._build_job_row(job))
        right_col.addWidget(proc_card)

        split.addLayout(right_col, 1)
        root.addLayout(split, 1)

    # ── Sub-builders ─────────────────────────────────────────────

    def _build_projects_table(self) -> QTableView:
        table = QTableView()
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().hide()
        table.setShowGrid(False)

        model = QStandardItemModel(0, 6)
        model.setHorizontalHeaderLabels(
            ["Project", "Drawings", "Comments", "Progress", "Status", "Engineer"]
        )
        for p in md.PROJECTS:
            row = [
                QStandardItem(p.name),
                QStandardItem(str(p.drawings)),
                QStandardItem(str(p.comments)),
                QStandardItem(f"{p.progress}%"),
                QStandardItem(p.status),
                QStandardItem(p.engineer),
            ]
            row[0].setFont(QFont("Cascadia Code", 13))
            for item in row:
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            model.appendRow(row)

        table.setModel(model)
        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        return table

    def _build_activity_list(self) -> QListWidget:
        lst = QListWidget()
        lst.setSpacing(2)
        for act in md.ACTIVITIES:
            item = QListWidgetItem(f"  {act['text']}   {act['time']}")
            item.setSizeHint(QSize(0, 38))
            lst.addItem(item)
        return lst

    def _build_job_row(self, job: dict) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        name_lbl = QLabel(job["name"])
        name_lbl.setFixedWidth(200)
        name_lbl.setStyleSheet("color: #A6A9B1; font-size:13px;")
        row.addWidget(name_lbl)

        bar = QProgressBar()
        bar.setValue(job["progress"])
        bar.setFixedHeight(6)
        bar.setStyleSheet(
            f"QProgressBar {{ background:#3A3C42; border-radius:3px; }}"
            f"QProgressBar::chunk {{ background: "
            f"{'#4ADE80' if job['progress']==100 else '#3E9BFF'}; border-radius:3px; }}"
        )
        row.addWidget(bar, 1)

        chip = StatusChip(job["status"])
        chip.setFixedWidth(72)
        row.addWidget(chip)
        return row
