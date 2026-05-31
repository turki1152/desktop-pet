"""
generate_emotes.py
===================
Draws the small "emote" icons that pop up in the speech bubble to show the
pet's mood (happy, angry, sad, surprised) plus a couple of extras (music note
for sleepy chatter, bell for reminders).

These are shared by every character, so a brand-new character automatically
gets emotion support without shipping any extra art.

Run once::

    python tools/generate_emotes.py
"""

from __future__ import annotations

import os

from PIL import Image, ImageDraw

S = 16  # icon canvas size in pixels (displayed larger via nearest-neighbour)
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "assets", "emotes"))


def _canvas():
    return Image.new("RGBA", (S, S), (0, 0, 0, 0))


def heart(color):
    img = _canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([2, 3, 8, 9], fill=color)
    d.ellipse([7, 3, 13, 9], fill=color)
    d.polygon([(2, 7), (13, 7), (8, 14)], fill=color)
    # tiny highlight
    d.point((4, 5), fill=(255, 255, 255, 200))
    return img


def teardrop(color):
    img = _canvas()
    d = ImageDraw.Draw(img)
    d.polygon([(8, 1), (3, 9), (13, 9)], fill=color)
    d.ellipse([3, 6, 13, 15], fill=color)
    d.ellipse([5, 9, 8, 12], fill=(255, 255, 255, 150))  # shine
    return img


def exclamation(color):
    img = _canvas()
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 1, 10, 10], radius=2, fill=color)
    d.ellipse([6, 12, 10, 16], fill=color)
    return img


def anger(color):
    """The classic manga 'popping vein' impact star."""
    img = _canvas()
    d = ImageDraw.Draw(img)
    c = 8
    for a, b in [((c, 1), (c, 15)), ((1, c), (15, c)),
                 ((3, 3), (13, 13)), ((13, 3), (3, 13))]:
        d.line([a, b], fill=color, width=2)
    d.ellipse([5, 5, 11, 11], fill=color)
    return img


def note(color):
    img = _canvas()
    d = ImageDraw.Draw(img)
    d.ellipse([3, 10, 8, 15], fill=color)        # note head
    d.rectangle([7, 3, 9, 13], fill=color)       # stem
    d.polygon([(9, 3), (13, 5), (9, 7)], fill=color)  # flag
    return img


def bell(color):
    img = _canvas()
    d = ImageDraw.Draw(img)
    d.pieslice([3, 2, 13, 13], 180, 360, fill=color)  # dome
    d.rectangle([3, 8, 13, 12], fill=color)
    d.rectangle([2, 12, 14, 13], fill=color)          # rim
    d.ellipse([6, 13, 10, 16], fill=color)            # clapper
    return img


def main():
    os.makedirs(OUT, exist_ok=True)
    icons = {
        "happy": heart((255, 120, 160)),       # pink heart
        "love": heart((230, 60, 80)),          # red heart
        "angry": anger((230, 60, 60)),         # red impact star
        "sad": teardrop((90, 160, 230)),       # blue tear
        "surprised": exclamation((255, 200, 60)),  # yellow !
        "music": note((130, 200, 180)),        # teal note
        "bell": bell((255, 200, 70)),          # reminder bell
    }
    for name, img in icons.items():
        img.save(os.path.join(OUT, f"{name}.png"))
    print(f"Generated {len(icons)} emotes in: {OUT}")


if __name__ == "__main__":
    main()
