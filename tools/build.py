#!/usr/bin/env python3
"""Builds the profile: one screen with a fan of cards, and a page for each card.

    pip install fonttools
    python tools/build.py

A README can't run scripts, so a card can't open in place. Instead the fan is
drawn once and cut into vertical strips, one per card, and each strip links to
cards/<slug>.md. That page opens on an SVG of the same card flying out of the
fan and flipping over to show its details. Clicking it goes back to the profile.

What the cards say lives in CARDS and the back_* functions. Edit, rerun, commit
README.md, cards/ and assets/.
"""
from __future__ import annotations

import base64
import io
import math
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "tools" / "fonts"
ASSETS = ROOT / "assets"
PAGES = ROOT / "cards"

USER = "Techspell01"
RAW = f"https://raw.githubusercontent.com/{USER}/{USER}/main"
BLOB = f"https://github.com/{USER}/{USER}/blob/main"
PROFILE = f"https://github.com/{USER}"
PORTFOLIO = "https://techspell01.github.io/portfolio/"
RESUME = PORTFOLIO + "Harinand-AS-Resume.pdf"
LINKEDIN = "https://www.linkedin.com/in/harinand-as/"
EMAIL = "harinand200406@gmail.com"

# =====================================================================
# CARDS, left to right across the fan. The middle one sits in front.
# =====================================================================
CARDS = [
    {"slug": "contact", "title": "Contact", "caption": "say hi", "accent": "#ff6b6b", "icon": "plane"},
    {"slug": "skills", "title": "Skills", "caption": "the toolbox", "accent": "#ff9f43", "icon": "code"},
    {"slug": "internships", "title": "Internships", "caption": "two in 2026", "accent": "#f2bf3a", "icon": "briefcase"},
    {"slug": "about", "title": "About me", "caption": "start here", "accent": "#ff7a59", "icon": None},
    {"slug": "projects", "title": "Projects", "caption": "6 shipped", "accent": "#2fc4a5", "icon": "layers"},
    {"slug": "education", "title": "Education", "caption": "B.Tech · 2027", "accent": "#4d9bff", "icon": "cap"},
    {"slug": "journey", "title": "Journey", "caption": "2024 → now", "accent": "#a47bff", "icon": "path"},
]
MID = len(CARDS) // 2

NAME = "Harinand AS"
EYEBROW = "PRODUCT ENGINEER · KOCHI, KERALA"
TAGLINE = "I take half-formed ideas and push them until they have a URL."
HINT = "pick a card ↓"

# =====================================================================
# Colours and geometry
# =====================================================================
INK, INK2 = "#0f1020", "#1d1736"
CREAM = "#fbf6ee"
TXT, TXT2, MUTED = "#1d1b2c", "#4a475c", "#8a8799"

W, H = 1200, 680  # the screen
TOP = 250  # title band; the fan lives below it
CW, CH = 230, 410  # a card at scale 1

# The cards fan out from a pivot below the screen, so the bottom edge cuts them off.
# k = steps from the middle: (tilt in degrees, how much lower its top sits, scale)
PIVOT = (W / 2, H + 300)
TOP_R = PIVOT[1] - 282  # distance from the pivot to the middle card's top edge
FAN = [(0, 0, 1.0), (14, 16, .94), (28, 38, .88), (41, 62, .82)]

POP_H, POP_CY = 560, H / 2  # the card once it has popped up
BACK_W = 960


def n(v: float) -> str:
    return f"{round(v, 2):g}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def mix(a: str, b: str, t: float) -> str:
    """t=0 gives a, t=1 gives b."""
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def dark(c: str) -> str:
    return mix(c, "#1d1b2c", 0.38)


def tint(c: str, t: float = 0.86) -> str:
    return mix(c, CREAM, t)


# =====================================================================
# Fonts: the portfolio's three faces, subset into each SVG
# =====================================================================
# Static cuts of the Google Fonts files in tools/fonts (OFL, licences alongside): Bricolage
# Grotesque at wght 800 / opsz 96, Instrument Sans at 400 and 600, DM Mono 400.
FACES = {  # key: (file, fallback for missing glyphs, generic family)
    "display": ("Bricolage-Display.ttf", "body", "system-ui,sans-serif"),
    "body": ("InstrumentSans-Regular.ttf", "display", "system-ui,sans-serif"),
    "semi": ("InstrumentSans-SemiBold.ttf", "display", "system-ui,sans-serif"),
    "mono": ("DMMono-Regular.ttf", "body", "ui-monospace,monospace"),
}


class Face:
    def __init__(self, file: str):
        self.path = FONT_DIR / file
        font = TTFont(self.path)
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm

    def has(self, ch: str) -> bool:
        return ord(ch) in self.cmap

    def advance(self, ch: str) -> float:
        return self.hmtx[self.cmap[ord(ch)]][0] / self.upm


FONTS = {k: Face(f) for k, (f, _, _) in FACES.items()}


def face_for(ch: str, key: str) -> str:
    tried = set()
    while key not in tried:
        if FONTS[key].has(ch):
            return key
        tried.add(key)
        key = FACES[key][1]
    raise ValueError(f"no font has {ch!r}")


def width(s: str, font: str, size: float, ls: float = 0.0) -> float:
    return sum(FONTS[face_for(ch, font)].advance(ch) for ch in s) * size + ls * len(s)


def wrap(s: str, font: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        t = f"{cur} {word}".strip()
        if cur and width(t, font, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = t
    return lines + [cur] if cur else lines


@lru_cache(maxsize=None)
def woff(key: str, chars: str) -> bytes:
    font = TTFont(FONTS[key].path)
    opts = subset.Options()
    opts.flavor = "woff"
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


class Svg:
    """One SVG file. Remembers which characters each font draws so it can embed just those."""

    def __init__(self):
        self.used: dict[str, set[str]] = defaultdict(set)

    def text(self, x, y, s, font, size, fill, anchor="start", ls=0.0, attrs="") -> str:
        runs: list[list[str]] = []
        for ch in s:
            f = face_for(ch, font)
            self.used[f].add(ch)
            if runs and runs[-1][0] == f:
                runs[-1][1] += ch
            else:
                runs.append([f, ch])
        body = "".join(esc(t) if f == font else f'<tspan class="f-{f}">{esc(t)}</tspan>' for f, t in runs)
        a = f'class="f-{font}" x="{n(x)}" y="{n(y)}" font-size="{n(size)}" fill="{fill}"'
        if anchor != "start":
            a += f' text-anchor="{anchor}"'
        if ls:
            a += f' letter-spacing="{n(ls)}"'
        if attrs:
            a += " " + attrs
        return f"<text {a}>{body}</text>"

    def para(self, x, y, s, font, size, fill, max_w, lh=1.45) -> tuple[str, float]:
        """Wrapped text from baseline y. Returns the markup and the last baseline."""
        lines = wrap(s, font, size, max_w)
        out = "".join(self.text(x, y + i * size * lh, ln, font, size, fill) for i, ln in enumerate(lines))
        return out, y + (len(lines) - 1) * size * lh

    def chip(self, x, y, label, fg, bg, size=14, font="mono", pad=11) -> tuple[str, float]:
        w, h = width(label, font, size) + pad * 2, size * 2
        return (f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{n(h / 2)}" fill="{bg}"/>'
                + self.text(x + w / 2, y + h / 2 + size * 0.36, label, font, size, fg, "middle")), w

    def chips(self, x, y, labels, max_w, fg, bg, size=14, gap=8, font="mono") -> tuple[str, float]:
        """Chips that wrap onto new rows. Returns the markup and the bottom edge."""
        out, cx, cy, h = [], x, y, size * 2
        for label in labels:
            w = width(label, font, size) + 22
            if cx > x and cx + w > x + max_w:
                cx, cy = x, cy + h + gap
            out.append(self.chip(cx, cy, label, fg, bg, size, font)[0])
            cx += w + gap
        return "".join(out), cy + h

    def render(self, w, h, title, desc, body, view=None, css="") -> str:
        vx, vy, vw, vh = view or (0, 0, w, h)
        fonts = []
        for key in sorted(self.used):
            data = base64.b64encode(woff(key, "".join(sorted(self.used[key] | {" "})))).decode()
            fonts.append(f"@font-face{{font-family:'pc-{key}';src:url(data:font/woff;base64,{data}) format('woff')}}")
            fonts.append(f".f-{key}{{font-family:'pc-{key}',{FACES[key][2]}}}")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(vw)}" height="{n(vh)}" '
            f'viewBox="{n(vx)} {n(vy)} {n(vw)} {n(vh)}" role="img" aria-labelledby="t d">\n'
            f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc)}</desc>\n'
            f"<style><![CDATA[\n" + "\n".join(fonts) + f"\n{css}\n"
            "@media (prefers-reduced-motion:reduce){*{animation:none!important}}\n]]></style>\n"
            f"{body}\n</svg>\n"
        )


# =====================================================================
# Icons, drawn in a 48-unit box
# =====================================================================
ICONS = {
    "plane": ['<path d="M5 23 43 7 32 41 23 28Z"/>', '<path d="M23 28 43 7"/>'],
    "code": ['<path d="M16 13 6 24l10 11M32 13l10 11-10 11M27 9l-6 30"/>'],
    "briefcase": ['<rect x="6" y="16" width="36" height="24" rx="4"/>', '<path d="M18 16v-5h12v5M6 27h36"/>'],
    "layers": ['<path d="M24 7 42 16 24 25 6 16Z"/>', '<path d="M6 24l18 9 18-9M6 32l18 9 18-9"/>'],
    "cap": ['<path d="M3 19 24 10l21 9-21 9Z"/>', '<path d="M12 23v9c0 3 5 6 12 6s12-3 12-6v-9M45 19v11"/>'],
    "path": ['<path d="M8 40c11 0 5-15 16-15s5-14 16-14" stroke-dasharray="1 6"/>', '<circle cx="8" cy="40" r="3"/>',
             '<path d="M40 13V3l8 3-8 3"/>'],
    "mail": ['<rect x="5" y="11" width="38" height="27" rx="4"/>', '<path d="m6 13 18 14 18-14"/>'],
    "link": ['<rect x="6" y="6" width="36" height="36" rx="8"/>', '<path d="M16 21v12M16 15v1M23 33V21M23 26c0-4 3-5 5-5s5 1 5 5v7"/>'],
    "globe": ['<circle cx="24" cy="24" r="18"/>', '<path d="M6 24h36M24 6c-6 6-6 30 0 36M24 6c6 6 6 30 0 36"/>'],
    "doc": ['<path d="M12 5h17l9 9v29H12z"/>', '<path d="M29 5v9h9M18 24h14M18 31h14"/>'],
}


def icon(name, cx, cy, size, color, sw=3.2) -> str:
    s = size / 48
    return (f'<g transform="translate({n(cx - size / 2)} {n(cy - size / 2)}) scale({n(s)})" fill="none" stroke="{color}" '
            f'stroke-width="{n(sw)}" stroke-linecap="round" stroke-linejoin="round">{"".join(ICONS[name])}</g>')


# =====================================================================
# The face of a card, centred on 0,0. Everything scales with its height.
# =====================================================================
ICON_Y, TITLE_Y, CAPTION_Y = 88, 160, 184  # from the card's top edge, at scale 1


def card_front(svg: Svg, i: int, w: float, h: float) -> str:
    """Side cards are half hidden in the fan, so their face is laid out in the part that shows."""
    c = CARDS[i]
    u = h / CH
    acc, ink = c["accent"], dark(c["accent"])
    x0, y0 = -w / 2, -h / 2
    mid, room = (f * w for f in face_room(i))
    # The number goes in the top corner that shows: the outer one, or the left on the middle card.
    side = 1 if i > MID else -1
    corner = w / 2 - 24 * u
    out = [
        f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(w)}" height="{n(h)}" rx="{n(16 * u)}" fill="{CREAM}"/>',
        f'<rect x="{n(x0 + 9 * u)}" y="{n(y0 + 9 * u)}" width="{n(w - 18 * u)}" height="{n(h - 18 * u)}" rx="{n(10 * u)}" '
        f'fill="{tint(acc, .9)}" stroke="{tint(acc, .55)}" stroke-width="{n(1.4 * u)}"/>',
        svg.text(side * corner, y0 + 40 * u, f"{i + 1:02d}", "semi", 15 * u, ink, "end" if side > 0 else "start", ls=0.5 * u),
        f'<circle cx="{n(-side * corner)}" cy="{n(y0 + 35 * u)}" r="{n(5 * u)}" fill="{acc}"/>',
    ]
    if c["icon"]:
        out.append(icon(c["icon"], mid, y0 + ICON_Y * u, 58 * u, ink, 3.2))
    else:  # the middle card wears a monogram
        out.append(svg.text(mid, y0 + (ICON_Y + 26) * u, "HA", "display", 68 * u, TXT, "middle", ls=-1 * u))
    size = min(26 * u, 26 * u * room / width(c["title"], "display", 26 * u))
    out.append(svg.text(mid, y0 + TITLE_Y * u, c["title"], "display", size, TXT, "middle"))
    size = min(12.5 * u, 12.5 * u * room / width(c["caption"], "mono", 12.5 * u))
    out.append(svg.text(mid, y0 + CAPTION_Y * u, c["caption"], "mono", size, TXT2, "middle"))
    if i == MID:  # the middle card has room for a little more
        y = y0 + 236 * u
        out.append(f'<line x1="{n(-w / 2 + 40 * u)}" y1="{n(y)}" x2="{n(w / 2 - 40 * u)}" y2="{n(y)}" stroke="{tint(acc, .5)}" '
                   f'stroke-width="{n(1.2 * u)}" stroke-dasharray="{n(2 * u)} {n(5 * u)}" stroke-linecap="round"/>')
        out.append(svg.text(0, y + 40 * u, "B.Tech AI & ML · 2027", "semi", 15 * u, TXT2, "middle"))
        out.append(svg.text(0, y + 64 * u, "Kochi, Kerala", "body", 15 * u, TXT2, "middle"))
        pw = width("open to work", "mono", 12.5 * u) + 44 * u
        out.append(f'<rect x="{n(-pw / 2)}" y="{n(y + 86 * u)}" width="{n(pw)}" height="{n(28 * u)}" rx="{n(14 * u)}" fill="#2fbf71" fill-opacity=".14"/>'
                   f'<circle cx="{n(-pw / 2 + 16 * u)}" cy="{n(y + 100 * u)}" r="{n(4.5 * u)}" fill="#2fbf71"/>')
        out.append(svg.text(-pw / 2 + 28 * u, y + 104.5 * u, "open to work", "mono", 12.5 * u, "#1f8a52"))
    return "".join(out)


@lru_cache(maxsize=None)
def face_room(i: int) -> tuple[float, float]:
    """Centre and width of the strip of card i's face left uncovered in the fan, as fractions of its width.

    Measured along the icon and title rows; the middle card is fully on show.
    """
    _, _, a, s = pose(i)
    w, h = CW * s, CH * s
    if i == MID:
        return 0.0, (w - 40 * s) / w
    cx, cy = centre(i)
    r = math.radians(a)
    order = draw_order()
    front = order[order.index(i) + 1:]
    xs = [-w / 2 + 14 * s + k for k in range(int(w - 28 * s))]
    lo, hi = -w / 2, w / 2
    for row in (ICON_Y - 30, ICON_Y + 30, TITLE_Y - 20, CAPTION_Y):
        ly = -h / 2 + row * s
        shown = [lx for lx in xs if not any(contains(j, cx + lx * math.cos(r) - ly * math.sin(r),
                                                     cy + lx * math.sin(r) + ly * math.cos(r)) for j in front)]
        lo, hi = max(lo, min(shown)), min(hi, max(shown))
    return (lo + hi) / 2 / w, (hi - lo - 20 * s) / w


# =====================================================================
# The screen
# =====================================================================
def pose(i: int) -> tuple[float, float, float, float]:
    """Bottom-centre x, y, tilt and scale of card i."""
    k = i - MID
    tilt, drop, s = FAN[abs(k)]
    a = math.radians(tilt if k > 0 else -tilt)
    r = TOP_R - drop - CH * s
    return PIVOT[0] + r * math.sin(a), PIVOT[1] - r * math.cos(a), math.degrees(a), s


def centre(i: int) -> tuple[float, float]:
    bx, by, a, s = pose(i)
    r, h = math.radians(a), CH * s
    return bx + math.sin(r) * h / 2, by - math.cos(r) * h / 2


def contains(i: int, x: float, y: float) -> bool:
    _, _, a, s = pose(i)
    cx, cy = centre(i)
    r = math.radians(a)
    dx, dy = x - cx, y - cy
    lx, ly = dx * math.cos(r) + dy * math.sin(r), -dx * math.sin(r) + dy * math.cos(r)
    return abs(lx) <= CW * s / 2 and abs(ly) <= CH * s / 2


def draw_order() -> list[int]:
    """Outermost first, so the middle card ends up on top."""
    out = []
    for k in range(MID, 0, -1):
        out += [MID - k, MID + k]
    return out + [MID]


def background() -> str:
    return (
        "<defs>"
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">'
        f'<stop offset="0" stop-color="{INK}"/><stop offset="1" stop-color="{INK2}"/></linearGradient>'
        f'<radialGradient id="glow" cx="{W / 2}" cy="{H + 80}" r="700" gradientUnits="userSpaceOnUse">'
        '<stop offset="0" stop-color="#ff8a5c" stop-opacity=".42"/><stop offset=".45" stop-color="#a26bff" stop-opacity=".16"/>'
        '<stop offset="1" stop-color="#a26bff" stop-opacity="0"/></radialGradient>'
        '<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        '<circle cx="12" cy="12" r="1.2" fill="#fff" fill-opacity=".07"/></pattern>'
        '<filter id="soft" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="12"/></filter>'
        "</defs>"
        f'<rect width="{W}" height="{H}" rx="22" fill="url(#bg)"/>'
        f'<rect width="{W}" height="{H}" rx="22" fill="url(#dots)"/>'
        f'<rect width="{W}" height="{H}" rx="22" fill="url(#glow)"/>'
    )


def title_band(svg: Svg) -> tuple[str, str]:
    cx = W / 2
    body = (
        f'<g class="rise r1">{svg.text(cx, 84, EYEBROW, "mono", 16, "#a19fc0", "middle", ls=3)}</g>'
        f'<g class="rise r2">{svg.text(cx, 160, NAME, "display", 78, CREAM, "middle", ls=-1)}</g>'
        f'<g class="rise r3">{svg.text(cx, 204, TAGLINE, "body", 23, "#cfcde3", "middle")}</g>'
        f'<g class="rise r4"><g class="bob">{svg.text(cx, 238, HINT, "mono", 15, "#ffb38a", "middle", ls=1)}</g></g>'
    )
    css = (
        ".rise{animation:rise .9s cubic-bezier(.2,.8,.2,1) both}"
        ".r2{animation-delay:.08s}.r3{animation-delay:.18s}.r4{animation-delay:.5s}"
        "@keyframes rise{from{opacity:0;transform:translateY(14px)}}"
        ".bob{animation:bob 1.8s ease-in-out 1.4s infinite}"
        "@keyframes bob{50%{transform:translateY(4px)}}"
    )
    return body, css


def fan(svg: Svg, skip: int | None = None) -> str:
    out = []
    for i in draw_order():
        if i == skip:
            continue
        bx, by, a, s = pose(i)
        w, h = CW * s, CH * s
        out.append(
            f'<g transform="translate({n(bx)} {n(by)}) rotate({n(a)}) translate(0 {n(-h / 2)})">'
            f'<rect x="{n(-w / 2)}" y="{n(-h / 2 + 8)}" width="{n(w)}" height="{n(h)}" rx="{n(16 * s)}" fill="#05040c" '
            f'fill-opacity=".6" filter="url(#soft)"/>{card_front(svg, i, w, h)}</g>'
        )
    return "".join(out)


def cuts() -> list[int]:
    """Where to slice the fan so each strip holds the card that owns most of it.

    Widths come out as multiples of 3 so every strip's percentage is exact.
    """
    order = draw_order()
    owner = []
    for x in range(W):
        counts = [0] * len(CARDS)
        for y in range(TOP, H, 3):
            for i in reversed(order):
                if contains(i, x + 0.5, y + 0.5):
                    counts[i] += 1
                    break
        owner.append(max(range(len(CARDS)), key=counts.__getitem__) if any(counts) else None)
    out = [0]
    for i in range(1, len(CARDS)):
        first = next(x for x, o in enumerate(owner) if o is not None and o >= i)
        out.append(round(first / 3) * 3)
    return out + [W]


# =====================================================================
# Backs of the cards
# =====================================================================
BX0, BY0, BH = (W - BACK_W) / 2, POP_CY - POP_H / 2, POP_H
PAD = 56
CX0, CY0, CWID = BX0 + PAD, BY0 + 158, BACK_W - PAD * 2  # content box


def tile(x, y, w, h, fill, stroke) -> str:
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>'


def back_about(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out, y = svg.para(CX0, CY0 + 6, (
        "I'm a product engineer finishing a B.Tech in AI & ML at Chinmaya Vishwa Vidyapeeth, class of 2027, "
        "based in Kochi, Kerala. I build things end to end, from the database schema to the last screen, "
        "and I don't call a project done until it's deployed."), "body", 21, TXT2, CWID, 1.5)
    out = [out]
    stats = [("14", "public repos"), ("5", "live apps"), ("2", "internships"), ("2", "mobile apps")]
    tw, ty = (CWID - 3 * 16) / 4, y + 40
    for k, (num, label) in enumerate(stats):
        tx = CX0 + k * (tw + 16)
        out.append(tile(tx, ty, tw, 104, tint(acc, .9), tint(acc, .6)))
        out.append(svg.text(tx + 22, ty + 56, num, "display", 42, ink))
        out.append(svg.text(tx + 22, ty + 84, label, "body", 16, TXT2))
    fy = ty + 104 + 50
    out.append(f'<circle cx="{n(CX0 + 7)}" cy="{n(fy - 6)}" r="7" fill="#2fbf71"/>')
    out.append(svg.text(CX0 + 24, fy, "Open to internships and junior product-engineering roles.", "semi", 19, TXT))
    return "".join(out)


PROJECTS = [
    ("Campus Hub", "Live", "Events, QR tickets and volunteer rosters for a college. The check-in code rotates every 30 seconds.",
     "Next.js · Postgres · Drizzle", "https://campus-hub-eight-rouge.vercel.app", "https://github.com/Techspell01/campus-hub"),
    ("PG Finder", "Live", "Student housing search that replaces a pile of WhatsApp forwards with one search box.",
     "React · TypeScript · Gemini", "https://pgfinder-mu.vercel.app", "https://github.com/Techspell01/Pg-Finder-"),
    ("MedReminder Circle", "Live", "Medication reminders shared with the family members who'd notice a missed dose.",
     "React · Vercel", "https://medreminder-tawny.vercel.app", "https://github.com/Techspell01/medreminder"),
    ("BunkerMe", "Live", "An installable PWA for the attendance maths every student already does in their head.",
     "PWA · JavaScript", "https://bunkerme.vercel.app", "https://github.com/Techspell01/bunkerme"),
    ("Quriobot", "Mobile", "A conversational assistant built as a native mobile app, with speech and camera.",
     "React Native · Expo", None, "https://github.com/Techspell01/quriobot"),
    ("NFC Habit Tracker", "Hardware", "Log a habit by tapping your phone on a physical NFC tag. Nothing to open.",
     "Android · NFC", None, "https://github.com/Techspell01/nfc-habit-tracker"),
]
MORE_PROJECTS = [
    ("Restaurant intelligence", "three ML studies from the Cognifyz internship: a "
     "[cuisine classifier](https://github.com/Techspell01/Ai-Based-Cuisine-Classification), a "
     "[recommender](https://github.com/Techspell01/Ai-Restaurant-Recommendation) and a "
     "[location analysis](https://github.com/Techspell01/Restaurants-Location-based-Analysis)"),
    ("[Marketing channel ROI](https://github.com/Techspell01/marketing-channel-roi-analysis)",
     "referral traffic converts ~9× better than organic search, confirmed with a chi-square test on GA360 data in BigQuery"),
    ("[Expense tracker](https://github.com/Techspell01/expense_tracker)",
     "a server-rendered Flask app, and the first thing I put on GitHub"),
]


def back_projects(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out = []
    gap, cols = 16, 3
    tw, th = (CWID - gap * (cols - 1)) / cols, 168
    for k, (name, status, desc, stack, _, _) in enumerate(PROJECTS):
        tx, ty = CX0 + (k % cols) * (tw + gap), CY0 - 18 + (k // cols) * (th + gap)
        out.append(tile(tx, ty, tw, th, tint(acc, .92), tint(acc, .62)))
        pill_bg = {"Live": "#2fbf71", "Mobile": "#4d9bff", "Hardware": "#ff9f43"}[status]
        pw = width(status, "mono", 11.5) + 16
        room = tw - 36 - pw - 10
        out.append(svg.text(tx + 18, ty + 34, name, "semi", min(19, 19 * room / width(name, "semi", 19)), TXT))
        out.append(f'<rect x="{n(tx + tw - 18 - pw)}" y="{n(ty + 17)}" width="{n(pw)}" height="22" rx="11" fill="{pill_bg}"/>')
        out.append(svg.text(tx + tw - 18 - pw / 2, ty + 32, status, "mono", 11.5, "#fff", "middle"))
        out.append(svg.para(tx + 18, ty + 62, desc, "body", 15, TXT2, tw - 36, 1.42)[0])
        out.append(svg.text(tx + 18, ty + th - 18, stack, "mono", 12, ink))
    return "".join(out)


INTERNSHIPS = [
    ("AI & ML Intern", "Litmus7", "Infopark, Ernakulam · on-site", "Jun 2026",
     ["Built the React and TypeScript front end of a retail promotions performance analyzer.",
      "Helped structure a LangGraph ReAct tool-calling agent with a Qdrant RAG pipeline behind it."],
     ["React", "TypeScript", "FastAPI", "LangGraph", "Qdrant", "PostgreSQL"]),
    ("Machine Learning Intern", "Cognifyz Technologies", "Remote", "May – Jun 2026",
     ["A cuisine classifier that predicts restaurant type from structured data.",
      "A TF-IDF and cosine-similarity recommender, and a Streamlit + Folium map of where restaurants cluster."],
     ["Python", "scikit-learn", "pandas", "Streamlit", "Folium"]),
]


def back_internships(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out = []
    gap = 20
    cw = (CWID - gap) / 2
    for k, (role, org, where, when, points, stack) in enumerate(INTERNSHIPS):
        x, y = CX0 + k * (cw + gap), CY0 - 18
        out.append(tile(x, y, cw, 352, tint(acc, .92), tint(acc, .6)))
        x += 22
        out.append(svg.text(x, y + 40, role, "display", 25, TXT))
        out.append(svg.text(x, y + 68, org, "semi", 18, ink))
        out.append(svg.text(x, y + 92, f"{when} · {where}", "mono", 12.5, TXT2))
        py = y + 132
        for p in points:
            out.append(f'<circle cx="{n(x + 4)}" cy="{n(py - 5)}" r="3.5" fill="{acc}"/>')
            m, last = svg.para(x + 18, py, p, "body", 16, TXT2, cw - 62, 1.42)
            out.append(m)
            py = last + 32
        out.append(svg.chips(x, y + 352 - 22 - 26 * 2 - 8, stack, cw - 44, ink, tint(acc, .72), 12.5)[0])
    return "".join(out)


SKILLS = [
    ("Languages", ["Python", "TypeScript", "JavaScript", "SQL", "C/C++", "HTML/CSS"]),
    ("Front end", ["React", "Next.js", "Vite", "Tailwind", "Motion", "PWA"]),
    ("Back end", ["FastAPI", "Flask", "PostgreSQL", "Drizzle", "SQLite", "Firebase"]),
    ("AI & LLMs", ["Gemini", "Claude", "Groq", "LangGraph", "Qdrant RAG", "Prompting"]),
    ("Data & ML", ["scikit-learn", "pandas", "NumPy", "OpenCV", "Streamlit", "BigQuery"]),
    ("Mobile", ["React Native", "Expo Router", "EAS Build", "Reanimated", "NFC"]),
    ("Tools", ["Git", "GitHub", "Vercel", "uv", "Android Studio"]),
]


def back_skills(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out = []
    for k, (label, items) in enumerate(SKILLS):
        y = CY0 - 20 + k * 45
        out.append(svg.text(CX0, y + 19, label.upper(), "mono", 12.5, ink, ls=1.5))
        out.append(svg.chips(CX0 + 132, y, items, CWID - 132, TXT, tint(acc, .78), 13.5, 7)[0])
    return "".join(out)


YEARS = ["Year 1", "Year 2", "Year 3", "Year 4"]


def back_education(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    y = CY0 - 18
    out = [tile(CX0, y, CWID, 132, tint(acc, .92), tint(acc, .6)),
           f'<circle cx="{n(CX0 + 66)}" cy="{n(y + 66)}" r="38" fill="{tint(acc, .72)}"/>',
           icon("cap", CX0 + 66, y + 64, 44, ink, 3.2),
           svg.text(CX0 + 128, y + 50, "B.Tech in Artificial Intelligence & Machine Learning", "semi", 23, TXT),
           svg.text(CX0 + 128, y + 80, "Chinmaya Vishwa Vidyapeeth, Deemed to be University", "body", 17.5, TXT2),
           svg.text(CX0 + 128, y + 106, "Final year · graduating 2027", "mono", 13, ink)]
    ry = y + 132 + 64
    step = CWID / (len(YEARS) - 1)
    out.append(f'<line x1="{n(CX0)}" y1="{n(ry)}" x2="{n(CX0 + CWID)}" y2="{n(ry)}" stroke="{acc}" stroke-width="3" stroke-linecap="round"/>')
    for k, label in enumerate(YEARS):
        x = CX0 + k * step
        anchor = "start" if k == 0 else "end" if k == len(YEARS) - 1 else "middle"
        last = k == len(YEARS) - 1
        if last:
            out.append(f'<circle cx="{n(x)}" cy="{n(ry)}" r="13" fill="{acc}" fill-opacity=".25"/>')
        out.append(f'<circle cx="{n(x)}" cy="{n(ry)}" r="{7 if last else 6}" fill="{acc}"/>')
        out.append(svg.text(x, ry + 34, label, "semi" if last else "body", 16, TXT if last else TXT2, anchor))
        out.append(svg.text(x, ry + 54, "now · final year" if last else "done", "mono", 12, ink if last else MUTED, anchor))
    out.append(svg.para(CX0, ry + 112, "Alongside the degree: two internships in 2026, and everything on the Projects card.",
                        "body", 19, TXT2, CWID)[0])
    return "".join(out)


JOURNEY = [
    ("Jul 2024", "Made the GitHub account", "and then shipped nothing for nineteen months."),
    ("Mar 2026", "First two repos public in 48 hours", "a Flask expense tracker and BunkerMe."),
    ("Jun 2026", "Two internships at once", "Litmus7 on-site and Cognifyz remote, plus the busiest month of commits."),
    ("Aug 2026", "Three apps in three days", "all deployed, each behind a live URL."),
    ("Sep 2026", "Campus Hub, end to end in a week", "rotating QR check-in, hand-rolled auth, Postgres."),
    ("Now", "Final year of the B.Tech", "graduating in 2027, and open to internships and junior roles."),
]


def back_journey(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out = []
    lx, row = CX0 + 128, 62
    y0 = CY0 - 8
    out.append(f'<line x1="{n(lx)}" y1="{n(y0)}" x2="{n(lx)}" y2="{n(y0 + row * (len(JOURNEY) - 1))}" stroke="{tint(acc, .55)}" stroke-width="2.5"/>')
    for k, (when, what, more) in enumerate(JOURNEY):
        y = y0 + k * row
        last = k == len(JOURNEY) - 1
        out.append(svg.text(CX0, y + 5, when, "mono", 14, ink if last else TXT2))
        out.append(f'<circle cx="{n(lx)}" cy="{n(y)}" r="{7 if last else 5.5}" fill="{acc if last else CREAM}" stroke="{acc}" stroke-width="2.5"/>')
        out.append(svg.text(lx + 28, y + 6, what, "semi", 18.5, TXT))
        out.append(svg.text(lx + 28, y + 28, more[0].upper() + more[1:], "body", 15.5, TXT2))
    return "".join(out)


CONTACT = [
    ("mail", "Email", EMAIL, f"mailto:{EMAIL}"),
    ("link", "LinkedIn", "linkedin.com/in/harinand-as", LINKEDIN),
    ("globe", "Portfolio", "techspell01.github.io/portfolio", PORTFOLIO),
    ("doc", "Résumé", "one page, PDF", RESUME),
]


def back_contact(svg: Svg, acc: str) -> str:
    ink = dark(acc)
    out, y = svg.para(CX0, CY0 + 6, (
        "Open to internships, junior product-engineering roles, or a side project that needs someone "
        "who will actually finish it. I reply fast."), "body", 21, TXT2, CWID, 1.5)
    out = [out]
    gap = 16
    tw, th = (CWID - gap) / 2, 104
    for k, (ic, label, value, _) in enumerate(CONTACT):
        tx, ty = CX0 + (k % 2) * (tw + gap), y + 38 + (k // 2) * (th + gap)
        out.append(tile(tx, ty, tw, th, tint(acc, .92), tint(acc, .6)))
        out.append(f'<circle cx="{n(tx + 50)}" cy="{n(ty + th / 2)}" r="27" fill="{tint(acc, .7)}"/>')
        out.append(icon(ic, tx + 50, ty + th / 2, 28, ink, 3.4))
        out.append(svg.text(tx + 96, ty + 44, label.upper(), "mono", 12.5, ink, ls=1.5))
        out.append(svg.text(tx + 96, ty + 72, value, "semi", 19, TXT))
    return "".join(out)


BACKS = {
    "about": ("Hi, I'm Harinand.", back_about),
    "projects": ("Things I've shipped", back_projects),
    "internships": ("Where I've worked", back_internships),
    "skills": ("What I build with", back_skills),
    "education": ("Where I study", back_education),
    "journey": ("How I got here", back_journey),
    "contact": ("Say hi", back_contact),
}


def card_back(svg: Svg, i: int) -> str:
    c = CARDS[i]
    acc = c["accent"]
    heading, content = BACKS[c["slug"]]
    x0, y0, w, h = BX0, BY0, BACK_W, BH
    out = [
        f'<rect x="{n(x0)}" y="{n(y0)}" width="{n(w)}" height="{n(h)}" rx="22" fill="{CREAM}"/>',
        f'<rect x="{n(x0 + 12)}" y="{n(y0 + 12)}" width="{n(w - 24)}" height="{n(h - 24)}" rx="14" fill="none" '
        f'stroke="{tint(acc, .55)}" stroke-width="1.5"/>',
        svg.text(x0 + PAD, y0 + 64, f'{i + 1} OF {len(CARDS)} · {c["title"].upper()}', "mono", 14, dark(acc), ls=2),
        svg.text(x0 + PAD - 2, y0 + 114, heading, "display", 44, TXT, ls=-0.5),
        f'<circle cx="{n(x0 + w - 86)}" cy="{n(y0 + 82)}" r="36" fill="{tint(acc, .78)}"/>',
    ]
    if c["icon"]:
        out.append(icon(c["icon"], x0 + w - 86, y0 + 82, 40, dark(acc), 3.2))
    else:
        out.append(svg.text(x0 + w - 86, y0 + 94, "HA", "display", 32, TXT, "middle"))
    out.append(content(svg, acc))
    out.append(svg.text(x0 + PAD, y0 + h - 30, "links are below the card ↓", "mono", 13, MUTED))
    out.append(svg.text(x0 + w - PAD, y0 + h - 30, "click the card to put it back", "mono", 13, MUTED, "end"))
    return "".join(out)


def popup(i: int) -> tuple[Svg, str, str]:
    """The deck, dimmed, with card i flying out of it and flipping over."""
    svg = Svg()
    band, _ = title_band(svg)  # without its CSS, so it sits still behind the card
    bx, by, a, s = pose(i)
    cx, cy = centre(i)
    k = POP_H / CH
    fw = CW * k
    lift = f"translate({n(cx - W / 2)}px,{n(cy - POP_CY)}px) rotate({n(a)}deg) scale({n(s / k)})"
    shadow = lambda x, y, w, h: (f'<rect x="{n(x)}" y="{n(y + 16)}" width="{n(w)}" height="{n(h)}" rx="22" fill="#000" '
                                 f'fill-opacity=".55" filter="url(#soft)"/>')
    front = (f'<g class="front">{shadow(W / 2 - fw / 2, POP_CY - POP_H / 2, fw, POP_H)}'
             f'<g transform="translate({n(W / 2)} {n(POP_CY)})">{card_front(svg, i, fw, POP_H)}</g></g>')
    back = f'<g class="back">{shadow(BX0, BY0, BACK_W, BH)}{card_back(svg, i)}</g>'
    body = (background() + f'<g class="deck">{band}{fan(svg, skip=i)}</g>'
            + f'<rect class="dim" width="{W}" height="{H}" rx="22" fill="#07060f" opacity=".74"/>'
            + f'<g class="fly">{front}{back}</g>')
    origin = f"transform-origin:{n(W / 2)}px {n(POP_CY)}px"
    css = (
        f".dim{{animation:dim .6s ease .1s both}}@keyframes dim{{from{{opacity:0}}}}"
        f".fly{{{origin};animation:fly .95s cubic-bezier(.22,.8,.25,1) .2s both}}"
        f"@keyframes fly{{from{{transform:{lift}}}70%{{transform:translate(0px,-14px) rotate(0deg) scale(1.02)}}"
        f"to{{transform:translate(0px,0px) rotate(0deg) scale(1)}}}}"
        f".front{{{origin};animation:flipout .26s cubic-bezier(.5,0,.9,.5) 1.05s both}}"
        f"@keyframes flipout{{to{{transform:scaleX(0)}}}}"
        f".back{{{origin};animation:flipin .42s cubic-bezier(.15,.8,.3,1.12) 1.31s both}}"
        f"@keyframes flipin{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}"
    )
    return svg, body, css


# =====================================================================
# Markdown
# =====================================================================
def readme(strips: list[int]) -> str:
    top = (f'<a href="{PORTFOLIO}"><img src="{RAW}/assets/deck-top.svg" width="100%" align="top" '
           f'alt="Harinand AS. {EYEBROW.title()}. {TAGLINE} Pick a card."></a>')
    cards = "".join(
        f'<a href="{BLOB}/cards/{c["slug"]}.md"><img src="{RAW}/assets/deck-{c["slug"]}.svg" '
        f'width="{n((strips[i + 1] - strips[i]) * 100 / W)}%" align="top" alt="{c["title"]} card"></a>'
        for i, c in enumerate(CARDS)
    )
    return (
        "<!-- Built by tools/build.py. The deck is one picture cut into a strip per card; "
        "each strip opens that card's page in cards/. Edit the script, not this file. -->\n\n"
        f'<p align="center">{top}<br>{cards}</p>\n\n'
        f'<p align="center"><sub>Pick a card and it flips over &nbsp;·&nbsp; <a href="{PORTFOLIO}">Portfolio</a> · '
        f'<a href="{LINKEDIN}">LinkedIn</a> · <a href="mailto:{EMAIL}">Email</a> · <a href="{RESUME}">Résumé</a></sub></p>\n'
    )


def page_links(slug: str) -> str:
    if slug == "projects":
        rows = "\n".join(
            f"| **{name}** | {desc} | " + " · ".join(x for x in ([f"[Live]({live})"] if live else []) + [f"[Code]({code})"]) + " |"
            for name, _, desc, _, live, code in PROJECTS
        )
        more = "\n".join(f"- **{name}**: {desc}" for name, desc in MORE_PROJECTS)
        return f"| Project | What it is | Links |\n|---|---|---|\n{rows}\n\n**Also built**\n\n{more}\n"
    if slug == "internships":
        return "\n".join(
            f"**{role} · {org}** · {when} · {where}  \n" + " ".join(points) + "\n"
            for role, org, where, when, points, _ in INTERNSHIPS
        ) + "\nThe three Cognifyz apps: [cuisine classifier](https://github.com/Techspell01/Ai-Based-Cuisine-Classification) · " \
            "[recommender](https://github.com/Techspell01/Ai-Restaurant-Recommendation) · " \
            "[location analysis](https://github.com/Techspell01/Restaurants-Location-based-Analysis)\n"
    if slug == "contact":
        return "\n".join(f"- **{label}**: [{value}]({href})" for _, label, value, href in CONTACT) + "\n"
    if slug == "education":
        return (f"**B.Tech in Artificial Intelligence & Machine Learning**, Chinmaya Vishwa Vidyapeeth, Deemed to be University. "
                f"Final year, graduating in 2027. [Résumé]({RESUME})\n")
    if slug == "journey":
        return f"The longer version, with the commits behind each date, is on my [portfolio]({PORTFOLIO}#journey).\n"
    if slug == "skills":
        return "\n".join(f"- **{label}**: {', '.join(items)}" for label, items in SKILLS) + "\n"
    return (f"[Portfolio]({PORTFOLIO}) · [LinkedIn]({LINKEDIN}) · [Email](mailto:{EMAIL}) · [Résumé]({RESUME})\n")


def page(i: int) -> str:
    c = CARDS[i]
    prev, nxt = CARDS[i - 1], CARDS[(i + 1) % len(CARDS)]
    nav = (f'<p align="center"><a href="{BLOB}/cards/{prev["slug"]}.md">← {prev["title"]}</a> &nbsp;·&nbsp; '
           f'<a href="{PROFILE}"><b>Back to the deck</b></a> &nbsp;·&nbsp; '
           f'<a href="{BLOB}/cards/{nxt["slug"]}.md">{nxt["title"]} →</a></p>')
    return (
        f"<!-- Built by tools/build.py -->\n\n"
        f'<a href="{PROFILE}"><img src="{RAW}/assets/pop-{c["slug"]}.svg" width="100%" '
        f'alt="The {c["title"]} card, flipped over: {BACKS[c["slug"]][0]}"></a>\n\n'
        f"{nav}\n\n{page_links(c['slug'])}"
    )


# =====================================================================
def write(path: Path, s: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding="utf-8", newline="\n")
    print(f"{path.relative_to(ROOT)}  {len(s.encode()) // 1024} KB")


def main() -> None:
    strips = cuts()
    print("strips:", strips)

    svg = Svg()
    band, css = title_band(svg)
    write(ASSETS / "deck-top.svg", svg.render(W, H, NAME, f"{EYEBROW}. {TAGLINE}", background() + band, (0, 0, W, TOP), css))

    for i, c in enumerate(CARDS):
        svg = Svg()
        body = background() + fan(svg)
        view = (strips[i], TOP, strips[i + 1] - strips[i], H - TOP)
        write(ASSETS / f"deck-{c['slug']}.svg", svg.render(W, H, f"{c['title']} card", f"{c['title']}: {c['caption']}", body, view))

    for i, c in enumerate(CARDS):
        svg, body, css = popup(i)
        write(ASSETS / f"pop-{c['slug']}.svg", svg.render(W, H, f"{c['title']} card", BACKS[c["slug"]][0], body, css=css))
        write(PAGES / f"{c['slug']}.md", page(i))

    # The whole screen in one file, for checking the cut lines by eye.
    svg = Svg()
    band, css = title_band(svg)
    guides = "".join(f'<line x1="{x}" y1="{TOP}" x2="{x}" y2="{H}" stroke="#0ff" stroke-opacity=".5" stroke-dasharray="4 4"/>' for x in strips[1:-1])
    (ROOT / "tools" / "preview.svg").write_text(svg.render(W, H, NAME, "", background() + band + fan(svg) + guides, css=css), encoding="utf-8")

    write(ROOT / "README.md", readme(strips))


if __name__ == "__main__":
    main()
