"""
Before starting robot hacking biting or w/e a server needs to be set up.
This screen just shows feedback if a vacuula-server.local has been
detected, no iteraction except TODO: make "here" a link that opens browser (i dunno how)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QHBoxLayout, QVBoxLayout, QWidget, QStackedLayout
from app.widgets.spinner import SpinnerWidget
from app.i18n import Translator
from PySide6.QtSvgWidgets import QSvgWidget

from app.constants import COMPUTER_SVG, SERVER_SVG

class FindVaaculaServer(QWidget):

    startFindServerRequested = Signal(str)

    """Simple informational screen shown while locating a Vaacula server."""

    def __init__(self, translator: Translator, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._translator = translator
        self._server_ip: str | None = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 40, 1, 26)
        outer.setSpacing(18)

        self._central_stack = QStackedLayout()
        outer.addLayout(self._central_stack, 1)

        self._info_page = self._build_info_page()
        self._central_stack.addWidget(self._info_page)

        outer.addLayout(self._build_status_row())

        self._translator.languageChanged.connect(self._retranslate)
        self._retranslate()
        self.reset_searching()

    def _build_info_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(24)


        self._title_label = QLabel(page)
        self._title_label.setObjectName("serversearchTitleLabel")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._title_label.setWordWrap(True)

        self._body_label = QLabel(page)
        self._body_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._body_label.setWordWrap(True)

        self._icon_row = self._build_icon_row(page)

        self._detailinfo_label = QLabel(page)
        self._detailinfo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._detailinfo_label.setWordWrap(True)

        layout.addWidget(self._title_label)
        layout.addWidget(self._body_label)
        layout.addWidget(self._icon_row)
        layout.addWidget(self._detailinfo_label)
        return page

    def _build_icon_row(self, parent: QWidget) -> QWidget:
        container = QWidget(parent)
        row = QHBoxLayout(container)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)

        computer = QSvgWidget(str(COMPUTER_SVG), parent)
        computer.setFixedSize(100, 100)

        dots_left = QLabel("•   •   •", parent)
        dots_left.setObjectName("serverSearchDOTS")
        dots_left.setAlignment(Qt.AlignmentFlag.AlignCenter)

        x_mark = QLabel("✕", parent)
        x_mark.setObjectName("serverSearchCROSS")
        x_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        dots_right = QLabel("•   •   •", parent)
        dots_right.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dots_right.setObjectName("serverSearchDOTS")

        server = QSvgWidget(str(SERVER_SVG), parent)
        server.setFixedSize(100, 100)

        row.addWidget(computer)
        row.addWidget(dots_left)
        row.addWidget(x_mark)
        row.addWidget(dots_right)
        row.addWidget(server)

        return container

    def reset_searching(self) -> None:
        self._server_ip = None
        self._central_stack.setCurrentWidget(self._info_page)
        self._status_label.setText(self._translator.tr("serversearch.status.searching"))
        self._spinner.start()

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

    def _retranslate(self) -> None:
        self._title_label.setText(self._translator.tr("serversearch.title"))
        self._body_label.setText(self._translator.tr("serversearch.body"))
        self._detailinfo_label.setText(self._translator.tr("serversearch.detailinfo"))

        if self._server_ip is None:
            self._status_label.setText(self._translator.tr("serversearch.status.searching"))
        else:
             self._status_label.setText(self._translator.tr("serversearch.status.found", ip=self._server_ip))
