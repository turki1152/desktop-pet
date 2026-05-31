"""
config.py
=========
Loads and saves the user's global settings to ``settings.json`` in the project
root.  Keeping this tiny and dependency-free means the pet starts instantly and
remembers your choices (character, size, speed, mute) between runs.
"""

from __future__ import annotations

import json
import os

from .paths import base_dir

# settings.json lives in the base directory (project root, or next to the .exe).
_SETTINGS_PATH = os.path.join(base_dir(), "settings.json")

# Sensible defaults used when settings.json is missing or partial.
DEFAULTS = {
    # Core
    "character":           "cat",
    "pet_name":            "",
    "scale":               0.55,
    "speed":               1.0,
    "muted":               False,
    "hide_fullscreen":     True,
    "mood_score":          2.5,
    "custom_lines":        [],
    "custom_sounds":       {},
    # Birthday
    "pet_birthday":        "",
    "last_birthday_year":  0,
    # Magnet
    "magnet_mode":         False,
    "magnet_attract":      True,
    # Reactions — each can be turned on/off independently
    "weather_enabled":     True,
    "weather_city":        "",          # empty = auto-detect by IP
    "reaction_battery":    True,
    "reaction_idle":       True,
    "reaction_gaming":     True,
    "reaction_downloads":  True,
    "reaction_folder":     True,
    "reaction_seasonal":   True,
    "reaction_birthday":   True,
    # Behavior tuning
    "chatter_freq":        "normal",   # "rarely" | "normal" | "often"
    "bubble_duration":     3.0,        # seconds the speech bubble stays up
}


class Settings:
    """A small dict-backed settings object that persists to disk on change."""

    def __init__(self, data: dict | None = None):
        self._data = dict(DEFAULTS)
        if data:
            self._data.update({k: v for k, v in data.items() if k in DEFAULTS})

    # --- convenient typed accessors ------------------------------------- #
    @property
    def character(self) -> str:
        return self._data["character"]

    @character.setter
    def character(self, value: str):
        self._data["character"] = value
        self.save()

    @property
    def pet_name(self) -> str:
        return str(self._data.get("pet_name", ""))

    @pet_name.setter
    def pet_name(self, value: str):
        self._data["pet_name"] = str(value).strip()
        self.save()

    @property
    def scale(self) -> float:
        return float(self._data["scale"])

    @scale.setter
    def scale(self, value: float):
        # Clamp to a friendly range so the pet never vanishes or fills the screen.
        self._data["scale"] = max(0.5, min(4.0, float(value)))
        self.save()

    @property
    def speed(self) -> float:
        return float(self._data["speed"])

    @speed.setter
    def speed(self, value: float):
        self._data["speed"] = max(0.25, min(4.0, float(value)))
        self.save()

    @property
    def muted(self) -> bool:
        return bool(self._data["muted"])

    @muted.setter
    def muted(self, value: bool):
        self._data["muted"] = bool(value)
        self.save()

    @property
    def hide_fullscreen(self) -> bool:
        return bool(self._data.get("hide_fullscreen", True))

    @hide_fullscreen.setter
    def hide_fullscreen(self, value: bool):
        self._data["hide_fullscreen"] = bool(value)
        self.save()

    @property
    def mood_score(self) -> float:
        return float(self._data.get("mood_score", 2.5))

    @mood_score.setter
    def mood_score(self, value: float):
        self._data["mood_score"] = max(0.0, min(5.0, float(value)))
        self.save()

    @property
    def custom_lines(self) -> list:
        return list(self._data.get("custom_lines", []))

    @custom_lines.setter
    def custom_lines(self, value: list):
        self._data["custom_lines"] = [str(s) for s in value]
        self.save()

    @property
    def custom_sounds(self) -> dict:
        return dict(self._data.get("custom_sounds", {}))

    @custom_sounds.setter
    def custom_sounds(self, value: dict):
        self._data["custom_sounds"] = {str(k): str(v) for k, v in value.items()}
        self.save()

    @property
    def pet_birthday(self) -> str:
        return str(self._data.get("pet_birthday", ""))

    @pet_birthday.setter
    def pet_birthday(self, value: str):
        self._data["pet_birthday"] = str(value)
        self.save()

    @property
    def last_birthday_year(self) -> int:
        return int(self._data.get("last_birthday_year", 0))

    @last_birthday_year.setter
    def last_birthday_year(self, value: int):
        self._data["last_birthday_year"] = int(value)
        self.save()

    @property
    def weather_enabled(self) -> bool:
        return bool(self._data.get("weather_enabled", True))

    @weather_enabled.setter
    def weather_enabled(self, value: bool):
        self._data["weather_enabled"] = bool(value)
        self.save()

    @property
    def weather_city(self) -> str:
        return str(self._data.get("weather_city", ""))

    @weather_city.setter
    def weather_city(self, value: str):
        self._data["weather_city"] = str(value).strip()
        self.save()

    @property
    def magnet_mode(self) -> bool:
        return bool(self._data.get("magnet_mode", False))

    @magnet_mode.setter
    def magnet_mode(self, value: bool):
        self._data["magnet_mode"] = bool(value)
        self.save()

    @property
    def magnet_attract(self) -> bool:
        return bool(self._data.get("magnet_attract", True))

    @magnet_attract.setter
    def magnet_attract(self, value: bool):
        self._data["magnet_attract"] = bool(value)
        self.save()

    # --- reaction toggles ------------------------------------------------ #
    def _bool_prop(self, key: str, default: bool = True) -> bool:
        return bool(self._data.get(key, default))

    @property
    def reaction_battery(self) -> bool:   return self._bool_prop("reaction_battery")
    @reaction_battery.setter
    def reaction_battery(self, v: bool):  self._data["reaction_battery"] = bool(v); self.save()

    @property
    def reaction_idle(self) -> bool:      return self._bool_prop("reaction_idle")
    @reaction_idle.setter
    def reaction_idle(self, v: bool):     self._data["reaction_idle"] = bool(v); self.save()

    @property
    def reaction_gaming(self) -> bool:    return self._bool_prop("reaction_gaming")
    @reaction_gaming.setter
    def reaction_gaming(self, v: bool):   self._data["reaction_gaming"] = bool(v); self.save()

    @property
    def reaction_downloads(self) -> bool: return self._bool_prop("reaction_downloads")
    @reaction_downloads.setter
    def reaction_downloads(self, v: bool):self._data["reaction_downloads"] = bool(v); self.save()

    @property
    def reaction_folder(self) -> bool:    return self._bool_prop("reaction_folder")
    @reaction_folder.setter
    def reaction_folder(self, v: bool):   self._data["reaction_folder"] = bool(v); self.save()

    @property
    def reaction_seasonal(self) -> bool:  return self._bool_prop("reaction_seasonal")
    @reaction_seasonal.setter
    def reaction_seasonal(self, v: bool): self._data["reaction_seasonal"] = bool(v); self.save()

    @property
    def reaction_birthday(self) -> bool:  return self._bool_prop("reaction_birthday")
    @reaction_birthday.setter
    def reaction_birthday(self, v: bool): self._data["reaction_birthday"] = bool(v); self.save()

    # --- behavior tuning ------------------------------------------------- #
    @property
    def chatter_freq(self) -> str:
        return str(self._data.get("chatter_freq", "normal"))

    @chatter_freq.setter
    def chatter_freq(self, value: str):
        self._data["chatter_freq"] = value
        self.save()

    @property
    def bubble_duration(self) -> float:
        return float(self._data.get("bubble_duration", 3.0))

    @bubble_duration.setter
    def bubble_duration(self, value: float):
        self._data["bubble_duration"] = max(1.0, min(10.0, float(value)))
        self.save()

    # --- persistence ----------------------------------------------------- #
    def save(self) -> None:
        try:
            with open(_SETTINGS_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2)
        except OSError:
            # Never crash the pet just because settings could not be written.
            pass

    @classmethod
    def load(cls) -> "Settings":
        try:
            with open(_SETTINGS_PATH, "r", encoding="utf-8") as fh:
                return cls(json.load(fh))
        except (OSError, ValueError):
            return cls()
