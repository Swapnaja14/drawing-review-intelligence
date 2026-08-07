"""
status_bar.py — Pre-configured application status bar.

Provides:
    AppStatusBar(QStatusBar)
        Displays a "Ready" / current-status message on the left and a
        version / technology string as a permanent right-aligned widget.
"""
from __future__ import annotations
from PySide6.QtWidgets import QStatusBar, QLabel


class AppStatusBar(QStatusBar):
    """
    Application status bar with a left status label and a right version label.

    Parameters
    ----------
    version:
        Version string shown on the right (default ``"v1.0.0"``).
    """

    def __init__(self, version: str = "v1.0.0", parent=None):
        super().__init__(parent)

        self._ready_lbl = QLabel("  Ready")
        self.addWidget(self._ready_lbl)

        ver_lbl = QLabel(
            f"UCC Analyzer {version}  ·  Python 3.12  ·  PySide6  "
        )
        self.addPermanentWidget(ver_lbl)

    # ── Public API ────────────────────────────────────────────────

    def set_message(self, text: str) -> None:
        """Update the left-side status message."""
        self._ready_lbl.setText(f"  {text}")

    def reset_message(self) -> None:
        """Reset the left-side label to the default "Ready" state."""
        self._ready_lbl.setText("  Ready")
