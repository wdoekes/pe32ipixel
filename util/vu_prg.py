import asyncio
import io
import math
import statistics
import sys
import time
import zlib

from bleak import BleakClient
from PIL import Image

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H, N = 96, 16, 16
ZONES = ((84, (0, 255, 0, 255)), (W, (255, 0, 0, 255)))


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


def prg_cmd(scr):
    return cmd(0x8008, (1).to_bytes(2, 'little') + bytes([scr]))


async def main(addr, action):
    acks = asyncio.Queue()
    async with BleakClient(addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))

        async def rtt(payload):
            t = time.monotonic()
            await client.write_gatt_char(TX, payload)
            ack = await acks.get()
            return 1000 * (time.monotonic() - t), ack

        if action == 'upload':
            for level in range(N):
                ms, ack = await rtt(png_cmd(level + 1, frame(level)))
                print(f'slot {level + 1:2d} {ms:6.1f}ms {ack.hex()}')
            return

        await asyncio.sleep(3)

        t0 = time.monotonic()
        times = []
        for _ in range(100):
            level = round((N - 1) * abs(math.sin(time.monotonic() - t0)))
            ms, ack = await rtt(prg_cmd(level + 1))
            times.append(ms)
            print(f'level {level:2d} {ms:6.1f}ms {ack.hex()}')
            await asyncio.sleep(0.5)
        print(f'median {statistics.median(times):.1f}ms  max {max(times):.1f}ms')


asyncio.run(main(*sys.argv[1:3]))
