"""
comment_table.py — Custom cell delegates for the comment data tables.

Provides:
    ConfidenceDelegate
        Renders a confidence float (0–1) as a threshold-coloured progress
        bar with a centred percentage label.

    StatusDelegate
        Renders a status string as a rounded pill with status-keyed colours.

    CategoryDelegate
        Renders a category string as a rounded pill with category-keyed colours.

All three delegates share the same selection highlight behaviour.
"""
from __future__ import annotations
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt, QModelIndex, QRect


class ConfidenceDelegate(QStyledItemDelegate):
    """
    Cell delegate that renders a confidence score as a coloured bar + text.

    The cell must store a ``float`` in ``Qt.ItemDataRole.UserRole``.
    Colour thresholds: ≥ 0.90 → green, ≥ 0.70 → amber, < 0.70 → red.
    """

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        val = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(val, float):
            super().paint(painter, option, index)
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if option.state & 0x0001:   # selected
            painter.fillRect(option.rect, QColor("#3E9BFF22"))

        # Track
        bar = QRect(
            option.rect.x() + 8,
            option.rect.y() + 18,
            option.rect.width() - 16,
            8,
        )
        painter.setBrush(QColor("#3A3C42"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar, 4, 4)

        # Fill
        fill_w = int(bar.width() * val)
        if fill_w > 0:
            fill_c = (
                "#4ADE80" if val >= 0.9
                else "#FBBF24" if val >= 0.7
                else "#F87171"
            )
            painter.setBrush(QColor(fill_c))
            painter.drawRoundedRect(
                QRect(bar.x(), bar.y(), fill_w, bar.height()), 4, 4
            )

        painter.setPen(QColor("#F2F3F5"))
        painter.setFont(QFont("Cascadia Code", 11))
        painter.drawText(
            option.rect, Qt.AlignmentFlag.AlignCenter, f"{int(val * 100)}%"
        )


class StatusDelegate(QStyledItemDelegate):
    """
    Cell delegate that renders a status string as a coloured pill badge.

    Supported statuses: Pending, Approved, Rejected, Flagged.
    """

    _STATUS_COLORS: dict[str, tuple[str, str]] = {
        "Pending":  ("#A6A9B1", "#3A3C42"),
        "Approved": ("#4ADE80", "#1a3d26"),
        "Rejected": ("#F87171", "#3d1a1a"),
        "Flagged":  ("#FBBF24", "#3d2e0a"),
    }

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        status = index.data()
        if not status:
            super().paint(painter, option, index)
            return

        if option.state & 0x0001:
            painter.fillRect(option.rect, QColor("#3E9BFF22"))

        text_c, bg_c = self._STATUS_COLORS.get(status, ("#A6A9B1", "#3A3C42"))

        # Pill: at least 100 px wide, but never wider than the cell minus 16 px padding
        pill_h = 24
        pill_w = min(max(100, len(status) * 12), option.rect.width() - 16)
        x = option.rect.x() + (option.rect.width() - pill_w) // 2
        y = option.rect.y() + (option.rect.height() - pill_h) // 2

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(x, y, pill_w, pill_h, 5, 5)
        painter.setPen(QColor(text_c))
        painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        painter.drawText(
            QRect(x, y, pill_w, pill_h),
            Qt.AlignmentFlag.AlignCenter,
            status.upper(),
        )


class CategoryDelegate(QStyledItemDelegate):
    """
    Cell delegate that renders a category string as a coloured pill badge.

    Each engineering discipline has its own accent and background colour.
    """

    _CAT_BG: dict[str, tuple[str, str]] = {
        "Dimensional":   ("#3E9BFF", "#0d2540"),
        "Structural":    ("#A78BFA", "#2a1a4d"),
        "Electrical":    ("#FBBF24", "#3d2e0a"),
        "Material":      ("#2DD4BF", "#0a2d2a"),
        "Documentation": ("#A6A9B1", "#2d2f34"),
        "Other":         ("#94A3B8", "#252b35"),
        "Mechanical":    ("#FB923C", "#3d1f0a"),
    }

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index: QModelIndex,
    ) -> None:
        cat = index.data()
        if not cat:
            super().paint(painter, option, index)
            return

        if option.state & 0x0001:
            painter.fillRect(option.rect, QColor("#3E9BFF22"))

        text_c, bg_c = self._CAT_BG.get(cat, ("#A6A9B1", "#2d2f34"))
        pill_w = min(120, option.rect.width() - 16)
        pill_h = 22
        x = option.rect.x() + 8
        y = option.rect.y() + (option.rect.height() - pill_h) // 2

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(bg_c))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(x, y, pill_w, pill_h, 4, 4)
        painter.setPen(QColor(text_c))
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        painter.drawText(
            QRect(x, y, pill_w, pill_h),
            Qt.AlignmentFlag.AlignCenter,
            cat.upper(),
        )
