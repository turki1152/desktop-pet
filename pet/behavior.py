"""
behavior.py
===========
The little "brain" of the pet: a compact finite-state machine that decides what
the character does and updates its position every tick.

States
------
* ``idle``  -- stands still and plays the idle animation for a random spell,
               then randomly chooses to keep idling, walk, or sleep.
* ``walk``  -- strolls left/right at the character's walk speed, automatically
               turning around when it reaches a screen edge.
* ``sleep`` -- naps (eyes closed, Zzz) for a while before waking up.
* ``fall``  -- accelerates downward under gravity until it lands on the taskbar
               (used after you pick the pet up and drop it).
* ``drag``  -- frozen logic-wise; the mouse is moving the pet directly.

The machine is driven by :meth:`Behavior.tick` with a delta-time so motion is
smooth and frame-rate independent.  All tuning (speeds, nap chance, idle time)
comes from the character's ``config.json``.
"""

from __future__ import annotations

import random

# State identifiers (also used as animation keys).
IDLE = "idle"
WALK = "walk"
SLEEP = "sleep"
FALL = "fall"
DRAG = "drag"

GRAVITY = 2200.0  # pixels per second^2 -- gives a snappy, satisfying drop.


class Behavior:
    def __init__(self, pet):
        self.pet = pet
        self.state = IDLE
        self._timer = 0.0       # seconds remaining in the current state
        self._direction = 1     # +1 walking right, -1 walking left
        self._vy = 0.0          # vertical velocity while falling
        self._step_accum = 0.0  # throttles footstep sounds while walking
        self._enter_idle()

    # ------------------------------------------------------------------ #
    # State transitions
    # ------------------------------------------------------------------ #
    def _set_state(self, state: str) -> None:
        self.state = state
        self.pet.on_state_changed(state)

    def _enter_idle(self) -> None:
        cfg = self.pet.character.behavior
        self._timer = random.uniform(cfg["idle_min"], cfg["idle_max"])
        self._set_state(IDLE)

    def _enter_walk(self) -> None:
        self._direction = random.choice((-1, 1))
        self.pet.facing_left = self._direction < 0
        self._timer = random.uniform(2.5, 6.0)
        self._step_accum = 0.0
        self._set_state(WALK)

    def _enter_sleep(self) -> None:
        self._timer = random.uniform(6.0, 14.0)
        self._set_state(SLEEP)
        self.pet.play_sound("sleep")

    def start_fall(self) -> None:
        """Called by the widget when the pet is released after a drag."""
        self._vy = 0.0
        self._set_state(FALL)

    def start_drag(self) -> None:
        self._set_state(DRAG)
        self.pet.play_sound("grab")

    # ------------------------------------------------------------------ #
    # Per-tick update
    # ------------------------------------------------------------------ #
    def tick(self, dt: float, speed: float) -> None:
        if self.state == DRAG:
            return  # the mouse is in charge.
        if self.state == FALL:
            self._tick_fall(dt)
        elif self.state == WALK:
            self._tick_walk(dt, speed)
        else:  # idle or sleep -- just count down, then re-decide.
            self._timer -= dt
            if self._timer <= 0:
                self._choose_next()

    def _tick_fall(self, dt: float) -> None:
        self._vy += GRAVITY * dt
        self.pet.y += self._vy * dt
        if self.pet.y >= self.pet.rest_y:
            # Landed on the taskbar.
            self.pet.y = self.pet.rest_y
            impact = self._vy
            self._vy = 0.0
            self.pet.play_sound("land")
            self.pet.on_land(impact)   # let the pet react to a hard landing
            self._enter_idle()

    def _tick_walk(self, dt: float, speed: float) -> None:
        step = self.pet.character.walk_speed * speed * self._direction * dt
        self.pet.x += step

        # Edge detection -- bounce off the walkable bounds.
        if self.pet.x <= self.pet.x_min:
            self.pet.x = self.pet.x_min
            self._direction = 1
            self.pet.facing_left = False
        elif self.pet.x + self.pet.width_px >= self.pet.x_max:
            self.pet.x = self.pet.x_max - self.pet.width_px
            self._direction = -1
            self.pet.facing_left = True

        # Occasional footstep sound.
        self._step_accum += dt
        if self._step_accum >= 0.4:
            self._step_accum = 0.0
            self.pet.play_sound("walk")

        self._timer -= dt
        if self._timer <= 0:
            self._enter_idle()

    def _choose_next(self) -> None:
        """From idle, randomly pick the next thing to do."""
        cfg = self.pet.character.behavior
        r = random.random()
        walk_chance = cfg["walk_chance"]
        sleep_chance = cfg["sleep_chance"]
        if r < walk_chance:
            self._enter_walk()
        elif r < walk_chance + sleep_chance:
            self._enter_sleep()
        else:
            self._enter_idle()
