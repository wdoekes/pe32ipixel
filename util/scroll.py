import argparse

from PIL import Image, ImageDraw, ImageFont

from ledgif import H, scroll_frames, write_gif

parser = argparse.ArgumentParser(description='Tekst die van rechts naar links scrollt, als GIF voor 96x16.')
parser.add_argument('text')
parser.add_argument('out')
parser.add_argument('--font', default='DejaVuSans-Bold.ttf',
                    help='TTF/OTF: pad, of bestandsnaam uit de systeemfonts')
parser.add_argument('--size', type=int, help='fontgrootte in px (default: grootste die past)')
parser.add_argument('--fg', default='white')
parser.add_argument('--bg', default='black')
parser.add_argument('--speed', type=int, default=1, help='px per frame')
parser.add_argument('--delay', type=int, default=40, help='ms per frame, veelvoud van 10')
parser.add_argument('--aa', action='store_true', help='anti-aliasing (default: scherpe pixels)')
args = parser.parse_args()


def fit_font(text):
    for size in range(2 * H, 0, -1):
        font = ImageFont.truetype(args.font, size)
        left, top, right, bottom = font.getbbox(text)
        if bottom - top <= H:
            return font


font = ImageFont.truetype(args.font, args.size) if args.size else fit_font(args.text)
left, top, right, bottom = font.getbbox(args.text)
strip = Image.new('RGB', (right - left, H), args.bg)
draw = ImageDraw.Draw(strip)
draw.fontmode = 'L' if args.aa else '1'
draw.text((-left, (H - (bottom - top)) // 2 - top), args.text, font=font, fill=args.fg)

write_gif(scroll_frames(strip, args.speed, args.bg), args.out, args.delay)
