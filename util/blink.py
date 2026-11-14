"""Knipperende tekst tussen twee slingerende bellen, als naadloos loopende GIF voor 96x16."""
import argparse
import math

from PIL import Image, ImageDraw, ImageOps

from ledgif import H, W, fit_text, write_gif

S = 4  # supersampling: bellen draaien op subpixels
BELL_W = 16  # vak per bel, inclusief ruimte voor de slingerbeweging
PIVOT = (BELL_W / 2, 1)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('out')
parser.add_argument('--text', default='BIERTJEUH!')
parser.add_argument('--font', default='DejaVuSans-Bold.ttf',
                    help='TTF/OTF: pad, of bestandsnaam uit de systeemfonts')
parser.add_argument('--fg', default='#ffcc00')
parser.add_argument('--off', default='black', help='tekstkleur in de "uit"-fase')
parser.add_argument('--frames', type=int, default=8, help='frames per knippercyclus')
parser.add_argument('--delay', type=int, default=100, help='ms per frame, veelvoud van 10')
parser.add_argument('--swing', type=float, default=15, help='maximale uitslag van de bellen, graden')
args = parser.parse_args()


def make_bell():
    """Bel van ~12x15 px, hangend aan PIVOT, getekend op S-voudige resolutie."""
    img = Image.new('RGBA', (BELL_W * S, H * S))
    d = ImageDraw.Draw(img)
    cx = BELL_W / 2

    def box(x0, y0, x1, y1):
        return [(cx + x0) * S, y0 * S, (cx + x1) * S, y1 * S]

    d.rectangle(box(-1, 0, 1, 2.5), fill=(200, 130, 10))
    d.ellipse(box(-3.5, 1.5, 3.5, 8.5), fill=(240, 180, 30))
    d.polygon([((cx + x) * S, y * S) for x, y in ((-3.5, 5), (3.5, 5), (6, 12), (-6, 12))],
              fill=(240, 180, 30))
    d.polygon([((cx + x) * S, y * S) for x, y in ((-2.5, 4), (-1.5, 4), (-3.5, 11.5), (-4.8, 11.5))],
              fill=(255, 235, 140))
    d.rectangle(box(-6.5, 11.5, 6.5, 13), fill=(200, 130, 10))
    d.ellipse(box(-1.4, 12.6, 1.4, 15.4), fill=(170, 100, 10))
    return img


bell = make_bell()
text_w = W - 2 * BELL_W - 2
text = fit_text(args.text, args.font, text_w, H - 1, S)
text_pos = ((W - text.width) // 2, (H - text.height) // 2)


def bell_frame(angle, mirror):
    hi = bell.rotate(angle, resample=Image.Resampling.BICUBIC, center=(PIVOT[0] * S, PIVOT[1] * S))
    if mirror:
        hi = ImageOps.mirror(hi)
    return hi.resize((BELL_W, H), Image.Resampling.BOX)


def frame(t):
    img = Image.new('RGB', (W, H))
    angle = args.swing * math.sin(2 * math.pi * t / args.frames)
    left = bell_frame(angle, False)
    right = bell_frame(angle, True)
    img.paste(left, (0, 0), left)
    img.paste(right, (W - BELL_W, 0), right)
    on = t < args.frames / 2
    img.paste(args.fg if on else args.off, (*text_pos, text_pos[0] + text.width, text_pos[1] + text.height), text)
    return img.tobytes()


write_gif(map(frame, range(args.frames)), args.out, args.delay)
