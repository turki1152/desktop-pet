"""
reminders.py
============
Simple daily reminders that pop up in the pet's speech bubble at a chosen time
(e.g. "08:00 -> Drink water").  Reminders are stored in ``reminders.json`` in
the project root and repeat every day.

Also provides :class:`ReminderDialog`, a small modern dialog for adding one.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime

from PyQt5.QtCore import Qt, QTime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTimeEdit, QPushButton)

from .paths import base_dir

_PATH = os.path.join(base_dir(), "reminders.json")


@dataclass
class Reminder:
    time: str            # "HH:MM"
    text: str
    enabled: bool = True
    last_fired: str = ""  # ISO date string of the last day it fired


class ReminderStore:
    """Loads/saves reminders and tells you which are due right now."""

    def __init__(self):
        self.items: list[Reminder] = []
        self.load()

    def load(self) -> None:
        self.items = []
        try:
            with open(_PATH, "r", encoding="utf-8") as fh:
                for row in json.load(fh):
                    self.items.append(Reminder(**row))
        except (OSError, ValueError, TypeError):
            self.items = []

    def save(self) -> None:
        try:
            with open(_PATH, "w", encoding="utf-8") as fh:
                json.dump([asdict(r) for r in self.items], fh, indent=2)
        except OSError:
            pass

    def add(self, time_str: str, text: str) -> None:
        self.items.append(Reminder(time=time_str, text=text))
        self.save()

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.save()

    def due(self, now: datetime | None = None) -> list[Reminder]:
        """Return reminders that should fire now and mark them fired today."""
        now = now or datetime.now()
        hhmm = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")
        fired = []
        for r in self.items:
            if r.enabled and r.time == hhmm and r.last_fired != today:
                r.last_fired = today
                fired.append(r)
        if fired:
            self.save()
        return fired


# Shared stylesheet so the dialog matches the modern menu.
DIALOG_QSS = """
QDialog { background-color: #2b2d3a; }
QLabel { color: #e8eaf2; font-size: 12px; }
QLineEdit, QTimeEdit {
    background-color: #3a3d4f; color: #f0f2fa; border: 1px solid #4a4e63;
    border-radius: 6px; padding: 6px 8px; selection-background-color: #5a6cff;
}
QPushButton {
    background-color: #5a6cff; color: white; border: none;
    border-radius: 6px; padding: 7px 16px; font-weight: bold;
}
QPushButton:hover { background-color: #6d7dff; }
QPushButton#cancel { background-color: #43465a; }
QPushButton#cancel:hover { background-color: #51546b; }
"""


class ReminderDialog(QDialog):
    """Tiny modal dialog: pick a time and type a message."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New reminder")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(DIALOG_QSS)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Remind me at:"))
        self.time_edit = QTimeEdit(QTime.currentTime())
        self.time_edit.setDisplayFormat("HH:mm")
        layout.addWidget(self.time_edit)

        layout.addWidget(QLabel("Message:"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText("Drink water 💧")
        self.text_edit.setMinimumWidth(240)
        layout.addWidget(self.text_edit)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("cancel")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Add")
        ok.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def result_values(self) -> tuple[str, str]:
        return self.time_edit.time().toString("HH:mm"), self.text_edit.text().strip()
