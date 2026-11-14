import sys

def dump(data):
    flags = data[10]
    pos = 13 + (3 << ((flags & 7) + 1) if flags & 0x80 else 0)
    gce = {}
    n = 0
    while data[pos] != 0x3B:
        if data[pos] == 0x21:
            label = data[pos + 1]
            pos += 2
            if label == 0xF9:
                packed = data[pos + 1]
                gce = dict(disp=(packed >> 2) & 7, transp=packed & 1, delay=int.from_bytes(data[pos + 2:pos + 4], 'little'))
            while data[pos]:
                pos += data[pos] + 1
            pos += 1
        else:
            x, y, w, h = (int.from_bytes(data[pos + i:pos + i + 2], 'little') for i in (1, 3, 5, 7))
            lflags = data[pos + 9]
            pos += 10 + (3 << ((lflags & 7) + 1) if lflags & 0x80 else 0) + 1
            while data[pos]:
                pos += data[pos] + 1
            pos += 1
            print(n, f'{x},{y} {w}x{h}', gce, 'lct' if lflags & 0x80 else '')
            n, gce = n + 1, {}

dump(open(sys.argv[1], 'rb').read())
