"""Backbutton, what it does is handled outside"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

from vacuula_installer.constants import BACK_BUTTON_SIZE


class BackButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("backButton")
        self.setFixedSize(BACK_BUTTON_SIZE, BACK_BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("🢨")
        self.hide()  # main_window.py reveals this only when being able to go back makes sense
