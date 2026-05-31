# 🐾 Desktop Pet

A lively animated companion that lives on your Windows taskbar — reacts to your battery, weather, downloads, and more. Pat it, drag it, throw it, or just let it wander while you work.

---

## ⬇️ Download

**[Download Desktop Pet](https://your-website.com)**

> If Windows shows a security warning, click **"More info"** → **"Run anyway"** — this is normal for new apps.

Starts automatically with Windows on first launch. No setup required.

---

## 🐱 Characters

| Cat | Slime | Naruto | Luffy |
|-----|-------|--------|-------|
| Default | Bouncy | Ninja | Pirate |

Add more characters from the website — right-click the pet → **Settings → Characters → Add Character**

---

## ✨ Features

- 🖱 **Interactive** — left-click to pat, drag to move, throw to fling, shake to annoy
- 💬 **Talks** — random chatter based on time of day, mood, and season
- 😊 **Mood system** — mood changes based on how you treat it, saved between sessions
- ⚡ **Reacts to your PC** — battery, downloads, idle, File Explorer, weather
- ☀️ **Live weather** — fetches real weather and reacts to it (set your city in Settings)
- 🎉 **Gags** — balloon, rocket, portal, dance, moonwalk, freeze, cursor steal, and more
- 🪟 **Sit on windows** — pet climbs to the top edge of any open app window
- 🧲 **Magnet mode** — attract or repel the pet with your cursor
- 📋 **Productivity** — quick notes, to-do list, countdown timer, reminders
- 🐾 **Multiple pets** — spawn more than one, they interact with each other
- 🎵 **Custom sounds** — replace any sound effect with your own `.wav` file
- 💬 **Custom lines** — add your own speech bubble messages
- 🌨 **Seasonal effects** — snow, cherry blossoms, autumn leaves
- 🔕 **Fullscreen hide** — disappears when you're in a game or video

---

## 🖱 Controls

| Action | Result |
|--------|--------|
| Left-click | Pat — pet jumps happily |
| Double-click | Pet says something |
| Drag | Pick up and move anywhere |
| Throw (fast drag release) | Fling the pet across the screen |
| Shake (back and forth) | Pet gets angry |
| Right-click | Full menu |

---

## ⚙️ Settings

Right-click the pet → **Settings**

- Change character, size, speed
- Set pet name & birthday
- Set your city for live weather
- Toggle reactions on/off
- Add custom speech lines and sounds
- Enable/disable auto-startup

---

## 🛠 For Developers

### Requirements
```
Python 3.10+
pip install PyQt5
```

### Run from source
```bash
python main.py
```

### Build the .exe
```bash
build_exe.bat
# Output: dist\DesktopPet.exe
```

### Build the installer
1. Run `build_exe.bat` first
2. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php)
3. Open `installer.iss` → click **Build**
4. Output: `output\DesktopPetSetup.exe`

### Add a new character
Drop a folder into `characters/` with this structure:
```
characters/
  my_pet/
    config.json       ← name, messages, sounds, scale
    idle/             ← frame_00.png, frame_01.png ...
    walk/
    sleep/
    fall/
    sounds/           ← walk.wav, grab.wav, land.wav, sleep.wav
```

---

## 📁 Project Structure

```
desktop-pet/
├── main.py               ← entry point
├── pet/                  ← all app modules
├── characters/           ← character art & config
├── assets/               ← icon, emotes
├── tools/                ← sprite & sound generators
├── build_exe.bat         ← builds DesktopPet.exe
├── installer.iss         ← builds the installer
└── DesktopPet.spec       ← PyInstaller config
```

---

## 📄 License

MIT — free to use, modify, and distribute.

---

*Made with ♥ by tyx*
