"""Placeholder robot detection.

TODO: Some fancy USB MTP enumeration to happen here
"""
from __future__ import annotations

import random

from PySide6.QtCore import QObject, QTimer, Signal

# (model_id, human-readable display name) -- placeholder catalog.
_FAKE_MODELS: list[tuple[str, str]] = [
    ("905-0724", "Neato Botvac D7"),
    ("905-0537", "Neato D10"),
]


class RobotDetector(QObject):
    """Fires :attr:`robotDetected` once, a fixed delay after :meth:`start`."""

    detectionStarted = Signal()
    robotDetected = Signal(str, str)  # model_id, display_name

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._simulate_detection)

    def start(self, delay_ms: int) -> None:
        """Begin (fake) detection; emits ``robotDetected`` after ``delay_ms``."""
        self.detectionStarted.emit()
        self._timer.start(delay_ms)

    def stop(self) -> None:
        """Cancel a pending detection, e.g. if the user navigates away."""
        self._timer.stop()

    def _simulate_detection(self) -> None:
        model_id, display_name = random.choice(_FAKE_MODELS)
        self.robotDetected.emit(model_id, display_name)
