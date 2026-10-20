"""CI guard: fail if v1/ is not what make_manifests.py would produce from build/ + curation/.
Regenerates into a temp copy (same contentVersion/updatedAt) and compares file trees."""
import json, os, shutil, subprocess, sys, tempfile, filecmp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
idx = json.load(open(os.path.join(ROOT, "v1/index.json")))
tmp = tempfile.mkdtemp()
for d in ("tools", "build", "curation"):
    shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d))
env = dict(os.environ, MANIFEST_NOW=idx["updatedAt"])
subprocess.run([sys.executable, os.path.join(tmp, "tools/make_manifests.py"), "--version", idx["contentVersion"]], check=True, env=env, cwd=tmp)
bad = []
for dirpath, _, files in os.walk(os.path.join(ROOT, "v1")):
    for f in files:
        a = os.path.join(dirpath, f)
        b = os.path.join(tmp, os.path.relpath(a, ROOT))
        if not os.path.exists(b) or not filecmp.cmp(a, b, shallow=False):
            bad.append(os.path.relpath(a, ROOT))
for dirpath, _, files in os.walk(os.path.join(tmp, "v1")):
    for f in files:
        if not os.path.exists(os.path.join(ROOT, os.path.relpath(os.path.join(dirpath, f), tmp))):
            bad.append("(missing) " + os.path.relpath(os.path.join(dirpath, f), tmp))
if bad:
    print("v1/ is stale - run `python tools/make_manifests.py` and commit. Differences:", *bad[:20], sep="\n  ")
    sys.exit(1)
print("v1/ manifests are up to date")
