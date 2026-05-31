"""
multi_pet.py
============
Singleton registry that tracks all living PetWidget instances so they can
find and react to each other: jealousy, chat, play-together.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .pet_widget import PetWidget


class PetManager:
    """Singleton registry of all active pets."""

    _instance: "PetManager | None" = None

    def __init__(self):
        self.pets: list["PetWidget"] = []
        PetManager._instance = self

    @classmethod
    def get(cls) -> "PetManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, pet: "PetWidget") -> None:
        if pet not in self.pets:
            self.pets.append(pet)

    def unregister(self, pet: "PetWidget") -> None:
        if pet in self.pets:
            self.pets.remove(pet)

    # ------------------------------------------------------------------ #
    def others(self, pet: "PetWidget") -> list["PetWidget"]:
        """All pets except *pet*."""
        return [p for p in self.pets if p is not pet]

    def visible_others(self, pet: "PetWidget") -> list["PetWidget"]:
        return [p for p in self.others(pet) if p.isVisible()]

    def nearby(self, pet: "PetWidget", radius: float = 200.0) -> list["PetWidget"]:
        """Pets within *radius* pixels of *pet*."""
        cx = pet.x + pet.width_px / 2
        cy = pet.y + pet.height_px / 2
        result = []
        for other in self.visible_others(pet):
            ox = other.x + other.width_px / 2
            oy = other.y + other.height_px / 2
            dist = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
            if dist <= radius:
                result.append(other)
        return result

    # ------------------------------------------------------------------ #
    def count(self) -> int:
        return len(self.pets)

    def is_rival_pair(self, a: "PetWidget", b: "PetWidget") -> bool:
        """True when the two character keys are a rival combination."""
        _RIVALS = {frozenset({"cat", "dog"}), frozenset({"naruto", "sasuke"})}
        pair = frozenset({a.character.key, b.character.key})
        return pair in _RIVALS

    def is_friend_pair(self, a: "PetWidget", b: "PetWidget") -> bool:
        """True when the two character keys are naturally friendly."""
        return a.character.key == b.character.key   # same species = friends
