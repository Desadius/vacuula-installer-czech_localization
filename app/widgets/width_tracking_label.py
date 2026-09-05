from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Signal

class WidthTrackingLabel(QLabel):
    """QLabel that announces changes to its own width."""
    # I was having problems with text width not updating,
    # turns out resizes are lazyloaded so made explicit

    widthChanged = Signal()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self.widthChanged.emit()