from __future__ import annotations
import sys

if sys.platform != "win32":
    raise ImportError("This module is only supported on Windows")

import ctypes
import functools
import os
import winreg
from ctypes import POINTER, c_ubyte, c_uint64, c_ushort, c_void_p, cast, pointer
from types import SimpleNamespace
from typing import Iterable

import comtypes
import comtypes.client
from comtypes import GUID

from . import MtpDevice, MtpError
from .consts import Response

DEBUG = True

# TODO: this is very rudamentory and llm made, however it works and will be good enough for initial release. 

def _dbg(*args) -> None:
    if DEBUG:
        print("[winmtp]", *args, flush=True)


# --------------------------------------------------------------------------
# constants
# --------------------------------------------------------------------------

# Set by the robot firmware (same for every gen4 unit).
GEN4_VID_PID = "VID_1D6B&PID_0100"

# Everything below is a fixed Windows SDK value (PortableDevice*.h).
GUID_DEVINTERFACE_WPD = "{6ac27878-a6fa-4155-ba85-f98f491d4f33}"

# WPD_CATEGORY_MTP_EXT_VENDOR_OPERATIONS (commands and properties share it)
_MTP_EXT = GUID("{4D545058-1A2E-4106-A357-771E0819FC56}")
_CMD_NO_DATA = 12      # EXECUTE_COMMAND_WITHOUT_DATA_PHASE
_CMD_DATA_READ = 13    # EXECUTE_COMMAND_WITH_DATA_TO_READ
_CMD_DATA_WRITE = 14   # EXECUTE_COMMAND_WITH_DATA_TO_WRITE
_CMD_READ_DATA = 15
_CMD_WRITE_DATA = 16
_CMD_END_TRANSFER = 17

_P_OPCODE = 1001
_P_OPPARAMS = 1002
_P_RESPONSE_CODE = 1003
_P_RESPONSE_PARAMS = 1004
_P_CONTEXT = 1006
_P_TOTAL_SIZE = 1007
_P_BYTES_TO_READ = 1008
_P_BYTES_READ = 1009
_P_BYTES_TO_WRITE = 1010
_P_BYTES_WRITTEN = 1011
_P_DATA = 1012
_P_OPTIMAL_BUF = 1013

# WPD_PROPERTY_COMMON_*
_COMMON = GUID("{F0422A9C-5DC8-4440-B5BD-5DF28835658A}")
_P_COMMAND_CATEGORY = 1001
_P_COMMAND_ID = 1002
_P_HRESULT = 1003

# WPD_CLIENT_*
_CLIENT = GUID("{204D9F0C-2292-4080-9F42-40664E70F859}")
_C_NAME, _C_MAJOR, _C_MINOR, _C_REVISION = 2, 3, 4, 5
_C_SECURITY_QOS, _C_DESIRED_ACCESS = 8, 9
SECURITY_IMPERSONATION = 0x20000
GENERIC_READ_WRITE = 0xC0000000

VT_UI4 = 19
UNKNOWN_SIZE = 0xFFFFFFFF

# Our own tuning
DEFAULT_CHUNK = 64 * 1024
MAX_CHUNK = 1024 * 1024


# --------------------------------------------------------------------------
# COM plumbing
# --------------------------------------------------------------------------

class _PV(ctypes.Structure):
    """Minimal PROPVARIANT view (VT_UI4 only), same layout as the real one:
    8-byte header, then the value union (16 bytes on 64-bit)."""
    _fields_ = [
        ("vt", c_ushort), ("r1", c_ushort), ("r2", c_ushort), ("r3", c_ushort),
        ("val", c_uint64),
    ] + ([("pad", c_uint64)] if ctypes.sizeof(c_void_p) == 8 else [])


_ole32 = ctypes.windll.ole32
_ole32.CoTaskMemFree.argtypes = [c_void_p]
_ole32.PropVariantClear.argtypes = [c_void_p]

_wpd: SimpleNamespace | None = None


def _load() -> SimpleNamespace:
    """Load the WPD type libraries once (comtypes generates wrappers)."""
    global _wpd
    if _wpd is None:
        sysdir = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")
        try:
            api = comtypes.client.GetModule(os.path.join(sysdir, "PortableDeviceApi.dll"))
            types = comtypes.client.GetModule(os.path.join(sysdir, "PortableDeviceTypes.dll"))
        except (OSError, comtypes.COMError) as e:
            raise MtpError(f"Could not load the WPD type libraries: {e!r}") from e
        _wpd = SimpleNamespace(api=api, types=types)
    return _wpd


@functools.cache
def _classes(name: str) -> tuple:
    """Both typelibs generate their own copy of some structs (PROPERTYKEY,
    PROPVARIANT), and objects coming back from the driver may expect either.
    Preferred (PortableDeviceTypes) copy first."""
    w = _load()
    out: list = []
    for mod in (w.types, w.api):
        cls = getattr(mod, name, None)
        if cls is not None and cls not in out:
            out.append(cls)
    if not out:
        raise MtpError(f"WPD type {name!r} not found in the generated comtypes modules")
    return tuple(out)


@functools.cache
def _key_as(cls, fmtid: str, pid: int):
    key = cls()
    key.fmtid = GUID(fmtid)
    key.pid = pid
    return key


def _k(guid: GUID, pid: int):
    """PROPERTYKEY in the preferred typelib's class."""
    return _key_as(_classes("_tagpropertykey")[0], str(guid), pid)


class _Results:
    """Wraps an IPortableDeviceValues returned by SendCommand. It may come from
    the other typelib copy, so retry each call with each PROPERTYKEY class."""

    def __init__(self, raw) -> None:
        self._raw = raw

    def __getattr__(self, name: str):
        method = getattr(self._raw, name)

        def call(key, *args):
            error: Exception | None = None
            for cls in _classes("_tagpropertykey"):
                k = key if isinstance(key, cls) else _key_as(cls, str(key.fmtid), key.pid)
                try:
                    return method(k, *args)
                except ctypes.ArgumentError as e:
                    error = e
            raise error  # type: ignore[misc]

        return call


def _hr(e: comtypes.COMError) -> str:
    return f"{e.args[0] & 0xFFFFFFFF:#010x}"


def _hex_args(args: Iterable[int]) -> list[str]:
    return [hex(a & 0xFFFFFFFF) for a in args]


def _new_values():
    w = _load()
    return comtypes.client.CreateObject(
        w.types.PortableDeviceValues, interface=w.types.IPortableDeviceValues
    )


def _make_collection(values: Iterable[int]):
    """IPortableDevicePropVariantCollection of VT_UI4 values. Masked to 32 bits,
    so -1 becomes 0xFFFFFFFF like the signed packing in the libusb transport."""
    w = _load()
    pv_cls = _classes("tag_inner_PROPVARIANT")[0]
    coll = comtypes.client.CreateObject(
        w.types.PortableDevicePropVariantCollection,
        interface=w.types.IPortableDevicePropVariantCollection,
    )
    for value in values:
        pv = _PV()
        pv.vt = VT_UI4
        pv.val = value & 0xFFFFFFFF
        coll.Add(cast(pointer(pv), POINTER(pv_cls)))
    return coll


def _read_collection(coll) -> tuple[int, ...]:
    """The typelib declares GetCount([in] DWORD*) and GetAt(DWORD,
    [in] PROPVARIANT*), so comtypes makes us pass the output buffers."""
    try:
        count = int(coll.GetCount())
    except TypeError:
        n = ctypes.c_ulong()
        coll.GetCount(ctypes.byref(n))
        count = n.value

    out = []
    for i in range(count):
        pv = _PV()
        error: Exception | None = None
        for cls in _classes("tag_inner_PROPVARIANT"):
            try:
                coll.GetAt(i, cast(pointer(pv), POINTER(cls)))
                error = None
                break
            except ctypes.ArgumentError as e:
                error = e
        if error is not None:
            raise error
        try:
            if pv.vt != VT_UI4:
                _dbg(f"  response param {i} has vt={pv.vt}, expected VT_UI4")
            out.append(int(pv.val) & 0xFFFFFFFF)
        finally:
            _ole32.PropVariantClear(ctypes.byref(pv))
    return tuple(out)


# --------------------------------------------------------------------------
# device lookup
# --------------------------------------------------------------------------

def _parent_id_prefix(serial: str) -> str | None:
    """Prefix shared by the instance IDs of all child interfaces of the
    composite USB device with this serial, e.g. ``6&12425a59&0``. Assigned by
    Windows per machine/port, so it's always looked up."""
    if not serial:
        return None
    key_path = rf"SYSTEM\CurrentControlSet\Enum\USB\{GEN4_VID_PID}\{serial}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return str(winreg.QueryValueEx(key, "ParentIdPrefix")[0]).lower()
    except OSError:
        return None


def _device_id_for(serial: str) -> str:
    """WPD PnP id of the robot's MTP interface (MI_00)."""
    prefix = _parent_id_prefix(serial)
    if prefix is None:
        raise MtpError(f"No ParentIdPrefix in the registry for serial {serial!r}")
    vid_pid = GEN4_VID_PID.lower()
    return rf"\\?\usb#{vid_pid}&mi_00#{prefix}&0000#{GUID_DEVINTERFACE_WPD}"


# --------------------------------------------------------------------------
# device
# --------------------------------------------------------------------------

class WindowsMtpDevice(MtpDevice):
    def __init__(self, serial: str, device_id: str | None = None) -> None:
        # Deliberately NOT calling MtpDevice.__init__: that one needs libusb.
        comtypes.CoInitialize()
        self._dev = None
        try:
            self._device_id = device_id or _device_id_for(serial)
            _dbg("device id:", self._device_id)
            self._dev = self._open(self._device_id)
        except BaseException:
            comtypes.CoUninitialize()
            raise

    @staticmethod
    def _open(device_id: str):
        w = _load()
        info = _new_values()
        info.SetStringValue(_k(_CLIENT, _C_NAME), "Vacuula Installer")
        info.SetUnsignedIntegerValue(_k(_CLIENT, _C_MAJOR), 1)
        info.SetUnsignedIntegerValue(_k(_CLIENT, _C_MINOR), 0)
        info.SetUnsignedIntegerValue(_k(_CLIENT, _C_REVISION), 0)
        info.SetUnsignedIntegerValue(_k(_CLIENT, _C_SECURITY_QOS), SECURITY_IMPERSONATION)
        info.SetUnsignedIntegerValue(_k(_CLIENT, _C_DESIRED_ACCESS), GENERIC_READ_WRITE)

        dev = comtypes.client.CreateObject(w.api.PortableDevice, interface=w.api.IPortableDevice)
        try:
            dev.Open(device_id, info)
        except comtypes.COMError as e:
            raise MtpError(f"Could not open WPD device {device_id!r}: {_hr(e)}") from e
        return dev

    def close(self) -> None:
        if self._dev is None:
            return
        try:
            self._dev.Close()
        except comtypes.COMError:
            pass
        finally:
            self._dev = None
            comtypes.CoUninitialize()

    def __enter__(self) -> "WindowsMtpDevice":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- low-level command plumbing ----------------------------------------

    @staticmethod
    def _command(pid: int, context: str | None = None):
        values = _new_values()
        values.SetGuidValue(_k(_COMMON, _P_COMMAND_CATEGORY), _MTP_EXT)
        values.SetUnsignedIntegerValue(_k(_COMMON, _P_COMMAND_ID), pid)
        if context is not None:
            values.SetStringValue(_k(_MTP_EXT, _P_CONTEXT), context)
        return values

    def _send(self, values) -> _Results:
        try:
            results = _Results(self._dev.SendCommand(0, values))
        except comtypes.COMError as e:
            raise MtpError(f"WPD SendCommand failed: {_hr(e)}") from e
        try:
            hr = int(results.GetErrorValue(_k(_COMMON, _P_HRESULT))) & 0xFFFFFFFF
        except comtypes.COMError:
            hr = 0
        if hr & 0x80000000:
            try:
                rc = int(results.GetUnsignedIntegerValue(_k(_MTP_EXT, _P_RESPONSE_CODE)))
                detail = f", robot answered {rc:#06x}"
            except comtypes.COMError:
                detail = ", command never reached the robot"
            raise MtpError(f"WPD driver returned HRESULT {hr:#010x}{detail}")
        return results

    def _begin(self, pid: int, opcode: int, args: list[int],
               total_size: int | None = None) -> _Results:
        values = self._command(pid)
        values.SetUnsignedIntegerValue(_k(_MTP_EXT, _P_OPCODE), opcode)
        values.SetIPortableDevicePropVariantCollectionValue(
            _k(_MTP_EXT, _P_OPPARAMS), _make_collection(args)
        )
        if total_size is not None:
            values.SetUnsignedLargeIntegerValue(_k(_MTP_EXT, _P_TOTAL_SIZE), total_size)
        return self._send(values)

    @staticmethod
    def _response(results: _Results, opcode: int) -> tuple[int, ...]:
        code = int(results.GetUnsignedIntegerValue(_k(_MTP_EXT, _P_RESPONSE_CODE)))
        try:
            params = _read_collection(
                results.GetIPortableDevicePropVariantCollectionValue(
                    _k(_MTP_EXT, _P_RESPONSE_PARAMS)
                )
            )
        except comtypes.COMError:
            params = ()
        _dbg(f"op {opcode:#06x} -> response {code:#06x} params={_hex_args(params)}")
        if code != Response.OK:
            raise MtpError(f"MTP op {opcode:#06x} failed: response code {code:#06x}")
        return params

    def _end_transfer(self, context: str, opcode: int) -> tuple[int, ...]:
        return self._response(self._send(self._command(_CMD_END_TRANSFER, context)), opcode)

    def _abort(self, context: str, opcode: int) -> None:
        """Best-effort END_TRANSFER after a failed data phase."""
        try:
            self._end_transfer(context, opcode)
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _chunk_size(results: _Results) -> int:
        try:
            size = int(results.GetUnsignedIntegerValue(_k(_MTP_EXT, _P_OPTIMAL_BUF)))
        except comtypes.COMError:
            size = DEFAULT_CHUNK
        return max(4096, min(size or DEFAULT_CHUNK, MAX_CHUNK))

    def _write_chunk(self, context: str, part: bytes) -> int:
        values = self._command(_CMD_WRITE_DATA, context)
        values.SetUnsignedIntegerValue(_k(_MTP_EXT, _P_BYTES_TO_WRITE), len(part))
        buf = (c_ubyte * len(part)).from_buffer_copy(part)
        values.SetBufferValue(_k(_MTP_EXT, _P_DATA), buf, len(part))
        return int(self._send(values).GetUnsignedIntegerValue(_k(_MTP_EXT, _P_BYTES_WRITTEN)))

    def _read_chunk(self, context: str, want: int) -> bytes:
        values = self._command(_CMD_READ_DATA, context)
        values.SetUnsignedIntegerValue(_k(_MTP_EXT, _P_BYTES_TO_READ), want)
        buf = (c_ubyte * want)()
        values.SetBufferValue(_k(_MTP_EXT, _P_DATA), buf, want)

        res = self._send(values)
        n = int(res.GetUnsignedIntegerValue(_k(_MTP_EXT, _P_BYTES_READ)))
        if n <= 0:
            return b""
        out = res.GetBufferValue(_k(_MTP_EXT, _P_DATA))
        addr = cast(out[0] if isinstance(out, tuple) else out, c_void_p).value
        try:
            return ctypes.string_at(addr, n)
        finally:
            _ole32.CoTaskMemFree(addr)  # driver allocates with CoTaskMemAlloc

    # --- MtpDevice transport overrides ---------------------------------------

    def open_session(self, session_id) -> None:
        pass  # Windows already opened the MTP session

    def _tx_no_data(self, code: int, args: Iterable[int]) -> tuple:
        args = list(args)
        _dbg(f"op {code:#06x} args={_hex_args(args)} (no data)")
        return self._response(self._begin(_CMD_NO_DATA, code, args), code)

    def _tx_data_out(self, code: int, args: Iterable[int], data: bytes) -> tuple:
        args = list(args)
        _dbg(f"op {code:#06x} args={_hex_args(args)} data out: {len(data)} bytes")
        results = self._begin(_CMD_DATA_WRITE, code, args, total_size=len(data))
        context = results.GetStringValue(_k(_MTP_EXT, _P_CONTEXT))
        chunk = self._chunk_size(results)

        try:
            sent = 0
            while sent < len(data):
                written = self._write_chunk(context, data[sent:sent + chunk])
                if written <= 0:
                    raise MtpError(f"WPD wrote 0 bytes at offset {sent}")
                sent += written
        except Exception:
            self._abort(context, code)
            raise
        return self._end_transfer(context, code)

    def _tx_data_in(self, code: int, args: Iterable[int]) -> tuple[tuple, bytes]:
        args = list(args)
        _dbg(f"op {code:#06x} args={_hex_args(args)} (data in)")
        results = self._begin(_CMD_DATA_READ, code, args)
        total = int(results.GetUnsignedLargeIntegerValue(_k(_MTP_EXT, _P_TOTAL_SIZE)))
        context = results.GetStringValue(_k(_MTP_EXT, _P_CONTEXT))
        chunk = self._chunk_size(results)
        # The driver reports 0 when it doesn't know the size up front, so 0 is
        # treated like "unknown" and read until a short chunk.
        unknown = total == 0 or total >= UNKNOWN_SIZE

        parts: list[bytes] = []
        got = 0
        try:
            while unknown or got < total:
                want = chunk if unknown else min(chunk, total - got)
                try:
                    part = self._read_chunk(context, want)
                except MtpError:
                    if total == 0 and got == 0:
                        break  # genuinely no data phase
                    raise
                parts.append(part)
                got += len(part)
                if not part or (unknown and len(part) < want):
                    break
        except Exception:
            self._abort(context, code)
            raise

        params = self._end_transfer(context, code)
        _dbg(f"  received {got} bytes")
        return params, b"".join(parts)