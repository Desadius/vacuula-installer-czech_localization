"""A page for adding wifi credentials

Includes an overengineered spec-compliance with wifi SSID:s

TODO: A wifi core class that attempts to use the original robot selfdetection methods:
    gen 3: connect to its own wifi, get wifis it can see
    gen 4: some bluetooth same thing-allo?

    - The function should silently fail without disrupting user or flow if computer (this app) does not
    have wifi or bluetooth
    - But if it succeedes replace SSID field with a selection menu of what the robot sees, preferably elegantly
    filtering based on whats (pententially) already typed

"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget, QLineEdit

from app.constants import CONNECT_SVG, WIREFRAME_SIZE
from app.i18n import Translator
from app.widgets.ssid_input import SsidInput 
from app.widgets.width_tracking_label import WidthTrackingLabel


class WifiScreen(QWidget):
    """Emits :attr:`wifiAdded` with SSID, password"""

    wifiAdded = Signal(str, str)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator

        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 26)
        outer.setSpacing(18)
        self._central_stack = QStackedLayout()
        outer.addLayout(self._central_stack, 1)

        self._wifipage = self._build_wifi_page()
        self._central_stack.addWidget(self._wifipage)
        self._translator.languageChanged.connect(self._retranslate)
        self._retranslate()


    def _build_wifi_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        # We go manual with this one
        layout.setSpacing(0)

        self._wifi_title_label = WidthTrackingLabel(page)
        self._wifi_title_label.setObjectName("serversearchTitleLabel")
        self._wifi_title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._wifi_title_label.setWordWrap(True)

        self._wifi_conn_expl = QLabel(page)
        self._wifi_conn_expl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._wifi_conn_expl.setWordWrap(True)
        self._wifi_conn_expl.setObjectName("wifiExplanationLabel")


        self._ssid_field_label = QLabel(page)
        self._ssid_field_label.setObjectName("serversearchBodyLabel")
        self._ssid_field_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._ssid_input = SsidInput(page)
        self._ssid_input.setFixedWidth(350)
        self._ssid_input.textChanged.connect(self._update_wifi_continue_enabled)
        self._ssid_input.returnPressed.connect(self._ssid_input.focusNextChild)

        self._password_field_label = QLabel(page)
        self._password_field_label.setObjectName("serversearchBodyLabel")
        self._password_field_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self._password_input = QLineEdit(page)
        self._password_input.setObjectName("wifiInput")
        self._password_input.setFixedWidth(350)
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.returnPressed.connect(self._handle_wifi_continue_clicked)

        self._wifi_disclaimer = QLabel(page)
        self._wifi_disclaimer.setObjectName("serversearchDetailLabel")
        self._wifi_disclaimer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._wifi_disclaimer.setWordWrap(True)

        self._wifi_continue_button = QPushButton(page)
        self._wifi_continue_button.setObjectName("continueButton")
        self._wifi_continue_button.setEnabled(False)
        self._wifi_continue_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._wifi_continue_button.clicked.connect(self._handle_wifi_continue_clicked)

        layout.addWidget(self._wifi_title_label)
        layout.addSpacing(24)
        layout.addWidget(self._wifi_conn_expl)
        layout.addSpacing(24)
        layout.addWidget(self._ssid_field_label)
        layout.addSpacing(2) 
        layout.addWidget(self._ssid_input, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)
        layout.addWidget(self._password_field_label)
        layout.addSpacing(2)
        layout.addWidget(self._password_input, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(24)
        layout.addWidget(self._wifi_disclaimer)
        layout.addSpacing(30)
        layout.addWidget(self._wifi_continue_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        return page

    # Just trigger on back navigation to fix valid input not allowing continue
    def wifi_revalidate_input(self) -> None:
        self._update_wifi_continue_enabled()
 
    def _update_wifi_continue_enabled(self) -> None:
        self._wifi_continue_button.setEnabled(self._ssid_input.is_valid())
 
    def _handle_wifi_continue_clicked(self) -> None:
        if not self._ssid_input.is_valid():
            return
        ssid = self._ssid_input.toPlainText()  # not stripped -- whitespace is valid SSID content
        password = self._password_input.text()
        self._wifi_continue_button.setEnabled(False)
        self.wifiAdded.emit(ssid, password)


    def _retranslate(self) -> None:
        self._wifi_title_label.setText(self._translator.tr("wifi.title"))
        self._ssid_field_label.setText(self._translator.tr("wifi.ssid.title"))
        self._wifi_continue_button.setText(self._translator.tr("wifi.button"))
        self._password_field_label.setText(self._translator.tr("wifi.pass.title"))
        self._wifi_disclaimer.setText(self._translator.tr("wifi.disclaimer"))
        self._wifi_conn_expl.setText(self._translator.tr("wifi.explanation"))
        