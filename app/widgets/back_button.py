"""Small back-navigation button shown in the top-left of the left panel.

Deliberately dumb: it just shows/hides itself and emits clicks (via the
inherited ``clicked`` signal). It has no idea what "back" means on any
given screen -- MainWindow decides that, since it's already the thing
orchestrating every screen transition. See MainWindow._set_back_action.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QToolButton, QWidget

from app.constants import BACK_BUTTON_SIZE


class BackButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("backButton")
        self.setFixedSize(BACK_BUTTON_SIZE, BACK_BUTTON_SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText("🢨")
        self.hide()  # MainWindow reveals this only when a back action is set