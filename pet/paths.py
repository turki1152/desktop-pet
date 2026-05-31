"""
paths.py
========
Resolves where the app's files live, working in three situations:

1. **Running from source** — files live in the project root (next to main.py).
2. **One-file .exe** (PyInstaller ``--onefile``) — the character art and assets
   are bundled *inside* the executable and extracted to a temp folder at launch
   (``sys._MEIPASS``). On first run we copy them out next to the .exe so they're
   editable and you can add your own characters.
3. **One-folder .exe** — same idea; the data sits next to the executable.

Writable files (``settings.json``, ``reminders.json``) always live next to the
executable (or in the project root when run from source).
"""

from __future__ import annotations

import os
import shutil
import sys


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def exe_dir() -> str:
    """The folder the app 'lives' in: next to the .exe, or the project root."""
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _bundle_dir() -> str:
    """Where PyInstaller unpacked bundled data (or the project root in source)."""
    return getattr(sys, "_MEIPASS", exe_dir())


def base_dir() -> str:
    """Base directory for both data and writable settings files."""
    return exe_dir()


def ensure_data() -> None:
    """On a frozen first run, copy bundled ``characters/`` and ``assets/`` out
    next to the executable so they're visible and editable. No-op from source.
    """
    if not is_frozen():
        return
    for name in ("characters", "assets"):
        dst = os.path.join(exe_dir(), name)
        src = os.path.join(_bundle_dir(), name)
        if not os.path.isdir(dst) and os.path.isdir(src):
            try:
                shutil.copytree(src, dst)
            except OSError:
                pass
