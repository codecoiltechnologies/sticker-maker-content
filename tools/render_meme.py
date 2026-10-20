"""Meme layouts. All memes are original captions on openly licensed photos or on Fluent emoji art.

Formats
  caption   white caption panel above the photo (modern meme style; works for Urdu too)
  classic   bold white top/bottom text with black outline on the photo
  compare   two stacked panels, each with its own label (e.g. Expectation / Reality)
  textpost  text card with an emoji reaction image (no photo)
Every photo meme gets a thin credit strip (author + licence) so attribution travels with the image.
"""
from __future__ import annotations

import os
import textwrap

from PIL import Image, ImageDraw, ImageOps

import render as R

W = 1080
BRAND = "Sticker Maker"


def _font(lang, bold=True, size=48):
    if lang == "ur":
        return R.font("noto_nastaliq_urdu_700.ttf", int(size * 0.9))
    return R.font("poppins_800.ttf" if bold else "inter_700.ttf", size)


def _wrap_px(text, fnt, max_w, rtl):
    d = ImageDraw.Draw(Image.new("L", (4, 4)))
    lines = []
    for para in text.split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append(""); continue
        for w in words:
            t = (cur + " " + w).strip()
            if d.textlength(t, font=fnt, direction="rtl" if rtl else None) <= max_w or not cur:
                cur = t
            else:
                lines.append(cur); cur = w
        lines.append(cur)
    return lines


def text_panel(text, width, lang, size=52, pad=44, bg=(255, 255, 255), fg=(20, 20, 24), align="left"):
    rtl = lang == "ur"
    for s in range(size, 26, -2):
        fnt = _font(lang, size=s)
        lines = _wrap_px(text, fnt, width - 2 * pad, rtl)
        if len(lines) <= 6:
            break
    lh = int(fnt.size * (1.9 if rtl else 1.28))
    h = pad * 2 + lh * len(lines) - (int(fnt.size * 0.28) if not rtl else 0)
    img = Image.new("RGB", (width, h), bg)
    d = ImageDraw.Draw(img)
    y = pad - (int(fnt.size * 0.12) if not rtl else int(fnt.size * 0.35))
    for line in lines:
        tw = d.textlength(line, font=fnt, direction="rtl" if rtl else None)
        x = width - pad - tw if (rtl or align == "right") else ((width - tw) / 2 if align == "center" else pad)
        d.text((x, y), line, font=fnt, fill=fg, direction="rtl" if rtl else None, language="ur" if rtl else None)
        y += lh
    return img


def credit_strip(width, credit: dict | None):
    h = 34
    img = Image.new("RGB", (width, h), (24, 24, 28))
    d = ImageDraw.Draw(img)
    f = R.font("inter_700.ttf", 17)
    left = ""
    if credit:
        lic = credit.get("license", "")
        who = credit.get("author", "")
        left = f"Photo: {who} · {lic} · Wikimedia Commons" if who and who != "Unknown" else f"Photo: Wikimedia Commons · {lic}"
        left = textwrap.shorten(left, 92, placeholder="…")
    d.text((14, 7), left, font=f, fill=(190, 190, 200))
    tw = d.textlength(BRAND, font=f)
    d.text((width - tw - 14, 7), BRAND, font=f, fill=(54, 169, 225))
    return img


def load_photo(path, width=W, max_h=1100):
    im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    s = width / im.width
    im = im.resize((width, int(im.height * s)), Image.LANCZOS)
    if im.height > max_h:  # centre crop very tall photos
        top = (im.height - max_h) // 3
        im = im.crop((0, top, width, top + max_h))
    return im


def stack(parts):
    h = sum(p.height for p in parts)
    out = Image.new("RGB", (parts[0].width, h), "white")
    y = 0
    for p in parts:
        out.paste(p, (0, y)); y += p.height
    return out


def caption_meme(photo, text, lang="en", credit=None):
    ph = load_photo(photo)
    return stack([text_panel(text, W, lang), ph, credit_strip(W, credit)])


def classic_meme(photo, top, bottom, credit=None):
    ph = load_photo(photo, max_h=1080)
    d = ImageDraw.Draw(ph)

    def draw_block(txt, at_top):
        if not txt:
            return
        txt = txt.upper()
        for s in range(96, 40, -4):
            fnt = R.font("anton_400.ttf", s)
            lines = _wrap_px(txt, fnt, W - 80, False)
            if len(lines) <= 3:
                break
        lh = int(s * 1.08)
        y = 26 if at_top else ph.height - 30 - lh * len(lines)
        for line in lines:
            tw = d.textlength(line, font=fnt)
            d.text(((W - tw) / 2, y), line, font=fnt, fill="white", stroke_width=max(4, s // 14), stroke_fill="black")
            y += lh

    draw_block(top, True)
    draw_block(bottom, False)
    return stack([ph, credit_strip(W, credit)])


def compare_meme(photo_a, label_a, photo_b, label_b, title=None, lang="en", credits=()):
    parts = []
    if title:
        parts.append(text_panel(title, W, lang, size=50))
    for ph, lab in ((photo_a, label_a), (photo_b, label_b)):
        img = load_photo(ph, max_h=620) if isinstance(ph, str) else ph
        if isinstance(ph, str) and img.height > 620:
            img = img.crop((0, 0, W, 620))
        tag = text_panel(lab, W, lang, size=40, pad=22, bg=(245, 247, 250))
        parts += [tag, img]
    cred = [c for c in credits if c]
    parts.append(credit_strip(W, cred[0] if len(cred) == 1 else ({"author": "various", "license": "see app"} if cred else None)))
    return stack(parts)


def emoji_tile(glyph_img, bg=(240, 247, 253), size=520):
    tile = Image.new("RGB", (W, size + 80), bg)
    e = R.emoji_sticker(glyph_img).resize((size, size), Image.LANCZOS)
    tile.paste(e, ((W - size) // 2, 40), e)
    return tile


def textpost_meme(text, glyph_img, lang="en", bg=(240, 247, 253)):
    return stack([text_panel(text, W, lang, size=56), emoji_tile(glyph_img, bg), credit_strip(W, None)])


def emoji_compare(label_a, emo_a, label_b, emo_b, title=None, lang="en"):
    a = emoji_tile(emo_a, (232, 246, 236), 380)
    b = emoji_tile(emo_b, (253, 236, 236), 380)
    return compare_meme(a, label_a, b, label_b, title=title, lang=lang)


def save_meme(img: Image.Image, path: str, thumb_path: str) -> tuple[int, int, int]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
    for q in (82, 76, 70, 62, 55, 48):
        img.save(path, "WEBP", quality=q, method=6)
        if os.path.getsize(path) < 260 * 1024:
            break
    while os.path.getsize(path) > 290 * 1024:  # very detailed photos: shrink until it fits
        img = img.resize((int(img.width * 0.9), int(img.height * 0.9)), Image.LANCZOS)
        img.save(path, "WEBP", quality=62, method=6)
    t = img.copy()
    t.thumbnail((360, 720), Image.LANCZOS)
    t.save(thumb_path, "WEBP", quality=72, method=6)
    return os.path.getsize(path), img.width, img.height
