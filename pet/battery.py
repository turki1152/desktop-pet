"""
battery.py
==========
Windows battery / power-status monitor.  Polls every 30 seconds via the Win32
GetSystemPowerStatus API and returns named event strings the pet can react to.
"""
from __future__ import annotations

import ctypes
import sys

_AVAILABLE = sys.platform == "win32"


class _PowerStatus(ctypes.Structure):
    _fields_ = [
        ("ACLineStatus",        ctypes.c_byte),   # 0=offline 1=online 255=unknown
        ("BatteryFlag",         ctypes.c_byte),   # bit flags; 128=no battery
        ("BatteryLifePercent",  ctypes.c_byte),   # 0-100, 255=unknown
        ("SystemStatusFlag",    ctypes.c_byte),
        ("BatteryLifeTime",     ctypes.c_long),
        ("BatteryFullLifeTime", ctypes.c_long),
    ]


def _read() -> tuple[bool, int | None]:
    """Return (is_charging, level_percent_or_None)."""
    if not _AVAILABLE:
        return False, None
    try:
        sps = _PowerStatus()
        ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps))
        if sps.BatteryFlag == 128:           # no battery (desktop)
            return False, None
        charging = (sps.ACLineStatus == 1)
        level = int(sps.BatteryLifePercent) if sps.BatteryLifePercent != 255 else None
        return charging, level
    except Exception:
        return False, None


class BatteryMonitor:
    """
    Call ``tick(dt)`` every frame.

    Returns a list of event strings (may be empty):
      'charging'   – charger just plugged in
      'unplugged'  – charger just removed
      'full'       – reached 100 % while charging
      'low'        – first drop below 20 % on battery
      'critical'   – first drop below 5 % on battery
    """

    INTERVAL = 30.0   # seconds between polls

    def __init__(self):
        self._accum            = self.INTERVAL   # fire immediately on first tick
        self._last_charging: bool | None = None
        self._last_level:    int  | None = None
        self._alerted_low      = False
        self._alerted_critical = False

    def tick(self, dt: float) -> list[str]:
        self._accum += dt
        if self._accum < self.INTERVAL:
            return []
        self._accum = 0.0
        return self._evaluate()

    def _evaluate(self) -> list[str]:
        charging, level = _read()
        events: list[str] = []

        # --- charging state change ----------------------------------- #
        if self._last_charging is not None:
            if charging and not self._last_charging:
                events.append("charging")
                self._alerted_low      = False   # reset so they fire again later
                self._alerted_critical = False
            elif not charging and self._last_charging:
                events.append("unplugged")
        self._last_charging = charging

        # --- level events ------------------------------------------- #
        if level is not None:
            if charging and level == 100 and self._last_level is not None and self._last_level < 100:
                events.append("full")
            if not charging:
                if level < 5 and not self._alerted_critical:
                    self._alerted_critical = True
                    self._alerted_low      = True
                    events.append("critical")
                elif level < 20 and not self._alerted_low:
                    self._alerted_low = True
                    events.append("low")
            self._last_level = level

        return events
