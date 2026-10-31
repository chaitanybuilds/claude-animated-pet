"""
Generates animated transparent-PNG sprite sheets for claude-animated-pet,
in the pixel-block style of the reference images (blocky body, notch ears,
two legs, slanted >< eyes option + round eye option).
Outputs frame PNGs into assets/frames/<state>/0000.png ...
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), "assets", "frames")
os.makedirs(OUT, exist_ok=True)

BODY = (224, 108, 74, 255)      # orange from reference
BODY_DARK = (196, 88, 58, 255)  # shade for outline/feet shadow
WHITE = (255, 255, 255, 255)
BLACK = (20, 20, 20, 255)

CANVAS = 160  # px canvas, body drawn in a blocky grid, scaled up
GRID = 16     # logical grid cells across canvas
CELL = CANVAS // GRID  # 10px per cell


def new_canvas():
    return Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))


def rect(draw, x0, y0, x1, y1, color):
    """Draw a filled rect using grid cell coords (inclusive)."""
    draw.rectangle(
        [x0 * CELL, y0 * CELL, (x1 + 1) * CELL - 1, (y1 + 1) * CELL - 1],
        fill=color,
    )


def draw_body(draw, squash=0, lean=0, bob=0):
    """
    Blocky pet body: wide head/body block, two ear notches on sides,
    two legs below. squash flattens height and widens; bob shifts y;
    lean shifts x of the whole body slightly (for walk/drag wobble).
    """
    top = 3 + bob + squash
    bot = 11 + bob
    left = 3 - squash // 2 + lean
    right = 12 + squash // 2 + lean

    # main torso block
    rect(draw, left + 1, top, right - 1, bot - 2, BODY)
    # ear/handle notches sticking out the sides (mid-height band)
    mid_top = top + 3
    mid_bot = top + 4
    rect(draw, left - 1, mid_top, left, mid_bot, BODY)
    rect(draw, right, mid_top, right + 1, mid_bot, BODY)
    # legs
    leg_y0 = bot - 1
    leg_y1 = bot + 1
    rect(draw, left + 2, leg_y0, left + 3, leg_y1, BODY)
    rect(draw, right - 3, leg_y0, right - 2, leg_y1, BODY)

    return left, top, right, bot


def draw_eyes_round(draw, left, top, right, bot, blink=False, happy=False, look=0):
    """White-background round refined eyes with black pupils (non-creepy)."""
    cy = top + 2
    ex_l = left + 3 + look
    ex_r = right - 4 + look
    if blink:
        # closed eyes = thin horizontal dark lines
        draw.rectangle([ex_l * CELL, (cy * CELL) + CELL // 2 - 1,
                         (ex_l + 1) * CELL, (cy * CELL) + CELL // 2 + 1], fill=BLACK)
        draw.rectangle([ex_r * CELL, (cy * CELL) + CELL // 2 - 1,
                         (ex_r + 1) * CELL, (cy * CELL) + CELL // 2 + 1], fill=BLACK)
        return
    for ex in (ex_l, ex_r):
        rect(draw, ex, cy, ex, cy + 1, WHITE)
        if happy:
            # curved happy eye -> small black arc at bottom only
            draw.rectangle([ex * CELL, (cy + 1) * CELL - 2, (ex + 1) * CELL, (cy + 1) * CELL],
                            fill=BLACK)
        else:
            draw.rectangle([ex * CELL + 1, cy * CELL + 2, ex * CELL + CELL - 1, (cy + 1) * CELL - 1],
                            fill=BLACK)


def frame(state, idx, builder):
    img = new_canvas()
    d = ImageDraw.Draw(img)
    builder(d)
    folder = os.path.join(OUT, state)
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, f"{idx:04d}.png"))


# ---- IDLE (gentle breathing bob, blink occasionally) ----
idle_frames = []
for i in range(24):
    bob = round(1 * abs(((i % 12) - 6) / 6))  # 0..1 bob
    blink = (i == 10 or i == 11)
    def b(d, bob=bob, blink=blink):
        l, t, r, bt = draw_body(d, bob=bob)
        draw_eyes_round(d, l, t, r, bt, blink=blink)
    frame("idle", i, b)

# ---- VIBE (music bob, happy eyes, side sway) ----
for i in range(20):
    import math
    phase = i / 20 * 2 * math.pi
    bob = round(1 + math.sin(phase) * 1)
    lean = round(math.sin(phase) * 1)
    def b(d, bob=bob, lean=lean):
        l, t, r, bt = draw_body(d, bob=bob, lean=lean)
        draw_eyes_round(d, l, t, r, bt, happy=True, look=lean)
    frame("vibe", i, b)

# ---- CURIOUS / TALK (used while bubble shown, slight head tilt via lean) ----
for i in range(10):
    lean = 1 if i % 4 < 2 else 0
    def b(d, lean=lean):
        l, t, r, bt = draw_body(d, lean=lean)
        draw_eyes_round(d, l, t, r, bt, look=lean)
    frame("talk", i, b)

# ---- DRAG (squashed/stretched, wide eyes excited) ----
for i in range(6):
    squash = 1
    def b(d, squash=squash):
        l, t, r, bt = draw_body(d, squash=squash, bob=-1)
        draw_eyes_round(d, l, t, r, bt, happy=(i % 2 == 0))
    frame("drag", i, b)

# ---- CLICK (squint / excited launch) ----
for i in range(8):
    def b(d, i=i):
        l, t, r, bt = draw_body(d, bob=-1 if i < 4 else 0)
        draw_eyes_round(d, l, t, r, bt, happy=True)
    frame("click", i, b)

# ---- SLEEP-ish unknown "what is this place" (confused, eyes look around) ----
for i in range(12):
    look = [-1, -1, 0, 1, 1, 0][i % 6]
    def b(d, look=look):
        l, t, r, bt = draw_body(d)
        draw_eyes_round(d, l, t, r, bt, look=look)
    frame("confused", i, b)

print("Sprite generation done.")
for s in ("idle", "vibe", "talk", "drag", "click", "confused"):
    n = len(os.listdir(os.path.join(OUT, s)))
    print(s, n, "frames")
