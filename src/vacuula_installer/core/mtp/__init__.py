from __future__ import annotations

from typing import Iterable

import usb.core
import usb.util

from .consts import *


class MTP_PACKET:
    def __init__(self, container_type=0, code=0, tx_id=0, payload=b''):
        self.container_type = container_type  # 2-byte
        self.code = code  # 2-bytes
        self.tx_id = tx_id  # 4-bytes
        self.payload = payload  # optional, arbitrary bytes

    @classmethod
    def parse(cls, raw_bytes):
        l = int.from_bytes(raw_bytes[0:4], 'little')
        container_type = int.from_bytes(raw_bytes[4:6], 'little')
        code = int.from_bytes(raw_bytes[6:8], 'little')
        tx_id = int.from_bytes(raw_bytes[8:12], 'little')
        payload = raw_bytes[12:]
        return cls(container_type, code, tx_id, payload)

    @property
    def length(self):
        return 4 + (2 + 2 + 4) + len(self.payload)

    def __bytes__(self):
        return (
                self.length.to_bytes(4, 'little')
                + self.container_type.to_bytes(2, 'little')
                + self.code.to_bytes(2, 'little')
                + self.tx_id.to_bytes(4, 'little')
                + self.payload
        )

    def __iter__(self):
        return iter(bytes(self))

    def __repr__(self):
        return f"MTP({self.container_type} {self.code} {self.tx_id} {self.payload})"


class MtpError(ValueError):
    pass


def find_mtp_bulk_endpoints(dev: usb.core.Device) -> tuple[usb.core.Endpoint, usb.core.Endpoint]:
    dev.reset()
    for interface in dev.get_active_configuration():
        if interface.bInterfaceClass != 6:  # PICTURE class (MTP is subclass of PTP)
            continue
        ep_in = ep_out = None
        for ep in interface:
            if usb.util.endpoint_type(ep.bmAttributes) == usb.util.ENDPOINT_TYPE_BULK:
                if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN:
                    ep_in = ep
                elif usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_OUT:
                    ep_out = ep
        if ep_in is not None and ep_out is not None:
            return ep_in, ep_out
    raise MtpError("Could not find MTP endpoints")

OBJECT_FILENAME_PROP = 0xDC07
ROOT_PARENT = 0xFFFFFFFF  # "root of the storage" in GetObjectHandles / parent in ObjectInfo

class MtpDevice:
    MAX_BUF = 4096

    def __init__(self, dev: usb.core.Device):
        self.ep_in, self.ep_out = find_mtp_bulk_endpoints(dev)
        dev.reset()
        self._tx_id = -1

    def _new_tx_id(self):
        self._tx_id += 1
        return self._tx_id

    def _write_pkt(self, pkt: MTP_PACKET):
        self.ep_out.write(pkt)

    def _read_pkt(self):
        return MTP_PACKET.parse(bytes(self.ep_in.read(self.MAX_BUF)))

    def _send_command(self, tx_id: int, code: int, args: Iterable[int]):
        pld = b''.join(arg.to_bytes(4, 'little', signed=arg < 0) for arg in args)
        self._write_pkt(MTP_PACKET(container_type=ContainerType.Command, code=code, tx_id=tx_id, payload=pld))

    def _send_data(self, tx_id: int, code: int, data: bytes):
        self._write_pkt(MTP_PACKET(container_type=ContainerType.Data, code=code, tx_id=tx_id, payload=data))

    def _read_data(self) -> bytes:
        data = self._read_pkt()
        if data.container_type != ContainerType.Data:
            raise MtpError(f"Expected Data, got {data.container_type}")
        return data.payload

    def _read_response(self) -> tuple[int]:
        resp = self._read_pkt()
        if resp.container_type != ContainerType.Response:
            raise MtpError(f"Expected Response, got {resp.container_type}")
        if resp.code != Response.OK:
            raise MtpError(f"Expected OK, got {resp.code}")
        n_params = len(resp.payload) // 4
        return tuple(int.from_bytes(resp.payload[i * 4:(i + 1) * 4], 'little') for i in range(n_params))

    def _tx_no_data(self, code: int, args: Iterable[int]) -> tuple:
        tx_id = self._new_tx_id()
        self._send_command(tx_id, code, args)
        return self._read_response()

    def _tx_data_out(self, code: int, args: Iterable[int], data: bytes) -> tuple:
        tx_id = self._new_tx_id()
        self._send_command(tx_id, code, args)
        self._send_data(tx_id, code, data)
        return self._read_response()

    def _tx_data_in(self, code: int, args: Iterable[int]) -> tuple[tuple, bytes]:
        tx_id = self._new_tx_id()
        self._send_command(tx_id, code, args)
        data = self._read_data()
        params = self._read_response()
        return params, data

    def open_session(self, session_id):
        self._tx_no_data(Operations.OpenSession, [session_id])

    def get_device_info(self):
        return self._tx_data_in(Operations.GetDeviceInfo, [])

    def get_storage_ids(self):
        _, ids_raw = self._tx_data_in(Operations.GetStorageIDs, [])
        n_ids = int.from_bytes(ids_raw[:4], 'little')
        return [int.from_bytes(ids_raw[4 + i * 4:4 + (i + 1) * 4], 'little') for i in range(n_ids)]

    def send_object_info(self, target_path: str, storage_id: int, parent_id: int = -1) -> int:
        object_info = bytes.fromhex(
            "01 00 ff ff"  # StorageID
            "00 00"  # Object Format
            "00 00      "  # Protection Status
            "00 00 00 00"  # Object Compressed Size
            "00 00      "  # Thumb Format
            "00 00 00 00"  # Thumb Compressed Size
            "00 00 00 00"  # Thumb Pix Width
            "00 00 00 00"  # Thumb Pix Height
            "00 00 00 00"  # Image Pix Width
            "00 00 00 00"  # Image Pix Height
            "00 00 00 00"  # Image Bit Depth
            "ff ff ff ff"  # Parent Object, 0xffffffff = root object
            "00 00      "  # Association Type
            "00 00 00 00"  # Association Description
            "00 00 00 00"  # Sequence Number
        ) + (len(target_path) + 1).to_bytes(1, 'little') + target_path.encode('utf-16-le') + bytes.fromhex(
            "00 00"  # null-terminator of actual filename
            "00"  # Date Created
            "00"  # Date Modified
            "00"  # Keywords
        )
        ids = self._tx_data_out(Operations.SendObjectInfo, [storage_id, parent_id], object_info)
        storage_id, parent_handle, newfile_handle = ids
        return newfile_handle

    def send_object(self, file_data: bytes):
        self._tx_data_out(Operations.SendObject, [], file_data)

    def set_object_prop_value(self, filehandle: int, prop: int, new_value: bytes):
        self._tx_data_out(Operations.SetObjectPropValue, [filehandle, prop], new_value)

    def send_file(self, target_path: str, storage_id: int, file_data: bytes):
        staging_path = f"./../../{target_path}.swu"
        file_handle = self.send_object_info(staging_path, storage_id)
        self.send_object(file_data)
        final_path = f"./../../{target_path}"
        payload = (len(final_path) + 1).to_bytes(1, 'little') + final_path.encode('utf-16-le') + bytes.fromhex(
            "00 00"  # null-terminator of actual filename
        )
        self.set_object_prop_value(file_handle, 0xDC07, payload)

    def get_object_handles(self, storage_id: int, parent_id: int = ROOT_PARENT) -> list[int]:
            """Children of `parent_id` on `storage_id` (ROOT_PARENT lists the top level)."""
            _, raw = self._tx_data_in(Operations.GetObjectHandles, [storage_id, 0, parent_id])
            n = int.from_bytes(raw[:4], 'little')
            return [int.from_bytes(raw[4 + i * 4:4 + (i + 1) * 4], 'little') for i in range(n)]

    def get_object_filename(self, handle: int) -> str:
        _, raw = self._tx_data_in(
            Operations.GetObjectPropValue, [handle, OBJECT_FILENAME_PROP]
        )
        # MTP string prop: 1-byte char count, then UTF-16LE, incl. null terminator
        n_chars = raw[0]
        return raw[1:1 + n_chars * 2].decode('utf-16-le').rstrip('\x00')

    def get_object(self, handle: int) -> bytes:
        """Read a file's full contents by object handle."""
        _, data = self._tx_data_in(Operations.GetObject, [handle])
        return data

    def find_object(self, storage_id: int, path_parts: Iterable[str], parent_id: int = ROOT_PARENT) -> int | None:
        """Resolve e.g. ['SW Update', 'version.txt'] to an object handle."""
        parent = parent_id
        for part in path_parts:
            for handle in self.get_object_handles(storage_id, parent):
                if self.get_object_filename(handle) == part:
                    parent = handle
                    break
            else:
                return None
        return parent

    def read_file(self, storage_id: int, path_parts: Iterable[str]) -> bytes | None:
        handle = self.find_object(storage_id, path_parts)
        if handle is None:
            return None
        return self.get_object(handle)
    
    def dump_tree(self, storage_id: int, parent_id: int = ROOT_PARENT, prefix: str = "") -> None:
        for handle in self.get_object_handles(storage_id, parent_id):
            try:
                name = self.get_object_filename(handle)
            except MtpError as e:
                print(f"{prefix}[{handle:#010x}] <error: {e}>")
                continue
            print(f"{prefix}[{handle:#010x}] {name}")
            self.dump_tree(storage_id, handle, prefix + "  ")
