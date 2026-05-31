"""
pet_widget.py
=============
The visible pet: frameless, always-on-top, per-pixel-transparent window that
renders the current animation frame, runs the behaviour brain, and ties together
all the extras -- speech bubbles, mood, reactions, gags, and the right-click menu.
"""

from __future__ import annotations

import os
import random
import time
from datetime import datetime

from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QIcon
from PyQt5.QtWidgets import QWidget, QMenu, QAction, QActionGroup, QSystemTrayIcon

from .battery import BatteryMonitor
from .behavior import (Behavior,
                       IDLE, WALK, SLEEP, FALL, DRAG, JUMP,
                       FOLLOW, FLEE, CLING, TRIP,
                       THROW, BALLOON, ROCKET, PORTAL,
                       MOONWALK, STUCK, FROZEN, DANCE,
                       UPSIDE_DOWN, WINDOW_SIT, SLIDE_EDGE)
from .bubble import SpeechBubble
from .character import Character, discover_characters
from .config import Settings
from .emotes import load_emotes, MENU_QSS
from .mood import MoodSystem, MOOD_MESSAGES
from .multi_pet import PetManager
from .notes import QuickNotesWindow, TodoListWindow
from .particles import ParticleOverlay
from .reminders import ReminderStore, ReminderDialog, CountdownWindow
from .sound import SoundPlayer
from .settings_dialog import SettingsDialog
from .system_events import SystemMonitor, move_cursor, get_cursor_pos, get_app_window_tops, get_clipboard_text
from .taskbar import get_taskbar_info, is_fullscreen_app_active
from .weather import WeatherMonitor

SIZE_PRESETS  = {"Tiny": 0.4, "Small": 0.55, "Medium": 0.75, "Large": 1.0}
SPEED_PRESETS = {"Slow": 0.6, "Normal": 1.0, "Fast": 1.6, "Turbo": 2.4}

EMOTIONS = {
    "happy":    ("happy",    "happy",    2.6),
    "angry":    ("angry",    "angry",    2.6),
    "sad":      ("sad",      "sad",      2.6),
    "surprised":("surprised","surprised",1.8),
    "sleepy":   ("music",    "sleepy",   3.0),
    "excited":  ("happy",    "excited",  2.6),
    "talk":     (None,       "idle",     3.4),
}

TICK_MS = 33   # ~30 fps

_SEASONAL: dict[str, list[str]] = {
    "new_year":     ["Happy New Year! 🎆", "New year, new adventures!",
                     f"{datetime.now().year} is going to be great!"],
    "valentine":    ["Happy Valentine's Day! 💕", "Sending you some love~ ♥", "You are appreciated! 💖"],
    "halloween":    ["Happy Halloween! 🎃", "Spooky season is here!", "Trick or treat? 👻"],
    "christmas":    ["Merry Christmas! 🎄", "Ho ho ho~ 🎅", "Happy holidays! ⭐", "Season's greetings! 🎁"],
    "new_year_eve": ["Happy New Year's Eve! 🎉", "Almost midnight! 🥂", "The countdown begins!"],
}


def _seasonal_category(month: int, day: int) -> str | None:
    if month == 1  and day == 1:            return "new_year"
    if month == 12 and day == 31:           return "new_year_eve"
    if month == 2  and day == 14:           return "valentine"
    if month == 10 and 28 <= day <= 31:     return "halloween"
    if month == 12 and 24 <= day <= 25:     return "christmas"
    return None


def _season_particle_theme(month: int) -> str | None:
    """Return a particle theme for the current month, or None."""
    if month in (12, 1, 2):   return "snow"
    if month in (3, 4):       return "flowers"
    if month in (9, 10, 11):  return "leaves"
    return None


class PetWidget(QWidget):
    def __init__(self, characters_dir: str, assets_dir: str, settings: Settings,
                 manager: PetManager | None = None, first_run: bool = False):
        super().__init__()
        self.characters_dir = characters_dir
        self.assets_dir     = assets_dir
        self.settings       = settings
        self.sound          = SoundPlayer(muted=settings.muted)
        self.emotes         = load_emotes(assets_dir)
        self.reminders      = ReminderStore()
        self._manager       = manager or PetManager.get()

        # Assign a birthday on first run (also record this year so the
        # celebration doesn't fire immediately on the day of first install).
        if not settings.pet_birthday:
            now = datetime.now()
            settings.pet_birthday = now.strftime("%m-%d")
            settings.last_birthday_year = now.year

        # --- Window flags -------------------------------------------- #
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # --- Runtime position state ---------------------------------- #
        self.facing_left = False
        self.x = 0.0
        self.y = 0.0
        self.width_px  = 0
        self.height_px = 0
        self.x_min = 0
        self.x_max = 0
        self.rest_y = 0
        self._taskbar_refresh = 0.0

        # --- Mouse interaction --------------------------------------- #
        self._dragging    = False
        self._drag_offset = QPoint()
        self._press_time  = 0.0
        self._drag_dist   = 0.0
        self._reversals   = 0
        self._last_dx     = 0.0
        # Throw velocity tracking (rolling average of mouse movement).
        self._drag_vx     = 0.0
        self._drag_vy     = 0.0
        self._drag_prev_x = 0.0
        self._drag_prev_y = 0.0

        # --- Chatter & reminders ------------------------------------- #
        self._chatter_left   = random.uniform(10, 22)
        self._reminder_accum = 0.0

        # --- Name recognition (clipboard) ---------------------------- #
        self._name_check_accum = 0.0
        self._last_clipboard   = ""

        # --- Fullscreen auto-hide ------------------------------------ #
        self._fs_accum             = 0.0
        self._hidden_for_fullscreen= False
        self._fs_active            = False   # used by SystemMonitor

        # --- Multi-pet interaction timer ----------------------------- #
        self._peer_chat_accum = random.uniform(30, 60)

        # --- Seasonal decoration timer ------------------------------- #
        self._seasonal_accum = random.uniform(90, 180)   # don't fire on startup

        # --- Cursor-steal gag state ---------------------------------- #
        self._steal_timer    = 0.0
        self._stolen_to_x    = 0
        self._stolen_to_y    = 0
        self._orig_cursor_x  = 0
        self._orig_cursor_y  = 0

        # --- Birthday check ------------------------------------------ #
        self._birthday_fired = False

        # --- Sub-windows (created lazily / once) --------------------- #
        self.bubble    = SpeechBubble()
        self.particles = ParticleOverlay()
        self._notes_win: QuickNotesWindow | None = None
        self._todo_win:  TodoListWindow   | None = None
        self._countdown: CountdownWindow  | None = None

        # --- System monitors ---------------------------------------- #
        self.mood_system     = MoodSystem(settings.mood_score)
        self._mood_save_accum = 0.0
        self._battery        = BatteryMonitor()
        self._sys_monitor    = SystemMonitor()
        self._weather        = WeatherMonitor(settings.weather_city)

        # --- Load character + brain ---------------------------------- #
        self.character: Character | None = None
        self._load_character(settings.character, place_center=True)
        self.behavior = Behavior(self)

        # Register with manager.
        self._manager.register(self)

        # --- System tray --------------------------------------------- #
        self._build_tray()

        # --- Heartbeat ------------------------------------------------ #
        self._last_time = time.perf_counter()
        self._timer     = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(TICK_MS)

        # --- First-run welcome --------------------------------------- #
        if first_run:
            QTimer.singleShot(1200, self._show_welcome)

    # ------------------------------------------------------------------ #
    # Character loading
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
        info = get_taskbar_info()
        self.x_min  = info.x_min
        self.x_max  = info.x_max
        floor_off = self.character.floor_offset if self.character else 0
        self.rest_y = (info.ground_y - self.height_px + floor_off) if info.sits_above \
                      else (info.ground_y - floor_off)

    @property
    def current_mood(self) -> str:
        return self.mood_system.mood

    # ------------------------------------------------------------------ #
    # Main heartbeat
    # ------------------------------------------------------------------ #
    def _tick(self) -> None:
        now = time.perf_counter()
        dt  = min(now - self._last_time, 0.1)
        self._last_time = now
        speed = self.settings.speed

        # --- Fullscreen hide ---------------------------------------- #
        self._fs_accum += dt
        if self._fs_accum >= 1.0:
            self._fs_accum  = 0.0
            self._fs_active = is_fullscreen_app_active()
            self._update_fullscreen_visibility()
        if self._hidden_for_fullscreen:
            return

        # --- Taskbar bounds refresh --------------------------------- #
        self._taskbar_refresh += dt
        if self._taskbar_refresh >= 2.0:
            self._taskbar_refresh = 0.0
            if not self._dragging:
                self._refresh_bounds()

        # --- Mood --------------------------------------------------- #
        self.mood_system.tick(dt)
        self._mood_save_accum += dt
        if self._mood_save_accum >= 30.0:
            self._mood_save_accum = 0.0
            self.settings.mood_score = self.mood_system.score
            self._update_tray_tooltip()

        # --- System monitors ---------------------------------------- #
        if self.settings.reaction_battery:
            self._tick_battery(dt)
        self._tick_system_events(dt)
        if self.settings.weather_enabled:
            self._tick_weather(dt)

        # --- Birthday check ----------------------------------------- #
        if not self._birthday_fired and self.settings.reaction_birthday:
            self._check_birthday()

        # --- Magnet mode -------------------------------------------- #
        if self.settings.magnet_mode and self.behavior.state in (IDLE, WALK, FOLLOW):
            self._tick_magnet(dt)

        # --- Cursor-steal gag countdown ----------------------------- #
        if self._steal_timer > 0:
            self._steal_timer -= dt
            if self._steal_timer <= 0:
                move_cursor(self._orig_cursor_x, self._orig_cursor_y)

        # --- Behavior + animation ----------------------------------- #
        self.behavior.tick(dt, speed)
        anim = self.character.animation(self.behavior.animation_state)
        if not self.behavior.anim_frozen:
            anim.update(dt, speed, reverse=self.behavior.anim_reversed)

        # --- Chatter & reminders ------------------------------------ #
        self._update_chatter(dt)
        self._check_reminders(dt)
        self._check_name_in_clipboard(dt)

        # --- Multi-pet interactions --------------------------------- #
        self._tick_peer_chat(dt)

        # --- Seasonal decorations ----------------------------------- #
        self._tick_seasonal(dt)

        # --- Paint + bubble reposition ------------------------------ #
        self.move(round(self.x), round(self.y))
        if self.bubble.isVisible():
            self.bubble.reposition(self.geometry())
        self.update()

    # ------------------------------------------------------------------ #
    # Fullscreen visibility
    # ------------------------------------------------------------------ #
    def _update_fullscreen_visibility(self) -> None:
        if self._dragging:
            return
        if not self.settings.hide_fullscreen:
            if self._hidden_for_fullscreen:
                self._hidden_for_fullscreen = False
                self.show()
            return
        if self._fs_active and not self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = True
            self.bubble.hide()
            self.hide()
        elif not self._fs_active and self._hidden_for_fullscreen:
            self._hidden_for_fullscreen = False
            self.show()

    # ------------------------------------------------------------------ #
    # Battery reactions
    # ------------------------------------------------------------------ #
    _BATTERY_MSGS = {
        "charging":  ["Oh! The charger is plugged in! ⚡", "Charging up~  ⚡", "Power incoming! ⚡"],
        "unplugged": ["Uh-oh, charger removed!", "Going wireless now...", "Unplugged!"],
        "full":      ["Battery full! 🔋 Ready for anything!", "100%! Fully charged! 🔋✨"],
        "low":       ["Hey! Battery is low! 🔋 Plug in soon!", "Low battery warning... save your work! ⚠️"],
        "critical":  ["CRITICAL BATTERY!! 🆘 Plug in NOW!", "Emergency! Battery dying!! 😱"],
    }

    def _tick_battery(self, dt: float) -> None:
        for event in self._battery.tick(dt):
            msgs = self._BATTERY_MSGS.get(event, [])
            if msgs:
                text = random.choice(msgs)
                emotion = "angry" if event == "critical" else \
                          "surprised" if event == "low" else "happy"
                self.show_emotion(emotion, text_override=text)
            if event == "critical":
                self.mood_system.on_shake()
            elif event in ("full", "charging"):
                self.mood_system.on_pat()

    # ------------------------------------------------------------------ #
    # System event reactions
    # ------------------------------------------------------------------ #
    _SYS_MSGS = {
        "user_away":      ["... * cricket sounds *", "Where did you go?", "Hello?? Anyone there? 👀"],
        "user_back":      ["Welcome back! 😊", "Oh hi! You're back!", "There you are! I missed you~"],
        "gaming_warning": ["You've been gaming for an hour! Take a break! 🎮",
                           "Your eyes need a rest... step away for a bit!", "Break time! 🎮☕"],
        "download_new":   ["Ooh a new download! 🎉", "Something just downloaded!", "New file! ✨"],
        "folder_open":    ["Ooh what's in those folders? 👀", "I see files! Let me look..."],
        "folder_closed":  ["The explorer is gone. Bye folders!"],
    }

    def _tick_system_events(self, dt: float) -> None:
        s = self.settings
        _event_allowed = {
            "user_away":      s.reaction_idle,
            "user_back":      s.reaction_idle,
            "gaming_warning": s.reaction_gaming,
            "download_new":   s.reaction_downloads,
            "folder_open":    s.reaction_folder,
            "folder_closed":  s.reaction_folder,
        }
        for event in self._sys_monitor.tick(dt, self._fs_active):
            if not _event_allowed.get(event, True):
                continue
            msgs = self._SYS_MSGS.get(event, [])
            if msgs:
                text = random.choice(msgs)
                emotion = "surprised" if event in ("user_away", "gaming_warning") else \
                          "happy"    if event in ("user_back", "download_new") else "talk"
                self.show_emotion(emotion, text_override=text)
            if event == "user_back":
                self.mood_system.on_interact()
                if hasattr(self, "behavior"):
                    self.behavior.reset_boredom()
            if event == "download_new":
                geo = self.geometry()
                self.particles.spawn(geo.center().x(), geo.top(), count=12)

    # ------------------------------------------------------------------ #
    # Weather reactions
    # ------------------------------------------------------------------ #
    def _tick_weather(self, dt: float) -> None:
        new_cond = self._weather.tick(dt)
        if new_cond:
            reaction = self._weather.random_reaction()
            if reaction:
                self.show_emotion("talk", text_override=reaction)
            # Affect mood slightly.
            if new_cond == "sunny":
                self.mood_system.on_pat()
            elif new_cond in ("thunder", "rain"):
                self.mood_system.on_interact()

    # ------------------------------------------------------------------ #
    # Birthday check
    # ------------------------------------------------------------------ #
    def _check_birthday(self) -> None:
        now = datetime.now()
        today = now.strftime("%m-%d")
        # Fire once per calendar year — never on the first run (year would match).
        if (today == self.settings.pet_birthday
                and now.year != self.settings.last_birthday_year):
            self.settings.last_birthday_year = now.year
            self._birthday_fired = True
            msgs = [
                "IT'S MY BIRTHDAY! 🎂🎉",
                "Today is my birthday!! 🎂 Make a wish!",
                "Birthday time!! 🎊🎂",
            ]
            self.show_emotion("happy", text_override=random.choice(msgs))
            geo = self.geometry()
            self.particles.spawn_seasonal("confetti", count=40)
            self.particles.spawn(geo.center().x(), geo.top(), count=15)
            self.mood_system.on_pat()
            self.mood_system.on_pat()

    # ------------------------------------------------------------------ #
    # Magnet mode
    # ------------------------------------------------------------------ #
    def _tick_magnet(self, dt: float) -> None:
        from PyQt5.QtGui import QCursor
        c      = QCursor.pos()
        pet_cx = self.x + self.width_px / 2
        pet_cy = self.y + self.height_px / 2
        dist   = ((c.x() - pet_cx) ** 2 + (c.y() - pet_cy) ** 2) ** 0.5
        if dist < 10 or dist > 500:
            return
        # Inverse-distance force, capped so the pet can't teleport
        force = min(220.0, 6000.0 / max(dist, 1.0))
        dx    = (c.x() - pet_cx) / max(dist, 1.0)
        sign  = 1 if self.settings.magnet_attract else -1
        self.x = max(self.x_min,
                     min(self.x + sign * dx * force * dt,
                         self.x_max - self.width_px))

    # ------------------------------------------------------------------ #
    # Multi-pet interactions
    # ------------------------------------------------------------------ #
    _PEER_CHAT = [
        ("Hey! Over here! 👋", "happy"),
        ("*waves at the other pet* Hi!", "happy"),
        ("We should play together sometime~", "talk"),
        ("There's another one of us! 😮", "surprised"),
        ("*nudges the other pet*", "talk"),
        ("You look familiar...", "talk"),
    ]
    _RIVAL_CHAT = [
        ("Stay away from my turf! 😤", "angry"),
        ("Hmph. Not happy to see you.", "angry"),
        ("*glares* ...", "angry"),
    ]
    _JEALOUS_MSGS = [
        "Wait, there's ANOTHER pet?! 😤",
        "Hey! Pay attention to ME! 😠",
        "I was here first!! 😤",
    ]

    def _tick_peer_chat(self, dt: float) -> None:
        self._peer_chat_accum -= dt
        if self._peer_chat_accum > 0:
            return
        self._peer_chat_accum = random.uniform(25, 55)

        nearby = self._manager.nearby(self, radius=250)
        if not nearby:
            return
        other = random.choice(nearby)

        if self._manager.is_rival_pair(self, other):
            text, kind = random.choice(self._RIVAL_CHAT)
        else:
            text, kind = random.choice(self._PEER_CHAT)

        self.show_emotion(kind, text_override=text)
        # Mirror reaction in the other pet.
        if random.random() < 0.5:
            display = self.settings.pet_name or self.character.name
            other.show_emotion("surprised", text_override=f"*notices {display}*")

    # ------------------------------------------------------------------ #
    # Seasonal decorations
    # ------------------------------------------------------------------ #
    def _tick_seasonal(self, dt: float) -> None:
        if not self.settings.reaction_seasonal:
            return
        now = datetime.now()
        theme = _season_particle_theme(now.month)
        if not theme:
            return
        self._seasonal_accum -= dt
        if self._seasonal_accum <= 0:
            self._seasonal_accum = random.uniform(90, 180)
            self.particles.spawn_seasonal(theme, count=15)

    # ------------------------------------------------------------------ #
    # Chatter
    # ------------------------------------------------------------------ #
    # Chatter interval per frequency setting.
    _CHATTER_RANGES = {
        "rarely": (60, 120), "normal": (28, 70),
        "often":  (12, 30),  "always": (4, 12),
    }

    def _update_chatter(self, dt: float) -> None:
        if self._dragging or self.bubble.isVisible():
            return
        if self.behavior.state not in (IDLE, WALK, FOLLOW, CLING):
            return
        self._chatter_left -= dt
        if self._chatter_left <= 0:
            lo, hi = self._CHATTER_RANGES.get(self.settings.chatter_freq, (28, 70))
            self._chatter_left = random.uniform(lo, hi)
            now = datetime.now()
            text: str | None = None

            season = _seasonal_category(now.month, now.day)
            if season and random.random() < 0.20:
                char_lines = self.character.messages.get(season)
                text = random.choice(char_lines if char_lines else _SEASONAL[season])

            if text is None:
                time_cat = ("morning" if 5 <= now.hour < 12 else
                            "afternoon" if 12 <= now.hour < 17 else
                            "evening" if 17 <= now.hour < 21 else "night")
                if random.random() < 0.35:
                    text = self.character.random_message(time_cat)

            mood = self.mood_system.mood
            if text is None and mood != "neutral" and random.random() < 0.25:
                lines = MOOD_MESSAGES.get(mood, [])
                if lines:
                    char_lines = self.character.messages.get(mood)
                    text = random.choice(char_lines if char_lines else lines)

            # User custom lines.
            if text is None:
                custom = self.settings.custom_lines
                if custom and random.random() < 0.30:
                    text = random.choice(custom)

            self.show_emotion("talk", text_override=text)

    def _check_reminders(self, dt: float) -> None:
        self._reminder_accum += dt
        if self._reminder_accum < 5.0:
            return
        self._reminder_accum = 0.0
        for r in self.reminders.due(datetime.now()):
            self.show_reminder(r.text)

    _NAME_REACTIONS = [
        "Did someone call me? 👀",
        "I heard my name! 🐾",
        "Yes? You called? 😊",
        "That's me! 🐾",
        "Hey, that's my name!",
    ]

    def _check_name_in_clipboard(self, dt: float) -> None:
        name = self.settings.pet_name
        if not name:
            return
        self._name_check_accum += dt
        if self._name_check_accum < 4.0:
            return
        self._name_check_accum = 0.0
        text = get_clipboard_text()
        if text and text != self._last_clipboard:
            self._last_clipboard = text
            if name.lower() in text.lower():
                self.show_emotion("happy", text_override=random.choice(self._NAME_REACTIONS))

    # ------------------------------------------------------------------ #
    # Painting
    # ------------------------------------------------------------------ #
    def paintEvent(self, _event) -> None:
        anim   = self.character.animation(self.behavior.animation_state)
        pixmap = anim.current(self.facing_left)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        if self.behavior.upside_down:
            # Flip the pixmap vertically around the widget center.
            cx = self.width_px  / 2.0
            cy = self.height_px / 2.0
            painter.translate(cx, cy)
            painter.scale(1.0, -1.0)
            painter.translate(-cx, -cy)

        x_off = (self.width_px  - pixmap.width())  // 2
        y_off = (self.height_px - pixmap.height()) // 2
        painter.drawPixmap(x_off, y_off, pixmap)
        painter.end()

    # ------------------------------------------------------------------ #
    # Behaviour callbacks
    # ------------------------------------------------------------------ #
    def on_state_changed(self, state: str) -> None:
        if not hasattr(self, "behavior"):
            return
        self.character.animation(self.behavior.animation_state).reset()
        if state == "sleep" and random.random() < 0.6:
            self.show_emotion("sleepy")

    def on_land(self, impact: float) -> None:
        if impact > 2300:
            self.show_emotion("sad")
        elif impact > 1500:
            self.show_emotion("surprised")

    def play_sound(self, event: str) -> None:
        path = self.settings.custom_sounds.get(event) or self.character.sounds.get(event)
        self.sound.play(path)

    # ------------------------------------------------------------------ #
    # Emotions / speech
    # ------------------------------------------------------------------ #
    def show_emotion(self, kind: str, text_override: str | None = None) -> None:
        if not self.isVisible():
            return
        emote_name, category, base_dur = EMOTIONS.get(kind, (None, kind, 2.5))
        text  = text_override if text_override is not None else self.character.random_message(category)
        emote = self.emotes.get(emote_name) if emote_name else None
        if text is None and emote is None:
            return
        # Scale base duration by the user's bubble_duration preference (normal=3.0).
        duration = base_dur * (self.settings.bubble_duration / 3.0)
        self.bubble.show_message(text, emote, duration)
        self.bubble.reposition(self.geometry())

    def show_reminder(self, text: str) -> None:
        if not self.isVisible():
            return
        self.bubble.show_message(text, self.emotes.get("bell"), 6.0)
        self.bubble.reposition(self.geometry())

    # ------------------------------------------------------------------ #
    # Mouse interaction
    # ------------------------------------------------------------------ #
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging    = True
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._press_time  = time.perf_counter()
            self._drag_dist   = 0.0
            self._reversals   = 0
            self._last_dx     = 0.0
            self._drag_vx     = 0.0
            self._drag_vy     = 0.0
            gp = event.globalPos()
            self._drag_prev_x = float(gp.x())
            self._drag_prev_y = float(gp.y())
            self.behavior.start_drag()
            self.behavior.reset_boredom()
            self.mood_system.on_interact()
        elif event.button() == Qt.RightButton:
            self._show_menu(event.globalPos())

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        top_left = event.globalPos() - self._drag_offset
        new_x    = max(self.x_min, min(float(top_left.x()), self.x_max - self.width_px))
        new_y    = float(top_left.y())

        dx = new_x - self.x
        dy = new_y - self.y
        self._drag_dist += abs(dx) + abs(dy)
        if dx and self._last_dx and ((dx > 0) != (self._last_dx > 0)):
            self._reversals += 1
            if self._reversals == 4:  # show angry the moment shaking is detected
                self.mood_system.on_shake()
                self.show_emotion("angry")
        if dx:
            self._last_dx = dx

        # Rolling velocity (exponential smoothing for throw).
        alpha         = 0.35
        gp            = event.globalPos()
        raw_vx        = gp.x() - self._drag_prev_x
        raw_vy        = gp.y() - self._drag_prev_y
        self._drag_vx = (1 - alpha) * self._drag_vx + alpha * raw_vx / max(TICK_MS / 1000.0, 0.001)
        self._drag_vy = (1 - alpha) * self._drag_vy + alpha * raw_vy / max(TICK_MS / 1000.0, 0.001)
        self._drag_prev_x = float(gp.x())
        self._drag_prev_y = float(gp.y())

        self.x, self.y = new_x, new_y
        self.move(round(self.x), round(self.y))
        if self.bubble.isVisible():
            self.bubble.reposition(self.geometry())

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.mood_system.on_interact()
            self.behavior.reset_boredom()
            self.show_emotion("talk")

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.LeftButton or not self._dragging:
            return
        self._dragging = False
        duration = time.perf_counter() - self._press_time

        if self._drag_dist < 8 and duration < 0.35:
            # Quick tap = affectionate pat.
            self.mood_system.on_pat()
            self.behavior.reset_boredom()
            self.behavior.start_jump()
            self.show_emotion("happy")
        else:
            if self._reversals >= 4:
                self.mood_system.on_shake()
                self.show_emotion("angry")
            else:
                self.mood_system.on_interact()
                self.behavior.reset_boredom()

            # Throw if released with significant velocity.
            speed = (self._drag_vx ** 2 + self._drag_vy ** 2) ** 0.5
            if speed > 300:
                self.behavior.start_throw(self._drag_vx, self._drag_vy)
            else:
                self.behavior.start_fall()

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

        # Settings — top of menu.
        settings_act = QAction("⚙  Settings…", menu)
        settings_act.triggered.connect(self._open_settings)
        menu.addAction(settings_act)
        menu.addSeparator()

        # Mood display (read-only).
        name = self.settings.pet_name
        mood_label = (f"{self.mood_system.emoji}  {name}  •  {self.mood_system.mood.title()}"
                      if name else
                      f"{self.mood_system.emoji}  {self.mood_system.mood.title()}")
        mood_act = QAction(mood_label, menu)
        mood_act.setEnabled(False)
        menu.addAction(mood_act)
        menu.addSeparator()

        # Appearance sub-menu (Character + Size + Speed collapsed).
        appear_menu = menu.addMenu("🎭  Appearance")
        char_menu = appear_menu.addMenu("Character")
        group = QActionGroup(char_menu)
        group.setExclusive(True)
        for key in discover_characters(self.characters_dir):
            act = QAction(key.title(), char_menu, checkable=True)
            act.setChecked(key == self.character.key)
            act.triggered.connect(lambda _c, k=key: self._change_character(k))
            group.addAction(act)
            char_menu.addAction(act)
        self._add_preset_submenu(appear_menu, "Size",  SIZE_PRESETS,
                                 self.settings.scale, self._change_scale)
        self._add_preset_submenu(appear_menu, "Speed", SPEED_PRESETS,
                                 self.settings.speed, self._change_speed)

        menu.addSeparator()

        # Fun & Gags sub-menu.
        fun_menu = menu.addMenu("🎉  Fun & Gags")
        for label, cb in [
            ("🎈  Give balloon",      lambda: self.behavior.start_balloon()),
            ("🚀  Launch rocket",     lambda: self.behavior.start_rocket()),
            ("🌀  Portal teleport",   lambda: self.behavior.start_portal()),
            ("🕺  Dance",             lambda: self.behavior.start_dance()),
            ("🌙  Moonwalk",          lambda: self.behavior.start_moonwalk()),
            ("🙃  Flip upside-down",  lambda: self.behavior.start_upside_down()),
            ("🥶  Frozen",            lambda: self.behavior.start_frozen()),
            ("😵  Stuck",             lambda: self.behavior.start_stuck()),
            ("📍  Slide off edge",    lambda: self.behavior.start_slide_edge()),
            ("😈  Steal cursor",      self._steal_cursor_gag),
            ("💥  Break desktop",     self._pretend_break_desktop),
            ("🌨  Scatter particles", self._scatter_seasonal),
            ("☁  Say weather",       self._say_weather),
        ]:
            a = QAction(label, fun_menu)
            a.triggered.connect(cb)
            fun_menu.addAction(a)

        # Magic items sub-menu.
        items_menu = menu.addMenu("🧪  Magic items")

        # Magnet — 3-way exclusive: Off / Attract / Repel.
        mag_menu = items_menu.addMenu("🧲  Magnet")
        mag_group = QActionGroup(mag_menu)
        mag_group.setExclusive(True)
        for _label, _mode, _attract in [
            ("Off",          False, True),
            ("🧲  Attract",  True,  True),
            ("↩  Repel",     True,  False),
        ]:
            _act = QAction(_label, mag_menu, checkable=True)
            _is_current = (
                (not _mode and not self.settings.magnet_mode) or
                (_mode and self.settings.magnet_mode and
                 self.settings.magnet_attract == _attract)
            )
            _act.setChecked(_is_current)
            _act.triggered.connect(
                lambda _c, m=_mode, a=_attract: self._set_magnet(m, a))
            mag_group.addAction(_act)
            mag_menu.addAction(_act)

        sit_act = QAction("🪟  Sit on window", items_menu)
        sit_act.triggered.connect(self._sit_on_window)
        items_menu.addAction(sit_act)

        menu.addSeparator()

        # Productivity sub-menu (includes Reminders).
        prod_menu = menu.addMenu("📋  Productivity")
        self._build_reminders_menu(prod_menu)
        prod_menu.addSeparator()

        notes_act = QAction("📝  Quick notes", prod_menu)
        notes_act.triggered.connect(self._open_notes)
        prod_menu.addAction(notes_act)

        todo_act = QAction("✅  To-do list", prod_menu)
        todo_act.triggered.connect(self._open_todo)
        prod_menu.addAction(todo_act)

        timer_act = QAction("⏱  Countdown / Pomodoro", prod_menu)
        timer_act.triggered.connect(self._open_countdown)
        prod_menu.addAction(timer_act)

        menu.addSeparator()

        # Multi-pet sub-menu.
        pets_menu = menu.addMenu(f"🐾  Pets  ({self._manager.count()})")
        spawn_act = QAction("➕  Spawn another pet", pets_menu)
        spawn_act.triggered.connect(self._spawn_pet)
        pets_menu.addAction(spawn_act)

        clone_act = QAction("🐑  Spawn clone", pets_menu)
        clone_act.triggered.connect(self._spawn_clone)
        pets_menu.addAction(clone_act)

        if len(self._manager.pets) > 1:
            dismiss_act = QAction("❌  Dismiss this pet", pets_menu)
            dismiss_act.triggered.connect(self._dismiss_self)
            pets_menu.addAction(dismiss_act)

        menu.addSeparator()

        mute_act = QAction("🔊  Unmute" if self.settings.muted else "🔇  Mute", menu)
        mute_act.triggered.connect(self._toggle_mute)
        menu.addAction(mute_act)

        visible_act = QAction("👁  Hide pet" if self.isVisible() else "👁  Show pet", menu)
        visible_act.triggered.connect(self._toggle_visibility)
        menu.addAction(visible_act)

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
            prefix = ("🔔  " if r.enabled else "🔕  (Off)  ")
            label  = prefix + f"{r.time}  {r.text[:26]}"
            sub    = rmenu.addMenu(label)
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
        # Notify other pets (jealousy only if there are already peers).
        for other in self._manager.visible_others(self):
            other.show_emotion("surprised",
                               text_override=f"Whoa, {key.title()}?! Lucky you!")
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

    def _set_magnet(self, mode: bool, attract: bool) -> None:
        self.settings.magnet_mode    = mode
        self.settings.magnet_attract = attract
        if mode:
            label = "Attract 🧲" if attract else "Repel ↩"
            self.show_emotion("talk", text_override=f"Magnet {label} ON")
        else:
            self.show_emotion("talk", text_override="Magnet OFF")

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
            self.reminders.items[index].enabled = not self.reminders.items[index].enabled
            self.reminders.save()
        self._refresh_tray_menu()

    def _delete_reminder(self, index: int) -> None:
        self.reminders.remove(index)
        self._refresh_tray_menu()

    def _toggle_visibility(self) -> None:
        if self.isVisible():
            self.bubble.hide()
            self.hide()
        else:
            self.show()
            self._refresh_tray_menu()

    def _open_settings(self) -> None:
        pet_pix = self.character.animation("idle").current()
        dialog = SettingsDialog(self.settings, self.characters_dir, self.assets_dir,
                                pet_pixmap=pet_pix)
        if dialog.exec_():
            dialog.apply(self)
            self._refresh_tray_menu()

    def _open_notes(self) -> None:
        if self._notes_win is None:
            self._notes_win = QuickNotesWindow()
        self._notes_win.show()
        self._notes_win.raise_()

    def _open_todo(self) -> None:
        if self._todo_win is None:
            self._todo_win = TodoListWindow()
        self._todo_win.show()
        self._todo_win.raise_()

    def _open_countdown(self) -> None:
        if self._countdown is None:
            self._countdown = CountdownWindow(on_finish=self._on_timer_done)
        self._countdown.show()
        self._countdown.raise_()

    def _on_timer_done(self, label: str) -> None:
        msgs = [
            f"{label} is done! ⏱",
            f"Time's up! ({label}) 🔔",
            f"Timer finished: {label} ✅",
        ]
        self.show_emotion("surprised", text_override=random.choice(msgs))
        geo = self.geometry()
        self.particles.spawn(geo.center().x(), geo.top(), count=10)

    # ------------------------------------------------------------------ #
    # Gag actions
    # ------------------------------------------------------------------ #
    def _steal_cursor_gag(self) -> None:
        """Briefly move the cursor to a silly spot then return it."""
        self._orig_cursor_x, self._orig_cursor_y = get_cursor_pos()
        # Teleport cursor to opposite side of the screen.
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        tx = screen.width()  - self._orig_cursor_x
        ty = screen.height() - self._orig_cursor_y
        move_cursor(tx, ty)
        self._stolen_to_x = tx
        self._stolen_to_y = ty
        self._steal_timer = 1.0
        self.show_emotion("happy", text_override="Hehe! Got your cursor! 😈")

    def _pretend_break_desktop(self) -> None:
        """Flash a red overlay twice and act panicked."""
        from PyQt5.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        flash = QWidget()
        flash.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        flash.setAttribute(Qt.WA_ShowWithoutActivating)
        flash.setAttribute(Qt.WA_DeleteOnClose)
        flash.setStyleSheet("background: red;")
        flash.setWindowOpacity(0.28)
        flash.setGeometry(screen.geometry())
        flash.show()
        QTimer.singleShot(300, flash.hide)
        QTimer.singleShot(380, flash.show)
        QTimer.singleShot(650, flash.close)
        self.show_emotion("surprised", text_override="Oops… did I do that?! 💥")

    def _scatter_seasonal(self) -> None:
        now   = datetime.now()
        theme = _season_particle_theme(now.month) or "confetti"
        self.particles.spawn_seasonal(theme, count=35)

    def _say_weather(self) -> None:
        cond = self._weather.condition
        if cond == "unknown":
            self.show_emotion("talk", text_override="I don't know the weather yet… check back soon! ☁")
            return
        reaction = self._weather.random_reaction()
        self.show_emotion("talk", text_override=reaction or f"It's {cond} outside!")

    def _sit_on_window(self) -> None:
        """Try to find a window and sit on top of it."""
        tops = get_app_window_tops()
        # Window must be above the taskbar and wide enough to walk on.
        # No lower bound on yt — we clamp the target y so the pet stays
        # fully on-screen even on maximized windows (yt ≈ 0 or negative).
        candidates = [
            (xl, xr, yt) for xl, xr, yt in tops
            if yt < self.rest_y - 10
            and (xr - xl) > self.width_px * 3
        ]
        if not candidates:
            self.show_emotion("sad", text_override="No windows to sit on!")
            return
        xl, xr, yt = random.choice(candidates)
        # Clamp so the pet's top edge is never above y=0 (never off-screen).
        target_y = max(yt, self.height_px)
        mid_x = (xl + xr) / 2.0
        self.behavior.start_window_sit(mid_x, target_y, xl, xr)
        self.show_emotion("happy", text_override="*climbs onto the window*")

    # ------------------------------------------------------------------ #
    # Multi-pet
    # ------------------------------------------------------------------ #
    def _spawn_pet(self) -> None:
        # Notify existing pets (jealousy).
        for other in self._manager.pets:
            if other is not self:
                other.show_emotion("angry",
                                   text_override=random.choice(self._JEALOUS_MSGS))
        new_pet = PetWidget(self.characters_dir, self.assets_dir,
                            self.settings, self._manager)
        new_pet.show()
        self._refresh_tray_menu()

    def _spawn_clone(self) -> None:
        """Spawn a new pet that starts as the same character as this one."""
        for other in self._manager.pets:
            if other is not self:
                other.show_emotion("angry",
                                   text_override=random.choice(self._JEALOUS_MSGS))
        new_pet = PetWidget(self.characters_dir, self.assets_dir,
                            self.settings, self._manager)
        new_pet._load_character(self.character.key)
        new_pet.behavior = Behavior(new_pet)
        new_pet.show()
        self._refresh_tray_menu()

    def _dismiss_self(self) -> None:
        self._manager.unregister(self)
        self._timer.stop()
        self.bubble.hide()
        if getattr(self, "tray", None):
            self.tray.hide()
        if self._countdown is not None:
            self._countdown.close()
            self._countdown = None
        if self._notes_win is not None:
            self._notes_win.close()
            self._notes_win = None
        if self._todo_win is not None:
            self._todo_win.close()
            self._todo_win = None
        self.close()

    # ------------------------------------------------------------------ #
    # Countdown finish callback
    # ------------------------------------------------------------------ #

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
        self._update_tray_tooltip()
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _show_welcome(self) -> None:
        name = self.settings.pet_name or "your new Desktop Pet"
        msgs = [
            f"Hi! I'm {name}! 🐾",
            "I'll live on your taskbar and keep you company!",
            "I start automatically with Windows 🚀",
            "Right-click me to open Settings anytime ⚙",
        ]
        delay = 0
        for msg in msgs:
            QTimer.singleShot(delay, lambda m=msg: self.show_emotion("happy", text_override=m))
            delay += 3200

    def _on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:   # left-click → mini popup
            from PyQt5.QtGui import QCursor
            mini = QMenu()
            mini.setStyleSheet(MENU_QSS)
            mini.setAttribute(Qt.WA_TranslucentBackground)
            mini.setWindowFlags(
                mini.windowFlags() | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
            vis_label = "👁  Hide pet" if self.isVisible() else "👁  Show pet"
            mini.addAction(vis_label, self._toggle_visibility)
            mini.addSeparator()
            mini.addAction("⚙  Settings", self._open_settings)
            mini.addSeparator()
            mini.addAction("❌  Exit", self._exit)
            mini.exec_(QCursor.pos())
        elif reason == QSystemTrayIcon.Context: # right-click → full menu
            self._refresh_tray_menu()

    def _refresh_tray_menu(self) -> None:
        if getattr(self, "tray", None):
            self.tray.setContextMenu(self._build_menu())

    def _update_tray_icon(self) -> None:
        if getattr(self, "tray", None):
            self.tray.setIcon(QIcon(self.character.animation("idle").current()))
            self._update_tray_tooltip()

    def _update_tray_tooltip(self) -> None:
        if getattr(self, "tray", None):
            mood  = self.mood_system.mood  if hasattr(self, "mood_system") else "neutral"
            emoji = self.mood_system.emoji if hasattr(self, "mood_system") else ""
            name  = self.settings.pet_name
            base  = f"{name}  •" if name else "Desktop Pet  •"
            self.tray.setToolTip(f"{base}  {mood.title()} {emoji}")
