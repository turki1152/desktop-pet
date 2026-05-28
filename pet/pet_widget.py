"""
pet_widget.py
=============
The visible pet: a frameless, always-on-top, per-pixel-transparent window that
renders the current animation frame, runs the behaviour brain, and ties together
the extras -- speech bubbles, mood emotes, reminders and the right-click menu.

Design goals that keep it light:

* One small window the exact size of the sprite, moved around the screen rather
  than a giant full-screen overlay.
* A single ~30 FPS :class:`~PyQt5.QtCore.QTimer` drives everything; each tick
  just advances the animation, nudges the position, and repaints one pixmap.
* The speech bubble is a second tiny window that only exists while talking.
"""

from __future__ import annotations

import os
import random
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QActionGroup, QSystemTrayIcon

from .behavior import Behavior
from .bubble import SpeechBubble
from .character import Character, discover_characters
from .config import Settings
from .emotes import load_emotes, MENU_QSS
from .reminders import ReminderStore, ReminderDialog
from .sound import SoundPlayer
from .taskbar import get_taskbar_info, is_fullscreen_app_active

# Preset size / speed choices exposed in the right-click menu. Sizes are kept
# small on purpose -- a desktop pet should be a cute accent, not a billboard.
SIZE_PRESETS = {"Tiny": 0.4, "Small": 0.55, "Medium": 0.75, "Large": 1.0}
SPEED_PRESETS = {"Slow": 0.6, "Normal": 1.0, "Fast": 1.6, "Turbo": 2.4}

# Emotion -> (emote icon name, message category, bubble seconds).
EMOTIONS = {
    "happy": ("happy", "happy", 2.6),
    "angry": ("angry", "angry", 2.6),
    "sad": ("sad", "sad", 2.6),
    "surprised": ("surprised", "surprised", 1.8),
    "sleepy": ("music", "sleepy", 3.0),
    "talk": (None, "idle", 3.4),
}

TICK_MS = 33  # ~30 frames per second.


class PetWidget(QWidget):
    def __init__(self, characters_dir: str, assets_dir: str, settings: Settings):
        super().__init__()
        self.characters_dir = characters_dir
        self.settings = settings
        self.sound = SoundPlayer(muted=settings.muted)
        self.emotes = load_emotes(assets_dir)
        self.reminders = ReminderStore()

        # --- window appearance: invisible chrome, visible sprite only ----- #
        self.setWindowFlags(
            Qt.FramelessWindowHint        # no title bar / border
            | Qt.WindowStaysOnTopHint     # float above other windows
            | Qt.Tool                     # no taskbar button / alt-tab entry
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)  # true per-pixel alpha
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # --- runtime state read by the behaviour brain -------------------- #
        self.facing_left = False
        self.x = 0.0
        self.y = 0.0
        self.width_px = 0
        self.height_px = 0
        self.x_min = 0
        self.x_max = 0
        self.rest_y = 0
        self._taskbar_refresh = 0.0

        # --- interaction tracking (pat vs drag vs shake) ------------------ #
        self._dragging = False
        self._drag_offset = QPoint()
        self._press_time = 0.0
        self._drag_dist = 0.0
        self._reversals = 0
        self._last_dx = 0.0

        # --- chatter & reminder scheduling -------------------------------- #
        self._chatter_left = random.uniform(10, 22)
        self._reminder_accum = 0.0

        # --- auto-hide when a full-screen app is in front ----------------- #
        self._fs_accum = 0.0
        self._hidden_for_fullscreen = False

        # --- speech bubble (its own tiny window) -------------------------- #
        self.bubble = SpeechBubble()

        # --- load character + brain --------------------------------------- #
        self.character: Character | None = None
        self._load_character(settings.character, place_center=True)
        self.behavior = Behavior(self)

        # --- optional system-tray icon ------------------------------------ #
        self._build_tray()

        # --- the single heartbeat ----------------------------------------- #
        self._last_time = time.perf_counter()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

    # ------------------------------------------------------------------ #
    # Character loading / placement
    # ------------------------------------------------------------------ #
    def _load_character(self, key: str, place_center: bool = False) -> None:
        folder = os.path.join(self.characters_dir, key)
        try:
            character = Character(folder, scale=self.settings.scale)
        except Exception:
            available = discover_characters(self.characters_dir)
            if not available:
                raise
            character = Character(os.path.join(self.characters_dir, available[0]),
                                  scale=self.settings.scale)
            key = available[0]

        self.character = character
        size = character.animation("idle").size
        self.width_px, self.height_px = size.width(), size.height()
        self.setFixedSize(self.width_px, self.height_px)

        self._refresh_bounds()
        if place_center:
            self.x = (self.x_min + self.x_max - self.width_px) / 2
            self.y = self.rest_y
        else:
            self.x = max(self.x_min, min(self.x, self.x_max - self.width_px))
            self.y = self.rest_y

    def _refresh_bounds(self) -> None:
        """Recompute the walkable area from the current taskbar position."""
        info = get_taskbar_info()
        self.x_min = info.x_min
        self.x_max = info.x_max
        self.rest_y = (info.ground_y - self.height_px) if info.sits_above else info.ground_y

    # ------------------------------------------------------------------ #
    # The heartbeat
    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_time, 0.1)  # cap big jumps (sleep/resume)
        self._last_time = now
        speed = self.settings.speed

        # Hide while a full-screen app (game, video, slideshow) is in front, so
        # the pet never covers it. Checked about once a second to stay cheap.
        self._fs_accum += dt
        if self._fs_accum >= 1.0:
            self._fs_accum = 0.0
            self._update_fullscreen_visibility()
        if self._hidden_for_fullscreen:
            return  # nothing to animate while hidden.

        # Re-check the taskbar every couple of seconds (auto-hide, DPI, moves).
        self._taskbar_refresh += dt
        if self._taskbar_refresh >= 2.0:
            self._taskbar_refresh = 0.0
            if not self._dragging:
                self._refresh_bounds()

        self.behavior.tick(dt, speed)

        anim = self.character.animation(self.behavior.state)
        anim.update(dt, speed)

        self._update_chatter(dt)
        self._check_reminders(dt)

        self.move(round(self.x), round(self.y))
        if self.bubble.isVisible():
            self.bubble.reposition(self.geometry())
        self.update()

    def _update_fullscreen_visibility(self) -> None:
        """Hide the pet (and its bubble) under full-screen apps; restore after."""
        if self._dragging:
            return
        fullscreen = is_fullscreen_app_active()
        if fullscreen and not self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = True
            self.bubble.hide()
            self.hide()
        elif not fullscreen and self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()

    def _update_chatter(self, dt: float) -> None:
        """Occasionally show a random personality line while idle/walking."""
        if self._dragging or self.bubble.isVisible():
            return
        if self.behavior.state not in ("idle", "walk"):
            return
        self._chatter_left -= dt
        if self._chatter_left <= 0:
            self._chatter_left = random.uniform(28, 70)
            self.show_emotion("talk")

    def _check_reminders(self, dt: float) -> None:
        self._reminder_accum += dt
        if self._reminder_accum < 5.0:
            return
        self._reminder_accum = 0.0
        for r in self.reminders.due(datetime.now()):
            self.show_reminder(r.text)

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:
        anim = self.character.animation(self.behavior.state)
        pixmap = anim.current(self.facing_left)
        painter = QPainter(self)
        x = (self.width_px - pixmap.width()) // 2
        y = (self.height_px - pixmap.height()) // 2
        painter.drawPixmap(x, y, pixmap)
        painter.end()

    # ------------------------------------------------------------------ #
    # Hooks called by the behaviour brain
    # ------------------------------------------------------------------ #
    def on_state_changed(self, state: str) -> None:
        self.character.animation(state).reset()
        # A sleepy thought now and then when lying down.
        if state == "sleep" and random.random() < 0.6:
            self.show_emotion("sleepy")

    def on_land(self, impact: float) -> None:
        """Called by the brain when a fall ends; react to a hard landing."""
        if impact > 2300:
            self.show_emotion("sad")
        elif impact > 1500:
            self.show_emotion("surprised")

    def play_sound(self, event: str) -> None:
        self.sound.play(self.character.sounds.get(event))

    # ------------------------------------------------------------------ #
    # Speech bubble / emotions
    # ------------------------------------------------------------------ #
    def show_emotion(self, kind: str, text_override: str | None = None) -> None:
        emote_name, category, duration = EMOTIONS.get(kind, (None, kind, 2.5))
        text = text_override if text_override is not None else self.character.random_message(category)
        emote = self.emotes.get(emote_name) if emote_name else None
        if text is None and emote is None:
            return
        self.bubble.show_message(text, emote, duration)
        self.bubble.reposition(self.geometry())

    def show_reminder(self, text: str) -> None:
        self.bubble.show_message(text, self.emotes.get("bell"), 6.0)
        self.bubble.reposition(self.geometry())

    # ------------------------------------------------------------------ #
    # Mouse interaction: pat / drag / shake + right-click menu
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._press_time = time.perf_counter()
            self._drag_dist = 0.0
            self._reversals = 0
            self._last_dx = 0.0
            self.behavior.start_drag()
        elif event.button() == Qt.RightButton:
            self._show_menu(event.globalPos())

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        top_left = event.globalPos() - self._drag_offset
        new_x = max(self.x_min, min(top_left.x(), self.x_max - self.width_px))
        new_y = float(top_left.y())

        dx = new_x - self.x
        self._drag_dist += abs(dx) + abs(new_y - self.y)
        # Count direction reversals -> "shaking" detection.
        if dx and self._last_dx and ((dx > 0) != (self._last_dx > 0)):
            self._reversals += 1
        if dx:
            self._last_dx = dx

        self.x, self.y = new_x, new_y
        self.move(round(self.x), round(self.y))
        if self.bubble.isVisible():
            self.bubble.reposition(self.geometry())

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or not self._dragging:
            return
        self._dragging = False
        duration = time.perf_counter() - self._press_time

        if self._drag_dist < 8 and duration < 0.35:
            # A quick tap with no movement = an affectionate pat.
            self.behavior._enter_idle()
            self.show_emotion("happy")
        else:
            if self._reversals >= 4:
                self.show_emotion("angry")  # you shook the poor thing!
            self.behavior.start_fall()       # drop and fall to the taskbar.

    # ------------------------------------------------------------------ #
    # Context menu
    # ------------------------------------------------------------------ #
    def _show_menu(self, global_pos) -> None:
        menu = self._build_menu()
        menu.exec_(global_pos)

    def _build_menu(self) -> QMenu:
        menu = QMenu()
        menu.setStyleSheet(MENU_QSS)
        menu.setAttribute(Qt.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

        # --- Change character -------------------------------------------- #
        char_menu = menu.addMenu("🎭  Change character")
        group = QActionGroup(char_menu)
        group.setExclusive(True)
        for key in discover_characters(self.characters_dir):
            act = QAction(key.title(), char_menu, checkable=True)
            act.setChecked(key == self.character.key)
            act.triggered.connect(lambda _c, k=key: self._change_character(k))
            group.addAction(act)
            char_menu.addAction(act)

        # --- Size & Speed ------------------------------------------------ #
        self._add_preset_submenu(menu, "📏  Size", SIZE_PRESETS,
                                 self.settings.scale, self._change_scale)
        self._add_preset_submenu(menu, "⚡  Speed", SPEED_PRESETS,
                                 self.settings.speed, self._change_speed)

        menu.addSeparator()

        # --- Say something now ------------------------------------------- #
        say_act = QAction("💬  Say something", menu)
        say_act.triggered.connect(lambda: self.show_emotion("talk"))
        menu.addAction(say_act)

        # --- Reminders --------------------------------------------------- #
        self._build_reminders_menu(menu)

        menu.addSeparator()

        # --- Mute -------------------------------------------------------- #
        mute_act = QAction("🔊  Unmute" if self.settings.muted else "🔇  Mute", menu)
        mute_act.triggered.connect(self._toggle_mute)
        menu.addAction(mute_act)

        menu.addSeparator()
        exit_act = QAction("❌  Exit", menu)
        exit_act.triggered.connect(self._exit)
        menu.addAction(exit_act)
        return menu

    def _add_preset_submenu(self, menu, title, presets, current, handler):
        sub = menu.addMenu(title)
        grp = QActionGroup(sub)
        grp.setExclusive(True)
        for label, value in presets.items():
            act = QAction(label, sub, checkable=True)
            act.setChecked(abs(current - value) < 1e-3)
            act.triggered.connect(lambda _c, v=value: handler(v))
            grp.addAction(act)
            sub.addAction(act)

    def _build_reminders_menu(self, menu) -> None:
        rmenu = menu.addMenu("⏰  Reminders")
        add = QAction("➕  Add reminder…", rmenu)
        add.triggered.connect(self._add_reminder)
        rmenu.addAction(add)
        if self.reminders.items:
            rmenu.addSeparator()
        for i, r in enumerate(self.reminders.items):
            label = f"{r.time}   {r.text[:22]}" + ("" if r.enabled else "  (off)")
            sub = rmenu.addMenu(("🔔  " if r.enabled else "🔕  ") + label)
            toggle = QAction("Disable" if r.enabled else "Enable", sub)
            toggle.triggered.connect(lambda _c, idx=i: self._toggle_reminder(idx))
            delete = QAction("🗑  Delete", sub)
            delete.triggered.connect(lambda _c, idx=i: self._delete_reminder(idx))
            sub.addAction(toggle)
            sub.addAction(delete)

    # ------------------------------------------------------------------ #
    # Menu actions
    # ------------------------------------------------------------------ #
    def _change_character(self, key: str) -> None:
        self.settings.character = key
        self._load_character(key)
        self.behavior = Behavior(self)
        self._update_tray_icon()

    def _change_scale(self, value: float) -> None:
        self.settings.scale = value
        self._load_character(self.character.key)
        self.behavior = Behavior(self)
        self._update_tray_icon()

    def _change_speed(self, value: float) -> None:
        self.settings.speed = value

    def _toggle_mute(self) -> None:
        self.settings.muted = not self.settings.muted
        self.sound.muted = self.settings.muted
        if self.settings.muted:
            self.sound.stop()

    def _add_reminder(self) -> None:
        dialog = ReminderDialog()
        if dialog.exec_():
            time_str, text = dialog.result_values()
            if text:
                self.reminders.add(time_str, text)
                self.bubble.show_message(f"Reminder set for {time_str} ✓",
                                         self.emotes.get("bell"), 2.5)
                self.bubble.reposition(self.geometry())
        self._refresh_tray_menu()

    def _toggle_reminder(self, index: int) -> None:
        if 0 <= index < len(self.reminders.items):
            r = self.reminders.items[index]
            r.enabled = not r.enabled
            self.reminders.save()
        self._refresh_tray_menu()

    def _delete_reminder(self, index: int) -> None:
        self.reminders.remove(index)
        self._refresh_tray_menu()

    def _exit(self) -> None:
        self._timer.stop()
        self.bubble.hide()
        if getattr(self, "tray", None):
            self.tray.hide()
        from PyQt5.QtWidgets import QApplication
        QApplication.quit()

    # ------------------------------------------------------------------ #
    # System tray
    # ------------------------------------------------------------------ #
    def _build_tray(self) -> None:
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(self)
        self._update_tray_icon()
        self.tray.setToolTip("Desktop Pet")
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason) -> None:
        # Rebuild on open so checkmarks / reminders stay in sync.
        if reason in (QSystemTrayIcon.Context, QSystemTrayIcon.Trigger):
            self._refresh_tray_menu()

    def _refresh_tray_menu(self) -> None:
        if getattr(self, "tray", None):
            self.tray.setContextMenu(self._build_menu())

    def _update_tray_icon(self) -> None:
        if getattr(self, "tray", None):
            self.tray.setIcon(QIcon(self.character.animation("idle").current()))
