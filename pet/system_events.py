"""
system_events.py
================
Monitors system-level conditions:
  * User idle time  (Win32 GetLastInputInfo)
  * Long fullscreen / gaming session duration
  * New files appearing in ~/Downloads
  * Open File Explorer windows (for "looks into folders" reaction)

Also provides helpers for the cursor-steal gag.
"""
from __future__ import annotations

import ctypes
import os
import sys

_WIN = sys.platform == "win32"


# ------------------------------------------------------------------ #
# Idle time
# ------------------------------------------------------------------ #
class _LII(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def idle_seconds() -> float:
    """Return seconds since the last keyboard or mouse input."""
    if not _WIN:
        return 0.0
    try:
        lii = _LII()
        lii.cbSize = ctypes.sizeof(lii)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        # GetTickCount64 is 64-bit and never wraps; fall back to GetTickCount.
        try:
            tick = ctypes.windll.kernel32.GetTickCount64()
        except AttributeError:
            tick = ctypes.windll.kernel32.GetTickCount()
        return max(0.0, (tick - lii.dwTime) / 1000.0)
    except Exception:
        return 0.0


# ------------------------------------------------------------------ #
# Cursor steal gag
# ------------------------------------------------------------------ #
def move_cursor(x: int, y: int) -> None:
    """Teleport the system cursor to (x, y)."""
    if _WIN:
        try:
            ctypes.windll.user32.SetCursorPos(x, y)
        except Exception:
            pass


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos() -> tuple[int, int]:
    """Return current cursor position."""
    if _WIN:
        try:
            pt = _POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        except Exception:
            pass
    return 0, 0


# ------------------------------------------------------------------ #
# Window spy (for folder detection and window sitting)
# ------------------------------------------------------------------ #
class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def get_app_window_tops() -> list[tuple[int, int, int]]:
    """
    Return list of (x_left, x_right, y_top) for every visible,
    captioned, sizeable application window.  Used for sit-on-window.
    """
    if not _WIN:
        return []
    results: list[tuple[int, int, int]] = []
    _WS_CAPTION = 0x00C00000

    def _cb(hwnd, _lp):
        u = ctypes.windll.user32
        if not u.IsWindowVisible(hwnd):
            return True
        if hwnd in (u.GetDesktopWindow(), u.GetShellWindow()):
            return True
        style = u.GetWindowLongW(hwnd, -16)   # GWL_STYLE
        if not (style & _WS_CAPTION):
            return True
        rc = _RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rc))
        w = rc.right - rc.left
        h = rc.bottom - rc.top
        if w > 100 and h > 40:
            results.append((rc.left, rc.right, rc.top))
        return True

    _FT = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
    ctypes.windll.user32.EnumWindows(_FT(_cb), 0)
    return results


def get_clipboard_text() -> str:
    """Return current clipboard text (empty string on failure)."""
    if not _WIN:
        return ""
    try:
        import ctypes.wintypes
        user32 = ctypes.windll.user32
        if not user32.OpenClipboard(None):
            return ""
        try:
            CF_UNICODETEXT = 13
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = ctypes.windll.kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                ctypes.windll.kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()
    except Exception:
        return ""


def has_explorer_window() -> bool:
    """True when any File Explorer / folder window is open."""
    if not _WIN:
        return False
    found = [False]

    def _cb(hwnd, _lp):
        if not ctypes.windll.user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
        if buf.value in ("CabinetWClass", "ExploreWClass"):
            found[0] = True
            return False
        return True

    _FT = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_long)
    ctypes.windll.user32.EnumWindows(_FT(_cb), 0)
    return found[0]


# ------------------------------------------------------------------ #
# Main monitor class
# ------------------------------------------------------------------ #
class SystemMonitor:
    """
    Call ``tick(dt, fullscreen_active)`` each frame.

    Returns a list of event strings:
      'user_away'        – no input for > 5 min
      'user_back'        – user returned
      'gaming_warning'   – fullscreen app running > 60 min straight
      'download_new'     – new file appeared in ~/Downloads
      'folder_open'      – File Explorer window just opened
      'folder_closed'    – File Explorer window just closed
    """

    IDLE_THRESHOLD   = 300.0    # 5 minutes of no input
    GAMING_THRESHOLD = 3600.0   # 1 hour of fullscreen

    def __init__(self):
        self._user_away       = False
        self._gaming_accum    = 0.0
        self._gaming_warned   = False
        self._dl_mtime        = self._dl_folder_mtime()
        self._folder_open     = False
        # Throttle timers
        self._idle_check      = 0.0
        self._dl_check        = 0.0
        self._folder_check    = 0.0

    def tick(self, dt: float, fullscreen_active: bool) -> list[str]:
        events: list[str] = []

        # --- idle / user back ---------------------------------------- #
        self._idle_check += dt
        if self._idle_check >= 15.0:
            self._idle_check = 0.0
            idle = idle_seconds()
            if idle > self.IDLE_THRESHOLD and not self._user_away:
                self._user_away = True
                events.append("user_away")
            elif idle < 10.0 and self._user_away:
                self._user_away = False
                events.append("user_back")

        # --- gaming / fullscreen session ------------------------------ #
        if fullscreen_active:
            self._gaming_accum += dt
            if self._gaming_accum >= self.GAMING_THRESHOLD and not self._gaming_warned:
                self._gaming_warned = True
                events.append("gaming_warning")
        else:
            self._gaming_accum  = 0.0
            self._gaming_warned = False

        # --- downloads watcher --------------------------------------- #
        self._dl_check += dt
        if self._dl_check >= 10.0:
            self._dl_check = 0.0
            mt = self._dl_folder_mtime()
            if mt is not None and mt != self._dl_mtime:
                self._dl_mtime = mt
                events.append("download_new")

        # --- explorer / folder windows ------------------------------- #
        self._folder_check += dt
        if self._folder_check >= 5.0:
            self._folder_check = 0.0
            now_open = has_explorer_window()
            if now_open and not self._folder_open:
                self._folder_open = True
                events.append("folder_open")
            elif not now_open and self._folder_open:
                self._folder_open = False
                events.append("folder_closed")

        return events

    @property
    def user_away(self) -> bool:
        return self._user_away

    @staticmethod
    def _dl_folder_mtime() -> float | None:
        path = os.path.join(os.path.expanduser("~"), "Downloads")
        try:
            return os.path.getmtime(path)
        except OSError:
            return None
