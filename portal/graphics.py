"""Branded slide / social-card rendering with Pillow (used for OG images and video frames)."""
from __future__ import annotations

import glob
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAVY = (11, 31, 58)
NAVY2 = (19, 41, 75)
GOLD = (201, 162, 39)
WHITE = (255, 255, 255)
SOFT = (199, 208, 222)

_FONT_DIR = Path(__file__).parent / "fonts"
_CANDIDATES = {
    "serif": ["Fraunces*.ttf", "/usr/share/fonts/**/DejaVuSerif-Bold.ttf",
              "C:/Windows/Fonts/georgiab.ttf", "/Library/Fonts/Georgia Bold.ttf"],
    "bold": ["Inter*Bold*.ttf", "/usr/share/fonts/**/Roboto-Bold.ttf",
             "/usr/share/fonts/**/DejaVuSans-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf",
             "C:/Windows/Fonts/arialbd.ttf"],
    "regular": ["Inter*Regular*.ttf", "/usr/share/fonts/**/Roboto-Regular.ttf",
                "/usr/share/fonts/**/DejaVuSans.ttf", "C:/Windows/Fonts/segoeui.ttf",
                "C:/Windows/Fonts/arial.ttf"],
}


@lru_cache(None)
def _font_path(kind: str) -> str | None:
    for pat in _CANDIDATES[kind]:
        base = pat if pat.startswith(("/", "C:")) else str(_FONT_DIR / pat)
        hits = sorted(glob.glob(base, recursive=True))
        if hits:
            return hits[0]
    return None


def font(kind: str, size: int):
    path = _font_path(kind)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def _wrap(draw, text, fnt, max_w):
    lines, line = [], ""
    for word in text.split():
        test = f"{line} {word}".strip()
        if draw.textlength(test, font=fnt) <= max_w or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit(draw, text, kind, max_w, max_h, start, minimum, spacing=1.18):
    size = start
    while size >= minimum:
        f = font(kind, size)
        lines = _wrap(draw, text, f, max_w)
        if len(lines) * size * spacing <= max_h:
            return f, lines, size
        size -= 4
    f = font(kind, minimum)
    lines = _wrap(draw, text, f, max_w)
    keep = max(1, int(max_h // (minimum * spacing)))
    if len(lines) > keep:
        lines = lines[:keep]
        lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return f, lines, minimum


def _background(w, h):
    img = Image.new("RGB", (w, h), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(h):  # vertical gradient navy -> navy2
        t = y / h
        d.line([(0, y), (w, y)], fill=tuple(int(NAVY[i] + (NAVY2[i] - NAVY[i]) * t) for i in range(3)))
    # soft gold glow in the top-right corner
    glow = Image.new("L", (w, h), 0)
    gd = ImageDraw.Draw(glow)
    r = int(max(w, h) * 0.45)
    gd.ellipse([w - r, -r, w + r, r], fill=40)
    img.paste(Image.new("RGB", (w, h), (40, 70, 115)), (0, 0), glow)
    return img


def render_card(out: Path, size: tuple[int, int], *, kicker: str, title: str,
                body: str = "", number: str = "", footer: str = "", progress: tuple[int, int] | None = None) -> Path:
    """Draw one branded frame. Layout adapts to landscape or portrait."""
    w, h = size
    portrait = h > w
    img = _background(w, h)
    d = ImageDraw.Draw(img)
    m = int(w * (0.09 if portrait else 0.07))
    unit = min(w, h) / 1080

    # top: kicker + gold rule
    kf = font("bold", int(30 * unit))
    d.text((m, m), kicker.upper(), font=kf, fill=GOLD)
    d.rectangle([m, m + int(52 * unit), m + int(120 * unit), m + int(58 * unit)], fill=GOLD)

    top = m + int(110 * unit)
    bottom = h - m - int(90 * unit)
    max_w = w - 2 * m

    # content is drawn on its own layer, then centred vertically in the free area
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    y = 0
    if number:
        nf = font("serif", int(150 * unit))
        ld.text((m, y), number, font=nf, fill=GOLD)
        y += int(190 * unit)
    avail = bottom - top - y
    if body:
        tf, tl, ts = _fit(ld, title, "serif", max_w, avail * 0.45, int((84 if portrait else 76) * unit), int(40 * unit))
    else:
        tf, tl, ts = _fit(ld, title, "serif", max_w, avail, int((110 if portrait else 96) * unit), int(44 * unit))
    for line in tl:
        ld.text((m, y), line, font=tf, fill=WHITE)
        y += ts * 1.18
    if body:
        y += int(40 * unit)
        bf, bl, bs = _fit(ld, body, "regular", max_w, bottom - top - y, int((52 if portrait else 46) * unit), int(28 * unit), 1.4)
        for line in bl:
            ld.text((m, y), line, font=bf, fill=SOFT)
            y += bs * 1.4
    content_h = min(y, bottom - top)
    offset = top + max(0, ((bottom - top) - content_h) / 2 - int(30 * unit))
    img.paste(layer, (0, int(offset)), layer)

    # footer
    ff = font("regular", int(28 * unit))
    d.text((m, h - m - int(30 * unit)), footer, font=ff, fill=SOFT)
    if progress:
        i, n = progress
        dot = int(12 * unit)
        x = w - m - n * dot * 2.2
        for k in range(n):
            fill = GOLD if k <= i else (70, 90, 125)
            d.ellipse([x, h - m - int(20 * unit), x + dot, h - m - int(20 * unit) + dot], fill=fill)
            x += dot * 2.2
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return out
