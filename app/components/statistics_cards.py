"""
statistics_cards.py — Statistical summary card widgets.

Provides:
    CategorySummaryCard(QFrame)
        Compact card with an emoji icon, a numeric count, and a discipline
        label.  Used in the Classification screen's category summary row.

Re-exports (for convenience):
    KpiCard — from app.components.kpi_card
"""
from __future__ import annotations
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Re-export so callers can do: from app.components.statistics_cards import KpiCard
from app.components.kpi_card import KpiCard  # noqa: F401

__all__ = ["CategorySummaryCard", "KpiCard"]


class CategorySummaryCard(QFrame):
    """
    Compact summary card for a single engineering discipline category.

    Displays an emoji icon above a bold numeric count and a wrapped label.

    Parameters
    ----------
    icon:
        Unicode emoji representing the discipline (e.g. ``"📐"``).
    count:
        Number to display prominently.
    label:
        Category name shown below the count.
    color:
        CSS hex colour applied to the count label (default accent blue).
    """

    def __init__(
        self,
        icon: str,
        count: int,
        label: str,
        color: str = "#3E9BFF",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(100)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        icon_lbl = QLabel(icon)
        icon_lbl.setFont(QFont("Segoe UI", 20))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon_lbl)

        cnt_lbl = QLabel(str(count))
        cnt_lbl.setFont(QFont("Segoe UI Variable", 20, QFont.Weight.Bold))
        cnt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cnt_lbl.setStyleSheet(f"color:{color};")
        lay.addWidget(cnt_lbl)

        lab_lbl = QLabel(label)
        lab_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lab_lbl.setObjectName("SubCaption")
        lab_lbl.setWordWrap(True)
        lay.addWidget(lab_lbl)
