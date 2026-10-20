"""Copy a small offline starter snapshot into the Android app's assets.

Usage: python tools/bundle_starter.py <app>/app/src/main/assets/content [--budget-kb 4500]

The snapshot holds the core manifests, a few complete packs (stickers, thumbs, tray, cover), every category
cover and the thumbnails of the first page of memes, so a phone with no internet on first launch still shows a
usable library. Everything else is fetched on demand. bundled-media.txt tells the app which paths are local.
"""
import argparse
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKS = ["cute-boy", "chibi-friends", "sm-originals", "good-morning", "happy-faces"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--budget-kb", type=int, default=4500)
    a = ap.parse_args()
    dest = os.path.abspath(a.dest)
    shutil.rmtree(dest, ignore_errors=True)
    os.makedirs(dest)
    index = json.load(open(os.path.join(ROOT, "v1/index.json"), encoding="utf-8"))
    files, media = [], []
    files.append("v1/index.json")
    for name, ref in index["manifests"].items():
        if name != "search":  # search downloads on first use (largest manifest)
            files.append(ref["path"])
    memes_index = json.load(open(os.path.join(ROOT, index["manifests"]["memes"]["path"]), encoding="utf-8"))
    first_page = memes_index["all"]["pages"][0]
    files.append(first_page)
    for m in json.load(open(os.path.join(ROOT, first_page), encoding="utf-8"))["items"]:
        media.append(m["thumb"])
    packs = {p["id"]: p for p in json.load(open(os.path.join(ROOT, index["manifests"]["packs"]["path"]), encoding="utf-8"))["packs"]}
    for pid in PACKS:
        p = packs[pid]
        files.append(p["manifest"])
        media += [p["tray"], p["cover"]]
        for s in json.load(open(os.path.join(ROOT, p["manifest"]), encoding="utf-8"))["stickers"]:
            media += [s["file"], s["thumb"]]
    for c in json.load(open(os.path.join(ROOT, index["manifests"]["categories"]["path"]), encoding="utf-8"))["categories"]:
        media.append(c["cover"])
    for p in packs.values():  # first preview thumb of every pack so home rows are never blank
        media.append(p["preview"][0])
    media = list(dict.fromkeys(media))
    total = 0
    for rel in files + media:
        src = os.path.join(ROOT, rel)
        out = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copyfile(src, out)
        total += os.path.getsize(src)
    open(os.path.join(dest, "bundled-media.txt"), "w").write("\n".join(media) + "\n")
    print(f"bundled {len(files)} manifests + {len(media)} media files, {total // 1024} KB")
    if total > a.budget_kb * 1024:
        sys.exit(f"starter snapshot is over budget ({total // 1024} KB > {a.budget_kb} KB)")


if __name__ == "__main__":
    main()
