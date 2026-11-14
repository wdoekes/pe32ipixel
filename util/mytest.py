import asyncio, io, random, sys, time, zlib
from bleak import BleakClient
from PIL import Image, ImageDraw

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H, BANDS = 96, 16, 16


def cmd(code, data=b''):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


def frame(levels):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    bw = W // BANDS
    for i, lvl in enumerate(levels):
        draw.rectangle((i * bw, H - lvl, i * bw + bw - 2, H - 1), fill=(0, 255, 0, 255))
    buf = io.BytesIO()
    img.save(buf, format='PNG', compress_level=9)
    png = buf.getvalue()
    hdr = b'\0' + len(png).to_bytes(4, 'little') + zlib.crc32(png).to_bytes(4, 'little') + b'\0\x65'
    return cmd(0x0002, hdr + png)


async def main(addr, n=50):
    acks = asyncio.Queue()
    async with BleakClient(addr) as client:
        print('mtu', client.mtu_size)
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))
        await client.write_gatt_char(TX, cmd(0x0104, b'\x01'))
        print('diy', (await acks.get()).hex())
        t0 = time.monotonic()
        for _ in range(n):
            payload = frame([random.randint(1, H) for _ in range(BANDS)])
            t = time.monotonic()
            await client.write_gatt_char(TX, payload)
            ack = await acks.get()
            print(f'{len(payload):4d}B {1000 * (time.monotonic() - t):6.1f}ms {ack.hex()}')
        print(f'{n / (time.monotonic() - t0):.1f} fps')


asyncio.run(main(sys.argv[1]))
