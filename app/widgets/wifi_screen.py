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

from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtWidgets import QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget, QLineEdit, QComboBox

from app.i18n import Translator
from app.widgets.ssid_input import SsidInput 
from app.widgets.width_tracking_label import WidthTrackingLabel


class WifiScreen(QWidget):
    """Emits :attr:`wifiAdded` with SSID, password"""

    wifiAdded = Signal(str, str)

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._title_width = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 40, 20, 26)
        outer.setSpacing(18)
        self._central_stack = QStackedLayout()
        outer.addLayout(self._central_stack, 1)

        self._wifipage = self._build_wifi_page()
        self._gen23_wifi_page = self._build_gen23_wifi_page()
        self._central_stack.addWidget(self._wifipage)
        self._central_stack.addWidget(self._gen23_wifi_page)
        self._translator.languageChanged.connect(self._retranslate)
        self._retranslate()

    def _build_gen23_wifi_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setSpacing(0)

        self._wifi_title_labelGen23 = WidthTrackingLabel(page)
        self._wifi_title_labelGen23.setObjectName("serversearchTitleLabel")
        self._wifi_title_labelGen23.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._wifi_title_labelGen23.setWordWrap(True)

        self._wifi_conn_explGen23 = QLabel(page)
        self._wifi_conn_explGen23.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._wifi_conn_explGen23.setWordWrap(True)
        self._wifi_conn_explGen23.setObjectName("wifiExplanationLabel")

        self._wifi_combo_boxGen23 = QComboBox(page)
        self._wifi_combo_boxGen23.setObjectName("wifiInput")
        self._wifi_combo_boxGen23.setFixedWidth(350)
        self._wifi_combo_boxGen23.addItems(["Apple", "Banana", "Cherry", "Date"]) #TODO temp

        layout.addWidget(self._wifi_title_labelGen23)
        layout.addWidget(self._wifi_conn_explGen23)
        layout.addWidget(self._wifi_combo_boxGen23)

        return page


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
        self._password_input.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
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

    def _apply_label_margins(self) -> None:
        available = self._wifi_title_labelGen23.width()
        if self._title_width <= available:
            content_width = self._title_width
        else:
            # Title needs to wrap. Word wrap breaks on whole words, so its
            # widest wrapped line will be narrower than `available` - using
            # `available` here would let body/detail wrap wider than the
            # title actually renders, the opposite of the intent.
            content_width = self._wrapped_title_width(available)
        extra = max(0, available - content_width)
        left, right = extra // 2, extra - extra // 2
        for label in (self._wifi_title_labelGen23, self._wifi_combo_boxGen23, self._detailinfo_label):
            label.setContentsMargins(left, 0, right, 0)

    # Part of getting title textwidth as limit for other Qlabels
    def _wrapped_title_width(self, available: int) -> int:
        """Width of the title's widest line once wrapped to fit `available`."""
        fm = self._wifi_title_labelGen23.fontMetrics()
        rect = fm.boundingRect(
            QRect(0, 0, available, 32767),
            Qt.TextFlag.TextWordWrap,
            self._wifi_title_labelGen23.text(),
        )
        return rect.width()

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

    def set_gen23_page(self) -> None:
        self._central_stack.setCurrentWidget(self._gen23_wifi_page)


    def _retranslate(self) -> None:
        self._title_widthGen23 = self._wifi_title_labelGen23.sizeHint().width()

        self._wifi_title_label.setText(self._translator.tr("wifi.title"))
        self._ssid_field_label.setText(self._translator.tr("wifi.ssid.title"))
        self._wifi_continue_button.setText(self._translator.tr("wifi.button"))
        self._password_field_label.setText(self._translator.tr("wifi.pass.title"))
        self._wifi_disclaimer.setText(self._translator.tr("wifi.disclaimer"))
        self._wifi_conn_expl.setText(self._translator.tr("wifi.explanation"))

        self._wifi_title_labelGen23.setText(self._translator.tr("wifi.title"))
        self._wifi_conn_explGen23.setText(self._translator.tr("wifi.ssid.gen23.title"))

        self._wifi_continue_button.setText(self._translator.tr("wifi.button"))
        self._password_field_label.setText(self._translator.tr("wifi.pass.title"))
        self._wifi_disclaimer.setText(self._translator.tr("wifi.disclaimer"))
        self._wifi_conn_expl.setText(self._translator.tr("wifi.explanation"))
        