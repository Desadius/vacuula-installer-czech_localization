"""The data the wizard accumulates as the user moves through its screens.
Data used by installers, presense of data by main windows for skipping screens (TODO)
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SessionData:
    server_ip: str | None = None
    server_certificate: str | None = None
    robot_model_id: str | None = None
    robot_model_display_name: str | None = None
    firmware_version: str | None = None
    wifi_ssid: str | None = None
    wifi_pass: str | None = None

    # Some dev only goodies, for dev only screen (TODO)
    enable_ssh: bool = False #also means install dropbear
    ssh_pubkey: str | None = None
    ssh_disable_pw: bool = False
    set_root_pass: str | None = None #none means no