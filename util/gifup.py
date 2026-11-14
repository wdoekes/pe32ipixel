import argparse
import asyncio
import time
import zlib

from bleak import BleakClient
from PIL import Image

TX = '0000fa02-0000-1000-8000-00805f9b34fb'
RX = '0000fa03-0000-1000-8000-00805f9b34fb'
SIZE = (96, 16)
WINDOW = 12 * 1024
CHUNK = 244


def cmd(code, data):
    return (len(data) + 4).to_bytes(2, 'little') + code.to_bytes(2, 'little') + data


def slots_cmd(code, slots):
    return cmd(code, len(slots).to_bytes(2, 'little') + bytes(slots))


def gif_windows(gif, slot):
    head = len(gif).to_bytes(4, 'little') + zlib.crc32(gif).to_bytes(4, 'little') + bytes([0x02, slot])
    for n, pos in enumerate(range(0, len(gif), WINDOW)):
        yield cmd(0x0003, bytes([0x02 if n else 0x00]) + head + gif[pos:pos + WINDOW])


async def main(args):
    with Image.open(args.gif) as img:
        if img.size != SIZE:
            raise SystemExit(f'{args.gif}: {img.size}, panel wil {SIZE} (anders zwart beeld)')
        print(f'{img.n_frames} frames')
    with open(args.gif, 'rb') as f:
        gif = f.read()

    acks = asyncio.Queue()
    async with BleakClient(args.addr) as client:
        await client.start_notify(RX, lambda _, d: acks.put_nowait(d))

        async def send(msg):
            for pos in range(0, len(msg), CHUNK):
                await client.write_gatt_char(TX, msg[pos:pos + CHUNK], response=True)
            return await asyncio.wait_for(acks.get(), 10)

        t0 = time.monotonic()
        try:
            for msg in gif_windows(gif, args.slot):
                ack = await send(msg)
                print(f'{len(msg):6d} B  {time.monotonic() - t0:6.1f}s  {ack.hex()}')
        except BaseException:
            # Includes Ctrl-C. A half-written slot is what pypixelcolor warns
            # can bootloop the panel, so leave it empty instead.
            if args.slot:
                print('upload afgebroken, slot wissen', (await send(slots_cmd(0x0102, [args.slot]))).hex())
            raise


parser = argparse.ArgumentParser()
parser.add_argument('addr')
parser.add_argument('gif')
parser.add_argument('--slot', type=int, default=0, help='0 = tonen zonder opslaan')
asyncio.run(main(parser.parse_args()))
