"""Validate the published content before it reaches the app.

Usage:
  python tools/validate.py                 # local checks (run in CI on every push / PR)
  python tools/validate.py --remote 40     # also fetch 40 random media URLs from each mirror
  python tools/validate.py --strict        # treat warnings (orphan files, near-limit sizes) as errors

Checks
  * v1/index.json schema, https mirrors, every manifest present with matching sha/bytes
  * every path in every manifest is safe (no "..", no absolute paths) and exists on disk
  * WhatsApp limits: 3-30 stickers per pack, 512x512 WebP, static <= 100 KB, animated <= 500 KB,
    tray 96x96 PNG <= 50 KB, animated flag consistent with the file
  * memes: WebP, dimensions match metadata, <= 300 KB, thumbnail present
  * licences: only allow-listed licences (no NonCommercial / NoDerivatives), photo credits have an author + source URL
  * unique ids; duplicate meme images (same bytes) flagged
  * no file over 20 MB; no secrets-looking files (keystores, .env, keys) in the repo
  * orphans: media files not referenced by any manifest (warning)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import urllib.request

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAFE = re.compile(r"^[A-Za-z0-9_\-./]+$")
LICENSES = re.compile(r"^(MIT|CC0|CC0 1\.0|Public domain|PD.*|CC BY(-SA)? (2\.0|2\.5|3\.0|4\.0)|CC BY 4\.0|All rights reserved)$", re.I)
SECRET_NAMES = re.compile(r"(\.jks|\.keystore|\.p12|\.pem|\.key|\.env|keystore\.properties|google-services\.json|id_rsa)$", re.I)

errors: list[str] = []
warnings: list[str] = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(path):
    try:
        return json.load(open(os.path.join(ROOT, path), encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        err(f"{path}: cannot parse JSON ({e})")
        return None


referenced: set[str] = set()


def need(path, ctx):
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in path or not SAFE.match(path):
        err(f"{ctx}: unsafe path {path!r}"); return False
    referenced.add(path)
    if not os.path.isfile(os.path.join(ROOT, path)):
        err(f"{ctx}: missing file {path}"); return False
    return True


def size(path):
    return os.path.getsize(os.path.join(ROOT, path))


def check_sticker(s, pack, animated):
    ctx = f"pack {pack['id']} sticker {s.get('id')}"
    if not need(s.get("file"), ctx) or not need(s.get("thumb"), ctx + " thumb"):
        return
    if s.get("gif"):
        need(s["gif"], ctx + " gif")
    p = os.path.join(ROOT, s["file"])
    with open(p, "rb") as f:
        head = f.read(16)
    if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
        err(f"{ctx}: not a WebP file"); return
    with Image.open(p) as im:
        if im.size != (512, 512):
            err(f"{ctx}: {im.size} (WhatsApp needs 512x512)")
        is_anim = getattr(im, "is_animated", False)
        if is_anim:
            dur = 0
            for i in range(im.n_frames):
                im.seek(i); dur += im.info.get("duration", 0)
            if dur > 10000:
                err(f"{ctx}: animation {dur} ms > 10 s")
    if bool(s.get("animated")) != is_anim:
        err(f"{ctx}: animated flag {s.get('animated')} but file animated={is_anim}")
    if is_anim != animated:
        err(f"{ctx}: pack type {pack['type']} mixes static/animated stickers")
    limit = 500 * 1024 if is_anim else 100 * 1024
    b = size(s["file"])
    if b > limit:
        err(f"{ctx}: {b} bytes > {limit}")
    elif b > limit * 0.97:
        warn(f"{ctx}: {b} bytes is within 3% of the limit")
    if s.get("bytes") not in (None, b):
        err(f"{ctx}: metadata bytes {s.get('bytes')} != {b}")
    if not s.get("emojis"):
        warn(f"{ctx}: no emojis (WhatsApp shows them for search)")


def check_pack(summary, detail):
    ctx = f"pack {summary['id']}"
    n = len(detail.get("stickers", []))
    if not 3 <= n <= 30:
        err(f"{ctx}: {n} stickers (WhatsApp needs 3-30)")
    if summary.get("count") != n:
        err(f"{ctx}: summary count {summary.get('count')} != {n}")
    if need(detail.get("tray"), ctx + " tray"):
        with Image.open(os.path.join(ROOT, detail["tray"])) as im:
            if im.format != "PNG" or im.size != (96, 96):
                err(f"{ctx}: tray must be 96x96 PNG, got {im.format} {im.size}")
        if size(detail["tray"]) > 50 * 1024:
            err(f"{ctx}: tray > 50 KB")
    need(detail.get("cover"), ctx + " cover")
    for t in summary.get("preview", []):
        need(t, ctx + " preview")
    animated = detail.get("type") == "animated"
    ids = set()
    for s in detail["stickers"]:
        if s.get("id") in ids:
            err(f"{ctx}: duplicate sticker id {s.get('id')}")
        ids.add(s.get("id"))
        check_sticker(s, detail, animated)
        check_credit(s.get("credit"), f"{ctx} sticker {s.get('id')}", photo=False)


def check_credit(c, ctx, photo):
    if not isinstance(c, (dict, str)) or not c:
        err(f"{ctx}: missing credit"); return
    if isinstance(c, str):
        return  # key into index.credits, checked separately
    lic = c.get("license", "")
    if not LICENSES.match(lic):
        err(f"{ctx}: licence {lic!r} not on the allow-list")
    if re.search(r"\bNC\b|\bND\b|NonCommercial|NoDerivs", lic, re.I):
        err(f"{ctx}: NonCommercial/NoDerivatives licences are not allowed")
    if photo:
        if not c.get("sourceUrl", "").startswith("https://"):
            err(f"{ctx}: photo credit without https source URL")
        a = c.get("author", "")
        if not a or a == "Unknown" or len(a) > 120 or "{" in a or "mw-parser" in a:
            err(f"{ctx}: bad author string {a[:40]!r}")


def check_meme(m, ctx):
    if not need(m.get("file"), ctx) or not need(m.get("thumb"), ctx + " thumb"):
        return
    with Image.open(os.path.join(ROOT, m["file"])) as im:
        if im.format != "WEBP":
            err(f"{ctx}: not WebP")
        if (m.get("width"), m.get("height")) != im.size:
            err(f"{ctx}: metadata {m.get('width')}x{m.get('height')} != {im.size}")
    b = size(m["file"])
    if b > 300 * 1024:
        err(f"{ctx}: {b} bytes > 300 KB")
    if m.get("language") not in ("en", "ur", "ur-Latn", "mixed"):
        err(f"{ctx}: unknown language {m.get('language')!r}")
    check_credit(m.get("credit"), ctx, photo=bool(m.get("credit", {}).get("sourceUrl")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", type=int, default=0, help="number of random media URLs to fetch from each mirror")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    index = load("v1/index.json")
    if not index:
        return finish(args)
    if index.get("schema") != 1:
        err(f"index.schema {index.get('schema')} != 1")
    for b in index.get("mediaBaseUrls", []):
        if not b.startswith("https://") or not b.endswith("/"):
            err(f"media base {b!r} must be https and end with /")
    required = {"packs", "categories", "memes", "trending", "search", "credits"}
    mans = index.get("manifests", {})
    if missing := required - set(mans):
        err(f"index.manifests missing {sorted(missing)}")
    for name, ref in mans.items():
        if need(ref["path"], f"manifest {name}"):
            data = open(os.path.join(ROOT, ref["path"]), "rb").read()
            if hashlib.sha256(data).hexdigest()[:16] != ref.get("sha"):
                err(f"manifest {name}: sha mismatch (re-run make_manifests.py)")
            if len(data) != ref.get("bytes"):
                err(f"manifest {name}: bytes mismatch")
    for key, c in index.get("credits", {}).items():
        check_credit(c, f"credits.{key}", photo=False)

    packs = load(mans.get("packs", {}).get("path", "v1/packs.json")) or {"packs": []}
    seen_packs = set()
    for p in packs["packs"]:
        if p["id"] in seen_packs:
            err(f"duplicate pack id {p['id']}")
        seen_packs.add(p["id"])
        if need(p.get("manifest"), f"pack {p['id']} manifest"):
            d = load(p["manifest"])
            data = open(os.path.join(ROOT, p["manifest"]), "rb").read()
            if hashlib.sha256(data).hexdigest()[:16] != p.get("sha"):
                err(f"pack {p['id']}: sha mismatch")
            if d:
                check_pack(p, d)

    cats = load(mans.get("categories", {}).get("path", "v1/categories.json")) or {"categories": []}
    for c in cats["categories"]:
        need(c.get("cover"), f"category {c['id']} cover")
        if c["kind"] == "stickers":
            for pid in c.get("packs", []):
                if pid not in seen_packs:
                    err(f"category {c['id']} lists unknown pack {pid}")
            if not c.get("packs"):
                err(f"category {c['id']} is empty")
        elif not c.get("itemCount"):
            err(f"meme category {c['id']} is empty")

    memes_idx = load(mans.get("memes", {}).get("path", "v1/memes/index.json")) or {"categories": {}, "all": {"pages": []}}
    meme_ids, digests = set(), {}
    for page in memes_idx["all"]["pages"]:
        if need(page, "memes/all page"):
            for m in load(page)["items"]:
                ctx = f"meme {m.get('id')}"
                if m["id"] in meme_ids:
                    err(f"duplicate meme id {m['id']}")
                meme_ids.add(m["id"])
                check_meme(m, ctx)
                if m.get("file") and os.path.isfile(os.path.join(ROOT, m["file"])):
                    h = hashlib.sha256(open(os.path.join(ROOT, m["file"]), "rb").read()).hexdigest()
                    if h in digests:
                        err(f"{ctx}: same image as {digests[h]}")
                    digests[h] = m["id"]
    total = 0
    for cid, ref in memes_idx["categories"].items():
        for page in ref["pages"]:
            if need(page, f"memes/{cid} page"):
                items = load(page)["items"]
                total += len(items)
                for m in items:
                    if m["id"] not in meme_ids:
                        err(f"memes/{cid}: {m['id']} missing from the 'all' feed")
                    if m["category"] != cid:
                        err(f"memes/{cid}: {m['id']} has category {m['category']}")
    if total != len(meme_ids):
        err(f"category feeds hold {total} memes but 'all' holds {len(meme_ids)}")

    trending = load(mans.get("trending", {}).get("path", "v1/trending.json")) or {"sections": []}
    for sec in trending["sections"]:
        if not sec.get("items"):
            err(f"trending section {sec.get('id')} is empty")
        for it in sec.get("items", []):
            if it["type"] == "pack" and it["pack"]["id"] not in seen_packs:
                err(f"trending {sec['id']}: unknown pack")
            if it["type"] == "meme" and it["meme"]["id"] not in meme_ids:
                err(f"trending {sec['id']}: unknown meme")

    search = load(mans.get("search", {}).get("path", "v1/search.json")) or {"entries": []}
    for e in search["entries"]:
        need(e.get("thumb"), f"search entry {e.get('t')}:{e.get('id')}")

    # repository hygiene
    for dirpath, dirnames, files in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, ROOT)
            if SECRET_NAMES.search(f):
                err(f"{rel}: looks like a secret / signing file - never commit it to this public repo")
            if os.path.getsize(full) > 20 * 1024 * 1024:
                err(f"{rel}: larger than 20 MB")
            if rel.startswith("media/") and rel not in referenced:
                warn(f"orphan media file {rel}")

    if args.remote:
        remote_check(index, sorted(referenced), args.remote)
    return finish(args, len(seen_packs), len(meme_ids))


def remote_check(index, paths, n):
    rnd = random.Random(7)
    sample = rnd.sample(paths, min(n, len(paths)))
    ua = {"User-Agent": "sticker-maker-content-validator (+https://github.com/codecoiltechnologies/sticker-maker-content)"}
    for base in index["mediaBaseUrls"]:
        bad = 0
        for p in sample:
            try:
                r = urllib.request.urlopen(urllib.request.Request(base + p, headers=ua), timeout=30)
                body = r.read()
                if len(body) != size(p):
                    err(f"remote {base}{p}: {len(body)} bytes, local {size(p)}"); bad += 1
            except Exception as e:  # noqa: BLE001
                err(f"remote {base}{p}: {e}"); bad += 1
        print(f"remote {base}: {len(sample) - bad}/{len(sample)} OK")


def finish(args, packs=0, memes=0):
    for w in warnings[:50]:
        print("warning:", w)
    if len(warnings) > 50:
        print(f"... and {len(warnings) - 50} more warnings")
    for e in errors[:200]:
        print("ERROR:", e)
    print(f"validated {packs} packs, {memes} memes, {len(referenced)} files: {len(errors)} errors, {len(warnings)} warnings")
    if errors or (args.strict and warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
