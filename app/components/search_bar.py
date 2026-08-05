"""
search_bar.py — Reusable search input widget.

Provides:
    SearchBar(QLineEdit)
        Pre-styled search field with a magnifier-emoji placeholder and a
        ``search_changed`` Signal; can be connected directly to a proxy
        model's ``setFilterFixedString`` slot.
"""
from __future__ import annotations
from PySide6.QtWidgets import QLineEdit
from PySide6.QtCore import Signal


class SearchBar(QLineEdit):
    """
    Styled search input with a ``search_changed`` Signal.

    The widget is a drop-in replacement for a bare ``QLineEdit`` connected
    to ``QSortFilterProxyModel.setFilterFixedString``.

    Parameters
    ----------
    placeholder:
        Placeholder text (default: global search hint).
    fixed_width:
        Widget width in pixels.  Pass ``0`` to allow free sizing.
    fixed_height:
        Widget height in pixels (default 36).
    """

    search_changed = Signal(str)

    def __init__(
        self,
        placeholder: str = "  🔍  Search…",
        fixed_width: int = 320,
        fixed_height: int = 36,
        parent=None,
    ):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        if fixed_width:
            self.setFixedWidth(fixed_width)
        self.setFixedHeight(fixed_height)
        self.textChanged.connect(self.search_changed)
