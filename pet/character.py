"""
character.py
============
Loads a *character* from a folder on disk.

A character folder is completely self-contained and looks like this::

    characters/
        cat/
            config.json        (optional -- sensible defaults are used)
            idle/   frame_00.png frame_01.png ...   (required)
            walk/   frame_00.png ...                (optional)
            sleep/  frame_00.png ...                (optional)
            fall/   frame_00.png ...                (optional)
            sounds/ step.wav ...                    (optional)

Adding a brand new pet is therefore as easy as dropping a new folder of PNG
frames into ``characters/`` -- no code changes required.
"""

from __future__ import annotations

import json
import os

from .animation import Animation

# Animation states the engine understands. "idle" is mandatory; the rest fall
# back to idle if a character does not provide them.
STATES = ("idle", "walk", "sleep", "fall")

# Defaults merged over whatever a character's config.json provides.
_DEFAULT_CONFIG = {
    "name": None,
    "personality": "",
    "fps": {"idle": 6, "walk": 10, "sleep": 3, "fall": 8},
    "scale": 2.5,
    "walk_speed": 38,
    "behavior": {
        "idle_min": 2.0,
        "idle_max": 6.0,
        "walk_chance": 0.55,
        "sleep_chance": 0.2,
    },
    # Speech-bubble lines grouped by mood (see config.json of the bundled pets).
    "messages": {},
    "sounds": {},
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class Character:
    """A loaded character: its animations, config and sound paths."""

    def __init__(self, folder: str, scale: float = 1.0):
        self.folder = folder
        self.key = os.path.basename(folder.rstrip(os.sep))
        self.config = self._load_config(folder)
        self.name = self.config["name"] or self.key.title()
        self.personality = self.config.get("personality", "")
        self.messages = self.config.get("messages", {}) or {}

        # Final pixel height of the sprite on screen.
        base_height = self._native_height(folder)
        self.height = max(8, int(base_height * float(self.config["scale"]) * scale))

        # Load every available animation, sharing the computed target height.
        self.animations: dict[str, Animation] = {}
        for state in STATES:
            fps = float(self.config["fps"].get(state, 6))
            anim = Animation.from_folder(os.path.join(folder, state), fps, self.height)
            if anim is not None:
                self.animations[state] = anim

        if "idle" not in self.animations:
            raise ValueError(f"Character '{self.key}' has no usable 'idle' animation")

        # Resolve optional sound file paths up front.
        self.sounds: dict[str, str] = {}
        sound_dir = os.path.join(folder, "sounds")
        for event, filename in self.config.get("sounds", {}).items():
            path = os.path.join(sound_dir, filename)
            if os.path.isfile(path):
                self.sounds[event] = path

    # ------------------------------------------------------------------ #
    def animation(self, state: str) -> Animation:
        """Return the animation for *state*, falling back to idle."""
        return self.animations.get(state, self.animations["idle"])

    def random_message(self, category: str) -> str | None:
        """Return a random line for *category* (e.g. 'idle', 'happy') or None."""
        import random
        lines = self.messages.get(category)
        if not lines:
            return None
        return random.choice(lines)

    @property
    def walk_speed(self) -> float:
        return float(self.config["walk_speed"])

    @property
    def behavior(self) -> dict:
        return self.config["behavior"]

    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_config(folder: str) -> dict:
        path = os.path.join(folder, "config.json")
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (OSError, ValueError):
                data = {}
        return _deep_merge(_DEFAULT_CONFIG, data)

    @staticmethod
    def _native_height(folder: str) -> int:
        """Peek at the first idle frame to learn the art's native height."""
        from PyQt5.QtGui import QPixmap
        idle = os.path.join(folder, "idle")
        if os.path.isdir(idle):
            for name in sorted(os.listdir(idle)):
                if name.lower().endswith(".png"):
                    pix = QPixmap(os.path.join(idle, name))
                    if not pix.isNull():
                        return pix.height()
        return 32  # matches the bundled art


def discover_characters(characters_dir: str) -> list[str]:
    """Return the folder keys of every valid character (has an idle folder)."""
    found = []
    if not os.path.isdir(characters_dir):
        return found
    for name in sorted(os.listdir(characters_dir)):
        path = os.path.join(characters_dir, name)
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, "idle")):
            found.append(name)
    return found
