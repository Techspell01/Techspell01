#!/usr/bin/env python3
"""Draw the arcade high-score card from live GitHub data. The Action runs this daily.

    GITHUB_TOKEN=... python tools/stats.py --user Techspell01 --out dist
    python tools/stats.py --data snapshot.json --out dist      # offline, from saved API output

Standard library only. Replaces github-readme-stats, whose shared instance is
rate-limited often enough to leave a broken image on the profile.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import sys
import urllib.request
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme as th  # noqa: E402
from theme import PAL, SLOT, document, n, odometer, panel, pixels, tab, text  # noqa: E402

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
            color[name] = edge["node"]["color"] or PAL["c"]
    # Same blend github-readme-stats suggests: bytes alone let one big repo win,
    # repo count alone ignores how much code there is.
    score = {k: size[k] ** .5 * count[k] ** .5 for k in size}
    ranked = sorted(score, key=score.get, reverse=True)
    total = sum(score.values()) or 1
    langs = [{"name": k, "color": color[k], "pct": score[k] / total * 100} for k in ranked[:TOP_LANGS]]

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
        "updated": dt.date.today().strftime("%d %b %Y").upper(),
    }


def fit(s: str, size: float, max_w: float, advance: dict) -> str:
    w = lambda t: sum(advance.get(ch, .5) for ch in t) * size
    while len(s) > 3 and w(s) > max_w:
        s = s[:-2] + "."
    return s


def card_svg(s: dict, advance: dict) -> str:
    W, H = 850, 392
    top = 16
    body, css = [], []
    body.append(panel(0, top, W - 6, H - top - 6, border=PAL["b"]))
    body.append(tab(24, top, "HIGH SCORES", PAL["b"]))
    body.append(text(W - 36, top + 32, f"UPDATED {s['updated']}", "pixel", 8, PAL["l"], "end"))

    # score table
    rows = [
        ("1ST", "CONTRIBUTIONS", s["contributions"], "y"),
        ("2ND", "COMMITS", s["commits"], "c"),
        ("3RD", "PUBLIC REPOS", s["repos"], "o"),
        ("4TH", "BEST STREAK", s["longest_streak"], "b"),
        ("5TH", "STREAK NOW", s["current_streak"], "P"),
    ]
    X = 32
    body.append(text(X, 68, "RANK", "pixel", 8, PAL["l"]) + text(X + 64, 68, "NAME", "pixel", 8, PAL["l"])
                + text(410, 68, "SCORE", "pixel", 8, PAL["l"], "end"))
    for i, (rank, name, value, colour) in enumerate(rows):
        y = 102 + i * 34
        body.append(text(X, y, rank, "pixel", 16, PAL[colour]))
        body.append(text(X + 64, y, name, "pixel", 16, PAL[colour]))
        svg, c = odometer(f"r{i}", 410, y, value, 16, PAL[colour], anchor="end", delay=.2 + i * .15, pad=5)
        body.append(svg)
        css.append(c)
    body.append(pixels(th.TROPHY, X + 330, 34, 2, cls="blink"))
    body.append(f'<path class="px" d="M440 56v212" stroke="{SLOT}" stroke-width="4" stroke-dasharray="8 8"/>')

    # languages as block meters
    LX = 468
    body.append(text(LX, 68, "TOP LANGUAGES", "pixel", 8, PAL["l"]))
    k = 0
    for i, lang in enumerate(s["languages"]):
        y = 100 + i * 30
        body.append(text(LX, y + 2, fit(lang["name"], 24, 112, advance), "body", 24, PAL["w"]))
        filled = max(1, round(lang["pct"] / 5))
        for b in range(20):
            on = b < filled
            fill = lang["color"] if on else SLOT
            cls = ' class="px pop"' if on else ' class="px"'
            delay = f' style="animation-delay:{n(.4 + k * .025)}s"' if on else ""
            body.append(f'<rect{cls}{delay} x="{LX + 118 + b * 9}" y="{y - 13}" width="7" height="14" fill="{fill}"/>')
            k += on
        body.append(text(W - 36, y, f"{lang['pct']:.0f}%", "pixel", 8, PAL["c"], "end"))

    # contributions as a VU meter
    body.append(text(X, 296, "CONTRIBUTIONS · LAST 52 WEEKS", "pixel", 8, PAL["l"]))
    weeks = s["weeks"]
    peak = max(weeks + [1])
    levels = ["g", "g", "y", "y", "o", "r"]
    col_w, gap, base = 12, 3, 358
    for i, c in enumerate(weeks):
        x = X + i * (col_w + gap)
        lit = math.ceil(c / peak * 6) if c else 0
        blocks = "".join(
            f'<rect x="{x}" y="{base - (j + 1) * 7}" width="{col_w}" height="5" fill="{PAL[levels[j]]}"/>' for j in range(lit)
        ) or f'<rect x="{x}" y="{base - 7}" width="{col_w}" height="5" fill="{SLOT}"/>'
        body.append(f'<g class="px vu" style="animation-delay:{n(.5 + i * .02)}s">{blocks}</g>')
    css.append(".vu{transform-box:fill-box;transform-origin:50% 100%;animation:vu .5s steps(6) both}"
               "@keyframes vu{from{transform:scaleY(0)}}")

    faces = "\n".join(th.font_face(k, (th.FONT_DIR / f"{k}.woff").read_bytes()) for k in th.USED)
    th.USED.clear()
    desc = (f"{s['contributions']} contributions and {s['commits']} commits in the last year; "
            f"{s['repos']} public repos; best streak {s['longest_streak']} days, current {s['current_streak']}. "
            "Top languages: " + ", ".join(f"{l['name']} {l['pct']:.0f}%" for l in s["languages"]) + ".")
    return document(W, H, "High scores", desc, "\n".join(body), "\n".join(css), faces)


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
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    (out / "github-stats.svg").write_text(card_svg(stats, th.load_metrics()["body_advance"]), encoding="utf-8")
    ElementTree.parse(out / "github-stats.svg")
    print(json.dumps({k: v for k, v in stats.items() if k != "weeks"}, indent=2))


if __name__ == "__main__":
    main()
