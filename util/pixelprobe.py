import asyncio
import sys
import time

from bleak import BleakClient

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
W, H = 96, 16

PIXELS = [((i, i), 0xFFFFFF) for i in range(1, H)] + [
    ((0, 0), 0xFF0000),
    ((W - 1, 0), 0x00FF00),
    ((0, H - 1), 0x0000FF),
    ((W - 1, H - 1), 0xFFFF00),
]


def cmd(code, data=b''):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


async def main(addr):
    acks = asyncio.Queue()
    async with BleakClient(addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))
        await client.write_gatt_char(TX, cmd(0x0104, b'\x01'))
        print('diy', (await acks.get()).hex())

        t = time.monotonic()
        for (x, y), rgb in PIXELS:
            await client.write_gatt_char(TX, cmd(0x0105, rgb.to_bytes(4, 'big') + bytes([x, y])))
        print(f'{len(PIXELS)} px in {1000 * (time.monotonic() - t):.0f}ms')

        await asyncio.sleep(1)
        while not acks.empty():
            print('response', acks.get_nowait().hex())


asyncio.run(main(sys.argv[1]))
