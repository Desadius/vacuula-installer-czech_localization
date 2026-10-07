#!/usr/bin/env python3
"""
neato_blast.py -- generated using claude based on blast protocol
Requires: pyserial
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
import time

try:
    import serial 
except ImportError:
    serial = None



REQ = 0x05   # robot is ready to receive the blast
ACK = 0x06   # block accepted / upload accepted
NAK = 0x15   # upload rejected

BAUD = 115200

ONESHOT_CHUNK = 1024      # SendFile()      write granularity
ONESHOT_DELAY = 0.003     # SendFile()      Sleep(3) between writes

ACK_CHUNK = 512           # SendFileBlocks() write granularity
ACK_BLOCK = 16 * 1024     # SendFileBlocks() bytes between ACKs
ACK_RETRIES = 5           # tries before giving up on an ACK
ACK_RETRY_DELAY = 1.0     # Sleep(1000) between tries

READ_WINDOW = 0.1         # Serial::Read() drains RX for ~100 ms
REQ_POLLS = 15            # Upload() polls 15 times for REQ
FINAL_TIMEOUT = 10.0      # GetTickCount() delta of 0x2710 after the blast
NO_HANDSHAKE_DELAY = 5.0  # Sleep(5000) when -k is used

UPLOAD_TYPES = ("code", "sound", "LDS", "Metadata", "Package",
                "Tarball", "Image", "mainboard")


def blast_checksum(data: bytes) -> int:
    """32-bit wrapping sum of every byte. Sent little-endian after the file."""
    return sum(data) & 0xFFFFFFFF


def patch_app_size(data: bytes, app_size: int) -> bytes:
    """Overwrite bytes [20:24] with app_size as LE uint32.

    Mirrors SendFileBlocks() at 0x0042055E. The binary raises
    "Error - cannot replace application size at byte 20" if the first
    read came back shorter than 24 bytes.
    """
    if len(data) < 24:
        raise ValueError("cannot replace application size at byte 20: "
                         "file is shorter than 24 bytes")
    return data[:20] + struct.pack("<I", app_size) + data[24:]


class NeatoRobot:
    """Serial link to the robot's debug terminal."""

    def __init__(self, port: str, baud: int = BAUD, verbose: bool = True):
        if serial is None:
            raise RuntimeError("pyserial is not installed (pip install pyserial)")
        self.verbose = verbose
        self.ser = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=0,          # non-blocking; we do our own timing windows
            write_timeout=None,
            rtscts=False,
            dsrdtr=False,
            xonxoff=False,
        )
        self.ser.dtr = True     # EscapeCommFunction(SETDTR) in Serial::Open()

    # -- plumbing ----------------------------------------------------------

    def close(self) -> None:
        self.ser.close()

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, flush=True)

    def send_command(self, command: str) -> None:
        """Send a terminal command. The trailing '\\n' is added here."""
        self._log(f"Command: {command}")
        self.ser.write(command.encode("ascii") + b"\n")
        self.ser.flush()

    def receive(self, window: float = READ_WINDOW) -> bytes:
        """Drain the RX buffer for `window` seconds and return what arrived.

        Serial::Read() loops on ReadFile() until 100 ms have elapsed, so a
        single "receive" in the original is a 100 ms scrape rather than a
        blocking read for a specific byte.
        """
        deadline = time.monotonic() + window
        out = bytearray()
        while time.monotonic() < deadline:
            n = self.ser.in_waiting
            if n:
                out += self.ser.read(n)
            else:
                time.sleep(0.002)
        return bytes(out)

    def wait_for(self, byte_value: int, polls: int,
                 window: float = READ_WINDOW,
                 gap: float = 0.0,
                 accumulate: bool = True) -> bytes:
        """Poll until `byte_value` shows up. Returns everything received.

        Raises TimeoutError once `polls` polls have gone by without it.
        """
        buf = bytearray()
        for _ in range(polls):
            chunk = self.receive(window)
            if accumulate:
                buf += chunk
            else:
                buf = bytearray(chunk)
            if byte_value in buf:
                return bytes(buf)
            if gap:
                time.sleep(gap)
        raise TimeoutError(
            f"timed out waiting for 0x{byte_value:02X}; "
            f"got {bytes(buf)!r}"
        )

    # -- the two BLAST variants -------------------------------------------

    def _blast_oneshot(self, data: bytes) -> None:
        """SendFile() @ 0x0041FF50 -- fire and forget."""
        total = len(data)
        blocks = (total + 1023) // 1024
        started = time.monotonic()
        sent = 0
        n = 0
        for off in range(0, total, ONESHOT_CHUNK):
            chunk = data[off:off + ONESHOT_CHUNK]
            self.ser.write(chunk)
            time.sleep(ONESHOT_DELAY)
            sent += len(chunk)
            n += 1
            elapsed = max(time.monotonic() - started, 1.0)
            self._log(
                f"{int(elapsed):-3d} sec - Sent block {n:5d}/{blocks:<5d} "
                f"-- {sent / 1000.0:5.1f} kB ({sent * 8 / elapsed / 1000.0:8.2f} kbps)"
            )
        self.ser.flush()

    def _blast_with_ack(self, data: bytes) -> None:
        """SendFileBlocks() @ 0x00420450 -- ACK after every 16 KiB."""
        total = len(data)
        off = 0
        remaining_in_block = ACK_BLOCK
        while off < total:
            take = min(ACK_CHUNK, remaining_in_block, total - off)
            self.ser.write(data[off:off + take])
            off += take
            remaining_in_block -= take

            if remaining_in_block == 0:
                self.ser.flush()
                self._log(f"Waiting for ACK during blast: {off}/{total}")
                self._await_block_ack()
                remaining_in_block = ACK_BLOCK
        self.ser.flush()

    def _await_block_ack(self) -> None:
        for attempt in range(ACK_RETRIES):
            resp = self.receive(READ_WINDOW)
            if ACK in resp:
                return
            time.sleep(ACK_RETRY_DELAY)
        raise TimeoutError(
            "Timeout waiting for ACK handshake during blast from robot")

    # -- the whole transaction --------------------------------------------

    def upload(self,
               path: str,
               kind: str = "code",
               reboot: bool = False,
               readflash: bool = False,
               noburn: bool = False,
               xmodem: bool = False,
               handshake: bool = True,
               blast_ack: bool = False,
               updatesw_verify: bool = False,
               has_mainboard_version: bool = True) -> bool:
        """Run one full upload. Returns True on ACK, False on NAK."""

        with open(path, "rb") as fh:
            data = fh.read()

        file_size = len(data)
        is_enc = path.lower().endswith(".enc")

        # Announced size includes the 4 checksum bytes.
        announced = file_size + 4
        if kind == "LDS" and not has_mainboard_version:
            announced = file_size

        # code/Tarball non-.enc: stamp the app size at offset 20.
        # Only SendFileBlocks() honours this in the original.
        replace_size = kind in ("code", "Tarball") and not is_enc
        if replace_size and blast_ack:
            data = patch_app_size(data, file_size)

        self._log(f"File         {path}")
        self._log(f"File size    {file_size}")
        self._log(f"Type         {kind}")

        # 1. the command line
        cmd = f"Upload {kind} "
        if xmodem:
            cmd += "xmodem "
        if reboot:
            cmd += "reboot "
        if readflash:
            cmd += "readflash "
        if not noburn:
            cmd += "burn "
        cmd += f"size {announced}"
        self.send_command(cmd)
        time.sleep(0.1)

        # 2. wait for REQ, or just pause if the handshake is off
        if handshake:
            pre = self.wait_for(REQ, REQ_POLLS)
            self._log(f"Receive before blast: {pre!r}")
        else:
            time.sleep(NO_HANDSHAKE_DELAY)

        # 3. blast
        if blast_ack:
            self._log(f"Using file blast with block size {ACK_BLOCK // 1024}k ...")
            self._blast_with_ack(data)
        else:
            self._log("Using one large file blast ...")
            self._blast_oneshot(data)

        # 4. trailing checksum
        checksum = blast_checksum(data)
        self.ser.write(struct.pack("<I", checksum))
        self.ser.flush()
        self._log(f"Size         - 0x{file_size:08X} {file_size}")
        self._log(f"Checksum     - 0x{checksum:08X}")
        self._log(f"Total sent   - 0x{file_size:08X} {file_size}")

        # 5. verdict
        if not handshake:
            self.send_command("")          # bare newline
            self._log("Upload sent to robot.")
            return True

        deadline = time.monotonic() + FINAL_TIMEOUT
        buf = bytearray()
        while time.monotonic() < deadline:
            buf += self.receive(READ_WINDOW)
            if ACK in buf:
                self._log("Upload completed OK.")
                ok = True
                break
            if NAK in buf:
                self._log("Robot Reported Upload failed.")
                return False
        else:
            raise TimeoutError("Timeout waiting for ACK/NAK handshake "
                               "character from robot after upload.")

        if ok and updatesw_verify:
            self.send_command("updatesw verify")
            self._log(f"Response: {self.receive(1.0)!r}")

        if reboot:
            self._log("Robot reboot requested ... "
                      "close serial port and wait 10 seconds ...")
            self.close()
            time.sleep(10)

        return True

def upload_file(
    port,
    file,
    type="code",
    reboot=False,
    updatesw_verify=False,
    no_handshake=False,
    noburn=False,
    readflash=False,
    blastack=False,
    no_mainboard_version=False,
    baud=BAUD,
    quiet=False,
):
    if not os.path.isfile(file):
        raise FileNotFoundError(f"no such file: {file}")

    robot = NeatoRobot(port, baud, verbose=not quiet)
    try:
        return robot.upload(
            file,
            kind=type,
            reboot=reboot,
            readflash=readflash,
            noburn=noburn,
            handshake=not no_handshake,
            blast_ack=blastack,
            updatesw_verify=updatesw_verify,
            has_mainboard_version=not no_mainboard_version,
        )
    finally:
        try:
            robot.close()
        except Exception:
            pass

# terminal app
def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Upload firmware to a Neato robot using the BLAST protocol."
    )
    p.add_argument("-p", "--port", required=True)
    p.add_argument("-f", "--file", required=True)
    p.add_argument("-t", "--type", default="code", choices=UPLOAD_TYPES)
    p.add_argument("-r", "--reboot", action="store_true")
    p.add_argument("-u", "--updatesw-verify", action="store_true")
    p.add_argument("-k", "--no-handshake", action="store_true")
    p.add_argument("--noburn", action="store_true")
    p.add_argument("--readflash", action="store_true")
    p.add_argument("--blastack", action="store_true")
    p.add_argument("--no-mainboard-version", action="store_true")
    p.add_argument("-b", "--baud", type=int, default=BAUD)
    p.add_argument("-q", "--quiet", action="store_true")
    args = p.parse_args(argv)

    try:
        ok = upload_file(
            port=args.port,
            file=args.file,
            type=args.type,
            reboot=args.reboot,
            updatesw_verify=args.updatesw_verify,
            no_handshake=args.no_handshake,
            noburn=args.noburn,
            readflash=args.readflash,
            blastack=args.blastack,
            no_mainboard_version=args.no_mainboard_version,
            baud=args.baud,
            quiet=args.quiet,
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 2

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())