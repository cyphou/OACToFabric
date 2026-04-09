import json, os

base = "output/migration_report/MigrationReport/MigrationReport.Report/definition/pages"

for d in sorted(os.listdir(base)):
    dp = os.path.join(base, d)
    if not os.path.isdir(dp):
        continue
    pj = os.path.join(dp, "page.json")
    if not os.path.exists(pj):
        continue
    pg = json.load(open(pj, encoding="utf-8"))
    vis_dir = os.path.join(dp, "visuals")
    has_vis = os.path.isdir(vis_dir) and len(os.listdir(vis_dir)) > 0
    name = pg.get("displayName", "?")
    if not has_vis:
        print(f"EMPTY PAGE: {d} -> {name}")
        print(f"  keys: {list(pg.keys())}")
        print(f"  {json.dumps(pg, indent=2)[:400]}")
        print()

# Also check a sample visual.json for correctness
sample = os.path.join(base, "Page_1", "visuals")
if os.path.isdir(sample):
    vdirs = sorted(os.listdir(sample))[:2]
    for vd in vdirs:
        vp = os.path.join(sample, vd, "visual.json")
        if os.path.exists(vp):
            v = json.load(open(vp, encoding="utf-8"))
            print(f"Sample visual ({vd}):")
            print(f"  keys: {list(v.keys())}")
            s = json.dumps(v, indent=2)[:500]
            print(f"  {s}")
            print()
