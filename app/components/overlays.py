"""
ToastNotification — bottom-right auto-dismissing overlay.
EmptyState       — centered icon + message + optional CTA.
"""
from __future__ import annotations
from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
                                QPushButton, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
try:
    import qtawesome as qta
    _HAS_QTA = True
except ImportError:
    _HAS_QTA = False


class ToastNotification(QWidget):
    """Floating bottom-right toast that auto-dismisses after `duration_ms`."""

    def __init__(self, message: str, kind: str = "info",
                 duration_ms: int = 3000, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        _colors = {"info": "#3E9BFF", "success": "#4ADE80",
                   "warning": "#FBBF24", "error": "#F87171"}
        accent = _colors.get(kind, "#3E9BFF")

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Color strip
        strip = QWidget()
        strip.setFixedWidth(4)
        strip.setStyleSheet(f"background:{accent}; border-radius:2px;")
        root.addWidget(strip)

        # Message
        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI", 13))
        msg_lbl.setWordWrap(True)
        root.addWidget(msg_lbl, 1)

        self.setStyleSheet(
            "QWidget { background-color:#2D2F34; border:1px solid #3A3C42;"
            "border-radius:8px; }"
        )
        self.setMinimumWidth(280)
        self.adjustSize()

        # Opacity fade
        self._eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._eff)
        self._anim_in = QPropertyAnimation(self._eff, b"opacity")
        self._anim_in.setDuration(200)
        self._anim_in.setStartValue(0.0)
        self._anim_in.setEndValue(1.0)
        self._anim_in.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._anim_out = QPropertyAnimation(self._eff, b"opacity")
        self._anim_out.setDuration(300)
        self._anim_out.setStartValue(1.0)
        self._anim_out.setEndValue(0.0)
        self._anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim_out.finished.connect(self.close)

        QTimer.singleShot(duration_ms, self._fade_out)

    def show_at(self, parent: QWidget):
        if parent:
            pr = parent.rect()
            self.adjustSize()
            x = parent.mapToGlobal(pr.bottomRight()).x() - self.width() - 24
            y = parent.mapToGlobal(pr.bottomRight()).y() - self.height() - 24
            self.move(x, y)
        self.show()
        self._anim_in.start()

    def _fade_out(self):
        self._anim_out.start()


class EmptyState(QWidget):
    def __init__(self, icon: str = "fa5s.inbox", message: str = "No data",
                 sub: str = "", cta_text: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        if _HAS_QTA:
            try:
                icon_lbl = QLabel()
                pixmap = qta.icon(icon, color="#A6A9B1").pixmap(64, 64)
                icon_lbl.setPixmap(pixmap)
                icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(icon_lbl)
            except Exception:
                pass

        msg_lbl = QLabel(message)
        msg_lbl.setFont(QFont("Segoe UI Variable", 17, QFont.Weight.DemiBold))
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg_lbl.setStyleSheet("color:#A6A9B1;")
        layout.addWidget(msg_lbl)

        if sub:
            sub_lbl = QLabel(sub)
            sub_lbl.setObjectName("SubCaption")
            sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(sub_lbl)

        if cta_text:
            btn = QPushButton(cta_text)
            btn.setObjectName("PrimaryBtn")
            btn.setFixedHeight(36)
            layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignCenter)
