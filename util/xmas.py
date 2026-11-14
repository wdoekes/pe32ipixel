"""Kerstslinger met slingerende rode ballen en glitter, als naadloos loopende GIF voor 96x16.

Alles wat beweegt heeft een periode die het aantal frames deelt, zodat het
laatste frame naadloos overloopt in het eerste.
"""
import argparse
import math
import random

from PIL import Image, ImageDraw

from ledgif import H, W, pick_period, star, twinkle, write_gif

S = 4  # supersampling: slingerende ballen bewegen op subpixels
SPACING = 16
RADIUS = 3.4
SWING = 0.3  # rad
NEEDLES = [(0, 60, 15), (0, 90, 20), (10, 130, 30), (30, 170, 50)]
GLITTER = [(255, 215, 80), (255, 240, 200), (200, 230, 255)]

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('out')
parser.add_argument('--frames', type=int, default=120,
                    help='looplengte; kies iets met veel delers (120, 240, 360)')
parser.add_argument('--delay', type=int, default=50, help='ms per frame, veelvoud van 10')
parser.add_argument('--glitter', type=int, default=60, help='aantal glitterpunten')
parser.add_argument('--seed', type=int)
args = parser.parse_args()

rnd = random.Random(args.seed)


def period(lo, hi):
    return pick_period(rnd, args.frames, lo, hi)


def garland_y(x):
    """Hangt door tussen de haken; de ballen hangen op de laagste punten."""
    return 1.5 + 2.5 * math.sin(math.pi * (x % SPACING) / SPACING)


def make_garland():
    img = Image.new('RGBA', (W, H))
    for x in range(W):
        yc = round(garland_y(x))
        for y in range(yc - 1, yc + 2 + (rnd.random() < 0.4)):
            if rnd.random() < 0.9:
                img.putpixel((x, y), rnd.choice(NEEDLES) + (255,))
    return img


garland = make_garland()
balls = [(x, garland_y(x), RADIUS + rnd.choice((3, 5)), period(40, 80), rnd.uniform(0, 2 * math.pi))
         for x in range(SPACING // 2, W, SPACING)]
sparkles = [(rnd.randrange(W), rnd.randrange(H), rnd.choice(GLITTER),
             period(15, 60), rnd.randrange(args.frames), rnd.uniform(2, 4))
            for _ in range(args.glitter)]


def draw_ball(d, t, ax, ay, length, per, phase):
    theta = SWING * math.sin(2 * math.pi * t / per + phase)
    dx, dy = math.sin(theta), math.cos(theta)
    cx, cy = (ax + length * dx) * S, (ay + length * dy) * S
    r = RADIUS * S
    d.line((ax * S, ay * S, cx - r * dx, cy - r * dy), fill=(150, 120, 50), width=S // 2)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(110, 0, 10))
    hx, hy, hr = cx - 0.2 * r, cy - 0.2 * r, 0.75 * r
    d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(200, 10, 25))
    hx, hy, hr = cx - 0.4 * r, cy - 0.4 * r, 0.25 * r
    d.ellipse((hx - hr, hy - hr, hx + hr, hy + hr), fill=(255, 190, 190))
    capx, capy = cx - r * dx, cy - r * dy
    d.rectangle((capx - S, capy - S // 2, capx + S, capy + S // 2), fill=(220, 180, 60))


def frame(t):
    hi = Image.new('RGB', (W * S, H * S))
    d = ImageDraw.Draw(hi)
    for ball in balls:
        draw_ball(d, t, *ball)
    img = hi.resize((W, H), Image.Resampling.BOX)
    img.paste(garland, mask=garland)
    px = img.load()
    for x, y, color, per, phase, width in sparkles:
        star(px, x, y, color, twinkle(t, per, phase, width))
    return img.tobytes()


write_gif(map(frame, range(args.frames)), args.out, args.delay)
