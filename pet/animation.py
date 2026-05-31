"""
animation.py
============
A minimal, fast sprite-frame animation player.

An :class:`Animation` is just an ordered list of frames plus a frame duration.
It is driven by :meth:`Animation.update` with a delta-time, which keeps the
playback speed independent of the UI tick rate and the global speed setting.

Frames are loaded once, pre-scaled to their final on-screen size with
*nearest-neighbour* sampling (so the pixel art stays crisp), and a horizontally
mirrored copy is cached for the left-facing direction.  Pre-scaling means the
paint loop only ever blits a ready-made pixmap -- which is what keeps CPU usage
near zero while the pet is on screen.
"""

from __future__ import annotations

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QTransform


def _natural_sorted(names: list[str]) -> list[str]:
    """Sort frame names in human order (frame_2 before frame_10)."""
    import re
    def _key(s: str):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]
    return sorted(names, key=_key)


class Animation:
    def __init__(self, frames: list[QPixmap], fps: float):
        self._frames = frames
        self._flipped = [p.transformed(QTransform().scale(-1, 1)) for p in frames]
        self.frame_duration = 1.0 / fps if fps > 0 else 0.1
        self._index = 0
        self._accum = 0.0

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def size(self):
        return self._frames[0].size() if self._frames else None

    def reset(self) -> None:
        self._index = 0
        self._accum = 0.0

    def update(self, dt: float, speed: float = 1.0, reverse: bool = False) -> None:
        """Advance the animation by *dt* seconds (scaled by *speed*)."""
        if self.frame_count <= 1:
            return
        self._accum += dt * speed
        while self._accum >= self.frame_duration:
            self._accum -= self.frame_duration
            step = -1 if reverse else 1
            self._index = (self._index + step) % self.frame_count

    def current(self, facing_left: bool = False) -> QPixmap:
        frames = self._flipped if facing_left else self._frames
        return frames[self._index]

    # ------------------------------------------------------------------ #
    @classmethod
    def from_folder(cls, folder: str, fps: float, target_height: int) -> "Animation | None":
        """Load every ``frame_*.png`` in *folder*, scaled to *target_height*.

        Returns ``None`` if the folder has no frames so callers can fall back
        to another animation gracefully.
        """
        if not os.path.isdir(folder):
            return None
        names = [n for n in os.listdir(folder)
                 if n.lower().startswith("frame_") and n.lower().endswith(".png")]
        if not names:
            return None

        frames: list[QPixmap] = []
        for name in _natural_sorted(names):
            pix = QPixmap(os.path.join(folder, name))
            if pix.isNull():
                continue
            scaled = pix.scaledToHeight(target_height, Qt.FastTransformation)
            frames.append(scaled)
        if not frames:
            return None
        return cls(frames, fps)
