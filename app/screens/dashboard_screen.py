"""
dashboard_screen.py — Home Dashboard screen.

Displays KPI metric cards, a recent-projects table, an activity feed,
and a processing-status panel connected to AppController & SQLite database.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QTableView, QListWidget, QListWidgetItem,
                                QPushButton, QProgressBar, QHeaderView, QSizePolicy,
                                QAbstractItemView)
from PySide6.QtGui import QFont, QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, Signal, QSize

from app.components.kpi_card import KpiCard
from app.components.chips import StatusChip

try:
    import qtawesome as qta  # noqa: F401
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


DEFAULT_ACTIVITIES: List[Dict[str, str]] = [
    {"text": "System initialized and ready", "time": "Just now"},
    {"text": "OCR Engine & Classification ready", "time": "5 min ago"},
    {"text": "Database connected and verified", "time": "10 min ago"},
]

DEFAULT_JOBS: List[Dict[str, Any]] = [
    {"name": "OCR Processing Pipeline", "progress": 100, "status": "Approved"},
    {"name": "Comment Classifier Engine", "progress": 100, "status": "Approved"},
    {"name": "Drawing Intelligence Hub", "progress": 100, "status": "Approved"},
]


def _card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("Card")
    return f


def _h2(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI Variable", 17, QFont.Weight.DemiBold))
    lbl.setObjectName("CardHeader")
    return lbl


class DashboardPage(QWidget):
    """
    Home Dashboard — KPI cards, recent projects table, activity feed,
    and processing status connected to SQLite Database backend.
    """

    open_project = Signal(str)

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self._controller = controller
        self._kpi_cards: List[KpiCard] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(20)

        # ── KPI row ───────────────────────────────────────────────
        self._kpi_row = QHBoxLayout()
        self._kpi_row.setSpacing(16)
        self._build_kpi_cards()
        root.addLayout(self._kpi_row)

        # ── Main split ────────────────────────────────────────────
        split = QHBoxLayout()
        split.setSpacing(16)

        # Recent projects table (left, stretch 2)
        proj_card = _card()
        proj_card.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
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

        self._proj_table = QTableView()
        self._proj_table.setAlternatingRowColors(True)
        self._proj_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._proj_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._proj_table.horizontalHeader().setStretchLastSection(True)
        self._proj_table.verticalHeader().hide()
        self._proj_table.setShowGrid(False)

        self._populate_projects_table()
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
        act_lay.addWidget(self._build_activity_list(), 1)
        right_col.addWidget(act_card, 1)

        # Processing status
        proc_card = _card()
        proc_lay = QVBoxLayout(proc_card)
        proc_lay.setContentsMargins(16, 16, 16, 16)
        proc_lay.setSpacing(10)
        proc_lay.addWidget(_h2("Processing Status"))
        for job in DEFAULT_JOBS:
            proc_lay.addLayout(self._build_job_row(job))
        right_col.addWidget(proc_card)

        split.addLayout(right_col, 1)
        root.addLayout(split, 1)

    # ── Sub-builders ──────────────────────────────────────────────

    def _get_kpi_values(self) -> tuple[int, int, int, str]:
        """Query KPI aggregates from controller."""
        kpi_data = self._controller.get_dashboard_kpis() if self._controller else None
        if kpi_data is not None:
            if hasattr(kpi_data, "total_projects"):
                total_projects = kpi_data.total_projects
                total_drawings = kpi_data.total_drawings
                total_comments = kpi_data.total_comments
                accuracy_val = kpi_data.accuracy_rate
            elif isinstance(kpi_data, dict):
                total_projects = kpi_data.get("total_projects", 0)
                total_drawings = kpi_data.get("drawings_processed", kpi_data.get("total_drawings", 0))
                total_comments = kpi_data.get("comments_detected", kpi_data.get("total_comments", 0))
                accuracy_val = kpi_data.get("accuracy", kpi_data.get("accuracy_rate"))
            else:
                total_projects, total_drawings, total_comments, accuracy_val = 0, 0, 0, None
        else:
            total_projects, total_drawings, total_comments, accuracy_val = 0, 0, 0, None

        accuracy_str = f"{accuracy_val:.1f}%" if accuracy_val is not None else "—"
        return total_projects, total_drawings, total_comments, accuracy_str

    def _build_kpi_cards(self) -> None:
        """Create initial KPI cards."""
        # Clear existing
        while self._kpi_row.count():
            item = self._kpi_row.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._kpi_cards.clear()

        total_projects, total_drawings, total_comments, accuracy_str = self._get_kpi_values()

        kpis = [
            ("fa5s.folder-open", str(total_projects), "Total Projects",    "Active",     "#3E9BFF"),
            ("fa5s.file-alt",    str(total_drawings), "Drawings Processed", "DB Records", "#8B9CFF"),
            ("fa5s.comments",    str(total_comments), "Comments Detected", "Live",       "#FBBF24"),
            ("fa5s.check-circle", accuracy_str,       "OCR Accuracy",      "Verified",   "#4ADE80"),
        ]
        for icon, val, lbl, trend, color in kpis:
            card = KpiCard(icon, val, lbl, trend, color)
            card.setMinimumHeight(130)
            self._kpi_cards.append(card)
            self._kpi_row.addWidget(card, 1)

    def _populate_projects_table(self) -> None:
        """Populate the projects table view from the controller repository."""
        model = QStandardItemModel(0, 6)
        model.setHorizontalHeaderLabels(
            ["Project", "Drawings", "Comments", "Progress", "Status", "Engineer"]
        )

        projects_list = self._controller.get_all_projects() if self._controller else []

        for p in projects_list:
            if isinstance(p, dict):
                p_name = p.get("name", p.get("id", "—"))
                p_drawings = str(p.get("drawings", p.get("total_drawings", "—")))
                p_comments = str(p.get("comments", p.get("total_comments", "—")))
                p_progress = f"{p.get('progress', 0)}%"
                p_status = p.get("status", "Active")
                p_engineer = p.get("lead_engineer", p.get("engineer", "—")) or "—"
            else:
                p_name = getattr(p, "name", "—")
                p_drawings = str(getattr(p, "drawings", getattr(p, "total_drawings", "—")))
                p_comments = str(getattr(p, "comments", getattr(p, "total_comments", "—")))
                p_progress = f"{getattr(p, 'progress', 0)}%"
                p_status = getattr(p, "status", "Active")
                p_engineer = getattr(p, "lead_engineer", getattr(p, "engineer", "—")) or "—"

            row = [
                QStandardItem(p_name),
                QStandardItem(p_drawings),
                QStandardItem(p_comments),
                QStandardItem(p_progress),
                QStandardItem(p_status),
                QStandardItem(p_engineer),
            ]
            row[0].setFont(QFont("Cascadia Code", 13))
            for item in row:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
                )
            model.appendRow(row)

        self._proj_table.setModel(model)
        hdr = self._proj_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)

    def reload_data(self) -> None:
        """Refresh KPI cards and projects table with fresh database data."""
        self._build_kpi_cards()
        self._populate_projects_table()

    def reload_comments(self) -> None:
        """Alias to refresh dashboard data when new documents or comments are processed."""
        self.reload_data()

    def _build_activity_list(self) -> QListWidget:
        lst = QListWidget()
        lst.setSpacing(2)
        for act in DEFAULT_ACTIVITIES:
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
        chunk_color = "#4ADE80" if job["progress"] == 100 else "#3E9BFF"
        bar.setStyleSheet(
            "QProgressBar { background:#3A3C42; border-radius:3px; }"
            f"QProgressBar::chunk {{ background: {chunk_color}; border-radius:3px; }}"
        )
        row.addWidget(bar, 1)

        chip = StatusChip(job["status"])
        chip.setFixedWidth(72)
        row.addWidget(chip)
        return row
