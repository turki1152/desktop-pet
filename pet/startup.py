"""
startup.py
==========
Windows registry helpers for launch-at-startup.

Writes / removes the value:
  HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run  →  DesktopPet
"""

from __future__ import annotations

import os
import sys

_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "DesktopPet"


def _startup_command() -> str:
    """Return the command string that launches the app."""
    exe = sys.executable
    # Running as a frozen .exe
    if getattr(sys, "frozen", False):
        return f'"{exe}"'
    # Running as a plain Python script
    script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "main.py")
    )
    return f'"{exe}" "{script}"'


def is_startup_enabled() -> bool:
    """Return True if the startup registry value exists."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY) as key:
            winreg.QueryValueEx(key, _APP_NAME)
            return True
    except Exception:
        return False


def set_startup(enabled: bool) -> None:
    """Add or remove the startup registry value."""
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _REG_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _APP_NAME, 0, winreg.REG_SZ, _startup_command())
            else:
                try:
                    winreg.DeleteValue(key, _APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass
