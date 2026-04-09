"""Check all page display names and visual counts."""
import json
import os

base = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "migration_report", "MigrationReport",
    "MigrationReport.Report", "definition", "pages",
)

empty_pages = ["Page_8", "Page_9", "Page_10", "Page_11", "Page_12", "Page_19", "Page_20", "Page_24"]
print("=== EMPTY PAGES (no visuals folder) ===")
for p in empty_pages:
    pf = os.path.join(base, p, "page.json")
    with open(pf, "r", encoding="utf-8") as f:
        d = json.load(f)
    print(f"  {p}: {d['displayName']}")

print()
print("=== PAGES WITH VISUALS ===")
for p in sorted(os.listdir(base), key=lambda x: int(x.split("_")[1]) if x.startswith("Page_") else 0):
    pd = os.path.join(base, p)
    if os.path.isdir(pd) and os.path.isdir(os.path.join(pd, "visuals")):
        with open(os.path.join(pd, "page.json"), "r", encoding="utf-8") as f:
            d = json.load(f)
        vis_dir = os.path.join(pd, "visuals")
        n = len([v for v in os.listdir(vis_dir) if os.path.isdir(os.path.join(vis_dir, v))])
        print(f"  {p}: {d['displayName']} ({n} visuals)")
