#!/usr/bin/env python3
"""Draw the GitHub activity card from live data. The GitHub Action runs this daily.

    GITHUB_TOKEN=... python tools/stats.py --user Techspell01 --out dist
    python tools/stats.py --data snapshot.json --out dist      # offline, from saved API output

Standard library only. Replaces github-readme-stats, whose shared instance is
rate-limited often enough to leave a broken image on the profile.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme as th  # noqa: E402
from theme import THEMES, document, hue_text, n, odometer, text  # noqa: E402

# The portfolio is a single HTML file with the photo embedded as base64, so it
# would make the whole profile read as "mostly HTML". Leave it out of languages.
EXCLUDE_REPOS = {"portfolio"}
EXCLUDE_LANGS: set[str] = set()
TOP_LANGS = 6

QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch(login: str, token: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if payload.get("errors"):
        raise SystemExit(f"GitHub API error: {payload['errors']}")
    return payload["data"]["user"]


def summarise(user: dict) -> dict:
    cc = user["contributionsCollection"]
    weeks = cc["contributionCalendar"]["weeks"]
    days = [d["contributionCount"] for w in weeks for d in w["contributionDays"]]

    longest = run = 0
    for c in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days and days[-1] == 0 else days  # today isn't over yet
    for c in reversed(tail):
        if not c:
            break
        current += 1

    size: dict[str, int] = {}
    count: dict[str, int] = {}
    color: dict[str, str] = {}
    repos = user["repositories"]["nodes"]
    for repo in repos:
        if repo["name"] in EXCLUDE_REPOS or repo["name"].lower() == user["login"].lower():
            continue
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            if name in EXCLUDE_LANGS:
                continue
            size[name] = size.get(name, 0) + edge["size"]
            count[name] = count.get(name, 0) + 1
            color[name] = edge["node"]["color"] or "#8b92ad"
    # Same blend github-readme-stats suggests: bytes alone let one big repo win,
    # repo count alone ignores how much code there is.
    score = {k: size[k] ** .5 * count[k] ** .5 for k in size}
    ranked = sorted(score, key=score.get, reverse=True)
    total = sum(score.values()) or 1
    langs = [{"name": k, "color": color[k], "pct": score[k] / total * 100} for k in ranked[:TOP_LANGS]]
    rest = sum(score[k] for k in ranked[TOP_LANGS:])
    if rest:
        langs.append({"name": "Other", "color": "#8b92ad", "pct": rest / total * 100})

    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "followers": user["followers"]["totalCount"],
        "current_streak": current,
        "longest_streak": longest,
        "weeks": [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks][-52:],
        "languages": langs,
        "updated": dt.date.today().strftime("%d %b %Y"),
    }


def card_svg(s: dict, theme: str, digits: list[float]) -> str:
    t = THEMES[theme]
    W, H = 850, 304
    X = 30
    body, css = [], []
    body.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="20" fill="{t["card"]}" stroke="{t["line"]}"/>')
    body.append(text(X, 44, "GITHUB ACTIVITY · LAST 12 MONTHS", "mono", 11, t["muted"], ls=1.4))
    body.append(text(W - X, 44, f"updated {s['updated']}", "mono", 10, t["muted"], "end"))

    metrics = [
        (s["contributions"], "", "CONTRIBUTIONS", "teal"),
        (s["commits"], "", "COMMITS", "saffron"),
        (s["current_streak"], "day" if s["current_streak"] == 1 else "days", f"STREAK · BEST {s['longest_streak']}", "rose"),
        (s["repos"], "", f"PUBLIC REPOS · {s['stars']} STAR{'' if s['stars'] == 1 else 'S'}", "violet"),
    ]
    size = 38
    for i, (value, suffix, label, hname) in enumerate(metrics):
        x = X + (i % 2) * 180
        y = 106 + (i // 2) * 70
        svg, c = odometer(f"m{i}", x - 1, y, value, size, hue_text(hname, t), digits, delay=.2 + i * .1)
        body.append(svg)
        css.append(c)
        if suffix:
            body.append(text(x + th.number_width(value, size, digits) + 6, y, suffix, "semi", 14, t["muted"]))
        body.append(text(x, y + 20, label, "mono", 10, t["ink2"], ls=1))
    body.append(f'<line x1="400" y1="68" x2="400" y2="196" stroke="{t["line"]}"/>')

    # languages: stacked bar + legend
    lx, lw = 430, W - X - 430
    body.append(text(lx, 84, "TOP LANGUAGES", "mono", 10, t["ink2"], ls=1))
    body.append(f'<defs><clipPath id="bar"><rect x="{lx}" y="98" width="{lw}" height="10" rx="5"/></clipPath></defs>'
                f'<rect x="{lx}" y="98" width="{lw}" height="10" rx="5" fill="{t["line"]}"/>')
    segs, x = [], lx
    for i, lang in enumerate(s["languages"]):
        w = lw * lang["pct"] / 100
        segs.append(f'<rect class="seg" style="animation-delay:{n(.3 + i * .12)}s" x="{n(x)}" y="98" width="{n(w + .6)}" height="10" fill="{lang["color"]}"/>')
        x += w
    body.append(f'<g clip-path="url(#bar)">{"".join(segs)}</g>')
    col_w = (lw - 30) / 2
    for i, lang in enumerate(s["languages"][:8]):
        cx = lx + (i % 2) * (col_w + 30)
        cy = 138 + (i // 2) * 26
        body.append(f'<circle cx="{n(cx + 5)}" cy="{n(cy - 4)}" r="4.5" fill="{lang["color"]}"/>')
        body.append(text(cx + 17, cy, lang["name"], "semi", 13, t["ink"]))
        body.append(text(cx + col_w, cy, f"{lang['pct']:.1f}%", "mono", 11, t["muted"], "end"))

    # contributions per week
    body.append(text(X, 232, "CONTRIBUTIONS PER WEEK", "mono", 10, t["muted"], ls=1))
    weeks = s["weeks"]
    top = max(weeks + [1])
    bw_total, gap, base, bh = W - X * 2, 3, 284, 38
    bw = (bw_total - gap * (len(weeks) - 1)) / max(len(weeks), 1)
    for i, c in enumerate(weeks):
        h = max(3, bh * c / top) if c else 3
        fill = t["accent"] if c else t["line"]
        op = .35 + .65 * c / top if c else 1
        body.append(f'<rect class="bar" style="animation-delay:{n(.4 + i * .016)}s" x="{n(X + i * (bw + gap))}" y="{n(base - h)}" '
                    f'width="{n(bw)}" height="{n(h)}" rx="2" fill="{fill}" fill-opacity="{n(op)}"/>')

    css.append(".seg{transform-box:fill-box;transform-origin:0 50%;animation:gx .9s cubic-bezier(.2,.8,.3,1) both}"
               "@keyframes gx{from{transform:scaleX(0)}}"
               ".bar{transform-box:fill-box;transform-origin:50% 100%;animation:gy .8s cubic-bezier(.2,.8,.3,1) both}"
               "@keyframes gy{from{transform:scaleY(0)}}")

    faces = "\n".join(th.font_face(k, (th.FONT_DIR / f"{k}.woff").read_bytes()) for k in th.USED)
    th.USED.clear()
    desc = (f"{s['contributions']} contributions and {s['commits']} commits in the last year; "
            f"current streak {s['current_streak']} days (best {s['longest_streak']}); {s['repos']} public repos. "
            "Top languages: " + ", ".join(f"{l['name']} {l['pct']:.0f}%" for l in s["languages"]) + ".")
    return document(W, H, "GitHub activity", desc, "\n".join(body), "\n".join(css), faces)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_REPOSITORY_OWNER"))
    ap.add_argument("--data", help="saved GraphQL `user` object, instead of calling the API")
    ap.add_argument("--out", default="dist")
    args = ap.parse_args()

    if args.data:
        user = json.loads(Path(args.data).read_text(encoding="utf-8"))
    else:
        token = os.environ.get("GITHUB_TOKEN")
        if not (args.user and token):
            raise SystemExit("need --user and GITHUB_TOKEN (or --data)")
        user = fetch(args.user, token)

    stats = summarise(user)
    digits = th.load_metrics()["display_digits"]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    for theme in THEMES:
        (out / f"github-stats-{theme}.svg").write_text(card_svg(stats, theme, digits), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "weeks"}, indent=2))


if __name__ == "__main__":
    main()
