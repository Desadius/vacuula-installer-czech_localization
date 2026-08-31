"""Second screen: ask the user to plug in the robot, presenting a last confirmation before
robot is rooted n stuff.

Has two internal pages to switch between, however TODO: a third for wifi should be added
"""
# TODO: Text explaining it is reversible might be fit for the "detected" page
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QStackedLayout, QVBoxLayout, QWidget

from app.constants import WIREFRAME_SIZE, WIREFRAME_SVG
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

        outer = QVBoxLayout(self)
        outer.setContentsMargins(48, 40, 48, 26)
        outer.setSpacing(18)

        self._central_stack = QStackedLayout()
        outer.addLayout(self._central_stack, 1)

        self._searching_page = self._build_searching_page()
        self._detected_page = self._build_detected_page()
        self._central_stack.addWidget(self._searching_page)
        self._central_stack.addWidget(self._detected_page)

        outer.addLayout(self._build_status_row())

        self._translator.languageChanged.connect(self._retranslate)
        self._retranslate()
        self.reset_searching()

    # -- page builders -----------------------------------------------------

    def _build_searching_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        layout.setSpacing(24)

        self._wireframe = QSvgWidget(str(WIREFRAME_SVG), page)
        self._wireframe.setFixedSize(*WIREFRAME_SIZE)

        self._instruction_label = QLabel(page)
        self._instruction_label.setObjectName("connectInstructionLabel")
        self._instruction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._instruction_label.setWordWrap(True)

        layout.addWidget(self._wireframe, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self._instruction_label)
        return page

    def _build_detected_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._start_install_button = QPushButton(page)
        self._start_install_button.setObjectName("goldButton")
        self._start_install_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_install_button.clicked.connect(self._handle_start_install_clicked)

        layout.addWidget(self._start_install_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        return page

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

    # -- public state transitions -------------------------------------------

    def reset_searching(self) -> None:
        """Go back to "no robot yet" -- e.g. when this screen is (re)shown."""
        self._model_id = None
        self._model_display_name = ""
        self._central_stack.setCurrentWidget(self._searching_page)
        self._status_label.setText(self._translator.tr("connect.status.waiting"))
        self._start_install_button.setEnabled(True)
        self._spinner.start()

    def show_robot_detected(self, model_id: str, display_name: str) -> None:
        """Swap in the golden install button for the given detected robot."""
        self._model_id = model_id
        self._model_display_name = display_name
        self._start_install_button.setText(self._translator.tr("connect.start_install"))
        self._status_label.setText(
            self._translator.tr("connect.status.detected", model=display_name)
        )
        self._spinner.stop()
        self._central_stack.setCurrentWidget(self._detected_page)

    # -- internal ------------------------------------------------------------

    def _handle_start_install_clicked(self) -> None:
        if self._model_id is None:
            return
        self._start_install_button.setEnabled(False)
        self._start_install_button.setText(self._translator.tr("connect.installing"))
        self._status_label.setText(
            self._translator.tr("install.launching", model=self._model_display_name)
        )
        self._spinner.start()
        self.startInstallRequested.emit(self._model_id)

    def _retranslate(self) -> None:
        self._instruction_label.setText(self._translator.tr("connect.title"))
        if self._model_id is None:
            self._status_label.setText(self._translator.tr("connect.status.waiting"))
            self._start_install_button.setText(self._translator.tr("connect.start_install"))
        else:
            self._status_label.setText(
                self._translator.tr("connect.status.detected", model=self._model_display_name)
            )
