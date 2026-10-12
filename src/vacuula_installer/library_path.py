"""Undo PyInstaller's ``LD_LIBRARY_PATH`` pollution for child processes.

The Linux bootloader prepends its bundle directory (``_internal``) to
``LD_LIBRARY_PATH`` and stashes the previous value in ``LD_LIBRARY_PATH_ORIG``.
Every child process inherits that, so the system's link handler
loads the bundled Qt instead of the system one and dies, e.g.::
The frozen app only needs the bundle path while it loads its own libraries
(PySide6/shiboken resolve it at import time), so once startup is done we can
restore the pre-PyInstaller value and every child spawned afterwards gets a clean environment.
https://pyinstaller.org/en/stable/runtime-information.html#ld-library-path-libpath-considerations
"""

from __future__ import annotations

import os
import sys


def restore_library_path() -> None:
    """Drop PyInstaller's bundle paths from the environment.

    No-op outside frozen Linux builds, where there is nothing to undo and
    clobbering the caller's ``LD_LIBRARY_PATH`` would be wrong.
    """
    if not (sys.platform.startswith("linux") and getattr(sys, "frozen", False)):
        return
    for name in ("LD_LIBRARY_PATH", "LD_PRELOAD"):
        original = os.environ.pop(f"{name}_ORIG", None)
        if original is not None:
            os.environ[name] = original
        else:
            os.environ.pop(name, None)
