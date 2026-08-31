"""Placeholder for a server detector

    Server detector will simply send ask for vacuula-server.local (mDNS)
    and if a mDNS multicast is recieved it will obtain an ip and confirmation
    server exists.
"""
# TODO: make sure passed ip gets where its needed (install scripts)

from __future__ import annotations
import logging
from PySide6.QtCore import QObject, QTimer, Signal


class ServerDetector(QObject):

    serverSearchStarted = Signal() # använder jag ens denna?
    serverDetected = Signal(str)  # ip

    logger = logging.getLogger(__name__)


    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._simulate_detection)

    def start(self, delay_ms: int) -> None:
        # Placeholder - just a timer pretending to have detected server
        self.serverSearchStarted.emit()
        self._timer.start(delay_ms)

    def stop(self) -> None:
        # Needed if a back button is implemented
        self._timer.stop()

    def _simulate_detection(self) -> None:
        self.serverDetected.emit("127.0.0.1")
