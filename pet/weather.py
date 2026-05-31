"""
weather.py
==========
Fetches current weather from wttr.in (no API key, no extra dependencies).
Network requests run in a daemon thread so the UI never blocks.

Condition strings returned:  'sunny', 'cloudy', 'rain', 'snow', 'thunder', 'fog'
"""
from __future__ import annotations

import json
import threading
import urllib.request

CACHE_TTL = 1800.0   # re-fetch every 30 minutes

_CODE_MAP: dict[str, list[str]] = {
    "sunny":   ["113"],
    "cloudy":  ["116", "119", "122"],
    "fog":     ["143", "248", "260"],
    "rain":    ["176", "263", "266", "293", "296", "299", "302", "305",
                "308", "311", "314", "317", "320", "353", "356", "359",
                "362", "365", "374", "377"],
    "snow":    ["179", "182", "185", "227", "230", "323", "326", "329",
                "332", "335", "338", "368", "371"],
    "thunder": ["200", "386", "389", "392", "395"],
}

_REACTIONS: dict[str, list[str]] = {
    "sunny":   ["It's so sunny outside! ☀️", "What lovely weather~", "Perfect day! ☀️"],
    "cloudy":  ["Kind of cloudy today...", "Where did the sun go? ☁️", "Moody weather out there."],
    "rain":    ["It's raining outside! Stay dry 🌧️", "Rainy day... perfect for napping.", "Don't forget your umbrella! ☂️"],
    "snow":    ["It's snowing!! ❄️", "Snow!! I wanna play outside!", "Everything is so white! ⛄"],
    "thunder": ["Thunderstorm! 😱 That was loud!", "BOOM! Did you hear that?! ⚡", "Scary weather out there..."],
    "fog":     ["So foggy... I can barely see anything.", "Spooky fog today 👻", "The world disappeared!"],
}


def _code_to_condition(code: str) -> str:
    for cond, codes in _CODE_MAP.items():
        if code in codes:
            return cond
    return "cloudy"


class WeatherMonitor:
    """
    Call ``tick(dt)`` each frame.

    Returns new condition string when it first changes, None otherwise.
    Use ``condition`` property to read the current value at any time.
    Use ``random_reaction()`` to get a speech line for the current weather.
    """

    def __init__(self, city: str = ""):
        self._city      = city.strip()
        self._condition = "unknown"
        self._accum     = CACHE_TTL   # trigger fetch on first tick
        self._fetching  = False
        self._pending:  str | None = None   # written by background thread

    def set_city(self, city: str) -> None:
        new = city.strip()
        if new != self._city:
            self._city  = new
            self._accum = CACHE_TTL   # force a re-fetch with the new city

    def tick(self, dt: float) -> str | None:
        # Collect result from previous background fetch.
        if self._pending is not None:
            new = self._pending
            self._pending = None
            if new != self._condition:
                self._condition = new
                return new

        self._accum += dt
        if self._accum >= CACHE_TTL and not self._fetching:
            self._accum    = 0.0
            self._fetching = True
            threading.Thread(target=self._bg_fetch, daemon=True).start()

        return None

    @property
    def condition(self) -> str:
        return self._condition

    def random_reaction(self) -> str | None:
        import random
        lines = _REACTIONS.get(self._condition)
        return random.choice(lines) if lines else None

    # ------------------------------------------------------------------ #
    def _bg_fetch(self) -> None:
        result = self._fetch_once()
        if result:
            self._pending = result
        self._fetching = False

    def _fetch_once(self) -> str | None:
        try:
            import urllib.parse
            location = urllib.parse.quote(self._city) if self._city else ""
            url = f"https://wttr.in/{location}?format=j1"
            req = urllib.request.Request(url, headers={"User-Agent": "DesktopPet/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            code = data["current_condition"][0]["weatherCode"]
            return _code_to_condition(code)
        except Exception:
            return None
