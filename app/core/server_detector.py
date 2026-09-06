"""Server detector

    Server detector simply asks for vacuula-server.local (mDNS)
    using OS cabability, mac, most linux distros have supported this for ages,
    windows since some release of win 10: basically everything, allows us to
    not have to do a custom mDNS client...
    
    If a IP is returned it will fetch the cert from the server.

    If both succeed the information is sent as signals, main_windows saves it
    in the session.

    NOTE: Does NOT support self-signed certs if server, proxy or w/e redirects to https!
    For that we would have to a. disable verification or b. use same selfsigned on all 
    server deployments and preprogram its public part here - none are desirable.
"""

from __future__ import annotations
import logging, socket, requests
from PySide6.QtCore import QObject, QTimer, Signal, QRunnable, QThreadPool, Slot
from app.constants import M_DNS_HOSTNAME, PATH_TO_SERVER_CERT

logger = logging.getLogger(__name__)

class _DetectionWorkerSignals(QObject):
    found = Signal(str, str)  # ip, cert
    not_found = Signal()


class _DetectionWorker(QRunnable):
    """Blocking mDNS resolution + HTTP cert fetch, dont run on GUI thread
    mDNS takes aages.."""

    def __init__(self) -> None:
        super().__init__()
        self.signals = _DetectionWorkerSignals()

    @Slot()
    def run(self) -> None:
        ip = self._resolve_vacuula()
        if ip is None:
            self.signals.not_found.emit()
            return

        try:
            response = requests.get(
                f"http://{ip}{PATH_TO_SERVER_CERT}", # For https the server can redirect but it MUST have a public cert in that case!
                headers={"Host": M_DNS_HOSTNAME},
                timeout=3,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.warning("Resolved host but failed to fetch cert", exc_info=False) # exc_info is incredibly verbose
            #self.signals.not_found.emit()

            # TODO: temp detection:
            self.signals.found.emit(ip, "Bananer är goda 1 2 3")

            return

        self.signals.found.emit(ip, response.text)

    @staticmethod
    def _resolve_vacuula() -> str | None:
        try:
            addr_info = socket.getaddrinfo(
                M_DNS_HOSTNAME, None, socket.AF_UNSPEC, socket.SOCK_STREAM
            )
        except OSError:
            return None # For example no such mDNS record can be found

        for family, _type, _proto, _canonname, sockaddr in addr_info:
            if family in (socket.AF_INET, socket.AF_INET6):
                host = sockaddr[0]
                if isinstance(host, str):
                    return host
        return None

class ServerDetector(QObject):
    """Polls for M_DNS_HOSTNAME and emits its IP + cert once found."""

    serverDetected = Signal(str, str)  # ip, cert

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._detection_logic)
        self._pool = QThreadPool.globalInstance()
        self._busy = False
        self._active = False
        self._workers: list[_DetectionWorker] = []

    def start(self, delay_ms: int) -> None:
        self._active = True
        self._timer.start(delay_ms)

    def stop(self) -> None:
        self._active = False  # any in-flight worker result gets ignored
        self._timer.stop()  # Needed for back button

    def _detection_logic(self) -> None:
        if self._busy:
            return  # previous attempt still in flight; try again next tick

        self._busy = True
        worker = _DetectionWorker()
        self._workers.append(worker)  # keep a ref alive until it finishes
        worker.signals.found.connect(self._on_found)
        worker.signals.not_found.connect(self._on_not_found)
        self._pool.start(worker)

    def _on_found(self, ip: str, cert: str) -> None:
        self._busy = False
        self._workers.clear()
        if not self._active:
            return  # stop() was called while this was resolving
        self._timer.stop()
        self._active = False
        self.serverDetected.emit(ip, cert)

    def _on_not_found(self) -> None:
        self._busy = False
        self._workers.clear()