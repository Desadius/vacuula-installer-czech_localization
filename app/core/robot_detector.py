"""Robot detection.
Multiple robots not allowed
Can be used to detect disconnection, care about polling rate

Lots here was generated using claude sonnet, for example the cross platform serial stuff cause I could not bother
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum, auto

import serial  # type: ignore[reportMissingTypeStubs]
import serial.tools.list_ports  # type: ignore[reportMissingTypeStubs]
import usb.core  # type: ignore[reportMissingTypeStubs]
import usb.util  # type: ignore[reportMissingTypeStubs]

from PySide6.QtCore import QObject, QTimer, Signal

# idVendor, idProduct
GEN4_USB = [0x1D6B, 0x0100]
GEN23_USB = [0x2108, 0x780c]

SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT_S = 1.0
GET_VERSION_CMD = b"GetVersion\n"


@dataclass(frozen=True)
class RobotUsbId:
    usb_idVendor: int
    usb_idProduct: int
    display_name: str

    # Default values, as not all generations have a serial connection /
    # a known usb serial-number pattern respectively.
    usb_iSerial_part: str = ""
    usb_iSerial_part_pos: int = 0
    usb_iManufacturer: str = "Neato Robotics"
    usb_iProduct: str = "Neato Robot"
    serial_model: str = ""


ROBOT_IDS: tuple[RobotUsbId, ...] = (
    RobotUsbId(usb_idVendor=GEN4_USB[0], usb_idProduct=GEN4_USB[1], display_name="Neato D10", usb_iSerial_part="N2", usb_iSerial_part_pos=4),
    RobotUsbId(usb_idVendor=GEN4_USB[0], usb_idProduct=GEN4_USB[1], display_name="Neato D9", usb_iSerial_part="N1", usb_iSerial_part_pos=4),
    RobotUsbId(usb_idVendor=GEN4_USB[0], usb_idProduct=GEN4_USB[1], display_name="Neato D8", usb_iSerial_part="N3", usb_iSerial_part_pos=4),
    RobotUsbId(usb_idVendor=GEN4_USB[0], usb_idProduct=GEN4_USB[1], display_name="Neato D800", usb_iSerial_part="N5", usb_iSerial_part_pos=4), # presumed, source is: jk, image on the internet
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac D7", serial_model="BotVacD7Connected"),
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac D6", serial_model="BotVacD6Connected"),
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac D5", serial_model="BotVacD5Connected"),
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac D4", serial_model="BotVacD4Connected"),
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac D3", serial_model="BotVacD3Connected"),
    RobotUsbId(usb_idVendor=GEN23_USB[0], usb_idProduct=GEN23_USB[1], display_name="Neato Botvac Connected", serial_model="BotVacConnected"),
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
    robotDetected = Signal(str, usb.core.Device)  # display_name, device

    # Probably never happens but needs to be handled:
    multipleRobotsDetected = Signal()

    def __init__(self, parent: QObject | None = None, lastState: State = State.NONE) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._update_robots)
        self._last_state = State(lastState)
        # Keyed by (bus, address) of the physical USB device. Avoids
        # repeating the blocking "getVersion" serial round-trip on every
        # single poll once a GEN23_USB robot has already been identified.
        self._resolved_cache: dict[tuple[int, int], RobotUsbId] = {}

    def start(self, delay_ms: int) -> None:
        """Begin polling; emits ``robotDetected`` after ``delay_ms``."""
        self._timer.start(delay_ms)

    def stop(self) -> None:
        """Cancel a pending detection, e.g. if the user navigates away."""
        self._timer.stop()

    def _update_robots(self) -> None:
        # GEN4_USB and GEN23_USB entries share one (idVendor, idProduct)
        # pair each, so query USB once per unique pair rather than once
        # per ROBOT_IDS entry.
        ids_by_usb_id: dict[tuple[int, int], list[RobotUsbId]] = {}
        for robot_id in ROBOT_IDS:
            key = (robot_id.usb_idVendor, robot_id.usb_idProduct)
            ids_by_usb_id.setdefault(key, []).append(robot_id)

        resolved: list[tuple[usb.core.Device, RobotUsbId]] = []
        for (vendor, product), candidates in ids_by_usb_id.items():
            for dev in usb.core.find(find_all=True, idVendor=vendor, idProduct=product):
                descriptor_matches = [c for c in candidates if self._descriptor_matches(dev, c)]
                if not descriptor_matches:
                    continue
                robot_id = self._resolve_robot(dev, descriptor_matches)
                if robot_id is not None:
                    resolved.append((dev, robot_id))

        if len(resolved) == 0:
            if self._last_state == State.ONE:
                self.robotDisconnected.emit()
            self._last_state = State.NONE
            self._resolved_cache.clear()

        elif len(resolved) == 1:
            device, robot_id = resolved[0]
            if self._last_state != State.ONE:
                self.robotDetected.emit(robot_id.display_name, device)
            self._last_state = State.ONE

        else:
            if self._last_state != State.MULTIPLE:
                self.multipleRobotsDetected.emit()
            self._last_state = State.MULTIPLE

    @staticmethod
    def _descriptor_matches(dev: usb.core.Device, robot_id: RobotUsbId) -> bool:
        """idVendor/idProduct alone isn't unique enough - several Neato
        generations (and potentially unrelated devices) share the same
        pair - so also check the manufacturer/product string descriptors.
        """
        try:
            manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else None
            product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else None
        except (usb.core.USBError, ValueError, NotImplementedError):
            return False
        return manufacturer == robot_id.usb_iManufacturer and product == robot_id.usb_iProduct

    def _resolve_robot(self, dev: usb.core.Device, candidates: list[RobotUsbId]) -> RobotUsbId | None:
        """Given a physical device and the RobotUsbId entries whose
        idVendor/idProduct/iManufacturer/iProduct all matched it, work out
        exactly which model it is. Each USB id group has exactly one valid
        way to resolve it.
        """
        usb_id = [dev.idVendor, dev.idProduct]

        if usb_id == GEN4_USB:
            return self._match_by_usb_serial(dev, candidates)

        if usb_id == GEN23_USB:
            return self._match_by_get_version(dev, candidates)

        return None

    @staticmethod
    def _match_by_usb_serial(dev: usb.core.Device, candidates: list[RobotUsbId]) -> RobotUsbId | None:
        serial_number = RobotDetector._get_serial(dev)
        for candidate in candidates:
            start = candidate.usb_iSerial_part_pos
            end = start + len(candidate.usb_iSerial_part)
            if serial_number[start:end] == candidate.usb_iSerial_part:
                return candidate
        return None

    def _match_by_get_version(self, dev: usb.core.Device, candidates: list[RobotUsbId]) -> RobotUsbId | None:
        cache_key = (dev.bus, dev.address)
        cached = self._resolved_cache.get(cache_key)
        if cached in candidates:
            return cached

        version_output = self._query_get_version(dev)
        if version_output is None:
            return None
        for candidate in candidates:
            if candidate.serial_model in version_output:
                self._resolved_cache[cache_key] = candidate
                return candidate
        return None

    @staticmethod
    def _find_serial_port(dev: usb.core.Device, target_serial: str) -> str | None:
        """Resolve the OS-specific serial port name (``COM3`` on Windows,
        ``/dev/ttyACM0`` on Linux, ``/dev/cu.usbmodemXXXX`` on macOS) for a
        pyusb device. pyserial's ``list_ports`` enumerates each platform's
        ports uniformly and reports vid/pid/serial_number regardless of
        OS, which is what makes this lookup cross-platform.
        """
        vid_pid_matches = [
            port
            for port in serial.tools.list_ports.comports()
            if port.vid == dev.idVendor and port.pid == dev.idProduct
        ]
        if target_serial:
            for port in vid_pid_matches:
                if port.serial_number == target_serial:
                    return port.device
        # Fall back to a bare vid/pid match - only safe when exactly one
        # candidate port is present (e.g. serial number unreadable).
        if len(vid_pid_matches) == 1:
            return vid_pid_matches[0].device
        return None

    @staticmethod
    def _query_get_version(dev: usb.core.Device) -> str | None:
        target_serial = RobotDetector._get_serial(dev)
        port_name = RobotDetector._find_serial_port(dev, target_serial)
        if port_name is None:
            return None
        try:
            with serial.Serial(port_name, baudrate=SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT_S) as ser:
                ser.reset_input_buffer()
                ser.write(GET_VERSION_CMD)
                ser.flush()
                raw = ser.read(4096)
        except (serial.SerialException, OSError):
            return None
        return raw.decode("ascii", errors="ignore")

    @staticmethod
    def _get_serial(dev: usb.core.Device) -> str:
        try:
            serial_number = dev.serial_number
        except (usb.core.USBError, ValueError, NotImplementedError):
            return ""
        return serial_number or ""