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

from PyQt5.QtCore import Qt, QTime, QTimer
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTimeEdit, QSpinBox, QPushButton,
                             QComboBox, QProgressBar, QWidget)

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


# ------------------------------------------------------------------ #
# Countdown / Pomodoro window
# ------------------------------------------------------------------ #
class CountdownWindow(QWidget):
    """Floating countdown timer with Pomodoro presets."""

    # (label, minutes) — None minutes means "use custom spinner"
    PRESETS = [
        ("Pomodoro  25 min",   25),
        ("Short break  5 min",  5),
        ("Long break  15 min", 15),
        ("Water  30 min",      30),
        ("Stretch  45 min",    45),
        ("Break  60 min",      60),
        ("Custom",             None),
    ]

    def __init__(self, on_finish=None, parent=None):
        super().__init__(parent)
        self.on_finish = on_finish
        self.setWindowTitle("Countdown")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(DIALOG_QSS.replace("QDialog", "QWidget"))
        self.setFixedWidth(300)

        self._remaining = 0
        self._label_text = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Preset selector.
        self._combo = QComboBox()
        for name, _ in self.PRESETS:
            self._combo.addItem(name)
        self._combo.currentIndexChanged.connect(self._on_preset_changed)
        layout.addWidget(self._combo)

        # Custom duration — only enabled when "Custom" is selected.
        h = QHBoxLayout()
        self._spin_lbl = QLabel("Minutes:")
        self._spin = QSpinBox()
        self._spin.setRange(1, 999)
        self._spin.setValue(25)
        self._spin.valueChanged.connect(self._on_spin_changed)
        h.addWidget(self._spin_lbl)
        h.addWidget(self._spin)
        layout.addLayout(h)

        # Big countdown display.
        self._time_lbl = QLabel("--:--")
        self._time_lbl.setAlignment(Qt.AlignCenter)
        self._time_lbl.setStyleSheet(
            "font-size: 36px; font-weight: bold; color: #eef0fa; padding: 8px 0;")
        layout.addWidget(self._time_lbl)

        # Progress bar.
        self._bar = QProgressBar()
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        self._bar.setStyleSheet(
            "QProgressBar { background: #3a3d4f; border-radius:4px; }"
            "QProgressBar::chunk { background: #5a6cff; border-radius:4px; }"
        )
        layout.addWidget(self._bar)

        # Buttons.
        brow = QHBoxLayout()
        brow.setSpacing(8)
        self._start_btn = QPushButton("Start")
        self._start_btn.clicked.connect(self._start)
        stop_btn = QPushButton("Stop")
        stop_btn.setObjectName("cancel")
        stop_btn.clicked.connect(self._stop)
        brow.addWidget(self._start_btn)
        brow.addWidget(stop_btn)
        layout.addLayout(brow)

        self._qt_timer = QTimer(self)
        self._qt_timer.timeout.connect(self._tick)
        self._total = 0

        # Sync initial state.
        self._on_preset_changed(0)
        self.adjustSize()

    def _on_preset_changed(self, idx: int) -> None:
        minutes = self.PRESETS[idx][1]
        is_custom = minutes is None
        self._spin.setEnabled(is_custom)
        self._spin_lbl.setEnabled(is_custom)
        if not is_custom:
            self._spin.setValue(minutes)

    def _on_spin_changed(self, _val: int) -> None:
        # Auto-select "Custom" when the user edits the spinner.
        custom_idx = len(self.PRESETS) - 1
        if self._combo.currentIndex() != custom_idx:
            self._combo.setCurrentIndex(custom_idx)

    def _start(self) -> None:
        row = self._combo.currentIndex()
        preset_minutes = self.PRESETS[row][1]
        if preset_minutes is None:
            minutes = self._spin.value()
            self._label_text = f"{minutes} min timer"
        else:
            minutes = preset_minutes
            self._label_text = self.PRESETS[row][0]
        self._total = minutes * 60
        self._remaining = self._total
        self._bar.setMaximum(self._total)
        self._bar.setValue(self._total)
        self._qt_timer.start(1000)
        self._start_btn.setEnabled(False)

    def _stop(self) -> None:
        self._qt_timer.stop()
        self._time_lbl.setText("--:--")
        self._bar.setValue(0)
        self._start_btn.setEnabled(True)

    def _tick(self) -> None:
        if self._remaining <= 0:
            return
        self._remaining -= 1
        self._bar.setValue(self._remaining)
        m, s = divmod(self._remaining, 60)
        self._time_lbl.setText(f"{m:02d}:{s:02d}")
        if self._remaining == 0:
            self._qt_timer.stop()
            self._start_btn.setEnabled(True)
            if self.on_finish:
                self.on_finish(self._label_text)
