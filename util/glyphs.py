"""Print pypixelcolor's 8x16 digit glyphs as a C table, plus the full
send_text frame for "1" to compare against the ESP's first counter frame."""
from pypixelcolor.commands.send_text import send_text

HEADER = 15         # LEN, CMD, window, SIZE, CRC32, 0x00, slot
PROPS = 1 + 13      # character count, properties
BLOCK = 1 + 3 + 16  # glyph type, RGB, 16 rows

frame = send_text('0123456789', char_height=16).windows[0].data
blocks = frame[HEADER + PROPS:]
assert len(blocks) == 10 * BLOCK and blocks[0] == 0x00, 'not all 8x16 glyphs'

print('static const uint8_t digits[10][16] = {')
for i in range(10):
    glyph = blocks[i * BLOCK + 4:(i + 1) * BLOCK]
    print('    {' + ', '.join(f'0x{b:02x}' for b in glyph) + f'}}, /* {i} */')
print('};')
print('/*', send_text('1', char_height=16).windows[0].data.hex(' '), '*/')
