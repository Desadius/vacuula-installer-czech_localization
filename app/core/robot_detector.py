"""Robot detection.
Multiple robots not allowed
Can be used to detect disconnection, care about polling rate
"""
from __future__ import annotations

from enum import IntEnum, auto
import usb.core

from PySide6.QtCore import QObject, QTimer, Signal

VENDOR_ID = 0x1D6B
GEN4_ID = 0x0100

class State(IntEnum):
    NONE = 0
    ONE = auto()
    MULTIPLE = auto()

class RobotDetector(QObject):
    """Fires :attr:`robotDetected` once, a fixed delay after :meth:`start`."""

    robotDisconnected = Signal()
    robotDetected = Signal(str, str, usb.core.Device)  # display_name, serial, device

    # Probably never happens but needs to be handled:
    multipleRobotsDetected = Signal()


    def __init__(self, parent: QObject | None = None, lastState = State.NONE) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._update_robots)
        self._last_state = State(lastState)

    def start(self, delay_ms: int) -> None:
        """Begin polling; emits ``robotDetected`` after ``delay_ms``."""
        self._timer.start(delay_ms)

    def stop(self) -> None:
        """Cancel a pending detection, e.g. if the user navigates away."""
        self._timer.stop()

    def _update_robots(self):
        devices = list(usb.core.find(find_all=True, idVendor=VENDOR_ID, idProduct=GEN4_ID))

        if len(devices) == 0:
            if self._last_state == State.ONE:
                self.robotDisconnected.emit()
            self._last_state = State.NONE

        elif len(devices) == 1:
            name, serial = self._get_name_and_serial(devices[0])
            self.robotDetected.emit(name, serial, devices[0])
            self._last_state = State.ONE

        else:
            if self._last_state != State.MULTIPLE:
                self.multipleRobotsDetected.emit()
            self._last_state = State.MULTIPLE

    @staticmethod
    def _get_name_and_serial(dev: usb.core.Device) -> tuple[str, str]:
        try:
            return (f"{dev.manufacturer} {dev.product}", f"{dev.serial_number}")
        except ValueError:
            return (repr(dev), "")