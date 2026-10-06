from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from vacuula_installer.i18n import Translator
from vacuula_installer.widgets.spinner import SpinnerWidget


class FirmwareScreen(QWidget):
    """Emits :attr:`flashFirmware` when user wants to flash firmware."""

    flashFirmware = Signal()

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator

        layers = QStackedLayout(self)
        layers.setStackingMode(QStackedLayout.StackingMode.StackAll)

        screen = QWidget(self)
        screen.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(screen)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.setSpacing(16)

        self._firmware_button = QPushButton(screen)
        self._firmware_button.setObjectName("flashButton")
        self._firmware_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._firmware_button.clicked.connect(self.flashFirmware)
        self._firmware_button.setText(translator.tr("firmware.flash"))

        outer.addStretch(1)
        outer.addSpacing(10)
        outer.addWidget(self._firmware_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        outer.addStretch(1)

        layers.addWidget(screen)

        outer.addLayout(self._build_status_row())
        self._spinner.start()
        self._status_label.setText(self._translator.tr("firmware.scan"))

    def _build_status_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch(1)

        self._status_label = QLabel(self)
        self._status_label.setObjectName("statusLabel")
        self._spinner = SpinnerWidget(self, diameter=16)

        row.addWidget(self._status_label)
        row.addWidget(self._spinner)
        row.addStretch(1)
        return row
