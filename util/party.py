"""Feestelijke tekst: regenboog die over de letters loopt, glitter op de letters en
dwarrelende confetti erachter, als naadloos loopende GIF voor 96x16."""
import argparse
import colorsys
import math
import random

from PIL import Image, ImageFilter

from ledgif import H, W, fit_text, pick_period, star, twinkle, write_gif

CONFETTI = [(255, 60, 60), (255, 200, 0), (60, 220, 255), (255, 80, 220), (80, 255, 80), (255, 140, 0)]
DIM = 0.7  # confetti iets gedempt, zodat de tekst voorgaat

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument('out')
parser.add_argument('--text', default='Gefeliciteerd!')
parser.add_argument('--font', default='DejaVuSans-Bold.ttf',
                    help='TTF/OTF: pad, of bestandsnaam uit de systeemfonts')
parser.add_argument('--frames', type=int, default=100,
                    help='looplengte; kies iets met veel delers (100, 120, 240)')
parser.add_argument('--delay', type=int, default=50, help='ms per frame, veelvoud van 10')
parser.add_argument('--confetti', type=int, default=35)
parser.add_argument('--sparkles', type=int, default=25)
parser.add_argument('--seed', type=int)
args = parser.parse_args()

rnd = random.Random(args.seed)

text = fit_text(args.text, args.font, W - 4, H - 2)
mask = Image.new('L', (W, H))
mask.paste(text, ((W - text.width) // 2, (H - text.height) // 2))
outline = mask.filter(ImageFilter.MaxFilter(3))
on_text = [(x, y) for y in range(H) for x in range(W) if mask.getpixel((x, y)) >= 160]

confetti = [(rnd.randrange(W), rnd.choice(CONFETTI), pick_period(rnd, args.frames, 25, 100),
             rnd.randrange(args.frames), rnd.uniform(0, 3), pick_period(rnd, args.frames, 20, 50))
            for _ in range(args.confetti)]
sparkles = [(*rnd.choice(on_text), pick_period(rnd, args.frames, 10, 50),
             rnd.randrange(args.frames), rnd.uniform(1.5, 3))
            for _ in range(args.sparkles)]


def rainbow(t):
    row = Image.new('RGB', (W, 1))
    row.putdata([tuple(int(255 * c) for c in colorsys.hsv_to_rgb((x / 64 + t / args.frames) % 1, 0.75, 1))
                 for x in range(W)])
    return row.resize((W, H), Image.Resampling.NEAREST)


def frame(t):
    img = Image.new('RGB', (W, H))
    px = img.load()
    for x0, color, per, phase, amp, sway in confetti:
        y = (t + phase) % per * (H + 2) // per - 1
        x = round(x0 + amp * math.sin(2 * math.pi * (t + phase) / sway))
        # Om en om liggend en staand: dat leest als fladderen.
        flake = ((0, 0), (1, 0)) if (t + phase) // 3 % 2 else ((0, 0), (0, 1))
        for dx, dy in flake:
            if 0 <= x + dx < W and 0 <= y + dy < H:
                px[x + dx, y + dy] = tuple(int(c * DIM) for c in color)
    img.paste('black', mask=outline)
    img.paste(rainbow(t), mask=mask)
    for x, y, per, phase, width in sparkles:
        star(px, x, y, (255, 255, 255), twinkle(t, per, phase, width))
    return img.tobytes()


write_gif(map(frame, range(args.frames)), args.out, args.delay)
