"""
filter_panel.py — Horizontal combo-box filter bar.

Provides:
    FilterComboBar(QWidget)
        A row of labelled QComboBox dropdowns.  Emits ``filter_changed``
        whenever any selection changes, making it easy for screens to
        react without wiring each combo individually.
"""
from __future__ import annotations
from typing import Sequence, Tuple
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
from PySide6.QtCore import Signal


class FilterComboBar(QWidget):
    """
    Horizontal bar of labelled combo-box filters.

    Parameters
    ----------
    filters:
        Sequence of ``(label, items)`` tuples.  Each tuple produces one
        labelled combo box.
    combo_height:
        Fixed height for each QComboBox (default 36 px).

    Signals
    -------
    filter_changed(str, str)
        Emitted as ``(label, selected_value)`` whenever any combo changes.
    """

    filter_changed = Signal(str, str)

    def __init__(
        self,
        filters: Sequence[Tuple[str, Sequence[str]]],
        combo_height: int = 36,
        parent=None,
    ):
        super().__init__(parent)
        self._combos: dict[str, QComboBox] = {}

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        for label, items in filters:
            lbl = QLabel(f"{label}:")
            lbl.setObjectName("SubCaption")
            lay.addWidget(lbl)

            cb = QComboBox()
            cb.addItems(items)
            cb.setFixedHeight(combo_height)
            # Capture label in default-argument to avoid late-binding closure bug
            cb.currentTextChanged.connect(
                lambda text, lbl=label: self.filter_changed.emit(lbl, text)
            )
            self._combos[label] = cb
            lay.addWidget(cb)

    # ── Public API ────────────────────────────────────────────────

    def current_values(self) -> dict[str, str]:
        """Return ``{label: current_text}`` for all combos."""
        return {label: cb.currentText() for label, cb in self._combos.items()}

    def set_value(self, label: str, value: str) -> None:
        """Set the current selection of a named combo programmatically."""
        if label in self._combos:
            self._combos[label].setCurrentText(value)

    def combo(self, label: str) -> QComboBox | None:
        """Return the QComboBox for a given label, or None if not found."""
        return self._combos.get(label)
