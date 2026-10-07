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

VALID_GEN4_VERSIONS = [
    ("1.7.0", "Firmware version: 1.7.0-2933"),
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
        try:
            mtp = MtpDevice(device)
            mtp.open_session(1)
            storage_id = mtp.get_storage_ids()[0]
            raw_version_data = mtp.read_file(storage_id, ["version.txt"])
        except Exception as e:
            print(f"Error connecting to gen4 robot: {e}")  # TODO: show error
            return

        if raw_version_data is None:
            self.firmwareDetected.emit(False, "Could not read version.txt from robot")
            return
        
        version_data = raw_version_data.decode("utf-8", errors="ignore")

        for version, version_search in VALID_GEN4_VERSIONS:
            if version_search in version_data:
                self.firmwareDetected.emit(True, version)
                return
        
        self.firmwareDetected.emit(False, "Invalid firmware")
