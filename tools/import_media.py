"""
import_media.py
================
Helper for adding your *own* characters (e.g. an anime character, a lofi-style
sprite, a game mascot) without any image editing.

It turns an animated **GIF** or a grid **sprite sheet** into the numbered
``frame_XX.png`` files the pet expects, and creates a starter ``config.json``
you can then edit (messages, personality, speeds, sounds).

Examples
--------
From a GIF (each GIF = one animation state)::

    python tools/import_media.py --name luffy --state walk --gif walk.gif
    python tools/import_media.py --name luffy --state idle --gif idle.gif

From a horizontal sprite sheet of 4 frames::

    python tools/import_media.py --name naruto --state walk --sheet run.png --cols 4

From a grid sheet, specifying the cell size and keying out a white background::

    python tools/import_media.py --name naruto --state idle --sheet sheet.png \
        --fw 64 --fh 64 --bg "#ffffff" --tolerance 30

After importing your states (at least ``idle``), run the pet and pick your new
character from the right-click menu. Tweak ``characters/<name>/config.json`` to
give it personality lines, sizes and sounds.
"""

from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageSequence

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "characters"))


def _key_out_background(img: Image.Image, hexcolor: str, tol: int) -> Image.Image:
    """Make pixels close to *hexcolor* fully transparent (for sheets w/o alpha)."""
    hexcolor = hexcolor.lstrip("#")
    tr, tg, tb = (int(hexcolor[i:i + 2], 16) for i in (0, 2, 4))
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if abs(r - tr) <= tol and abs(g - tg) <= tol and abs(b - tb) <= tol:
                px[x, y] = (r, g, b, 0)
    return img


def _frames_from_gif(path: str) -> list[Image.Image]:
    im = Image.open(path)
    frames = []
    for frame in ImageSequence.Iterator(im):
        frames.append(frame.convert("RGBA"))
    return frames


def _frames_from_sheet(path: str, cols: int, rows: int,
                       fw: int, fh: int) -> list[Image.Image]:
    sheet = Image.open(path).convert("RGBA")
    sw, sh = sheet.size
    # Derive missing grid info from whatever the user supplied.
    if fw and fh:
        cols = cols or sw // fw
        rows = rows or sh // fh
    else:
        cols = cols or 1
        rows = rows or 1
        fw = sw // cols
        fh = sh // rows
    frames = []
    for r in range(rows):
        for c in range(cols):
            box = (c * fw, r * fh, c * fw + fw, r * fh + fh)
            frames.append(sheet.crop(box))
    return frames


def _autocrop(img: Image.Image) -> Image.Image:
    """Trim fully transparent borders so the pet sits flush on the taskbar."""
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def _ensure_config(folder: str, name: str, state: str, fps: int) -> None:
    cfg_path = os.path.join(folder, "config.json")
    if os.path.isfile(cfg_path):
        with open(cfg_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    else:
        cfg = {
            "name": name.title(),
            "personality": "Describe your character here.",
            "fps": {"idle": 6, "walk": 8, "sleep": 3, "fall": 8},
            "scale": 2.5,
            "walk_speed": 38,
            "behavior": {"idle_min": 2.0, "idle_max": 6.0,
                         "walk_chance": 0.55, "sleep_chance": 0.2},
            "messages": {
                "idle": ["Hello!", "Drink some water. 💧"],
                "happy": ["Yay!"], "angry": ["Hey!"],
                "sad": ["Ouch..."], "surprised": ["!"], "sleepy": ["Zzz..."],
            },
            "sounds": {},
        }
    cfg.setdefault("fps", {})[state] = fps
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)


def main():
    ap = argparse.ArgumentParser(description="Import a GIF or sprite sheet as a pet animation.")
    ap.add_argument("--name", required=True, help="character folder name, e.g. luffy")
    ap.add_argument("--state", required=True,
                    choices=["idle", "walk", "sleep", "fall"], help="animation state")
    ap.add_argument("--gif", help="path to an animated GIF")
    ap.add_argument("--sheet", help="path to a sprite-sheet image")
    ap.add_argument("--cols", type=int, default=0, help="sheet: number of columns")
    ap.add_argument("--rows", type=int, default=0, help="sheet: number of rows")
    ap.add_argument("--fw", type=int, default=0, help="sheet: frame width in px")
    ap.add_argument("--fh", type=int, default=0, help="sheet: frame height in px")
    ap.add_argument("--bg", help="background color to make transparent, e.g. #ffffff")
    ap.add_argument("--tolerance", type=int, default=20, help="color match tolerance for --bg")
    ap.add_argument("--fps", type=int, default=8, help="playback fps for this state")
    ap.add_argument("--no-crop", action="store_true", help="do not auto-trim transparent borders")
    args = ap.parse_args()

    if not args.gif and not args.sheet:
        ap.error("provide either --gif or --sheet")

    if args.gif:
        frames = _frames_from_gif(args.gif)
    else:
        frames = _frames_from_sheet(args.sheet, args.cols, args.rows, args.fw, args.fh)

    if args.bg:
        frames = [_key_out_background(f, args.bg, args.tolerance) for f in frames]
    if not args.no_crop:
        frames = [_autocrop(f) for f in frames]

    out_dir = os.path.join(ROOT, args.name, args.state)
    os.makedirs(out_dir, exist_ok=True)
    # Clear any previous frames for this state.
    for old in os.listdir(out_dir):
        if old.startswith("frame_") and old.endswith(".png"):
            os.remove(os.path.join(out_dir, old))
    for i, frame in enumerate(frames):
        frame.save(os.path.join(out_dir, f"frame_{i:02d}.png"))

    _ensure_config(os.path.join(ROOT, args.name), args.name, args.state, args.fps)
    print(f"Imported {len(frames)} frames -> {out_dir}")
    print(f"Edit characters/{args.name}/config.json to give it personality & sounds.")


if __name__ == "__main__":
    main()
