import argparse

from PIL import Image

from ledgif import H, scroll_frames, write_gif

parser = argparse.ArgumentParser(description='Een rij sprites die van rechts naar links scrollt, als GIF voor 96x16.')
parser.add_argument('image', help='sprite; wordt naar 16 px hoogte geschaald als hij groter is')
parser.add_argument('out')
parser.add_argument('--count', type=int, default=44)
parser.add_argument('--gap', type=int, default=2, help='px tussen de sprites')
parser.add_argument('--bg', default='black')
parser.add_argument('--speed', type=int, default=1, help='px per frame')
parser.add_argument('--delay', type=int, default=40, help='ms per frame, veelvoud van 10')
args = parser.parse_args()

with Image.open(args.image) as img:
    sprite = img.convert('RGBA')
if sprite.height > H:
    sprite = sprite.resize((sprite.width * H // sprite.height, H), Image.Resampling.NEAREST)

step = sprite.width + args.gap
strip = Image.new('RGB', (args.count * step - args.gap, H), args.bg)
for i in range(args.count):
    strip.paste(sprite, (i * step, (H - sprite.height) // 2), sprite)

write_gif(scroll_frames(strip, args.speed, args.bg), args.out, args.delay)
