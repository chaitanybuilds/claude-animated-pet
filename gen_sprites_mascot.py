"""
Builds claude-animated-pet's animation frames from the official-style Claude mascot
illustration pack (static PNGs) instead of the procedural blocky sprite.
Each state uses ONE source illustration, trimmed to its bounding box, then
animated purely via affine transforms (bob / sway / squash-stretch / rotate)
-- the same "treat the sprite as one rigid body" technique real pixel-art
mascot animations use, since the source art itself can't be redrawn frame
by frame.

Usage:
    python gen_sprites_mascot.py /path/to/mascot_pack/2x
"""
import os
import sys
import math
from PIL import Image

OUT = os.path.join(os.path.dirname(__file__), "assets", "frames")
WORK = 240          # internal working canvas (gives room for squash/rotate)
PAD_RATIO = 0.18     # padding around trimmed art as a fraction of its size

STATE_SOURCE = {
    "idle": "building-colorful-blocks@2x.png",
    "vibe": "happy-pixel-celebrating@2x.png",
    "talk": "examining-green-globe@2x.png",
    "confused": "confusion-spiral-pixel@2x.png",
    "drag": "fast-performance-trail@2x.png",
    "click": "rocket-launch-success@2x.png",
    "welcome": "welcome-pixel-banner@2x.png",
}


def load_trimmed(path):
    im = Image.open(path).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    w, h = im.size
    side = int(max(w, h) * (1 + PAD_RATIO * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(im, ((side - w) // 2, (side - h) // 2), im)
    canvas = canvas.resize((WORK, WORK), Image.LANCZOS)
    return canvas


def transform_frame(src, dx=0, dy=0, scale_x=1.0, scale_y=1.0, angle=0.0):
    """Apply scale about center, then rotate, then translate, onto a WORK canvas."""
    w, h = src.size
    sw, sh = max(1, int(w * scale_x)), max(1, int(h * scale_y))
    scaled = src.resize((sw, sh), Image.LANCZOS)
    if angle:
        scaled = scaled.rotate(angle, resample=Image.BICUBIC, expand=True)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ox = (w - scaled.width) // 2 + dx
    oy = (h - scaled.height) // 2 + dy
    out.paste(scaled, (ox, oy), scaled)
    return out


def save_sequence(state, frames):
    folder = os.path.join(OUT, state)
    os.makedirs(folder, exist_ok=True)
    # clear any old frames for this state first
    for f in os.listdir(folder):
        if f.endswith(".png"):
            os.remove(os.path.join(folder, f))
    for i, img in enumerate(frames):
        img.save(os.path.join(folder, f"{i:04d}.png"))
    print(f"{state}: {len(frames)} frames")


def build_idle(src):
    frames = []
    n = 24
    for i in range(n):
        t = i / n * 2 * math.pi
        bob = int(math.sin(t) * 4)
        sy = 1.0 + math.sin(t) * 0.015
        frames.append(transform_frame(src, dy=bob, scale_y=sy))
    return frames


def build_vibe(src):
    frames = []
    n = 20
    for i in range(n):
        t = i / n * 2 * math.pi
        bob = int(math.sin(t) * 9)
        lean = math.sin(t) * 8
        sx = 1.0 - abs(math.sin(t)) * 0.04
        sy = 1.0 + abs(math.sin(t)) * 0.06
        frames.append(transform_frame(src, dy=-abs(bob), angle=lean, scale_x=sx, scale_y=sy))
    return frames


def build_talk(src):
    frames = []
    n = 12
    for i in range(n):
        t = i / n * 2 * math.pi
        lean = math.sin(t) * 5
        bob = int(math.sin(t * 2) * 2)
        frames.append(transform_frame(src, dy=bob, angle=lean))
    return frames


def build_confused(src):
    frames = []
    n = 16
    for i in range(n):
        t = i / n * 2 * math.pi
        lean = math.sin(t) * 10
        bob = int(math.cos(t) * 3)
        frames.append(transform_frame(src, dy=bob, angle=lean))
    return frames


def build_drag(src):
    frames = []
    n = 8
    for i in range(n):
        t = i / n * 2 * math.pi
        sx = 1.08 + math.sin(t) * 0.05
        sy = 0.92 - math.sin(t) * 0.05
        lean = math.sin(t) * 6
        frames.append(transform_frame(src, scale_x=sx, scale_y=sy, angle=lean))
    return frames


def build_click(src):
    frames = []
    n = 10
    for i in range(n):
        # crouch down then launch upward with a stretch
        p = i / (n - 1)
        if p < 0.4:
            k = p / 0.4
            dy = int(k * 10)
            sy = 1.0 - k * 0.12
            sx = 1.0 + k * 0.08
        else:
            k = (p - 0.4) / 0.6
            dy = int(10 - k * 30)
            sy = 1.0 + k * 0.18
            sx = 1.0 - k * 0.06
        frames.append(transform_frame(src, dy=dy, scale_x=sx, scale_y=sy))
    return frames


def build_welcome(src):
    frames = []
    n = 14
    for i in range(n):
        p = i / (n - 1)
        # bounce-in: scale overshoot 0 -> 1.15 -> 1.0, then small idle bob loop tail
        if p < 0.6:
            k = p / 0.6
            s = 0.6 + k * 0.6  # 0.6 -> 1.2
        else:
            k = (p - 0.6) / 0.4
            s = 1.2 - k * 0.2  # 1.2 -> 1.0
        frames.append(transform_frame(src, scale_x=s, scale_y=s))
    return frames


BUILDERS = {
    "idle": build_idle,
    "vibe": build_vibe,
    "talk": build_talk,
    "confused": build_confused,
    "drag": build_drag,
    "click": build_click,
    "welcome": build_welcome,
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python gen_sprites_mascot.py /path/to/mascot_pack/2x")
        sys.exit(1)
    src_dir = sys.argv[1]
    for state, filename in STATE_SOURCE.items():
        path = os.path.join(src_dir, filename)
        if not os.path.exists(path):
            print(f"WARNING: missing {path}, skipping {state}")
            continue
        src = load_trimmed(path)
        frames = BUILDERS[state](src)
        save_sequence(state, frames)


if __name__ == "__main__":
    main()
