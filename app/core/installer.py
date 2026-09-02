"""Placeholder install-script dispatch.

O_SCRIPTS is for mapping detected model and the proper script
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from app.core.session import SessionData

logger = logging.getLogger(__name__)

# Matching on serial number now, easy to change and technically arbitrary, but fetcher must work for any supported vac
# TODO: use ids from USB instead
# "model_id", "name-of-install-script"
_SCRIPTS: dict[str, str] = {
    "905-0724": "install_gen4.py", #Neato D10 Intelligent
    "905-09596": "install_gen4.py", #Neato D8 Intelligent
    "905-0559": "install_gen4.py", #Neato D9 Intelligent

    "905-0537": "install_gen3.py", #Neato Botvac D7 Connected
    "905-0415": "install_gen3.py", #---//---

    "905-0517": "install_gen3.py",
}



class InstallerLauncher(QObject):
    """Dispatches to a model-specific install script (currently a stub)."""

    installStarted = Signal(str)  # model_id
    installFinished = Signal(str, bool)  # model_id, success

    def launch(self, session: SessionData) -> None:
        model_id = session.robot_model_id
        install_suceeded = False
        if model_id == None:
            logger.error("Invalid session state, no model_id")
            return #maybe not return, just go to installfinished(bla, False)?
        else:
            script = _SCRIPTS.get(model_id, None)
            if script == None:
                logger.error("No model match!")
                return #maybe not return, just go to installfinished(bla, False)?

            self.installStarted.emit(model_id)

            # TODO: real install scripts
            # Take needed info from session (SessionData)
            #   QProcess.startDetached(sys.executable, [str(scripts_dir / script)])
            logger.info("Placeholder: would launch install script %r for %r", script, session)
            # Bla bla
            install_suceeded = True

        self.installFinished.emit(model_id, install_suceeded)
