"""Assemble the public manifests (v1/*.json) from build/ metadata + curation files.

Usage: python tools/make_manifests.py [--version 2026.10.20-1]

Inputs
  build/packs/<id>.json          written by build_stickers.py
  build/memes/<id>.json          written by build_memes.py (one file per meme)
  curation/trending.json         hand-curated Trending sections (see CONTENT_GUIDE.md)
  curation/categories.json       optional overrides (cover, order) per category
Outputs
  v1/index.json                  entry point the app downloads first
  v1/categories.json, v1/packs.json, v1/packs/<id>.json
  v1/memes/index.json, v1/memes/<category>/<page>.json, v1/memes/all/<page>.json
  v1/trending.json, v1/search.json, v1/credits.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import spec_stickers as S  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "codecoiltechnologies/sticker-maker-content"
BRANCH = "main"
PAGE = 24
SCHEMA = 1

CREDITS = {
    "fluent": {"source": "Fluent Emoji 3D", "author": "Microsoft", "license": "MIT",
               "licenseUrl": "https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE",
               "sourceUrl": "https://github.com/microsoft/fluentui-emoji"},
    "noto": {"source": "Noto Animated Emoji", "author": "Google", "license": "CC BY 4.0",
             "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
             "sourceUrl": "https://googlefonts.github.io/noto-emoji-animation/"},
    "text": {"source": "Original text sticker", "author": "CodeCoil", "license": "CC BY 4.0",
             "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
             "note": "Lettering in SIL Open Font License fonts; emoji art from Fluent Emoji (MIT)."},
    "own": {"source": "Sticker Maker original artwork", "author": "CodeCoil", "license": "All rights reserved",
            "note": "Original character art from the Sticker Maker app design."},
    "meme-emoji": {"source": "Original meme", "author": "CodeCoil", "license": "CC BY 4.0",
                   "licenseUrl": "https://creativecommons.org/licenses/by/4.0/",
                   "note": "Caption by CodeCoil; emoji art from Fluent Emoji (MIT)."},
}


def dump(path, obj):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    open(full, "w", encoding="utf-8").write(data)
    return path, hashlib.sha256(data.encode()).hexdigest()[:16], len(data.encode())


def load_json(path, default=None):
    full = os.path.join(ROOT, path)
    return json.load(open(full, encoding="utf-8")) if os.path.exists(full) else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=dt.datetime.utcnow().strftime("%Y.%m.%d-1"))
    args = ap.parse_args()
    now = os.environ.get("MANIFEST_NOW") or dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    added = load_json("curation/added.json", {})  # id -> ISO date first published (keeps "Recently added" honest)
    today = (os.environ.get("MANIFEST_NOW") or dt.date.today().isoformat())[:10]

    shutil.rmtree(os.path.join(ROOT, "v1"), ignore_errors=True)

    # ---------------- packs
    packs = []
    for p in sorted(glob.glob(os.path.join(ROOT, "build/packs/*.json"))):
        packs.append(json.load(open(p, encoding="utf-8")))
    order = [x[0] for x in S.EMOJI_PACKS] + [x[0] for x in S.TEXT_PACKS] + ["cute-boy", "chibi-friends", "sm-originals"] + [x[0] for x in S.ANIMATED_PACKS]
    packs.sort(key=lambda p: order.index(p["id"]) if p["id"] in order else 999)
    premium = set(load_json("curation/premium.json", {"packs": []})["packs"])
    pack_summaries, outputs = [], {}
    for p in packs:
        if len(p["stickers"]) < 3:
            print("skip pack with <3 stickers:", p["id"]); continue
        added.setdefault("pack:" + p["id"], today)
        detail = {"id": p["id"], "title": p["title"], "category": p["category"], "type": p["type"],
                  "language": p.get("language", ""), "tray": p["tray"], "cover": p["cover"],
                  "publisher": "Sticker Maker", "addedAt": added["pack:" + p["id"]],
                  "stickers": [{k: v for k, v in s.items() if k != "credit"} | {"credit": s["credit"]} for s in p["stickers"]]}
        path, sha, size = dump(f"v1/packs/{p['id']}.json", detail)
        tags = sorted({t for s in p["stickers"] for t in s.get("tags", [])})[:24]
        pack_summaries.append({"id": p["id"], "title": p["title"], "category": p["category"], "type": p["type"],
                               "language": p.get("language", ""), "tray": p["tray"], "cover": p["cover"],
                               "count": len(p["stickers"]), "preview": [s["thumb"] for s in p["stickers"][:4]],
                               "tags": tags, "addedAt": detail["addedAt"], "manifest": path, "sha": sha,
                               "bytes": sum(s.get("bytes", 0) for s in p["stickers"]), "pro": p["id"] in premium})
    outputs["packs"] = dump("v1/packs.json", {"packs": pack_summaries})

    # ---------------- memes
    memes = [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(os.path.join(ROOT, "build/memes/*.json")))]
    for m in memes:
        added.setdefault("meme:" + m["id"], today)
        m["addedAt"] = added["meme:" + m["id"]]
    memes.sort(key=lambda m: (m["addedAt"], m["id"]), reverse=True)
    meme_index = {"pageSize": PAGE, "categories": {}, "all": {}}

    def paginate(key, items):
        pages = []
        for i in range(0, len(items), PAGE):
            path, _, _ = dump(f"v1/memes/{key}/{i // PAGE + 1}.json", {"items": items[i:i + PAGE]})
            pages.append(path)
        return {"count": len(items), "pages": pages}

    cats_meme = [c[0] for c in S.CATEGORIES if c[2] == "memes"]
    for cid in cats_meme:
        items = [m for m in memes if m["category"] == cid]
        if items:
            meme_index["categories"][cid] = paginate(cid, items)
    meme_index["all"] = paginate("all", memes)
    outputs["memes"] = dump("v1/memes/index.json", meme_index)

    # ---------------- categories
    overrides = load_json("curation/categories.json", {})
    categories = []
    for i, (cid, title, kind, desc) in enumerate(S.CATEGORIES):
        if kind == "stickers":
            mine = [p for p in pack_summaries if p["category"] == cid]
            if not mine:
                print("! empty sticker category", cid); continue
            cover = overrides.get(cid, {}).get("cover") or mine[0]["preview"][0]  # 160 px thumb is plenty for a category tile
            categories.append({"id": cid, "title": title, "kind": kind, "description": desc, "order": i,
                               "cover": cover, "packCount": len(mine), "itemCount": sum(p["count"] for p in mine),
                               "packs": [p["id"] for p in mine]})
        else:
            mine = [m for m in memes if m["category"] == cid]
            if not mine:
                print("! empty meme category", cid); continue
            cover = overrides.get(cid, {}).get("cover") or mine[-1]["thumb"]
            categories.append({"id": cid, "title": title, "kind": kind, "description": desc, "order": i,
                               "cover": cover, "itemCount": len(mine),
                               "languages": sorted({m["language"] for m in mine})})
    outputs["categories"] = dump("v1/categories.json", {"categories": categories})

    # ---------------- trending (curated)
    cur = load_json("curation/trending.json", {"sections": []})
    by_pack = {p["id"]: p for p in pack_summaries}
    by_meme = {m["id"]: m for m in memes}
    sections = []
    for sec in cur["sections"]:
        items = []
        for ref in sec.get("items", []):
            kind, _, rid = ref.partition(":")
            if kind == "pack" and rid in by_pack:
                items.append({"type": "pack", "pack": by_pack[rid]})
            elif kind == "meme" and rid in by_meme:
                items.append({"type": "meme", "meme": by_meme[rid]})
            else:
                raise SystemExit(f"trending.json references unknown item {ref}")
        sections.append({k: v for k, v in sec.items() if k != "items"} | {"items": items})
    recent_packs = sorted(pack_summaries, key=lambda p: p["addedAt"], reverse=True)[:12]
    sections.append({"id": "recent-packs", "title": "Recently added packs", "subtitle": "Newest in the library",
                     "basis": "Sorted by the date each pack was published", "items": [{"type": "pack", "pack": p} for p in recent_packs]})
    sections.append({"id": "recent-memes", "title": "Fresh memes", "subtitle": "Newest in the library",
                     "basis": "Sorted by the date each meme was published", "items": [{"type": "meme", "meme": m} for m in memes[:16]]})
    outputs["trending"] = dump("v1/trending.json", {"updatedAt": cur.get("updatedAt", today), "curator": cur.get("curator", "Sticker Maker editors"),
                                                    "note": cur.get("note", ""), "tags": cur.get("tags", []), "sections": sections})

    # ---------------- search
    entries = []
    for c in categories:
        entries.append({"t": "c", "id": c["id"], "title": c["title"], "k": c["kind"], "thumb": c["cover"], "tags": c["description"].lower().split()[:8]})
    for p in packs:
        if p["id"] not in by_pack:
            continue
        entries.append({"t": "p", "id": p["id"], "title": p["title"], "thumb": by_pack[p["id"]]["preview"][0], "cat": p["category"], "tags": by_pack[p["id"]]["tags"][:12]})
        for s in p["stickers"]:
            entries.append({"t": "s", "id": s["id"], "pack": p["id"], "title": s["title"], "thumb": s["thumb"], "tags": s.get("tags", [])[:8]})
    for m in memes:
        entries.append({"t": "m", "id": m["id"], "cat": m["category"], "title": m["title"], "thumb": m["thumb"], "lang": m["language"],
                        "tags": m.get("tags", [])[:8], "meme": m})
    outputs["search"] = dump("v1/search.json", {"entries": entries})

    # ---------------- credits
    photo_sources = sorted({(m["credit"].get("author", ""), m["credit"].get("license", ""), m["credit"].get("sourceUrl", ""))
                            for m in memes if m["credit"].get("sourceUrl")})
    outputs["credits"] = dump("v1/credits.json", {"libraries": list(CREDITS.values()),
                                                  "photos": [{"author": a, "license": l, "sourceUrl": u} for a, l, u in photo_sources]})

    # ---------------- index
    n_stickers = sum(p["count"] for p in pack_summaries)
    index = {"schema": SCHEMA, "contentVersion": args.version, "updatedAt": now,
             "mediaBaseUrls": [f"https://cdn.jsdelivr.net/gh/{REPO}@{BRANCH}/", f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"],
             "manifests": {k: {"path": v[0], "sha": v[1], "bytes": v[2]} for k, v in outputs.items()},
             "counts": {"stickers": n_stickers, "packs": len(pack_summaries), "animatedStickers": sum(p["count"] for p in pack_summaries if p["type"] == "animated"),
                        "memes": len(memes), "categories": len(categories)},
             "credits": CREDITS, "minAppVersionCode": 3}
    dump("v1/index.json", index)
    os.makedirs(os.path.join(ROOT, "curation"), exist_ok=True)
    json.dump(dict(sorted(added.items())), open(os.path.join(ROOT, "curation/added.json"), "w"), indent=1)
    print(json.dumps(index["counts"]))


if __name__ == "__main__":
    main()
