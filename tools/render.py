"""Image helpers shared by the content generators.

Everything here produces files that meet WhatsApp's third-party sticker rules:
  * static sticker: 512x512 WebP, < 100 KB
  * animated sticker: 512x512 animated WebP, < 500 KB, every frame >= 8 ms, total <= 10 s
  * tray icon: 96x96 PNG, < 50 KB
"""
from __future__ import annotations

import io
import math
import os
import random
from functools import lru_cache

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

FONT_DIR = os.environ.get("SM_FONT_DIR", "/home/claude/work/fonts")
SIZE = 512
MARGIN = 16  # WhatsApp recommends a 16 px transparent margin


@lru_cache(maxsize=256)
def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size, layout_engine=ImageFont.Layout.RAQM)


# --------------------------------------------------------------------------- encoding

def encode_webp(img: Image.Image, max_bytes: int, lossless_first: bool = False) -> bytes:
    """Encode a still image as WebP under max_bytes, lowering quality until it fits."""
    if lossless_first:
        b = io.BytesIO()
        img.save(b, "WEBP", lossless=True, method=6)
        if b.tell() < max_bytes:
            return b.getvalue()
    for q in (92, 86, 80, 74, 68, 60, 52, 44, 36):
        b = io.BytesIO()
        img.save(b, "WEBP", quality=q, method=6, alpha_quality=90)
        if b.tell() < max_bytes:
            return b.getvalue()
    raise ValueError("could not fit image under %d bytes" % max_bytes)


def save_sticker(img: Image.Image, path: str) -> int:
    assert img.size == (SIZE, SIZE) and img.mode == "RGBA"
    data = encode_webp(img, 99 * 1024)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)
    return len(data)


def save_thumb(img: Image.Image, path: str, size: int = 160) -> int:
    t = img.copy()
    t.thumbnail((size, size), Image.LANCZOS)
    data = encode_webp(t, 24 * 1024)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").write(data)
    return len(data)


def save_tray(img: Image.Image, path: str) -> int:
    t = fit(img, 96, margin=2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for colors in (None, 128, 64):
        b = io.BytesIO()
        (t if colors is None else t.quantize(colors, method=Image.Quantize.FASTOCTREE)).save(b, "PNG", optimize=True)
        if b.tell() < 48 * 1024:
            open(path, "wb").write(b.getvalue())
            return b.tell()
    raise ValueError("tray too big")


def save_animated(frames: list[Image.Image], durations: list[int], path: str) -> int:
    """Encode an animated 512x512 WebP under 500 KB (drops frames / lowers quality as needed)."""
    frames = [f.convert("RGBA") for f in frames]
    durations = [max(int(d), 10) for d in durations]
    total = sum(durations)
    if total > 10000:  # WhatsApp: max 10 s
        keep, acc = [], 0
        for f, d in zip(frames, durations):
            if acc + d > 10000:
                break
            keep.append((f, d)); acc += d
        frames, durations = [k[0] for k in keep], [k[1] for k in keep]
    for step in (1, 2, 3):
        fs = frames[::step]
        ds = [sum(durations[i:i + step]) for i in range(0, len(durations), step)][: len(fs)]
        for q in (75, 62, 50, 40, 30):
            b = io.BytesIO()
            fs[0].save(b, "WEBP", save_all=True, append_images=fs[1:], duration=ds, loop=0, quality=q, method=4,
                       minimize_size=True, allow_mixed=False)
            if b.tell() < 495 * 1024:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                open(path, "wb").write(b.getvalue())
                return b.tell()
    raise ValueError("animated sticker too big: " + path)


# --------------------------------------------------------------------------- geometry

def trim(img: Image.Image) -> Image.Image:
    bb = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    return img.crop(bb) if bb else img


def fit(img: Image.Image, size: int = SIZE, margin: int = MARGIN) -> Image.Image:
    img = trim(img.convert("RGBA"))
    s = min((size - 2 * margin) / img.width, (size - 2 * margin) / img.height)
    img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    c = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c.alpha_composite(img, ((size - img.width) // 2, (size - img.height) // 2))
    return c


def dilate(alpha: Image.Image, radius: int) -> Image.Image:
    """Round-ish dilation of an alpha mask (blur + threshold is much faster than big MaxFilters)."""
    if radius <= 0:
        return alpha
    a = alpha.filter(ImageFilter.MaxFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(radius / 2.2))
    return a.point(lambda v: 255 if v > 18 else int(v * 255 / 18))


def die_cut(content: Image.Image, border: int = 12, border_color=(255, 255, 255, 255), shadow: bool = True) -> Image.Image:
    """White sticker border + soft shadow around any RGBA content."""
    alpha = content.getchannel("A")
    ring = dilate(alpha, border)
    out = Image.new("RGBA", content.size, (0, 0, 0, 0))
    if shadow:
        sh = Image.new("RGBA", content.size, (0, 0, 0, 0))
        sh.putalpha(ring.point(lambda v: v * 70 // 255))
        sh = sh.filter(ImageFilter.GaussianBlur(5))
        out.alpha_composite(sh, (0, 5))
    white = Image.new("RGBA", content.size, border_color)
    white.putalpha(ring)
    out.alpha_composite(white)
    out.alpha_composite(content)
    return out


# --------------------------------------------------------------------------- text stickers

PALETTES = {
    # name: (gradient top, gradient bottom, inner stroke)
    "sunny": ((255, 214, 64), (255, 140, 0), (120, 50, 0)),
    "cherry": ((255, 112, 150), (226, 24, 84), (110, 0, 40)),
    "ocean": ((88, 205, 255), (30, 120, 230), (10, 40, 110)),
    "mint": ((120, 240, 190), (20, 170, 120), (0, 80, 55)),
    "grape": ((200, 140, 255), (120, 60, 220), (50, 10, 110)),
    "fire": ((255, 190, 60), (240, 40, 40), (110, 10, 10)),
    "night": ((120, 140, 255), (40, 30, 120), (10, 5, 50)),
    "gold": ((255, 236, 150), (210, 150, 30), (100, 60, 0)),
    "emerald": ((80, 210, 120), (0, 120, 70), (0, 50, 30)),
    "rose": ((255, 170, 200), (240, 80, 140), (120, 20, 60)),
    "sky": ((170, 230, 255), (60, 160, 240), (10, 70, 140)),
    "ink": ((125, 125, 150), (35, 35, 50), (0, 0, 0)),
    "lime": ((210, 255, 90), (90, 200, 20), (30, 90, 0)),
    "coral": ((255, 170, 120), (255, 90, 70), (120, 30, 20)),
    "royal": ((90, 120, 255), (40, 50, 200), (10, 15, 90)),
    "teal": ((70, 220, 220), (0, 140, 160), (0, 60, 70)),
}


def gradient(size, top, bottom) -> Image.Image:
    w, h = size
    g = Image.new("RGBA", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    return g.resize((w, h))


def _wrap(text: str, fnt, max_w: int, draw, rtl: bool) -> list[str]:
    if "\n" in text:
        return text.split("\n")
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt, direction="rtl" if rtl else None) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def text_block(text: str, font_name: str, palette: str, box_w: int, box_h: int, rtl: bool = False,
               max_size: int = 150, min_size: int = 40, stroke_ratio: float = 0.085, upper: bool = False,
               line_gap: float = 0.08, lang: str | None = None) -> Image.Image:
    """Render text with gradient fill + dark stroke, auto-sized to fit (box_w x box_h). Returns trimmed RGBA."""
    if upper:
        text = text.upper()
    top, bottom, stroke = PALETTES[palette]
    scratch = ImageDraw.Draw(Image.new("L", (10, 10)))
    direction = "rtl" if rtl else None
    for size in range(max_size, min_size - 1, -4):
        fnt = font(font_name, size)
        sw = max(2, int(size * stroke_ratio))
        lines = _wrap(text, fnt, box_w - 2 * sw, scratch, rtl)
        if len(lines) > 4:
            continue
        boxes = [scratch.textbbox((0, 0), l, font=fnt, stroke_width=sw, direction=direction, language=lang) for l in lines]
        widths = [b[2] - b[0] for b in boxes]
        heights = [b[3] - b[1] for b in boxes]
        gap = int(size * line_gap)
        total_h = sum(heights) + gap * (len(lines) - 1)
        if max(widths) <= box_w and total_h <= box_h:
            break
    W, H = max(widths) + 8, total_h + 8
    fill_mask = Image.new("L", (W, H), 0)
    stroke_mask = Image.new("L", (W, H), 0)
    df, ds = ImageDraw.Draw(fill_mask), ImageDraw.Draw(stroke_mask)
    y = 4
    for l, b, w, h in zip(lines, boxes, widths, heights):
        x = 4 + (W - 8 - w) // 2 - b[0]
        ds.text((x, y - b[1]), l, font=fnt, fill=255, stroke_width=sw, stroke_fill=255, direction=direction, language=lang)
        df.text((x, y - b[1]), l, font=fnt, fill=255, direction=direction, language=lang)
        y += h + gap
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    st = Image.new("RGBA", (W, H), stroke + (255,)); st.putalpha(stroke_mask)
    out.alpha_composite(st)
    gr = gradient((W, H), top, bottom); gr.putalpha(fill_mask)
    out.alpha_composite(gr)
    # glossy highlight on the upper part of the letters
    hl = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    hl_mask = ImageChops.multiply(fill_mask, Image.linear_gradient("L").resize((W, H)).point(lambda v: max(0, 120 - v) if v < 120 else 0))
    hl.putalpha(hl_mask)
    out.alpha_composite(hl)
    return trim(out)


def text_sticker(text: str, font_name: str, palette: str, emoji: Image.Image | None = None, emoji_pos: str = "top",
                 rtl: bool = False, rotate: float = 0.0, upper: bool = False, sub: str | None = None,
                 sub_font: str | None = None, sub_palette: str | None = None, sub_rtl: bool = False,
                 lang: str | None = None, sub_lang: str | None = None) -> Image.Image:
    """Compose a complete 512x512 text sticker with optional emoji accent and second (smaller) line."""
    canvas = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))  # work at 2x for smooth edges
    has_emoji = emoji is not None
    text_h = 560 if not has_emoji or emoji_pos == "corner" else 430
    if sub:
        text_h = (560 if not has_emoji or emoji_pos == "corner" else 520) - 130
    main = text_block(text, font_name, palette, 740 if emoji_pos == "corner" and has_emoji else 880, text_h, rtl=rtl, upper=upper, max_size=300, min_size=80, lang=lang)
    parts = []
    if has_emoji and emoji_pos == "top":
        e = trim(emoji.convert("RGBA"))
        es = (230 if sub else 330) / max(e.size)
        parts.append(e.resize((int(e.width * es), int(e.height * es)), Image.LANCZOS))
    parts.append(main)
    if sub:
        parts.append(text_block(sub, sub_font or font_name, sub_palette or palette, 760, 180, rtl=sub_rtl,
                                max_size=150, min_size=50, lang=sub_lang))
    gap = 18
    total_h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    corner = has_emoji and emoji_pos == "corner"
    y = (1024 - total_h) // 2 + (70 if corner else 0)
    for p in parts:
        x = (1024 - p.width) // 2 - (90 if corner else 0)
        canvas.alpha_composite(p, (max(0, x), y))
        y += p.height + gap
    if corner:
        e = trim(emoji.convert("RGBA"))
        es = 260 / max(e.size)
        e = e.resize((int(e.width * es), int(e.height * es)), Image.LANCZOS).rotate(-12, expand=True, resample=Image.BICUBIC)
        bb = canvas.getbbox() or (0, 0, 1024, 1024)
        ex = min(1024 - e.width, bb[2] - int(e.width * 0.28))
        ey = max(0, bb[1] - int(e.height * 0.72))
        canvas.alpha_composite(e, (ex, ey))
    if rotate:
        canvas = canvas.rotate(rotate, expand=False, resample=Image.BICUBIC)
    cut = die_cut(fit(canvas, 1024, margin=60), border=26)
    return fit(cut, SIZE, MARGIN)


def emoji_sticker(img: Image.Image, outline: bool = False) -> Image.Image:
    """Fluent 3D PNG (256 px) -> 512 sticker. Upscaled in two steps with a light unsharp mask."""
    img = trim(img.convert("RGBA"))
    big = img.resize((img.width * 2, img.height * 2), Image.BICUBIC)
    big = big.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    if outline:
        big = die_cut(fit(big, 1024, margin=60), border=22)
    return fit(big, SIZE, MARGIN + 8)


def seeded(key: str) -> random.Random:
    return random.Random(key)


def angle_for(key: str, spread: float = 6) -> float:
    r = seeded(key)
    return round(r.uniform(-spread, spread), 1) if r.random() < 0.7 else 0.0


def contact_sheet(paths: list[str], out: str, cols: int = 6, cell: int = 200, bg=(48, 60, 70)) -> None:
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * cell, rows * cell), bg)
    for i, p in enumerate(paths):
        im = Image.open(p)
        im.seek(0)
        im = im.convert("RGBA")
        im.thumbnail((cell - 8, cell - 8))
        sheet.paste(im, ((i % cols) * cell + 4, (i // cols) * cell + 4), im)
    sheet.save(out)
