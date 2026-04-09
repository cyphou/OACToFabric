"""Diagnose PBIR visuals and relationships in the migration output."""
import os, json, re

base = r"output\migration_report\MigrationReport\MigrationReport.Report\definition\pages"
sm_base = r"output\migration_report\MigrationReport\MigrationReport.SemanticModel\definition"

print("=" * 70)
print("VISUALS DIAGNOSTIC")
print("=" * 70)
total_visuals = 0
for page_dir in sorted(os.listdir(base)):
    page_path = os.path.join(base, page_dir)
    if not os.path.isdir(page_path):
        continue
    pj = os.path.join(page_path, "page.json")
    display = "?"
    if os.path.exists(pj):
        display = json.load(open(pj, encoding="utf-8")).get("displayName", "?")
    vis_dir = os.path.join(page_path, "visuals")
    vis_count = 0
    vis_names = []
    if os.path.isdir(vis_dir):
        for v in os.listdir(vis_dir):
            vj = os.path.join(vis_dir, v, "visual.json")
            if os.path.exists(vj):
                vis_count += 1
                vdata = json.load(open(vj, encoding="utf-8"))
                vtype = vdata.get("visual", {}).get("visualType", "?")
                # Check if visual has data/column bindings
                vc = vdata.get("visual", {}).get("visualContainerObjects", {})
                projs = vdata.get("visual", {}).get("prototypeQuery", {})
                vis_names.append(f"{v[:8]}({vtype})")
    total_visuals += vis_count
    print(f"  {page_dir}: \"{display}\" — {vis_count} visuals")
    if vis_names:
        for vn in vis_names:
            print(f"    {vn}")
print(f"\nTotal visuals: {total_visuals}")

# Check a sample visual.json for structure
print("\n" + "=" * 70)
print("SAMPLE VISUAL DETAIL")
print("=" * 70)
for page_dir in sorted(os.listdir(base)):
    page_path = os.path.join(base, page_dir)
    vis_dir = os.path.join(page_path, "visuals")
    if not os.path.isdir(vis_dir):
        continue
    for v in os.listdir(vis_dir):
        vj = os.path.join(vis_dir, v, "visual.json")
        if os.path.exists(vj):
            print(f"File: {vj}")
            print(json.dumps(json.load(open(vj, encoding="utf-8")), indent=2)[:2000])
            print("...")
            break
    else:
        continue
    break

# relationships
print("\n" + "=" * 70)
print("RELATIONSHIPS DIAGNOSTIC")
print("=" * 70)
rel_path = os.path.join(sm_base, "relationships.tmdl")
if os.path.exists(rel_path):
    content = open(rel_path, encoding="utf-8").read()
    rels = re.findall(r"^relationship\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE)
    print(f"Total relationships defined: {len(rels)}")
    # Show first few
    lines = content.split("\n")
    for i, line in enumerate(lines[:80]):
        print(f"  {i+1:3}: {line}")
    if len(lines) > 80:
        print(f"  ... ({len(lines)} total lines)")
else:
    print("NO relationships.tmdl file found!")

# Check model.tmdl for ref relationship
print("\n" + "=" * 70)
print("MODEL.TMDL REF RELATIONSHIPS")
print("=" * 70)
model_path = os.path.join(sm_base, "model.tmdl")
model = open(model_path, encoding="utf-8").read()
ref_rels = re.findall(r"^ref relationship\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE)
print(f"ref relationship entries in model.tmdl: {len(ref_rels)}")
for r in ref_rels[:10]:
    print(f"  {r[0] or r[1]}")
