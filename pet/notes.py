"""
notes.py
========
Two persistent mini-windows accessible from the tray menu:
  QuickNotesWindow  – a scratch-pad that saves to notes.txt
  TodoListWindow    – a checklist that saves to todo_list.json
"""
from __future__ import annotations

import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QTextEdit,
    QVBoxLayout, QWidget,
)

from .paths import base_dir

_NOTES_PATH = os.path.join(base_dir(), "notes.txt")
_TODO_PATH  = os.path.join(base_dir(), "todo_list.json")

_QSS = """
QWidget            { background: #2b2d3a; color: #eef0fa; font-size: 12px; }
QTextEdit, QLineEdit {
    background: #3a3d4f; color: #f0f2fa;
    border: 1px solid #4a4e63; border-radius: 6px; padding: 6px;
}
QScrollBar:vertical {
    background: #3a3d4f; width: 8px; border-radius: 4px;
}
QScrollBar::handle:vertical { background: #5a6cff; border-radius: 4px; }
QPushButton {
    background: #5a6cff; color: white; border: none;
    border-radius: 6px; padding: 6px 14px; font-weight: bold;
}
QPushButton:hover          { background: #6d7dff; }
QPushButton[role="del"]    { background: #8b2020; }
QPushButton[role="del"]:hover { background: #aa3030; }
QCheckBox              { spacing: 8px; color: #eef0fa; }
QCheckBox::indicator   { width: 14px; height: 14px; border-radius: 3px;
                         border: 1px solid #5a6cff; background: #3a3d4f; }
QCheckBox::indicator:checked { background: #5a6cff; }
QScrollArea            { border: none; }
"""


class QuickNotesWindow(QWidget):
    """Always-on-top notepad — saves to notes.txt on close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝  Quick Notes")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_QSS)
        self.resize(320, 280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._edit = QTextEdit()
        self._edit.setPlaceholderText("Write anything here…")
        layout.addWidget(self._edit)

        row = QHBoxLayout()
        row.addStretch()
        clr = QPushButton("Clear")
        clr.setProperty("role", "del")
        clr.clicked.connect(self._edit.clear)
        sv = QPushButton("Save")
        sv.clicked.connect(self._save)
        row.addWidget(clr)
        row.addWidget(sv)
        layout.addLayout(row)

        self._load()

    def _load(self) -> None:
        try:
            with open(_NOTES_PATH, "r", encoding="utf-8") as fh:
                self._edit.setPlainText(fh.read())
        except OSError:
            pass

    def _save(self) -> None:
        try:
            with open(_NOTES_PATH, "w", encoding="utf-8") as fh:
                fh.write(self._edit.toPlainText())
        except OSError:
            pass

    def closeEvent(self, event) -> None:
        self._save()
        super().closeEvent(event)


class TodoListWindow(QWidget):
    """Persistent checklist — items saved to todo_list.json."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("✅  To-Do List")
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setStyleSheet(_QSS)
        self.resize(300, 380)

        self._items: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Your to-do list:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._container = QWidget()
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setAlignment(Qt.AlignTop)
        self._vbox.setSpacing(4)
        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        row = QHBoxLayout()
        self._entry = QLineEdit()
        self._entry.setPlaceholderText("Add a task…")
        self._entry.returnPressed.connect(self._add)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add)
        row.addWidget(self._entry, 1)
        row.addWidget(add_btn)
        layout.addLayout(row)

        self._load()

    # ------------------------------------------------------------------ #
    def _add(self) -> None:
        text = self._entry.text().strip()
        if text:
            self._items.append({"text": text, "done": False})
            self._entry.clear()
            self._rebuild()
            self._save()

    def _toggle(self, idx: int, checked: bool) -> None:
        if 0 <= idx < len(self._items):
            self._items[idx]["done"] = checked
            self._save()
            self._rebuild()

    def _delete(self, idx: int) -> None:
        if 0 <= idx < len(self._items):
            self._items.pop(idx)
            self._rebuild()
            self._save()

    def _rebuild(self) -> None:
        while self._vbox.count():
            child = self._vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for i, item in enumerate(self._items):
            row = QHBoxLayout()
            cb = QCheckBox(item["text"])
            cb.setChecked(item["done"])
            cb.toggled.connect(lambda chk, idx=i: self._toggle(idx, chk))
            if item["done"]:
                cb.setText("✓ " + item["text"])
                cb.setStyleSheet("QCheckBox { color: #606280; }")
            del_btn = QPushButton("✕")
            del_btn.setProperty("role", "del")
            del_btn.setFixedWidth(28)
            del_btn.clicked.connect(lambda _c, idx=i: self._delete(idx))
            row.addWidget(cb, 1)
            row.addWidget(del_btn)
            wrapper = QWidget()
            wrapper.setLayout(row)
            self._vbox.addWidget(wrapper)

    # ------------------------------------------------------------------ #
    def _load(self) -> None:
        try:
            with open(_TODO_PATH, "r", encoding="utf-8") as fh:
                self._items = json.load(fh)
        except (OSError, ValueError):
            self._items = []
        self._rebuild()

    def _save(self) -> None:
        try:
            with open(_TODO_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._items, fh, indent=2)
        except OSError:
            pass
