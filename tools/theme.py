"""Palette, fonts and small SVG helpers shared by build.py and stats.py.

Standard library only — the GitHub Action runs stats.py without installing anything.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "assets" / "fonts"

# Same tokens as the portfolio (techspell01.github.io/portfolio), tuned to sit on
# GitHub's two page backgrounds: #0d1117 in dark mode, #ffffff in light.
THEMES = {
    "dark": dict(
        card="#10131b", card2="#161a26", well="#0b0e15", line="#262b3c", line2="#39405a",
        ink="#edeff8", ink2="#c4c9dc", muted="#8b92ad", accent="#ff9d4d", live="#3ddc97",
        road="#222737", land="#1a1f2d", mix=0.0, glow=0.30, stars=0.9,
    ),
    "light": dict(
        card="#fbfbfe", card2="#ffffff", well="#f1f3f9", line="#dfe2ee", line2="#c3c8dc",
        ink="#13151f", ink2="#3d4256", muted="#6a7089", accent="#e5761f", live="#0f9d68",
        road="#dde1ee", land="#d5dae8", mix=0.36, glow=0.17, stars=0.0,
    ),
}

HUES = dict(
    saffron=(240, 128, 42), rose=(224, 69, 123), teal=(15, 168, 150), violet=(124, 92, 255),
    coral=(236, 90, 82), cyan=(31, 169, 196), indigo=(66, 99, 235), lime=(150, 190, 20),
)

# One static face per family name, so browsers never synthesise a weight.
FACES = {
    "display": ("HA Display", 800, "'Trebuchet MS',system-ui,sans-serif"),
    "title": ("HA Title", 700, "'Trebuchet MS',system-ui,sans-serif"),
    "sans": ("HA Sans", 400, "system-ui,-apple-system,'Segoe UI',sans-serif"),
    "semi": ("HA Semi", 600, "system-ui,-apple-system,'Segoe UI',sans-serif"),
    "mono": ("HA Mono", 500, "ui-monospace,'Cascadia Mono',Consolas,monospace"),
}

BASE_CSS = """
text{font-kerning:normal}
%s
.rise{animation:rise .9s cubic-bezier(.2,.8,.3,1) both}
.ping{transform-box:fill-box;transform-origin:center;animation:ping 2.2s cubic-bezier(0,0,.2,1) infinite}
@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes ping{0%%{transform:scale(1);opacity:.8}75%%,100%%{transform:scale(3);opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
""" % "\n".join(
    f".f-{k}{{font-family:'{fam}',{fb};font-weight:{w}}}" for k, (fam, w, fb) in FACES.items()
)

# Characters recorded by text() since the last reset — build.py subsets fonts to these.
USED: dict[str, set[str]] = {}


def n(v: float) -> str:
    """Compact number for SVG attributes."""
    return f"{round(v, 2):g}"


def parse(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def hexc(rgb) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in rgb)


def hue(name) -> str:
    return hexc(HUES[name])


def hue_text(name, t: dict) -> str:
    """A hue pulled toward ink so small coloured text stays readable on light cards."""
    ink, m = parse(t["ink"]), t["mix"]
    return hexc(tuple(a * (1 - m) + b * m for a, b in zip(HUES[name], ink)))


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def text(x, y, s, font, size, fill, anchor="start", ls=0.0, attrs="") -> str:
    USED.setdefault(font, set()).update(s)
    style = f"font-size:{n(size)}px" + (f";letter-spacing:{n(ls)}px" if ls else "")
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    extra = f" {attrs}" if attrs else ""
    return f'<text class="f-{font}" x="{n(x)}" y="{n(y)}" style="{style}" fill="{fill}"{a}{extra}>{esc(s)}</text>'


def font_face(key: str, woff: bytes) -> str:
    fam, weight, _ = FACES[key]
    b64 = base64.b64encode(woff).decode()
    return f"@font-face{{font-family:'{fam}';font-weight:{weight};src:url(data:font/woff;base64,{b64}) format('woff')}}"


def document(w, h, title, desc, body, css="", fonts="") -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" '
        f'role="img" aria-labelledby="title desc">\n'
        f'<title id="title">{esc(title)}</title>\n<desc id="desc">{esc(desc)}</desc>\n'
        f"<style><![CDATA[\n{fonts}\n{BASE_CSS}\n{css}\n]]></style>\n{body}\n</svg>\n"
    )


def number_width(value, size, digits) -> float:
    return sum(digits[int(ch)] for ch in str(value)) * size


def odometer(uid, x, y, value, size, fill, digits, font="display", delay=0.0, anchor="start"):
    """Digits that roll up to `value` once on load. Returns (svg, css).

    `digits` holds the advance width of 0-9 in em. Every column spins through a
    full 0-9 cycle and lands on its digit. The resting position is the final
    number, so with animations off it still reads correctly.
    """
    s = str(value)
    lh = size * 1.5
    total = number_width(value, size, digits)
    x0 = {"start": x, "middle": x - total / 2, "end": x - total}[anchor]
    svg = [f'<clipPath id="{uid}c"><rect x="{n(x0 - 10)}" y="{n(y - size * .84)}" width="{n(total + 20)}" height="{n(size * 1.06)}"/></clipPath>',
           f'<g clip-path="url(#{uid}c)">']
    css = []
    left = x0
    for i, ch in enumerate(s):
        cw = digits[int(ch)] * size
        cx = left + cw / 2
        left += cw
        steps = 10 + int(ch)
        col = "".join(
            text(cx, y - (steps - j) * lh, str(j % 10), font, size, fill, "middle") for j in range(steps + 1)
        )
        name = f"{uid}{i}"
        css.append(f"@keyframes {name}{{from{{transform:translateY({n(steps * lh)}px)}}to{{transform:none}}}}")
        css.append(f".{name}{{animation:{name} 2.4s cubic-bezier(.16,1,.3,1) {n(delay + i * .09)}s both}}")
        svg.append(f'<g class="{name}">{col}</g>')
    svg.append("</g>")
    return "".join(svg), "\n".join(css)


def load_metrics() -> dict:
    return json.loads((FONT_DIR / "metrics.json").read_text())
