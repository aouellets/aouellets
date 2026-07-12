#!/usr/bin/env python3
"""Silhouette matte for the profile portrait.

Cuts the subject out of assets/portrait.jpg with a hand-traced polygon matte
(no ML dependencies) and writes assets/portrait_masked.png, the input that
scripts/ascii_portrait.py converts to the ASCII grid.

The polygons below are tuned to the CURRENT photo (runner, centered, square
crop). If you swap the photo, re-trace the shapes — coordinates are fractions
of image width/height, so eyeball them off any image viewer.

Full pipeline after swapping assets/portrait.jpg:
    python3 scripts/matte_portrait.py
    python3 scripts/ascii_portrait.py assets/portrait_masked.png \
        --cols 48 --crop 0.14 0.0 0.87 0.76 --char-aspect 0.55 \
        --contrast 1.25 > assets/portrait_ascii.txt
    python3 scripts/build_profile.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SUBJECT_FLOOR = 42  # min luminance inside the matte so black clothing keeps texture

img = Image.open(ROOT / "assets/portrait.jpg").convert("L")
W, H = img.size

def pts(fr):
    return [(x * W, y * H) for x, y in fr]

mask = Image.new("L", (W, H), 0)
d = ImageDraw.Draw(mask)

# head + neck
d.ellipse([0.405 * W, 0.030 * H, 0.585 * W, 0.300 * H], fill=255)
d.polygon(pts([(0.44, 0.26), (0.56, 0.26), (0.57, 0.36), (0.43, 0.36)]), fill=255)
# torso down through the shorts
d.polygon(pts([(0.30, 0.36), (0.70, 0.345), (0.78, 0.52), (0.80, 0.75),
               (0.84, 1.0), (0.30, 1.0), (0.26, 0.75), (0.28, 0.52)]), fill=255)
# viewer-left arm (outer edge -> hand -> inner edge)
d.polygon(pts([(0.30, 0.36), (0.21, 0.42), (0.175, 0.53), (0.165, 0.63),
               (0.19, 0.71), (0.225, 0.755), (0.26, 0.72), (0.27, 0.62),
               (0.28, 0.50), (0.30, 0.44)]), fill=255)
# viewer-right arm (bent, hand in front of torso)
d.polygon(pts([(0.70, 0.345), (0.82, 0.42), (0.86, 0.52), (0.81, 0.61),
               (0.72, 0.665), (0.645, 0.695), (0.615, 0.655), (0.68, 0.60),
               (0.72, 0.52), (0.695, 0.44)]), fill=255)

mask = mask.filter(ImageFilter.GaussianBlur(5))

gray = ImageOps.autocontrast(img, cutoff=1)
px, mx = gray.load(), mask.load()
out = Image.new("L", (W, H), 0)
op = out.load()
for y in range(H):
    for x in range(W):
        a = mx[x, y] / 255.0
        op[x, y] = int(a * max(px[x, y], SUBJECT_FLOOR))

out.save(ROOT / "assets/portrait_masked.png")
print("wrote assets/portrait_masked.png")
