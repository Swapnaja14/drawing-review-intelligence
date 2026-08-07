"""
metadata_panel.py — Drawing metadata side panel.

Provides:
    DrawingMetadataPanel(QFrame)
        Renders a labelled list of engineering drawing metadata fields
        in a fixed-width right-side panel.
"""
from __future__ import annotations
from typing import Sequence, Tuple
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtGui import QFont

# Default sample fields (used when no data is supplied at construction time)
_DEFAULT_FIELDS: Sequence[Tuple[str, str]] = (
    ("Drawing Number", "UCC-E-101"),
    ("Drawing Title",  "P&ID Unit 4-A"),
    ("Revision",       "Rev A"),
    ("Project Name",   "UCC Site-4 Expansion"),
    ("Discipline",     "Process/Piping"),
    ("Sheet",          "1 of 3"),
    ("Scale",          "1:50"),
    ("Date",           "2026-07-28"),
)


class DrawingMetadataPanel(QFrame):
    """
    Right-side panel displaying engineering drawing metadata as form rows.

    Each field is shown as a grey label above a monospace value label.
    The panel can be refreshed at runtime via ``update_fields()``.

    Parameters
    ----------
    fields:
        Sequence of ``(label, value)`` string pairs.  Defaults to
        ``_DEFAULT_FIELDS`` (sample data for the mockup).
    fixed_width:
        Panel width in pixels (default 280).
    """

    def __init__(
        self,
        fields: Sequence[Tuple[str, str]] | None = None,
        fixed_width: int = 280,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedWidth(fixed_width)
        self.setStyleSheet(
            "#Card { border-radius:0; border-top:none;"
            " border-bottom:none; border-right:none; }"
        )

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(16, 16, 16, 16)
        self._lay.setSpacing(12)

        # Header
        hdr = QLabel("Drawing Metadata")
        hdr.setFont(QFont("Segoe UI Variable", 15, QFont.Weight.DemiBold))
        self._lay.addWidget(hdr)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        self._lay.addWidget(sep)

        # Field rows
        self._field_start_index = self._lay.count()
        self._append_fields(fields or _DEFAULT_FIELDS)
        self._lay.addStretch()

    # ── Public API ────────────────────────────────────────────────

    def update_fields(self, fields: Sequence[Tuple[str, str]]) -> None:
        """
        Replace all field rows with new data without recreating the header.

        Parameters
        ----------
        fields:
            New sequence of ``(label, value)`` pairs.
        """
        # Remove existing field widgets (keep header + separator)
        while self._lay.count() > self._field_start_index:
            item = self._lay.takeAt(self._lay.count() - 1)
            if item.widget():
                item.widget().deleteLater()

        self._append_fields(fields)
        self._lay.addStretch()

    # ── Private helpers ───────────────────────────────────────────

    def _append_fields(self, fields: Sequence[Tuple[str, str]]) -> None:
        for key, val in fields:
            k_lbl = QLabel(key)
            k_lbl.setObjectName("FormLabel")
            self._lay.addWidget(k_lbl)

            v_lbl = QLabel(val)
            v_lbl.setFont(QFont("Cascadia Code", 12))
            v_lbl.setWordWrap(True)
            self._lay.addWidget(v_lbl)
