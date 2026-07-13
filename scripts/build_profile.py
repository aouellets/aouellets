#!/usr/bin/env python3
"""Generate assets/profile-dark.svg and assets/profile-light.svg.

Layout: ASCII halftone face portrait (assets/portrait_tones.json — a per-cell
luminance grid) in an inset well on the left; name, roles, stack, shipped
work, stat chips, and contact on the right. GFBT palette — near-black
surfaces, bone text, blood-red accent. Each portrait cell gets a glyph AND a
color from a deep-red-to-bone ramp, so the face carries photographic tone.

GitHub stats are fetched live when GITHUB_TOKEN (or GH_TOKEN) is set — the
profile workflow provides one — and fall back to "--" placeholders offline.
Stdlib only; safe to run anywhere: python3 scripts/build_profile.py
"""

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGIN = "aouellets"

# Design tokens (UI/UX Pro Max: token-driven, surfaces lifted off pure black,
# AA-checked text pairs, red reserved for accent moments).
TOKENS = {
    "dark": {
        "card": "#141112", "well": "#1b1718", "border": "#2e2325",
        "text": "#ece7dd", "muted": "#a39c8f", "dim": "#5f5852",
        "red": "#e5484d", "brand": "#c9182b",
    },
    "light": {
        "card": "#faf8f4", "well": "#f0ece3", "border": "#ddd5c7",
        "text": "#211d18", "muted": "#6d6557", "dim": "#b3aa99",
        "red": "#a4111f", "brand": "#a4111f",
    },
}

MONO = ("font-family=\"'JetBrains Mono','SFMono-Regular',Menlo,Consolas,"
        "'DejaVu Sans Mono','Liberation Mono',monospace\"")

# Halftone portrait: glyph texture ramp + per-tone color stops.
GLYPHS = " .':;i1tfLCG08@"
# Cells at or below SKIP are background. Set just above the matte's soft-edge
# falloff band: in light mode those low-alpha edge cells would invert to the
# DARKEST ink and draw a heavy outline ring around the silhouette.
SKIP = 45
HALFTONE = {
    # dark mode: brighter pixel -> hotter color (deep red -> brand red -> bone)
    "dark": [(37, "#69161f"), (64, "#8a1826"), (96, "#a81828"), (128, "#bf182b"),
             (160, "#d63a41"), (192, "#e5484d"), (220, "#eda28f"),
             (242, "#ece7dd")],
    # light mode: stops indexed by ink strength (255 - tone); darker feature -> heavier
    # ink. Visible warm floor so skin never fades to paper, then a deliberate cliff
    # into the feature bands so eyes/brows/beard stand off the skin field.
    "light": [(0, "#dcae93"), (64, "#d09a7c"), (112, "#b45a45"), (152, "#9c2b28"),
              (184, "#8c0f1b"), (216, "#690a11")],
}


def halftone_cell(tone, mode, frac_y=0.0):
    """(glyph, color) for one portrait cell, or None for background."""
    if tone <= SKIP:
        return None
    level = tone if mode == "dark" else 255 - tone
    if mode == "light" and frac_y > 0.78:
        level = min(level, 168)  # mute the clothing slab below the shoulder line
    if mode == "dark" and frac_y > 0.74:
        level = max(level, 75)  # give the garment a solid mass instead of faint mist
    idx = min(int(level / 255 * len(GLYPHS)), len(GLYPHS) - 1)
    if mode == "light":
        idx = max(idx, 3)  # keep the skin field contiguous instead of airy dots
    glyph = GLYPHS[idx]
    color = HALFTONE[mode][0][1]
    for threshold, c in HALFTONE[mode]:
        if level >= threshold:
            color = c
    return glyph, color


def fetch_stats():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    query = """
    { user(login: "%s") {
        createdAt
        followers { totalCount }
        repositories(first: 1, ownerAffiliations: OWNER) { totalCount }
        contributionsCollection {
          contributionCalendar { totalContributions }
        }
    } }""" % LOGIN
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query}).encode(),
        headers={"Authorization": f"bearer {token}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            user = json.load(r)["data"]["user"]
        created = datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
        years = (datetime.now(timezone.utc) - created).days // 365
        return {
            "repos": str(user["repositories"]["totalCount"]),
            "contribs": f'{user["contributionsCollection"]["contributionCalendar"]["totalContributions"]:,}',
            "years": str(years),
            "followers": str(user["followers"]["totalCount"]),
        }
    except Exception as e:  # offline / rate-limited: keep placeholders
        print(f"stats fetch failed ({e}); using placeholders")
        return None


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(mode, grid, stats):
    t = TOKENS[mode]
    s = stats or {k: "--" for k in ("repos", "contribs", "years", "followers")}
    W, H = 920, 568
    pad = 24

    # portrait well geometry
    cols, rows_n, tones = grid["cols"], grid["rows"], grid["tones"]
    art_fs = 6.1
    art_lh = art_fs * 1.28
    well_w = round(cols * art_fs * 0.6) + 36
    well_h = H - 2 * pad
    art_x = pad + 18
    art_y0 = pad + (well_h - rows_n * art_lh) / 2 + art_fs

    rx = pad + well_w + 26          # right column origin
    rw = W - rx - pad               # right column width

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" role="img" aria-label="Alexander Ouellet — profile card">',
        f'<title>alexander@{LOGIN}</title>',
        f'<rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="14" '
        f'fill="{t["card"]}" stroke="{t["border"]}" stroke-width="1.5"/>',
        f'<rect x="{pad}" y="{pad}" width="{well_w}" height="{well_h}" rx="10" fill="{t["well"]}"/>',
    ]

    # halftone face: per-cell glyph + color, merged into same-color tspan runs.
    # Background cells become spaces that inherit the current run so column
    # alignment is preserved.
    for i, row_tones in enumerate(tones):
        runs, cur_color, buf = [], None, ""
        for tone in row_tones:
            cell = halftone_cell(tone, mode, i / max(rows_n - 1, 1))
            glyph, color = (" ", cur_color) if cell is None else cell
            if color != cur_color:
                if buf:
                    runs.append((cur_color, buf))
                cur_color, buf = color, ""
            buf += glyph
        if buf:
            runs.append((cur_color, buf))
        if not any(txt.strip() for _, txt in runs):
            continue
        tspans = "".join(
            f'<tspan fill="{c}">{esc(txt)}</tspan>' if c else f'<tspan>{esc(txt)}</tspan>'
            for c, txt in runs)
        svg.append(f'<text x="{art_x}" y="{art_y0 + i * art_lh:.1f}" xml:space="preserve" '
                   f'{MONO} font-size="{art_fs}">{tspans}</text>')
    svg.append(f'<text x="{art_x}" y="{pad + well_h - 14}" {MONO} font-size="10" '
               f'fill="{t["dim"]}">$ ascii --halftone portrait.jpg</text>')

    y = pad + 40

    def text(x, yy, content, size, fill, weight=None, spacing=None, anchor=None):
        attrs = f'{MONO} font-size="{size}" fill="{fill}"'
        if weight:
            attrs += f' font-weight="{weight}"'
        if spacing:
            attrs += f' letter-spacing="{spacing}"'
        if anchor:
            attrs += f' text-anchor="{anchor}"'
        svg.append(f'<text x="{x}" y="{yy:.1f}" {attrs}>{content}</text>')

    # identity
    text(rx, y, "ALEXANDER OUELLET", 27, t["text"], weight=700, spacing="-0.5")
    y += 26
    text(rx, y, "AI Product Executive", 13.5, t["red"], weight=600, spacing="0.5")
    y += 14
    svg.append(f'<rect x="{rx}" y="{y}" width="56" height="3" fill="{t["brand"]}"/>')
    y += 30

    def label(name):
        nonlocal y
        text(rx, y, esc(name), 10.5, t["dim"], weight=700, spacing="2.5")
        y += 19

    def row(segs, lh=19, size=13):
        nonlocal y
        parts = ""
        for txt, c in segs:
            weight = ' font-weight="600"' if c == "text" else ""
            parts += f'<tspan fill="{t[c]}"{weight}>{esc(txt)}</tspan>'
        svg.append(f'<text x="{rx}" y="{y:.1f}" xml:space="preserve" {MONO} '
                   f'font-size="{size}">{parts}</text>')
        y += lh

    label("ROLES")
    row([("Founder @ SkillMe", "text"), (" — MCP-native Claude skills", "muted")])
    row([("Founder @ DiligenceOS", "text"), (" — due diligence pipelines", "muted")])
    row([("President @ HWPO Training", "text"), (" — Hard Work Pays Off", "muted")])
    row([("Co-founder @ Good Friends Bad Times", "text")], lh=19)
    y += 12

    label("STACK")
    row([("TypeScript · Python · Swift", "text")])
    row([("Next.js · React Native / Expo · Supabase · Vercel", "muted")])
    y += 12

    label("FOCUS")
    row([("AI product architecture · RAG / vector pipelines", "text")])
    row([("MCP servers · industrial AI", "muted")])
    y += 12

    label("SHIPPED — PRIVATE REPOS, REDACTED")
    row([("skills registry (MCP) · industrial retrieval", "muted")])
    row([("diligence extraction · training platform @ scale", "muted")])
    y += 16

    # stat chips
    chips = [(s["repos"], "REPOS"), (s["contribs"], "CONTRIB 1Y"),
             (s["years"], "YRS ON GH"), (s["followers"], "FOLLOWERS")]
    gap, ch = 10, 48
    cw = (rw - gap * (len(chips) - 1)) / len(chips)
    for i, (num, lab) in enumerate(chips):
        cx = rx + i * (cw + gap)
        svg.append(f'<rect x="{cx:.1f}" y="{y}" width="{cw:.1f}" height="{ch}" rx="8" '
                   f'fill="{t["well"]}" stroke="{t["border"]}" stroke-width="1"/>')
        text(cx + cw / 2, y + 22, esc(num), 17, t["red"], weight=700, anchor="middle")
        text(cx + cw / 2, y + 38, lab, 8.5, t["dim"], weight=700, spacing="1.5", anchor="middle")
    y += ch + 30

    row([("alexander.ouellet@icloud.com", "muted"), (" · ", "dim"),
         ("goodfriends-badtimes.com", "muted")], size=12)

    svg.append("</svg>")
    return "\n".join(svg) + "\n"


def main():
    grid = json.loads((ROOT / "assets/portrait_tones.json").read_text())
    stats = fetch_stats()
    for mode in ("dark", "light"):
        path = ROOT / f"assets/profile-{mode}.svg"
        path.write_text(build_svg(mode, grid, stats))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
