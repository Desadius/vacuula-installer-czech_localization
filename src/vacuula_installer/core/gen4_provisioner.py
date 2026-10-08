from __future__ import annotations

import threading
from pathlib import Path
from textwrap import dedent

import usb.core  # type: ignore[reportMissingTypeStubs]
from PySide6.QtCore import QObject, Signal

from vacuula_installer.core.mtp import MtpDevice

VENDOR_ID = 0x1D6B
PRODUCT_ID = 0x0100

# install path -> local filename, inside scripts/gen4
FILES = {
    '/usr/sbin/enable_vacuula_shell.sh': 'enable_vacuula_shell.sh',
    '/usr/sbin/enable_vacuula_full.sh': 'enable_vacuula_full.sh',
    '/lib/systemd/system/usb-gadgets.service': 'usb-gadgets.service',
    '/etc/systemd/resolved.conf': 'resolved.conf',
    '/etc/systemd/network/wireless.network': 'wireless.network',
}


def device_description(dev: usb.core.Device) -> str:
    try:
        return f"{dev.product} ({dev.manufacturer}) {dev.serial_number}"
    except ValueError:
        return f"{dev!r}"


class Gen4Provisioner(QObject):
    """Pushes the vacuula install files to a Gen4 robot over MTP.
    Runs on a worker thread so the GUI doesn't freeze during the transfer."""

    stepChanged = Signal(int) # 1 connect, 2 upload
    provisioningFailed = Signal(str)
    provisioningFinished = Signal()

    _step = Signal(int)      # worker thread -> GUI thread
    _done = Signal(object)   # str | None -- failed stage, or None on success

    def __init__(
        self,
        vacuula_server: str,
        vacuula_cert: str | bytes,
        wifi_ssid: str | None = None,
        wifi_psk: str | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.vacuula_server = vacuula_server
        self.vacuula_cert = vacuula_cert.encode() if isinstance(vacuula_cert, str) else vacuula_cert
        self.wifi_ssid = wifi_ssid
        self.wifi_psk = wifi_psk
        self._active = False
        self._step.connect(self._on_step)
        self._done.connect(self._on_done)

    def start(self, dev: usb.core.Device) -> None:
        self._active = True
        threading.Thread(target=self._run, args=(dev,), daemon=True).start()

    def stop(self) -> None:
        self._active = False

    def _run(self, dev: usb.core.Device) -> None:
        self._step.emit(1)  # connecting
        try:
            mtp = MtpDevice(dev)
            mtp.open_session(1)
            storage_id = mtp.get_storage_ids()[0]
            data = mtp.read_file(storage_id, ["version.txt"])
            print(f"data: {data}", mtp.get_storage_ids())
        except Exception:
            self._done.emit("error.generic.connect")
            return

        self._step.emit(2)  # uploading
        try:
            self._install_static_files(mtp, storage_id)
            self._set_vacuula_server(mtp, storage_id)
            self._set_wifi(mtp, storage_id)
        except Exception:
            self._done.emit("error.generic.upload")
            return
        self._done.emit(None)

    def _install_static_files(self, mtp: MtpDevice, storage_id: int) -> None:
        # install static files
        for install_path, local_path in FILES.items():
            with open(Path("scripts/gen4") / local_path, 'rb') as f:
                mtp.send_file(install_path, storage_id, f.read())

    def _set_vacuula_server(self, mtp: MtpDevice, storage_id: int) -> None:
        # set server
        new_config = dedent(f"""\
            [N]
            host = {self.vacuula_server}
            port = 3443
            cacerts = config/ssl/vacuula.crt
            ntp = pool.ntp.org
            check_host = {self.vacuula_server}
            check_port = 80
            check_timeout = 10
            """).encode('utf-8')
        mtp.send_file('/home/root/tron/config/vendors.ini', storage_id, new_config)

        # install certificate
        mtp.send_file('/home/root/tron/config/ssl/vacuula.crt', storage_id, self.vacuula_cert)

    def _set_wifi(self, mtp: MtpDevice, storage_id: int) -> None:
        # update Wifi (optional)
        if self.wifi_ssid is None:
            return
        wifi_config = dedent(f"""\
            ctrl_interface=/var/run/wpa_supplicant
            ctrl_interface_group=0
            update_config=1
            network={{
                    ssid="{self.wifi_ssid}"
                    scan_ssid=1
                    psk="{self.wifi_psk}"
}}
            """).encode('utf-8')
        mtp.send_file('/etc/wpa_supplicant/wpa_supplicant-wlan0.conf', storage_id, wifi_config)

    def _on_step(self, step: int) -> None:
        if self._active:
            self.stepChanged.emit(step)

    def _on_done(self, failed_stage: str | None) -> None:
        if not self._active:
            return
        self._active = False
        if failed_stage is not None:
            self.provisioningFailed.emit(failed_stage)
        else:
            self.provisioningFinished.emit()