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
    "character": "cat",   # folder name inside characters/
    "scale": 0.55,        # extra size multiplier on top of the character's own
    "speed": 1.0,         # animation + walk speed multiplier
    "muted": False,       # global sound on/off
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
