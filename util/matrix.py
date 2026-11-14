"""Matrix-code die van links naar rechts loopt, als naadloos loopende GIF voor 96x16.

Drie banen met 3x5-glyphs: cijfers (ook gespiegeld, zoals in de film) en
procedureel gegenereerde tekens. Elke stroom heeft een witte kop die steeds
van teken wisselt en een groene staart die uitdooft en af en toe wisselt.
Alle periodes delen het aantal frames, zodat de loop naadloos is.
"""
import argparse
import random

from PIL import Image

from ledgif import H, W, divisors, pick_period, write_gif

GW, GH = 3, 5
CELL = GW + 1
LANES = range(0, H - GH + 1, GH)  # y-offsets: 0, 5, 10
CELLS = W // CELL
HEAD = (220, 255, 220)

DIGITS = [
    '111101101101111', '010110010010111', '111001111100111', '111001111001111', '101101111001001',
    '111100111001111', '111100111101111', '111001010010010', '111101111101111', '111101111001111',
]

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('out')
parser.add_argument('--frames', type=int, default=120,
                    help='looplengte; kies iets met veel delers (120, 240, 360)')
parser.add_argument('--delay', type=int, default=50, help='ms per frame, veelvoud van 10')
parser.add_argument('--streams', type=int, default=2, help='stromen per baan')
parser.add_argument('--seed', type=int)
args = parser.parse_args()

rnd = random.Random(args.seed)
cycles = divisors(args.frames)


def bits(rows):
    return frozenset((x, y) for y in range(GH) for x in range(GW) if rows[y * GW + x] == '1')


def stroke_glyph():
    """Twee of drie lijnstukken: leest als een onbekend schrift, niet als ruis."""
    while True:
        px = set()
        for _ in range(rnd.randint(2, 3)):
            kind = rnd.randrange(3)
            if kind == 0:
                x, y0 = rnd.randrange(GW), rnd.randrange(GH - 2)
                px.update((x, y) for y in range(y0, rnd.randint(y0 + 2, GH - 1) + 1))
            elif kind == 1:
                y, x0 = rnd.randrange(GH), rnd.randrange(GW - 1)
                px.update((x, y) for x in range(x0, GW))
            else:
                y0, flip = rnd.randrange(GH - 2), rnd.random() < 0.5
                px.update((GW - 1 - i if flip else i, y0 + i) for i in range(GW))
        if 5 <= len(px) <= 10:
            return frozenset(px)


digits = [bits(d) for d in DIGITS]
glyph_set = list({*digits, *(frozenset((GW - 1 - x, y) for x, y in g) for g in digits),
                  *(stroke_glyph() for _ in range(40))})


def stream():
    trail = rnd.randint(5, 14)
    dist = CELLS + trail + rnd.randint(2, CELLS)
    speed = rnd.uniform(0.15, 0.5)  # cellen per frame
    cycle = min(cycles, key=lambda c: abs(c - dist / speed))
    return trail, dist, cycle, rnd.randrange(cycle)


streams = [[stream() for _ in range(args.streams)] for _ in LANES]
# Per cel een eigen wisseltempo; de tabel loopt rond met het aantal frames.
change = [[pick_period(rnd, args.frames, 6, 30) for _ in range(CELLS)] for _ in LANES]
glyphs = [[[rnd.choice(glyph_set) for _ in range(args.frames // p)] for p in row] for row in change]


def frame(t):
    img = Image.new('RGB', (W, H))
    px = img.load()
    for lane, y0 in enumerate(LANES):
        heads, fade = set(), {}
        for trail, dist, cycle, phase in streams[lane]:
            head = (t + phase) % cycle * dist // cycle
            if head < CELLS:
                heads.add(head)
            for k in range(1, trail + 1):
                if 0 <= head - k < CELLS:
                    fade[head - k] = max(fade.get(head - k, 0), (1 - k / (trail + 1)) ** 1.3)

        def put(cell, glyph, rgb):
            for x, y in glyph:
                px[cell * CELL + x, y0 + y] = rgb

        for cell, b in fade.items():
            g = 255 * b
            put(cell, glyphs[lane][cell][t // change[lane][cell]],
                (int(g * 0.1), max(40, int(g)), int(g * 0.25)))
        for cell in heads:
            put(cell, rnd.choice(glyph_set), HEAD)
    return img.tobytes()


write_gif(map(frame, range(args.frames)), args.out, args.delay)
