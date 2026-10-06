"""Server detector

    Server detector uses zeroconf python package that should be cross,
    compatible with all OS.
    
    If a IP is returned it will fetch the cert from the server.

If a IP is returned it will fetch the cert from the server.

If both succeed the information is sent as signals, main_windows saves it
in the session.

NOTE: Does NOT support self-signed certs if server, proxy or w/e redirects to https!
For that we would have to a. disable verification or b. use same selfsigned on all
server deployments and preprogram its public part here - none are desirable.
"""

from __future__ import annotations
import logging, requests, threading
from PySide6.QtCore import QObject, QTimer, Signal, QRunnable, QThreadPool, Slot
from zeroconf import Zeroconf, ServiceBrowser, ServiceInfo, ServiceListener
from vacuula_installer.constants import M_DNS_SERVICE_TYPE

logger = logging.getLogger(__name__)


class _DetectionWorkerSignals(QObject):
    found = Signal(str, str)  # ip, cert
    not_found = Signal()


class _ServiceListener(ServiceListener):
    """Receives mDNS service discovery results."""

    def __init__(self) -> None:
        self.info: ServiceInfo | None = None
        self.event = threading.Event()

    def add_service(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
    ) -> None:
        info = zeroconf.get_service_info(
            service_type,
            name,
            timeout=1000,
        )

        if info is not None:
            self.info = info
            self.event.set()

    def update_service(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
    ) -> None:
        # A service can be updated after initially appearing.
        info = zeroconf.get_service_info(
            service_type,
            name,
            timeout=1000,
        )

        if info is not None:
            self.info = info
            self.event.set()

    def remove_service(
        self,
        zeroconf: Zeroconf,
        service_type: str,
        name: str,
    ) -> None:
        pass


class _DetectionWorker(QRunnable):
    """Blocking mDNS resolution + HTTP cert fetch, dont run on GUI thread
    mDNS takes aages.."""

    def __init__(self) -> None:
        super().__init__()
        self.signals = _DetectionWorkerSignals()

    @Slot()
    def run(self) -> None:
        info = self._discover_vacuula()

        if info is None:
            self.signals.not_found.emit()
            return

        addresses = info.parsed_addresses()

        if not addresses:
            logger.warning("Vacuula service found but has no addresses")
            self.signals.not_found.emit()
            return

        # Prefer IPv4.
        ip = next(
            (addr for addr in addresses if ":" not in addr),
            addresses[0],
        )

        # DNS-SD TXT records are bytes -> bytes.
        properties = {
            self._decode_property(key): self._decode_property(value)
            for key, value in info.properties.items()
        }

        cert_path = properties.get("cert-path")

        if not cert_path:
            logger.warning(
                "Vacuula service found but has no cert-path property"
            )
            self.signals.not_found.emit()
            return

        port = info.port

        url = f"http://{ip}:{port}{cert_path}"

        logger.debug(
            "Vacuula server discovered at %s",
            url,
        )

        try:
            response = requests.get(
                url,
                timeout=3,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.warning(
                "Resolved host but failed to fetch cert", exc_info=False
            )  # exc_info is incredibly verbose
            # self.signals.not_found.emit()

            # TODO: temp detection:
            self.signals.found.emit(ip, "Bananer är goda 1 2 3")

            return

        self.signals.found.emit(ip, response.text)

    @staticmethod
    def _discover_vacuula() -> ServiceInfo | None:
        zeroconf = Zeroconf()
        listener = _ServiceListener()

        browser = ServiceBrowser(
            zeroconf,
            M_DNS_SERVICE_TYPE,
            listener,
        )

        try:
            # Wait until a service is discovered or timeout expires.
            listener.event.wait(3.0)
            return listener.info
        finally:
            # Stop browsing and release the mDNS socket.
            browser.cancel()
            zeroconf.close()

    @staticmethod
    def _decode_property(value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")

        return value



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
