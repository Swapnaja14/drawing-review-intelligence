"""3.1 Splash Screen — frameless, auto-transitions to main window."""
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QApplication
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient


class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 340)

        # Center on screen
        screen = QApplication.primaryScreen()
        if screen:
            sg = screen.geometry()
            self.move(sg.center() - self.rect().center())

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 32)
        root.setSpacing(0)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo emoji / icon
        logo = QLabel("🔍")
        logo.setFont(QFont("Segoe UI", 52))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(logo)

        root.addSpacing(8)

        # App name
        title = QLabel("UCC Analyzer")
        title.setFont(QFont("Segoe UI Variable", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #F2F3F5;")
        root.addWidget(title)

        # Tagline
        tag = QLabel("AI-Powered Drawing Review & Comment Analysis")
        tag.setFont(QFont("Segoe UI", 12))
        tag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tag.setStyleSheet("color: #A6A9B1;")
        root.addWidget(tag)

        root.addSpacing(28)

        # Progress bar
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)   # indeterminate
        self._bar.setFixedHeight(4)
        self._bar.setStyleSheet(
            "QProgressBar { background:#3A3C42; border-radius:2px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #3E9BFF, stop:1 #8B9CFF); border-radius:2px; }"
        )
        root.addWidget(self._bar)

        root.addSpacing(16)

        # Version
        ver = QLabel("v1.0.0  ·  © 2026 UCC Engineering")
        ver.setFont(QFont("Segoe UI", 10))
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color: #5B5F6A;")
        root.addWidget(ver)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 16, 16)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#26272B"))
        grad.setColorAt(1, QColor("#1E1F22"))
        p.fillPath(path, grad)

        # Subtle accent glow top-center
        glow = QLinearGradient(self.width()//2 - 100, 0, self.width()//2 + 100, 80)
        glow.setColorAt(0, QColor(62, 155, 255, 0))
        glow.setColorAt(0.5, QColor(62, 155, 255, 35))
        glow.setColorAt(1, QColor(62, 155, 255, 0))
        p.fillPath(path, glow)
        p.end()
