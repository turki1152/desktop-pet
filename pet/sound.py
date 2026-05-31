"""
sound.py
========
Optional, completely non-blocking sound effects.

Uses the standard-library :mod:`winsound` so there are *no* extra dependencies
and no audio engine running in the background.  Sounds are played fire-and-forget
with ``SND_ASYNC`` -- if a character ships no sounds, or the user mutes the pet,
this module simply does nothing.
"""

from __future__ import annotations

import os

try:
    import winsound  # Windows-only; guarded so imports never explode elsewhere.
except ImportError:  # pragma: no cover
    winsound = None


class SoundPlayer:
    def __init__(self, muted: bool = False):
        self.muted = muted

    def play(self, path: str | None) -> None:
        """Play a .wav file asynchronously, if possible and not muted."""
        if self.muted or not path or winsound is None:
            return
        if not os.path.isfile(path):
            return
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            # Audio is a nicety, never a reason to interrupt the pet.
            pass

    def stop(self) -> None:
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
