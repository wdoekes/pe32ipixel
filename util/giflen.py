from PIL import Image
import sys

img = Image.open(sys.argv[1])
duration = 0

while True:
  try:
    duration += img.info["duration"]
    img.seek(img.tell() + 1)
  except EOFError:
    break

print(f"Total duration: {duration} ms")
