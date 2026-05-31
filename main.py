"""
Desktop Pet -- entry point
==========================
Run with::

    python main.py

This launches a small animated character that lives on top of your Windows
taskbar.  Left-click and drag it around; let go and it falls back down.
Right-click it (or its tray icon) for the menu: change character, size, speed,
mute, or exit.
"""

from __future__ import annotations

import os
import sys

# --- DPI handling ---------------------------------------------------------- #
# Make the process DPI-aware *before* Qt starts and disable Qt's own scaling so
# that Qt geometry matches the physical pixels reported by the Win32 taskbar API
# (see pet/taskbar.py).  This keeps the pet perfectly aligned on high-DPI / 4K
# displays.
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "0")
if sys.platform == "win32":
    try:
        import ctypes
        # PROCESS_PER_MONITOR_DPI_AWARE = 2
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        # Give Windows a unique App ID so it groups our windows separately
        # from python.exe and uses our custom icon in the taskbar.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "DesktopPet.App.1")
    except Exception:
        pass

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from pet.config import Settings  # noqa: E402
from pet.character import discover_characters  # noqa: E402
from pet.multi_pet import PetManager  # noqa: E402
from pet.pet_widget import PetWidget  # noqa: E402
from pet.paths import base_dir, ensure_data  # noqa: E402

# When packaged as an .exe, copy the bundled characters/assets out on first run.
ensure_data()

_BASE = base_dir()
CHARACTERS_DIR = os.path.join(_BASE, "characters")
ASSETS_DIR = os.path.join(_BASE, "assets")


def main() -> int:
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling, True)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # Set the app icon from icon.ico so every window (including settings)
    # shows the cat — not the Python logo — in the title bar and taskbar.
    _icon_path = os.path.join(ASSETS_DIR, "icon.ico")
    if os.path.isfile(_icon_path):
        from PyQt5.QtGui import QIcon, QPixmap
        from PyQt5.QtCore import Qt as _Qt
        pix = QPixmap(_icon_path)
        if not pix.isNull():
            icon = QIcon()
            for sz in (16, 32, 48, 64):
                icon.addPixmap(pix.scaled(sz, sz, _Qt.KeepAspectRatio, _Qt.FastTransformation))
            app.setWindowIcon(icon)

    if not discover_characters(CHARACTERS_DIR):
        print("No characters found. Run: python tools/generate_sprites.py")
        return 1

    # Detect first run BEFORE loading settings (settings.json won't exist yet).
    _settings_path = os.path.join(_BASE, "settings.json")
    _first_run = not os.path.isfile(_settings_path)

    settings = Settings.load()

    # On first run as a packaged .exe, silently enable startup so the pet
    # launches automatically every time Windows starts.
    if _first_run and getattr(sys, "frozen", False):
        from pet.startup import set_startup
        set_startup(True)

    manager  = PetManager()
    pet = PetWidget(CHARACTERS_DIR, ASSETS_DIR, settings, manager, first_run=_first_run)
    pet.show()

    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
