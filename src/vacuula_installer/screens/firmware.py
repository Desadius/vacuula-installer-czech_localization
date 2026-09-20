from PySide6.QtCore import Signal
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QPushButton, QStackedLayout, QVBoxLayout, QWidget

from vacuula_installer.i18n import Translator
from vacuula_installer.widgets.background_flair import BackgroundFlairWidget


class FirmwareScreen(QWidget):
    """Emits :attr:`flashFirmware` when user wants to flash firmware."""

    flashFirmware = Signal()

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator

        layers = QStackedLayout(self)
        layers.setStackingMode(QStackedLayout.StackingMode.StackAll)

        self._flair = BackgroundFlairWidget(self)
        layers.addWidget(self._flair)

        foreground = QWidget(self)
        foreground.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        fg_layout = QVBoxLayout(foreground)
        fg_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fg_layout.setSpacing(16)

        self._firmware_button = QPushButton(foreground)
        self._firmware_button.setObjectName("flashButton")
        self._firmware_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._firmware_button.clicked.connect(self.flashFirmware)
        self._firmware_button.setText(translator.tr("firmware.flash"))

        fg_layout.addStretch(1)
        fg_layout.addSpacing(10)
        fg_layout.addWidget(
            self._firmware_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        fg_layout.addStretch(1)

        layers.addWidget(foreground)
