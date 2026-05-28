# 🐾 Desktop Pet

A lightweight, customizable **desktop mascot for Windows** — a tiny pixel-art
character that sits, walks, naps, and falls along the top of your taskbar.
Pick it up and drop it, swap characters, resize it, and let it quietly keep you
company while using almost no system resources.

![Desktop Pet preview](docs/preview.png)

> Five characters ship with the app — a **cat**, a **slime**, a **ghost**, plus
> two original chibi fan-art mascots: **Naruto** and **Luffy**.

![Bundled characters](docs/characters.png)

---

## ✨ Features

- **Truly transparent** — per-pixel alpha, no window frame, no taskbar button,
  no Alt-Tab entry. Just the character floats on your desktop.
- **Lives on the taskbar** — automatically detects the taskbar position
  (bottom / top / left / right) and DPI, and rests on top of it.
- **Stays out of your way** — automatically hides while a full-screen app is in
  front (games, full-screen video, slideshows) and reappears when you're back on
  the desktop.
- **Smooth sprite animations** — idle, walking, sleeping, and falling, driven by
  a frame-rate-independent animation system.
- **A little brain** — randomly decides to idle, wander left/right, or nap, with
  edge detection so it never walks off the screen.
- **Drag & drop** — left-click and drag the pet anywhere; let go and it falls
  back down to the taskbar with gravity.
- **Personality speech bubbles** — each character has its own lines and randomly
  pipes up with wholesome reminders like *"Drink some water!"* or *"Posture
  check!"* — written to match its vibe (sassy cat, cheerful slime, caring ghost).
- **Emotions** — pat it and it's **happy** 💗, shake it around and it gets
  **angry** 💢, drop it from a height and it's **sad** 😢 — each shown with a mood
  icon and a matching line.
- **Reminders** — set a time and a message (e.g. *08:00 → Drink water*) and the
  pet will pop a bubble to remind you. Add/remove them from the menu.
- **Modern menu** — a clean, dark, rounded right-click menu (and matching
  reminder dialog), also available from the system-tray icon.
- **Multiple characters & easy modding** — every character is just a folder of
  PNG frames. Drop in a new folder and it appears in the menu — no code needed.
  Includes an **import tool** to turn a GIF or sprite sheet into a character.
- **Adjustable size & animation speed**, remembered between runs.
- **Retro sound effects** — each bundled character has its own little blips for
  grabbing, walking, landing, and napping (zero-dependency, via `winsound`).
  Toggle them with **Mute** in the menu.
- **Low CPU & memory** — one small window, a single ~30 FPS timer, and
  pre-scaled sprites mean the paint loop is just a blit.

---

## 🚀 Setup

### 1. Requirements
- **Windows 10 / 11**
- **Python 3.9+** ([python.org](https://www.python.org/downloads/) — tick
  *"Add Python to PATH"* during install)

### 2. Install dependencies
```bat
pip install -r requirements.txt
```
> `PyQt5` is the only thing needed to run the pet. `Pillow` is optional and only
> used if you want to regenerate the bundled art.

### 3. Run it
```bat
python main.py
```
Or simply **double-click `run.bat`** to start it with no console window.

That's it — your pet appears on the taskbar. 🎉

### 4. (Optional) Build a single-file `.exe`
Want to run it without Python, or share it? Build one portable executable:

```bat
build_exe.bat
```

This uses **PyInstaller** to produce a single file — `dist\DesktopPet.exe` —
with the characters and assets bundled inside it. Move that one `.exe` anywhere
(Desktop, USB stick, another PC) and double-click it — **no Python needed**.

On first run it creates editable `characters\` and `assets\` folders next to
itself (so you can customise it and add your own characters), and saves
`settings.json` / `reminders.json` there too.

> Tip: to start your pet automatically at login, press `Win+R`, type
> `shell:startup`, and drop a shortcut to `DesktopPet.exe` in that folder.

---

## 🎮 Using your pet

| Action | How |
| --- | --- |
| Move it around | **Left-click and drag** |
| Drop it | **Release** — it falls to the taskbar |
| **Pat it** (happy 💗) | **Quick click** without moving it |
| **Annoy it** (angry 💢) | **Shake it** while dragging |
| **Hurt its feelings** (sad 😢) | **Drop it from high up** |
| Make it talk | Menu → **Say something** |
| Open the menu | **Right-click** the pet (or its tray icon) |
| Change character | Menu → **Change character** |
| Resize | Menu → **Size** (Tiny … Large) |
| Animation/walk speed | Menu → **Speed** (Slow … Turbo) |
| Add a reminder | Menu → **Reminders → Add reminder…** |
| Mute sounds | Menu → **Mute / Unmute** |
| Quit | Menu → **Exit** |

Your character, size, speed, and mute choices are saved to `settings.json`, and
reminders to `reminders.json` — both restored next time.

---

## 💬 Messages, personality & emotions

Every character chatters on its own with lines drawn from its `config.json`,
grouped by mood:

- **`idle`** — random everyday chatter and wellness nudges (*"Drink some
  water!"*, *"Stretch those legs!"*). Shown every ~30–70s while idle/walking.
- **`happy`** — when you **pat** it (a quick click).
- **`angry`** — when you **shake** it around while dragging.
- **`sad`** — when you **drop** it from a height (hard landing).
- **`surprised`** / **`sleepy`** — small reactions to a bump or a nap.

The bundled pets have distinct voices: the **cat** is lazy and sassy, the
**slime** is relentlessly wholesome, the **ghost** is spooky but caring,
**Naruto** is an energetic never-give-up ninja (*"Believe it!"*), and **Luffy**
is an adventure-loving, meat-obsessed captain (*"I'm gonna be King of the
Pirates!"*). Edit any character's `messages` to give it your own voice.

> The Naruto and Luffy sprites here are **original chibi pixel art** inspired by
> the characters — not official artwork — so the project stays free to share.

## ⏰ Reminders

Right-click → **Reminders → Add reminder…**, pick a time and type a message
(e.g. *"Drink water 💧"*). At that time each day your pet pops a bubble with the
message and a little bell. Manage them from the same submenu (disable or delete).
Reminders are stored in `reminders.json`.

---

## 🧩 Adding your own characters

Want a **One Piece**, **Naruto**, or **lofi**-style character? You don't need to
draw anything — just grab some frames and import them. There are two ways.

### Folder layout
A character is just a folder inside `characters/`. The structure is:

```
characters/
└── mychar/
    ├── config.json        (optional — sensible defaults are used)
    ├── idle/              (required)  frame_00.png, frame_01.png, ...
    ├── walk/              (optional)  frame_00.png, ...
    ├── sleep/             (optional)  frame_00.png, ...
    ├── fall/              (optional)  frame_00.png, ...
    └── sounds/            (optional)  walk.wav, ...
```

- **Frames** are PNGs with transparency, named `frame_00.png`, `frame_01.png`, …
  played in order and looped. Any missing animation falls back to `idle`. Pixel
  art works best (it's upscaled with nearest-neighbour so it stays crisp), but
  any PNG works.
- Restart the pet and your character appears under **Change character**.

### Easiest: import a GIF or sprite sheet (no editing needed)
Find an animated **GIF** (e.g. a "Luffy running" loop) or a **sprite sheet**,
then let the import tool slice it into frames and create a starter config:

```bat
REM Each GIF becomes one animation state:
python tools/import_media.py --name luffy --state idle --gif idle.gif
python tools/import_media.py --name luffy --state walk --gif run.gif

REM Or a horizontal sprite sheet of 4 frames:
python tools/import_media.py --name naruto --state walk --sheet run.png --cols 4

REM Grid sheet + key out a white background to transparency:
python tools/import_media.py --name naruto --state idle --sheet sheet.png ^
    --fw 64 --fh 64 --bg "#ffffff" --tolerance 30
```

It auto-trims transparent borders and writes `characters/<name>/config.json`.
Then edit that file to give your character a name, personality and message lines
(see the reference below), restart, and pick it from the menu.

> ⚠️ Use art you have the right to use. Official anime/game sprites are
> copyrighted — great for personal/offline use, but don't redistribute them.

### `config.json` reference
Everything is optional; the values below are the defaults.

```json
{
  "name": "My Character",
  "personality": "A short note about this character's vibe.",
  "fps": { "idle": 6, "walk": 10, "sleep": 3, "fall": 8 },
  "scale": 2.5,
  "walk_speed": 38,
  "behavior": {
    "idle_min": 2.0,
    "idle_max": 6.0,
    "walk_chance": 0.55,
    "sleep_chance": 0.2
  },
  "messages": {
    "idle":      ["Drink some water!", "Don't forget to stretch~"],
    "happy":     ["Yay!", "Hehe~"],
    "angry":     ["Hey! Stop that!"],
    "sad":       ["Ouch..."],
    "surprised": ["!"],
    "sleepy":    ["Zzz..."]
  },
  "sounds": {
    "walk": "walk.wav",
    "sleep": "sleep.wav",
    "land": "land.wav",
    "grab": "grab.wav"
  }
}
```

| Key | Meaning |
| --- | --- |
| `name` | Display name in the menu (defaults to the folder name) |
| `personality` | Free-text note for whoever edits the messages (not shown in-app) |
| `fps` | Playback speed per animation state |
| `scale` | Base on-screen size multiplier for this character |
| `walk_speed` | Pixels per second while walking |
| `behavior.idle_min/max` | Seconds to stay idle before re-deciding |
| `behavior.walk_chance` | Probability of wandering after idling |
| `behavior.sleep_chance` | Probability of napping after idling |
| `messages` | Speech-bubble lines per mood: `idle` (random chatter), `happy`, `angry`, `sad`, `surprised`, `sleepy`. Any group can be omitted. |
| `sounds` | Map of event → `.wav` file in the `sounds/` folder. Events: `walk`, `sleep`, `land`, `grab` |

### Regenerating the bundled art, sounds & emotes
The default characters (art, sound effects, personality) and the shared mood
icons are all generated procedurally. To tweak or rebuild them:
```bat
python tools/generate_sprites.py    REM pixel-art frames + config (incl. messages)
python tools/generate_sounds.py     REM the .wav sound effects
python tools/generate_emotes.py     REM the shared mood icons (happy/angry/...)
```

---

## 🗂️ Project structure

```
desktop pet/
├── main.py                 # entry point (DPI setup + app bootstrap)
├── run.bat                 # double-click launcher (no console window)
├── build_exe.bat           # build a standalone DesktopPet.exe (PyInstaller)
├── requirements.txt
├── settings.json           # saved user preferences
├── reminders.json          # saved reminders (created on first use)
├── pet/                    # the application package
│   ├── paths.py            # file locations (works as script or frozen .exe)
│   ├── config.py           # load/save settings
│   ├── taskbar.py          # Win32 taskbar position + full-screen detection
│   ├── animation.py        # sprite-frame animation player
│   ├── character.py        # loads a character folder (frames/messages/sounds)
│   ├── behavior.py         # idle/walk/sleep/fall state machine
│   ├── bubble.py           # the floating speech bubble
│   ├── emotes.py           # mood-icon loader + modern menu stylesheet
│   ├── reminders.py        # reminder storage + add-reminder dialog
│   ├── sound.py            # optional non-blocking sound effects
│   └── pet_widget.py       # transparent window + emotions + menu + tray
├── characters/             # one folder per character (drop in your own!)
│   ├── cat/  slime/  ghost/  naruto/  luffy/
├── assets/
│   ├── icon.ico            # app/exe icon
│   └── emotes/             # shared mood icons (happy, angry, sad, ...)
├── tools/
│   ├── generate_sprites.py # builds the bundled pixel art + configs
│   ├── generate_sounds.py  # synthesizes the sound effects
│   ├── generate_emotes.py  # draws the mood icons
│   └── import_media.py     # turn a GIF / sprite sheet into a character
└── docs/                   # README images
```

---

## ⚙️ How it works (in brief)

- **Transparency:** a frameless `QWidget` with `WA_TranslucentBackground` and the
  `Qt.Tool | WindowStaysOnTopHint` flags — the only thing drawn is the sprite.
- **Taskbar tracking:** `SHAppBarMessage(ABM_GETTASKBARPOS)` via `ctypes` reports
  the taskbar's exact rectangle and docked edge; re-checked every couple of
  seconds so it copes with auto-hide and resolution changes.
- **Animation:** frames are loaded and pre-scaled once (with a cached mirrored
  copy for facing direction); a single `QTimer` advances them by delta-time, so
  speed is independent of the tick rate.
- **Behaviour:** a small finite-state machine (`idle → walk/sleep`, plus `fall`
  and `drag`) with gravity for the drop.
- **Emotions & bubbles:** interactions are classified (quick click = pat, shaky
  drag = shake, fast landing = hard drop) and trigger a mood; the speech bubble
  is a second tiny transparent window shown only while talking.

---

## 🩹 Troubleshooting

- **"No characters found"** — run `python tools/generate_sprites.py` to create
  the bundled art.
- **`ModuleNotFoundError: PyQt5`** — run `pip install -r requirements.txt`.
- **Pet disappeared** — this is by design while a **full-screen** app (game,
  video, slideshow) is in front; it comes back when you return to the desktop or
  a normal window. (A *maximised* window does not hide it — only true
  full-screen does.)
- **No tray icon** — harmless; right-click the pet itself to open the menu.
- **No sound** — make sure **Mute** is off in the menu and your system volume is
  up. If the `characters/*/sounds/` folders are empty, run
  `python tools/generate_sounds.py` to recreate the `.wav` files.

---

## 📄 License

Free to use, modify, and share. The bundled pixel art is generated by the
included script, so it's yours to remix too. Enjoy your new desktop buddy! 🐱👻🟢
#   d e s k t o p - p e t  
 