"""Generic error screen.

Any part of the app can route here when something unrecoverable happens
(a core worker failing, a device disappearing mid-flow, etc). There's no
per-error "retry this one step" logic -- the only way out is restarting
the whole wizard from the welcome screen, since by the time something
has gone wrong we can't trust assumptions the later screens made about
device/session state.

Usage from MainWindow:
    self._error_screen.show_error("some.translation.key")          # translated
    self._error_screen.show_error("Raw message", translate=False)  # shown as-is

    # with a detailed row, translated as "some.translation.key.detailed"
    self._error_screen.show_error("some.translation.key", detailed=True)

    self._error_screen.restartRequested.connect(self._handle_restart)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from vacuula_installer.i18n import Translator


class ErrorScreen(QWidget):
    """Emits :attr:`restartRequested` when the user chooses to start over."""

    restartRequested = Signal()

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._message_key: str | None = None   # set when the message should be re-translated
        self._detailed: bool | str = False           # whether a ".detailed" row is shown

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 40, 20, 26)
        outer.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        outer.setSpacing(16)

        self._icon_label = QLabel("⚠", self)
        self._icon_label.setObjectName("errorIconLabel")
        self._icon_label.setStyleSheet(
            "font-size: 45px;"
        )
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # self._title_label = QLabel(self)
        # self._title_label.setObjectName("serversearchTitleLabel")
        # self._title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        # self._title_label.setWordWrap(True)

        self._detail_label = QLabel(self)
        self._detail_label.setObjectName("serversearchBodyLabel")
        self._detail_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._detail_label.setWordWrap(True)

        self._detailed_label = QLabel(self)
        self._detailed_label.setObjectName("serversearchDetailLabel")
        self._detailed_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._detailed_label.setWordWrap(True)
        self._detailed_label.setOpenExternalLinks(True)
        self._detailed_label.hide()

        self._restart_button = QPushButton(self)
        self._restart_button.setObjectName("continueButton")
        self._restart_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._restart_button.clicked.connect(self.restartRequested)

        outer.addWidget(self._icon_label)
        # outer.addWidget(self._title_label)
        outer.addWidget(self._detail_label)
        outer.addWidget(self._detailed_label)
        outer.addSpacing(14)
        outer.addWidget(self._restart_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._translator.languageChanged.connect(self._retranslate)
        self._retranslate()

    def show_error(self, message_key: str, *, detailed: bool | str = False) -> None:
        """Set the detail text. `message` is a translation key by default
        (re-applied on language change); pass `translate=False` for text
        that's already final, e.g. something a device returned.

        `detailed` adds a second row, translated as `f"{message}.detailed"`.
        Only meaningful together with `translate=True` -- a raw, untranslated
        message has no key to derive a ".detailed" key from.
        """
        self._message_key = message_key
        self._detailed = detailed
        self._detail_label.setText(self._translator.tr(self._message_key))
        self._update_detailed_label()

    def _update_detailed_label(self) -> None:
        if self._detailed and isinstance(self._detailed, str):
            self._detailed_label.setText(self._translator.tr(self._detailed))
            self._detailed_label.show()
        elif self._detailed:
            self._detailed_label.setText(self._translator.tr(f"{self._message_key}.detailed"))
            self._detailed_label.show()
        else:
            self._detailed_label.clear()
            self._detailed_label.hide()

    def _retranslate(self) -> None:
        # self._title_label.setText(self._translator.tr("error.title"))
        self._restart_button.setText(self._translator.tr("error.restart"))
        if self._message_key is not None:
            self._message_text = self._translator.tr(self._message_key)
            self._detail_label.setText(self._message_text)
        self._update_detailed_label()