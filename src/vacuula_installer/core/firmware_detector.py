"""Reads the firmware version from a detected Gen4 robot over MTP."""
from __future__ import annotations

import threading

from vacuula_installer.core.mtp import MtpDevice, MtpError
import usb.core  # type: ignore[reportMissingTypeStubs]
from PySide6.QtCore import QObject, Signal

VERSION_PATH = ["SW Update", "version.txt"]

VALID_GEN3_VERSIONS = [
    ("4.5.3", "Software,4,5,3,189,0"),
]

class FirmwareDetector(QObject):
    firmwareDetected = Signal(bool, str) # true if valid firmware detected, false if not | str is either the version string or an error message

    # TODO: palceholder code to detect firmware!
    def detect(self, device: usb.core.Device, gen23_version: str | None) -> None:
        if gen23_version is not None:
            # we have an gen23 robot
            print(f"Detected Gen23 robot with firmware version: {gen23_version}")
            for version, version_search in VALID_GEN3_VERSIONS:
                if version_search in gen23_version:
                    self.firmwareDetected.emit(True, version)
                    return
        
        #gen4:
        self.firmwareDetected.emit(True, "1.7.0")
