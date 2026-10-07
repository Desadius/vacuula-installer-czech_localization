"""Minimal MTP client over pyusb - just enough to read one file."""
from __future__ import annotations

import struct

import usb.core  # type: ignore[reportMissingTypeStubs]
import usb.util  # type: ignore[reportMissingTypeStubs]

# Container types
_CMD, _DATA, _RESP = 1, 2, 3
# Operations
_OPEN_SESSION = 0x1002
_CLOSE_SESSION = 0x1003
_GET_STORAGE_IDS = 0x1004
_GET_OBJECT_HANDLES = 0x1007
_GET_OBJECT_INFO = 0x1008
_GET_OBJECT = 0x1009
_RESP_OK = 0x2001

_ROOT = 0xFFFFFFFF
_TIMEOUT_MS = 3000


class MtpError(Exception):
    pass


class MtpDevice:
    def __init__(self, dev: usb.core.Device) -> None:
        self._dev = dev
        self._tid = 0
        self._buf = b""
        self._iface_num = -1
        self._ep_in = None
        self._ep_out = None

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "MtpDevice":
        self._claim()
        self._transaction(_OPEN_SESSION, [1])
        return self

    def __exit__(self, *exc) -> None:
        try:
            self._transaction(_CLOSE_SESSION, [])
        except Exception:
            pass
        try:
            usb.util.release_interface(self._dev, self._iface_num)
            usb.util.dispose_resources(self._dev)
        except Exception:
            pass

    def _claim(self) -> None:
        cfg = self._dev.get_active_configuration()
        iface = None
        for i in cfg:
            # Still-image class (PTP/MTP) or vendor-specific with 3 endpoints
            if i.bInterfaceClass == 0x06 or (i.bInterfaceClass == 0xFF and i.bNumEndpoints >= 3):
                iface = i
                break
        if iface is None:
            raise MtpError("No MTP interface found")
        self._iface_num = iface.bInterfaceNumber
        try:
            if self._dev.is_kernel_driver_active(self._iface_num):
                self._dev.detach_kernel_driver(self._iface_num)
        except (NotImplementedError, usb.core.USBError):
            pass  # Windows/macOS: not applicable
        usb.util.claim_interface(self._dev, self._iface_num)

        def is_bulk(d, direction):
            return (usb.util.endpoint_direction(d.bEndpointAddress) == direction
                    and usb.util.endpoint_type(d.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK)

        self._ep_in = usb.util.find_descriptor(iface, custom_match=lambda e: is_bulk(e, usb.util.ENDPOINT_IN))
        self._ep_out = usb.util.find_descriptor(iface, custom_match=lambda e: is_bulk(e, usb.util.ENDPOINT_OUT))
        if self._ep_in is None or self._ep_out is None:
            raise MtpError("Bulk endpoints not found")

    # -- wire protocol -----------------------------------------------------
    def _send_cmd(self, code: int, params: list[int]) -> int:
        self._tid += 1
        payload = struct.pack(f"<{len(params)}I", *params)
        header = struct.pack("<IHHI", 12 + len(payload), _CMD, code, self._tid)
        self._ep_out.write(header + payload, _TIMEOUT_MS)
        return self._tid

    def _recv_container(self) -> tuple[int, int, bytes]:
        while len(self._buf) < 12:
            self._buf += bytes(self._ep_in.read(65536, _TIMEOUT_MS))
        length = struct.unpack_from("<I", self._buf)[0]
        while len(self._buf) < length:
            self._buf += bytes(self._ep_in.read(65536, _TIMEOUT_MS))
        packet, self._buf = self._buf[:length], self._buf[length:]
        _, ctype, code, _ = struct.unpack_from("<IHHI", packet)
        return ctype, code, packet[12:]

    def _transaction(self, code: int, params: list[int]) -> bytes:
        """Run one operation; returns the data phase (b'' if none)."""
        self._send_cmd(code, params)
        data = b""
        while True:
            ctype, rcode, payload = self._recv_container()
            if ctype == _DATA:
                data += payload
            elif ctype == _RESP:
                if rcode != _RESP_OK:
                    raise MtpError(f"MTP op {code:#06x} failed: {rcode:#06x}")
                return data

    # -- high level --------------------------------------------------------
    def _storage_ids(self) -> list[int]:
        data = self._transaction(_GET_STORAGE_IDS, [])
        n = struct.unpack_from("<I", data)[0]
        return list(struct.unpack_from(f"<{n}I", data, 4))

    def _children(self, storage: int, parent: int) -> list[int]:
        data = self._transaction(_GET_OBJECT_HANDLES, [storage, 0, parent])
        n = struct.unpack_from("<I", data)[0]
        return list(struct.unpack_from(f"<{n}I", data, 4))

    def _filename(self, handle: int) -> str:
        data = self._transaction(_GET_OBJECT_INFO, [handle])
        # Fixed part of ObjectInfo is 52 bytes, then PTP string (len byte + UTF-16LE)
        n = data[52]
        return data[53:53 + n * 2].decode("utf-16le").rstrip("\x00")

    def read_file(self, path: list[str]) -> bytes | None:
        """Read e.g. ['SW Update', 'version.txt'] from whichever storage has it."""
        print(f"Looking for path {'/'.join(path)}")
        for storage in self._storage_ids():
            print(f"Checking storage {storage:#010x} for path {'/'.join(path)}")
            parent, found = _ROOT, True
            for part in path:
                for h in self._children(storage, parent):
                    if self._filename(h) == part:
                        parent = h
                        break
                else:
                    found = False
                    break
            if found:
                return self._transaction(_GET_OBJECT, [parent])
        return None