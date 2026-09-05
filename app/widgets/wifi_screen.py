from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget

from app.constants import CONNECT_SVG, WIREFRAME_SIZE
from app.i18n import Translator
from app.widgets.spinner import SpinnerWidget


class ConnectScreen(QWidget):
    """Emits :attr:`startInstallRequested` with the detected model id."""

    startInstallRequested = Signal(str)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._model_id: str | None = None
        self._model_display_name: str = ""