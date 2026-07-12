#!/usr/bin/env python3
"""Generate assets/profile-dark.svg and assets/profile-light.svg.

Layout: ASCII portrait (assets/portrait_ascii.txt) on the left, a dotted-leader
spec sheet on the right, GFBT palette (near-black / bone / blood red).

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
WIDTH_CHARS = 66  # right-column line width in characters

PALETTES = {
    "dark": {
        "card": "#0d0c0c", "border": "#2b1519", "text": "#e8e4da",
        "dim": "#6f6a60", "red": "#e5484d", "portrait": "#e8e4da",
    },
    "light": {
        "card": "#faf8f3", "border": "#e2dbcd", "text": "#1b1815",
        "dim": "#9a927f", "red": "#a4111f", "portrait": "#2a2622",
    },
}


def fetch_stats():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    query = """
    { user(login: "%s") {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER) {
          totalCount nodes { stargazerCount }
        }
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
            "years": str(years),
            "repos": str(user["repositories"]["totalCount"]),
            "stars": str(sum(n["stargazerCount"] for n in user["repositories"]["nodes"])),
            "followers": str(user["followers"]["totalCount"]),
            "contribs": f'{user["contributionsCollection"]["contributionCalendar"]["totalContributions"]:,}',
        }
    except Exception as e:  # offline / rate-limited: keep placeholders
        print(f"stats fetch failed ({e}); using placeholders")
        return None


def content(stats):
    s = stats or {k: "--" for k in ("years", "repos", "stars", "followers", "contribs")}
    kv, sect, blank = "kv", "sect", "blank"
    return [
        ("head", None, None),
        (kv, "Host", [("AI Product / Systems Builder", "text")]),
        (kv, "Uptime", [(f'{s["years"]} yrs shipping on GitHub', "text")]),
        (blank, None, None),
        (sect, "Roles", None),
        (kv, "Founder", [("SkillMe", "red"), (" — MCP-native Claude skills catalog", "text")]),
        (kv, "Founder", [("DiligenceOS", "red"), (" — due diligence as a pipeline", "text")]),
        (kv, "President", [("HWPO Training", "red"), (" — Hard Work Pays Off", "text")]),
        (kv, "Co-founder", [("Good Friends Bad Times", "red")]),
        (blank, None, None),
        (sect, "Stack", None),
        (kv, "Languages", [("TypeScript · Python · Swift", "text")]),
        (kv, "Frameworks", [("Next.js · React Native / Expo", "text")]),
        (kv, "Infra", [("Supabase · Vercel · MCP servers", "text")]),
        (kv, "Focus", [("AI architecture · RAG pipelines · industrial AI", "text")]),
        (kv, "Training", [("CrossFit", "text")]),
        (blank, None, None),
        (sect, "Shipped — private repos, redacted", None),
        (kv, "mcp", [("skills registry — agents install their own tools", "text")]),
        (kv, "rag", [("industrial retrieval — docs + telemetry answers", "text")]),
        (kv, "diligence", [("extraction — documents in, decisions out", "text")]),
        (kv, "mobile", [("training platform at brand scale", "text")]),
        (blank, None, None),
        (sect, "Contact", None),
        (kv, "Email", [("alexander.ouellet@icloud.com", "text")]),
        (kv, "Web", [("goodfriends-badtimes.com", "text")]),
        (blank, None, None),
        (sect, "GitHub", None),
        (kv, "Repos / Stars", [(f'{s["repos"]}', "red"), (" / ", "dim"), (f'{s["stars"]}', "red")]),
        (kv, "Followers / Contributions [1y]",
         [(f'{s["followers"]}', "red"), (" / ", "dim"), (f'{s["contribs"]}', "red")]),
    ]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_svg(palette, ascii_lines, rows):
    p = PALETTES[palette]
    fs_info, lh_info = 13, 13.8
    fs_art, lh_art = 11, 14.6
    x_art, x_info = 30, 372
    y0 = 42
    height = max(y0 + len(rows) * lh_info, y0 + len(ascii_lines) * lh_art) + 26
    width = 920
    mono = ("font-family=\"'JetBrains Mono','SFMono-Regular',Menlo,Consolas,"
            "'DejaVu Sans Mono','Liberation Mono',monospace\"")

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="0 0 {width} {height:.0f}" role="img" aria-label="Alexander Ouellet — profile card">',
        f'<title>alexander@{LOGIN}</title>',
        f'<rect x="1.5" y="1.5" width="{width - 3}" height="{height - 3:.0f}" rx="12" '
        f'fill="{p["card"]}" stroke="{p["border"]}" stroke-width="1.5"/>',
    ]

    # left column: ascii portrait
    for i, line in enumerate(ascii_lines):
        if not line.strip():
            continue
        out.append(
            f'<text x="{x_art}" y="{y0 + 6 + i * lh_art:.1f}" xml:space="preserve" {mono} '
            f'font-size="{fs_art}" fill="{p["portrait"]}" opacity="0.92">{esc(line)}</text>'
        )

    # right column: spec sheet
    info_w = 920 - x_info - 30
    for i, (kind, key, value) in enumerate(rows):
        y = y0 + 10 + i * lh_info
        if kind == "blank":
            continue
        if kind == "head":
            out.append(
                f'<text x="{x_info}" y="{y:.1f}" {mono} font-size="14" font-weight="bold">'
                f'<tspan fill="{p["text"]}">alexander</tspan><tspan fill="{p["red"]}">@</tspan>'
                f'<tspan fill="{p["text"]}">{LOGIN}</tspan></text>'
            )
            out.append(f'<line x1="{x_info + 172}" y1="{y - 4:.1f}" x2="{x_info + info_w}" '
                       f'y2="{y - 4:.1f}" stroke="{p["border"]}" stroke-width="1"/>')
            continue
        if kind == "sect":
            label = esc(key)
            out.append(
                f'<text x="{x_info}" y="{y:.1f}" {mono} font-size="{fs_info}" font-weight="bold" '
                f'fill="{p["red"]}">- {label}</text>'
            )
            rule_x = x_info + (len(key) + 3) * 7.9
            out.append(f'<line x1="{rule_x:.0f}" y1="{y - 4:.1f}" x2="{x_info + info_w}" '
                       f'y2="{y - 4:.1f}" stroke="{p["border"]}" stroke-width="1"/>')
            continue
        # kv line with dotted leader; value right-aligned to a fixed char width
        val_len = sum(len(t) for t, _ in value)
        dots = WIDTH_CHARS - len(key) - val_len - 5
        dots = max(dots, 2)
        tspans = (
            f'<tspan fill="{p["dim"]}">. </tspan>'
            f'<tspan fill="{p["text"]}">{esc(key)}:</tspan>'
            f'<tspan fill="{p["dim"]}"> {"." * dots} </tspan>'
        )
        for t, role in value:
            tspans += f'<tspan fill="{p[role if role != "text" else "text"]}">{esc(t)}</tspan>'
        out.append(f'<text x="{x_info}" y="{y:.1f}" xml:space="preserve" {mono} '
                   f'font-size="{fs_info}">{tspans}</text>')

    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ascii_lines = (ROOT / "assets/portrait_ascii.txt").read_text().splitlines()
    rows = content(fetch_stats())
    for palette in ("dark", "light"):
        path = ROOT / f"assets/profile-{palette}.svg"
        path.write_text(build_svg(palette, ascii_lines, rows))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
