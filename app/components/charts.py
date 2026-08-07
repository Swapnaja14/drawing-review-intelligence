"""
charts.py — QtCharts chart factory functions.

Provides:
    build_pareto_chart()   -> QChartView | QFrame
    build_monthly_chart()  -> QChartView | QFrame
    build_category_pie()   -> QChartView | QFrame
    no_chart_label(text)   -> QFrame   (fallback when QtCharts unavailable)

All functions return a QWidget ready to embed directly in any layout.
When ``PySide6.QtCharts`` is not installed, each chart function falls back
to ``no_chart_label()`` so the rest of the UI remains functional.
"""
from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPainter

try:
    from PySide6.QtCharts import (
        QChart, QChartView,
        QBarSeries, QBarSet,
        QLineSeries, QPieSeries,
        QValueAxis, QBarCategoryAxis,
    )
    _HAS_CHARTS = True
except ImportError:
    _HAS_CHARTS = False

from app import mock_data as md

__all__ = [
    "build_pareto_chart",
    "build_monthly_chart",
    "build_category_pie",
    "no_chart_label",
]


# ── Per-category accent colours ───────────────────────────────────────────────

_CAT_COLORS: dict[str, str] = {
    "Dimensional":   "#3E9BFF",
    "Structural":    "#A78BFA",
    "Electrical":    "#FBBF24",
    "Material":      "#2DD4BF",
    "Documentation": "#A6A9B1",
    "Other":         "#94A3B8",
}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _styled_chart(title: str = "") -> "QChart":
    """Return a QChart pre-styled for the dark theme."""
    chart = QChart()
    chart.setTitle(title)
    chart.setBackgroundBrush(QColor("#2D2F34"))
    chart.setPlotAreaBackgroundBrush(QColor("#26272B"))
    chart.setPlotAreaBackgroundVisible(True)
    chart.legend().setLabelColor(QColor("#A6A9B1"))
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
    if title:
        chart.setTitleBrush(QColor("#F2F3F5"))
        chart.setTitleFont(
            QFont("Segoe UI Variable", 13, QFont.Weight.DemiBold)
        )
    chart.setAnimationOptions(QChart.AnimationOption.AllAnimations)
    chart.setAnimationDuration(600)
    return chart


def _chart_view(chart: "QChart") -> "QChartView":
    """Wrap a QChart in a transparent, antialiased QChartView."""
    view = QChartView(chart)
    view.setRenderHint(QPainter.RenderHint.Antialiasing)
    view.setStyleSheet("background: transparent; border:none;")
    return view


def _axis_style(axis, color: str = "#A6A9B1") -> None:
    """Apply consistent axis label and grid-line styling."""
    axis.setLabelsColor(QColor(color))
    axis.setGridLineColor(QColor("#3A3C42"))
    axis.setLabelsFont(QFont("Segoe UI", 10))


# ── Public chart builders ─────────────────────────────────────────────────────

def no_chart_label(text: str) -> QFrame:
    """
    Return a placeholder card shown when QtCharts is not installed.

    Parameters
    ----------
    text:
        Short description of the missing chart (e.g. ``"Pareto Chart"``).
    """
    f = QFrame()
    f.setObjectName("Card")
    lay = QVBoxLayout(f)
    lbl = QLabel(f"📊  {text}\n(PySide6.QtCharts not available)")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet("color:#A6A9B1; font-size:14px;")
    lay.addWidget(lbl)
    return f


def build_pareto_chart():
    """
    Build a Pareto chart: bar series for category counts with a
    cumulative-percentage line overlay.

    Returns
    -------
    QChartView | QFrame
        QChartView if QtCharts is available, fallback QFrame otherwise.
    """
    if not _HAS_CHARTS:
        return no_chart_label("Pareto Chart")

    chart = _styled_chart("Pareto — Comments by Category")
    chart.legend().hide()

    cats   = md.PARETO_DATA["categories"]
    counts = md.PARETO_DATA["counts"]
    cumuls = md.PARETO_DATA["cumulative"]

    bar_set = QBarSet("Count")
    bar_set.setColor(QColor("#FFFFFF"))
    bar_set.setBorderColor(QColor("#CCCCCC"))
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
    for i, pct in enumerate(cumuls):
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


def build_monthly_chart():
    """
    Build a monthly trend line chart (total comments vs approved).

    Returns
    -------
    QChartView | QFrame
    """
    if not _HAS_CHARTS:
        return no_chart_label("Monthly Trend")

    chart = _styled_chart("Monthly Comment Trend")

    months   = md.MONTHLY_COUNTS["months"]
    total    = md.MONTHLY_COUNTS["comments"]
    approved = md.MONTHLY_COUNTS["approved"]

    for data, color, name in [
        (total,    "#3E9BFF", "Total"),
        (approved, "#4ADE80", "Approved"),
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


def build_category_pie():
    """
    Build a category distribution donut chart.

    Returns
    -------
    QChartView | QFrame
    """
    if not _HAS_CHARTS:
        return no_chart_label("Category Distribution")

    chart = _styled_chart("Category Distribution")
    chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)

    series = QPieSeries()
    series.setHoleSize(0.45)   # donut style
    for cat, count in md.CATEGORY_COUNTS.items():
        slice_ = series.append(cat, count)
        slice_.setColor(QColor(_CAT_COLORS.get(cat, "#A6A9B1")))
        slice_.setLabelColor(QColor("#F2F3F5"))
        slice_.setLabelFont(QFont("Segoe UI", 10))

    chart.addSeries(series)
    return _chart_view(chart)
