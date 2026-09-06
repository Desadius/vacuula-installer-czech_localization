"""Robot detection.
Multiple robots not allowed
Can be used to detect disconnection, care about polling rate
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum, auto
import usb.core # type: ignore[reportMissingTypeStubs]

from PySide6.QtCore import QObject, QTimer, Signal

@dataclass(frozen=True)
class RobotUsbId:
    vendor_id: int
    product_id: int
    display_name: str

# TODO: Refactor to find model name other way, there were only two vendor/product id combinations..
# TODO: Needs to differentiate between gen2 and 3, for example by connecting over serial on the same usb; baud 115200

ROBOT_IDS: tuple[RobotUsbId, ...] = (
    RobotUsbId(vendor_id=0x1D6B, product_id=0x0100, display_name="Gen 4"),
    RobotUsbId(vendor_id=0x2108, product_id=0x780c, display_name="Gen 2/3"),
)

class State(IntEnum):
    NONE = 0
    ONE = auto()
    MULTIPLE = auto()

class RobotDetector(QObject):
    """Fires
        :attr:`robotDetected` when robot is detected,
        :attr:`robotDisconnected` when robot looses connection,
        :attr:`multipleRobotsDetected` if more than one detected,
    Only firing on change of state
    If class is deconstructed it can be initialised with the expected state
    """

    robotDisconnected = Signal()
    robotDetected = Signal(str, str, usb.core.Device)  # display_name, serial, device

    # Probably never happens but needs to be handled:
    multipleRobotsDetected = Signal()


    def __init__(self, parent: QObject | None = None, lastState: State = State.NONE) -> None:
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
        matches: list[tuple[usb.core.Device, RobotUsbId]] = []
        for robot_id in ROBOT_IDS:
            found = usb.core.find(
                find_all=True, idVendor=robot_id.vendor_id, idProduct=robot_id.product_id
            )
            matches.extend((dev, robot_id) for dev in found) # Not sure this error actually is a problem

        if len(matches) == 0:
            if self._last_state == State.ONE:
                self.robotDisconnected.emit()
            self._last_state = State.NONE

        elif len(matches) == 1:
            device, robot_id = matches[0]
            self.robotDetected.emit(robot_id.display_name, self._get_serial(device), device)

        else:
            if self._last_state != State.MULTIPLE:
                self.multipleRobotsDetected.emit()
            self._last_state = State.MULTIPLE

    @staticmethod
    def _get_serial(dev: usb.core.Device) -> str:
        try:
            return f"{dev.serial_number}"
        except ValueError:
            return ""