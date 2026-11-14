import asyncio
import io
import statistics
import sys
import time
import zlib

from bleak import BleakClient
from PIL import Image

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H = 96, 16


def cmd(code, data=b''):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


def png_cmd(scr, color):
    buf = io.BytesIO()
    Image.new('RGBA', (W, H), color).save(buf, format='PNG')
    png = buf.getvalue()
    hdr = b'\0' + len(png).to_bytes(4, 'little') + zlib.crc32(png).to_bytes(4, 'little') + bytes([0, scr])
    return cmd(0x0002, hdr + png)


async def main(addr, n=10):
    acks = asyncio.Queue()
    async with BleakClient(addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))

        async def rtt(payload):
            t = time.monotonic()
            await client.write_gatt_char(TX, payload)
            await acks.get()
            return 1000 * (time.monotonic() - t)

        await rtt(cmd(0x0104, b'\x01'))
        for name, make in (
            ('brightness', lambda i: cmd(0x8004, bytes([50 + i]))),
            ('png 0x65', lambda i: png_cmd(0x65, (20 * i, 0, 0, 255))),
            ('png 0x01', lambda i: png_cmd(0x01, (0, 20 * i, 0, 255))),
        ):
            ms = [await rtt(make(i)) for i in range(n)]
            print(f'{name:10s} median {statistics.median(ms):6.1f}ms  max {max(ms):6.1f}ms')


asyncio.run(main(sys.argv[1]))
