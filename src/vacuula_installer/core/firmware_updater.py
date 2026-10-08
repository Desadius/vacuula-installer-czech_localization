from __future__ import annotations

import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

import httpx
import usb.core  # type: ignore[reportMissingTypeStubs]
from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class FirmwareAsset:
    filename: str
    asset_id: str | None = None   # GitHub release asset id (private API, current)
    url: str | None = None        # plain direct download link (future)


GITHUB_REPO = "vacuula/neato-firmware"
GITHUB_TOKEN = "" # temp

FIRMWARE_ASSETS: dict[str, FirmwareAsset] = {
    "gen4-1.7.0": FirmwareAsset("Neato_1.7.0-2933.swu", asset_id="623052647"),
    "gen3-4.5.3": FirmwareAsset("Neato_4.5.3_189.tgz", asset_id="623054653"),
    "gen3-4.6.0": FirmwareAsset("Neato_4.6.0_72.tgz", asset_id="623054703"),
}

GEN23_TARGET_FIRMWARE = "gen3-4.5.3"
GEN4_TARGET_FIRMWARE = "gen4-1.7.0"

DOWNLOAD_TIMEOUT_S = 60.0
CHUNK_SIZE = 64 * 1024


def _resolve_download(asset: FirmwareAsset) -> tuple[str, dict[str, str]]:
    """(url, headers) to request `asset` with -- hides whether it's coming
    from the private GitHub API or a plain public link."""
    if asset.url is not None:
        return asset.url, {}
    if asset.asset_id is not None:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/assets/{asset.asset_id}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/octet-stream",
        }
        return url, headers
    raise ValueError(f"Firmware asset {asset.filename!r} has neither url nor asset_id set")


def firmware_cache_dir() -> Path:
    path = Path(tempfile.gettempdir()) / "vacuula_firmware"
    path.mkdir(parents=True, exist_ok=True)
    return path


# -- updater ------------------------------------------------------------------------


class FirmwareUpdater(QObject):
    downloadProgress = Signal(str, int)     # key, percent 0-100 (-1 if unknown total)
    downloadFinished = Signal(str, str)     # key, local file path
    downloadFailed = Signal(str, str)       # key, reason

    _progress = Signal(str, int)            # worker thread -> GUI thread
    _done = Signal(str, object)             # key, path on success | None on failure
    _failed = Signal(str, str)              # key, reason

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._active_downloads: dict[str, threading.Event] = {}

        self._progress.connect(self.downloadProgress)
        self._done.connect(self._on_download_done)
        self._failed.connect(self._on_download_failed)

    # -- downloading --------------------------------------------------------------

    def download_firmware(self, key: str) -> None:
        asset = FIRMWARE_ASSETS.get(key)
        if asset is None:
            self._failed.emit(key, "Unknown firmware")
            return

        stop_event = threading.Event()
        self._active_downloads[key] = stop_event
        threading.Thread(
            target=self._download_worker, args=(key, asset, stop_event), daemon=True
        ).start()

    def cancel_download(self, key: str) -> None:
        stop_event = self._active_downloads.get(key)
        if stop_event is not None:
            stop_event.set()

    def _download_worker(self, key: str, asset: FirmwareAsset, stop_event: threading.Event) -> None:
        dest = firmware_cache_dir() / asset.filename
        try:
            url, headers = _resolve_download(asset)
        except ValueError as e:
            self._failed.emit(key, str(e))
            return

        try:
            with httpx.stream(
                "GET", url, headers=headers, follow_redirects=True, timeout=DOWNLOAD_TIMEOUT_S
            ) as response:
                if not response.is_success:
                    self._failed.emit(key, f"HTTP {response.status_code}")
                    return
                total = int(response.headers.get("content-length", 0))
                received = 0
                last_reported = -1

                tmp_path = dest.with_suffix(dest.suffix + ".part")
                with open(tmp_path, "wb") as f:
                    for chunk in response.iter_bytes(CHUNK_SIZE):
                        if stop_event.is_set():
                            self._failed.emit(key, "Cancelled")
                            return
                        f.write(chunk)
                        received += len(chunk)
                        percent = int(received * 100 / total) if total > 0 else -1
                        if percent != last_reported:
                            last_reported = percent
                            self._progress.emit(key, percent)
                tmp_path.replace(dest)
        except (httpx.HTTPError, OSError) as e:
            self._failed.emit(key, str(e))
            return

        self._done.emit(key, str(dest))

    def _on_download_done(self, key: str, path: object) -> None:
        self._active_downloads.pop(key, None)
        self.downloadFinished.emit(key, str(path))

    def _on_download_failed(self, key: str, reason: str) -> None:
        self._active_downloads.pop(key, None)
        self.downloadFailed.emit(key, reason)

    # -- update flows (not implemented yet) ----------------------------------------

    def start_gen23_update(self, device: usb.core.Device, firmware_key: str = GEN23_TARGET_FIRMWARE) -> None:
        pass

    def start_gen4_update(self, device: usb.core.Device, firmware_key: str = GEN4_TARGET_FIRMWARE) -> None:
        pass