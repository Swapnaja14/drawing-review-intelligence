"""Status chip and category badge components."""
from __future__ import annotations
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

_STATUS_COLORS = {
    "Pending":  ("#A6A9B1", "#3A3C42"),
    "Approved": ("#4ADE80", "#1a3d26"),
    "Rejected": ("#F87171", "#3d1a1a"),
    "Flagged":  ("#FBBF24", "#3d2e0a"),
}
_STATUS_COLORS_LIGHT = {
    "Pending":  ("#5B5F6A", "#E8E9EC"),
    "Approved": ("#1E8E3E", "#D4F2DC"),
    "Rejected": ("#D93025", "#FAD5D3"),
    "Flagged":  ("#E8A000", "#FDF0CD"),
}

_CATEGORY_COLORS = {
    "Dimensional":   ("#3E9BFF", "#0d2540"),
    "Structural":    ("#A78BFA", "#2a1a4d"),
    "Electrical":    ("#FBBF24", "#3d2e0a"),
    "Material":      ("#2DD4BF", "#0a2d2a"),
    "Documentation": ("#A6A9B1", "#2d2f34"),
    "Other":         ("#94A3B8", "#252b35"),
    "Mechanical":    ("#FB923C", "#3d1f0a"),
}
_CATEGORY_COLORS_LIGHT = {
    "Dimensional":   ("#0067C5", "#DCEEFF"),
    "Structural":    ("#7C3AED", "#EDE9FE"),
    "Electrical":    ("#D97706", "#FEF3C7"),
    "Material":      ("#0F766E", "#CCFBF1"),
    "Documentation": ("#6B7280", "#F3F4F6"),
    "Other":         ("#64748B", "#F1F5F9"),
    "Mechanical":    ("#EA580C", "#FFF7ED"),
}


class StatusChip(QLabel):
    def __init__(self, status: str, dark: bool = True, parent=None):
        super().__init__(parent)
        self.set_status(status, dark)

    def set_status(self, status: str, dark: bool = True):
        palette = _STATUS_COLORS if dark else _STATUS_COLORS_LIGHT
        text_c, bg_c = palette.get(status, ("#A6A9B1", "#3A3C42"))
        self.setText(status.upper())
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"color:{text_c}; background-color:{bg_c};"
            f"border-radius:4px; padding:2px 8px;"
        )
        self.setFixedHeight(22)


class CategoryBadge(QLabel):
    def __init__(self, category: str, dark: bool = True, parent=None):
        super().__init__(parent)
        self.set_category(category, dark)

    def set_category(self, category: str, dark: bool = True):
        palette = _CATEGORY_COLORS if dark else _CATEGORY_COLORS_LIGHT
        text_c, bg_c = palette.get(category, ("#A6A9B1", "#2d2f34"))
        self.setText(category.upper())
        self.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"color:{text_c}; background-color:{bg_c};"
            f"border-radius:4px; padding:2px 10px;"
        )
        self.setFixedHeight(22)
