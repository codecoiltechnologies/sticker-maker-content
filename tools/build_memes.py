"""Render every meme in spec_memes.py.

Usage: python tools/build_memes.py [category ...]
Outputs media/memes/<category>/<id>.webp (max 1080 px wide), media/meme-thumbs/<category>/<id>.webp (360 px)
and build/memes/<id>.json. IDs are derived from category + caption, so they stay stable when the spec is reordered.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import render_meme as M  # noqa: E402
import sources as SRC  # noqa: E402
import spec_memes  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONLY = set(sys.argv[1:])

EMOJI_CREDIT = {"source": "Original meme", "author": "CodeCoil", "license": "CC BY 4.0",
                "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                "note": "Caption by CodeCoil; emoji art from Fluent Emoji (MIT, Microsoft)."}


def meme_id(item) -> str:
    body = json.dumps({k: v for k, v in item.items() if k not in ("tags",)}, ensure_ascii=False, sort_keys=True)
    return item["cat"].removeprefix("memes-") + "-" + hashlib.sha1(body.encode()).hexdigest()[:8]


def photo_credit(key):
    p = SRC.photo(key)
    lic = p["license"]
    return {"source": "Wikimedia Commons", "author": re.sub(r"\s+", " ", p.get("author") or "Unknown").strip(),
            "license": lic, "licenseUrl": p.get("licenseUrl") or "", "sourceUrl": p["page"],
            "note": "Photo modified: cropped, resized and captioned. Caption by CodeCoil."}


def title_of(item) -> str:
    t = item.get("text") or " ".join(x for x in (item.get("top"), item.get("bottom")) if x) or item.get("title") or ""
    t = t.replace("\n", " ").replace('"', "").strip()
    return (t[:77] + "…") if len(t) > 80 else t


def render(item):
    fmt = item["fmt"]
    lang = "ur" if item["lang"] == "ur" else "en"
    credits = []
    if fmt == "caption":
        c = photo_credit(item["photo"]); credits.append(c)
        img = M.caption_meme(SRC.photo(item["photo"])["path"], item["text"], lang=lang, credit=c)
    elif fmt == "classic":
        c = photo_credit(item["photo"]); credits.append(c)
        img = M.classic_meme(SRC.photo(item["photo"])["path"], item["top"], item["bottom"], credit=c)
    elif fmt == "compare":
        (la, pa), (lb, pb) = item["a"], item["b"]
        credits = [photo_credit(pa), photo_credit(pb)]
        img = M.compare_meme(SRC.photo(pa)["path"], la, SRC.photo(pb)["path"], lb, title=item.get("title"), lang=lang, credits=credits)
    elif fmt == "textpost":
        img = M.textpost_meme(item["text"], SRC.emoji(item["emoji"]), lang=lang)
    elif fmt == "emojicompare":
        (la, ea), (lb, eb) = item["a"], item["b"]
        img = M.emoji_compare(la, SRC.emoji(ea), lb, SRC.emoji(eb), title=item.get("title"), lang=lang)
    else:
        raise ValueError(fmt)
    credit = credits[0] if len(credits) == 1 else (dict(credits[0], author=" & ".join(c["author"] for c in credits)) if credits else EMOJI_CREDIT)
    return img, credit


def main():
    os.chdir(ROOT)
    os.makedirs("build/memes", exist_ok=True)
    seen, count = set(), 0
    for item in spec_memes.MEMES:
        if ONLY and item["cat"] not in ONLY:
            continue
        mid = meme_id(item)
        if mid in seen:
            print("duplicate meme skipped:", mid, file=sys.stderr); continue
        seen.add(mid)
        f = f"media/memes/{item['cat']}/{mid}.webp"
        t = f"media/meme-thumbs/{item['cat']}/{mid}.webp"
        try:
            img, credit = render(item)
        except Exception as e:  # noqa: BLE001
            print("! failed", mid, e, file=sys.stderr); continue
        size, w, h = M.save_meme(img, f, t)
        text = item.get("text") or "\n".join(x for x in (item.get("title"), item.get("top"), item.get("bottom")) if x)
        words = re.findall(r"[a-z]{3,}", (item.get("tags", "") + " " + text).lower())
        meta = {"id": mid, "title": title_of(item), "category": item["cat"], "file": f, "thumb": t, "width": w, "height": h,
                "bytes": size, "fileType": "image/webp", "language": item["lang"], "format": item["fmt"], "text": text,
                "tags": sorted(set(words))[:16], "credit": credit}
        json.dump(meta, open(f"build/memes/{mid}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        count += 1
    print("memes built:", count)


if __name__ == "__main__":
    main()
