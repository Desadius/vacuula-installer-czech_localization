"""The data the wizard accumulates as the user moves through its screens.
Data used by installers, presense of data by main windows for skipping screens (TODO)
"""
from __future__ import annotations
from dataclasses import dataclass

import usb.core # type: ignore[reportMissingTypeStubs]

@dataclass
class SessionData:
    server_ip: str | None = None
    server_certificate: str | None = None

    robot_serial_nbr: str | None = None # Prob not used by scripts?
    robot_model_display_name: str | None = None
    robot_usb_device: usb.core.Device | None = None
    firmware_version: str | None = None # Not use, maybe not needed

    wifi_ssid: str | None = None
    wifi_pass: str | None = None

    # Some dev only goodies, for dev only screen (TODO)
    enable_ssh: bool = False #also means install dropbear
    ssh_pubkey: str | None = None
    ssh_disable_pw: bool = False
    set_root_pass: str | None = None #none means no