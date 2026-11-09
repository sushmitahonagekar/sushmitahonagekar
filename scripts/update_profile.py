#!/usr/bin/env python3
"""Refresh the live streak numbers inside assets/profile.svg.

Usage:  python scripts/update_profile.py assets/profile.svg sushmitahonagekar

Set the environment variable GH_TOKEN to a GitHub token (classic, scope
`read:user`). With a token the numbers match your real profile, including
private contributions. Without one, only PUBLIC contributions are counted.
Standard library only.
"""
import json, os, re, sys, datetime as dt, urllib.request

FONT = "'DejaVu Sans Mono',Consolas,Menlo,'Courier New',monospace"
RED, WHT, DIM = "#ff2b4d", "#f4f0ff", "#8f86ad"


# ---------------------------------------------------------------- data
def graphql(token, query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-streak"})
    data = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_with_token(user, token):
    """All-time daily counts (public + private) using the GraphQL API."""
    q0 = "query($l:String!){user(login:$l){createdAt}}"
    created = dt.datetime.fromisoformat(
        graphql(token, q0, {"l": user})["user"]["createdAt"].replace("Z", "+00:00")).date()
    q = """query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){
      contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    today = dt.datetime.now(dt.timezone.utc).date()
    days, start = {}, created
    while start <= today:
        end = min(start + dt.timedelta(days=364), today)
        d = graphql(token, q, {"l": user, "f": f"{start}T00:00:00Z", "t": f"{end}T23:59:59Z"})
        for w in d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for x in w["contributionDays"]:
                days[x["date"]] = x["contributionCount"]
        start = end + dt.timedelta(days=1)
    return sorted((dt.date.fromisoformat(k), v) for k, v in days.items() if dt.date.fromisoformat(k) <= today), created


def fetch_public(user):
    """Public-only fallback (last 12 months). Private work is NOT included."""
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                 headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    id_to_date = {i: d for d, i in re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="(contribution-day-component-\d+-\d+)"', html)}
    days = {}
    for i, txt in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>', html):
        if i in id_to_date:
            m = re.match(r"(\d+) contribution", txt.strip())
            days[id_to_date[i]] = int(m.group(1)) if m else 0
    today = dt.datetime.now(dt.timezone.utc).date()
    out = sorted((dt.date.fromisoformat(d), c) for d, c in days.items() if dt.date.fromisoformat(d) <= today)
    return out, (out[0][0] if out else today)


# ---------------------------------------------------------------- maths
def compute(days):
    total = sum(c for _, c in days)
    best = (0, None, None); run = 0; start = None
    for d, c in days:
        if c > 0:
            if run == 0: start = d
            run += 1
            if run > best[0]: best = (run, start, d)
        else:
            run = 0
    idx = len(days) - 1
    if idx >= 0 and days[idx][1] == 0:      # today still empty -> streak may end yesterday
        idx -= 1
    cur, cs, ce = 0, None, None
    if idx >= 0 and days[idx][1] > 0:
        ce = days[idx][0]
        while idx >= 0 and days[idx][1] > 0:
            cur += 1; cs = days[idx][0]; idx -= 1
        # a streak that ended before yesterday is over
        today = dt.datetime.now(dt.timezone.utc).date()
        if (today - ce).days > 1:
            cur, cs, ce = 0, None, None
    return total, (cur, cs, ce), best


def fmt(a, b):
    if not a: return "no streak yet"
    f = lambda d: f"{d.strftime('%b')} {d.day}"
    return f(a) if a == b else f"{f(a)} - {f(b)}"


# ---------------------------------------------------------------- svg
def render(total, cur, cur_rng, longest, long_rng, rng):
    def t(x, y, s, size, fill, weight=400, glow=False):
        g = ' filter="url(#glow)"' if glow else ""
        return (f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{FONT}" font-size="{size}" '
                f'font-weight="{weight}" fill="{fill}"{g}>{s}</text>')
    o = t(200, 262, total, 52, WHT, 700, True) + t(200, 312, "Total Contributions", 15, RED) + t(200, 336, rng, 12, DIM)
    o += ('<circle cx="500" cy="243" r="56" fill="none" stroke="#2a1650" stroke-width="5"/>'
          f'<circle cx="500" cy="243" r="56" fill="none" stroke="{RED}" stroke-width="5" stroke-linecap="round" '
          'stroke-dasharray="240 112" filter="url(#glow)"><animateTransform attributeName="transform" type="rotate" '
          'from="0 500 243" to="360 500 243" dur="6s" repeatCount="indefinite"/></circle>')
    o += t(500, 262, cur, 52, WHT, 700, True) + t(500, 312, "Current Streak", 15, "#ffb340", 700) + t(500, 336, cur_rng, 12, DIM)
    o += t(800, 262, longest, 52, WHT, 700, True) + t(800, 312, "Longest Streak", 15, RED) + t(800, 336, long_rng, 12, DIM)
    return o


def render_placeholder():
    return render("--", "--", "updates automatically", "--", "updates automatically", "all time")


def update(svg_path, user):
    token = os.environ.get("GH_TOKEN", "").strip()
    if token:
        days, created = fetch_with_token(user, token); src = "token (public + private)"
    else:
        if os.environ.get("REQUIRE_TOKEN") == "1":
            sys.exit("ERROR: secret PROFILE_TOKEN is missing - see the setup steps.")
        days, created = fetch_public(user); src = "public only"
    total, (cur, cs, ce), (lo, ls, le) = compute(days)
    rng = f"{created.strftime('%b')} {created.day}, {created.year} - Present"
    svg = open(svg_path, encoding="utf-8").read()
    new = re.sub(r"(<!--STREAK_START-->).*?(<!--STREAK_END-->)",
                 lambda m: m.group(1) + render(total, cur, fmt(cs, ce), lo, fmt(ls, le), rng) + m.group(2),
                 svg, flags=re.S)
    open(svg_path, "w", encoding="utf-8").write(new)
    print(f"[{src}] total={total} current={cur} longest={lo}")


if __name__ == "__main__":
    update(sys.argv[1] if len(sys.argv) > 1 else "assets/profile.svg",
           sys.argv[2] if len(sys.argv) > 2 else "sushmitahonagekar")
