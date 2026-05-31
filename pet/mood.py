"""
mood.py
=======
Tracks how the pet is feeling right now.

Score 0.0 – 5.0 maps to six named moods:
  0 = angry   1 = sleepy   2 = neutral
  3 = curious 4 = excited  5 = happy

The score drifts toward neutral (2.5) slowly on its own.
Interactions push it up; shaking pushes it down.
Being ignored for 5+ minutes drifts it toward sleepy.
"""

from __future__ import annotations

MOODS = ["angry", "sleepy", "neutral", "curious", "excited", "happy"]

MOOD_EMOJI = {
    "angry":   "😠",
    "sleepy":  "😴",
    "neutral": "😐",
    "curious": "🤔",
    "excited": "🤩",
    "happy":   "😊",
}

# Generic chatter shown occasionally when mood is strong.
MOOD_MESSAGES: dict[str, list[str]] = {
    "happy":   ["I'm so happy right now! ♥", "Life is good~", "Yay! 😊", "Everything is wonderful!"],
    "excited": ["AHH this is so fun!!", "I'm full of energy!", "Let's do something!", "YESYESYES 🤩"],
    "curious": ["What's that over there?", "Hmm… interesting.", "I wonder…", "Tell me more!"],
    "sleepy":  ["zzzz…", "So… sleepy…", "Just five more minutes…", "I can barely keep my eyes open."],
    "angry":   ["Leave me alone.", "Hmph.", "Not in the mood.", "Stop that!! 😠"],
    "neutral": [],
}


class MoodSystem:
    """Manages the pet's current emotional state."""

    def __init__(self, score: float = 2.5):
        self._score    = max(0.0, min(5.0, float(score)))
        self._idle_acc = 0.0   # seconds since last interaction

    # ------------------------------------------------------------------ #
    @property
    def score(self) -> float:
        return self._score

    @property
    def mood(self) -> str:
        idx = max(0, min(len(MOODS) - 1, round(self._score)))
        return MOODS[idx]

    @property
    def emoji(self) -> str:
        return MOOD_EMOJI[self.mood]

    # ------------------------------------------------------------------ #
    def tick(self, dt: float) -> None:
        self._idle_acc += dt

        # Very slow drift back toward neutral (2.5).
        diff = 2.5 - self._score
        self._score += diff * dt * 0.004

        # Ignored for >5 minutes → drift toward sleepy (1.0).
        if self._idle_acc > 300:
            self._score = max(1.0, self._score - dt * 0.015)

        self._score = max(0.0, min(5.0, self._score))

    # ------------------------------------------------------------------ #
    def on_pat(self) -> None:
        """Quick affectionate tap → happier."""
        self._idle_acc = 0.0
        self._score = min(5.0, self._score + 0.6)

    def on_shake(self) -> None:
        """Shaken around → annoyed."""
        self._idle_acc = 0.0
        self._score = max(0.0, self._score - 0.9)

    def on_interact(self) -> None:
        """Any interaction (drag, double-click) → slight positive nudge."""
        self._idle_acc = 0.0
        self._score = min(5.0, self._score + 0.1)
