"""Entry point for the Vacuula robot-vacuum setup wizard."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from vacuula_installer.app_identity import apply_app_icon, prepare_app_identity
from vacuula_installer.constants import DEFAULT_LANGUAGE, LOCALES_DIR
from vacuula_installer.i18n import Translator
from vacuula_installer.logger import setup_logging
from vacuula_installer.main_window import MainWindow
from vacuula_installer.theme import STYLE_SHEET

prepare_app_identity()
setup_logging()
logger = logging.getLogger(__name__)

def main() -> int:
    logger.info("Starting Vacuula Installer")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    apply_app_icon(app)
    app.setStyleSheet(STYLE_SHEET)

    translator = Translator(LOCALES_DIR, default_language=DEFAULT_LANGUAGE)

    window = MainWindow(translator)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
