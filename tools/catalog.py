"""Build a searchable catalogue of the source emoji (Fluent 3D + Noto animated) with Unicode subgroups.

Usage: python tools/catalog.py <work_dir>
Writes <work_dir>/catalog.json
"""
import json, os, sys, re

work = sys.argv[1]

def norm(cp):
    return "_".join(p.lower() for p in re.split(r"[\s_-]+", cp.strip()) if p and p.lower() != "fe0f")

# Unicode subgroups from emoji-test.txt
sub = {}
group = subgroup = None
for line in open(os.path.join(work, "ref/emoji-test.txt"), encoding="utf-8"):
    if line.startswith("# group:"): group = line.split(":", 1)[1].strip()
    elif line.startswith("# subgroup:"): subgroup = line.split(":", 1)[1].strip()
    elif "; fully-qualified" in line:
        cps = line.split(";")[0]
        name = line.split("#", 1)[1].split(" ", 3)[-1].strip() if "#" in line else ""
        sub[norm(cps)] = {"group": group, "subgroup": subgroup, "name": name}

items = []
fluent_root = os.path.join(work, "fluent/assets")
for d in sorted(os.listdir(fluent_root)):
    meta_p = os.path.join(fluent_root, d, "metadata.json")
    if not os.path.exists(meta_p): continue
    m = json.load(open(meta_p, encoding="utf-8"))
    png = None
    for sub_dir in ("3D", "Default/3D"):
        p = os.path.join(fluent_root, d, sub_dir)
        if os.path.isdir(p):
            pngs = [f for f in os.listdir(p) if f.endswith(".png")]
            if pngs: png = os.path.join(p, pngs[0]); break
    if not png: continue
    code = norm(m.get("unicode", ""))
    u = sub.get(code, {})
    items.append({"src": "fluent", "name": m.get("cldr") or d.lower(), "glyph": m.get("glyph", ""), "code": code,
                  "group": u.get("group") or m.get("group"), "subgroup": u.get("subgroup", ""),
                  "keywords": m.get("keywords", []), "file": os.path.relpath(png, work)})

noto = json.load(open(os.path.join(work, "noto_api.json")))
for ic in noto["icons"]:
    code = norm(ic["codepoint"])
    if any(t in code for t in ("1f3fb", "1f3fc", "1f3fd", "1f3fe", "1f3ff")):  # skip skin-tone variants
        continue
    u = sub.get(code, {})
    items.append({"src": "noto", "name": u.get("name") or ic["tags"][0].strip(":").replace("-", " "), "code": code,
                  "glyph": "".join(chr(int(c, 16)) for c in code.split("_")),
                  "group": u.get("group") or ic["categories"][0], "subgroup": u.get("subgroup", ""),
                  "keywords": [t.strip(":") for t in ic["tags"]], "popularity": ic.get("popularity")})

json.dump(items, open(os.path.join(work, "catalog.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
from collections import Counter
print(Counter(i["src"] for i in items))
print(Counter((i["src"], i["subgroup"]) for i in items if not i["subgroup"]).most_common(5))
