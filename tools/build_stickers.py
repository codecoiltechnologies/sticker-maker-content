"""Generate every sticker pack defined in spec_stickers.py into the content repo.

Usage: python tools/build_stickers.py <work_dir> [pack_id ...]
  work_dir holds the downloaded sources (fluent/, catalog.json, noto/, legacy/).
Outputs (relative to the repo root):
  media/stickers/<pack>/<nn>.webp   512x512 sticker (WhatsApp ready)
  media/thumbs/<pack>/<nn>.webp     160x160 preview
  media/trays/<pack>.png            96x96 tray icon
  media/covers/<pack>.webp          720x400 pack cover
  media/gifs/<pack>/<nn>.gif        animated packs only: 240 px GIF for sharing outside WhatsApp
  build/packs/<pack>.json           pack metadata consumed by make_manifests.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageDraw, ImageSequence

sys.path.insert(0, os.path.dirname(__file__))
import render as R  # noqa: E402
import spec_stickers as S  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/work"
ONLY = set(sys.argv[2:])

FLUENT_CREDIT = {"source": "Fluent Emoji 3D", "author": "Microsoft", "license": "MIT",
                 "licenseUrl": "https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE",
                 "sourceUrl": "https://github.com/microsoft/fluentui-emoji"}
NOTO_CREDIT = {"source": "Noto Animated Emoji", "author": "Google", "license": "CC BY 4.0",
               "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
               "sourceUrl": "https://googlefonts.github.io/noto-emoji-animation/"}
TEXT_CREDIT = {"source": "Original CodeCoil text sticker", "author": "CodeCoil",
               "license": "CC BY 4.0", "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
               "note": "Fonts: SIL Open Font License / Apache 2.0. Emoji art: Fluent Emoji (MIT, Microsoft)."}
OWN_CREDIT = {"source": "Sticker Maker original artwork", "author": "CodeCoil", "license": "All rights reserved",
              "note": "Original artwork from the Sticker Maker design, used with permission of the owner."}


def norm(s: str) -> str:
    return "_".join("%x" % ord(c) for c in s if ord(c) != 0xFE0F)


CATALOG = json.load(open(os.path.join(WORK, "catalog.json"), encoding="utf-8"))
FLUENT = {norm(i["glyph"]): i for i in CATALOG if i["src"] == "fluent"}
NOTO = [i for i in CATALOG if i["src"] == "noto"]


def split_glyphs(s: str) -> list[str]:
    """Greedy longest-match split of an emoji string against the Fluent catalogue."""
    out, i = [], 0
    while i < len(s):
        for j in range(min(len(s), i + 12), i, -1):
            if norm(s[i:j]) in FLUENT:
                out.append(s[i:j]); i = j; break
        else:
            if s[i] not in "️‍ ":
                print("  ! no Fluent art for", repr(s[i]), file=sys.stderr)
            i += 1
    return out


def fluent_img(glyph: str) -> Image.Image | None:
    item = FLUENT.get(norm(glyph))
    return Image.open(os.path.join(WORK, item["file"])).convert("RGBA") if item else None


def paths(pack: str, n: int, ext: str = "webp"):
    nn = "%02d" % n
    return (f"media/stickers/{pack}/{nn}.{ext}", f"media/thumbs/{pack}/{nn}.webp", nn)


def cover(pack: str, imgs: list[Image.Image], color=(54, 169, 225)) -> str:
    W, H = 720, 400
    bg = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(bg)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(color[k] * (0.30 + 0.30 * t) + 255 * (0.70 - 0.30 * t)) for k in range(3)) + (255,))
    pos = [(30, 110, 250), (235, 50, 300), (470, 110, 250)]
    for (x, y, s), im in zip(pos, (imgs * 3)[:3]):
        im = im.resize((s, s), Image.LANCZOS)
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        sh.putalpha(im.getchannel("A").point(lambda a: a * 50 // 255))
        bg.alpha_composite(sh.filter(R.ImageFilter.GaussianBlur(8)), (x + 6, y + 12))
        bg.alpha_composite(im, (x, y))
    p = f"media/covers/{pack}.webp"
    os.makedirs(os.path.join(ROOT, "media/covers"), exist_ok=True)
    bg.convert("RGB").save(os.path.join(ROOT, p), "WEBP", quality=80, method=6)
    return p


PACK_COLORS = {"emoji": (255, 190, 40), "love": (240, 80, 130), "sad": (90, 110, 200), "funny": (255, 150, 40),
               "reactions": (54, 169, 225), "animals": (120, 190, 90), "cartoon": (180, 120, 230), "gaming": (110, 80, 220),
               "birthday": (200, 90, 220), "good-morning": (255, 170, 60), "islamic": (30, 150, 100), "urdu": (40, 160, 150),
               "desi": (240, 110, 60), "attitude": (60, 60, 80), "festivals": (230, 70, 70), "text": (54, 169, 225),
               "food": (240, 140, 50), "sports": (40, 170, 90), "work-study": (70, 110, 200), "filmy": (210, 160, 40),
               "nature": (60, 180, 140), "animated": (255, 120, 80), "friendship": (80, 150, 230)}


def finish(pack_id, title, category, kind, stickers, images, language="", extra=None) -> dict:
    tray = f"media/trays/{pack_id}.png"
    R.save_tray(images[0], os.path.join(ROOT, tray))
    meta = {"id": pack_id, "title": title, "category": category, "type": kind, "language": language,
            "tray": tray, "cover": cover(pack_id, images[:3], PACK_COLORS.get(category, (54, 169, 225))),
            "stickers": stickers}
    if extra:
        meta.update(extra)
    os.makedirs(os.path.join(ROOT, "build/packs"), exist_ok=True)
    json.dump(meta, open(os.path.join(ROOT, f"build/packs/{pack_id}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return meta


# --------------------------------------------------------------------------- builders

def build_emoji_pack(spec, used: dict) -> dict:
    """used: glyph -> (file, thumb, bytes) of stickers already rendered by an earlier pack.
    Packs may share an emoji; the file is stored once and referenced by both packs."""
    pack_id, title, category, glyphs = spec
    stickers, images = [], []
    seen_here = set()
    for g in split_glyphs(glyphs):
        if norm(g) in seen_here or len(stickers) >= 30:
            continue
        src = fluent_img(g)
        if src is None:
            continue
        seen_here.add(norm(g))
        img = R.emoji_sticker(src)
        nn = "%02d" % (len(stickers) + 1)
        if norm(g) in used:
            f, t, size = used[norm(g)]
        else:
            f, t, nn = paths(pack_id, len(stickers) + 1)
            size = R.save_sticker(img, os.path.join(ROOT, f))
            R.save_thumb(img, os.path.join(ROOT, t))
            used[norm(g)] = (f, t, size)
        item = FLUENT[norm(g)]
        stickers.append({"id": f"{pack_id}-{nn}", "title": item["name"].capitalize(), "file": f, "thumb": t,
                         "emojis": [g], "tags": sorted(set(item["keywords"][:8])), "bytes": size,
                         "fileType": "image/webp", "credit": "fluent"})
        images.append(img)
    return finish(pack_id, title, category, "static", stickers, images)


def noto_frames(code: str):
    cache = os.path.join(WORK, "noto", code + ".webp")
    if not os.path.exists(cache) or os.path.getsize(cache) == 0:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        url = f"https://fonts.gstatic.com/s/e/notoemoji/latest/{code}/512.webp"
        open(cache, "wb").write(urllib.request.urlopen(url, timeout=60).read())
    im = Image.open(cache)
    frames, durs = [], []
    for fr in ImageSequence.Iterator(im):
        frames.append(fr.convert("RGBA").copy()); durs.append(fr.info.get("duration", 40) or 40)
    return frames, durs


def build_animated_pack(spec, used: set[str]) -> dict:
    pack_id, title, category, subgroups, limit = spec
    # round-robin over the listed subgroups (in spec order) so every pack mixes its themes and the
    # first stickers - which make the cover - come from the pack's main subgroup
    groups = [[i for i in NOTO if i["subgroup"] == g and i["code"] not in used] for g in subgroups]
    cands = [g[k] for k in range(max(map(len, groups), default=0)) for g in groups if k < len(g)]
    stickers, images = [], []
    for item in cands:
        if len(stickers) >= limit:
            break
        code = item["code"]
        try:
            frames, durs = noto_frames(code)
        except Exception as e:  # noqa: BLE001
            print("  ! noto", code, e, file=sys.stderr); continue
        if len(frames) < 2:
            continue
        frames = [R.fit(f, 512, 16) if f.size != (512, 512) else f for f in frames]
        f, t, nn = paths(pack_id, len(stickers) + 1)
        try:
            size = R.save_animated(frames, durs, os.path.join(ROOT, f))
        except ValueError as e:
            print("  !", e, file=sys.stderr); continue
        used.add(code)
        still = frames[len(frames) // 3]
        R.save_thumb(still, os.path.join(ROOT, t))
        gif = f"media/gifs/{pack_id}/{nn}.gif"
        os.makedirs(os.path.dirname(os.path.join(ROOT, gif)), exist_ok=True)
        small = []
        for fr in frames[::2]:
            bg = Image.new("RGBA", fr.size, (255, 255, 255, 0))
            bg.alpha_composite(fr)
            small.append(bg.resize((240, 240), Image.LANCZOS))
        small[0].save(os.path.join(ROOT, gif), save_all=True, append_images=small[1:], loop=0,
                      duration=[sum(durs[i:i + 2]) for i in range(0, len(durs), 2)][: len(small)], disposal=2,
                      transparency=0, optimize=True)
        stickers.append({"id": f"{pack_id}-{nn}", "title": item["name"].capitalize(), "file": f, "thumb": t, "gif": gif,
                         "emojis": [item["glyph"]], "tags": sorted(set(item["keywords"]))[:8], "bytes": size,
                         "fileType": "image/webp", "animated": True, "credit": "noto"})
        images.append(still)
    return finish(pack_id, title, category, "animated", stickers, images)


def build_text_pack(spec, _used=None) -> dict:
    pack_id, title, category, language, items = spec
    stickers, images = [], []
    for text, fnt, pal, emo, layout, wa_emoji, extra in items:
        e_img = fluent_img(emo) if emo and layout != "none" else None
        img = R.text_sticker(text, fnt, pal, e_img, layout if e_img else "top", rtl=extra.get("rtl", False),
                             rotate=R.angle_for(pack_id + text, 4), upper=extra.get("upper", False),
                             sub=extra.get("sub"), sub_font=R_SUB_FONT if extra.get("sub") else None,
                             lang=extra.get("lang"))
        f, t, nn = paths(pack_id, len(stickers) + 1)
        size = R.save_sticker(img, os.path.join(ROOT, f))
        R.save_thumb(img, os.path.join(ROOT, t))
        title_txt = text if not extra.get("sub") else f"{extra['sub']} ({text})"
        stickers.append({"id": f"{pack_id}-{nn}", "title": title_txt, "text": text, "file": f, "thumb": t,
                         "emojis": [wa_emoji or "😀"], "tags": [w.lower().strip("!?.,") for w in (extra.get("sub", "") + " " + text).split()][:8],
                         "language": extra.get("lang") or (language if language != "ar" else "en"),
                         "bytes": size, "fileType": "image/webp", "credit": "text"})
        images.append(img)
    return finish(pack_id, title, category, "static", stickers, images, language=language)


R_SUB_FONT = "lilita_one_400.ttf"


def build_legacy() -> list[dict]:
    """Original CodeCoil chibi artwork from the v1 app (user-owned)."""
    src = os.path.join(WORK, "legacy")
    out = []
    groups = [("cute-boy", "Cute Boy", [("cute_boy", 9)]),
              ("chibi-friends", "Chibi Friends", [("girl_emotes", 4), ("cat_emotes", 4), ("cute_panda", 4),
                                                  ("lovely_emotes", 4), ("cute_mushroom", 4)])]
    old = json.load(open(os.path.join(src, "packs.json"), encoding="utf-8"))
    old_by_id = {p["id"]: p for p in old["packs"]}
    for pack_id, title, parts in groups:
        stickers, images = [], []
        for folder, n in parts:
            for s in old_by_id[folder]["stickers"][:n]:
                img = Image.open(os.path.join(src, folder, s["file"])).convert("RGBA")
                img = R.fit(img)
                f, t, nn = paths(pack_id, len(stickers) + 1)
                size = R.save_sticker(img, os.path.join(ROOT, f))
                R.save_thumb(img, os.path.join(ROOT, t))
                stickers.append({"id": f"{pack_id}-{nn}", "title": f"{title} {len(stickers) + 1}", "file": f, "thumb": t,
                                 "emojis": s["emojis"], "tags": ["chibi", "cartoon", "cute", folder.split("_")[-1]],
                                 "bytes": size, "fileType": "image/webp", "credit": "own"})
                images.append(img)
        out.append(finish(pack_id, title, "cartoon", "static", stickers, images))
    # Artwork from the original app design (Figma) that is not Fluent emoji.
    orig = [("funny_stickers_01", "Cheeky Wink", ["😜"], "wink tongue funny"), ("funny_stickers_02", "Trending", ["🔥"], "trending hot fire"),
            ("love_stickers_01", "In Love", ["😍"], "love hearts"), ("cute_stickers_01", "Wink Girl", ["😉"], "girl wink cute"),
            ("animal_stickers_01", "Wink Kitty", ["😺"], "cat kitty wink")]
    stickers, images = [], []
    for name, title, emojis, tags in orig:
        img = R.fit(Image.open(os.path.join(src, "originals", name + ".webp")).convert("RGBA"))
        f, t, nn = paths("sm-originals", len(stickers) + 1)
        size = R.save_sticker(img, os.path.join(ROOT, f))
        R.save_thumb(img, os.path.join(ROOT, t))
        stickers.append({"id": f"sm-originals-{nn}", "title": title, "file": f, "thumb": t, "emojis": emojis,
                         "tags": tags.split() + ["original"], "bytes": size, "fileType": "image/webp", "credit": "own"})
        images.append(img)
    out.append(finish("sm-originals", "Sticker Maker Originals", "cartoon", "static", stickers, images))
    return out


def run_text(spec):
    return build_text_pack(spec)


if __name__ == "__main__":
    os.chdir(ROOT)
    results = []
    used_f: dict = {}
    for spec in S.EMOJI_PACKS:
        if ONLY and spec[0] not in ONLY and "emoji" not in ONLY:
            continue
        m = build_emoji_pack(spec, used_f); print("emoji", m["id"], len(m["stickers"]), flush=True)
    todo_text = [s for s in S.TEXT_PACKS if not ONLY or s[0] in ONLY or "text" in ONLY]
    with ProcessPoolExecutor(2) as ex:
        for m in ex.map(run_text, todo_text):
            print("text", m["id"], len(m["stickers"]), flush=True)
    if not ONLY or "legacy" in ONLY:
        for m in build_legacy():
            print("legacy", m["id"], len(m["stickers"]), flush=True)
    used_n: set[str] = set()
    if ONLY and "animated" not in ONLY:  # rebuilding single packs: keep other animated packs' emoji out
        by_glyph = {i["glyph"]: i["code"] for i in NOTO}
        for spec in S.ANIMATED_PACKS:
            pth = os.path.join(ROOT, "build/packs", spec[0] + ".json")
            if spec[0] not in ONLY and os.path.exists(pth):
                for st in json.load(open(pth, encoding="utf-8"))["stickers"]:
                    used_n.update(by_glyph[e] for e in st["emojis"] if e in by_glyph)
    for spec in S.ANIMATED_PACKS:
        if ONLY and spec[0] not in ONLY and "animated" not in ONLY:
            continue
        m = build_animated_pack(spec, used_n); print("animated", m["id"], len(m["stickers"]), flush=True)
    print("DONE")
