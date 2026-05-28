"""
generate_sounds.py
===================
Procedurally synthesizes small retro-style sound effects for the bundled
characters and wires them into each character's ``config.json``.

Uses only the Python standard library (:mod:`wave`, :mod:`math`, :mod:`struct`)
so there are no extra dependencies.  Four short effects are produced per
character and dropped in ``characters/<name>/sounds/``:

    grab.wav   played when you pick the pet up
    walk.wav   played as a soft footstep while walking
    land.wav   played when the pet lands after a fall
    sleep.wav  played when the pet lies down for a nap

Run once to (re)create them::

    python tools/generate_sounds.py
"""

from __future__ import annotations

import json
import math
import os
import struct
import wave

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "characters"))
RATE = 22050  # sample rate (Hz); plenty for short blips and keeps files tiny.


# --------------------------------------------------------------------------- #
# Tiny synthesizer
# --------------------------------------------------------------------------- #
def _wave_sample(kind: str, phase: float) -> float:
    """Return one sample (-1..1) of the given waveform at *phase* (0..1)."""
    if kind == "square":
        return 1.0 if (phase % 1.0) < 0.5 else -1.0
    if kind == "tri":
        p = phase % 1.0
        return 4 * abs(p - 0.5) - 1
    if kind == "saw":
        return 2 * (phase % 1.0) - 1
    return math.sin(2 * math.pi * phase)  # sine


def tone(f0: float, f1: float, dur: float, kind: str = "sine",
         vol: float = 0.5, vibrato: float = 0.0) -> list[float]:
    """Synthesize a tone that sweeps from *f0* to *f1* Hz over *dur* seconds.

    A short attack and an exponential decay envelope are applied so the blip
    sounds soft rather than clicky. *vibrato* adds a gentle pitch wobble.
    """
    n = max(1, int(RATE * dur))
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        if vibrato:
            freq *= 1.0 + vibrato * math.sin(2 * math.pi * 7 * t)
        phase += freq / RATE
        # Envelope: 8% attack, exponential decay to the end.
        atk = min(1.0, t / 0.08) if t < 0.08 else 1.0
        env = atk * math.exp(-3.0 * t)
        out.append(_wave_sample(kind, phase) * vol * env)
    return out


def noise(dur: float, vol: float = 0.3) -> list[float]:
    """A short burst of (decaying) pseudo-random noise -- airy whoosh/squish."""
    import random
    n = max(1, int(RATE * dur))
    out = []
    smooth = 0.0
    for i in range(n):
        t = i / n
        # Low-pass the white noise a little so it sounds soft, not harsh.
        smooth = 0.7 * smooth + 0.3 * (random.uniform(-1, 1))
        out.append(smooth * vol * math.exp(-4.0 * t))
    return out


def mix(*layers: list[float]) -> list[float]:
    """Sum several sample lists, padding shorter ones with silence."""
    length = max(len(l) for l in layers)
    out = [0.0] * length
    for layer in layers:
        for i, s in enumerate(layer):
            out[i] += s
    return out


def _write_wav(path: str, samples: list[float]) -> None:
    # Soft-clip then convert to 16-bit PCM mono.
    frames = bytearray()
    for s in samples:
        s = max(-1.0, min(1.0, s))
        frames += struct.pack("<h", int(s * 32767))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


# --------------------------------------------------------------------------- #
# Per-character effect recipes
# --------------------------------------------------------------------------- #
def _effects(character: str) -> dict[str, list[float]]:
    if character == "cat":
        return {
            # A little two-syllable "meow" rising then falling.
            "grab": tone(520, 880, 0.13, "tri", 0.5) + tone(820, 560, 0.14, "tri", 0.45),
            "walk": tone(240, 200, 0.05, "square", 0.18),     # soft padded step
            "land": tone(170, 80, 0.16, "sine", 0.55),        # gentle thud
            "sleep": tone(330, 300, 0.30, "sine", 0.3, vibrato=0.02),  # tiny purr
        }
    if character == "slime":
        return {
            "grab": tone(420, 1150, 0.10, "square", 0.4),     # squeak up
            "walk": tone(620, 300, 0.10, "square", 0.3),      # descending boing
            "land": mix(noise(0.12, 0.3), tone(160, 90, 0.12, "sine", 0.4)),  # squish
            "sleep": tone(220, 190, 0.30, "tri", 0.3),
        }
    if character == "naruto":
        return {
            "grab": tone(420, 900, 0.12, "square", 0.4),    # energetic "hyah!"
            "walk": tone(300, 260, 0.05, "square", 0.2),
            "land": tone(180, 90, 0.16, "sine", 0.5),
            "sleep": tone(300, 280, 0.30, "sine", 0.3),
        }
    if character == "luffy":
        return {
            # cheery two-note "shishi" giggle
            "grab": tone(520, 820, 0.08, "square", 0.4) + tone(820, 1120, 0.08, "square", 0.38),
            "walk": tone(360, 300, 0.06, "square", 0.24),
            "land": tone(170, 85, 0.16, "sine", 0.5),
            "sleep": tone(260, 240, 0.30, "tri", 0.3),
        }
    # ghost
    return {
        "grab": tone(300, 300, 0.26, "sine", 0.45, vibrato=0.06),  # wavy "boo"
        "walk": noise(0.06, 0.12),                                  # airy step
        "land": tone(150, 95, 0.16, "sine", 0.35),
        "sleep": tone(240, 220, 0.32, "sine", 0.28, vibrato=0.05),
    }


SOUND_MAP = {"walk": "walk.wav", "land": "land.wav",
             "grab": "grab.wav", "sleep": "sleep.wav"}


def build_for(character: str) -> None:
    folder = os.path.join(ROOT, character)
    sounds_dir = os.path.join(folder, "sounds")
    for event, samples in _effects(character).items():
        _write_wav(os.path.join(sounds_dir, SOUND_MAP[event]), samples)

    # Patch the character's config.json to reference the new sound files.
    cfg_path = os.path.join(folder, "config.json")
    cfg = {}
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    cfg["sounds"] = dict(SOUND_MAP)
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def main():
    characters = ("cat", "slime", "ghost", "naruto", "luffy")
    for character in characters:
        build_for(character)
    print(f"Generated sounds for {', '.join(characters)} in: {ROOT}")


if __name__ == "__main__":
    main()
