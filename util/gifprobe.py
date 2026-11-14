import argparse
import asyncio
import io
import time
import zlib

from bleak import BleakClient
from PIL import Image, ImageDraw

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H = 96, 16
WINDOW = 12 * 1024
CHUNK = 244


def cmd(code, data):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


def make_gif(frames, noise):
    imgs = []
    for i in range(frames):
        img = Image.effect_noise((W, H), 80).convert('RGB') if noise else Image.new('RGB', (W, H))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 0, 30, H - 1), fill=(0, 0, 0))
        draw.text((1, 2), str(i), fill=(255, 255, 255))
        x = 32 + i % (W - 32)
        draw.line((x, 0, x, H - 1), fill=(0, 255, 0))
        imgs.append(img)
    buf = io.BytesIO()
    imgs[0].save(buf, format='GIF', save_all=True, append_images=imgs[1:], duration=100, loop=0)
    return buf.getvalue()


def gif_windows(gif, slot):
    head = len(gif).to_bytes(4, 'little') + zlib.crc32(gif).to_bytes(4, 'little') + bytes([0x02, slot])
    for n, pos in enumerate(range(0, len(gif), WINDOW)):
        yield cmd(0x0003, bytes([0x02 if n else 0x00]) + head + gif[pos:pos + WINDOW])


async def main(args):
    gif = make_gif(args.frames, args.noise)
    print(f'{args.frames} frames, {len(gif)} B ({len(gif) / args.frames:.0f} B/frame)')
    acks = asyncio.Queue()
    async with BleakClient(args.addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))
        t0 = time.monotonic()
        for msg in gif_windows(gif, args.slot):
            for pos in range(0, len(msg), CHUNK):
                await client.write_gatt_char(TX, msg[pos:pos + CHUNK], response=True)
            ack = await asyncio.wait_for(acks.get(), 10)
            print(f'{len(msg):6d} B  {time.monotonic() - t0:6.1f}s  {ack.hex()}')


parser = argparse.ArgumentParser()
parser.add_argument('addr')
parser.add_argument('frames', type=int)
parser.add_argument('--slot', type=int, default=0, help='0 = tonen zonder opslaan')
parser.add_argument('--noise', action='store_true', help='ruis-achtergrond: worst case B/frame')
asyncio.run(main(parser.parse_args()))
