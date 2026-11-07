#!/usr/bin/env python3
"""Refresh the live streak section inside assets/profile.svg.

Usage:  python scripts/update_profile.py assets/profile.svg sushmitahonagekar
Needs only the Python standard library. Reads your PUBLIC contribution
calendar from GitHub, so no token is required.
"""
import re, sys, datetime as dt, urllib.request

FONT = "'DejaVu Sans Mono',Consolas,Menlo,'Courier New',monospace"
RED, VIO, WHT, DIM = "#ff2b4d", "#8b5cf6", "#f4f0ff", "#8f86ad"
LEVELS = ["#261a3c", "#4b2a85", "#8b5cf6", "#ff5c7a", "#ff2b4d"]


def fetch_days(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    id_to_date = {i: d for d, i in re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="(contribution-day-component-\d+-\d+)"', html)}
    days = {}
    for i, txt in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', html):
        if i in id_to_date:
            m = re.match(r"(\d+) contribution", txt.strip())
            days[id_to_date[i]] = int(m.group(1)) if m else 0
    return sorted((dt.date.fromisoformat(d), c) for d, c in days.items())


def stats(days):
    total = sum(c for _, c in days)
    longest = (0, None, None); run = 0; start = None
    for d, c in days:
        if c > 0:
            if run == 0: start = d
            run += 1
            if run > longest[0]: longest = (run, start, d)
        else:
            run = 0
    # current streak: ends today, or yesterday if today has nothing yet
    idx = len(days) - 1
    if idx >= 0 and days[idx][1] == 0: idx -= 1
    cur = 0; cend = days[idx][0] if idx >= 0 else None; cstart = cend
    while idx >= 0 and days[idx][1] > 0:
        cur += 1; cstart = days[idx][0]; idx -= 1
    return total, (cur, cstart, cend if cur else None), longest


def fmt(a, b):
    if not a: return "no streak yet"
    f = lambda d: f"{d.strftime('%b')} {d.day}"
    return f(a) if a == b else f"{f(a)} - {f(b)}"


def level(c):
    return 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 9 else 4


def streak_markup(days):
    total, (cur, cs, ce), (lo, ls, le) = stats(days) if days else (0, (0, None, None), (0, None, None))
    rng = f"{days[0][0].strftime('%b')} {days[0][0].day}, {days[0][0].year} - Present" if days else ""
    def txt(x, y, s, size, fill, weight=400, glow=False):
        g = ' filter="url(#glow)"' if glow else ""
        return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{FONT}" font-size="{size}" '
                f'font-weight="{weight}" fill="{fill}"{g}>{s}</text>')
    o = ""
    o += txt(200, 262, total, 52, WHT, 700, True) + txt(200, 312, "Total Contributions", 15, RED) + txt(200, 336, rng, 12, DIM)
    o += (f'<circle cx="500" cy="243" r="56" fill="none" stroke="#2a1650" stroke-width="5"/>'
          f'<circle cx="500" cy="243" r="56" fill="none" stroke="{RED}" stroke-width="5" stroke-linecap="round" '
          f'stroke-dasharray="240 112" filter="url(#glow)"><animateTransform attributeName="transform" type="rotate" '
          f'from="0 500 243" to="360 500 243" dur="6s" repeatCount="indefinite"/></circle>')
    o += txt(500, 262, cur, 52, WHT, 700, True) + txt(500, 312, "Current Streak", 15, "#ffb340", 700) + txt(500, 336, fmt(cs, ce), 12, DIM)
    o += txt(800, 262, lo, 52, WHT, 700, True) + txt(800, 312, "Longest Streak", 15, RED) + txt(800, 336, fmt(ls, le), 12, DIM)
    return o


def update(svg_path, user):
    days = fetch_days(user)
    svg = open(svg_path, encoding="utf-8").read()
    new = re.sub(r"(<!--STREAK_START-->).*?(<!--STREAK_END-->)",
                 lambda m: m.group(1) + streak_markup(days) + m.group(2), svg, flags=re.S)
    open(svg_path, "w", encoding="utf-8").write(new)
    print(f"updated {svg_path}: {len(days)} days, total {sum(c for _, c in days)}")


if __name__ == "__main__":
    update(sys.argv[1] if len(sys.argv) > 1 else "assets/profile.svg",
           sys.argv[2] if len(sys.argv) > 2 else "sushmitahonagekar")
