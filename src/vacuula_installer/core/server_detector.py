"""Server detector

    Server detector uses zeroconf python package that should be cross,
    compatible with all OS.

If a IP is returned it will fetch the cert from the server.

If both succeed the information is sent as signals, main_windows saves it
in the session.

A server can also be checked manually (user-entered address) with
ServerDetector.check_manual(). It runs the exact same checks as mDNS
discovery and reports why it failed: "not_found" if nothing answered,
"incompatible" if something answered but isn't a (compatible) Vacuula server.

NOTE: Does NOT support self-signed certs if server, proxy or w/e redirects to https!
For that we would have to a. disable verification or b. use same selfsigned on all
server deployments and preprogram its public part here - none are desirable.

DEBUG: with MDNS_DEBUG = True everything mDNS/HTTP related is logged at
DEBUG level -- including zeroconf's and urllib3's own internal logs -- to
stderr AND to a file (path printed at startup), since the windowed Windows
build has no console.
"""

from __future__ import annotations

import itertools
import logging
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import requests
import zeroconf as zeroconf_pkg
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, Slot
from zeroconf import (
    DNSIncoming,
    ServiceBrowser,
    ServiceInfo,
    ServiceListener,
    Zeroconf,
    ZeroconfServiceTypes,
)

from vacuula_installer.constants import M_DNS_SERVICE_TYPE

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Debug switches
# ---------------------------------------------------------------------------
MDNS_DEBUG = True
# When our service isn't found, also list EVERY mDNS service type on the
# network. Tells you whether mDNS works at all from this machine (firewall,
# wrong adapter, VPN...) vs. the Vacuula server just not announcing. Slow
# (blocks the worker ~2 s), debug only.
MDNS_DEBUG_LIST_ALL_TYPES = True
MDNS_DEBUG_LIST_TYPES_TIMEOUT_S = 2.0
# How much of each HTTP response body to log.
HTTP_DEBUG_BODY_CHARS = 300

MDNS_DEBUG_LOG_FILE = Path(tempfile.gettempdir()) / "vacuula_mdns_debug.log"


class _Readable(str):
    """A string whose repr() is itself, so '%r' in a log format shows it
    as-is instead of quoted and escaped."""

    def __repr__(self) -> str:
        return str(self)


# Set while we parse a packet for display. zeroconf logs its own errors while
# parsing a bad packet; those logs would come back through the filter and
# trigger another parse, looping forever. While this is set, the filter drops
# them instead.
_parsing = threading.local()


def _render_dns_packet(data: bytes) -> str | None:
    """Parse a raw mDNS packet into readable questions/records, or None if
    it isn't one."""
    if len(data) < 12:  # smaller than a DNS header
        return None
    _parsing.active = True
    try:
        msg = DNSIncoming(data)
    except Exception:  # noqa: BLE001
        return None
    finally:
        _parsing.active = False
    if not getattr(msg, "valid", True):
        return None

    answers = getattr(msg, "answers", [])
    if callable(answers):  # a method in newer zeroconf, a list in older
        answers = answers()

    is_response = getattr(msg, "is_response", None)
    kind = "response" if callable(is_response) and is_response() else "query"
    lines = [f"DNS {kind} id={getattr(msg, 'id', '?')} flags=0x{getattr(msg, 'flags', 0):04x}"]
    for question in getattr(msg, "questions", []):
        lines.append(f"      Q  {question}")
    for record in answers:
        lines.append(f"      A  {record}")
    return "\n    " + "\n    ".join(lines)


def _readable_arg(value: object) -> object:
    if isinstance(value, (bytes, bytearray)):
        data = bytes(value)
        rendered = _render_dns_packet(data)
        if rendered is not None:
            return _Readable(rendered)
        return _Readable(data.decode("utf-8", errors="replace"))
    if isinstance(value, (list, tuple)) and value and all(
        isinstance(v, (bytes, bytearray)) for v in value
    ):
        return _Readable("".join(str(_readable_arg(v)) for v in value))
    return value


class _ReadablePacketFilter(logging.Filter):
    """Rewrites raw packet bytes in zeroconf's debug logs into parsed DNS
    text (questions and records), falling back to UTF-8 for non-DNS bytes."""

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(_parsing, "active", False):
            return False  # zeroconf complaining about our own display parse
        if record.name.startswith("zeroconf") and record.args:
            try:
                if isinstance(record.args, tuple):
                    record.args = tuple(_readable_arg(a) for a in record.args)
                elif isinstance(record.args, dict):
                    record.args = {k: _readable_arg(v) for k, v in record.args.items()}
            except Exception:  # noqa: BLE001 -- never lose a log line over this
                pass
        return True


def _enable_debug_logging() -> None:
    """Route this module's, zeroconf's and urllib3's logs at DEBUG to
    stderr (if there is one) and a log file."""
    fmt = logging.Formatter(
        "%(asctime)s.%(msecs)03d [%(threadName)s] %(name)s %(levelname)s: %(message)s",
        "%H:%M:%S",
    )
    handlers: list[logging.Handler] = []

    # Windowed PyInstaller builds have sys.stderr = None.
    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(fmt)
        handlers.append(stream)

    try:
        file_handler = logging.FileHandler(MDNS_DEBUG_LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(fmt)
        handlers.append(file_handler)
    except OSError as exc:
        if sys.stderr is not None:
            print(f"Could not open mDNS debug log file: {exc}", file=sys.stderr)

    packet_filter = _ReadablePacketFilter()
    for h in handlers:
        h.addFilter(packet_filter)

    for name in (__name__, "zeroconf", "urllib3"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.DEBUG)
        if not getattr(lg, "_vacuula_debug_attached", False):
            for h in handlers:
                lg.addHandler(h)
            lg._vacuula_debug_attached = True  # type: ignore[attr-defined]
        lg.propagate = False  # don't print twice if the root logger is configured

    logger.debug("=" * 72)
    logger.debug("mDNS debug logging enabled, log file: %s", MDNS_DEBUG_LOG_FILE)
    logger.debug("python %s on %s", sys.version.replace("\n", " "), sys.platform)
    logger.debug(
        "zeroconf %s, requests %s, frozen=%s",
        getattr(zeroconf_pkg, "__version__", "?"),
        getattr(requests, "__version__", "?"),
        getattr(sys, "frozen", False),
    )
    logger.debug("looking for service type %r", M_DNS_SERVICE_TYPE)
    _log_network_adapters()
    if sys.stderr is not None:
        print(f"[server_detector] mDNS debug log file: {MDNS_DEBUG_LOG_FILE}", file=sys.stderr)


def _log_network_adapters() -> None:
    """Which interfaces/IPs zeroconf can multicast on. ifaddr is a
    zeroconf dependency, so it's always available."""
    try:
        import ifaddr  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("ifaddr not importable, can't list adapters")
        return
    try:
        adapters = ifaddr.get_adapters()
    except Exception:  # noqa: BLE001 -- debug helper, never break detection
        logger.debug("listing adapters failed", exc_info=True)
        return
    logger.debug("network adapters (%d):", len(adapters))
    for adapter in adapters:
        ips = ", ".join(
            f"{ip.ip if isinstance(ip.ip, str) else ip.ip[0]}/{ip.network_prefix}"
            for ip in adapter.ips
        )
        logger.debug("  %s (%s): %s", adapter.nice_name, adapter.name, ips or "no IPs")


if MDNS_DEBUG:
    _enable_debug_logging()


DEFAULT_SERVER_PORT = 80
MANUAL_CERT_PATH = "/api/cert"

REQUEST_TIMEOUT_S = 3
MDNS_BROWSE_TIMEOUT_S = 3.0
MDNS_RESOLVE_TIMEOUT_MS = 1000

NOT_FOUND = "not_found"          # nothing answered at that address
INCOMPATIBLE = "incompatible"    # something answered, but not a usable Vacuula server

_attempt_counter = itertools.count(1)


class _ServerCheckError(Exception):
    def __init__(self, kind: str, detail: str = "") -> None:
        super().__init__(detail or kind)
        self.kind = kind


@dataclass(frozen=True)
class _ServerDetails:
    ip: str
    cert: str
    port: int
    gen4_port: int
    version: str


# ---------------------------------------------------------------------------
# Debug helpers
# ---------------------------------------------------------------------------

def _describe_info(info: ServiceInfo) -> str:
    """Everything a ServiceInfo knows, on several lines."""
    try:
        addresses = info.parsed_addresses()
    except Exception:  # noqa: BLE001
        addresses = ["<parse failed>"]
    props: dict[str, str] = {}
    for key, value in (info.properties or {}).items():
        k = key.decode("utf-8", "replace") if isinstance(key, bytes) else str(key)
        if value is None:
            props[k] = "<None>"
        else:
            props[k] = value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value)
    return (
        f"\n    name      = {info.name!r}"
        f"\n    type      = {info.type!r}"
        f"\n    server    = {info.server!r}"
        f"\n    port      = {info.port!r}"
        f"\n    addresses = {addresses!r}"
        f"\n    weight    = {getattr(info, 'weight', '?')!r}, priority = {getattr(info, 'priority', '?')!r}"
        f"\n    host_ttl  = {getattr(info, 'host_ttl', '?')!r}, other_ttl = {getattr(info, 'other_ttl', '?')!r}"
        f"\n    interface_index = {getattr(info, 'interface_index', '?')!r}"
        f"\n    properties = {props!r}"
    )


def _log_response(tag: str, url: str, response: requests.Response, elapsed: float) -> None:
    body = response.text or ""
    snippet = body[:HTTP_DEBUG_BODY_CHARS]
    if len(body) > HTTP_DEBUG_BODY_CHARS:
        snippet += f"... (+{len(body) - HTTP_DEBUG_BODY_CHARS} chars)"
    logger.debug(
        "[%s] GET %s -> HTTP %s in %.0f ms\n    final url    = %s\n    redirects    = %s"
        "\n    content-type = %r\n    length       = %d chars\n    headers      = %r\n    body         = %r",
        tag,
        url,
        response.status_code,
        elapsed * 1000,
        response.url,
        [f"{r.status_code} {r.url}" for r in response.history] or "none",
        response.headers.get("Content-Type"),
        len(body),
        dict(response.headers),
        snippet,
    )


# ---------------------------------------------------------------------------
# Shared HTTP check
# ---------------------------------------------------------------------------

def _check_server(ip: str, port: int, cert_path: str, tag: str) -> _ServerDetails:
    host = f"[{ip}]" if ":" in ip else ip  # IPv6 needs brackets in a URL
    base_url = f"http://{host}:{port}"
    logger.debug("[%s] checking server at %s (cert path %r)", tag, base_url, cert_path)

    # -- cert: the first request decides "not found" vs "answered"
    cert_url = f"{base_url}{cert_path}"
    started = time.monotonic()
    try:
        cert_response = requests.get(cert_url, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as exc:
        logger.debug(
            "[%s] GET %s failed after %.0f ms: %s: %s",
            tag, cert_url, (time.monotonic() - started) * 1000, type(exc).__name__, exc,
        )
        raise _ServerCheckError(NOT_FOUND, f"no answer from {base_url}: {exc}") from exc
    _log_response(tag, cert_url, cert_response, time.monotonic() - started)

    if not cert_response.ok:
        raise _ServerCheckError(
            INCOMPATIBLE, f"{cert_path} returned HTTP {cert_response.status_code}"
        )
    cert = cert_response.text
    if "BEGIN CERTIFICATE" not in cert:
        logger.debug("[%s] cert response has no 'BEGIN CERTIFICATE' marker", tag)
        raise _ServerCheckError(INCOMPATIBLE, f"{cert_path} did not return a certificate")
    logger.debug("[%s] certificate looks valid (%d chars)", tag, len(cert))

    # -- server info
    server_url = f"{base_url}/api/server"
    started = time.monotonic()
    try:
        server_response = requests.get(server_url, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as exc:
        logger.debug(
            "[%s] GET %s failed after %.0f ms: %s: %s",
            tag, server_url, (time.monotonic() - started) * 1000, type(exc).__name__, exc,
        )
        raise _ServerCheckError(NOT_FOUND, f"/api/server: {exc}") from exc
    _log_response(tag, server_url, server_response, time.monotonic() - started)

    try:
        server_response.raise_for_status()
        server_info = server_response.json()
        logger.debug("[%s] /api/server json: %r", tag, server_info)
        version = str(server_info["version"])
        gen4_port = int(server_info["gen4_port"])
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        logger.debug("[%s] /api/server unusable: %s: %s", tag, type(exc).__name__, exc)
        raise _ServerCheckError(INCOMPATIBLE, f"/api/server unusable: {exc}") from exc

    logger.debug(
        "[%s] server OK: ip=%s port=%s version=%s gen4_port=%s", tag, ip, port, version, gen4_port
    )
    return _ServerDetails(ip=ip, cert=cert, port=port, gen4_port=gen4_port, version=version)


def _parse_address(text: str) -> tuple[str, int]:
    original = text
    text = text.strip()
    for prefix in ("http://", "https://"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):]
    text = text.split("/", 1)[0]

    if text.count(":") == 1:  # host:port (more colons = bare IPv6)
        host, port_text = text.split(":")
        port = int(port_text) if port_text.isdigit() else DEFAULT_SERVER_PORT
    else:
        host, port = text, DEFAULT_SERVER_PORT

    logger.debug("parsed manual address %r -> host=%r port=%r", original, host, port)
    return host, port


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------

class _WorkerSignals(QObject):
    found = Signal(str, str, int, int)  # ip, cert, vacuula_port, gen4_port
    failed = Signal(str)


class _ServiceListener(ServiceListener):
    """Receives mDNS service discovery results."""

    def __init__(self, tag: str, started: float) -> None:
        self.info: ServiceInfo | None = None
        self.event = threading.Event()
        self._tag = tag
        self._started = started

    def _since(self) -> str:
        return f"+{(time.monotonic() - self._started) * 1000:.0f} ms"

    def _resolve(self, zc: Zeroconf, type_: str, name: str, why: str) -> None:
        logger.debug(
            "[%s] %s %s: type=%r name=%r -- resolving (timeout %d ms)",
            self._tag, self._since(), why, type_, name, MDNS_RESOLVE_TIMEOUT_MS,
        )
        resolve_started = time.monotonic()
        info = zc.get_service_info(type_, name, timeout=MDNS_RESOLVE_TIMEOUT_MS)
        took = (time.monotonic() - resolve_started) * 1000
        if info is None:
            logger.debug(
                "[%s] %s resolve of %r returned None after %.0f ms "
                "(no SRV/TXT/A answer in time)",
                self._tag, self._since(), name, took,
            )
            return
        logger.debug(
            "[%s] %s resolved %r in %.0f ms:%s",
            self._tag, self._since(), name, took, _describe_info(info),
        )
        self.info = info
        self.event.set()

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._resolve(zc, type_, name, "service ADDED")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        # A service can be updated after initially appearing.
        self._resolve(zc, type_, name, "service UPDATED")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        logger.debug(
            "[%s] %s service REMOVED: type=%r name=%r", self._tag, self._since(), type_, name
        )


class _DetectionWorker(QRunnable):
    """Blocking mDNS resolution + HTTP cert fetch, dont run on GUI thread
    mDNS takes aages.."""

    def __init__(self) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._tag = f"mdns#{next(_attempt_counter)}"

    @Slot()
    def run(self) -> None:
        threading.current_thread().name = f"server-detect-{self._tag}"
        logger.debug("[%s] ---- detection attempt start ----", self._tag)
        started = time.monotonic()
        try:
            self._run()
        finally:
            logger.debug(
                "[%s] ---- detection attempt end (%.0f ms) ----",
                self._tag, (time.monotonic() - started) * 1000,
            )

    def _run(self) -> None:
        info = self._discover_vacuula()
        if info is None:
            logger.debug("[%s] no %r service found", self._tag, M_DNS_SERVICE_TYPE)
            if MDNS_DEBUG and MDNS_DEBUG_LIST_ALL_TYPES:
                self._log_all_service_types()
            self.signals.failed.emit(NOT_FOUND)
            return

        addresses = info.parsed_addresses()
        logger.debug("[%s] service addresses: %r", self._tag, addresses)
        if not addresses:
            logger.warning("[%s] Vacuula service found but has no addresses", self._tag)
            self.signals.failed.emit(NOT_FOUND)
            return

        # Prefer IPv4.
        ip = next((addr for addr in addresses if ":" not in addr), addresses[0])
        logger.debug(
            "[%s] chose address %r (%s)", self._tag, ip,
            "IPv4" if ":" not in ip else "IPv6, no IPv4 available",
        )

        # DNS-SD TXT records are bytes -> bytes.
        properties = {
            self._decode_property(key): self._decode_property(value)
            for key, value in info.properties.items()
            if value is not None
        }
        logger.debug("[%s] decoded TXT properties: %r", self._tag, properties)
        cert_path = properties.get("cert-path")
        if not cert_path:
            logger.warning("[%s] Vacuula service found but has no cert-path property", self._tag)
            self.signals.failed.emit(INCOMPATIBLE)
            return

        port = info.port or DEFAULT_SERVER_PORT
        if not info.port:
            logger.debug("[%s] service has no port, falling back to %d", self._tag, DEFAULT_SERVER_PORT)

        try:
            details = _check_server(ip, port, cert_path, self._tag)
        except _ServerCheckError as exc:
            logger.warning("[%s] mDNS server check failed (%s): %s", self._tag, exc.kind, exc)
            self.signals.failed.emit(exc.kind)
            return

        logger.debug("[%s] Vacuula server version: %s", self._tag, details.version)
        self.signals.found.emit(details.ip, details.cert, details.port, details.gen4_port)

    def _discover_vacuula(self) -> ServiceInfo | None:
        started = time.monotonic()
        logger.debug("[%s] creating Zeroconf instance (all interfaces)", self._tag)
        zeroconf = Zeroconf()
        logger.debug(
            "[%s] Zeroconf up in %.0f ms; browsing %r for up to %.1f s",
            self._tag, (time.monotonic() - started) * 1000, M_DNS_SERVICE_TYPE, MDNS_BROWSE_TIMEOUT_S,
        )
        listener = _ServiceListener(self._tag, started)
        browser = ServiceBrowser(zeroconf, M_DNS_SERVICE_TYPE, listener)

        try:
            # Wait until a service is discovered or timeout expires.
            got_one = listener.event.wait(MDNS_BROWSE_TIMEOUT_S)
            logger.debug(
                "[%s] browse wait ended after %.0f ms: %s",
                self._tag, (time.monotonic() - started) * 1000,
                "service resolved" if got_one else "TIMED OUT, nothing resolved",
            )
            return listener.info
        finally:
            # Stop browsing and release the mDNS socket.
            browser.cancel()
            zeroconf.close()
            logger.debug("[%s] browser cancelled, Zeroconf closed", self._tag)

    def _log_all_service_types(self) -> None:
        logger.debug(
            "[%s] listing ALL mDNS service types on the network (%.1f s)...",
            self._tag, MDNS_DEBUG_LIST_TYPES_TIMEOUT_S,
        )
        started = time.monotonic()
        try:
            types = ZeroconfServiceTypes.find(timeout=MDNS_DEBUG_LIST_TYPES_TIMEOUT_S)
        except Exception:  # noqa: BLE001 -- debug helper, never break detection
            logger.debug("[%s] listing service types failed", self._tag, exc_info=True)
            return
        took = (time.monotonic() - started) * 1000
        if not types:
            logger.debug(
                "[%s] NO mDNS service types seen at all in %.0f ms -- mDNS is likely "
                "blocked here (firewall, VPN, wrong adapter, guest/isolated network)",
                self._tag, took,
            )
            return
        logger.debug("[%s] %d service types seen in %.0f ms:", self._tag, len(types), took)
        for service_type in sorted(types):
            marker = "  <-- ours" if service_type == M_DNS_SERVICE_TYPE else ""
            logger.debug("[%s]   %s%s", self._tag, service_type, marker)

    @staticmethod
    def _decode_property(value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value


class _ManualCheckWorker(QRunnable):
    """Same checks as _DetectionWorker, for one user-entered address."""

    def __init__(self, address: str) -> None:
        super().__init__()
        self.signals = _WorkerSignals()
        self._address = address
        self._tag = f"manual#{next(_attempt_counter)}"

    @Slot()
    def run(self) -> None:
        threading.current_thread().name = f"server-detect-{self._tag}"
        logger.debug("[%s] ---- manual check start: %r ----", self._tag, self._address)
        started = time.monotonic()
        try:
            self._run()
        finally:
            logger.debug(
                "[%s] ---- manual check end (%.0f ms) ----",
                self._tag, (time.monotonic() - started) * 1000,
            )

    def _run(self) -> None:
        host, port = _parse_address(self._address)
        if not host:
            logger.debug("[%s] empty host after parsing", self._tag)
            self.signals.failed.emit(NOT_FOUND)
            return
        try:
            details = _check_server(host, port, MANUAL_CERT_PATH, self._tag)
        except _ServerCheckError as exc:
            logger.warning("[%s] Manual server check failed (%s): %s", self._tag, exc.kind, exc)
            self.signals.failed.emit(exc.kind)
            return

        logger.debug("[%s] Vacuula server version (manual): %s", self._tag, details.version)
        self.signals.found.emit(details.ip, details.cert, details.port, details.gen4_port)


# ---------------------------------------------------------------------------
# Public detector
# ---------------------------------------------------------------------------

class ServerDetector(QObject):
    """Polls mDNS for M_DNS_SERVICE_TYPE, or checks a manual address, and
    emits the server's IP + cert once found."""

    # ip, cert, vacuula_port, gen4_port, manual (True = user-entered address)
    serverDetected = Signal(str, str, int, int, bool)
    # Manual check only: NOT_FOUND ("not_found") or INCOMPATIBLE ("incompatible")
    manualCheckFailed = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(False)
        self._timer.timeout.connect(self._detection_logic)
        self._pool = QThreadPool.globalInstance()
        self._busy = False
        self._manual_busy = False
        self._active = False
        self._found = False
        # keep refs alive until each worker finishes
        self._workers: set[QRunnable] = set()

    def start(self, delay_ms: int) -> None:
        logger.debug("ServerDetector.start(delay_ms=%d)", delay_ms)
        self._active = True
        self._found = False
        self._timer.start(delay_ms)

    def stop(self) -> None:
        logger.debug(
            "ServerDetector.stop() (busy=%s, manual_busy=%s, in-flight workers=%d)",
            self._busy, self._manual_busy, len(self._workers),
        )
        self._active = False  # any in-flight mDNS result gets ignored
        self._timer.stop()  # Needed for back button

    def check_manual(self, address: str) -> None:
        """Check a user-entered address ('ip', 'ip:port', or a URL)."""
        if self._manual_busy:
            logger.debug("check_manual(%r) ignored: a manual check is already running", address)
            return
        logger.debug("check_manual(%r) queued", address)
        self._manual_busy = True
        worker = _ManualCheckWorker(address)
        self._workers.add(worker)
        worker.signals.found.connect(
            lambda ip, cert, port, gen4, w=worker: self._on_manual_found(w, ip, cert, port, gen4)
        )
        worker.signals.failed.connect(
            lambda kind, w=worker: self._on_manual_failed(w, kind)
        )
        self._pool.start(worker)

    # -- mDNS --------------------------------------------------------------------

    def _detection_logic(self) -> None:
        if self._busy:
            logger.debug("timer tick skipped: previous mDNS attempt still running")
            return  # previous attempt still in flight; try again next tick
        self._busy = True
        worker = _DetectionWorker()
        logger.debug("timer tick: queueing mDNS attempt %s", worker._tag)
        self._workers.add(worker)
        worker.signals.found.connect(
            lambda ip, cert, port, gen4, w=worker: self._on_found(w, ip, cert, port, gen4)
        )
        worker.signals.failed.connect(lambda kind, w=worker: self._on_not_found(w, kind))
        self._pool.start(worker)

    def _on_found(self, worker: QRunnable, ip: str, cert: str, port: int, gen4_port: int) -> None:
        self._busy = False
        self._workers.discard(worker)
        if not self._active or self._found:
            logger.debug(
                "mDNS result for %s:%s ignored (active=%s, already found=%s)",
                ip, port, self._active, self._found,
            )
            return  # stopped, or a manual check already won
        self._finish(ip, cert, port, gen4_port, manual=False)

    def _on_not_found(self, worker: QRunnable, kind: str) -> None:
        logger.debug("mDNS attempt finished without a server (%s); will retry on next tick", kind)
        self._busy = False
        self._workers.discard(worker)

    # -- manual ------------------------------------------------------------------

    def _on_manual_found(self, worker: QRunnable, ip: str, cert: str, port: int, gen4_port: int) -> None:
        self._manual_busy = False
        self._workers.discard(worker)
        if self._found:
            logger.debug("manual result for %s:%s ignored: mDNS already found a server", ip, port)
            return  # mDNS already found one in the meantime
        self._finish(ip, cert, port, gen4_port, manual=True)

    def _on_manual_failed(self, worker: QRunnable, kind: str) -> None:
        self._manual_busy = False
        self._workers.discard(worker)
        if self._found:
            logger.debug("manual failure (%s) ignored: a server was already found", kind)
            return
        logger.debug("manual check failed: %s", kind)
        self.manualCheckFailed.emit(kind)

    # -- shared ------------------------------------------------------------------

    def _finish(self, ip: str, cert: str, port: int, gen4_port: int, *, manual: bool) -> None:
        logger.debug(
            "SERVER DETECTED via %s: ip=%s port=%s gen4_port=%s cert=%d chars",
            "manual entry" if manual else "mDNS", ip, port, gen4_port, len(cert),
        )
        self._found = True
        self._timer.stop()
        self._active = False
        self.serverDetected.emit(ip, cert, port, gen4_port, manual)