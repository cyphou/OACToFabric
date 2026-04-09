"""Fix PBIR report: remove empty pages and add missing visuals/ dirs."""
import json
import os
import shutil

base = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "migration_report", "MigrationReport",
    "MigrationReport.Report", "definition", "pages",
)

# Pages with no visuals folder (crash PBI Desktop)
empty_pages = {"Page_8", "Page_9", "Page_10", "Page_11", "Page_12", "Page_19", "Page_20", "Page_24"}

# 1. Remove empty page directories
for p in empty_pages:
    pd = os.path.join(base, p)
    if os.path.isdir(pd):
        shutil.rmtree(pd)
        print(f"Removed: {p}/")

# 2. Update pages.json
pj_path = os.path.join(base, "pages.json")
with open(pj_path, "r", encoding="utf-8") as f:
    pj = json.load(f)

old_count = len(pj["pageOrder"])
pj["pageOrder"] = [p for p in pj["pageOrder"] if p not in empty_pages]
new_count = len(pj["pageOrder"])

with open(pj_path, "w", encoding="utf-8") as f:
    json.dump(pj, f, indent=2)

print(f"\nUpdated pages.json: {old_count} -> {new_count} pages")
print("Remaining pages:", pj["pageOrder"])

# 3. Ensure all remaining pages have visuals/ folder
for p in pj["pageOrder"]:
    vd = os.path.join(base, p, "visuals")
    if not os.path.isdir(vd):
        os.makedirs(vd, exist_ok=True)
        print(f"Created missing visuals/ for {p}")

print("\nDone! Report should now open in PBI Desktop.")
