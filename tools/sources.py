"""Lookups into the downloaded source material (Fluent emoji by glyph, Commons photos by file name)."""
from __future__ import annotations

import glob
import json
import os
from functools import lru_cache

from PIL import Image

WORK = os.environ.get("SM_WORK", "/home/claude/work")


def norm(s: str) -> str:
    return "_".join("%x" % ord(c) for c in s if ord(c) != 0xFE0F)


@lru_cache(maxsize=1)
def _fluent():
    cat = json.load(open(os.path.join(WORK, "catalog.json"), encoding="utf-8"))
    return {norm(i["glyph"]): i for i in cat if i["src"] == "fluent"}


def emoji(glyph: str) -> Image.Image:
    item = _fluent().get(norm(glyph))
    if not item:
        raise KeyError("no Fluent art for " + glyph)
    return Image.open(os.path.join(WORK, item["file"])).convert("RGBA")


@lru_cache(maxsize=1)
def _photos():
    out = {}
    for d in ("photos", "photos2", "photos3"):
        p = os.path.join(WORK, d, "sources.json")
        if not os.path.exists(p):
            continue
        for hits in json.load(open(p, encoding="utf-8")).values():
            for h in hits:
                if h.get("file"):
                    h = dict(h, path=os.path.join(WORK, d, h["file"]), key=f"{d}/{h['file']}")
                    out[h["key"]] = h
    return out


def photo(key: str) -> dict:
    """key like 'photos2/cat_q_3.jpg' -> metadata with absolute 'path' and licence fields."""
    return _photos()[key]


def all_photos() -> dict:
    return _photos()
