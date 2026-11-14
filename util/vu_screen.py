import asyncio
import io
import sys
import time
import zlib

from bleak import BleakClient
from PIL import Image

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H, N = 96, 16, 9
REMOCON = 0x6F
ZONES = ((84, (0, 255, 0, 255)), (W, (255, 0, 0, 255)))
SWEEP = [*range(N), *range(N - 2, 0, -1)]


def cmd(code, data=b''):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


def frame(level):
    lit = round(W * level / (N - 1))
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    x0 = 0
    for x1, color in ZONES:
        if lit > x0:
            img.paste(color, (x0, 0, min(lit, x1), H))
        x0 = x1
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=9)
    return buf.getvalue()


def png_cmd(scr, png):
    hdr = b'\0' + len(png).to_bytes(4, 'little') + zlib.crc32(png).to_bytes(4, 'little') + bytes([0, scr])
    return cmd(0x0002, hdr + png)


async def main(addr, action):
    acks = asyncio.Queue()
    async with BleakClient(addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))

        if action == 'upload':
            for level in range(N):
                await client.write_gatt_char(TX, png_cmd(REMOCON + level, frame(level)))
                print(f'slot {REMOCON + level:#04x} {(await acks.get()).hex()}')
            return

        for level in SWEEP * 5:
            t = time.monotonic()
            await client.write_gatt_char(TX, cmd(0x8007, bytes([level + 1])))
            ms = 1000 * (time.monotonic() - t)
            await asyncio.sleep(0.2)
            responses = []
            while not acks.empty():
                responses.append(acks.get_nowait().hex())
            print(f'level {level} {ms:5.1f}ms {" ".join(responses)}')


asyncio.run(main(*sys.argv[1:3]))
