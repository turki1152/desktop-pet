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

from PyQt5.QtCore import Qt, QTimer, QRect, QSize, QPropertyAnimation, QEasingCurve
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

        # Auto-hide timer — triggers a fade-out rather than an instant hide.
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_fade_out)

        # Opacity animation shared for both fade-in and fade-out.
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._fading_out = False
        self._anim.finished.connect(self._on_anim_finished)

        # Typewriter: reveal one character every tick.
        self._visible_chars = 0
        self._type_timer = QTimer(self)
        self._type_timer.timeout.connect(self._advance_char)

    # ------------------------------------------------------------------ #
    def show_message(self, text: str | None, emote: QPixmap | None = None,
                     duration: float = 3.0) -> None:
        """Display *text* (and optional *emote*) for *duration* seconds."""
        if not text and emote is None:
            return
        self._text = text or ""
        self._emote = emote if (emote and not emote.isNull()) else None
        # Size the bubble to the full text immediately so it doesn't jump around
        # as characters type in; then reveal from zero.
        self._visible_chars = 0
        self._type_timer.stop()
        self._relayout()
        self._fading_out = False
        self._anim.stop()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(180)
        self._anim.start()
        # Delay typewriter start by 80ms so it begins after the fade-in.
        QTimer.singleShot(80, lambda: self._type_timer.start(38))
        self._hide_timer.start(int(duration * 1000))

    def _advance_char(self) -> None:
        if self._visible_chars < len(self._text):
            self._visible_chars += 1
            self.update()
        else:
            self._type_timer.stop()

    def _start_fade_out(self) -> None:
        self._type_timer.stop()
        self._fading_out = True
        self._anim.stop()
        self._anim.setStartValue(self.windowOpacity())
        self._anim.setEndValue(0.0)
        self._anim.setDuration(280)
        self._anim.start()

    def _on_anim_finished(self) -> None:
        if self._fading_out:
            self._fading_out = False
            self.hide()

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
            display = self._text[:self._visible_chars]
            p.drawText(text_area, Qt.TextWordWrap | Qt.AlignVCenter | Qt.AlignLeft, display)
        p.end()
