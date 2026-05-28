"""
generate_sprites.py
====================
Procedurally generates the pixel-art sprite frames for the bundled characters
(cat, slime, ghost) so the application ships with ready-to-use animations.

Each character is drawn on a small 32x32 transparent canvas.  The application
later upscales these frames with nearest-neighbour sampling so they keep their
crisp, retro pixel look at any size.

Run this once to (re)create the ``characters/`` folders::

    python tools/generate_sprites.py

You normally never need to run it by hand -- the repository already contains
the generated PNGs.  It is included so the art is reproducible and so you can
tweak the characters or use it as a template for your own.
"""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw

# Base resolution every frame is drawn at.  Small on purpose: pixel art.
SIZE = 32

# Where the generated characters are written (one folder per character).
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "characters"))


# --------------------------------------------------------------------------- #
# Small drawing helpers
# --------------------------------------------------------------------------- #
def _new_frame() -> Image.Image:
    """Return a fresh fully transparent RGBA canvas."""
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def _save(frames: list[Image.Image], folder: str) -> None:
    """Save a list of frames as frame_00.png, frame_01.png ... in *folder*."""
    os.makedirs(folder, exist_ok=True)
    # Remove stale frames so re-running cannot leave orphans behind.
    for old in os.listdir(folder):
        if old.startswith("frame_") and old.endswith(".png"):
            os.remove(os.path.join(folder, old))
    for i, frame in enumerate(frames):
        frame.save(os.path.join(folder, f"frame_{i:02d}.png"))


def _ellipse(d: ImageDraw.ImageDraw, box, fill, outline=None):
    d.ellipse(box, fill=fill, outline=outline)


# --------------------------------------------------------------------------- #
# Cat -- a round chibi cat with ears and four little paws
# --------------------------------------------------------------------------- #
def _cat_base(bob: int, paw_phase: int, eyes: str, body_color, accent):
    """
    Draw one cat frame.

    bob        vertical offset of the whole body in pixels (breathing/hop)
    paw_phase  0..1, alternates which paws are forward for the walk cycle
    eyes       "open", "blink" or "closed"
    """
    img = _new_frame()
    d = ImageDraw.Draw(img)

    cx = SIZE // 2
    top = 5 + bob          # top of the head/body blob
    body_bottom = 27 + bob

    # Ears (triangles) sitting on top of the head.
    d.polygon([(cx - 9, top + 2), (cx - 4, top - 4), (cx - 2, top + 3)], fill=body_color)
    d.polygon([(cx + 9, top + 2), (cx + 4, top - 4), (cx + 2, top + 3)], fill=body_color)
    # Inner ear (pink).
    d.polygon([(cx - 7, top + 1), (cx - 5, top - 2), (cx - 4, top + 1)], fill=accent)
    d.polygon([(cx + 7, top + 1), (cx + 5, top - 2), (cx + 4, top + 1)], fill=accent)

    # Main body / head -- one big friendly blob.
    _ellipse(d, [cx - 11, top, cx + 11, body_bottom], fill=body_color)

    # Paws at the bottom; walk cycle shifts the pair left/right slightly.
    shift = 2 if paw_phase else -2
    d.ellipse([cx - 9 + shift, body_bottom - 4, cx - 3 + shift, body_bottom + 1], fill=body_color)
    d.ellipse([cx + 3 - shift, body_bottom - 4, cx + 9 - shift, body_bottom + 1], fill=body_color)

    # Tail curling up on the left.
    d.line([(cx - 11, body_bottom - 4), (cx - 14, body_bottom - 9),
            (cx - 12, body_bottom - 13)], fill=body_color, width=3)

    # Face.
    eye_y = top + 9
    if eyes == "open":
        d.ellipse([cx - 6, eye_y, cx - 3, eye_y + 4], fill=(30, 30, 40))
        d.ellipse([cx + 3, eye_y, cx + 6, eye_y + 4], fill=(30, 30, 40))
        # little shine
        d.point((cx - 5, eye_y + 1), fill=(255, 255, 255))
        d.point((cx + 4, eye_y + 1), fill=(255, 255, 255))
    elif eyes == "blink":
        d.line([(cx - 6, eye_y + 2), (cx - 3, eye_y + 2)], fill=(30, 30, 40))
        d.line([(cx + 3, eye_y + 2), (cx + 6, eye_y + 2)], fill=(30, 30, 40))
    else:  # closed / sleeping -- gentle downward curve
        d.arc([cx - 6, eye_y - 1, cx - 2, eye_y + 3], 20, 160, fill=(30, 30, 40))
        d.arc([cx + 2, eye_y - 1, cx + 6, eye_y + 3], 20, 160, fill=(30, 30, 40))

    # Nose + mouth.
    d.point((cx, eye_y + 4), fill=accent)
    d.line([(cx, eye_y + 5), (cx - 2, eye_y + 6)], fill=(120, 80, 80))
    d.line([(cx, eye_y + 5), (cx + 2, eye_y + 6)], fill=(120, 80, 80))
    return img


def _draw_zzz(img: Image.Image, step: int):
    """Overlay a small floating 'Z' that rises and fades for sleep frames."""
    d = ImageDraw.Draw(img)
    x = 22
    y = 8 - step          # rises over time
    fade = 255 - step * 40
    col = (90, 90, 160, max(60, fade))
    size = 3 + step
    d.line([(x, y), (x + size, y)], fill=col)
    d.line([(x + size, y), (x, y + size)], fill=col)
    d.line([(x, y + size), (x + size, y + size)], fill=col)


def build_cat():
    body = (244, 164, 96)      # warm sandy orange
    accent = (255, 182, 193)   # pink
    name = "cat"
    folder = os.path.join(ROOT, name)

    idle = [
        _cat_base(0, 0, "open", body, accent),
        _cat_base(-1, 0, "open", body, accent),
        _cat_base(0, 0, "blink", body, accent),
        _cat_base(-1, 0, "open", body, accent),
    ]
    walk = [
        _cat_base(0, 0, "open", body, accent),
        _cat_base(-1, 1, "open", body, accent),
        _cat_base(0, 0, "open", body, accent),
        _cat_base(-1, 1, "open", body, accent),
    ]
    sleep = []
    for i in range(4):
        f = _cat_base(0, 0, "closed", body, accent)
        _draw_zzz(f, i)
        sleep.append(f)
    fall = [_cat_base(-1, 1, "open", body, accent)]

    _save(idle, os.path.join(folder, "idle"))
    _save(walk, os.path.join(folder, "walk"))
    _save(sleep, os.path.join(folder, "sleep"))
    _save(fall, os.path.join(folder, "fall"))
    _write_config(folder, "Cat", {"idle": 6, "walk": 10, "sleep": 3, "fall": 8},
                  personality="A lazy, sassy, secretly-affectionate house cat.",
                  messages=MESSAGES["cat"])


# --------------------------------------------------------------------------- #
# Slime -- a squishy green blob that squashes and stretches
# --------------------------------------------------------------------------- #
def _slime_base(squash: float, eyes: str, color):
    img = _new_frame()
    d = ImageDraw.Draw(img)
    cx = SIZE // 2
    base = 28
    # squash: <1 wider & flatter, >1 taller & narrower
    width = int(11 / squash)
    height = int(15 * squash)
    top = base - height
    d.pieslice([cx - width, top, cx + width, base + height // 2], 180, 360, fill=color)
    d.rectangle([cx - width, base - 2, cx + width, base], fill=color)

    # Glossy highlight.
    d.ellipse([cx - width + 3, top + 3, cx - width + 8, top + 9], fill=(255, 255, 255, 110))

    eye_y = top + height // 2 + 1
    if eyes == "open":
        d.ellipse([cx - 5, eye_y, cx - 2, eye_y + 4], fill=(30, 50, 30))
        d.ellipse([cx + 2, eye_y, cx + 5, eye_y + 4], fill=(30, 50, 30))
        d.point((cx - 4, eye_y + 1), fill=(255, 255, 255))
        d.point((cx + 3, eye_y + 1), fill=(255, 255, 255))
    elif eyes == "blink":
        d.line([(cx - 5, eye_y + 2), (cx - 2, eye_y + 2)], fill=(30, 50, 30))
        d.line([(cx + 2, eye_y + 2), (cx + 5, eye_y + 2)], fill=(30, 50, 30))
    else:
        d.arc([cx - 5, eye_y - 1, cx - 1, eye_y + 3], 20, 160, fill=(30, 50, 30))
        d.arc([cx + 1, eye_y - 1, cx + 5, eye_y + 3], 20, 160, fill=(30, 50, 30))
    # smile
    d.arc([cx - 3, eye_y + 3, cx + 3, eye_y + 8], 20, 160, fill=(30, 50, 30))
    return img


def build_slime():
    color = (120, 220, 150)
    name = "slime"
    folder = os.path.join(ROOT, name)

    idle = [
        _slime_base(1.0, "open", color),
        _slime_base(0.95, "open", color),
        _slime_base(1.0, "blink", color),
        _slime_base(0.95, "open", color),
    ]
    # Walk = a hop: squash, launch, stretch, land.
    walk = [
        _slime_base(0.8, "open", color),
        _slime_base(1.15, "open", color),
        _slime_base(1.0, "open", color),
        _slime_base(0.9, "open", color),
    ]
    sleep = []
    for i in range(4):
        f = _slime_base(0.7, "closed", color)  # flattened puddle
        _draw_zzz(f, i)
        sleep.append(f)
    fall = [_slime_base(1.2, "open", color)]

    _save(idle, os.path.join(folder, "idle"))
    _save(walk, os.path.join(folder, "walk"))
    _save(sleep, os.path.join(folder, "sleep"))
    _save(fall, os.path.join(folder, "fall"))
    _write_config(folder, "Slime", {"idle": 5, "walk": 9, "sleep": 3, "fall": 8},
                  personality="A bubbly, wholesome, endlessly encouraging blob.",
                  messages=MESSAGES["slime"])


# --------------------------------------------------------------------------- #
# Ghost -- a floating sheet ghost with a wavy hem
# --------------------------------------------------------------------------- #
def _ghost_base(bob: int, wave: int, eyes: str):
    img = _new_frame()
    d = ImageDraw.Draw(img)
    cx = SIZE // 2
    top = 5 + bob
    bottom = 25 + bob
    color = (240, 240, 255, 235)

    # Rounded head + rectangular body.
    d.pieslice([cx - 9, top, cx + 9, top + 18], 180, 360, fill=color)
    d.rectangle([cx - 9, top + 9, cx + 9, bottom], fill=color)

    # Wavy hem made of three little arcs; phase shifts to ripple.
    for i, bx in enumerate((-9, -3, 3)):
        up = (i + wave) % 2 == 0
        if up:
            d.pieslice([cx + bx, bottom - 3, cx + bx + 6, bottom + 3], 0, 180, fill=color)
        else:
            d.pieslice([cx + bx, bottom - 3, cx + bx + 6, bottom + 3], 180, 360, fill=(0, 0, 0, 0))
            d.rectangle([cx + bx, bottom - 3, cx + bx + 6, bottom], fill=color)

    eye_y = top + 7
    if eyes == "open":
        d.ellipse([cx - 5, eye_y, cx - 2, eye_y + 4], fill=(60, 60, 90))
        d.ellipse([cx + 2, eye_y, cx + 5, eye_y + 4], fill=(60, 60, 90))
    elif eyes == "blink":
        d.line([(cx - 5, eye_y + 2), (cx - 2, eye_y + 2)], fill=(60, 60, 90))
        d.line([(cx + 2, eye_y + 2), (cx + 5, eye_y + 2)], fill=(60, 60, 90))
    else:
        d.arc([cx - 5, eye_y - 1, cx - 1, eye_y + 3], 20, 160, fill=(60, 60, 90))
        d.arc([cx + 1, eye_y - 1, cx + 5, eye_y + 3], 20, 160, fill=(60, 60, 90))
    # tiny mouth
    d.ellipse([cx - 1, eye_y + 5, cx + 1, eye_y + 8], fill=(60, 60, 90))
    return img


def build_ghost():
    name = "ghost"
    folder = os.path.join(ROOT, name)

    idle = [
        _ghost_base(0, 0, "open"),
        _ghost_base(-1, 1, "open"),
        _ghost_base(0, 0, "blink"),
        _ghost_base(-1, 1, "open"),
    ]
    walk = [
        _ghost_base(0, 0, "open"),
        _ghost_base(-2, 1, "open"),
        _ghost_base(0, 0, "open"),
        _ghost_base(-2, 1, "open"),
    ]
    sleep = []
    for i in range(4):
        f = _ghost_base(0, i % 2, "closed")
        _draw_zzz(f, i)
        sleep.append(f)
    fall = [_ghost_base(0, 0, "open")]

    _save(idle, os.path.join(folder, "idle"))
    _save(walk, os.path.join(folder, "walk"))
    _save(sleep, os.path.join(folder, "sleep"))
    _save(fall, os.path.join(folder, "fall"))
    _write_config(folder, "Ghost", {"idle": 6, "walk": 8, "sleep": 3, "fall": 8},
                  personality="A spooky-but-caring, gently melancholic spirit.",
                  messages=MESSAGES["ghost"])


# --------------------------------------------------------------------------- #
# Chibi humanoids (original fan-art style: a spiky-haired ninja and a
# straw-hat pirate).  These are simple, original pixel drawings inspired by
# popular characters -- not copies of any official sprite art.
# --------------------------------------------------------------------------- #
def _chibi_base(bob, leg_phase, eyes, *, skin, hair_color, outfit,
                hair="spiky", headband=False, strawhat=False,
                whiskers=False, scar=False):
    img = _new_frame()
    d = ImageDraw.Draw(img)
    cx = SIZE // 2
    head_top = 3 + bob

    # Legs (drawn first, behind the body); the pair alternates for walking.
    leg_y = 26
    off = 1 if leg_phase else 0
    d.rectangle([cx - 4, leg_y - off, cx - 1, 30 - off], fill=(60, 60, 90))
    d.rectangle([cx + 1, leg_y + off, cx + 4, 30 + off], fill=(60, 60, 90))

    # Body / torso.
    d.rounded_rectangle([cx - 6, 17 + bob, cx + 6, 27 + bob], radius=3, fill=outfit)
    # Arms.
    d.rectangle([cx - 8, 18 + bob, cx - 6, 24 + bob], fill=outfit)
    d.rectangle([cx + 6, 18 + bob, cx + 8, 24 + bob], fill=outfit)
    d.ellipse([cx - 9, 23 + bob, cx - 6, 26 + bob], fill=skin)  # hands
    d.ellipse([cx + 6, 23 + bob, cx + 9, 26 + bob], fill=skin)

    # Head.
    d.ellipse([cx - 8, head_top, cx + 8, head_top + 16], fill=skin)

    # Hair.
    if hair == "spiky":
        # Rounded hair cap over the top of the head...
        d.pieslice([cx - 8, head_top - 2, cx + 8, head_top + 12], 180, 360, fill=hair_color)
        # ...topped with spikes of alternating height so it reads as hair.
        for j, hx in enumerate(range(-8, 9, 3)):
            peak = 6 if j % 2 == 0 else 4
            d.polygon([(cx + hx - 1, head_top + 2), (cx + hx + 1, head_top - peak),
                       (cx + hx + 3, head_top + 2)], fill=hair_color)
    elif hair == "short":
        d.pieslice([cx - 8, head_top - 1, cx + 8, head_top + 14], 180, 360, fill=hair_color)

    # Head accessories.
    if headband:
        d.rectangle([cx - 8, head_top + 4, cx + 8, head_top + 7], fill=(40, 70, 150))
        d.rectangle([cx - 3, head_top + 4, cx + 3, head_top + 7], fill=(170, 175, 185))  # plate
        d.line([(cx - 2, head_top + 5), (cx + 2, head_top + 6)], fill=(90, 95, 110))
    if strawhat:
        d.ellipse([cx - 11, head_top + 2, cx + 11, head_top + 8], fill=(225, 195, 120))  # brim
        d.pieslice([cx - 7, head_top - 4, cx + 7, head_top + 8], 180, 360, fill=(232, 205, 135))  # crown
        d.rectangle([cx - 7, head_top + 1, cx + 7, head_top + 3], fill=(200, 60, 60))  # red band

    # Face.
    eye_y = head_top + 9
    if eyes == "open":
        d.ellipse([cx - 5, eye_y, cx - 2, eye_y + 4], fill=(40, 40, 60))
        d.ellipse([cx + 2, eye_y, cx + 5, eye_y + 4], fill=(40, 40, 60))
        d.point((cx - 4, eye_y + 1), fill=(255, 255, 255))
        d.point((cx + 3, eye_y + 1), fill=(255, 255, 255))
    elif eyes == "blink":
        d.line([(cx - 5, eye_y + 2), (cx - 2, eye_y + 2)], fill=(40, 40, 60))
        d.line([(cx + 2, eye_y + 2), (cx + 5, eye_y + 2)], fill=(40, 40, 60))
    else:
        d.arc([cx - 5, eye_y - 1, cx - 1, eye_y + 3], 20, 160, fill=(40, 40, 60))
        d.arc([cx + 1, eye_y - 1, cx + 5, eye_y + 3], 20, 160, fill=(40, 40, 60))

    # Big happy grin.
    d.arc([cx - 3, eye_y + 3, cx + 3, eye_y + 8], 20, 160, fill=(120, 60, 60))

    if whiskers:  # three little marks on each cheek
        for wy in (eye_y + 1, eye_y + 3, eye_y + 5):
            d.line([(cx - 7, wy), (cx - 5, wy)], fill=(150, 110, 90))
            d.line([(cx + 5, wy), (cx + 7, wy)], fill=(150, 110, 90))
    if scar:  # little stitched scar under the left eye
        d.line([(cx - 4, eye_y + 5), (cx - 3, eye_y + 7)], fill=(150, 70, 70))
        d.line([(cx - 5, eye_y + 6), (cx - 2, eye_y + 6)], fill=(150, 70, 70))
    return img


def build_naruto():
    name = "naruto"
    folder = os.path.join(ROOT, name)
    P = dict(skin=(255, 220, 177), hair_color=(245, 205, 70), outfit=(240, 140, 30),
             hair="spiky", headband=True, whiskers=True)

    idle = [_chibi_base(0, 0, "open", **P), _chibi_base(-1, 0, "open", **P),
            _chibi_base(0, 0, "blink", **P), _chibi_base(-1, 0, "open", **P)]
    walk = [_chibi_base(0, 0, "open", **P), _chibi_base(-1, 1, "open", **P),
            _chibi_base(0, 0, "open", **P), _chibi_base(-1, 1, "open", **P)]
    sleep = []
    for i in range(4):
        f = _chibi_base(0, 0, "closed", **P)
        _draw_zzz(f, i)
        sleep.append(f)
    fall = [_chibi_base(-1, 1, "open", **P)]

    _save(idle, os.path.join(folder, "idle"))
    _save(walk, os.path.join(folder, "walk"))
    _save(sleep, os.path.join(folder, "sleep"))
    _save(fall, os.path.join(folder, "fall"))
    _write_config(folder, "Naruto", {"idle": 6, "walk": 10, "sleep": 3, "fall": 8},
                  personality="An energetic, never-give-up ninja-in-training.",
                  messages=MESSAGES["naruto"])


def build_luffy():
    name = "luffy"
    folder = os.path.join(ROOT, name)
    P = dict(skin=(255, 220, 177), hair_color=(35, 35, 45), outfit=(210, 60, 50),
             hair="short", strawhat=True, scar=True)

    idle = [_chibi_base(0, 0, "open", **P), _chibi_base(-1, 0, "open", **P),
            _chibi_base(0, 0, "blink", **P), _chibi_base(-1, 0, "open", **P)]
    walk = [_chibi_base(0, 0, "open", **P), _chibi_base(-1, 1, "open", **P),
            _chibi_base(0, 0, "open", **P), _chibi_base(-1, 1, "open", **P)]
    sleep = []
    for i in range(4):
        f = _chibi_base(0, 0, "closed", **P)
        _draw_zzz(f, i)
        sleep.append(f)
    fall = [_chibi_base(-1, 1, "open", **P)]

    _save(idle, os.path.join(folder, "idle"))
    _save(walk, os.path.join(folder, "walk"))
    _save(sleep, os.path.join(folder, "sleep"))
    _save(fall, os.path.join(folder, "fall"))
    _write_config(folder, "Luffy", {"idle": 6, "walk": 10, "sleep": 3, "fall": 8},
                  personality="A cheerful, adventure-loving, meat-obsessed pirate captain.",
                  messages=MESSAGES["luffy"])


# --------------------------------------------------------------------------- #
# Per-character configuration file
# --------------------------------------------------------------------------- #
def _write_config(folder: str, display_name: str, fps: dict,
                  personality: str = "", messages: dict | None = None):
    """Write a config.json describing animation speeds, behaviour and chatter."""
    cfg = {
        "name": display_name,
        # A one-line description of the character's vibe (shown nowhere, but
        # handy documentation for whoever edits the messages below).
        "personality": personality,
        # Frames-per-second for each animation state.
        "fps": fps,
        # Base on-screen scale multiplier (user can still override globally).
        "scale": 2.5,
        # Walking speed in pixels per second (before the global speed factor).
        "walk_speed": 38,
        # Probability weights used when picking the next idle behaviour.
        "behavior": {
            "idle_min": 2.0,     # seconds to stay idle (minimum)
            "idle_max": 6.0,     # seconds to stay idle (maximum)
            "walk_chance": 0.55,
            "sleep_chance": 0.2,
        },
        # Personality-driven speech-bubble lines, grouped by mood. "idle" lines
        # are the random chatter; the rest are shown when the matching emotion
        # is triggered (pet it = happy, shake it = angry, drop it hard = sad).
        "messages": messages or {},
        # Optional sound effects, mapped to .wav files in the "sounds" folder.
        # The bundled effects are created by tools/generate_sounds.py. Leave
        # this empty ({}) for a silent pet, or point at your own .wav files.
        "sounds": {
            "walk": "walk.wav",
            "land": "land.wav",
            "grab": "grab.wav",
            "sleep": "sleep.wav",
        },
    }
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "config.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


# Personality-driven chatter for each bundled character.
MESSAGES = {
    "cat": {
        "idle": ["Feed me, human.", "Drink some water. 💧", "Five more minutes...",
                 "Pet me. Now.", "Is it nap o'clock yet?", "Stretch those legs!",
                 "I knocked something off your desk. You're welcome."],
        "happy": ["Purrr~", "Okay, you may pet me.", "Hehe, that tickles!", "Fine... I like you."],
        "angry": ["Hey! Put me down!", "Hiss! Stop shaking me!", "Rude!", "I'll remember this."],
        "sad": ["Ow... my tail.", "That was a long fall...", "Be gentle, please.", "Mrrp... ouch."],
        "surprised": ["Wha—?!", "Hey!", "Mrow?!"],
        "sleepy": ["Zzz... fish...", "Nap time. Shhh.", "Do not disturb."],
    },
    "slime": {
        "idle": ["Stay hydrated! 💧", "You're doing amazing!", "Don't forget to stretch~",
                 "Squish squish!", "Take a deep breath.", "Posture check! Sit up straight.",
                 "Remember to blink and rest your eyes!"],
        "happy": ["Boing!", "Yay! Friends!", "Squishy hugs!", "Wheee!"],
        "angry": ["H-hey! Too wobbly!", "Stop the shaking!", "I'm getting dizzy!", "Meanie!"],
        "sad": ["Splat...", "That squished me flat.", "Gentle, please...", "Aww..."],
        "surprised": ["Whee?!", "Up we go!", "Eep!"],
        "sleepy": ["Zzz... bouncy dreams...", "Melting into a nap~", "So sleepy..."],
    },
    "ghost": {
        "idle": ["Boo... drink water. 💧", "I watch over you.", "Don't stay up too late...",
                 "It's cold here...", "Rest your eyes a moment.", "Take a little break~",
                 "I'm always here if you're lonely."],
        "happy": ["Hehe, you found me!", "Spooky-happy!", "You're not scared? Yay!", "Floaty and glad~"],
        "angry": ["Booo! Stop that!", "You disturb my haunting!", "Grr... spooky rage!",
                  "Unhand me, mortal!"],
        "sad": ["Wooo... that hurt.", "So lonely down here...", "Boo-hoo...", "Gentle with spirits..."],
        "surprised": ["Boo?!", "Eep!", "A draft?!"],
        "sleepy": ["Zzz... haunting in my sleep...", "Drifting off~", "Spooky slumber..."],
    },
    "naruto": {
        "idle": ["Believe it!", "Gonna be Hokage someday!", "Ramen time! 🍜",
                 "Train hard, hydrate harder! 💧", "Never give up — but take breaks!",
                 "Dattebayo!", "Stretch, then back to training!"],
        "happy": ["Yatta!", "Hehe, that's my friend!", "Believe it!", "You're awesome, ya know!"],
        "angry": ["Hey! Knock it off!", "Grr, not cool!", "Put me down, dattebayo!",
                  "You wanna fight?!"],
        "sad": ["Ow... that hurt.", "I won't cry... okay, maybe a little.",
                "Be nice, will ya?", "That was a rough one..."],
        "surprised": ["Huh?!", "Whoa!", "Dattebayo?!"],
        "sleepy": ["Zzz... ramen dreams...", "Even ninjas nap.", "So sleepy..."],
    },
    "luffy": {
        "idle": ["I'm gonna be King of the Pirates!", "MEAT! 🍖", "Adventure time!",
                 "Eat well, stay strong! 💪", "Shishishi!", "Let's find some treasure!",
                 "Don't forget to drink water!"],
        "happy": ["Shishishi!", "You're my nakama now!", "That was fun!", "I like you!"],
        "angry": ["Hey! Cut it out!", "Don't shake the captain!", "Grrr!", "That's not nice!"],
        "sad": ["Owww...", "That really hurt...", "No fair...", "I miss my crew..."],
        "surprised": ["Whoa?!", "Huh?!", "Eh?!"],
        "sleepy": ["Zzz... mountains of meat...", "Nap before adventure.", "So full... so sleepy..."],
    },
}


def main():
    build_cat()
    build_slime()
    build_ghost()
    build_naruto()
    build_luffy()
    print(f"Generated characters in: {ROOT}")


if __name__ == "__main__":
    main()
