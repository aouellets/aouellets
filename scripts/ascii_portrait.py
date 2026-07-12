#!/usr/bin/env python3
"""Convert a portrait photo into an ASCII character grid for the profile SVG.

Usage:
    python3 scripts/ascii_portrait.py assets/portrait.jpg > assets/portrait_ascii.txt

The defaults (crop window, columns, tone mapping) are tuned for the current
portrait; pass --help for the knobs to re-tune after swapping the photo.
"""

import argparse
import sys

from PIL import Image, ImageEnhance, ImageOps

# Dark -> light character ramp. On a dark page the dense glyphs read as bright,
# so bright pixels map to the dense end.
RAMP = " .'`^:;il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def to_ascii(path, cols, crop, char_aspect, contrast, invert, gamma):
    img = Image.open(path).convert("L")
    w, h = img.size
    l, t, r, b = (int(c * s) for c, s in zip(crop, (w, h, w, h)))
    img = img.crop((l, t, r, b))
    img = ImageOps.autocontrast(img, cutoff=2)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    if invert:
        img = ImageOps.invert(img)

    rows = max(1, round(cols * (img.height / img.width) * char_aspect))
    img = img.resize((cols, rows))

    px = img.load()
    lines = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            v = (px[x, y] / 255.0) ** gamma
            line += RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
        lines.append(line.rstrip())
    return lines


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("image")
    p.add_argument("--cols", type=int, default=46)
    p.add_argument("--crop", type=float, nargs=4, default=[0.16, 0.0, 0.86, 0.74],
                   metavar=("L", "T", "R", "B"), help="crop window as 0-1 fractions")
    p.add_argument("--char-aspect", type=float, default=0.5,
                   help="height/width ratio compensation for monospace cells")
    p.add_argument("--contrast", type=float, default=1.35)
    p.add_argument("--gamma", type=float, default=1.0,
                   help=">1 darkens midtones, <1 brightens them")
    p.add_argument("--invert", action="store_true",
                   help="map dark pixels to dense glyphs instead of bright ones")
    a = p.parse_args()
    sys.stdout.write("\n".join(to_ascii(a.image, a.cols, a.crop, a.char_aspect,
                                        a.contrast, a.invert, a.gamma)) + "\n")


if __name__ == "__main__":
    main()
