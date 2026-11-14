"""GIF writer and shared drawing helpers for the 96x16 iPixel panel.

The panel's decoder can't handle delta frames (sub-rectangles, transparency),
which Pillow writes by default. ffmpeg with -gifflags 0 writes every frame
in full, with one shared palette.
"""
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 96, 16
FLAT = 'split[a][b];[a]palettegen=reserve_transparent=0[p];[b][p]paletteuse'


def write_gif(frames, out, delay):
    """Write an iterable of W*H RGB24 frames (bytes) to out, delay ms each."""
    cmd = ['ffmpeg', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', f'1000/{delay}', '-i', '-', '-vf', FLAT, '-gifflags', '0', out]
    with subprocess.Popen(cmd, stdin=subprocess.PIPE) as ffmpeg:
        ffmpeg.stdin.writelines(frames)
    if ffmpeg.returncode:
        raise subprocess.CalledProcessError(ffmpeg.returncode, cmd)


def scroll_frames(strip, speed, bg):
    """Frames of strip scrolling right to left, from off-screen right to off-screen left."""
    canvas = Image.new('RGB', (W + strip.width + W, H), bg)
    canvas.paste(strip, (W, 0))
    for x in range(0, strip.width + W + 1, speed):
        yield canvas.crop((x, 0, x + W, H)).tobytes()


def fit_text(text, font_path, width, height, scale=4):
    """Anti-aliased 'L' mask of text, as tall as height allows, squeezed horizontally to fit width."""
    font = ImageFont.truetype(font_path, height * scale)
    left, top, right, bottom = font.getbbox(text)
    mask = Image.new('L', (right - left, bottom - top))
    ImageDraw.Draw(mask).text((-left, -top), text, font=font, fill=255)
    size = (min(width, round(mask.width / scale)), min(height, round(mask.height / scale)))
    return mask.resize(size, Image.Resampling.LANCZOS)


# Seamless loops: everything periodic gets a period that divides the frame count.

def divisors(n):
    return [d for d in range(1, n + 1) if n % d == 0]


def pick_period(rnd, frames, lo, hi):
    return rnd.choice([d for d in divisors(frames) if lo <= d <= hi] or [frames])


def twinkle(t, period, phase, width):
    """Brightness 0..1 of a twinkle that peaks once per period."""
    return max(0.0, 1 - abs((t + phase) % period - period / 2) / width)


def star(px, x, y, color, b):
    """Lighten a pixel towards color*b; above 0.6 also a dimmer plus-shaped glint."""
    points = [(x, y, b)]
    if b > 0.6:
        points += [(x + dx, y + dy, b * 0.4) for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1))]
    for px_x, px_y, pb in points:
        if 0 <= px_x < W and 0 <= px_y < H:
            px[px_x, px_y] = tuple(max(c, int(g * pb)) for c, g in zip(px[px_x, px_y], color))
