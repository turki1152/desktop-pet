"""
settings_dialog.py
==================
Full settings dialog — tabs:
  General   — character, size, speed, sound, startup, fullscreen, weather
  Characters— add / remove downloadable characters
  Reactions — per-event toggles, chatter frequency, bubble duration
  Speech    — user-defined custom chatter lines
  Sounds    — per-event .wav overrides
  Help / About
"""
from __future__ import annotations

import os
import shutil
import zipfile

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QImage
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from .character import discover_characters
from .startup import is_startup_enabled, set_startup

SOUND_EVENTS = ["walk", "grab", "land", "sleep"]

_PROTECTED_CHARACTERS = {"cat"}   # these can never be removed

_QSS = """
QDialog {
    background-color: #1e2030;
    font-family: "Segoe UI";
    font-size: 12px;
}
QTabWidget::pane {
    background-color: #252838;
    border: 1px solid #363952;
    border-radius: 0 8px 8px 8px;
}
QTabBar::tab {
    background-color: #1e2030;
    color: #7880a4;
    padding: 9px 18px;
    border: 1px solid transparent;
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #252838;
    color: #eef0fa;
    border-color: #363952;
    font-weight: bold;
}
QTabBar::tab:hover:!selected { color: #b0b8d8; background-color: #222436; }
QWidget { background: #252838; }
QLabel  { color: #b0b8d8; font-size: 12px; background: transparent; }
QLabel[class="section"] {
    color: #5a6cff; font-size: 11px; font-weight: bold;
    padding-top: 6px; background: transparent;
}
QLabel[class="hint"] { color: #585e7a; font-size: 11px; background: transparent; }
QComboBox {
    background-color: #2e3045;
    color: #eef0fa;
    border: 1px solid #454860;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    min-height: 30px;
}
QComboBox:hover { border-color: #5a6cff; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView {
    background-color: #2e3045;
    color: #eef0fa;
    selection-background-color: #5a6cff;
    border: 1px solid #454860;
    padding: 4px;
    outline: none;
}
QCheckBox { color: #c0c4de; spacing: 10px; font-size: 12px; background: transparent; }
QCheckBox::indicator {
    width: 17px; height: 17px;
    border-radius: 5px;
    border: 1.5px solid #454860;
    background: #2e3045;
}
QCheckBox::indicator:checked { background: #5a6cff; border-color: #5a6cff; }
QCheckBox::indicator:hover   { border-color: #5a6cff; }
QListWidget {
    background-color: #1a1c2c;
    color: #eef0fa;
    border: 1px solid #363952;
    border-radius: 8px;
    font-size: 12px;
    padding: 4px;
    outline: none;
}
QListWidget::item { padding: 6px 8px; border-radius: 5px; }
QListWidget::item:selected { background-color: #5a6cff; color: white; }
QListWidget::item:hover:!selected { background-color: #2e3045; }
QLineEdit {
    background-color: #2e3045;
    color: #eef0fa;
    border: 1px solid #454860;
    border-radius: 6px;
    padding: 5px 10px;
    font-size: 12px;
    min-height: 30px;
}
QLineEdit:focus { border-color: #5a6cff; }
QPushButton {
    background-color: #5a6cff;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 7px 16px;
    font-size: 12px;
    font-weight: bold;
    min-height: 30px;
}
QPushButton:hover   { background-color: #6d7dff; }
QPushButton:pressed { background-color: #4a5aee; }
QPushButton#cancel  { background-color: #363952; color: #b0b8d8; font-weight: normal; }
QPushButton#cancel:hover { background-color: #454860; }
QPushButton#danger  { background-color: #7a2030; color: #ffb0b8; font-weight: normal; }
QPushButton#danger:hover { background-color: #9a2838; }
QPushButton#small   { padding: 5px 10px; min-height: 26px; font-size: 11px; font-weight: normal; }
QSlider::groove:horizontal {
    height: 6px; background: #363952; border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px; height: 16px; margin: -5px 0;
    background: #5a6cff; border-radius: 8px;
}
QSlider::sub-page:horizontal { background: #5a6cff; border-radius: 3px; }
QScrollBar:vertical {
    background: #1a1c2c; width: 8px; border-radius: 4px; margin: 0;
}
QScrollBar::handle:vertical { background: #454860; border-radius: 4px; min-height: 20px; }
QScrollBar::handle:vertical:hover { background: #5a6cff; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QDialogButtonBox QPushButton { min-width: 90px; }
"""


def _section(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "section")
    return lbl


def _hint(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("class", "hint")
    return lbl


class SettingsDialog(QDialog):
    def __init__(self, settings, characters_dir: str, assets_dir: str = "",
                 parent=None, pet_pixmap: QPixmap | None = None):
        super().__init__(parent)
        self.settings        = settings
        self.characters_dir  = characters_dir
        self._assets_dir     = assets_dir
        self._pet_pixmap     = pet_pixmap   # live sprite from the running pet

        self.setWindowTitle("Desktop Pet — Settings")
        self.setMinimumWidth(620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(_QSS)

        # Window icon — prefer the pet sprite so it's never the Python logo
        if pet_pixmap and not pet_pixmap.isNull():
            self.setWindowIcon(QIcon(pet_pixmap))
        else:
            icon_path = os.path.join(assets_dir, "icon.ico") if assets_dir else ""
            if os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 14)
        root.setSpacing(0)

        # ── Header banner ────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(64)
        header.setStyleSheet("background: #12141f; border-bottom: 1px solid #2a2d42;")
        h_row = QHBoxLayout(header)
        h_row.setContentsMargins(18, 0, 18, 0)
        h_row.setSpacing(14)

        # Icon — use the live pet sprite (pixel art stays crisp with FastTransformation)
        icon_lbl = QLabel()
        if self._pet_pixmap and not self._pet_pixmap.isNull():
            pix = self._pet_pixmap.scaled(
                44, 44, Qt.KeepAspectRatio, Qt.FastTransformation)
            icon_lbl.setPixmap(pix)
        else:
            icon_path = os.path.join(assets_dir, "icon.ico") if assets_dir else ""
            if os.path.isfile(icon_path):
                pix = QPixmap(icon_path).scaled(
                    44, 44, Qt.KeepAspectRatio, Qt.FastTransformation)
                icon_lbl.setPixmap(pix)
            else:
                icon_lbl.setText("🐾")
                icon_lbl.setStyleSheet("font-size: 28px; background: transparent;")
        icon_lbl.setFixedSize(48, 48)
        h_row.addWidget(icon_lbl)

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_lbl = QLabel("Desktop Pet")
        title_lbl.setStyleSheet(
            "color: #eef0fa; font-size: 15px; font-weight: bold; background: transparent;")
        sub_lbl = QLabel("Settings")
        sub_lbl.setStyleSheet("color: #5a6cff; font-size: 11px; background: transparent;")
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)
        h_row.addLayout(title_col)
        h_row.addStretch()

        root.addWidget(header)

        # ── Tabs ─────────────────────────────────────────────────────────
        tabs_wrapper = QWidget()
        tabs_wrapper.setStyleSheet("background: #1e2030;")
        tw_lay = QVBoxLayout(tabs_wrapper)
        tw_lay.setContentsMargins(14, 10, 14, 0)
        tw_lay.setSpacing(0)

        tabs = QTabWidget()
        tabs.tabBar().setExpanding(True)   # tabs spread across full width — no arrows
        tabs.addTab(self._make_general_tab(),    "General")
        tabs.addTab(self._make_characters_tab(), "Characters")
        tabs.addTab(self._make_reactions_tab(),  "Reactions")
        tabs.addTab(self._make_speech_tab(),     "Speech")
        tabs.addTab(self._make_sounds_tab(),     "Sounds")
        tabs.addTab(self._make_help_tab(),       "Help")
        tabs.addTab(self._make_about_tab(),      "About")
        tw_lay.addWidget(tabs)
        root.addWidget(tabs_wrapper)

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(14, 10, 14, 0)
        btn_row.setSpacing(8)

        uninstall_btn = QPushButton("🗑  Uninstall…")
        uninstall_btn.setObjectName("danger")
        uninstall_btn.setFixedHeight(32)
        uninstall_btn.clicked.connect(self._uninstall)
        btn_row.addWidget(uninstall_btn)
        btn_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        if cancel_btn:
            cancel_btn.setObjectName("cancel")
        btn_row.addWidget(buttons)

        root.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    # General tab
    # ------------------------------------------------------------------ #
    def _make_general_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        form.addRow(_section("Pet Identity"))

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g.  Whiskers, Buddy, Luna…")
        self._name_edit.setText(self.settings.pet_name)
        form.addRow("Pet name:", self._name_edit)

        self._birthday_edit = QLineEdit()
        self._birthday_edit.setPlaceholderText("MM-DD  e.g. 06-15")
        self._birthday_edit.setMaxLength(5)
        self._birthday_edit.setText(self.settings.pet_birthday)
        form.addRow("Birthday:", self._birthday_edit)
        form.addRow("", _hint("Format: MM-DD  •  Pet celebrates once per year"))

        form.addRow(_section("Appearance"))

        self._char_combo = QComboBox()
        characters = discover_characters(self.characters_dir)
        for key in characters:
            self._char_combo.addItem(key.title(), key)
        idx = next((i for i, k in enumerate(characters)
                    if k == self.settings.character), 0)
        self._char_combo.setCurrentIndex(idx)
        form.addRow("Character:", self._char_combo)

        self._size_combo = QComboBox()
        _sizes = [("Tiny (0.4×)", 0.4), ("Small (0.55×)", 0.55),
                  ("Medium (0.75×)", 0.75), ("Large (1.0×)", 1.0)]
        for label, val in _sizes:
            self._size_combo.addItem(label, val)
        self._size_combo.setCurrentIndex(
            min(range(len(_sizes)), key=lambda i: abs(_sizes[i][1] - self.settings.scale)))
        form.addRow("Size:", self._size_combo)

        self._speed_combo = QComboBox()
        _speeds = [("Slow (0.6×)", 0.6), ("Normal (1.0×)", 1.0),
                   ("Fast (1.6×)", 1.6), ("Turbo (2.4×)", 2.4)]
        for label, val in _speeds:
            self._speed_combo.addItem(label, val)
        self._speed_combo.setCurrentIndex(
            min(range(len(_speeds)), key=lambda i: abs(_speeds[i][1] - self.settings.speed)))
        form.addRow("Speed:", self._speed_combo)

        form.addRow(_section("Audio"))

        self._mute_check = QCheckBox("Mute all sound effects")
        self._mute_check.setChecked(self.settings.muted)
        form.addRow("", self._mute_check)

        form.addRow(_section("System"))

        self._startup_check = QCheckBox("Launch Desktop Pet when Windows starts")
        self._startup_check.setChecked(is_startup_enabled())
        form.addRow("", self._startup_check)

        self._fullscreen_check = QCheckBox("Hide pet when a fullscreen app is active")
        self._fullscreen_check.setChecked(self.settings.hide_fullscreen)
        form.addRow("", self._fullscreen_check)

        form.addRow(_section("Weather"))

        self._weather_check = QCheckBox("Fetch live weather and react to it")
        self._weather_check.setChecked(self.settings.weather_enabled)
        form.addRow("", self._weather_check)

        self._city_edit = QLineEdit()
        self._city_edit.setPlaceholderText("e.g.  London, Tokyo, New York  (leave empty to auto-detect)")
        self._city_edit.setText(self.settings.weather_city)
        form.addRow("City:", self._city_edit)
        form.addRow("", _hint("Uses wttr.in — no account needed.  Leave blank to detect by IP."))

        return w

    # ------------------------------------------------------------------ #
    # Characters tab
    # ------------------------------------------------------------------ #
    def _make_characters_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(_section("Installed Characters"))
        lay.addWidget(_hint(
            "Characters are stored in the 'characters/' folder.  "
            "Each character zip includes its sprites AND speech lines."))

        self._char_list = QListWidget()
        self._refresh_char_list()
        lay.addWidget(self._char_list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        add_btn = QPushButton("➕  Add Character (.zip)")
        add_btn.clicked.connect(self._add_character)
        btn_row.addWidget(add_btn)

        remove_btn = QPushButton("🗑  Remove Selected")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_character)
        btn_row.addWidget(remove_btn)

        lay.addLayout(btn_row)
        lay.addWidget(_hint(
            "Import a character .zip from the Desktop Pet website.\n"
            "The zip must contain a single folder with an 'idle/' subfolder and config.json.\n"
            "The built-in cat character cannot be removed."))
        lay.addStretch()
        return w

    def _refresh_char_list(self) -> None:
        self._char_list.clear()
        for key in discover_characters(self.characters_dir):
            protected = key.lower() in _PROTECTED_CHARACTERS
            label = f"{'🔒  ' if protected else '     '}{key.title()}"
            if protected:
                label += "  (built-in)"
            self._char_list.addItem(label)
            # Store key in item data using Qt.UserRole-equivalent via setData
            item = self._char_list.item(self._char_list.count() - 1)
            item.setData(Qt.UserRole, key)

    def _add_character(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Character ZIP", "", "ZIP archives (*.zip)")
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                # Find the top-level folder name
                roots = {n.split("/")[0] for n in names if n.strip()}
                if len(roots) != 1:
                    raise ValueError("ZIP must contain exactly one character folder.")
                char_key = list(roots)[0]
                if not char_key:
                    raise ValueError("Invalid ZIP structure.")
                # Must have an idle/ subfolder
                has_idle = any(
                    n.startswith(f"{char_key}/idle/") and n.endswith(".png")
                    for n in names
                )
                if not has_idle:
                    raise ValueError(f"No idle sprites found inside '{char_key}/idle/'.")
                dest = self.characters_dir
                zf.extractall(dest)
        except Exception as exc:
            QMessageBox.warning(self, "Import Failed",
                                f"Could not import character:\n{exc}")
            return
        self._refresh_char_list()
        # Also update the General tab character combo
        current_key = self._char_combo.currentData()
        self._char_combo.clear()
        for key in discover_characters(self.characters_dir):
            self._char_combo.addItem(key.title(), key)
        idx = next((i for i in range(self._char_combo.count())
                    if self._char_combo.itemData(i) == current_key), 0)
        self._char_combo.setCurrentIndex(idx)
        QMessageBox.information(self, "Character Added",
                                f"'{char_key.title()}' was added successfully!\n"
                                "Speech lines are loaded from the character's config.json.")

    def _remove_character(self) -> None:
        item = self._char_list.currentItem()
        if not item:
            return
        key = item.data(Qt.UserRole)
        if key.lower() in _PROTECTED_CHARACTERS:
            QMessageBox.information(self, "Protected",
                                    f"'{key.title()}' is a built-in character and cannot be removed.")
            return
        reply = QMessageBox.question(
            self, "Remove Character",
            f"Remove '{key.title()}' and all its files?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        folder = os.path.join(self.characters_dir, key)
        try:
            shutil.rmtree(folder)
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Could not remove character:\n{exc}")
            return
        self._refresh_char_list()
        # Update combo in General tab
        current_key = self._char_combo.currentData()
        self._char_combo.clear()
        for k in discover_characters(self.characters_dir):
            self._char_combo.addItem(k.title(), k)
        # If the active character was removed, fall back to first
        idx = next((i for i in range(self._char_combo.count())
                    if self._char_combo.itemData(i) == current_key), 0)
        self._char_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------ #
    # Reactions tab
    # ------------------------------------------------------------------ #
    def _make_reactions_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        form.addRow(_section("System Reactions"))

        self._r_battery   = QCheckBox("React to battery changes (charging, low, full)")
        self._r_idle      = QCheckBox("React when you leave or return to the computer")
        self._r_gaming    = QCheckBox("Warn after 1 hour of fullscreen / gaming")
        self._r_downloads = QCheckBox("React when a new file appears in Downloads")
        self._r_folder    = QCheckBox("React when File Explorer is opened")
        self._r_birthday  = QCheckBox("Birthday celebration once per year")

        self._r_battery.setChecked(self.settings.reaction_battery)
        self._r_idle.setChecked(self.settings.reaction_idle)
        self._r_gaming.setChecked(self.settings.reaction_gaming)
        self._r_downloads.setChecked(self.settings.reaction_downloads)
        self._r_folder.setChecked(self.settings.reaction_folder)
        self._r_birthday.setChecked(self.settings.reaction_birthday)

        for cb in (self._r_battery, self._r_idle, self._r_gaming,
                   self._r_downloads, self._r_folder, self._r_birthday):
            form.addRow("", cb)

        form.addRow(_section("Visual & Ambiance"))

        self._r_seasonal  = QCheckBox("Seasonal particle effects (snow, flowers, leaves)")
        self._r_seasonal.setChecked(self.settings.reaction_seasonal)
        form.addRow("", self._r_seasonal)

        form.addRow(_section("Chatter Frequency"))

        self._chatter_combo = QComboBox()
        self._chatter_combo.addItem("Rarely  (60 – 120 s)",  "rarely")
        self._chatter_combo.addItem("Normal  (28 – 70 s)",   "normal")
        self._chatter_combo.addItem("Often   (12 – 30 s)",   "often")
        self._chatter_combo.addItem("Always  (4 – 12 s)",    "always")
        freq_map = {"rarely": 0, "normal": 1, "often": 2, "always": 3}
        self._chatter_combo.setCurrentIndex(
            freq_map.get(self.settings.chatter_freq, 1))
        form.addRow("How often the pet talks:", self._chatter_combo)

        form.addRow(_section("Speech Bubble Duration"))

        self._bubble_combo = QComboBox()
        self._bubble_combo.addItem("Short  (2 s)",    2.0)
        self._bubble_combo.addItem("Normal (3 s)",    3.0)
        self._bubble_combo.addItem("Long   (5 s)",    5.0)
        self._bubble_combo.addItem("Very long (8 s)", 8.0)
        dur_map = {2.0: 0, 3.0: 1, 5.0: 2, 8.0: 3}
        self._bubble_combo.setCurrentIndex(
            dur_map.get(round(self.settings.bubble_duration, 1), 1))
        form.addRow("How long bubbles stay:", self._bubble_combo)

        return w

    # ------------------------------------------------------------------ #
    # Speech tab
    # ------------------------------------------------------------------ #
    def _make_speech_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(_section("Custom Speech Lines"))
        lay.addWidget(_hint(
            "These lines are mixed into the pet's random chatter.\n"
            "Press Enter or click Add to save a line."))

        self._speech_list = QListWidget()
        for line in self.settings.custom_lines:
            self._speech_list.addItem(line)
        lay.addWidget(self._speech_list)

        row = QHBoxLayout()
        row.setSpacing(6)
        self._speech_input = QLineEdit()
        self._speech_input.setPlaceholderText("Type something the pet should say...")
        self._speech_input.returnPressed.connect(self._add_speech_line)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("small")
        add_btn.setMinimumWidth(64)
        add_btn.clicked.connect(self._add_speech_line)
        del_btn = QPushButton("Remove")
        del_btn.setObjectName("cancel")
        del_btn.setMinimumWidth(80)
        del_btn.clicked.connect(self._del_speech_line)
        row.addWidget(self._speech_input, 1)
        row.addWidget(add_btn)
        row.addWidget(del_btn)
        lay.addLayout(row)
        return w

    # ------------------------------------------------------------------ #
    # Sounds tab
    # ------------------------------------------------------------------ #
    def _make_sounds_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        lay.addWidget(_section("Custom Sound Effects"))
        lay.addWidget(_hint(
            "Select a .wav file to override the character's default sound.\n"
            "Leave blank to use the character's own sounds."))

        self._sound_edits: dict[str, QLineEdit] = {}
        for event in SOUND_EVENTS:
            row = QHBoxLayout()
            row.setSpacing(6)
            lbl = QLabel(f"{event.title()}:")
            lbl.setFixedWidth(60)
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            edit = QLineEdit()
            edit.setText(self.settings.custom_sounds.get(event, ""))
            edit.setPlaceholderText("(character default)")
            browse = QPushButton("Browse")
            browse.setObjectName("small")
            browse.setMinimumWidth(72)
            browse.clicked.connect(lambda _c, e=event: self._browse_sound(e))
            clear = QPushButton("Clear")
            clear.setObjectName("cancel")
            clear.setMinimumWidth(60)
            clear.clicked.connect(lambda _c, e=event: self._sound_edits[e].clear())
            row.addWidget(lbl)
            row.addWidget(edit, 1)
            row.addWidget(browse)
            row.addWidget(clear)
            self._sound_edits[event] = edit
            lay.addLayout(row)

        lay.addStretch()
        return w

    # ------------------------------------------------------------------ #
    # Help tab
    # ------------------------------------------------------------------ #
    def _make_help_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #252838; border: none; }")

        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(20, 16, 20, 20)
        lay.setSpacing(4)

        def _h(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                "color: #5a6cff; font-size: 13px; font-weight: bold; "
                "background: transparent; padding-top: 14px; padding-bottom: 2px;")
            return lbl

        def _p(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #b0b8d8; font-size: 12px; background: transparent; padding-left: 4px;")
            return lbl

        def _row(icon: str, label: str, desc: str) -> QLabel:
            lbl = QLabel(f"<b style='color:#eef0fa'>{icon}  {label}</b>"
                         f"<span style='color:#585e7a'> — </span>"
                         f"<span style='color:#9098b8'>{desc}</span>")
            lbl.setWordWrap(True)
            lbl.setStyleSheet("background: transparent; font-size: 12px; padding: 3px 4px;")
            return lbl

        lay.addWidget(_h("🖱  Basic Interaction"))
        lay.addWidget(_row("Left-click",   "Pat",       "Pet jumps and feels loved. Improves mood."))
        lay.addWidget(_row("Double-click", "Chat",      "Pet says something. Mood affects what it says."))
        lay.addWidget(_row("Drag",         "Pick up",   "Drag the pet anywhere on screen."))
        lay.addWidget(_row("Throw",        "Launch",    "Release while moving fast to send it flying."))
        lay.addWidget(_row("Shake",        "Angry",     "Shake the pet back and forth 4+ times — it gets mad."))
        lay.addWidget(_row("Right-click",  "Menu",      "Opens the full menu with all options."))

        lay.addWidget(_h("🔔  System Tray Icon"))
        lay.addWidget(_row("Left-click",  "Quick menu", "Show/Hide pet, open Settings, or Exit."))
        lay.addWidget(_row("Right-click", "Full menu",  "Access every feature from the tray."))

        lay.addWidget(_h("🎭  Appearance"))
        lay.addWidget(_row("Character", "Skin",   "Choose from installed characters."))
        lay.addWidget(_row("Size",      "Scale",  "Tiny / Small / Medium / Large."))
        lay.addWidget(_row("Speed",     "Movement", "How fast the pet walks and reacts."))

        lay.addWidget(_h("😊  Mood System"))
        lay.addWidget(_p(
            "The pet has a mood (Happy, Neutral, Sad, Excited, Grumpy) that changes based on "
            "how you interact with it. Patting and playing raise the mood; shaking or ignoring "
            "it lowers it. Mood affects what the pet says."))

        lay.addWidget(_h("⚡  Automatic Reactions"))
        lay.addWidget(_row("Battery",   "Charger events", "Reacts when you plug in, unplug, or hit low/critical battery."))
        lay.addWidget(_row("Idle",      "Away / Back",    "Notices when you leave and welcomes you back."))
        lay.addWidget(_row("Gaming",    "Long session",   "Warns after 1 hour of fullscreen / gaming."))
        lay.addWidget(_row("Downloads", "New file",       "Celebrates when a new file appears in Downloads."))
        lay.addWidget(_row("Explorer",  "Folder open",    "Comments when File Explorer is opened or closed."))
        lay.addWidget(_row("Weather",   "Live weather",   "Fetches current weather and reacts (set your city in General)."))
        lay.addWidget(_row("Birthday",  "Annual",         "Celebrates once a year on the pet's birthday."))
        lay.addWidget(_row("Seasonal",  "Particles",      "Snow in winter, flowers in spring, leaves in autumn."))

        lay.addWidget(_h("🎉  Fun & Gags"))
        for icon, label, desc in [
            ("🎈", "Balloon",       "Pet rises to the top and floats."),
            ("🚀", "Rocket",        "Blasts off the screen and returns."),
            ("🌀", "Portal",        "Disappears and reappears at a random spot."),
            ("🕺", "Dance",         "Dances in place."),
            ("🌙", "Moonwalk",      "Walks backwards like Michael Jackson."),
            ("🙃", "Flip",          "Rendered upside down until it recovers."),
            ("🥶", "Frozen",        "Freezes the animation for a moment."),
            ("😵", "Stuck",         "Struggles in place."),
            ("📍", "Slide off edge","Slides off-screen and walks back."),
            ("😈", "Steal cursor",  "Teleports your cursor to the opposite side for 1 s."),
            ("💥", "Break desktop", "Flashes a red overlay as if something went wrong."),
            ("🌨", "Particles",     "Spawns seasonal particles."),
        ]:
            lay.addWidget(_row(icon, label, desc))

        lay.addWidget(_h("🐾  Characters"))
        lay.addWidget(_p(
            "Go to Settings → Characters to add new characters from ZIP files downloaded "
            "from the Desktop Pet website. Each ZIP includes the character's sprites and "
            "speech lines in its config.json. Remove characters you no longer want "
            "(the built-in cat cannot be removed)."))

        lay.addStretch()
        scroll.setWidget(inner)
        return scroll

    # ------------------------------------------------------------------ #
    # About tab
    # ------------------------------------------------------------------ #
    def _make_about_tab(self) -> QWidget:
        w = QWidget()
        outer = QVBoxLayout(w)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(0)

        title = QLabel("🐾  Desktop Pet")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #eef0fa; background: transparent; padding-bottom: 4px;")
        outer.addWidget(title)

        version = QLabel("Version 1.0.0")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet("font-size: 12px; color: #5a6cff; background: transparent; padding-bottom: 18px;")
        outer.addWidget(version)

        desc = QLabel(
            "A lively animated desktop companion that reacts to what\n"
            "you do on your PC — battery, weather, downloads, idling,\n"
            "and much more. Tap it, drag it, give it gags, or just let\n"
            "it wander around while you work."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8890b4; font-size: 12px; background: transparent; padding-bottom: 20px;")
        outer.addWidget(desc)

        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background: #363952; margin-bottom: 18px;")
        outer.addWidget(line)

        info_layout = QFormLayout()
        info_layout.setSpacing(8)
        info_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        info_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        def _info_val(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #eef0fa; background: transparent; font-size: 12px;")
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            return lbl

        def _info_key(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #585e7a; background: transparent; font-size: 12px;")
            return lbl

        info_layout.addRow(_info_key("Author:"),    _info_val("tyx"))
        info_layout.addRow(_info_key("GitHub:"),    _info_val("github.com/turki1152/desktop-pet"))
        info_layout.addRow(_info_key("License:"),   _info_val("MIT"))
        info_layout.addRow(_info_key("Built with:"),_info_val("Python 3.10  •  PyQt5"))
        outer.addLayout(info_layout)
        outer.addStretch()

        credit = QLabel("Made with ♥ for your desktop")
        credit.setAlignment(Qt.AlignCenter)
        credit.setStyleSheet("color: #3a3e56; font-size: 11px; background: transparent; padding-top: 16px;")
        outer.addWidget(credit)

        return w

    # ------------------------------------------------------------------ #
    # Uninstaller
    # ------------------------------------------------------------------ #
    def _uninstall(self) -> None:
        reply = QMessageBox.question(
            self, "Uninstall Desktop Pet",
            "This will:\n"
            "  • Remove Desktop Pet from Windows startup\n"
            "  • Delete your settings (settings.json)\n\n"
            "Your character files will NOT be deleted.\n\n"
            "Are you sure?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        # Remove from startup
        set_startup(False)

        # Delete settings file
        from .paths import base_dir
        settings_path = os.path.join(base_dir(), "settings.json")
        try:
            if os.path.isfile(settings_path):
                os.remove(settings_path)
        except OSError:
            pass

        QMessageBox.information(
            self, "Uninstalled",
            "Desktop Pet has been removed from startup and settings cleared.\n\n"
            "To fully uninstall, delete the application folder:\n"
            f"{base_dir()}")

        from PyQt5.QtWidgets import QApplication
        self.reject()
        QApplication.quit()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _add_speech_line(self) -> None:
        text = self._speech_input.text().strip()
        if text:
            self._speech_list.addItem(text)
            self._speech_input.clear()

    def _del_speech_line(self) -> None:
        row = self._speech_list.currentRow()
        if row >= 0:
            self._speech_list.takeItem(row)

    def _browse_sound(self, event: str) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, f"Select sound for '{event}'", "", "WAV files (*.wav)")
        if path:
            self._sound_edits[event].setText(path)

    # ------------------------------------------------------------------ #
    # Apply
    # ------------------------------------------------------------------ #
    def apply(self, pet_widget) -> None:
        s = self.settings

        # Identity
        s.pet_name = self._name_edit.text().strip()
        bday = self._birthday_edit.text().strip()
        if bday != s.pet_birthday:
            s.pet_birthday = bday
            s.last_birthday_year = 0

        # Appearance
        new_char = self._char_combo.currentData()
        if new_char and new_char != s.character:
            pet_widget._change_character(new_char)

        new_scale = self._size_combo.currentData()
        if abs(new_scale - s.scale) > 1e-3:
            pet_widget._change_scale(new_scale)

        new_speed = self._speed_combo.currentData()
        if abs(new_speed - s.speed) > 1e-3:
            pet_widget._change_speed(new_speed)

        if self._mute_check.isChecked() != s.muted:
            pet_widget._toggle_mute()

        # System
        set_startup(self._startup_check.isChecked())
        s.hide_fullscreen = self._fullscreen_check.isChecked()

        # Weather
        s.weather_enabled = self._weather_check.isChecked()
        new_city = self._city_edit.text().strip()
        if new_city != s.weather_city:
            s.weather_city = new_city
            pet_widget._weather.set_city(new_city)

        # Reactions
        s.reaction_battery   = self._r_battery.isChecked()
        s.reaction_idle      = self._r_idle.isChecked()
        s.reaction_gaming    = self._r_gaming.isChecked()
        s.reaction_downloads = self._r_downloads.isChecked()
        s.reaction_folder    = self._r_folder.isChecked()
        s.reaction_birthday  = self._r_birthday.isChecked()
        s.reaction_seasonal  = self._r_seasonal.isChecked()
        s.chatter_freq       = self._chatter_combo.currentData()
        s.bubble_duration    = float(self._bubble_combo.currentData())

        # Speech & sounds
        s.custom_lines = [
            self._speech_list.item(i).text()
            for i in range(self._speech_list.count())
        ]
        s.custom_sounds = {
            event: edit.text().strip()
            for event, edit in self._sound_edits.items()
            if edit.text().strip()
        }
