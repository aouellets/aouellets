#!/usr/bin/env python3
"""Bust-portrait matte for the profile halftone.

Crops assets/portrait.jpg to a classic bust framing — ~5% headroom over the
hair, head ≈53% of frame width, chin at ~60% height, shoulders and chest
filling the bottom corners — cuts the subject out with a hand-traced polygon
matte (no ML dependencies), and writes assets/portrait_masked.png for
scripts/ascii_portrait.py.

The crop box and shapes are tuned to the CURRENT photo. If you swap the
photo, re-trace them; shape coordinates are fractions of the CROPPED frame
(they may extend past 0..1 — PIL clips them to the frame).

Full pipeline after swapping assets/portrait.jpg (a higher-resolution,
face-forward photo gives the halftone more detail to work with):
    python3 scripts/matte_portrait.py
    python3 scripts/ascii_portrait.py assets/portrait_masked.png \
        --cols 104 --crop 0 0 1 1 --char-aspect 0.43 \
        --contrast 1.05 --json assets/portrait_tones.json
    python3 scripts/build_profile.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CROP = (0.325, 0.008, 0.665, 0.444)  # bust frame within the source photo
SUBJECT_FLOOR = 60  # min luminance inside the matte so dark clothing keeps texture
# (must sit clearly above build_profile.SKIP so the clothing mass survives the
# background cutoff in both render modes)

src = Image.open(ROOT / "assets/portrait.jpg").convert("L")
sw, sh = src.size
img = src.crop((int(CROP[0] * sw), int(CROP[1] * sh),
                int(CROP[2] * sw), int(CROP[3] * sh)))
W, H = img.size

def pts(fr):
    return [(x * W, y * H) for x, y in fr]

mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)

# head (with headroom — the ellipse starts above the hairline)
d.ellipse([0.215 * W, 0.039 * H, 0.782 * W, 0.685 * H], fill=255)
# neck
d.polygon(pts([(0.35, 0.56), (0.65, 0.56), (0.67, 0.83), (0.33, 0.83)]), fill=255)
# shoulders and chest, running off the frame edges so the bust is grounded
d.polygon(pts([(-0.20, 0.96), (0.10, 0.80), (0.35, 0.74), (0.65, 0.74),
               (0.90, 0.80), (1.20, 0.96), (1.35, 1.15), (1.35, 1.40),
               (-0.30, 1.40), (-0.30, 1.15)]), fill=255)

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
