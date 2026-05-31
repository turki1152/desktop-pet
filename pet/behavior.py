"""
behavior.py
===========
Finite-state machine that drives everything the pet does physically.

States
------
Core:       idle, walk, sleep, fall, drag, jump
Cursor:     follow, flee, cling, trip
Thrown:     throw (velocity-based flight with bouncing)
Items:      balloon (float up), rocket (fast launch), portal (teleport)
Gags:       moonwalk, stuck, frozen, dance, upside_down
Window:     window_sit (rest on top of an app window)
Edge:       slide_edge (slide down a screen border)
"""

from __future__ import annotations

import random

from PyQt5.QtGui import QCursor

# ------------------------------------------------------------------ #
# State identifiers
# ------------------------------------------------------------------ #
IDLE        = "idle"
WALK        = "walk"
SLEEP       = "sleep"
FALL        = "fall"
DRAG        = "drag"
JUMP        = "jump"
FOLLOW      = "follow"
FLEE        = "flee"
CLING       = "cling"
TRIP        = "trip"
THROW       = "throw"
BALLOON     = "balloon"
ROCKET      = "rocket"
PORTAL      = "portal"
MOONWALK    = "moonwalk"
STUCK       = "stuck"
FROZEN      = "frozen"
DANCE       = "dance"
UPSIDE_DOWN = "upside_down"
WINDOW_SIT  = "window_sit"
SLIDE_EDGE  = "slide_edge"

GRAVITY = 2200.0   # px/s²

# States that render with the walk animation.
_WALK_ANIM   = {FOLLOW, FLEE, TRIP, MOONWALK, DANCE, SLIDE_EDGE}
# States that render with the fall animation.
_FALL_ANIM   = {THROW, ROCKET}


class Behavior:
    def __init__(self, pet):
        self.pet   = pet
        self.state = IDLE

        self._timer      = 0.0
        self._direction  = 1
        self._vy         = 0.0          # vertical velocity
        self._vx         = 0.0          # horizontal velocity (throw/rocket)
        self._step_accum = 0.0

        # Cursor awareness.
        self._cursor_accum = 0.0
        self._face_accum   = 0.0
        self._cling_cool   = 0.0

        # Trip phases.
        self._trip_phase = ""

        # Dream timer (fires during SLEEP — reset in _enter_sleep).
        self._dream_accum = 0.0

        # Idle-activity timer (fires during IDLE).
        self._activity_accum = random.uniform(20.0, 45.0)

        # Boredom timer (how long since last interaction).
        self._boredom_accum = 0.0

        # Window-sit target (y coordinate of the window top edge + left/right bounds).
        self._window_target_y: int | None = None
        self._win_xl: int = 0
        self._win_xr: int = 0

        # Dance direction-flip timer.
        self._dance_flip = 0.0

        # Upside-down is a flag on top of another state.
        self.upside_down = False

        self._enter_idle()

    # ------------------------------------------------------------------ #
    # Animation alias
    # ------------------------------------------------------------------ #
    @property
    def animation_state(self) -> str:
        if self.state in _WALK_ANIM:
            return WALK
        if self.state in _FALL_ANIM:
            return FALL
        if self.state in (STUCK, FROZEN, BALLOON, PORTAL, WINDOW_SIT, UPSIDE_DOWN):
            return IDLE
        return self.state

    @property
    def anim_frozen(self) -> bool:
        """True → animation should stop advancing."""
        return self.state == FROZEN

    @property
    def anim_reversed(self) -> bool:
        """True → animation frames play in reverse (moonwalk effect)."""
        return self.state == MOONWALK

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def _set_state(self, state: str) -> None:
        self.state = state
        self.pet.on_state_changed(state)

    def _enter_idle(self) -> None:
        cfg = self.pet.character.behavior
        self._timer = random.uniform(cfg["idle_min"], cfg["idle_max"])
        self.upside_down = False
        self._set_state(IDLE)

    def _enter_walk(self) -> None:
        self._direction = random.choice((-1, 1))
        self.pet.facing_left = self._direction < 0
        self._timer = random.uniform(2.5, 6.0)
        self._step_accum = 0.0
        self._set_state(WALK)

    def _enter_sleep(self) -> None:
        self._timer      = random.uniform(6.0, 14.0)
        self._dream_accum = random.uniform(12.0, 22.0)
        # Random sleeping position.
        self.pet.facing_left = random.random() < 0.5
        self._set_state(SLEEP)
        self.pet.play_sound("sleep")

    def start_fall(self) -> None:
        self._vy = 0.0
        self._vx = 0.0
        self.upside_down = False
        self._set_state(FALL)

    def start_drag(self) -> None:
        self._set_state(DRAG)
        self.pet.play_sound("grab")

    def start_jump(self) -> None:
        self._vy = -370.0
        self._set_state(JUMP)

    # ------------------------------------------------------------------ #
    # Throw  (velocity-based fling after release)
    # ------------------------------------------------------------------ #
    def start_throw(self, vx: float, vy: float) -> None:
        """Called by the widget after a fast drag release."""
        self._vx = max(-1200.0, min(1200.0, vx))
        self._vy = max(-1200.0, min(400.0,  vy))
        self.upside_down = abs(vx) > 600
        self._set_state(THROW)

    def _tick_throw(self, dt: float) -> None:
        self._vy += GRAVITY * dt
        self._vx *= max(0.0, 1.0 - dt * 1.2)   # air friction
        self.pet.x += self._vx * dt
        self.pet.y += self._vy * dt

        # Bounce off horizontal edges.
        if self.pet.x <= self.pet.x_min:
            self.pet.x  = self.pet.x_min
            self._vx    = abs(self._vx) * 0.55
            self.pet.facing_left = False
            self.pet.show_emotion("surprised")
        elif self.pet.x + self.pet.width_px >= self.pet.x_max:
            self.pet.x  = self.pet.x_max - self.pet.width_px
            self._vx    = -abs(self._vx) * 0.55
            self.pet.facing_left = True
            self.pet.show_emotion("surprised")

        # Land.
        if self.pet.y >= self.pet.rest_y:
            self.pet.y  = self.pet.rest_y
            self._vy    = 0.0
            self._vx    = 0.0
            self.upside_down = False
            self.pet.play_sound("land")
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Balloon  (float slowly upward, eventually pops at top)
    # ------------------------------------------------------------------ #
    def start_balloon(self) -> None:
        self._timer = random.uniform(6.0, 10.0)
        self._vy    = -55.0   # gentle upward drift
        self._set_state(BALLOON)
        self.pet.show_emotion("happy")

    def _tick_balloon(self, dt: float) -> None:
        self.pet.y += self._vy * dt
        # Light left-right sway.
        self._vy = max(-80.0, self._vy - dt * 4)
        sway = 12.0 * dt
        self.pet.x += sway * (1 if self._direction > 0 else -1)
        if self.pet.x <= self.pet.x_min or self.pet.x + self.pet.width_px >= self.pet.x_max:
            self._direction *= -1

        self._timer -= dt
        screen_top = 0
        if self.pet.y < screen_top - self.pet.height_px or self._timer <= 0:
            # Pop!
            self.pet.show_emotion("surprised")
            self.start_fall()

    # ------------------------------------------------------------------ #
    # Rocket  (launch fast upward, exit screen, return)
    # ------------------------------------------------------------------ #
    def start_rocket(self) -> None:
        self._vy = -1400.0
        self._timer = 0.0
        self._set_state(ROCKET)
        self.pet.show_emotion("excited")

    def _tick_rocket(self, dt: float) -> None:
        self.pet.y += self._vy * dt
        self._vy   += GRAVITY * 0.45 * dt   # gentler gravity so it actually goes high

        # Once off-screen, teleport back above the screen and fall back down.
        if self.pet.y + self.pet.height_px < -20:
            self.pet.y = float(-self.pet.height_px - 10)
            self._vy   = 0.0
            self.start_fall()
            return

        # Safety: if it somehow never went off-screen, land normally.
        if self.pet.y >= self.pet.rest_y:
            self.pet.y = float(self.pet.rest_y)
            self._vy   = 0.0
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Portal  (hide → teleport → reappear)
    # ------------------------------------------------------------------ #
    def start_portal(self) -> None:
        self._timer = 1.2   # hide for 1.2 s
        self._set_state(PORTAL)
        self.pet.hide()
        self.pet.bubble.hide()

    def _tick_portal(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0:
            # Reappear at a random position.
            new_x = random.uniform(self.pet.x_min,
                                   self.pet.x_max - self.pet.width_px)
            self.pet.x = new_x
            self.pet.y = float(self.pet.rest_y)
            self.pet.show()
            self.pet.show_emotion("surprised")
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Moonwalk  (walk but facing wrong direction)
    # ------------------------------------------------------------------ #
    def start_moonwalk(self) -> None:
        self._direction  = random.choice((-1, 1))
        self.pet.facing_left = self._direction > 0   # intentionally backwards
        self._timer      = random.uniform(3.0, 5.0)
        self._step_accum = 0.0
        self._set_state(MOONWALK)

    def _tick_moonwalk(self, dt: float, speed: float) -> None:
        step = self.pet.character.walk_speed * speed * self._direction * dt
        self.pet.x += step
        if self.pet.x <= self.pet.x_min:
            self.pet.x  = self.pet.x_min
            self._direction = 1
            self.pet.facing_left = True
        elif self.pet.x + self.pet.width_px >= self.pet.x_max:
            self.pet.x  = self.pet.x_max - self.pet.width_px
            self._direction = -1
            self.pet.facing_left = False

        self._step_accum += dt
        if self._step_accum >= 0.4:
            self._step_accum = 0.0
            self.pet.play_sound("walk")

        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Stuck  (frozen in place, confused)
    # ------------------------------------------------------------------ #
    def start_stuck(self) -> None:
        self._timer = random.uniform(3.0, 6.0)
        self._set_state(STUCK)
        self.pet.show_emotion("surprised")

    def _tick_stuck(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0:
            self.pet.show_emotion("happy")
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Frozen  (pretends to be frozen, animation stops)
    # ------------------------------------------------------------------ #
    def start_frozen(self) -> None:
        self._timer = random.uniform(3.0, 5.0)
        self._set_state(FROZEN)

    def _tick_frozen(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0:
            self.pet.show_emotion("surprised")
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Dance  (rapid left-right shuffling)
    # ------------------------------------------------------------------ #
    def start_dance(self) -> None:
        self._timer      = random.uniform(4.0, 8.0)
        self._dance_flip = random.uniform(0.2, 0.5)
        self._direction  = 1
        self.pet.facing_left = False
        self._set_state(DANCE)

    def _tick_dance(self, dt: float, speed: float) -> None:
        self._dance_flip -= dt
        if self._dance_flip <= 0:
            self._dance_flip  = random.uniform(0.18, 0.45)
            self._direction  *= -1
            self.pet.facing_left = self._direction < 0

        step = self.pet.character.walk_speed * speed * 0.6 * self._direction * dt
        self.pet.x = max(self.pet.x_min,
                         min(self.pet.x + step, self.pet.x_max - self.pet.width_px))

        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Upside-down  (flag that flips rendering, uses idle physics)
    # ------------------------------------------------------------------ #
    def start_upside_down(self) -> None:
        self.upside_down = True
        self._timer = random.uniform(3.0, 6.0)
        self._set_state(UPSIDE_DOWN)

    def _tick_upside_down(self, dt: float) -> None:
        self._timer -= dt
        if self._timer <= 0:
            self.upside_down = False
            self.pet.show_emotion("surprised")
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Window-sit  (rest on top of an application window)
    # ------------------------------------------------------------------ #
    def start_window_sit(self, target_x: float, target_y: int,
                         win_xl: int = 0, win_xr: int = 0) -> None:
        self._window_target_y = target_y
        self._win_xl = win_xl if win_xr > win_xl else self.pet.x_min
        self._win_xr = win_xr if win_xr > win_xl else self.pet.x_max
        # Walk toward target_x first.
        self._direction      = 1 if target_x > self.pet.x + self.pet.width_px / 2 else -1
        self.pet.facing_left = self._direction < 0
        self._timer          = random.uniform(4.0, 8.0)
        self._step_accum     = 0.0
        self._set_state(WINDOW_SIT)

    def _tick_window_sit(self, dt: float, speed: float) -> None:
        if self._window_target_y is not None:
            # Smoothly move to the window's top edge.
            ty = float(self._window_target_y - self.pet.height_px)
            dy = ty - self.pet.y
            self.pet.y += dy * min(1.0, dt * 4)

        # Walk along the window's top edge (clamped to the window's own bounds).
        step = self.pet.character.walk_speed * speed * 0.5 * self._direction * dt
        self.pet.x += step
        x_lo = max(self.pet.x_min, self._win_xl)
        x_hi = min(self.pet.x_max, self._win_xr) - self.pet.width_px
        if x_hi <= x_lo:   # window too narrow — jump off immediately
            self._window_target_y = None
            self.start_fall()
            return
        if self.pet.x <= x_lo:
            self.pet.x = float(x_lo)
            self._direction = 1
            self.pet.facing_left = False
        elif self.pet.x >= x_hi:
            self.pet.x = float(x_hi)
            self._direction = -1
            self.pet.facing_left = True

        self._timer -= dt
        if self._timer <= 0:
            self._window_target_y = None
            self.start_fall()

    # ------------------------------------------------------------------ #
    # Slide-edge  (walk to screen edge, fall over it)
    # ------------------------------------------------------------------ #
    def start_slide_edge(self) -> None:
        self._direction      = random.choice((-1, 1))
        self.pet.facing_left = self._direction < 0
        self._step_accum     = 0.0
        self._set_state(SLIDE_EDGE)

    def _tick_slide_edge(self, dt: float, speed: float) -> None:
        step = self.pet.character.walk_speed * speed * 1.4 * self._direction * dt
        self.pet.x += step
        if ((self.pet.x + self.pet.width_px >= self.pet.x_max and self._direction > 0)
                or (self.pet.x <= self.pet.x_min and self._direction < 0)):
            # Walk fully off-screen then reappear from the other side (reuses TRIP logic).
            self._enter_trip()

    # ------------------------------------------------------------------ #
    # Per-tick dispatcher
    # ------------------------------------------------------------------ #
    def tick(self, dt: float, speed: float) -> None:
        if self.state == DRAG:
            return

        if self._cling_cool > 0:
            self._cling_cool = max(0.0, self._cling_cool - dt)

        # Boredom accumulator (only reset on interactions in pet_widget).
        self._boredom_accum += dt

        # Dispatch.
        if   self.state == FALL:        self._tick_fall(dt)
        elif self.state == JUMP:        self._tick_jump(dt)
        elif self.state == THROW:       self._tick_throw(dt)
        elif self.state == WALK:        self._tick_walk(dt, speed)
        elif self.state == FOLLOW:      self._tick_follow(dt, speed)
        elif self.state == FLEE:        self._tick_flee(dt, speed)
        elif self.state == CLING:       self._tick_cling(dt)
        elif self.state == TRIP:        self._tick_trip(dt, speed)
        elif self.state == BALLOON:     self._tick_balloon(dt)
        elif self.state == ROCKET:      self._tick_rocket(dt)
        elif self.state == PORTAL:      self._tick_portal(dt)
        elif self.state == MOONWALK:    self._tick_moonwalk(dt, speed)
        elif self.state == STUCK:       self._tick_stuck(dt)
        elif self.state == FROZEN:      self._tick_frozen(dt)
        elif self.state == DANCE:       self._tick_dance(dt, speed)
        elif self.state == UPSIDE_DOWN: self._tick_upside_down(dt)
        elif self.state == WINDOW_SIT:  self._tick_window_sit(dt, speed)
        elif self.state == SLIDE_EDGE:  self._tick_slide_edge(dt, speed)
        elif self.state in (IDLE, SLEEP):
            self._timer -= dt
            if self._timer <= 0:
                if self.state == SLEEP:
                    self._enter_idle()
                else:
                    self._choose_next()
            # Dreams during sleep.
            if self.state == SLEEP:
                self._tick_dreams(dt)
            # Idle activities.
            if self.state == IDLE:
                self._tick_idle_activities(dt)

        # Cursor awareness (only while calm).
        if self.state in (IDLE, WALK):
            if self.state == IDLE:
                self._face_accum += dt
                if self._face_accum >= 0.45:
                    self._face_accum = 0.0
                    self._face_toward_cursor()
            self._cursor_accum += dt
            if self._cursor_accum >= 1.1:
                self._cursor_accum = 0.0
                self._check_cursor_proximity()

    # ------------------------------------------------------------------ #
    # Dream bubbles during sleep
    # ------------------------------------------------------------------ #
    _DREAMS = [
        "💭 chasing butterflies…",
        "💭 eating cake…",
        "💭 flying!",
        "💭 exploring new worlds…",
        "💭 playing with yarn…",
        "💭 running on a beach…",
        "💭 infinite fish 🐟",
        "💭 becoming a wizard…",
        "💭 winning a race!",
        "💭 being very famous…",
        "💭 napping on a cloud…",
    ]

    def _tick_dreams(self, dt: float) -> None:
        self._dream_accum -= dt
        if self._dream_accum <= 0:
            self._dream_accum = random.uniform(15.0, 30.0)
            self.pet.show_emotion("talk", text_override=random.choice(self._DREAMS))

    # ------------------------------------------------------------------ #
    # Random idle activities (text-based, no extra sprites needed)
    # ------------------------------------------------------------------ #
    _ACTIVITIES = [
        ("*yawns*", "talk"),
        ("*stretches arms* Ahh~", "happy"),
        ("*snacks on something*  🍎", "talk"),
        ("*looks around curiously*", "talk"),
        ("*taps feet impatiently*", "talk"),
        ("*brushes fur*", "talk"),
        ("Hmm… what should I do?", "talk"),
        ("*hums a little tune* 🎵", "happy"),
        ("*peeks over the edge*", "surprised"),
        ("*does a little spin*", "happy"),
    ]

    def _tick_idle_activities(self, dt: float) -> None:
        self._activity_accum -= dt
        if self._activity_accum <= 0:
            self._activity_accum = random.uniform(20.0, 45.0)
            text, kind = random.choice(self._ACTIVITIES)
            self.pet.show_emotion(kind, text_override=text)
            # Occasionally trigger a physical reaction too.
            if kind == "happy" and random.random() < 0.4:
                self.start_jump()

    # ------------------------------------------------------------------ #
    # Fall / Jump helpers
    # ------------------------------------------------------------------ #
    def _tick_fall(self, dt: float) -> None:
        self._vy += GRAVITY * dt
        self.pet.y += self._vy * dt
        if self.pet.y >= self.pet.rest_y:
            self.pet.y = self.pet.rest_y
            impact = self._vy
            self._vy = 0.0
            self.pet.play_sound("land")
            self.pet.on_land(impact)
            self._enter_idle()

    def _tick_jump(self, dt: float) -> None:
        self._vy += GRAVITY * dt
        self.pet.y += self._vy * dt
        if self.pet.y >= self.pet.rest_y:
            self.pet.y = self.pet.rest_y
            self._vy = 0.0
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Walk
    # ------------------------------------------------------------------ #
    def _tick_walk(self, dt: float, speed: float) -> None:
        step = self.pet.character.walk_speed * speed * self._direction * dt
        self.pet.x += step

        if self.pet.x <= self.pet.x_min:
            self.pet.x = self.pet.x_min
            if random.random() < 0.07:
                self._direction = -1
                self._enter_trip()
                return
            self._direction = 1
            self.pet.facing_left = False
        elif self.pet.x + self.pet.width_px >= self.pet.x_max:
            self.pet.x = self.pet.x_max - self.pet.width_px
            if random.random() < 0.07:
                self._direction = 1
                self._enter_trip()
                return
            self._direction = -1
            self.pet.facing_left = True

        self._step_accum += dt
        if self._step_accum >= 0.4:
            self._step_accum = 0.0
            self.pet.play_sound("walk")

        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # Cursor: facing + proximity
    # ------------------------------------------------------------------ #
    def _face_toward_cursor(self) -> None:
        cursor_x = QCursor.pos().x()
        pet_cx   = self.pet.x + self.pet.width_px / 2
        self.pet.facing_left = cursor_x < pet_cx

    def _check_cursor_proximity(self) -> None:
        c = QCursor.pos()
        pet_cx = self.pet.x + self.pet.width_px / 2
        pet_cy = self.pet.y + self.pet.height_px / 2
        dist   = ((c.x() - pet_cx) ** 2 + (c.y() - pet_cy) ** 2) ** 0.5

        mood = getattr(self.pet, "current_mood", "neutral")
        if mood == "angry":
            flee_chance, follow_chance = 0.45, 0.05
        elif mood in ("happy", "excited"):
            flee_chance, follow_chance = 0.18, 0.22
        elif mood == "curious":
            flee_chance, follow_chance = 0.22, 0.20
        elif mood == "sleepy":
            flee_chance, follow_chance = 0.20, 0.08
        else:
            flee_chance, follow_chance = 0.28, 0.14

        if dist < 65 and random.random() < flee_chance:
            self._enter_flee(c.x())
        elif dist < 220 and self.state == IDLE and random.random() < follow_chance:
            self._enter_follow()

    # ------------------------------------------------------------------ #
    # FOLLOW
    # ------------------------------------------------------------------ #
    def _enter_follow(self) -> None:
        self._timer = random.uniform(3.5, 6.0)
        self._step_accum = 0.0
        self._set_state(FOLLOW)

    def _tick_follow(self, dt: float, speed: float) -> None:
        cursor_x = QCursor.pos().x()
        pet_cx   = self.pet.x + self.pet.width_px / 2
        dist     = abs(cursor_x - pet_cx)

        if dist < 38:
            self.pet.facing_left = cursor_x < pet_cx
            self._timer -= dt
            if self._timer <= 0:
                self._enter_idle()
            return

        direction = 1 if cursor_x > pet_cx else -1
        self.pet.facing_left = direction < 0
        step = self.pet.character.walk_speed * speed * 0.85 * direction * dt
        self.pet.x = max(self.pet.x_min,
                         min(self.pet.x + step, self.pet.x_max - self.pet.width_px))

        self._step_accum += dt
        if self._step_accum >= 0.4:
            self._step_accum = 0.0
            self.pet.play_sound("walk")

        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # FLEE
    # ------------------------------------------------------------------ #
    def _enter_flee(self, cursor_x: float) -> None:
        pet_cx = self.pet.x + self.pet.width_px / 2
        self._direction = 1 if pet_cx >= cursor_x else -1
        self.pet.facing_left = self._direction < 0
        self._timer = random.uniform(1.8, 3.2)
        self._step_accum = 0.0
        self._set_state(FLEE)
        self.pet.show_emotion("surprised")

    def _tick_flee(self, dt: float, speed: float) -> None:
        step = self.pet.character.walk_speed * speed * 2.2 * self._direction * dt
        self.pet.x += step
        if self.pet.x <= self.pet.x_min:
            self.pet.x = self.pet.x_min
            self._direction = 1
            self.pet.facing_left = False
        elif self.pet.x + self.pet.width_px >= self.pet.x_max:
            self.pet.x = self.pet.x_max - self.pet.width_px
            self._direction = -1
            self.pet.facing_left = True
        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    # ------------------------------------------------------------------ #
    # CLING
    # ------------------------------------------------------------------ #
    def start_cling(self) -> None:
        if self._cling_cool > 0 or self.state not in (IDLE, WALK):
            return
        self._timer = random.uniform(3.0, 5.5)
        self._set_state(CLING)
        self.pet.show_emotion("happy")

    def _tick_cling(self, dt: float) -> None:
        c     = QCursor.pos()
        new_x = float(c.x() - self.pet.width_px  // 2)
        new_y = float(c.y() - self.pet.height_px // 2)
        speed_px = (abs(new_x - self.pet.x) + abs(new_y - self.pet.y)) / max(dt, 0.001)
        self.pet.x = max(self.pet.x_min, min(new_x, self.pet.x_max - self.pet.width_px))
        self.pet.y = new_y
        self._timer -= dt
        if self._timer <= 0 or speed_px > 900:
            self._cling_cool = 30.0
            self.start_fall()

    # ------------------------------------------------------------------ #
    # TRIP
    # ------------------------------------------------------------------ #
    def _enter_trip(self) -> None:
        self._trip_phase = "walking_off"
        self._step_accum = 0.0
        self._set_state(TRIP)
        self.pet.show_emotion("surprised")

    def _tick_trip(self, dt: float, speed: float) -> None:
        if self._trip_phase == "walking_off":
            step = self.pet.character.walk_speed * speed * self._direction * dt
            self.pet.x += step
            fully_off = (self.pet.x + self.pet.width_px < self.pet.x_min - 4
                         or self.pet.x > self.pet.x_max + 4)
            if fully_off:
                self.pet.hide()
                self.pet.bubble.hide()
                self._trip_phase = "offscreen"
                self._timer = 1.3
        elif self._trip_phase == "offscreen":
            self._timer -= dt
            if self._timer <= 0:
                if self._direction > 0:
                    self.pet.x = float(self.pet.x_min - self.pet.width_px)
                else:
                    self.pet.x = float(self.pet.x_max)
                # Keep the same direction — it already points back into the screen.
                self.pet.facing_left = self._direction < 0
                self.pet.show()
                self._trip_phase = "walking_on"
        elif self._trip_phase == "walking_on":
            step = self.pet.character.walk_speed * speed * self._direction * dt
            self.pet.x += step
            back_in = self.pet.x_min <= self.pet.x <= self.pet.x_max - self.pet.width_px
            if back_in:
                self.pet.show_emotion("sad")
                self._enter_idle()

    # ------------------------------------------------------------------ #
    # Next-state chooser
    # ------------------------------------------------------------------ #
    def _choose_next(self) -> None:
        cfg = self.pet.character.behavior
        walk_chance  = cfg["walk_chance"]
        sleep_chance = cfg["sleep_chance"]

        mood = getattr(self.pet, "current_mood", "neutral")
        if mood == "sleepy":
            sleep_chance = min(sleep_chance * 2.0, 0.6)
        elif mood in ("excited", "happy"):
            walk_chance  = min(walk_chance * 1.3, 0.75)
            sleep_chance = sleep_chance * 0.5

        # Bored pet has a chance to do a gag.
        if self._boredom_accum > 180.0 and random.random() < 0.15:
            gag = random.choice([self.start_moonwalk, self.start_dance,
                                  self.start_stuck, self.start_slide_edge])
            gag()
            return

        r = random.random()
        if r < walk_chance:
            self._enter_walk()
        elif r < walk_chance + sleep_chance:
            self._enter_sleep()
        else:
            self._enter_idle()

    def reset_boredom(self) -> None:
        """Call this whenever the user interacts with the pet."""
        self._boredom_accum = 0.0
