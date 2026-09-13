"""Arcade palette, pixel fonts and SVG helpers shared by build.py and stats.py.

Standard library only — the GitHub Action runs stats.py without installing anything.
"""
from __future__ import annotations

import base64
import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"

# PICO-8's sixteen colours, plus skin, hair and three screen darks. One letter
# each, so sprites can be drawn as text.
PAL = {
    "k": "#000000", "B": "#1d2b53", "p": "#7e2553", "G": "#008751",
    "n": "#ab5236", "e": "#5f574f", "c": "#c2c3c7", "w": "#fff1e8",
    "r": "#ff004d", "o": "#ffa300", "y": "#ffec27", "g": "#00e436",
    "b": "#29adff", "l": "#83769c", "P": "#ff77a8", "f": "#ffccaa",
    "s": "#c68642", "S": "#8d5524", "h": "#1f1414", "N": "#6b2c1f",
    "d": "#0b0a18", "D": "#15142b", "u": "#23214a",
}
SCREEN, PANEL, SLOT = PAL["d"], PAL["D"], PAL["u"]

FACES = {
    "pixel": ("Press Start 2P", 400, "ui-monospace,Consolas,monospace"),
    "body": ("VT323", 400, "ui-monospace,Consolas,monospace"),
}

BASE_CSS = """
%s
.px{shape-rendering:crispEdges}
.blink{animation:blink 1s steps(1) infinite}
.pop{transform-box:fill-box;transform-origin:center;animation:pop .35s steps(3) both}
@keyframes blink{50%%{opacity:0}}
@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:none}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" % "\n".join(f".f-{k}{{font-family:'{fam}',{fb};font-weight:{w}}}" for k, (fam, w, fb) in FACES.items())

# Characters recorded by text() since the last reset — build.py subsets fonts to these.
USED: dict[str, set[str]] = {}


def n(v: float) -> str:
    return f"{round(v, 2):g}"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text(x, y, s, font, size, fill, anchor="start", ls=0.0, attrs="") -> str:
    USED.setdefault(font, set()).update(s)
    style = f"font-size:{n(size)}px" + (f";letter-spacing:{n(ls)}px" if ls else "")
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    extra = f" {attrs}" if attrs else ""
    return f'<text class="f-{font}" x="{n(x)}" y="{n(y)}" style="{style}" fill="{fill}"{a}{extra}>{esc(s)}</text>'


def pixel_width(s: str, size: float, ls: float = 0.0) -> float:
    """Press Start 2P is monospaced at exactly 1em per glyph."""
    return len(s) * (size + ls)


def font_face(key: str, woff: bytes) -> str:
    fam, weight, _ = FACES[key]
    return (f"@font-face{{font-family:'{fam}';font-weight:{weight};"
            f"src:url(data:font/woff;base64,{base64.b64encode(woff).decode()}) format('woff')}}")


def document(w, h, title, desc, body, css="", fonts="") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" '
        f'role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{esc(title)}</title>\n<desc id="desc">{esc(desc)}</desc>\n'
        f"<style><![CDATA[\n{fonts}\n{BASE_CSS}\n{css}\n]]></style>\n{body}\n</svg>\n"
    )


# ---------------------------------------------------------------- pixels
def art(s: str) -> list[str]:
    return [row for row in textwrap.dedent(s).strip("\n").split("\n")]


def pixels(rows, x, y, px, pal=PAL, attrs="", cls="") -> str:
    """Draw a sprite given as rows of palette letters ('.' is transparent).

    Each colour becomes one <path> of merged horizontal runs.
    """
    if isinstance(rows, str):
        rows = art(rows)
    runs: dict[str, list[str]] = {}
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            ch = row[i]
            k = i + 1
            while k < len(row) and row[k] == ch:
                k += 1
            if ch not in ". ":
                runs.setdefault(ch, []).append(f"M{n(x + i * px)} {n(y + j * px)}h{n((k - i) * px)}v{n(px)}h{n(-(k - i) * px)}z")
            i = k
    paths = "".join(f'<path fill="{pal[ch]}" d="{"".join(d)}"/>' for ch, d in runs.items())
    extra = f" {attrs}" if attrs else ""
    return f'<g class="px{" " + cls if cls else ""}"{extra}>{paths}</g>'


def size_of(rows) -> tuple[int, int]:
    if isinstance(rows, str):
        rows = art(rows)
    return max(len(r) for r in rows), len(rows)


def frames(parts: list[str], dur: float, uid: str) -> tuple[str, str]:
    """Flip-book: show each part in turn, one slot of `dur` each."""
    count = len(parts)
    svg = "".join(
        f'<g class="{uid}" style="animation-delay:{n(-((count - i) % count) / count * dur)}s{";opacity:0" if i else ""}">{p}</g>'
        for i, p in enumerate(parts)
    )
    css = (f".{uid}{{animation:{uid} {n(dur)}s steps(1) infinite}}"
           f"@keyframes {uid}{{0%{{opacity:1}}{n(100 / count)}%,100%{{opacity:0}}}}")
    return svg, css


def notched(x, y, w, h, c=4) -> str:
    return (f"M{n(x + c)} {n(y)}H{n(x + w - c)}V{n(y + c)}H{n(x + w)}V{n(y + h - c)}H{n(x + w - c)}V{n(y + h)}"
            f"H{n(x + c)}V{n(y + h - c)}H{n(x)}V{n(y + c)}H{n(x + c)}Z")


def panel(x, y, w, h, border=PAL["w"], fill=PANEL, bw=4, shadow=True) -> str:
    """A notched NES-style dialog box."""
    out = []
    if shadow:
        out.append(f'<path class="px" d="{notched(x + 6, y + 6, w, h, bw * 2)}" fill="#000" fill-opacity=".45"/>')
    out.append(f'<path class="px" d="{notched(x, y, w, h, bw * 2)}" fill="{border}"/>')
    out.append(f'<path class="px" d="{notched(x + bw, y + bw, w - bw * 2, h - bw * 2, bw)}" fill="{fill}"/>')
    return "".join(out)


def tab(x, y, label, color, fill=PANEL, size=16) -> str:
    """A title that sits on a panel's top border."""
    w = pixel_width(label, size) + 20
    return (f'<rect class="px" x="{n(x)}" y="{n(y - size / 2 - 5)}" width="{n(w)}" height="{n(size + 10)}" fill="{fill}"/>'
            + text(x + 10, y + size / 2, label, "pixel", size, color))


def crt(uid, x, y, w, h, radius=8) -> tuple[str, str]:
    """Scanlines, a vignette and a slow refresh band over a screen area."""
    svg = (f'<defs><pattern id="{uid}sl" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="2" fill="#000" fill-opacity=".22"/></pattern>'
           f'<radialGradient id="{uid}vg" cx=".5" cy=".5" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".6"/></radialGradient>'
           f'<linearGradient id="{uid}rb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
           f'<clipPath id="{uid}cp"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" rx="{radius}"/></clipPath></defs>'
           f'<g clip-path="url(#{uid}cp)" pointer-events="none">'
           f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="url(#{uid}sl)"/>'
           f'<rect class="{uid}rb" x="{n(x)}" y="{n(y - 80)}" width="{n(w)}" height="80" fill="url(#{uid}rb)"/>'
           f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="url(#{uid}vg)"/></g>')
    css = f".{uid}rb{{animation:{uid}rb 7s linear infinite}}@keyframes {uid}rb{{to{{transform:translateY({n(h + 80)}px)}}}}"
    return svg, css


def odometer(uid, x, y, value, size, fill, digits=None, font="pixel", delay=0.0, anchor="start", pad=0):
    """Digits that roll up to `value` once on load. Returns (svg, css).

    `digits` holds each digit's advance in em (None = monospaced 1em). The
    resting position is the final number, so with animations off it still reads.
    """
    s = str(value).zfill(pad)
    widths = digits or [1.0] * 10
    lh = size * 1.6
    total = sum(widths[int(ch)] for ch in s) * size
    x0 = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
    svg = [f'<clipPath id="{uid}c"><rect x="{n(x0 - 4)}" y="{n(y - size * 1.05)}" width="{n(total + 8)}" height="{n(size * 1.15)}"/></clipPath>',
           f'<g clip-path="url(#{uid}c)">']
    css = []
    left = x0
    for i, ch in enumerate(s):
        cw = widths[int(ch)] * size
        cx = left + cw / 2
        left += cw
        steps = 10 + int(ch)
        col = "".join(text(cx, y - (steps - j) * lh, str(j % 10), font, size, fill, "middle") for j in range(steps + 1))
        name = f"{uid}{i}"
        css.append(f"@keyframes {name}{{from{{transform:translateY({n(steps * lh)}px)}}to{{transform:none}}}}")
        css.append(f".{name}{{animation:{name} 1.8s steps({steps}) {n(delay + i * .12)}s both}}")
        svg.append(f'<g class="{name}">{col}</g>')
    svg.append("</g>")
    return "".join(svg), "\n".join(css)


def load_metrics() -> dict:
    return json.loads((FONT_DIR / "metrics.json").read_text())


# Sprites stats.py needs too.
COIN = """
..oyyo..
.oyyyyo.
oyywyyyo
oyywyyyo
oyywyyyo
oyyyyyyo
.oyyyyo.
..oooo..
"""
TROPHY = """
.yyyyyyyy.
yyywwyyyyy
y.yywyyy.y
y.yyyyyy.y
.yyyyyyyy.
..yyyyyy..
...oyyo...
....yy....
...oooo...
..nnnnnn..
"""
