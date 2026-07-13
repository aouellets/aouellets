#!/usr/bin/env python3
"""Face matte for the profile portrait.

Crops assets/portrait.jpg to a head-and-shoulders frame, cuts the subject out
with a hand-traced polygon matte (no ML dependencies), and writes
assets/portrait_masked.png — the input scripts/ascii_portrait.py turns into
the ASCII grid.

The crop box and shapes below are tuned to the CURRENT photo. If you swap the
photo, re-trace them; coordinates are fractions of the CROPPED frame.

Full pipeline after swapping assets/portrait.jpg (a higher-resolution,
face-forward photo gives the halftone more detail to work with):
    python3 scripts/matte_portrait.py
    python3 scripts/ascii_portrait.py assets/portrait_masked.png \
        --cols 104 --crop 0.15 0.02 0.87 0.90 --char-aspect 0.44 \
        --contrast 1.05 --json assets/portrait_tones.json
    python3 scripts/build_profile.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CROP = (0.26, 0.0, 0.72, 0.42)  # face box within the source photo
SUBJECT_FLOOR = 46  # min luminance inside the matte so dark clothing keeps texture

src = Image.open(ROOT / "assets/portrait.jpg").convert("L")
sw, sh = src.size
img = src.crop((int(CROP[0] * sw), int(CROP[1] * sh),
                int(CROP[2] * sw), int(CROP[3] * sh)))
W, H = img.size

def pts(fr):
    return [(x * W, y * H) for x, y in fr]

mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)

# head
d.ellipse([0.30 * W, 0.06 * H, 0.72 * W, 0.73 * H], fill=255)
# neck
d.polygon(pts([(0.40, 0.60), (0.62, 0.60), (0.64, 0.88), (0.38, 0.88)]), fill=255)
# shoulders rising into the bottom of the frame
d.polygon(pts([(0.03, 1.0), (0.22, 0.85), (0.40, 0.79), (0.62, 0.79),
               (0.80, 0.85), (0.99, 1.0)]), fill=255)

mask = mask.filter(ImageFilter.GaussianBlur(2.5))

# Sharpen features, then stretch contrast across the SUBJECT's tonal range only
# (a global autocontrast is dominated by the black background and flattens the
# face into one density band).
gray = img.filter(ImageFilter.UnsharpMask(radius=3, percent=130))
px, mx = gray.load(), mask.load()
subject = sorted(px[x, y] for y in range(H) for x in range(W) if mx[x, y] > 128)
lo, hi = subject[int(len(subject) * 0.02)], subject[int(len(subject) * 0.98)]

out = Image.new("L", (W, H), 0)
op = out.load()
for y in range(H):
    for x in range(W):
        a = mx[x, y] / 255.0
        v = (min(max(px[x, y], lo), hi) - lo) / (hi - lo) * 255
        op[x, y] = int(a * max(v, SUBJECT_FLOOR))

out.save(ROOT / "assets/portrait_masked.png")
print(f"wrote assets/portrait_masked.png ({W}x{H})")
