"""The Vaacula logo badge. Just adds ✨flair✨
"""
from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

from app.constants import LOGO_SVG
from app.theme import PALETTE


class LogoWidget(QSvgWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(str(LOGO_SVG), parent)
        self._apply_glow()

    def _apply_glow(self) -> None:
        glow = QGraphicsDropShadowEffect(self)
        glow.setBlurRadius(48)
        glow.setOffset(0, 0)
        glow.setColor(QColor(PALETTE.accent_blue))
        self.setGraphicsEffect(glow)
