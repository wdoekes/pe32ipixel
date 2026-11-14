"""Woorden één voor één gecentreerd laten flitsen, als GIF voor 96x16."""
import argparse

from PIL import Image

from ledgif import H, W, fit_text, write_gif

COLORS = ['#ffcc00', '#ff3030', '#30e0ff', '#ff40e0', '#40ff40', '#ff8c00', 'white']

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('out')
parser.add_argument('words', nargs='+', help='één argument per beeld, quote woorden met spaties')
parser.add_argument('--font', default='DejaVuSans-Bold.ttf',
                    help='TTF/OTF: pad, of bestandsnaam uit de systeemfonts')
parser.add_argument('--colors', nargs='+', default=COLORS, help='kleuren per woord, roulerend')
parser.add_argument('--on', type=int, default=700, help='ms per woord')
parser.add_argument('--off', type=int, default=150, help='ms zwart tussen de woorden')
parser.add_argument('--delay', type=int, default=50, help='ms per frame; on en off worden hierop afgerond')
args = parser.parse_args()

blank = Image.new('RGB', (W, H)).tobytes()


def frames():
    for i, word in enumerate(args.words):
        mask = fit_text(word, args.font, W - 4, H - 2)
        img = Image.new('RGB', (W, H))
        img.paste(args.colors[i % len(args.colors)], ((W - mask.width) // 2, (H - mask.height) // 2), mask)
        yield from [img.tobytes()] * max(1, round(args.on / args.delay))
        yield from [blank] * round(args.off / args.delay)


write_gif(frames(), args.out, args.delay)
