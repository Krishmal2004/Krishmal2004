"""Generate terminal-styled profile cards (stats, activity, achievements) into assets/.

Uses only the Python standard library. Set GITHUB_TOKEN for higher API rate limits.
"""
import datetime as dt
import html
import json
import os
import re
import urllib.request

USER = os.environ.get("GH_USER", "Krishmal2004")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

FONT = "Consolas, 'SF Mono', Menlo, 'DejaVu Sans Mono', 'Courier New', monospace"
G, TXT, MUTED, BG, BAR, BORDER = "#00ff9c", "#c9d1d9", "#8b949e", "#0d1117", "#161b22", "#30363d"
LANG_COLORS = {
    "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5", "Go": "#00ADD8",
    "Java": "#b07219", "Rust": "#dea584", "C#": "#178600", "C++": "#f34b7d", "C": "#555555",
    "Dart": "#00B4AB", "HTML": "#e34c26", "CSS": "#663399", "Kotlin": "#A97BFF", "Swift": "#F05138",
    "Shell": "#89e051", "PLpgSQL": "#336790",
}
EXCLUDED_LANGS = {"Jupyter Notebook"}  # notebook JSON bytes would dwarf real code
esc = html.escape


def get(url, raw=False):
    headers = {"User-Agent": "profile-stats", "Accept": "application/vnd.github+json"}
    if TOKEN and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        body = r.read().decode("utf-8")
    return body if raw else json.loads(body)


def search_count(q):
    return get(f"https://api.github.com/search/issues?per_page=1&q={urllib.request.quote(q)}")["total_count"]


def contributions():
    page = get(f"https://github.com/users/{USER}/contributions", raw=True)
    dates = dict(re.findall(r'data-date="(\d{4}-\d\d-\d\d)" id="([^"]+)"', page))
    dates = {v: k for k, v in dates.items()}
    days = {}
    for cid, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', page):
        if cid in dates:
            m = re.match(r"(\d+) contribution", text)
            days[dates[cid]] = int(m.group(1)) if m else 0
    return sorted(days.items())


def streaks(days):
    counts = [c for _, c in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current, i = 0, len(counts) - 1
    if i >= 0 and counts[i] == 0:  # today not counted yet
        i -= 1
    while i >= 0 and counts[i]:
        current, i = current + 1, i - 1
    return current, longest


def window(w, h, title):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>
  text {{ font-family: {FONT}; }}
  .f {{ opacity: 0; animation: in .4s ease-out forwards; }}
  .grow {{ transform-box: fill-box; transform-origin: bottom; transform: scaleY(0); animation: grow .6s ease-out forwards; }}
  .fill {{ transform: scaleX(0); animation: fill .9s ease-out forwards; }}
  @keyframes in {{ to {{ opacity: 1; }} }}
  @keyframes grow {{ to {{ transform: scaleY(1); }} }}
  @keyframes fill {{ to {{ transform: scaleX(1); }} }}
</style>
<defs><filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="12" fill="{BG}" stroke="{G}" stroke-opacity=".45"/>
<path d="M1 13a12 12 0 0 1 12-12h{w-26}a12 12 0 0 1 12 12v21H1z" fill="{BAR}"/>
<circle cx="22" cy="18" r="6" fill="#ff5f56"/><circle cx="42" cy="18" r="6" fill="#ffbd2e"/><circle cx="62" cy="18" r="6" fill="#27c93f"/>
<text x="{w/2}" y="23" text-anchor="middle" font-size="12" fill="{MUTED}">{esc(title)}</text>
'''


def prompt(x, y, cmd):
    return (f'<text x="{x}" y="{y}" font-size="14"><tspan fill="{G}">krishmal@github</tspan><tspan fill="{TXT}">:</tspan>'
            f'<tspan fill="#58a6ff">~</tspan><tspan fill="{TXT}">$ {esc(cmd)}</tspan></text>\n')


def stats_card(s, langs, updated):
    w, h = 900, 330
    out = [window(w, h, "stats — zsh"), prompt(24, 62, f"gh stats --user {USER.lower()} --langs")]
    rows = [
        ("contributions", f"{s['year']:,}", "last 12 months"),
        ("current streak", f"{s['current']} days", ""),
        ("longest streak", f"{s['longest']} days", ""),
        ("public repos", f"{s['repos']}", f"{s['own']} own · {s['repos'] - s['own']} forks"),
        ("stars earned", f"{s['stars']}", ""),
        ("pull requests", f"{s['prs']}", "total opened"),
        ("oss PRs merged", f"{s['oss']}", "to other repos"),
        ("followers", f"{s['followers']}", ""),
    ]
    for i, (k, v, note) in enumerate(rows):
        y = 100 + i * 25
        out.append(f'<text class="f" style="animation-delay:{.2 + i * .08:.2f}s" x="24" y="{y}" font-size="14" xml:space="preserve">'
                   f'<tspan fill="{G}">›</tspan><tspan fill="{MUTED}"> {k:<15}</tspan><tspan fill="{TXT}" font-weight="bold">{esc(v):<10}</tspan>'
                   f'<tspan fill="#484f58"> {esc(note)}</tspan></text>\n')
    out.append(f'<line x1="470" y1="46" x2="470" y2="{h - 20}" stroke="{BORDER}"/>\n')
    out.append(f'<text x="494" y="100" font-size="13" fill="{MUTED}"># top languages (bytes, own repos)</text>\n')
    total = sum(b for _, b in langs) or 1
    for i, (name, b) in enumerate(langs[:7]):
        y, pct = 128 + i * 26, b / total * 100
        col = LANG_COLORS.get(name, G)
        out.append(f'<g class="f" style="animation-delay:{.4 + i * .08:.2f}s">'
                   f'<text x="494" y="{y}" font-size="13" fill="{TXT}">{esc(name)}</text>'
                   f'<rect x="604" y="{y - 11}" width="200" height="12" rx="2" fill="{BAR}" stroke="{BORDER}"/>'
                   f'<rect class="fill" style="animation-delay:{.5 + i * .08:.2f}s" x="604" y="{y - 11}" width="{max(pct * 2, 2):.1f}" height="12" rx="2" fill="{col}"/>'
                   f'<text x="876" y="{y}" font-size="13" fill="{MUTED}" text-anchor="end">{pct:4.1f}%</text></g>\n')
    out.append(f'<text x="{w - 24}" y="{h - 14}" font-size="11" fill="#484f58" text-anchor="end">updated {updated} · auto-generated by GitHub Actions</text>\n</svg>\n')
    return "".join(out)


def activity_card(days, updated):
    w, h, n = 900, 280, 60
    recent = days[-n:]
    peak = max([c for _, c in recent] + [1])
    out = [window(w, h, "activity — zsh"), prompt(24, 62, f"contributions --graph --days {n}")]
    x0, y0, gw, gh = 60, 225, 810, 140
    for f in (0, .25, .5, .75, 1):
        y = y0 - gh * f
        out.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0 + gw}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="{"0" if f == 0 else "3 4"}"/>'
                   f'<text x="{x0 - 10}" y="{y + 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{round(peak * f)}</text>\n')
    step = gw / n
    pts = []
    for i, (d, c) in enumerate(recent):
        bh = gh * c / peak
        x = x0 + i * step
        pts.append((x + step / 2, y0 - bh))
        if c:
            out.append(f'<rect class="grow" style="animation-delay:{i * .015:.2f}s" x="{x + 2:.1f}" y="{y0 - bh:.1f}" width="{step - 4:.1f}" height="{bh:.1f}" rx="2" fill="{G}" fill-opacity="{.35 + .65 * c / peak:.2f}"/>\n')
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    out.append(f'<polyline class="f" style="animation-delay:1.1s" points="{line}" fill="none" stroke="{G}" stroke-width="1.5" filter="url(#glow)"/>\n')
    total = sum(c for _, c in recent)
    out.append(f'<text x="{x0}" y="{y0 + 20}" font-size="11" fill="{MUTED}">{recent[0][0]}</text>'
               f'<text x="{x0 + gw}" y="{y0 + 20}" font-size="11" fill="{MUTED}" text-anchor="end">{recent[-1][0]}</text>'
               f'<text x="{w / 2}" y="{y0 + 20}" font-size="12" fill="{TXT}" text-anchor="middle">{total} contributions · peak {peak}/day</text>\n'
               f'<text x="{w - 24}" y="{h - 12}" font-size="11" fill="#484f58" text-anchor="end">updated {updated}</text>\n</svg>\n')
    return "".join(out)


def rank(v, tiers):
    for letter, t in zip("SABC", tiers):
        if v >= t:
            return letter
    return "D"


def achievements_card(s):
    ranks = {"S": "#ffd700", "A": G, "B": "#58a6ff", "C": "#bc8cff", "D": MUTED}
    items = [
        ("⚡", "Commits", s["year"], (1000, 500, 200, 50), "contribs / yr"),
        ("⇄", "Open Source", s["oss"], (100, 40, 10, 1), "PRs merged"),
        ("◆", "Repos", s["repos"], (100, 50, 20, 5), "public"),
        ("▲", "Streak", s["longest"], (100, 30, 14, 7), "days max"),
        ("★", "Stars", s["stars"], (100, 30, 10, 1), "earned"),
        ("☍", "Followers", s["followers"], (100, 50, 10, 1), "people"),
    ]
    w, h = 900, 230
    out = [window(w, h, "achievements — zsh"), prompt(24, 62, "achievements --list")]
    tw = 136
    for i, (icon, name, val, tiers, unit) in enumerate(items):
        r = rank(val, tiers)
        c = ranks[r]
        x = 24 + i * (tw + 6)
        out.append(f'<g class="f" style="animation-delay:{.2 + i * .12:.2f}s">'
                   f'<rect x="{x}" y="80" width="{tw}" height="128" rx="8" fill="{BAR}" stroke="{c}" stroke-opacity=".55"/>'
                   f'<text x="{x + 14}" y="104" font-size="16" fill="{c}">{icon}</text>'
                   f'<text x="{x + tw - 14}" y="112" font-size="34" font-weight="bold" fill="{c}" text-anchor="end" filter="url(#glow)">{r}</text>'
                   f'<text x="{x + 14}" y="150" font-size="14" fill="{TXT}" font-weight="bold">{name}</text>'
                   f'<text x="{x + 14}" y="176" font-size="20" fill="{c}">{val:,}</text>'
                   f'<text x="{x + 14}" y="196" font-size="11" fill="{MUTED}">{unit}</text></g>\n')
    out.append("</svg>\n")
    return "".join(out)


def main():
    user = get(f"https://api.github.com/users/{USER}")
    repos = get(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    own = [r for r in repos if not r["fork"]]
    lang_bytes = {}
    for r in own:
        for name, b in get(r["languages_url"]).items():
            if name not in EXCLUDED_LANGS:
                lang_bytes[name] = lang_bytes.get(name, 0) + b
    langs = sorted(lang_bytes.items(), key=lambda kv: -kv[1])
    days = contributions()
    current, longest = streaks(days)
    s = {
        "year": sum(c for _, c in days), "current": current, "longest": longest,
        "repos": user["public_repos"], "own": len(own), "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in own),
        "prs": search_count(f"author:{USER} type:pr"),
        "oss": search_count(f"author:{USER} type:pr is:merged -user:{USER}"),
    }
    updated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(OUT, exist_ok=True)
    for name, svg in (("stats.svg", stats_card(s, langs, updated)),
                      ("activity.svg", activity_card(days, updated)),
                      ("achievements.svg", achievements_card(s))):
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
            f.write(svg)
    print(json.dumps(s), langs[:7])


if __name__ == "__main__":
    main()
