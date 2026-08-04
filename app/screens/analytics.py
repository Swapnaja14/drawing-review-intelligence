"""3.9 Dashboard Analytics — filter bar, KPI cards, Pareto + line + pie charts via QtCharts."""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFrame,
                                QLabel, QPushButton, QComboBox, QSizePolicy,
                                QDateEdit, QGridLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPainter

try:
    from PySide6.QtCharts import (QChart, QChartView, QBarSeries, QBarSet,
                                   QLineSeries, QPieSeries, QValueAxis,
                                   QBarCategoryAxis, QCategoryAxis)
    _HAS_CHARTS = True
except ImportError:
    _HAS_CHARTS = False

from app import mock_data as md
from app.components.kpi_card import KpiCard


_CAT_COLORS = {
    "Dimensional":   "#3E9BFF",
    "Structural":    "#A78BFA",
    "Electrical":    "#FBBF24",
    "Material":      "#2DD4BF",
    "Documentation": "#A6A9B1",
    "Other":         "#94A3B8",
}


def _styled_chart(title: str = "") -> QChart:
    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(QColor("#2D2F34"))
    chart.setPlotAreaBackgroundBrush(QColor("#26272B"))
    chart.setPlotAreaBackgroundVisible(True)
    chart.legend().setLabelColor(QColor("#A6A9B1"))
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    if title:
        chart.setTitleBrush(QColor("#F2F3F5"))
        f = QFont("Segoe UI Variable", 13, QFont.Weight.DemiBold)
        chart.setTitleFont(f)
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(600)
    return chart


def _chart_view(chart: QChart) -> QChartView:
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet("background: transparent; border:none;")
    return view


def _axis_style(axis, color="#A6A9B1"):
    axis.setLabelsColor(QColor(color))
    axis.setGridLineColor(QColor("#3A3C42"))
    lf = QFont("Segoe UI", 10)
    axis.setLabelsFont(lf)


# ── Pareto chart ──────────────────────────────────────────────────────────────

def _build_pareto() -> QChartView:
    chart = _styled_chart("Pareto — Comments by Category")
    chart.legend().hide()

    cats   = md.PARETO_DATA["categories"]
    counts = md.PARETO_DATA["counts"]
    cumuls = md.PARETO_DATA["cumulative"]

    bar_set = QBarSet("Count")
    bar_set.setColor(QColor("#3E9BFF"))
    for v in counts:
        bar_set.append(v)

    bar_series = QBarSeries()
    bar_series.append(bar_set)
    chart.addSeries(bar_series)

    line_series = QLineSeries()
    line_series.setName("Cumulative %")
    line_series.setColor(QColor("#FBBF24"))
    pen = line_series.pen()
    pen.setWidth(2)
    line_series.setPen(pen)
    for i, (c, pct) in enumerate(zip(cats, cumuls)):
        line_series.append(i + 0.5, pct * max(counts) / 100)
    chart.addSeries(line_series)

    ax_cat = QBarCategoryAxis()
    ax_cat.append(cats)
    _axis_style(ax_cat)
    chart.addAxis(ax_cat, Qt.AlignmentFlag.AlignBottom)
    bar_series.attachAxis(ax_cat)

    ax_val = QValueAxis()
    ax_val.setRange(0, max(counts) * 1.1)
    ax_val.setLabelFormat("%d")
    _axis_style(ax_val)
    chart.addAxis(ax_val, Qt.AlignmentFlag.AlignLeft)
    bar_series.attachAxis(ax_val)
    line_series.attachAxis(ax_cat)
    line_series.attachAxis(ax_val)

    return _chart_view(chart)


# ── Monthly trend chart ────────────────────────────────────────────────────────

def _build_monthly() -> QChartView:
    chart = _styled_chart("Monthly Comment Trend")

    months  = md.MONTHLY_COUNTS["months"]
    total   = md.MONTHLY_COUNTS["comments"]
    approved = md.MONTHLY_COUNTS["approved"]

    for data, color, name in [
        (total,   "#3E9BFF", "Total"),
        (approved,"#4ADE80", "Approved"),
    ]:
        series = QLineSeries()
        series.setName(name)
        series.setColor(QColor(color))
        pen = series.pen()
        pen.setWidth(2)
        series.setPen(pen)
        for i, v in enumerate(data):
            series.append(i, v)
        chart.addSeries(series)

    ax_cat = QBarCategoryAxis()
    ax_cat.append(months)
    _axis_style(ax_cat)
    chart.addAxis(ax_cat, Qt.AlignmentFlag.AlignBottom)

    ax_val = QValueAxis()
    ax_val.setRange(0, max(total) * 1.15)
    ax_val.setLabelFormat("%d")
    _axis_style(ax_val)
    chart.addAxis(ax_val, Qt.AlignmentFlag.AlignLeft)

    for series in chart.series():
        series.attachAxis(ax_cat)
        series.attachAxis(ax_val)

    return _chart_view(chart)


# ── Category distribution donut ────────────────────────────────────────────────

def _build_category_pie() -> QChartView:
    chart = _styled_chart("Category Distribution")
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)

    series = QPieSeries()
    series.setHoleSize(0.45)   # donut
    for cat, count in md.CATEGORY_COUNTS.items():
        slice_ = series.append(cat, count)
        slice_.setColor(QColor(_CAT_COLORS.get(cat, "#A6A9B1")))
        slice_.setLabelColor(QColor("#F2F3F5"))
        slice_.setLabelFont(QFont("Segoe UI", 10))

    chart.addSeries(series)
    return _chart_view(chart)


# ── Fallback (no QtCharts) ────────────────────────────────────────────────────

def _no_chart_label(text: str) -> QFrame:
    f = QFrame()
    f.setObjectName("Card")
    lay = QVBoxLayout(f)
    lbl = QLabel(f"📊  {text}\n(PySide6.QtCharts not available)")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("color:#A6A9B1; font-size:14px;")
    lay.addWidget(lbl)
    return f


# ── Analytics Page ────────────────────────────────────────────────────────────

class AnalyticsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        # ── Filter bar ────────────────────────────────────────────
        fb = QHBoxLayout()
        fb.setSpacing(12)

        for label, items in [
            ("Project",   ["All Projects"] + [p.name for p in md.PROJECTS]),
            ("Category",  ["All Categories"] + list(md.CATEGORY_COUNTS.keys())),
        ]:
            lbl = QLabel(label + ":")
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
            ("fa5s.comments",    "2,036", "Total Comments",  "+143",  "#3E9BFF"),
            ("fa5s.check-circle","1,812", "Approved",        "+128",  "#4ADE80"),
            ("fa5s.times-circle","  112", "Rejected",        "−8",    "#F87171"),
            ("fa5s.flag",        "  112", "Flagged",         "+23",   "#FBBF24"),
        ]:
            card = KpiCard(icon, val, lbl, trend, color)
            card.setMinimumHeight(120)
            kpi_row.addWidget(card, 1)
        root.addLayout(kpi_row)

        # ── Chart grid ────────────────────────────────────────────
        grid = QGridLayout()
        grid.setSpacing(16)

        if _HAS_CHARTS:
            pareto_view = _build_pareto()
            monthly_view = _build_monthly()
            pie_view = _build_category_pie()
        else:
            pareto_view = _no_chart_label("Pareto Chart")
            monthly_view = _no_chart_label("Monthly Trend")
            pie_view = _no_chart_label("Category Distribution")

        def _wrap(view, min_h=280) -> QFrame:
            f = QFrame()
            f.setObjectName("Card")
            l = QVBoxLayout(f)
            l.setContentsMargins(8, 8, 8, 8)
            view.setMinimumHeight(min_h)
            l.addWidget(view)
            return f

        grid.addWidget(_wrap(pareto_view, 320), 0, 0, 2, 1)
        grid.addWidget(_wrap(monthly_view, 220), 0, 1)
        grid.addWidget(_wrap(pie_view, 220), 1, 1)

        root.addLayout(grid, 1)
