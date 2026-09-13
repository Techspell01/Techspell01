#!/usr/bin/env python3
"""Build the arcade-style SVGs in assets/.

    pip install fonttools
    python tools/build.py

Everything personal is in the DATA block, and every sprite is drawn as text in
the SPRITES block (one letter per pixel, colours in theme.PAL). Edit, rerun,
commit assets/. The high-score card and snake come from the GitHub Action
(tools/stats.py), not from here.
"""
from __future__ import annotations

import io
import json
import math
import random
import sys
from pathlib import Path
from xml.etree import ElementTree

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme as th  # noqa: E402
from theme import PAL, PANEL, SCREEN, SLOT, art, crt, document, frames, n, notched, panel, pixel_width, pixels, size_of, tab, text  # noqa: E402

SRC_FONTS = Path(__file__).resolve().parent / "fonts"
OUT = th.ROOT / "assets"

# =====================================================================
# DATA
# =====================================================================
NAME = "HARINAND AS"
SUBTITLE = "PRODUCT ENGINEER · AI & ML"
HUD = [("HARINAND", "000014"), ("LIVE", "×05"), ("WORLD", "KL-07"), ("CLASS", "2027")]  # score = public repos
PROMPTS = ["▶ PRESS START", "▶ OPEN TO WORK", "▶ KOCHI · KERALA"]
COPYRIGHT = "© 2026 TECHSPELL01 · MADE IN KERALA"

BUTTONS = [  # (slug, label, icon, face, edge, ink)
    ("portfolio", "PORTFOLIO", "star", "y", "o", "k"),
    ("linkedin", "LINKEDIN", "linkedin", "b", "B", "k"),
    ("email", "EMAIL", "mail", "r", "p", "w"),
    ("resume", "RÉSUMÉ", "scroll", "g", "G", "k"),
]

PLAYER = [
    ("NAME", "Harinand AS"),
    ("CLASS", "Product engineer"),
    ("GUILD", "B.Tech AI & ML · class of 2027"),
    ("BASE", "Kochi, Kerala, India"),
]
PLAYER_STATS = [  # (label, count, icon, colour) — real numbers, drawn as items
    ("SHIPPED", 14, "coin", "y"),
    ("LIVE", 5, "heart", "r"),
    ("QUESTS", 2, "star", "o"),
    ("MOBILE", 2, "phone", "b"),
]
SPECIAL = "Turns half-formed ideas into live URLs"

BOSS = dict(
    eyebrow="WORLD 4 · FINAL-YEAR PROJECT",
    title=["FISHING BOAT", "SAFETY SYSTEM"],
    desc=("Capsize and distress detection for small Kerala fishing boats. A Random Forest runs "
          "on the ESP32 itself and relays the alert to shore over LoRa, so it works exactly "
          "where there is no signal."),
    powerups=["ESP32", "C/C++", "emlearn", "LoRa", "FastAPI", "React"],
    phase=1, phases=7, phase_label="SENSING RIG",
)

LEVELS = [  # (slug, world, title, status, description, power-ups, colour, icon)
    ("campus-hub", "WORLD 1-1", "CAMPUS HUB", "LIVE",
     "Events, QR tickets and volunteer rosters for a college. Check-in codes rotate every 30 seconds.",
     ["Next.js", "Postgres", "Drizzle"], "g", "qr"),
    ("pg-finder", "WORLD 1-2", "PG FINDER", "LIVE",
     "Student housing search that replaces a pile of WhatsApp forwards with one search box.",
     ["React", "TypeScript", "Gemini"], "b", "house"),
    ("medreminder", "WORLD 1-3", "MEDREMINDER CIRCLE", "LIVE",
     "Medication reminders shared with the family members who would notice a missed dose.",
     ["React", "Firebase", "PWA"], "P", "pill"),
    ("bunkerme", "WORLD 1-4", "BUNKERME", "LIVE",
     "An installable PWA for the attendance maths every student already does in their head.",
     ["PWA", "JavaScript", "Offline"], "o", "calendar"),
    ("quriobot", "WORLD 2-1", "QURIOBOT", "MOBILE",
     "A conversational assistant with speech and camera input, built as a native mobile app.",
     ["React Native", "Expo"], "l", "robot"),
    ("nfc-habit-tracker", "WORLD 3-1", "NFC HABIT TRACKER", "HARDWARE",
     "Log a habit by tapping your phone on a physical NFC tag. Nothing to open, no guilt.",
     ["Android", "NFC"], "y", "nfc"),
]

INVENTORY = [  # (category, icon, items)
    ("LANGUAGES", "sword", ["Python", "TypeScript", "JavaScript", "HTML", "CSS", "C/C++"]),
    ("FRONT END", "shield", ["React", "Next.js", "Vite", "Tailwind", "Motion", "PWA"]),
    ("BACK END", "gear", ["FastAPI", "Flask", "PostgreSQL", "Drizzle", "SQLite", "Firebase"]),
    ("AI & LLMS", "gem", ["Gemini API", "Claude API", "Groq API", "LangGraph", "Qdrant RAG", "Prompting"]),
    ("DATA & ML", "potion", ["scikit-learn", "pandas", "NumPy", "OpenCV", "Streamlit", "BigQuery"]),
    ("MOBILE", "phone", ["React Native", "Expo Router", "EAS Build", "Reanimated", "NFC"]),
    ("EDGE", "chip", ["ESP32", "PlatformIO", "emlearn", "LoRa", "Raspberry Pi"]),
    ("TOOLS", "wrench", ["Git", "GitHub", "Vercel", "uv", "Android Studio"]),
]

WORLD_MAP = [  # (date, title, sub)
    ("JUL 2024", "Made the account", "then 19 quiet months"),
    ("MAR 2026", "First repos public", "Flask app + PWA in 48h"),
    ("JUN 2026", "Two internships", "Litmus7 · Cognifyz"),
    ("AUG 2026", "3 apps in 3 days", "all live on Vercel"),
    ("SEP 2026", "Campus Hub", "~10k lines in a week"),
    ("NOW", "Boss stage", "boat safety system"),
]

EMAIL = "harinand200406@gmail.com"

# =====================================================================
# SPRITES — one letter per pixel, '.' is transparent (colours: theme.PAL)
# =====================================================================
HEAD = """
.....hhhhhh.....
....hhhhhhhhh...
...hhhhhhhhhhh..
...hhhhhhsssh...
...hhhhsssksss..
...hhhSsssksss..
....hhSssssss...
.....sssSSs.....
"""
BODY = {
    "a": """
....oooooooo....
...ooooooooooss.
..sooowoooooo...
....nnnnnnnnn...
""",
    "b": """
....oooooooo....
...oooooooooo...
...sooowooooos..
....nnnnnnnnn...
""",
}
LEGS = {
    "a": """
....BBBBBBBB....
...BBBB..BBBB...
..BBB......BBB..
.kww........kww.
""",
    "b": """
....BBBBBBBB....
.....BBBBBB.....
.....BBB.BB.....
....kww..kww....
""",
    "c": """
....BBBBBBBB....
....BBB..BBB....
...BBB....BBB...
..kww......kww..
""",
}


def hero(body="b", legs="b", blink=False):
    head = art(HEAD)
    if blink:
        head = [r.replace("k", "S") for r in head]
    return head + art(BODY[body]) + art(LEGS[legs])


RUN = [hero("a", "a"), hero("b", "b"), hero("a", "c")]

BUG = ["""
..k......k..
...k....k...
..gggggggg..
.gGggGGggGg.
gggggggggggg
gkwgggggkwgg
.gggggggggg.
..g.g..g.g..
.g..g..g..g.
""", """
..k......k..
...k....k...
..gggggggg..
.gGggGGggGg.
gggggggggggg
gkwgggggkwgg
.gggggggggg.
.g.g..g..g..
..g..g..g.g.
"""]
BUG_FLAT = """
............
............
............
............
............
..k......k..
.gggggggggg.
gxxgggggxxgg
gggggggggggg
"""
QBLOCK = """
kkkkkkkkkk
kyoooooook
kooowwwook
koowoowwok
kooooowwok
koooowwook
kooooooook
koooowwook
kyoooooonk
kkkkkkkkkk
"""
COIN_FRAMES = [th.COIN, """
...oyo..
..oyyyo.
..oywyo.
..oywyo.
..oywyo.
..oyyyo.
..oyyyo.
...ooo..
""", """
....oy..
....oy..
....oy..
....oy..
....oy..
....oy..
....oy..
....oo..
"""]
HEART = """
.rr.rr.
rrwrrrr
rrrrrrr
.rrrrr.
..rrr..
...r...
"""
STAR = """
...yy...
...yy...
yyyyyyyy
.yyyyyy.
..yyyy..
.yy..yy.
yy....yy
"""
PHONE = """
.ccccc.
.cbbbc.
.cbwbc.
.cbbbc.
.cbbbc.
.cbbbc.
.ccwcc.
"""
PALM = """
....GG...GG...
..GGggG.GggGG.
.GggGGggggGGgG
Gg..GgggggG..g
G..Gg.nNn.gG.G
...G..NnN..G..
.......n......
.......nn.....
........n.....
........nn....
........nn....
........nn....
.......nn.....
.......nn.....
......nn......
......nn......
......nn......
.....nnnn.....
"""
GROUND = """
gggggggggggggggg
gGgggGgggggGgggG
GnGGnGGnGGGnGGnG
nnnnnnnnnnnnnnnn
nnNnnnnnnnNnnnnn
nnnnnnNnnnnnnnNn
nNnnnnnnnnnnnnnn
nnnnnnnnNnnnnnnn
nnnnNnnnnnnnNnnn
nnnnnnnnnnnnnnnn
nNnnnnnnnNnnnnnn
nnnnnnNnnnnnnnnN
"""
MOON = """
...ffff...
..ffwwff..
.ffffffcf.
fffcffffff
fffffffcff
ffcfffffff
ffffffcfff
.ffcfffff.
..ffffff..
...ffff...
"""
STORM = """
.......llll.....llll.......
....lllllllll.lllllllll....
..lllllllllllllllllllllll..
.lllllllllllllllllllllllll.
llllkkllllllllllllllkkllll.
lllllrkkllllllllllkkrlllll.
lllllrrlllllllllllllrrllll.
llllllllllkkkkkkkllllllllll
.llllllllkllllllllkllllll..
..eeeeeeeeeeeeeeeeeeeeee...
...b...b...b...b...b...b...
"""
BOLT = """
..yyy.
.yyy..
yyy...
yyyyy.
..yyy.
.yyy..
.yy...
yy....
"""
BOAT = """
..........r.........
..........k.........
..........k.........
......wwwwkwww......
......wbbwkwbbw.....
......wwwwwwwww.....
rrrrrrrrrrrrrrrrrrrr
.rwwwwwwwwwwwwwwwwr.
..rrrrrrrrrrrrrrrr..
...nnnnnnnnnnnnnn...
"""
FISH = ["""
..xx....
.xxxx.x.
xkxxxxx.
.xxxx.x.
..xx....
""", """
..xx....
.xxxx..x
xkxxxxxx
.xxxx..x
..xx....
"""]
LIGHTHOUSE = """
....kk....
...kyyk...
..kyyyyk..
..kkkkkk..
...rrrr...
...rrrr...
...wwww...
...wwww...
..rrrrrr..
..rrrrrr..
..wwwwww..
..wwwwww..
..rrrrrr..
.rrrrrrrr.
.wwwwwwww.
.wwwwwwww.
.rrrrrrrr.
eeeeeeeeee
"""
WAVE = """
....ww......ww..
..wbbbw...wbbbw.
bbbbbbbbbbbbbbbb
BBbbBBBBBBbbBBBB
"""
CASTLE = """
k.k.k......k.k.k
wwwww......wwwww
wcwcw.rr...wcwcw
wwwww.rrr..wwwww
wwwww.r....wwwww
wwwwwwwwwwwwwwww
wcwwwwwkkwwwwwcw
wwwwwwkkkkwwwwww
wwwwwwkkkkwwwwww
wwwwwwkkkkwwwwww
"""
FLAG2 = """
k.k.k......k.k.k
wwwww......wwwww
wcwcw.rrr..wcwcw
wwwww.rr...wwwww
wwwww.r....wwwww
wwwwwwwwwwwwwwww
wcwwwwwkkwwwwwcw
wwwwwwkkkkwwwwww
wwwwwwkkkkwwwwww
wwwwwwkkkkwwwwww
"""

ICONS8 = {  # 'x' takes the ink colour passed in
    "star": "...xx...\n...xx...\nxxxxxxxx\n.xxxxxx.\n..xxxx..\n.xx..xx.\nxx....xx",
    "linkedin": "xxxxxxxx\nx.xxxxxx\nxxxxxxxx\nx.x..xxx\nx.x.x.xx\nx.x.xx.x\nx.x.xx.x\nxxxxxxxx",
    "mail": "xxxxxxxx\nxx....xx\nx.x..x.x\nx..xx..x\nx......x\nxxxxxxxx",
    "scroll": ".xxxxx..\n.x...xx.\n.x.xx.x.\n.x....x.\n.x.xxxx.\n.x....x.\n.x.xx.x.\n.xxxxxx.",
    "sword": "......ww\n.....wcw\n....wcw.\n.n.wcw..\n..ncw...\n..nn....\n.n..n...\nn.......",
    "shield": ".bbbbbb.\nbwwbbbbb\nbwbbbbbb\nbbbbbbbb\nbbbbbbbb\n.bbbbbb.\n..bbbb..\n...bb...",
    "gear": "...cc...\n.c.cc.c.\n..cccc..\ncccu.ccc\ncccu.ccc\n..cccc..\n.c.cc.c.\n...cc...",
    "gem": "..pppp..\n.pPPPPp.\npPwPPPPp\npPPPPPPp\n.pPPPPp.\n..pPPp..\n...pp...",
    "potion": "...nn...\n...ww...\n..w..w..\n.wggggw.\nwgggwggw\nwggggggw\n.wggggw.\n..wwww..",
    "phone": ".kkkkk..\n.kbbbk..\n.kbwbk..\n.kbbbk..\n.kbbbk..\n.kkckk..",
    "chip": ".c.c.c..\nceeeeec.\n.eyeee..\nceeeeec.\n.eeeee..\nceeeeec.\n.c.c.c..",
    "wrench": ".c...c..\n.cc.cc..\n..ccc...\n...c....\n...c....\n...c....\n..ccc...",
}

ICONS16 = {
    "house": """
.......rr.......
......rrrr......
.....rrrrrr.....
....rrrrrrrr....
...rrrrrrrrrr...
....wwwwwwww....
....wbbwwbbw....
....wbbwwbbw....
....wwwwwwww....
....wwwnnwww....
....wwwnnw..ccc.
....wwwnnw.cbbbc
..........cbwbbc
..........cbbbbc
...........ccccn
..............nn
""",
    "pill": """
................
..........kkk...
.........krrrk..
........krrrrrk.
.......krrrrrrk.
......kwkrrrrk..
.....kwwwkrrk...
....kwwwwwkk....
...kwwwwwwk.....
..kwwwwwwk......
..kwwwwwk.......
...kkkkk........
...........PP.PP
..........PPPPPP
...........PPPP.
............PP..
""",
    "calendar": """
................
...c...c...c....
.kkckkkckkkckkk.
.krrrrrrrrrrrrk.
.krrrrrrrrrrrrk.
.kwwwwwwwwwwwwk.
.kwgwwgwwrwwgwk.
.kwwwwwwwwwwwwk.
.kwgwwrwwgwwgwk.
.kwwwwwwwwwwwwk.
.kwgwwgwwgwwwwk.
.kwwwwwwwwwwwwk.
.kkkkkkkkkkkkkk.
""",
    "robot": """
..........wwwww.
.......y.wkwkwkw
.......k..wwwww.
...kkkkkkkkkw...
...kcccccccck...
...kcbbcccbbck..
...kcbbcccbbck..
...kcccccccck...
...kcckkkkcck...
...kcccccccck...
...kkkkkkkkkk...
.....kcccck.....
...kkcccccckk...
...kccccccccck..
""",
    "nfc": """
................
.kkkkkkk........
.keeeeek....l...
.kbbbbbk..l..l..
.kbbbbbk.l..l.l.
.kbwbbbk.l..l.l.
.kbbbbbk.l..l.l.
.kbbbbbk..l..l..
.keeeeek....l...
.keekeek........
.kkkkkkk..yyyyyy
..........yooooy
..........yyyyyy
""",
}


def qr_icon(seed=3):
    """A 16x16 QR-looking pattern (it doesn't scan)."""
    rng = random.Random(seed)
    g = [["w"] * 16 for _ in range(16)]
    for y in range(1, 15):
        for x in range(1, 15):
            g[y][x] = "k" if rng.random() < .45 else "w"
    for ox, oy in ((1, 1), (10, 1), (1, 10)):
        for y in range(5):
            for x in range(5):
                edge = x in (0, 4) or y in (0, 4)
                core = 1 < x < 3 and 1 < y < 3
                g[oy + y][ox + x] = "k" if edge or core else "w"
        for i in range(-1, 6):  # quiet zone
            for yy, xx in ((oy - 1, ox + i), (oy + 5, ox + i), (oy + i, ox - 1), (oy + i, ox + 5)):
                if 0 <= yy < 16 and 0 <= xx < 16:
                    g[yy][xx] = "w"
    return ["".join(r) for r in g]


ICONS16["qr"] = qr_icon()

# =====================================================================
# FONTS
# =====================================================================
FONT_SPECS = {
    "pixel": ("PressStart2P-Regular.ttf", None),
    "body": ("VT323-Regular.ttf", None),
}
STATS_CHARSET = "".join(chr(c) for c in range(0x20, 0x7F)) + "·—–’é★♥▶→×©"
STATIC: dict[str, bytes] = {}
METRICS: dict[str, tuple] = {}


def load_fonts():
    for key, (file, axes) in FONT_SPECS.items():
        font = TTFont(SRC_FONTS / file)
        if axes:
            font = instancer.instantiateVariableFont(font, axes)
        buf = io.BytesIO()
        font.save(buf)
        STATIC[key] = buf.getvalue()
        f = TTFont(io.BytesIO(STATIC[key]))
        METRICS[key] = (f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)


def woff(key: str, chars: str) -> bytes:
    font = TTFont(io.BytesIO(STATIC[key]))
    opts = subset.Options()
    opts.layout_features = ["kern", "liga", "calt", "ccmp", "locl"]
    opts.hinting = False
    sub = subset.Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO()
    font.save(buf)
    return buf.getvalue()


def width(s: str, font: str, size: float, ls: float = 0.0) -> float:
    cmap, hmtx, upm = METRICS[font]
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        if g is None:
            raise SystemExit(f"'{ch}' is not in the {font} font — rephrase {s!r}")
        total += hmtx[g][0]
    return total * size / upm + ls * len(s)


def wrap(s: str, font: str, size: float, max_w: float) -> list[str]:
    lines, cur = [], ""
    for word in s.split():
        trial = f"{cur} {word}".strip()
        if cur and width(trial, font, size) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    return lines + ([cur] if cur else [])


def finish(name, w, h, title, desc, body, css=""):
    faces = "\n".join(th.font_face(k, woff(k, "".join(sorted(chars)))) for k, chars in th.USED.items())
    th.USED.clear()
    path = OUT / f"{name}.svg"
    path.write_text(document(w, h, title, desc, "\n".join(body), "\n".join(css), faces), encoding="utf-8")
    return path


def ink(rows, colour):
    return pixels(rows, 0, 0, 1, pal={**PAL, "x": PAL[colour]})


def icon8(name, x, y, px, colour="k", attrs=""):
    return pixels(ICONS8[name], x, y, px, pal={**PAL, "x": PAL[colour]}, attrs=attrs)


def chip(x, y, label, border, h=26, size=20):
    w = width(label, "body", size) + 18
    return (f'<path class="px" d="{notched(x, y, w, h, 2)}" fill="{PAL[border]}"/>'
            f'<path class="px" d="{notched(x + 2, y + 2, w - 4, h - 4, 2)}" fill="{SLOT}"/>'
            + text(x + w / 2, y + h / 2 + size * .3, label, "body", size, PAL["w"], "middle")), w


# =====================================================================
# TITLE SCREEN
# =====================================================================
def title_screen():
    W, H = 850, 400
    sx, sy, sw, sh = 6, 6, W - 18, H - 18
    ground = 330
    body, css = [], []
    body.append(panel(0, 0, W - 6, H - 6, border=PAL["B"], fill=SCREEN, bw=6))
    body.append(f'<defs><clipPath id="scr"><path d="{notched(sx, sy, sw, sh, 6)}"/></clipPath>'
                f'<linearGradient id="logo" gradientUnits="userSpaceOnUse" x1="0" y1="{ground - 206}" x2="0" y2="{ground - 158}">'
                f'<stop offset="0" stop-color="{PAL["y"]}"/><stop offset=".42" stop-color="{PAL["y"]}"/>'
                f'<stop offset=".42" stop-color="{PAL["o"]}"/><stop offset=".72" stop-color="{PAL["o"]}"/>'
                f'<stop offset=".72" stop-color="{PAL["r"]}"/><stop offset="1" stop-color="{PAL["r"]}"/></linearGradient></defs>')
    body.append('<g clip-path="url(#scr)">')

    # starfield, two parallax layers
    rng = random.Random(7)
    for li, (count, size, col, op, speed) in enumerate([(50, 2, "c", .5, 18), (22, 3, "w", .85, 42)]):
        pts = [(rng.uniform(0, sw), rng.uniform(sy + 70, ground - 40)) for _ in range(count)]
        rects = "".join(f'<rect x="{n(sx + x + dx)}" y="{n(y)}" width="{size}" height="{size}"/>' for dx in (0, sw) for x, y in pts)
        body.append(f'<g class="px st{li}" fill="{PAL[col]}" fill-opacity="{op}">{rects}</g>')
        css.append(f".st{li}{{animation:st{li} {n(sw / speed)}s linear infinite}}@keyframes st{li}{{to{{transform:translateX(-{sw}px)}}}}")
    body.append(pixels(MOON, 740, 92, 4))

    # HUD
    cols = [34, 262, 470, 668]
    for (label, value), x in zip(HUD, cols):
        body.append(text(x, 40, label, "pixel", 16, PAL["w"]))
        if label == "LIVE":
            body.append(pixels(th.COIN, x, 50, 2))
            body.append(text(x + 22, 66, value, "pixel", 16, PAL["w"]))
        else:
            body.append(text(x, 66, value, "pixel", 16, PAL["w"]))

    # logo
    cx, base = W / 2 - 3, ground - 158
    assert pixel_width(NAME, 48) < sw - 200
    stroke = 'stroke="{c}" stroke-width="10" stroke-linejoin="miter"'
    logo = (text(cx + 6, base + 6, NAME, "pixel", 48, PAL["p"], "middle", attrs=stroke.format(c=PAL["p"]))
            + text(cx, base, NAME, "pixel", 48, PAL["k"], "middle", attrs=stroke.format(c=PAL["k"]))
            + f'<g class="g1">{text(cx, base, NAME, "pixel", 48, PAL["b"], "middle")}</g>'
            + f'<g class="g2">{text(cx, base, NAME, "pixel", 48, PAL["r"], "middle")}</g>'
            + text(cx, base, NAME, "pixel", 48, "url(#logo)", "middle"))
    body.append(f'<g class="drop">{logo}</g>')
    css.append(".drop{animation:drop 1.2s steps(16) .15s both}"
               "@keyframes drop{0%{transform:translateY(-240px)}55%{transform:none}70%{transform:translateY(-18px)}85%,100%{transform:none}}"
               ".g1,.g2{opacity:0;animation:g1 5.5s steps(1) infinite}.g2{animation-name:g2}"
               "@keyframes g1{0%,90%{opacity:0;transform:none}91%{opacity:.9;transform:translate(-6px,2px)}93%{opacity:.9;transform:translate(5px,-2px)}95%,100%{opacity:0;transform:none}}"
               "@keyframes g2{0%,90%{opacity:0;transform:none}91%{opacity:.9;transform:translate(6px,-1px)}93%{opacity:.9;transform:translate(-4px,2px)}95%,100%{opacity:0;transform:none}}")
    body.append(text(cx, ground - 116, SUBTITLE, "pixel", 16, PAL["b"], "middle"))

    parts = [f'<g class="blink">{text(cx, ground - 72, p, "pixel", 16, PAL["w"], "middle")}</g>' for p in PROMPTS]
    svg, c = frames(parts, 3.2 * len(PROMPTS), "msg")
    body.append(svg)
    css.append(c)

    # palms, slow parallax
    pw, ph = size_of(PALM)
    dark = {**PAL, "G": "#0f3b2c", "g": "#17583b", "n": "#4d2c1c", "N": "#2e1a10"}
    palms = "".join(pixels(PALM, sx + x + dx, ground - ph * 3, 3, pal=dark) for dx in (0, sw) for x in (40, 250, 470, 640))
    body.append(f'<g class="palms">{palms}</g>')
    css.append(f".palms{{animation:palms {n(sw / 30)}s linear infinite}}@keyframes palms{{to{{transform:translateX(-{sw}px)}}}}")

    # scrolling ground
    tile = 64
    tiles = "".join(pixels(GROUND, sx + i * tile, ground, 4) for i in range(math.ceil(sw / tile) + 2))
    body.append(f'<g class="ground">{tiles}</g>')
    css.append(f".ground{{animation:ground .5s linear infinite}}@keyframes ground{{to{{transform:translateX(-{tile}px)}}}}")
    body.append(text(cx + 2, H - 22, COPYRIGHT, "pixel", 8, PAL["k"], "middle"))
    body.append(text(cx, H - 24, COPYRIGHT, "pixel", 8, PAL["f"], "middle"))

    # ? block, coin, bug and the hero, all on one 6 s loop
    px = 4
    hx, hy = 90, ground - 16 * px
    block_x, block_y = hx + 32 - 15, hy - 64 - 30
    body.append(f'<g class="bump">{pixels(QBLOCK, block_x, block_y, 3)}</g>')
    coin, c = frames([pixels(f, block_x + 3, block_y - 26, 3) for f in COIN_FRAMES], .45, "spin")
    body.append(f'<g class="coinpop">{coin}{text(block_x + 36, block_y - 12, "+1", "pixel", 8, PAL["w"])}</g>')
    css.append(c)

    bug_w, bug_h = 12 * 3, 9 * 3
    bug_x0 = sx + sw + 20
    target = hx + 32 - bug_w / 2
    walk, c = frames([pixels(b, bug_x0, ground - bug_h, 3) for b in BUG], .3, "bugwalk")
    css.append(c)
    body.append(f'<g class="bugmove"><g class="bugalive">{walk}</g>'
                f'<g class="bugdead">{pixels(BUG_FLAT, bug_x0, ground - bug_h, 3, pal={**PAL, "x": PAL["w"]})}</g></g>')
    body.append(f'<g class="score">{text(hx + 32, ground - 40, "+100", "pixel", 8, PAL["y"], "middle")}</g>')

    run, c = frames([pixels(f, hx, hy, px) for f in RUN], .36, "run")
    css.append(c)
    body.append(f'<g class="jump">{run}</g>')
    css.append(f"""
.jump{{animation:jump 6s ease-in-out infinite}}
@keyframes jump{{0%,8.33%{{transform:none}}12.5%{{transform:translateY(-64px)}}16.67%,53.33%{{transform:none}}58.33%{{transform:translateY(-72px)}}63.33%{{transform:translateY(-{bug_h}px)}}66.67%,100%{{transform:none}}}}
.bump{{animation:bump 6s steps(1) infinite}}
@keyframes bump{{0%,12.4%{{transform:none}}12.5%{{transform:translateY(-8px)}}14.5%,100%{{transform:none}}}}
.coinpop{{opacity:0;animation:coinpop 6s infinite}}
@keyframes coinpop{{0%,12.4%{{opacity:0;transform:translateY(14px)}}12.5%{{opacity:1;transform:none}}22%{{opacity:1;transform:translateY(-34px)}}24%,100%{{opacity:0;transform:translateY(-34px)}}}}
.bugmove{{animation:bugmove 6s linear infinite}}
@keyframes bugmove{{0%{{transform:none}}63.33%,100%{{transform:translateX({n(target - bug_x0)}px)}}}}
.bugalive{{animation:bugalive 6s steps(1) infinite}}
@keyframes bugalive{{0%{{opacity:1}}63.33%,100%{{opacity:0}}}}
.bugdead{{opacity:0;animation:bugdead 6s steps(1) infinite}}
@keyframes bugdead{{0%{{opacity:0}}63.33%{{opacity:1}}72%,100%{{opacity:0}}}}
.score{{opacity:0;animation:score 6s infinite}}
@keyframes score{{0%,63.3%{{opacity:0;transform:none}}63.4%{{opacity:1;transform:none}}76%,100%{{opacity:0;transform:translateY(-28px)}}}}""")

    body.append("</g>")
    svg, c = crt("t", sx, sy, sw, sh)
    body.append(svg)
    css.append(c)
    return finish("title", W, H, f"{NAME} — {SUBTITLE}",
                  "An 8-bit arcade title screen: the pixel hero runs past coconut palms, "
                  "headbutts a question block for a coin and stomps a bug. "
                  f"HUD: {HUD[0][1]} public repos, 5 live apps, world KL-07 (Kochi), class of 2027. Open to work.",
                  body, css)


# =====================================================================
# BUTTONS
# =====================================================================
def button(slug, label, icon, face, edge, ink_c, index):
    size = 16
    W = round(16 + 16 + 12 + pixel_width(label, size) + 18)
    H = 50
    body = [
        f'<path class="px" d="{notched(0, 0, W, H, 4)}" fill="{PAL["k"]}"/>',
        f'<path class="px" d="{notched(3, 3, W - 6, H - 6, 3)}" fill="{PAL[edge]}"/>',
        f'<g class="press"><path class="px" d="{notched(3, 3, W - 6, H - 13, 3)}" fill="{PAL[face]}"/>'
        f'<rect class="px" x="7" y="6" width="{W - 14}" height="3" fill="#fff" fill-opacity=".35"/>'
        + icon8(icon, 16, 13, 2, ink_c)
        + text(44, 30, label, "pixel", size, PAL[ink_c]) + "</g>",
    ]
    css = (f".press{{animation:press 4s steps(1) {n(index * .6)}s infinite}}"
           "@keyframes press{0%,8%{transform:none}9%,15%{transform:translateY(5px)}16%,100%{transform:none}}")
    return finish(f"btn-{slug}", W, H, label.title(), f"{label.title()} button", body, [css])


# =====================================================================
# PLAYER CARD
# =====================================================================
def player_card():
    W = 850
    body, css = [], []
    top = 16
    x0, vx = 244, 384
    rows_y = [72, 108, 144, 180]
    stat_y = [236, 270, 304, 338]
    H = stat_y[-1] + 62
    body.append(panel(0, top, W - 6, H - top - 6))
    body.append(tab(24, top, "PLAYER 1", PAL["y"]))

    # portrait
    bx, by, bs = 30, 50, 176
    body.append(f'<defs><pattern id="chk" width="32" height="32" patternUnits="userSpaceOnUse">'
                f'<rect width="32" height="32" fill="{SLOT}"/><rect width="16" height="16" fill="{PANEL}"/><rect x="16" y="16" width="16" height="16" fill="{PANEL}"/></pattern></defs>')
    body.append(f'<path class="px" d="{notched(bx, by, bs, bs, 6)}" fill="{PAL["l"]}"/>'
                f'<path class="px" d="{notched(bx + 4, by + 4, bs - 8, bs - 8, 4)}" fill="url(#chk)"/>')
    face, c = frames([pixels(hero(), bx + 8, by + 8, 10)] * 7 + [pixels(hero(blink=True), bx + 8, by + 8, 10)], 4.0, "idle")
    body.append(face)
    css.append(c)
    body.append(f'<g class="blink">{text(bx + bs / 2, by + bs + 34, "P1 READY", "pixel", 16, PAL["g"], "middle")}</g>')

    for (label, value), y in zip(PLAYER, rows_y):
        body.append(text(x0, y, label, "pixel", 16, PAL["l"]))
        body.append(text(vx, y + 2, value, "body", 28, PAL["w"]))
        assert vx + width(value, "body", 28) < W - 40, value
    body.append(f'<path class="px" d="M{x0} {rows_y[-1] + 22}h{W - 40 - x0}" stroke="{SLOT}" stroke-width="4" stroke-dasharray="8 8"/>')

    sprites = {"coin": (th.COIN, 2), "heart": (HEART, 2), "star": (STAR, 2), "phone": (PHONE, 2)}
    k = 0
    for (label, count, icon, colour), y in zip(PLAYER_STATS, stat_y):
        body.append(text(x0, y, label, "pixel", 16, PAL[colour]))
        rows, px = sprites[icon]
        iw, ih = size_of(rows)
        step = iw * px + 6
        for i in range(count):
            body.append(f'<g class="pop" style="animation-delay:{n(.3 + k * .06)}s">{pixels(rows, vx + i * step, y - ih * px + 1, px)}</g>')
            k += 1
        body.append(text(W - 40, y, f"{count:02d}", "pixel", 16, PAL["w"], "end"))
        assert vx + count * step < W - 90, label
    special_y = stat_y[-1] + 40
    body.append(text(bx, special_y, "SPECIAL MOVE", "pixel", 16, PAL["P"]))
    body.append(text(vx, special_y + 2, SPECIAL, "body", 28, PAL["o"]))

    desc = "; ".join(f"{a}: {b}" for a, b in PLAYER) + ". " + "; ".join(f"{a} {c}" for a, c, *_ in PLAYER_STATS) + f". Special move: {SPECIAL}."
    return finish("player", W, H, "Player 1", desc, body, css)


# =====================================================================
# BOSS STAGE
# =====================================================================
def boss_stage():
    B = BOSS
    W = 850
    top = 16
    X, col_w = 32, 380
    body, css = [], []
    desc_lines = wrap(B["desc"], "body", 24, col_w)
    y_desc = 160
    y_pu = y_desc + (len(desc_lines) - 1) * 23 + 38
    y_chips = y_pu + 12
    chip_rows, cx, cy = [], X, y_chips
    for p in B["powerups"]:
        w = width(p, "body", 20) + 18
        if cx + w > X + col_w:
            cx, cy = X, cy + 34
        chip_rows.append((cx, cy, p))
        cx += w + 8
    y_prog = cy + 58
    H = max(y_prog + 44, 360)
    body.append(panel(0, top, W - 6, H - top - 6, border=PAL["r"]))
    body.append(tab(24, top, "BOSS STAGE", PAL["r"]))

    body.append(text(X, 62, B["eyebrow"], "pixel", 8, PAL["l"]))
    for i, line in enumerate(B["title"]):
        body.append(text(X, 96 + i * 28, line, "pixel", 16, PAL["y"]))
    body.append("".join(text(X, y_desc + i * 23, line, "body", 24, PAL["c"]) for i, line in enumerate(desc_lines)))
    body.append(text(X, y_pu, "POWER-UPS", "pixel", 8, PAL["l"]))
    for x, y, p in chip_rows:
        body.append(chip(x, y, p, "b")[0])
    body.append(text(X, y_prog, f"QUEST {B['phase']}/{B['phases']} · {B['phase_label']}", "pixel", 8, PAL["g"]))
    for i in range(B["phases"]):
        cls = "px blink" if i == B["phase"] - 1 else "px"
        fill = PAL["g"] if i < B["phase"] else SLOT
        body.append(f'<rect class="{cls}" x="{X + i * 50}" y="{y_prog + 10}" width="44" height="12" fill="{fill}"/>')

    # the scene
    sx, sy, sw = 440, top + 26, W - 6 - 440 - 26
    sh = H - 6 - 26 - sy
    body.append(f'<path class="px" d="{notched(sx - 4, sy - 4, sw + 8, sh + 8, 6)}" fill="{SLOT}"/>')
    body.append(f'<defs><clipPath id="scene"><path d="{notched(sx, sy, sw, sh, 4)}"/></clipPath></defs><g clip-path="url(#scene)">')
    body.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{SCREEN}"/>')
    rng = random.Random(11)
    stars = "".join(f'<rect x="{n(sx + rng.uniform(0, sw))}" y="{n(sy + rng.uniform(4, sh * .55))}" width="2" height="2"/>' for _ in range(30))
    body.append(f'<g class="px" fill="{PAL["c"]}" fill-opacity=".6">{stars}</g>')
    body.append(f'<rect class="flash" x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{PAL["w"]}" opacity="0"/>')

    sea = round(sy + sh * .6)
    storm_w, _ = size_of(STORM)
    st_x, st_y = sx + (sw - storm_w * 5) / 2 - 20, sy + round(sh * .14)
    hp_x = st_x + 20
    body.append(text(hp_x, st_y - 14, "STORM", "pixel", 8, PAL["w"]))
    body.append(f'<rect class="px" x="{n(hp_x + 48)}" y="{n(st_y - 22)}" width="84" height="10" fill="{PAL["k"]}"/>'
                f'<rect class="px" x="{n(hp_x + 50)}" y="{n(st_y - 20)}" height="6" fill="{PAL["r"]}" width="80">'
                '<animate attributeName="width" dur="16s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;.1;.3;.5;.7;.9" values="80;68;54;40;26;80"/></rect>')
    body.append(f'<g class="hover">{pixels(STORM, st_x, st_y, 5)}</g>')
    body.append(f'<g class="bolt">{pixels(BOLT, st_x + 48, st_y + 58, 5)}{pixels(BOLT, st_x + 72, st_y + 98, 5)}</g>')
    css.append(".hover{animation:hover 1.6s steps(1) infinite}@keyframes hover{50%{transform:translateY(4px)}}"
               ".bolt{opacity:0;animation:bolt 4s steps(1) infinite}@keyframes bolt{0%,70%{opacity:0}71%,73%{opacity:1}74%,75%{opacity:0}76%,79%{opacity:1}80%,100%{opacity:0}}"
               ".flash{animation:flash 4s steps(1) infinite}@keyframes flash{0%,70%{opacity:0}71%{opacity:.14}73%,75%{opacity:0}76%{opacity:.1}78%,100%{opacity:0}}")

    # lighthouse on its rock
    LPX, BPX = 5, 5
    lh_w, lh_h = size_of(LIGHTHOUSE)
    lx = sx + sw - 30 - lh_w * LPX
    ly = sea + 10 - lh_h * LPX
    lamp_x, lamp_y = lx + 5 * LPX, ly + 1.5 * LPX
    beam_l = f'<polygon points="{n(lamp_x)},{n(lamp_y)} {n(lamp_x - 170)},{n(lamp_y - 30)} {n(lamp_x - 170)},{n(lamp_y + 26)}" fill="{PAL["y"]}" fill-opacity=".16"/>'
    beam_r = f'<polygon points="{n(lamp_x)},{n(lamp_y)} {n(lamp_x + 90)},{n(lamp_y - 20)} {n(lamp_x + 90)},{n(lamp_y + 18)}" fill="{PAL["y"]}" fill-opacity=".16"/>'
    beams, c = frames([beam_l, "", beam_r, ""], 2.4, "beam")
    body.append(beams)
    css.append(c)
    body.append(f'<rect class="px" x="{n(lx - 16)}" y="{sea + 6}" width="{lh_w * LPX + 36}" height="{sh}" fill="{PAL["e"]}"/>'
                f'<rect class="px" x="{n(lx - 6)}" y="{sea - 2}" width="{lh_w * LPX + 16}" height="12" fill="{PAL["e"]}"/>')
    body.append(pixels(LIGHTHOUSE, lx, ly, LPX))

    # boat, signal, packet
    boat_x, boat_y = sx + 36, sea + 14 - 10 * BPX
    ant_x, ant_y = boat_x + 10.5 * BPX, boat_y + .5 * BPX
    body.append(f'<g class="bob">{pixels(BOAT, boat_x, boat_y, BPX)}'
                + "".join(f'<rect class="ring r{i}" x="{n(ant_x - 8)}" y="{n(ant_y - 8)}" width="16" height="16" fill="none" stroke="{PAL["g"]}" stroke-width="2"/>' for i in range(2))
                + "</g>")
    css.append(".bob{animation:bob 1.2s steps(1) infinite}@keyframes bob{50%{transform:translateY(4px)}}"
               ".ring{transform-box:fill-box;transform-origin:center;opacity:0;animation:ring 3.2s steps(4) infinite}.r1{animation-delay:.3s}"
               "@keyframes ring{0%{opacity:1;transform:scale(.4)}25%{opacity:0;transform:scale(2.4)}100%{opacity:0}}")
    route = f"M{n(ant_x)} {n(ant_y)} Q{n((ant_x + lamp_x) / 2)} {n(min(ant_y, lamp_y) - 80)} {n(lamp_x)} {n(lamp_y)}"
    steps = 14
    kp = ";".join(n(i / steps) for i in range(steps + 1)) + ";1"
    kt = ";".join(n(i / steps * .5) for i in range(steps + 1)) + ";1"
    body.append(f'<rect class="px" x="-4" y="-4" width="8" height="8" fill="{PAL["g"]}" opacity="0">'
                f'<animateMotion dur="3.2s" repeatCount="indefinite" path="{route}" calcMode="discrete" keyPoints="{kp}" keyTimes="{kt}"/>'
                '<animate attributeName="opacity" dur="3.2s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;.5" values="1;0"/></rect>')
    body.append(f'<g opacity="0">{text(lamp_x - 20, ly - 14, "ALERT SENT!", "pixel", 8, PAL["g"], "middle")}'
                '<animate attributeName="opacity" dur="3.2s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;.5;.9" values="0;1;0"/></g>')

    # under the water
    body.append(f'<rect x="{sx}" y="{sea + 9}" width="{sw}" height="{sh}" fill="{PAL["B"]}"/>')
    for i, (fy, dur, delay, flip) in enumerate([(sea + 50, 9, 0, False), (sea + 92, 12, -5, True)]):
        fish_frames = [pixels(f, 0, 0, 4, pal={**PAL, "x": PAL["o" if i == 0 else "P"]}) for f in FISH]
        swim, c = frames(fish_frames, .6, f"fin{i}")
        css.append(c)
        mirror = ' transform="scale(-1 1)"' if flip else ""
        body.append(f'<g class="swim{i}"><g transform="translate(0 {fy})"><g{mirror}>{swim}</g></g></g>')
        a, b = (sx - 40, sx + sw + 40) if not flip else (sx + sw + 40, sx - 40)
        css.append(f".swim{i}{{animation:swim{i} {dur}s steps({dur * 6}) {delay}s infinite}}"
                   f"@keyframes swim{i}{{from{{transform:translateX({a}px)}}to{{transform:translateX({b}px)}}}}")
    bubbles = "".join(f'<rect class="px bub" style="animation-delay:{-i * .7}s" x="{n(sx + 40 + i * 70)}" y="{sh + sy - 10}" width="4" height="4" fill="{PAL["b"]}"/>' for i in range(5))
    body.append(bubbles)
    css.append(f".bub{{animation:bub 3.5s steps(14) infinite}}@keyframes bub{{from{{transform:none;opacity:.8}}to{{transform:translateY(-{n(sy + sh - 10 - sea - 16)}px);opacity:0}}}}")

    # waves
    wave_tile = 48
    waves = "".join(pixels(WAVE, sx + i * wave_tile, sea, 3) for i in range(math.ceil(sw / wave_tile) + 2))
    body.append(f'<g class="waves">{waves}</g>')
    css.append(f".waves{{animation:waves 1.4s linear infinite}}@keyframes waves{{to{{transform:translateX(-{wave_tile}px)}}}}")
    body.append("</g>")
    svg, c = crt("b", sx, sy, sw, sh, radius=4)
    body.append(svg)
    css.append(c)

    return finish("boss", W, H, "Boss stage: " + " ".join(B["title"]).title(),
                  f"{B['desc']} Power-ups: {', '.join(B['powerups'])}. Quest {B['phase']} of {B['phases']}: {B['phase_label'].lower()}. "
                  "Animation: a fishing boat under a storm sends an alert packet to a lighthouse on shore.",
                  body, css)


# =====================================================================
# LEVEL CARDS
# =====================================================================
def level_card(idx, slug, world, title, status, desc, powerups, colour, icon):
    W = 420
    top = 14
    body, css = [], []
    tx = 124
    tw = W - 6 - tx - 22
    tsize = 16 if pixel_width(title, 16) <= tw else 12
    assert pixel_width(title, tsize) <= tw, title
    lines = wrap(desc, "body", 21, tw)
    assert len(lines) <= 4, f"{title}: {len(lines)} lines"
    H = 236
    body.append(panel(0, top, W - 6, H - top - 6, border=PAL[colour]))
    body.append(tab(20, top, world, PAL[colour], size=8))

    # status badge
    badge = status
    bw = pixel_width(badge, 8) + (30 if status == "LIVE" else 16)
    bx = W - 6 - 20 - bw
    body.append(f'<path class="px" d="{notched(bx, top - 9, bw, 20, 2)}" fill="{PAL[colour]}"/>'
                f'<path class="px" d="{notched(bx + 2, top - 7, bw - 4, 16, 2)}" fill="{PANEL}"/>')
    if status == "LIVE":
        body.append(f'<g class="blink">{pixels(HEART, bx + 8, top - 4, 1.5)}</g>')
        body.append(text(bx + 22, top + 5, badge, "pixel", 8, PAL["g"]))
    else:
        body.append(text(bx + 8, top + 5, badge, "pixel", 8, PAL[colour]))

    # thumbnail
    ix, iy, isz = 22, 44, 88
    body.append(f'<defs><pattern id="chk" width="16" height="16" patternUnits="userSpaceOnUse">'
                f'<rect width="16" height="16" fill="{SLOT}"/><rect width="8" height="8" fill="{PANEL}"/><rect x="8" y="8" width="8" height="8" fill="{PANEL}"/></pattern></defs>')
    body.append(f'<path class="px" d="{notched(ix, iy, isz, isz, 4)}" fill="{PAL[colour]}"/>'
                f'<path class="px" d="{notched(ix + 4, iy + 4, isz - 8, isz - 8, 2)}" fill="url(#chk)"/>')
    rows = ICONS16[icon]
    iw, ih = size_of(rows)
    ipx = 4
    body.append(f'<g class="float" style="animation-delay:{n(-idx * .4)}s">{pixels(rows, ix + (isz - iw * ipx) / 2, iy + (isz - ih * ipx) / 2, ipx)}</g>')
    css.append(".float{animation:float 1.6s steps(1) infinite}@keyframes float{50%{transform:translateY(-4px)}}")

    body.append(text(tx, 64 if tsize == 16 else 62, title, "pixel", tsize, PAL["w"]))
    body.append("".join(text(tx, 90 + i * 20, line, "body", 21, PAL["c"]) for i, line in enumerate(lines)))
    x = 22
    for p in powerups:
        svg, w = chip(x, H - 6 - 22 - 26, p, colour)
        body.append(svg)
        x += w + 8
    assert x < W - 20, title
    body.append(pixels(STAR, W - 6 - 22 - 16, H - 6 - 22 - 20, 2, cls="blink"))
    return finish(f"level-{slug}", W, H, f"{world}: {title.title()}",
                  f"{status.title()}. {desc} Power-ups: {', '.join(powerups)}.", body, css)


# =====================================================================
# INVENTORY
# =====================================================================
def inventory():
    W = 850
    top = 16
    X, slots_x, rh = 30, 156, 46
    y0 = top + 30
    H = y0 + len(INVENTORY) * rh + 22
    body, css = [], []
    body.append(panel(0, top, W - 6, H - top - 6, border=PAL["y"]))
    body.append(tab(24, top, "INVENTORY", PAL["y"]))
    positions = []
    k = 0
    for r, (cat, icon, items) in enumerate(INVENTORY):
        y = y0 + r * rh
        body.append(icon8(icon, X, y + 8, 2))
        body.append(text(X + 26, y + 23, cat, "pixel", 8, PAL["y"]))
        x = slots_x
        for item in items:
            w = width(item, "body", 21) + 16
            assert x + w <= W - 36, f"inventory row {cat} overflows"
            body.append(f'<g class="pop" style="animation-delay:{n(.1 + k * .03)}s">'
                        f'<path class="px" d="{notched(x, y + 2, w, 32, 2)}" fill="{PAL["e"]}"/>'
                        f'<path class="px" d="{notched(x + 2, y + 4, w - 4, 28, 2)}" fill="{SLOT}"/>'
                        + text(x + w / 2, y + 24, item, "body", 21, PAL["w"], "middle") + "</g>")
            positions.append((x, y + 2, w))
            x += w + 7
            k += 1
    # a menu cursor that wanders the slots
    rng = random.Random(5)
    picks = rng.sample(positions, 10)
    kt = ";".join(n(i / len(picks)) for i in range(len(picks)))
    dur = 1.3 * len(picks)
    anim = lambda attr, vals: f'<animate attributeName="{attr}" dur="{n(dur)}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" values="{";".join(n(v) for v in vals)}"/>'
    x, y, w = picks[0]
    body.append(f'<rect class="px blink" x="{n(x - 3)}" y="{n(y - 3)}" width="{n(w + 6)}" height="38" fill="none" stroke="{PAL["y"]}" stroke-width="3">'
                + anim("x", [p[0] - 3 for p in picks]) + anim("y", [p[1] - 3 for p in picks]) + anim("width", [p[2] + 6 for p in picks]) + "</rect>")
    body.append(f'<g>{text(0, 21, "▶", "pixel", 8, PAL["y"], "middle")}'
                f'<animateTransform attributeName="transform" type="translate" dur="{n(dur)}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt}" '
                f'values="{";".join(f"{n(p[0] - 12)} {n(p[1])}" for p in picks)}"/></g>')
    desc = " ".join(f"{c.title()}: {', '.join(i)}." for c, _, i in INVENTORY)
    return finish("inventory", W, H, "Inventory", desc, body, css)


# =====================================================================
# WORLD MAP
# =====================================================================
def world_map():
    W, H = 850, 336
    top_y, low_y = 132, 202
    nodes = [(92 + i * 136, low_y if i % 2 == 0 else top_y) for i in range(len(WORLD_MAP))]
    pts = [nodes[0]]
    for (x1, y1), (x2, y2) in zip(nodes, nodes[1:]):
        mx = (x1 + x2) / 2
        pts += [(mx, y1), (mx, y2), (x2, y2)]
    d = f"M{pts[0][0]} {pts[0][1]}" + "".join(f"L{n(x)} {n(y)}" for x, y in pts[1:])
    seg = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    node_frac = [0.0]
    acc = 0
    for i, s in enumerate(seg):
        acc += s
        if (i + 1) % 3 == 0:
            node_frac.append(acc / total)

    body, css = [], []
    body.append(panel(0, 0, W - 6, H - 6, border=PAL["b"], fill=PAL["B"]))
    body.append(f'<defs><clipPath id="map"><path d="{notched(4, 4, W - 14, H - 14, 4)}"/></clipPath>'
                f'<pattern id="grass" width="24" height="24" patternUnits="userSpaceOnUse"><rect width="24" height="24" fill="{PAL["G"]}"/>'
                f'<rect x="4" y="6" width="4" height="4" fill="{PAL["g"]}" fill-opacity=".5"/><rect x="16" y="16" width="4" height="4" fill="{PAL["g"]}" fill-opacity=".5"/></pattern></defs>'
                '<g clip-path="url(#map)">')
    rng = random.Random(9)
    glints = [(rng.uniform(10, W - 20), rng.choice([rng.uniform(10, 84), rng.uniform(254, H - 20)])) for _ in range(26)]
    g1 = "".join(f'<rect x="{n(x)}" y="{n(y)}" width="8" height="2"/>' for x, y in glints[::2])
    g2 = "".join(f'<rect x="{n(x)}" y="{n(y)}" width="8" height="2"/>' for x, y in glints[1::2])
    svg, c = frames([f'<g class="px" fill="{PAL["b"]}">{g1}</g>', f'<g class="px" fill="{PAL["b"]}">{g2}</g>'], 1.6, "glint")
    body.append(svg)
    css.append(c)

    ix, iy, iw, ih = 36, 96, W - 84, 144
    body.append(f'<path class="px" d="{notched(ix - 6, iy - 6, iw + 12, ih + 12, 12)}" fill="{PAL["f"]}"/>'
                f'<path class="px" d="{notched(ix, iy, iw, ih, 8)}" fill="url(#grass)"/>')
    for x, y in [(ix + 10, iy + 10), (ix + 232, iy + 10), (ix + 520, iy + 10), (ix + 740, iy + 100)]:
        body.append(pixels(PALM, x, y, 2))
    body.append(f'<path d="{d}" fill="none" stroke="{PAL["f"]}" stroke-width="14" stroke-linecap="square" stroke-linejoin="miter"/>'
                f'<path d="{d}" fill="none" stroke="{PAL["o"]}" stroke-width="2" stroke-dasharray="4 8"/>')

    P = 18.0
    walk_total, pause = 11.0, .7
    times, keypts = [0.0], [0.0]
    t = 0.0
    arrive = [0.0]
    for i in range(1, len(node_frac)):
        t += walk_total * (node_frac[i] - node_frac[i - 1])
        times.append(t)
        keypts.append(node_frac[i])
        arrive.append(t)
        if i < len(node_frac) - 1:
            t += pause
            times.append(t)
            keypts.append(node_frac[i])
    times.append(P)
    keypts.append(1.0)

    for i, ((date, title, sub), (x, y)) in enumerate(zip(WORLD_MAP, nodes)):
        last = i == len(WORLD_MAP) - 1
        at = arrive[i] / P
        if last:
            castle_w, castle_h = size_of(CASTLE)
            flag, c = frames([pixels(CASTLE, x - 24, y - 22, 3), pixels(FLAG2, x - 24, y - 22, 3)], .8, "flag")
            body.append(flag)
            css.append(c)
        else:
            body.append(f'<path class="px" d="{notched(x - 15, y - 15, 30, 30, 4)}" fill="{PAL["k"]}"/>'
                        f'<path class="px" d="{notched(x - 12, y - 12, 24, 24, 3)}" fill="{PAL["o"]}">'
                        f'<animate attributeName="fill" dur="{P}s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;{at:.4f};.985" values="{PAL["o"]};{PAL["g"]};{PAL["o"]}"/></path>'
                        + text(x + 1, y + 8, str(i + 1), "pixel", 16, PAL["k"], "middle"))
        lw = max(pixel_width(date, 8), width(title, "body", 22), width(sub, "body", 19)) + 20
        lx = min(max(x - lw / 2, 12), W - 18 - lw)
        ly = 18 if y == top_y else H - 84
        body.append(f'<path class="px" d="{notched(lx, ly, lw, 62, 4)}" fill="{PAL["k"]}" fill-opacity=".55"/>'
                    + text(lx + lw / 2, ly + 17, date, "pixel", 8, PAL["y"], "middle")
                    + text(lx + lw / 2, ly + 38, title, "body", 22, PAL["w"], "middle")
                    + text(lx + lw / 2, ly + 55, sub, "body", 19, PAL["c"], "middle"))

    walk, c = frames([pixels(RUN[0], -16, -30, 2), pixels(RUN[2], -16, -30, 2)], .32, "walk")
    css.append(c)
    kt = ";".join(f"{v / P:.4f}" for v in times)
    kp = ";".join(f"{v:.4f}" for v in keypts)
    body.append(f'<g><animateMotion dur="{P}s" repeatCount="indefinite" path="{d}" calcMode="linear" keyTimes="{kt}" keyPoints="{kp}"/>'
                f'<animate attributeName="opacity" dur="{P}s" repeatCount="indefinite" keyTimes="0;.955;.965;.995;1" values="1;1;0;0;1"/>'
                f"{walk}</g>")
    body.append("</g>")
    desc = " → ".join(f"{a}: {b} ({c})" for a, b, c in WORLD_MAP)
    return finish("worldmap", W, H, "World map", "An overworld map of the journey so far. " + desc, body, css)


# =====================================================================
# CONTINUE?
# =====================================================================
def continue_screen():
    W, H = 850, 200
    body, css = [], []
    body.append(panel(0, 0, W - 6, H - 6, border=PAL["r"], fill=SCREEN))
    cx = (W - 6) / 2
    label = "CONTINUE?"
    lw = pixel_width(label, 32)
    body.append(text(cx - 26, 74, label, "pixel", 32, PAL["w"], "middle"))
    digits = [text(cx - 26 + lw / 2 + 30, 74, str(9 - i), "pixel", 32, PAL["r"], "middle") for i in range(10)]
    svg, c = frames(digits, 10, "count")
    body.append(svg)
    css.append(c)
    body.append(f'<g class="blink">{text(cx, 118, "INSERT COIN ▶ HIRE PLAYER 1", "pixel", 16, PAL["y"], "middle")}</g>')
    ew = width(EMAIL, "body", 32)
    body.append(text(cx, 162, EMAIL, "body", 32, PAL["w"], "middle"))
    for side in (-1, 1):
        spin, c = frames([pixels(f, cx + side * (ew / 2 + 34) - 12, 140, 3) for f in COIN_FRAMES], .45, f"cs{side + 1}")
        body.append(spin)
        css.append(c)
    svg, c = crt("c", 6, 6, W - 18, H - 18)
    body.append(svg)
    css.append(c)
    return finish("continue", W, H, "Continue?", f"Insert coin to hire player 1: {EMAIL}", body, css)


# =====================================================================
def main():
    load_fonts()
    OUT.mkdir(exist_ok=True)
    (OUT / "fonts").mkdir(exist_ok=True)
    for key in FONT_SPECS:
        (OUT / "fonts" / f"{key}.woff").write_bytes(woff(key, STATS_CHARSET))
    (OUT / "fonts" / "metrics.json").write_text(json.dumps({"body_advance": {chr(c): width(chr(c), "body", 1) for c in range(0x20, 0x7F)}}, indent=1))

    made = [title_screen(), player_card(), boss_stage(), inventory(), world_map(), continue_screen()]
    made += [button(*b, i) for i, b in enumerate(BUTTONS)]
    made += [level_card(i, *lv) for i, lv in enumerate(LEVELS)]
    for p in made:
        ElementTree.parse(p)  # GitHub serves these as standalone images, where any XML error breaks them
        print(f"{p.stat().st_size / 1024:6.1f} KB  {p.relative_to(th.ROOT)}")


if __name__ == "__main__":
    main()
