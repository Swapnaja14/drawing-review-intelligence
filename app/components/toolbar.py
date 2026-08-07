"""
toolbar.py — Generic toolbar utility widgets.

Provides:
    make_toolbar_btn(text, tooltip) -> QToolButton
        Factory that returns a standard 36×36 square toolbar button.

    ToolbarSeparator(QFrame)
        Thin vertical separator line for use inside toolbars.
"""
from __future__ import annotations
from PySide6.QtWidgets import QToolButton, QFrame


def make_toolbar_btn(text: str, tooltip: str = "") -> QToolButton:
    """
    Create and return a standard square toolbar button.

    Parameters
    ----------
    text:
        Unicode glyph or short label for the button face.
    tooltip:
        Tooltip text shown on hover.

    Returns
    -------
    QToolButton
        Fixed at 36×36 px, ready to add to any toolbar layout.
    """
    btn = QToolButton()
    btn.setText(text)
    btn.setToolTip(tooltip)
    btn.setFixedSize(36, 36)
    return btn


class ToolbarSeparator(QFrame):
    """Thin vertical separator line for use inside horizontal toolbars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.VLine)
        self.setStyleSheet("color: #3A3C42;")
