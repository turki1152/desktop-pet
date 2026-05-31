"""
particles.py
============
Tiny floating heart particles that burst from the pet when it's patted.
The overlay is a full-screen, click-through, transparent window so the
hearts can drift anywhere without intercepting mouse events.
"""

from __future__ import annotations

import random
import time

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtWidgets import QApplication, QWidget


_HEARTS = ["♥", "♡"]
_COLORS = [
    QColor(255, 100, 130),
    QColor(255, 60,  100),
    QColor(255, 150, 170),
    QColor(255, 200, 210),
]
GRAVITY = 60.0   # gentle downward pull after the initial burst

# Seasonal glyphs and colours.
_SEASONAL: dict[str, tuple[list[str], list[QColor]]] = {
    "snow":    (["❄", "❅", "❆", "·"],
                [QColor(200, 220, 255), QColor(180, 210, 255), QColor(255, 255, 255)]),
    "confetti":(["🎉", "🎊", "✨", "★", "•"],
                [QColor(255, 220, 50), QColor(255, 100, 200), QColor(100, 200, 255),
                 QColor(100, 255, 150)]),
    "hearts":  (_HEARTS, _COLORS),
    "leaves":  (["🍂", "🍁", "•", "·"],
                [QColor(200, 100, 30), QColor(220, 140, 20), QColor(160, 80, 20)]),
    "flowers": (["🌸", "🌼", "✿", "·"],
                [QColor(255, 180, 210), QColor(255, 220, 100), QColor(200, 240, 200)]),
}


class _Particle:
    __slots__ = ("x", "y", "vx", "vy", "opacity", "size", "glyph", "color",
                 "gravity", "fade_rate")

    def __init__(self, x: float, y: float,
                 glyphs=None, colors=None,
                 vy_range=(-160, -80), vx_range=(-55, 55),
                 gravity: float = GRAVITY, fade_rate: float = 1.1):
        glyphs = glyphs or _HEARTS
        colors = colors or _COLORS
        self.x = x + random.uniform(-24, 24)
        self.y = y + random.uniform(-8, 8)
        self.vx = random.uniform(*vx_range)
        self.vy = random.uniform(*vy_range)
        self.opacity = 1.0
        self.size = random.randint(11, 18)
        self.glyph = random.choice(glyphs)
        self.color = random.choice(colors)
        self.gravity = gravity
        self.fade_rate = fade_rate


class ParticleOverlay(QWidget):
    """Full-screen transparent overlay that animates floating heart particles."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self._particles: list[_Particle] = []
        self._last_t = time.perf_counter()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------ #
    def spawn(self, center_x: int, top_y: int, count: int = 7) -> None:
        """Burst *count* heart particles from the given screen position."""
        for _ in range(count):
            self._particles.append(_Particle(center_x, top_y))
        self._start()

    def spawn_seasonal(self, theme: str = "confetti", count: int = 25) -> None:
        """
        Scatter *count* seasonal particles across the top of the screen.
        theme: 'snow', 'confetti', 'hearts', 'leaves', 'flowers'
        """
        glyphs, colors = _SEASONAL.get(theme, _SEASONAL["confetti"])
        primary = QApplication.primaryScreen()
        if primary is None:
            return
        screen = primary.geometry()
        for _ in range(count):
            x = random.randint(0, max(0, screen.width() - 1))
            y = -random.randint(0, 40)          # start just above screen
            p = _Particle(x, y, glyphs=glyphs, colors=colors,
                          vy_range=(30, 90), vx_range=(-20, 20),
                          gravity=8.0, fade_rate=0.25)
            self._particles.append(p)
        self._start()

    def _start(self) -> None:
        primary = QApplication.primaryScreen()
        if primary is None:
            return
        screen = primary.geometry()
        self.setGeometry(screen)
        if not self._timer.isActive():
            self._last_t = time.perf_counter()
            self._timer.start(33)
            self.show()
            self.raise_()

    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._last_t = now

        for p in self._particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += p.gravity * dt
            p.opacity -= dt * p.fade_rate

        self._particles = [p for p in self._particles if p.opacity > 0]
        if not self._particles:
            self._timer.stop()
            self.hide()
            return

        self.update()

    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for p in self._particles:
            color = QColor(p.color)
            color.setAlphaF(max(0.0, p.opacity))
            painter.setPen(color)
            painter.setFont(QFont("Segoe UI Emoji", p.size))
            painter.drawText(int(p.x), int(p.y), p.glyph)
        painter.end()
