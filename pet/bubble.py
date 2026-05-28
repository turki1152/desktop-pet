"""
bubble.py
=========
A small, modern speech bubble that floats above the pet to show messages
(random personality chatter, reminders) together with an optional mood emote.

Like the pet itself it is a frameless, translucent, always-on-top window that
never steals focus.  It paints a rounded "cloud" with a little tail pointing
down at the character, wraps the text, and auto-hides after a few seconds.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer, QRect, QSize
from PyQt5.QtGui import QPainter, QColor, QFont, QPainterPath, QFontMetrics, QPixmap
from PyQt5.QtWidgets import QWidget

# Visual tuning.
PAD = 10            # inner padding around the text
TAIL_H = 8          # height of the little pointer at the bottom
RADIUS = 12         # corner radius
MAX_TEXT_W = 200    # text wraps beyond this width
EMOTE_PX = 22       # on-screen size of the mood icon
BG = QColor(38, 40, 54, 240)       # bubble fill (dark, slightly translucent)
BORDER = QColor(120, 130, 200, 220)
TEXT = QColor(240, 242, 250)


class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput  # clicks pass straight through it
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self._text = ""
        self._emote: QPixmap | None = None
        self._text_rect = QRect()
        self._font = QFont("Segoe UI", 9)
        self._font.setBold(True)

        # Auto-hide timer (single shot, restarted on every new message).
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    # ------------------------------------------------------------------ #
    def show_message(self, text: str | None, emote: QPixmap | None = None,
                     duration: float = 3.0) -> None:
        """Display *text* (and optional *emote*) for *duration* seconds."""
        if not text and emote is None:
            return
        self._text = text or ""
        self._emote = emote if (emote and not emote.isNull()) else None
        self._relayout()
        self.show()
        self.raise_()
        self._hide_timer.start(int(duration * 1000))

    # ------------------------------------------------------------------ #
    def _relayout(self) -> None:
        """Measure the content and resize the window to fit the bubble."""
        fm = QFontMetrics(self._font)
        text_w = 0
        self._text_rect = QRect()
        if self._text:
            self._text_rect = fm.boundingRect(
                QRect(0, 0, MAX_TEXT_W, 1000),
                Qt.TextWordWrap | Qt.AlignLeft, self._text)
            text_w = self._text_rect.width()

        emote_w = (EMOTE_PX + 6) if self._emote else 0
        content_w = emote_w + text_w
        content_h = max(self._text_rect.height(), EMOTE_PX if self._emote else 0)

        w = content_w + PAD * 2
        h = content_h + PAD * 2 + TAIL_H
        self.resize(QSize(max(w, 36), max(h, 30)))

    def reposition(self, pet_geom: QRect) -> None:
        """Place the bubble centred just above the pet."""
        x = pet_geom.center().x() - self.width() // 2
        y = pet_geom.top() - self.height() + 2
        # Keep the bubble on-screen horizontally.
        screen = self.screen().geometry() if self.screen() else None
        if screen:
            x = max(screen.left() + 2, min(x, screen.right() - self.width() - 2))
            if y < screen.top() + 2:
                y = screen.top() + 2
        self.move(x, y)

    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        w, h = self.width(), self.height()
        body = QRect(0, 0, w, h - TAIL_H)

        # Rounded body + downward tail as one path.
        path = QPainterPath()
        path.addRoundedRect(0.5, 0.5, w - 1, h - TAIL_H - 1, RADIUS, RADIUS)
        cx = w // 2
        tail = QPainterPath()
        tail.moveTo(cx - 7, h - TAIL_H - 1)
        tail.lineTo(cx, h - 1)
        tail.lineTo(cx + 7, h - TAIL_H - 1)
        path = path.united(tail)

        p.setPen(BORDER)
        p.setBrush(BG)
        p.drawPath(path)

        # Contents.
        x = PAD
        inner_h = body.height() - PAD * 2
        if self._emote:
            ey = PAD + (inner_h - EMOTE_PX) // 2
            p.drawPixmap(x, ey,
                         self._emote.scaled(EMOTE_PX, EMOTE_PX,
                                            Qt.KeepAspectRatio, Qt.SmoothTransformation))
            x += EMOTE_PX + 6

        if self._text:
            p.setFont(self._font)
            p.setPen(TEXT)
            text_area = QRect(x, PAD, w - x - PAD, inner_h)
            p.drawText(text_area, Qt.TextWordWrap | Qt.AlignVCenter | Qt.AlignLeft, self._text)
        p.end()
