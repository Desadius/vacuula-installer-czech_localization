from __future__ import annotations

from PySide6.QtCore import QObject, Signal
import usb
import tarfile
from pathlib import Path
from vacuula_installer.core.neato_blast import upload_file
from vacuula_installer.core.robot_detector import RobotDetector
import tempfile

from vacuula_installer.core.session import SessionData


def rc4_ksa(S, key):
    for i in range(256):
        S[i] = i

    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) & 0xFF
        S[i], S[j] = S[j], S[i]


def rc4_prga(S, length):
    out = [0] * length
    i = j = 0

    for k in range(length):
        i = (i + 1) & 0xFF
        j = (j + S[i]) & 0xFF
        S[i], S[j] = S[j], S[i]
        out[k] = S[(S[i] + S[j]) & 0xFF]

    return out


def string_to_bytes(s):
    return [ord(c) for c in s]


def byte_to_hex(b):
    return format(b, '02x')


def mac_to_skey(mac, key = "h6CX\t\t:<*{Y"):
    S = [0] * 256
    key_bytes = string_to_bytes(key)
    rc4_ksa(S, key_bytes)

    stream = rc4_prga(S, 256)
    mac_bytes = string_to_bytes(mac)

    result = ""
    for i in range(len(mac_bytes)):
        result += byte_to_hex(stream[i] ^ mac_bytes[i])

    extra_char = result[len(mac_bytes) >> 1]
    result += extra_char

    return result



def reset_network_cmd(mac: str):
    skey = mac_to_skey(mac)
    return f"SetWifi reset_network skey {skey}"

def getversion_cmd():
    return "GetVerion"



class Gen23WiFiFixer:
    gen23_wifiReset = Signal(str) #serial(mac), [available wifi network ssid:s]
    gen23_fwResetRequired = Signal() # triggers page showing fw reset progress
    gen23_fwResetFinished = Signal(bool) # sucessfull or not TODO

    def __init__(self, parent: QObject | None = None) -> None:
        print("förfann")

    def gen23_get_mac_from_version(self, get_version: str | None) -> str | None:
        if not get_version:
            return None
        serial = get_version.split("MainBoard Serial Number,")[1].split(",")[1].strip()
        if len(serial) == 12:
            return serial
        return None

    def fix_robot(self, device: usb.core.Device, mac: str, session: SessionData) -> None:
        if self._upload_scripts(device, session):
            print("Continuing with network reset after successful script upload.")
            self._reset_network(device, mac)

    def _reset_network(self, device: usb.core.Device, mac: str) -> None:
        cmd = reset_network_cmd(mac)
        RobotDetector.write_cmd(device, cmd)

    def _upload_scripts(self, device: usb.core.Device, session: SessionData) -> bool:
        target_serial = RobotDetector._get_serial(device)
        port = RobotDetector._find_serial_port(device, target_serial)

        with tempfile.TemporaryDirectory() as tmp:  # deleted when the block exits
            tarball = self._generate_tarball(Path(tmp), session)
            try:
                upload_file(port, str(tarball), "Tarball", noburn=True)
            except Exception as e:
                print(f"Error uploading scripts: {e}")  # TODO: show error
                return False

        print("Scripts uploaded successfully.")
        return True

    def _generate_tarball(self, tmp_dir: Path, session: SessionData) -> Path:
        tarball = tmp_dir / "vacuula.tar.gz"
        if not session.server_certificate or not session.server_ip:
            return tarball
        # cert
        cert_path = tmp_dir / "cert.pem"
        cert_path.write_bytes(session.server_certificate.encode())

        # additional info
        ip_to_use = f"vacuula-local-{session.server_ip.replace('.', '-')}.nip.io"
        ip_to_use_path = tmp_dir / "ip_to_use"
        ip_to_use_path.write_bytes(ip_to_use.encode())

        # make tarball
        tarball = tmp_dir / "vacuula.tar.gz"
        with tarfile.open(tarball, "w:gz") as tar:
            for p in Path("scripts/gen3").iterdir():
                tar.add(p, arcname=p.name)
            tar.add(cert_path, arcname="cert.pem")
            tar.add(ip_to_use_path, arcname="ip_to_use")
        return tarball