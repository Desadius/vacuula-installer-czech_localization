#!/usr/bin/env python3
"""Entry point for the Vacuula robot-vacuum setup wizard.

Run with:

    python main.py
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.constants import DEFAULT_LANGUAGE, LOCALES_DIR
from app.i18n import Translator
from app.main_window import MainWindow
from app.theme import STYLE_SHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Vacuula Setup")
    app.setStyleSheet(STYLE_SHEET)

    translator = Translator(LOCALES_DIR, default_language=DEFAULT_LANGUAGE)

    window = MainWindow(translator)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
