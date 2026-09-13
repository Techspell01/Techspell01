#!/usr/bin/env python3
"""Build the animated SVGs in assets/ — a dark and a light variant of each.

    pip install fonttools
    python tools/build.py

Everything personal is in the DATA block below: edit it, rerun, commit assets/.
The stats card and the contribution snake are not built here; the GitHub Action
makes those from live data every day (see tools/stats.py).
"""
from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme as th  # noqa: E402
from theme import THEMES, document, hue, hue_text, n, odometer, text  # noqa: E402

SRC_FONTS = Path(__file__).resolve().parent / "fonts"
OUT = th.ROOT / "assets"

# =====================================================================
# DATA
# =====================================================================
NAME = "Harinand AS"
EYEBROW = "OPEN TO WORK · KOCHI, KERALA, INDIA"
ROLE = "Product engineer · B.Tech AI & ML, class of 2027"
LEAD = ["I take half-formed ideas and push them", "until they have a URL."]
TYPED = [  # keep each under ~45 characters
    "shipping 14 public repos since March 2026",
    "5 of them live on Vercel, not just READMEs",
    "ex-intern @ Litmus7 · LangGraph + Qdrant RAG",
    "now: offline capsize detection on an ESP32",
    "open to internships & junior roles",
]

# Cycled through the browser window in the header.
LIVE = [
    ("Campus Hub", "campus-hub-eight-rouge.vercel.app", "QR passes that expire in 30 seconds", "teal"),
    ("Adukala.AI", "adukala-ai.vercel.app", "Dinner from what's left in the fridge", "saffron"),
    ("PG Finder", "pgfinder-mu.vercel.app", "Student housing, minus the forwards", "indigo"),
    ("MedReminder", "medreminder-tawny.vercel.app", "Missed doses, noticed by family", "rose"),
    ("BunkerMe", "bunkerme.vercel.app", "Attendance maths as an offline PWA", "violet"),
]

STATS = [  # (number, label, sub-label, hue)
    (14, "PUBLIC REPOS", "since March 2026", "teal"),
    (5, "LIVE ON VERCEL", "deployed, not demoed", "saffron"),
    (2, "AI & ML INTERNSHIPS", "Litmus7 · Cognifyz", "violet"),
    (2, "NATIVE MOBILE APPS", "React Native · Expo", "rose"),
]

BUTTONS = [  # (file slug, label, icon, hue)
    ("portfolio", "Portfolio", "globe", "saffron"),
    ("linkedin", "LinkedIn", "linkedin", "indigo"),
    ("email", "Email", "mail", "rose"),
    ("resume", "Résumé", "doc", "teal"),
]

BUILDING = dict(
    eyebrow="NOW BUILDING · FINAL-YEAR PROJECT",
    title="Fishing Boat Safety System",
    desc=("Capsize and distress detection for small Kerala fishing boats. A Random Forest "
          "runs on the ESP32 itself and relays a three-state alert to shore over LoRa, "
          "so it works exactly where there is no signal."),
    chips=["ESP32", "C/C++", "emlearn", "LoRa", "FastAPI", "React"],
    phase=1, phases=7, phase_label="SENSING RIG",
    hue="cyan",
)

PROJECTS = [  # (slug, title, eyebrow, status, description, chips, hue)
    ("campus-hub", "Campus Hub", "FULL-STACK · POSTGRES", "LIVE",
     "Events, QR ticketing and volunteer duty rosters for a college, with check-in codes that rotate every 30 seconds.",
     ["Next.js 16", "TypeScript", "PostgreSQL", "Drizzle"], "teal"),
    ("adukala", "Adukala.AI", "AI · COOKING", "LIVE",
     "Tell it what's actually left in your fridge and it returns something you can cook tonight, not a shopping list.",
     ["React", "Vite", "Gemini", "Groq"], "saffron"),
    ("pg-finder", "PG Finder", "SEARCH · STUDENT HOUSING", "LIVE",
     "Student housing search that replaces a pile of WhatsApp forwards and dead phone numbers with one box.",
     ["React", "TypeScript", "Tailwind", "Gemini"], "indigo"),
    ("medreminder", "MedReminder Circle", "HEALTH · REALTIME", "LIVE",
     "Medication reminders shared with the family members who would actually notice a missed dose.",
     ["React", "Firebase", "Firestore", "PWA"], "rose"),
    ("quriobot", "Quriobot", "MOBILE · AI", "MOBILE",
     "A conversational assistant with speech and camera input, built as a native app rather than one more tab.",
     ["React Native", "Expo", "TypeScript"], "violet"),
    ("nfc-habit-tracker", "NFC Habit Tracker", "HARDWARE · ANDROID", "NFC",
     "Log a habit by tapping your phone on a physical NFC tag. Nothing to open, no streak to guilt you.",
     ["Android", "NFC", "JavaScript"], "lime"),
]

TOOLBOX = [  # (group, hue, chips) — the things skillicons has no icon for
    ("AI & LLMs", "violet", ["Gemini API", "Claude API", "Groq API", "LangGraph", "Qdrant · RAG", "Prompt engineering"]),
    ("Data & ML", "teal", ["pandas", "NumPy", "Streamlit", "Folium", "seaborn", "TF-IDF", "BigQuery"]),
    ("Mobile", "rose", ["React Native", "Expo Router", "EAS Build", "Reanimated", "NFC", "Speech & TTS"]),
    ("Edge · now", "saffron", ["ESP32", "C/C++", "PlatformIO", "emlearn", "LoRa", "Raspberry Pi"]),
]

TIMELINE = [  # (date, title, sub, hue)
    ("JUL 2024", "Made the account", "then nineteen quiet months", "indigo"),
    ("MAR 2026", "First two repos public", "a Flask app and a PWA in 48 hours", "coral"),
    ("JUN 2026", "Two AI & ML internships", "Litmus7 on-site, Cognifyz remote", "violet"),
    ("AUG 2026", "Three apps in three days", "all deployed, all live on Vercel", "saffron"),
    ("SEP 2026", "Campus Hub, in a week", "~10k lines of TypeScript, one deploy", "teal"),
    ("NOW", "Boat safety system", "final-year project, sensing rig first", "cyan"),
]

# =====================================================================
# FONTS
# =====================================================================
FONT_SPECS = {
    "display": ("Bricolage-var.ttf", {"wght": 800, "opsz": 96, "wdth": 100}),
    "title": ("Bricolage-var.ttf", {"wght": 700, "opsz": 32, "wdth": 100}),
    "sans": ("Instrument-var.ttf", {"wght": 400, "wdth": 100}),
    "semi": ("Instrument-var.ttf", {"wght": 600, "wdth": 100}),
    "mono": ("DMMono-500.ttf", None),
}
# What stats.py may need to draw, since it can't subset at runtime.
STATS_CHARSET = "".join(chr(c) for c in range(0x20, 0x7F)) + "·—–’“”…→é"

STATIC: dict[str, bytes] = {}
METRICS: dict[str, tuple[dict, object, int]] = {}


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
    opts.layout_features = ["kern", "liga", "calt", "ccmp", "locl", "mark", "mkmk"]
    opts.hinting = False
    opts.desubroutinize = True
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
            raise SystemExit(f"'{ch}' is not in the {font} font — rephrase or add a fallback")
        total += hmtx[g][0]
    return total * size / upm + ls * len(s)


def digit_widths(font: str) -> list[float]:
    return [width(str(d), font, 1) for d in range(10)]


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


def finish(name: str, theme: str, w, h, title, desc, body, css=""):
    faces = "\n".join(th.font_face(k, woff(k, "".join(sorted(chars)))) for k, chars in th.USED.items())
    th.USED.clear()
    path = OUT / f"{name}-{theme}.svg"
    path.write_text(document(w, h, title, desc, body, css, faces), encoding="utf-8")
    return path


def rgba(name, a):
    return f'fill="{hue(name)}" fill-opacity="{n(a)}"'


def chip_row(x, y, items, hue_name, t, font="mono", size=10.5, h=22, gap=6, padx=9, max_x=None, cls=""):
    """Pill chips on one baseline row. Returns (svg, right edge)."""
    out = []
    for item in items:
        w = width(item, font, size) + padx * 2
        if max_x and x + w > max_x:
            break
        c = f' class="{cls}"' if cls else ""
        out.append(
            f'<g{c}><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{h}" rx="{h / 2}" {rgba(hue_name, .12)} '
            f'stroke="{hue(hue_name)}" stroke-opacity=".32"/>'
            + text(x + w / 2, y + h / 2 + size * .36, item, font, size, hue_text(hue_name, t), "middle")
            + "</g>"
        )
        x += w + gap
    return "".join(out), x - gap


def card(w, h, t, rx=20, tint=None, stroke=None):
    grad = ""
    fill_over = ""
    if tint:
        grad = (f'<linearGradient id="tint" x1="0" y1="0" x2="1" y2="1">'
                f'<stop offset="0" stop-color="{hue(tint)}" stop-opacity=".13"/>'
                f'<stop offset=".6" stop-color="{hue(tint)}" stop-opacity=".02"/></linearGradient>')
        fill_over = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="url(#tint)"/>'
    border = stroke or t["line"]
    op = ' stroke-opacity=".35"' if stroke else ""
    return (f"<defs>{grad}</defs>"
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="{t["card"]}"/>{fill_over}'
            f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="none" stroke="{border}"{op}/>')


# =====================================================================
# HEADER
# =====================================================================
def typing_timeline(phrases, cw):
    """Per-phrase (time, chars) steps for a type → hold → delete loop."""
    TYPE, DELETE, HOLD, GAP = 0.055, 0.02, 2.3, 0.45
    t, per = 0.35, []
    for p in phrases:
        ev = [(t, 0)]
        for k in range(1, len(p) + 1):
            ev.append((t + k * TYPE, k))
        t += len(p) * TYPE + HOLD
        for k in range(len(p) - 1, -1, -1):
            ev.append((t + (len(p) - k) * DELETE, k))
        t += len(p) * DELETE + GAP
        per.append(ev)
    return per, t


def smil_discrete(events, total, fmt):
    keys, vals = ["0"], [fmt(0)]
    for time, k in events:
        keys.append(f"{time / total:.5f}")
        vals.append(fmt(k))
    return ";".join(keys), ";".join(vals)


def header(theme):
    t = THEMES[theme]
    W, H = 850, 340
    body, css = [], []
    g = t["glow"]

    body.append(f"""<defs>
<clipPath id="cardclip"><rect width="{W}" height="{H}" rx="22"/></clipPath>
<filter id="blur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="54"/></filter>
<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="{t['line2']}"/></pattern>
<radialGradient id="fade" cx=".78" cy=".45" r=".5"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<mask id="dotmask"><rect width="{W}" height="{H}" fill="url(#fade)"/></mask>
<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="14" stdDeviation="14" flood-color="#000" flood-opacity="{.45 if theme == 'dark' else .14}"/></filter>
</defs>
<g clip-path="url(#cardclip)">
<rect width="{W}" height="{H}" fill="{t['card']}"/>
<g filter="url(#blur)">
<circle class="b1" cx="140" cy="20" r="150" fill="{hue('saffron')}" fill-opacity="{n(g)}"/>
<circle class="b2" cx="600" cy="330" r="170" fill="{hue('violet')}" fill-opacity="{n(g * .95)}"/>
<circle class="b3" cx="830" cy="40" r="120" fill="{hue('teal')}" fill-opacity="{n(g * .7)}"/>
</g>
<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#dotmask)" opacity=".75"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="21.5" fill="none" stroke="{t['line']}"/>""")
    css.append("""
.b1{animation:d1 17s ease-in-out infinite alternate}
.b2{animation:d2 21s ease-in-out infinite alternate}
.b3{animation:d3 15s ease-in-out infinite alternate}
@keyframes d1{to{transform:translate(90px,50px)}}
@keyframes d2{to{transform:translate(-110px,-40px)}}
@keyframes d3{to{transform:translate(-60px,70px)}}""")

    # ---- left column
    X = 48
    body.append(f'<g class="rise" style="animation-delay:.05s">'
                f'<circle cx="{X + 5}" cy="59" r="4" fill="{t["live"]}"/>'
                f'<circle class="ping" cx="{X + 5}" cy="59" r="4" fill="none" stroke="{t["live"]}" stroke-width="1.4"/>'
                + text(X + 18, 63, EYEBROW, "mono", 11.5, t["muted"], ls=1.5) + "</g>")
    body.append(f'<g class="rise" style="animation-delay:.15s">' + text(X - 3, 138, NAME, "display", 66, t["ink"], ls=-1.4) + "</g>")
    body.append(f'<g class="rise" style="animation-delay:.28s">' + text(X, 176, ROLE, "semi", 16.5, t["ink2"]) + "</g>")
    lead = "".join(text(X, 208 + i * 23, line, "sans", 15.5, t["muted"]) for i, line in enumerate(LEAD))
    body.append(f'<g class="rise" style="animation-delay:.4s">{lead}</g>')
    for line in [ROLE, *LEAD]:
        assert width(line, "semi", 16.5) < 440, f"header line too wide: {line}"

    # ---- terminal line with typed phrases
    py, ph, pw = 256, 40, 440
    size = 14
    cw = width("0", "mono", size)
    x0 = X + 40
    assert all(x0 + len(p) * cw < X + pw - 12 for p in TYPED), "a TYPED phrase is too long"
    per, total = typing_timeline(TYPED, cw)
    base = py + ph / 2 + size * .36
    term = [f'<rect x="{X}" y="{py}" width="{pw}" height="{ph}" rx="12" fill="{t["card2"]}" fill-opacity=".85" stroke="{t["line"]}"/>',
            text(X + 16, base, "$", "mono", size, t["accent"])]
    defs = []
    for i, (phrase, ev) in enumerate(zip(TYPED, per)):
        keys, vals = smil_discrete(ev, total, lambda k: n(k * cw))
        defs.append(f'<clipPath id="ty{i}"><rect x="{n(x0)}" y="{py}" height="{ph}" width="0">'
                    f'<animate attributeName="width" dur="{n(total)}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{keys}" values="{vals}"/>'
                    f"</rect></clipPath>")
        term.append(f'<g clip-path="url(#ty{i})">' + text(x0, base, phrase, "mono", size, t["ink2"]) + "</g>")
    merged = sorted((e for ev in per for e in ev), key=lambda e: e[0])
    keys, vals = smil_discrete(merged, total, lambda k: n(x0 + k * cw + 1))
    term.append(f'<rect class="blink" x="{n(x0 + 1)}" y="{n(base - 13)}" width="{n(cw * .9)}" height="17" rx="1.5" fill="{t["accent"]}">'
                f'<animate attributeName="x" dur="{n(total)}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{keys}" values="{vals}"/></rect>')
    body.append(f"<defs>{''.join(defs)}</defs>")
    body.append(f'<g class="rise" style="animation-delay:.52s">{"".join(term)}</g>')
    css.append(".blink{animation:blink 1.05s steps(1) infinite}@keyframes blink{50%{opacity:0}}")

    # ---- browser window stack cycling through live projects
    bx, by, bw, bh = 518, 56, 280, 228
    ghost = lambda dx, dy, op: (f'<rect x="{bx + dx}" y="{by + dy}" width="{bw}" height="{bh}" rx="14" fill="{t["card2"]}" '
                                f'stroke="{t["line2"]}" opacity="{op}"/>')
    body.append(f'<g class="float2">{ghost(34, -24, .28)}{ghost(17, -12, .55)}</g>')
    win = [f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="14" fill="{t["card2"]}" stroke="{t["line2"]}" filter="url(#shadow)"/>']
    for i, c in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
        win.append(f'<circle cx="{bx + 18 + i * 14}" cy="{by + 20}" r="4.5" fill="{c}"/>')
    ux, uw = bx + 62, bw - 76
    win.append(f'<rect x="{ux}" y="{by + 9}" width="{uw}" height="22" rx="11" fill="{t["well"]}" stroke="{t["line"]}"/>')
    win.append(f'<line x1="{bx}" y1="{by + 40}" x2="{bx + bw}" y2="{by + 40}" stroke="{t["line"]}"/>')
    hx, hy, hw, hh = bx + 14, by + 54, bw - 28, 96
    win.append(f'<defs><clipPath id="hero"><rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" rx="10"/></clipPath>'
               + "".join(f'<linearGradient id="hg{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{hue(p[3])}"/>'
                         f'<stop offset="1" stop-color="{hue(LIVE[(i + 1) % len(LIVE)][3])}" stop-opacity=".85"/></linearGradient>'
                         for i, p in enumerate(LIVE)) + "</defs>")
    cycle = 3.2 * len(LIVE)
    share = 100 / len(LIVE)
    css.append(f"""
.proj{{opacity:0;animation:proj {n(cycle)}s ease-in-out infinite both}}
.p0{{opacity:1}}
@keyframes proj{{0%{{opacity:0;transform:translateY(8px)}}{n(share * .12)}%{{opacity:1;transform:none}}{n(share * .9)}%{{opacity:1;transform:none}}{n(share)}%{{opacity:0;transform:translateY(-6px)}}100%{{opacity:0}}}}
.float{{animation:float 6s ease-in-out infinite alternate}}
.float2{{animation:float 8s ease-in-out -3s infinite alternate}}
@keyframes float{{to{{transform:translateY(-7px)}}}}
.skel{{animation:skel 1.8s ease-in-out infinite alternate}}
@keyframes skel{{to{{opacity:.45}}}}""")
    for i, (pname, domain, tagline, hname) in enumerate(LIVE):
        assert width(domain, "mono", 9) < uw - 20, f"domain too long: {domain}"
        assert width(tagline, "sans", 11.5) < hw - 30, f"tagline too long: {tagline}"
        win.append(
            f'<g class="proj p{i}" style="animation-delay:{n(i * 3.2)}s">'
            + text(ux + 12, by + 24, domain, "mono", 9, t["ink2"])
            + f'<g clip-path="url(#hero)"><rect x="{hx}" y="{hy}" width="{hw}" height="{hh}" fill="url(#hg{i})"/>'
            f'<circle cx="{hx + hw - 20}" cy="{hy + 6}" r="62" fill="#fff" fill-opacity=".13"/>'
            f'<circle cx="{hx + hw - 20}" cy="{hy + 6}" r="34" fill="#fff" fill-opacity=".12"/></g>'
            + text(hx + 16, hy + 52, pname, "title", 23, "#ffffff", ls=-.3)
            + text(hx + 16, hy + 74, tagline, "sans", 11.5, "#ffffff", attrs='fill-opacity=".9"')
            + "</g>")
    ly = hy + hh + 16
    win.append(f'<rect x="{hx}" y="{ly}" width="58" height="22" rx="11" fill="{t["live"]}" fill-opacity=".14" stroke="{t["live"]}" stroke-opacity=".4"/>'
               f'<circle cx="{hx + 13}" cy="{ly + 11}" r="3" fill="{t["live"]}"/>'
               f'<circle class="ping" cx="{hx + 13}" cy="{ly + 11}" r="3" fill="none" stroke="{t["live"]}"/>'
               + text(hx + 22, ly + 15, "LIVE", "mono", 9.5, t["live"], ls=.8)
               + text(hx + 70, ly + 15, "deployed on Vercel", "sans", 11.5, t["muted"]))
    win.append(f'<g class="skel"><rect x="{hx}" y="{ly + 36}" width="{hw * .78}" height="7" rx="3.5" fill="{t["line"]}"/>'
               f'<rect x="{hx}" y="{ly + 50}" width="{hw * .5}" height="7" rx="3.5" fill="{t["line"]}"/></g>')
    body.append(f'<g class="float">{"".join(win)}</g>')

    return finish("header", theme, W, H,
                  f"{NAME} — product engineer",
                  f"{ROLE}. {' '.join(LEAD)} Cycles through live projects: " + ", ".join(p[0] for p in LIVE) + ".",
                  "\n".join(body), "\n".join(css))


# =====================================================================
# STATS STRIP
# =====================================================================
def stats_strip(theme):
    t = THEMES[theme]
    W, H = 850, 124
    cell = W / len(STATS)
    size = 44
    body, css = [card(W, H, t)], []
    for i, (num, label, sub, hname) in enumerate(STATS):
        x = i * cell + 30
        if i:
            body.append(f'<line x1="{n(i * cell)}" y1="24" x2="{n(i * cell)}" y2="{H - 24}" stroke="{t["line"]}"/>')
        svg, c = odometer(f"s{i}", x - 1, 64, num, size, hue_text(hname, t), digit_widths("display"), delay=.15 + i * .12)
        body.append(svg)
        css.append(c)
        body.append(text(x, 88, label, "mono", 10.5, t["ink2"], ls=1.1))
        body.append(text(x, 106, sub, "sans", 12.5, t["muted"]))
        assert width(label, "mono", 10.5, 1.1) < cell - 40, label
    desc = "; ".join(f"{a} {b.lower()} ({c})" for a, b, c, _ in STATS)
    return finish("stats", theme, W, H, "At a glance", desc, "\n".join(body), "\n".join(css))


# =====================================================================
# BUTTONS
# =====================================================================
ICONS = {
    "globe": '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/>',
    "linkedin": '<rect x="3" y="3" width="18" height="18" rx="4"/><path d="M8 11v6M8 7.5v.01M12 17v-6M12 13.5a2.5 2.5 0 0 1 5 0V17"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m4 7 8 6 8-6"/>',
    "doc": '<path d="M7 3h7l5 5v13H7z"/><path d="M14 3v5h5M10 13h6M10 17h4"/>',
}


def button(slug, label, icon, hname, theme, index):
    t = THEMES[theme]
    size = 15
    lw = width(label, "semi", size)
    aw = width("→", "sans", 15)
    W, H = round(56 + lw + 10 + aw + 20), 50
    col = hue_text(hname, t)
    body = [
        f'<defs><clipPath id="bc"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15"/></clipPath>'
        f'<linearGradient id="sheen" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="#fff" stop-opacity="{.16 if theme == "dark" else .7}"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15" fill="{t["card2"]}"/>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15" {rgba(hname, .07)}/>',
        f'<g clip-path="url(#bc)"><rect class="sh" x="-70" y="-10" width="60" height="{H + 20}" fill="url(#sheen)" transform="skewX(-20)"/></g>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="15" fill="none" stroke="{hue(hname)}" stroke-opacity=".35"/>',
        f'<circle cx="26" cy="25" r="15" {rgba(hname, .15)}/>',
        f'<g transform="translate(17 16) scale(.75)" fill="none" stroke="{col}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round">{ICONS[icon]}</g>',
        text(52, 30, label, "semi", size, t["ink"]),
        f'<g class="arrow">{text(52 + lw + 10, 30, "→", "sans", 15, col)}</g>',
    ]
    css = (f".sh{{animation:sh 7s ease-in-out {n(1.2 + index * .35)}s infinite}}"
           f"@keyframes sh{{0%{{transform:skewX(-20deg) translateX(0)}}18%,100%{{transform:skewX(-20deg) translateX({W + 160}px)}}}}"
           ".arrow{animation:nudge 2.4s ease-in-out infinite}@keyframes nudge{50%{transform:translateX(3px)}}")
    return finish(f"btn-{slug}", theme, W, H, label, f"{label} link", "\n".join(body), css)


# =====================================================================
# NOW BUILDING
# =====================================================================
def wave_path(x0, y, amp, L, count, bottom):
    d = f"M{n(x0)} {n(y)} q{n(L / 4)} {n(-amp)} {n(L / 2)} 0 " + " ".join(f"t{n(L / 2)} 0" for _ in range(count * 2 - 1))
    return d + f" V{n(bottom)} H{n(x0)} Z"


def boat(bx, by, t, hname, main=True):
    cabin = t["ink2"]
    parts = [
        f'<path d="M{bx - 38} {by - 6} H{bx + 42} L{bx + 31} {by + 11} H{bx - 30} Z" fill="{t["accent"]}"/>',
        f'<path d="M{bx - 35} {by - 2} H{bx + 39}" stroke="#fff" stroke-opacity=".55" stroke-width="2"/>',
        f'<rect x="{bx - 20}" y="{by - 24}" width="28" height="18" rx="2.5" fill="{cabin}"/>',
        f'<rect x="{bx - 15}" y="{by - 20}" width="8" height="6" rx="1" fill="{hue(hname)}"/>',
        f'<path d="M{bx + 15} {by - 6} V{by - 48}" stroke="{cabin}" stroke-width="2" stroke-linecap="round"/>',
    ]
    if main:
        parts.append(f'<circle class="tx" cx="{bx + 15}" cy="{by - 50}" r="2.8" fill="#ff5f57"/>')
        parts.append(f'<g fill="none" stroke="{t["accent"]}" stroke-width="1.6" stroke-linecap="round">'
                     f'<path class="arc a1" d="M{bx + 22} {by - 57} a9 9 0 0 1 0 14"/>'
                     f'<path class="arc a2" d="M{bx + 27} {by - 62} a15 15 0 0 1 0 24"/></g>')
    return "".join(parts)


def now_building(theme):
    t = THEMES[theme]
    B = BUILDING
    hname = B["hue"]
    W = 850
    X, tw = 38, 400
    desc_lines = wrap(B["desc"], "sans", 14.5, tw)
    y_desc = 126
    y_chips = y_desc + (len(desc_lines) - 1) * 22 + 22
    y_prog = y_chips + 50
    H = y_prog + 36
    body, css = [card(W, H, t, tint=hname, stroke=hue(hname))], []

    body.append(text(X, 56, B["eyebrow"], "mono", 11, hue_text(hname, t), ls=1.4))
    body.append(text(X, 94, B["title"], "title", 29, t["ink"], ls=-.4))
    body.append("".join(text(X, y_desc + i * 22, line, "sans", 14.5, t["ink2"]) for i, line in enumerate(desc_lines)))
    chips, _ = chip_row(X, y_chips, B["chips"], hname, t)
    body.append(chips)
    label = f"PHASE {B['phase']} / {B['phases']} · {B['phase_label']}"
    body.append(text(X, y_prog, label, "mono", 10.5, t["muted"], ls=1.1))
    seg_w, gap = 44, 6
    for i in range(B["phases"]):
        on = i < B["phase"]
        cls = ' class="cur"' if i == B["phase"] - 1 else ""
        fill = f'fill="{hue(hname)}"' if on else f'fill="{t["line"]}"'
        body.append(f'<rect{cls} x="{X + i * (seg_w + gap)}" y="{y_prog + 10}" width="{seg_w}" height="6" rx="3" {fill}/>')
    css.append(".cur{animation:cur 1.4s ease-in-out infinite alternate}@keyframes cur{to{opacity:.35}}")

    # ---- the scene
    sx, sy, sw, sh = 468, 16, W - 468 - 16, H - 32
    yw = sy + sh * .64
    L = 80
    scene = [f'<defs><clipPath id="scene"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="15"/></clipPath>'
             f'<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{hue(hname)}" stop-opacity="{.2 if theme == "dark" else .16}"/>'
             f'<stop offset="1" stop-color="{hue(hname)}" stop-opacity=".03"/></linearGradient></defs>',
             f'<g clip-path="url(#scene)"><rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="{t["well"]}"/>'
             f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" fill="url(#sky)"/>']
    if t["stars"]:
        pts = [(.08, .12), (.2, .3), (.33, .08), (.45, .22), (.56, .1), (.7, .28), (.83, .12), (.93, .3), (.62, .4), (.14, .45)]
        for i, (px, pyy) in enumerate(pts):
            scene.append(f'<circle class="star" style="animation-delay:{n(i * .37)}s" cx="{n(sx + px * sw)}" cy="{n(sy + pyy * sh * .6)}" r="{1 + (i % 3) * .35}" fill="#fff" fill-opacity=".7"/>')
        css.append(".star{animation:tw 2.6s ease-in-out infinite alternate}@keyframes tw{to{opacity:.15}}")

    count = math.ceil(sw / L) + 3
    scene.append(f'<path class="w1" d="{wave_path(sx, yw - 5, 4, L, count, sy + sh)}" {rgba(hname, .22)}/>')

    # shore and gateway
    tx, ty = sx + sw - 46, yw - 16
    scene.append(f'<path d="M{sx + sw - 104} {yw + 3} C{sx + sw - 80} {yw - 14} {sx + sw - 60} {yw - 16} {sx + sw} {yw - 20} V{sy + sh} H{sx + sw - 104} Z" fill="{t["land"]}"/>')
    scene.append(f'<g stroke="{t["ink2"]}" stroke-width="1.8" stroke-linecap="round" fill="none">'
                 f'<path d="M{tx - 10} {ty} L{tx} {ty - 58} L{tx + 10} {ty}"/><path d="M{tx - 6} {ty - 20} H{tx + 6} M{tx - 3} {ty - 40} H{tx + 3}"/></g>'
                 f'<rect x="{tx + 14}" y="{ty - 12}" width="16" height="12" rx="1.5" fill="{t["ink2"]}"/>'
                 f'<circle cx="{tx}" cy="{ty - 61}" r="3.2" fill="{t["muted"]}">'
                 f'<animate attributeName="fill" dur="3.2s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;.5;.72" values="{t["muted"]};{t["live"]};{t["muted"]}"/></circle>'
                 f'<circle cx="{tx}" cy="{ty - 61}" r="3" fill="none" stroke="{t["live"]}" stroke-width="1.5" opacity="0">'
                 f'<animate attributeName="r" dur="3.2s" repeatCount="indefinite" keyTimes="0;.5;.8;1" values="3;3;18;18"/>'
                 f'<animate attributeName="opacity" dur="3.2s" repeatCount="indefinite" keyTimes="0;.499;.5;.8;1" values="0;0;.9;0;0"/></circle>')
    scene.append(text(sx + sw - 14, ty - 84, "SHORE · GATEWAY", "mono", 8.5, t["muted"], "end", ls=.9))

    bx, by = sx + 92, yw + 3
    scene.append(text(bx - 40, by - 82, "BOAT · ESP32", "mono", 8.5, t["muted"], ls=.9))

    # packet from the boat's antenna to the gateway
    ax, ay = bx + 15, by - 52
    route = f"M{ax} {ay} Q{n((ax + tx) / 2)} {n(min(ay, ty) - 46)} {tx} {ty - 64}"
    scene.append(f'<path class="route" d="{route}" fill="none" stroke="{t["line2"]}" stroke-width="1.4" stroke-dasharray="3 5"/>')
    scene.append(f'<circle r="3.4" fill="{t["accent"]}" opacity="0"><animateMotion dur="3.2s" repeatCount="indefinite" path="{route}" keyPoints="0;1;1" keyTimes="0;.5;1" calcMode="linear"/>'
                 f'<animate attributeName="opacity" dur="3.2s" repeatCount="indefinite" keyTimes="0;.04;.46;.5;1" values="0;1;1;0;0"/></circle>')
    css.append(".route{animation:flow 1.2s linear infinite}@keyframes flow{to{stroke-dashoffset:-16}}"
               ".tx{animation:tx 3.2s steps(1) infinite}@keyframes tx{0%{opacity:1}12%{opacity:.25}24%{opacity:1}36%{opacity:.25}48%,100%{opacity:1}}"
               ".arc{opacity:0;animation:arc 3.2s ease-out infinite}.a2{animation-delay:.14s}@keyframes arc{0%{opacity:0}6%{opacity:1}30%,100%{opacity:0}}")

    # a far boat — the mesh hop
    fx, fy = sx + 200, yw - 3
    scene.append(f'<g opacity=".4" transform="translate({n(fx)} {n(fy)}) scale(.5)"><g>'
                 f'<animateTransform attributeName="transform" type="translate" dur="3.8s" repeatCount="indefinite" values="0 0;0 4;0 0"/>'
                 f'{boat(0, 0, t, hname, main=False)}</g></g>')
    scene.append(f'<path class="w2" d="{wave_path(sx, yw, 5, L, count, sy + sh)}" {rgba(hname, .38)}/>')
    scene.append(f'<g><animateTransform attributeName="transform" type="translate" dur="3.2s" repeatCount="indefinite" values="0 0;0 4;0 0" keyTimes="0;.5;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
                 f'<g><animateTransform attributeName="transform" type="rotate" dur="4.6s" repeatCount="indefinite" values="-5 {bx} {by};5 {bx} {by};-5 {bx} {by}" keyTimes="0;.5;1" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
                 f'{boat(bx, by, t, hname)}</g></g>')
    scene.append(f'<path class="w3" d="{wave_path(sx, yw + 9, 4, L, count, sy + sh)}" {rgba(hname, .7)}/>')
    scene.append("</g>")
    scene.append(f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="15" fill="none" stroke="{hue(hname)}" stroke-opacity=".22"/>')
    css.append(f".w1{{animation:wave 7s linear infinite}}.w2{{animation:wave 4.6s linear infinite reverse}}.w3{{animation:wave 3.2s linear infinite}}"
               f"@keyframes wave{{to{{transform:translateX(-{L}px)}}}}")
    body.append("".join(scene))

    return finish("building", theme, W, H, f"Now building: {B['title']}",
                  f"{B['desc']} Built with {', '.join(B['chips'])}. {label.title()}. "
                  "Animation: a fishing boat rocks on the waves and sends an alert packet to a shore gateway.",
                  "\n".join(body), "\n".join(css))


# =====================================================================
# PROJECT CARDS
# =====================================================================
def project_card(idx, slug, title, eyebrow, status, desc, chips, hname, theme):
    t = THEMES[theme]
    W, H = 420, 200
    X = 24
    body = [card(W, H, t, rx=18, tint=hname, stroke=hue(hname))]
    body.append(f'<defs><clipPath id="cc"><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="18"/></clipPath>'
                f'<linearGradient id="glare" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                f'<stop offset=".5" stop-color="#fff" stop-opacity="{.07 if theme == "dark" else .55}"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>'
                f'<g clip-path="url(#cc)"><rect class="glare" x="-160" y="-40" width="120" height="{H + 80}" fill="url(#glare)" transform="skewX(-18)"/>'
                f'<circle cx="{W - 30}" cy="{H + 10}" r="90" {rgba(hname, .07)}/></g>')
    body.append(text(X, 38, eyebrow, "mono", 10.5, hue_text(hname, t), ls=1.2))

    # status pill
    live = status == "LIVE"
    scol = t["live"] if live else hue_text(hname, t)
    sfill = t["live"] if live else hue(hname)
    pw = width(status, "mono", 9.5, .8) + (30 if live else 20)
    px = W - X - pw
    pill = f'<rect x="{n(px)}" y="22" width="{n(pw)}" height="22" rx="11" fill="{sfill}" fill-opacity=".13" stroke="{sfill}" stroke-opacity=".4"/>'
    if live:
        pill += (f'<circle cx="{n(px + 12)}" cy="33" r="3" fill="{scol}"/>'
                 f'<circle class="ping" style="animation-delay:{n(idx * .3)}s" cx="{n(px + 12)}" cy="33" r="3" fill="none" stroke="{scol}"/>')
    pill += text(px + (21 if live else 10), 37, status, "mono", 9.5, scol, ls=.8)
    body.append(pill)

    body.append(text(X - 1, 80, title, "title", 25, t["ink"], ls=-.3))
    lines = wrap(desc, "sans", 13.5, W - X * 2)
    assert len(lines) <= 3, f"{title}: description is {len(lines)} lines"
    body.append("".join(text(X, 106 + i * 19.5, line, "sans", 13.5, t["ink2"]) for i, line in enumerate(lines)))
    row, _ = chip_row(X, H - 22 - 22, chips, hname, t, max_x=W - X)
    body.append(row)
    css = (f".glare{{animation:glare 9s ease-in-out {n(1 + idx * .7)}s infinite}}"
           f"@keyframes glare{{0%{{transform:skewX(-18deg) translateX(0)}}16%,100%{{transform:skewX(-18deg) translateX({W + 320}px)}}}}")
    return finish(f"project-{slug}", theme, W, H, title, f"{eyebrow.title()}. {desc} Built with {', '.join(chips)}.",
                  "\n".join(body), css)


# =====================================================================
# TOOLBOX
# =====================================================================
def toolbox(theme):
    t = THEMES[theme]
    W = 850
    X, cx0, rh = 30, 190, 52
    H = len(TOOLBOX) * rh + 28
    body, css = [card(W, H, t)], []
    k = 0
    for r, (group, hname, items) in enumerate(TOOLBOX):
        y = 14 + r * rh
        if r:
            body.append(f'<line x1="{X}" y1="{y}" x2="{W - X}" y2="{y}" stroke="{t["line"]}" stroke-dasharray="3 5"/>')
        body.append(f'<rect x="{X}" y="{y + 20}" width="10" height="10" rx="3" fill="{hue(hname)}"/>')
        body.append(text(X + 20, y + 30, group, "title", 15.5, t["ink"]))
        x = cx0
        for item in items:
            w = width(item, "semi", 12.5) + 24
            assert x + w <= W - X, f"toolbox row '{group}' overflows"
            body.append(f'<g class="pop" style="animation-delay:{n(.1 + k * .035)}s">'
                        f'<rect x="{n(x)}" y="{y + 11}" width="{n(w)}" height="28" rx="14" {rgba(hname, .12)} stroke="{hue(hname)}" stroke-opacity=".3"/>'
                        + text(x + w / 2, y + 29.5, item, "semi", 12.5, hue_text(hname, t), "middle") + "</g>")
            x += w + 8
            k += 1
    css.append(".pop{transform-box:fill-box;transform-origin:center;animation:pop .6s cubic-bezier(.3,1.4,.5,1) both}"
               "@keyframes pop{from{opacity:0;transform:scale(.7)}to{opacity:1;transform:none}}")
    desc = " ".join(f"{g}: {', '.join(i)}." for g, _, i in TOOLBOX)
    return finish("toolbox", theme, W, H, "Toolbox", desc, "\n".join(body), "\n".join(css))


# =====================================================================
# TIMELINE
# =====================================================================
def catmull(points):
    segs = []
    pts = [points[0], *points, points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segs.append((p1, c1, c2, p2))
    return segs


def bez_len(seg, steps=240):
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = seg
    total, px, py = 0.0, x0, y0
    for i in range(1, steps + 1):
        u = i / steps
        a, b, c, d = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u ** 3
        x, y = a * x0 + b * x1 + c * x2 + d * x3, a * y0 + b * y1 + c * y2 + d * y3
        total += math.hypot(x - px, y - py)
        px, py = x, y
    return total


def timeline(theme):
    t = THEMES[theme]
    W, H = 850, 288
    up, down = 124, 170
    step = (W - 190) / (len(TIMELINE) - 1)
    # The last node sits low so the runner standing on it clears its label.
    last = len(TIMELINE) - 1
    nodes = [(95 + i * step, down if (last - i) % 2 == 0 else up) for i in range(len(TIMELINE))]
    pts = [(26, 148), *nodes, (W - 26, 148)]
    segs = catmull(pts)
    d = f"M{n(pts[0][0])} {n(pts[0][1])} " + " ".join(
        f"C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(p[0])} {n(p[1])}" for _, c1, c2, p in segs)
    lens = [bez_len(s) for s in segs]
    total = sum(lens)
    fracs = [sum(lens[:i + 1]) / total for i in range(len(TIMELINE))]

    # The runner stops at NOW; the road past it stays grey — that part isn't built yet.
    P, RUN = 15.0, .72
    end = fracs[-1]
    body, css = [card(W, H, t)], []
    body.append(f'<path d="{d}" fill="none" stroke="{t["road"]}" stroke-width="13" stroke-linecap="round"/>')
    body.append(f'<path d="{d}" pathLength="1" fill="none" stroke="{t["accent"]}" stroke-opacity=".85" stroke-width="13" stroke-linecap="round" stroke-dasharray="1 1" stroke-dashoffset="1">'
                f'<animate attributeName="stroke-dashoffset" dur="{P}s" repeatCount="indefinite" keyTimes="0;{RUN};.95;1" values="1;{n(1 - end)};{n(1 - end)};1"/></path>')
    body.append(f'<path d="{d}" fill="none" stroke="{t["card"]}" stroke-width="1.5" stroke-dasharray="5 8" stroke-linecap="round" opacity=".8"/>')

    for i, ((date, title, sub, hname), (x, y), f) in enumerate(zip(TIMELINE, nodes, fracs)):
        at = RUN * f / end
        col = hue(hname)
        body.append(f'<circle cx="{n(x)}" cy="{y}" r="7" fill="none" stroke="{col}" stroke-width="2" opacity="0">'
                    f'<animate attributeName="r" dur="{P}s" repeatCount="indefinite" keyTimes="0;{at:.4f};{min(at + .07, .99):.4f};1" values="7;7;24;24"/>'
                    f'<animate attributeName="opacity" dur="{P}s" repeatCount="indefinite" keyTimes="0;{at - .001:.4f};{at:.4f};{min(at + .07, .99):.4f};1" values="0;0;.9;0;0"/></circle>')
        if i == len(TIMELINE) - 1:
            body.append(f'<circle class="ping" cx="{n(x)}" cy="{y}" r="7" fill="none" stroke="{col}" stroke-width="1.5"/>')
        body.append(f'<circle cx="{n(x)}" cy="{y}" r="7.5" fill="{t["card"]}" stroke="{t["line2"]}" stroke-width="2.5">'
                    f'<animate attributeName="fill" dur="{P}s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;{at:.4f};.96" values="{t["card"]};{col};{t["card"]}"/>'
                    f'<animate attributeName="stroke" dur="{P}s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;{at:.4f};.96" values="{t["line2"]};{col};{t["line2"]}"/></circle>')
        lw = max(width(title, "title", 15), width(sub, "sans", 12))
        cx = min(max(x, lw / 2 + 26), W - lw / 2 - 26)
        ys = (52, 72, 90) if y == up else (216, 236, 254)
        body.append(text(cx, ys[0], date, "mono", 10.5, hue_text(hname, t), "middle", ls=1.2))
        body.append(text(cx, ys[1], title, "title", 15, t["ink"], "middle"))
        body.append(text(cx, ys[2], sub, "sans", 12, t["muted"], "middle"))
        assert lw < step * 2 - 20, f"timeline label too wide: {title}"

    # the runner
    swing = .18
    run_s = RUN * P
    steps = int(run_s / swing)
    keys = [i * swing / P for i in range(steps + 1)] + [RUN + .01, 1]
    leg = lambda amp: ";".join([f"{(amp if i % 2 == 0 else -amp)} 0 0" for i in range(steps + 1)] + ["0 0 0", "0 0 0"])
    kt = ";".join(f"{k:.4f}" for k in keys)
    limb = lambda amp, x2, y2, extra="": (f'<g><animateTransform attributeName="transform" type="rotate" dur="{P}s" repeatCount="indefinite" keyTimes="{kt}" values="{leg(amp)}"/>'
                                         f'<path d="M0 0 L{x2} {y2}" {extra}/></g>')
    ink = t["ink"]
    runner = (
        f'<g stroke="{ink}" stroke-width="2.6" stroke-linecap="round" fill="none">'
        f'<g transform="translate(1 -14)">{limb(30, 0, 12)}{limb(-30, 0, 12)}</g>'
        f'<path d="M1 -14 L3.5 -27"/>'
        f'<g transform="translate(3 -24)">{limb(-34, 0, 9)}{limb(34, 0, 9)}</g>'
        f'<path class="scarf" d="M3 -28 L-6 -26" stroke="{t["accent"]}" stroke-width="2.4"/>'
        f"</g>"
        f'<circle cx="4.6" cy="-32.5" r="4.4" fill="{ink}"/>'
    )
    body.append(f'<g><animateMotion dur="{P}s" repeatCount="indefinite" path="{d}" keyPoints="0;{end:.4f};{end:.4f}" keyTimes="0;{RUN};1" calcMode="linear"/>'
                f'<animate attributeName="opacity" dur="{P}s" repeatCount="indefinite" keyTimes="0;.93;.96;.995;1" values="1;1;0;0;1"/>'
                f'<g transform="translate(0 -3) scale(1.3)">{runner}</g></g>')
    css.append(".scarf{transform-box:fill-box;transform-origin:100% 50%;animation:scarf .3s ease-in-out infinite alternate}"
               "@keyframes scarf{to{transform:rotate(-14deg)}}")
    desc = " → ".join(f"{a}: {b} ({c})" for a, b, c, _ in TIMELINE)
    return finish("timeline", theme, W, H, "The road so far", desc, "\n".join(body), "\n".join(css))


# =====================================================================
def main():
    load_fonts()
    OUT.mkdir(exist_ok=True)
    (OUT / "fonts").mkdir(exist_ok=True)
    for key in FONT_SPECS:
        (OUT / "fonts" / f"{key}.woff").write_bytes(woff(key, STATS_CHARSET))
    (OUT / "fonts" / "metrics.json").write_text(json.dumps(
        {"display_digits": digit_widths("display"), "mono_char": width("0", "mono", 1)}, indent=2))

    made = []
    for theme in THEMES:
        made += [header(theme), stats_strip(theme), now_building(theme), toolbox(theme), timeline(theme)]
        made += [button(*b, theme, i) for i, b in enumerate(BUTTONS)]
        made += [project_card(i, *p, theme) for i, p in enumerate(PROJECTS)]
    for p in made:
        print(f"{p.stat().st_size / 1024:6.1f} KB  {p.relative_to(th.ROOT)}")


if __name__ == "__main__":
    main()
