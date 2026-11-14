import argparse

from PIL import Image, ImageDraw

from ledgif import H, W, write_gif

parser = argparse.ArgumentParser()
parser.add_argument('frames', type=int)
parser.add_argument('out')
parser.add_argument('--noise', action='store_true', help='ruis-achtergrond: worst case B/frame')
parser.add_argument('--tag', default='', help='prefix voor het framenummer, bv. slotnummer')
parser.add_argument('--delay', type=int, default=500, help='ms per frame')
args = parser.parse_args()


def frame(i):
    img = Image.effect_noise((W, H), 80).convert('RGB') if args.noise else Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, 44, H - 1), fill=(0, 0, 0))
    draw.text((1, 2), f'{args.tag}{i}', fill=(255, 255, 255))
    x = 46 + i % (W - 46)
    draw.line((x, 0, x, H - 1), fill=(0, 255, 0))
    return img.tobytes()


write_gif(map(frame, range(args.frames)), args.out, args.delay)
