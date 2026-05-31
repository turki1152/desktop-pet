"""
taskbar.py
==========
Detects the Windows taskbar position and size so the pet can sit *on top* of it
and walk along it -- no matter whether the taskbar is at the bottom (default),
top, left or right of the screen, and regardless of its height/DPI.

It uses the Win32 ``SHAppBarMessage`` API (via :mod:`ctypes`) which reports the
taskbar's exact rectangle and which screen edge it is docked to.  If anything
goes wrong we fall back to the primary screen geometry so the pet still works.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass

# --- Win32 constants -------------------------------------------------------- #
ABM_GETTASKBARPOS = 0x00000005
ABE_LEFT, ABE_TOP, ABE_RIGHT, ABE_BOTTOM = 0, 1, 2, 3


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", _RECT),
        ("lParam", wintypes.LPARAM),
    ]


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
    ]


_MONITOR_DEFAULTTONEAREST = 2


def is_fullscreen_app_active() -> bool:
    """True when the foreground window covers an entire monitor (a game, a
    full-screen video, a slideshow...).  Used to politely hide the pet so it
    doesn't sit on top of full-screen content.

    A *maximised* window does not count: it leaves the taskbar visible, so its
    rectangle stops short of the monitor's bottom edge -- only a true
    full-screen window reaches all four monitor edges.
    """
    try:
        u = ctypes.windll.user32
        hwnd = u.GetForegroundWindow()
        if not hwnd:
            return False
        if hwnd in (u.GetDesktopWindow(), u.GetShellWindow()):
            return False

        rect = _RECT()
        u.GetWindowRect(hwnd, ctypes.byref(rect))

        mon = u.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
        info = _MONITORINFO()
        info.cbSize = ctypes.sizeof(_MONITORINFO)
        if not u.GetMonitorInfoW(mon, ctypes.byref(info)):
            return False
        m = info.rcMonitor
        return (rect.left <= m.left and rect.top <= m.top
                and rect.right >= m.right and rect.bottom >= m.bottom)
    except Exception:
        return False


@dataclass
class TaskbarInfo:
    """Where the pet should live, in *physical* screen pixels.

    ground_y      The y coordinate the pet's resting line snaps to.
    sits_above    If True the pet's *bottom* rests on ground_y (normal bottom
                  taskbar). If False the pet's *top* aligns to ground_y.
    x_min, x_max  Horizontal range the pet may walk within.
    """

    ground_y: int
    sits_above: bool
    x_min: int
    x_max: int


def _screen_size() -> tuple[int, int]:
    """Primary screen width/height in physical pixels."""
    user32 = ctypes.windll.user32
    return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)


def get_taskbar_info() -> TaskbarInfo:
    """Return a :class:`TaskbarInfo` describing where the pet should rest."""
    screen_w, screen_h = _screen_size()
    try:
        data = _APPBARDATA()
        data.cbSize = ctypes.sizeof(_APPBARDATA)
        res = ctypes.windll.shell32.SHAppBarMessage(ABM_GETTASKBARPOS, ctypes.byref(data))
        if not res:
            raise OSError("SHAppBarMessage failed")

        rc, edge = data.rc, data.uEdge

        if edge == ABE_BOTTOM:
            # Most common: pet sits on the taskbar's top edge, walks full width.
            return TaskbarInfo(ground_y=rc.top, sits_above=True, x_min=0, x_max=screen_w)
        if edge == ABE_TOP:
            # Pet hangs just under the taskbar's bottom edge.
            return TaskbarInfo(ground_y=rc.bottom, sits_above=False, x_min=0, x_max=screen_w)
        if edge in (ABE_LEFT, ABE_RIGHT):
            # Vertical taskbar: let the pet rest on the desktop bottom, but keep
            # it out of the taskbar's column.
            x_min = rc.right if edge == ABE_LEFT else 0
            x_max = rc.left if edge == ABE_RIGHT else screen_w
            return TaskbarInfo(ground_y=screen_h, sits_above=True, x_min=x_min, x_max=x_max)
    except Exception:
        pass

    # Fallback: rest on the bottom of the primary screen.
    return TaskbarInfo(ground_y=screen_h, sits_above=True, x_min=0, x_max=screen_w)
