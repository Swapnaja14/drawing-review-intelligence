"""
analytics_screen.py — Dashboard Analytics screen.

Provides:
    AnalyticsPage(QWidget)
        Filter bar, KPI summary cards, and a grid of Pareto, monthly trend,
        and category distribution charts.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QComboBox,
                                QDateEdit, QGridLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from app import mock_data as md
from app.components.kpi_card import KpiCard
from app.components.charts import (
    build_pareto_chart,
    build_monthly_chart,
    build_category_pie,
)


class AnalyticsPage(QWidget):
    """
    Analytics Dashboard — filter bar, KPI cards, Pareto + line + donut charts.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Filter bar ────────────────────────────────────────────
        fb = QHBoxLayout()
        fb.setSpacing(12)

        for label, items in [
            ("Project",  ["All Projects"]  + [p.name for p in md.PROJECTS]),
            ("Category", ["All Categories"] + list(md.CATEGORY_COUNTS.keys())),
        ]:
            lbl = QLabel(f"{label}:")
            lbl.setObjectName("SubCaption")
            fb.addWidget(lbl)
            cb = QComboBox()
            cb.addItems(items)
            cb.setFixedHeight(36)
            fb.addWidget(cb)

        from_lbl = QLabel("From:")
        from_lbl.setObjectName("SubCaption")
        fb.addWidget(from_lbl)
        date_from = QDateEdit(QDate(2026, 1, 1))
        date_from.setFixedHeight(36)
        fb.addWidget(date_from)

        to_lbl = QLabel("To:")
        to_lbl.setObjectName("SubCaption")
        fb.addWidget(to_lbl)
        date_to = QDateEdit(QDate.currentDate())
        date_to.setFixedHeight(36)
        fb.addWidget(date_to)

        fb.addStretch()

        apply_btn = QPushButton("Apply Filters")
        apply_btn.setObjectName("PrimaryBtn")
        apply_btn.setFixedHeight(36)
        fb.addWidget(apply_btn)
        root.addLayout(fb)

        # ── KPI summary ───────────────────────────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        for icon, val, lbl, trend, color in [
            ("fa5s.comments",     "2,036", "Total Comments", "+143", "#3E9BFF"),
            ("fa5s.check-circle", "1,812", "Approved",       "+128", "#4ADE80"),
            ("fa5s.times-circle", "  112", "Rejected",       "−8",   "#F87171"),
            ("fa5s.flag",         "  112", "Flagged",        "+23",  "#FBBF24"),
        ]:
            card = KpiCard(icon, val, lbl, trend, color)
            card.setMinimumHeight(120)
            kpi_row.addWidget(card, 1)
        root.addLayout(kpi_row)

        # ── Chart grid ────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)

        pareto_view  = build_pareto_chart()
        monthly_view = build_monthly_chart()
        pie_view     = build_category_pie()

        def _wrap(view, min_h: int = 280) -> QFrame:
            f = QFrame()
            f.setObjectName("Card")
            lay = QVBoxLayout(f)
            lay.setContentsMargins(8, 8, 8, 8)
            view.setMinimumHeight(min_h)
            lay.addWidget(view)
            return f

        grid.addWidget(_wrap(pareto_view,  320), 0, 0, 2, 1)
        grid.addWidget(_wrap(monthly_view, 220), 0, 1)
        grid.addWidget(_wrap(pie_view,     220), 1, 1)

        root.addLayout(grid, 1)
