#!/usr/bin/env python3
"""Prepare the portrait crop for the profile halftone.

Full-rectangle print, no cutout: every cell of the frame renders. A soft
face matte drives a BACKGROUND DIM (studio-dark backdrop) instead of a hard
silhouette cut, so the figure emerges from a dark field with no visible
matte edge, and exposure is set from the face region only.

Outputs consumed by scripts/ascii_portrait.py:
  assets/portrait_masked.png      grayscale, face-exposed, background-dimmed,
                                  luminance floor so every cell draws a glyph
  assets/portrait_masked_rgb.png  color companion, saturation-lifted, same dim

The crop box and matte shapes are tuned to the CURRENT photo. If you swap
the photo, re-trace them; shape coordinates are fractions of the CROPPED
frame (they may extend past 0..1 — PIL clips them to the frame).

Full pipeline after swapping assets/portrait.jpg (a higher-resolution,
face-forward photo gives the halftone more detail to work with):
    python3 scripts/matte_portrait.py
    python3 scripts/ascii_portrait.py assets/portrait_masked.png \
        --cols 128 --crop 0 0 1 1 --char-aspect 0.43 \
        --rgb assets/portrait_masked_rgb.png \
        --contrast 1.0 --json assets/portrait_tones.json
    python3 scripts/build_profile.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CROP = (0.325, 0.008, 0.665, 0.444)  # bust frame within the source photo
FLOOR = 60      # min luminance so the full rectangle stays a contiguous glyph field
BG_LEVEL = 0.12  # background brightness relative to the subject
BG_SAT = 0.25   # background keeps only a whisper of its color — the face owns it

src = Image.open(ROOT / "assets/portrait.jpg")
sw, sh = src.size
box = (int(CROP[0] * sw), int(CROP[1] * sh), int(CROP[2] * sw), int(CROP[3] * sh))

gray = src.convert("L").crop(box).filter(ImageFilter.UnsharpMask(radius=2, percent=80))
W, H = gray.size

def pts(fr):
    return [(x * W, y * H) for x, y in fr]

# soft face/bust matte — used only to dim the background, never to cut it out
mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)
d.ellipse([0.215 * W, 0.039 * H, 0.782 * W, 0.685 * H], fill=255)
d.polygon(pts([(0.35, 0.56), (0.65, 0.56), (0.67, 0.83), (0.33, 0.83)]), fill=255)
d.polygon(pts([(-0.20, 0.96), (0.10, 0.80), (0.35, 0.74), (0.65, 0.74),
               (0.90, 0.80), (1.20, 0.96), (1.35, 1.15), (1.35, 1.40),
               (-0.30, 1.40), (-0.30, 1.15)]), fill=255)
mask = mask.filter(ImageFilter.GaussianBlur(6))
mx = mask.load()

# expose for the face: stretch percentiles from the subject region only
px = gray.load()
subject = sorted(px[x, y] for y in range(H) for x in range(W) if mx[x, y] > 128)
lo, hi = subject[int(len(subject) * 0.02)], subject[int(len(subject) * 0.98)]

def dim(x, y):
    return BG_LEVEL + (1.0 - BG_LEVEL) * (mx[x, y] / 255.0)

out = Image.new("L", (W, H), 0)
op = out.load()
for y in range(H):
    for x in range(W):
        v = (min(max(px[x, y], lo), hi) - lo) / (hi - lo) * 255
        op[x, y] = int(max(v * dim(x, y), FLOOR))
out.save(ROOT / "assets/portrait_masked.png")
print(f"wrote assets/portrait_masked.png ({W}x{H})")

rgb = ImageEnhance.Color(src.convert("RGB").crop(box)).enhance(1.25)
rp = rgb.load()
rgb_out = Image.new("RGB", (W, H), (0, 0, 0))
rop = rgb_out.load()
for y in range(H):
    for x in range(W):
        f = dim(x, y)
        m = mx[x, y] / 255.0
        sat = BG_SAT + (1.0 - BG_SAT) * m
        # subject-weighted exposure: the face/tee get a strong value lift so
        # they read luminous on the dark card; the backdrop stays truly dark
        gamma = 1.0 - 0.45 * m  # 1.0 (bg) -> 0.55 (subject)
        r, g, b = rp[x, y]
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        vals = []
        for c in (r, g, b):
            c = lum + (c - lum) * sat
            c = 255 * (max(c, 0) / 255) ** gamma
            vals.append(int(c * f))
        rop[x, y] = tuple(vals)
rgb_out.save(ROOT / "assets/portrait_masked_rgb.png")
print(f"wrote assets/portrait_masked_rgb.png ({W}x{H})")
