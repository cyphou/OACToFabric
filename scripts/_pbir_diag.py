"""Comprehensive PBIR diagnostic for PBI Desktop crash."""
import json
import os
import re

base = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "migration_report", "MigrationReport",
)
report_dir = os.path.join(base, "MigrationReport.Report", "definition")
sm_dir = os.path.join(base, "MigrationReport.SemanticModel", "definition")
errors = []

# 1. Check all JSON files parse and have required $schema
for root, dirs, files in os.walk(base):
    for f in files:
        fp = os.path.join(root, f)
        if f.endswith(".json"):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if "$schema" not in data:
                    errors.append("MISSING_SCHEMA: " + os.path.relpath(fp, base))
            except Exception as e:
                errors.append("JSON_ERROR: " + os.path.relpath(fp, base) + " -> " + str(e))
        elif f.endswith((".pbir", ".pbip", ".pbism")):
            try:
                with open(fp, "r", encoding="utf-8") as fh:
                    json.load(fh)
            except Exception as e:
                errors.append("JSON_ERROR: " + os.path.relpath(fp, base) + " -> " + str(e))

# 2. Check all TMDL files for syntax issues
tmdl_dir = os.path.join(sm_dir, "tables")
for f in sorted(os.listdir(tmdl_dir)):
    fp = os.path.join(tmdl_dir, f)
    with open(fp, "r", encoding="utf-8") as fh:
        content = fh.read()
    backtick_count = content.count("```")
    if backtick_count % 2 != 0:
        errors.append(f"TMDL_BACKTICK: {f} -> unmatched ({backtick_count})")
    lines = content.strip().split("\n")
    if lines and not lines[0].startswith("table "):
        errors.append(f"TMDL_HEADER: {f} -> {lines[0][:60]}")

# 3. Check model.tmdl ref tables match actual files
with open(os.path.join(sm_dir, "model.tmdl"), "r", encoding="utf-8") as fh:
    model = fh.read()

ref_tables = re.findall(r"ref table (?:'([^']+)'|([A-Za-z_][A-Za-z0-9_]*))", model)
ref_names = [t[0] or t[1] for t in ref_tables]
table_files = [os.path.splitext(f)[0] for f in os.listdir(tmdl_dir)]
for rt in ref_names:
    if rt not in table_files:
        errors.append(f"MISSING_TABLE_FILE: model refs '{rt}' but no .tmdl")
for tf in table_files:
    if tf not in ref_names:
        errors.append(f"ORPHAN_TABLE_FILE: {tf}.tmdl not in model.tmdl")

# 4. Pages
pages_dir = os.path.join(report_dir, "pages")
with open(os.path.join(pages_dir, "pages.json"), "r", encoding="utf-8") as fh:
    pj = json.load(fh)
page_order = pj.get("pageOrder", [])
actual_pages = [d for d in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, d))]

for p in page_order:
    pd = os.path.join(pages_dir, p)
    if not os.path.isdir(pd):
        errors.append(f"MISSING_PAGE_DIR: {p}")
    elif not os.path.exists(os.path.join(pd, "page.json")):
        errors.append(f"MISSING_PAGE_JSON: {p}")
    vd = os.path.join(pd, "visuals")
    if not os.path.isdir(vd):
        errors.append(f"NO_VISUALS_DIR: {p}")

# 5. Visual name vs folder name
for p in page_order:
    vd = os.path.join(pages_dir, p, "visuals")
    if not os.path.isdir(vd):
        continue
    for v in os.listdir(vd):
        vjp = os.path.join(vd, v, "visual.json")
        if os.path.exists(vjp):
            with open(vjp, "r", encoding="utf-8") as fh:
                vdata = json.load(fh)
            jname = vdata.get("name", "")
            if jname != v:
                errors.append(f"NAME_MISMATCH: {p}/visuals/{v} -> json.name={jname!r}")

# 6. Duplicate displayNames
dns = {}
for p in page_order:
    pjf = os.path.join(pages_dir, p, "page.json")
    if os.path.exists(pjf):
        with open(pjf, "r", encoding="utf-8") as fh:
            pd = json.load(fh)
        dn = pd.get("displayName", "")
        dns.setdefault(dn, []).append(p)
for dn, ps in dns.items():
    if len(ps) > 1:
        errors.append(f"DUPLICATE_DISPLAYNAME: {dn!r} used by {ps}")

# 7. Check page.json has all required fields
required_page_fields = {"$schema", "name", "displayName", "displayOption", "height", "width"}
for p in page_order:
    pjf = os.path.join(pages_dir, p, "page.json")
    if os.path.exists(pjf):
        with open(pjf, "r", encoding="utf-8") as fh:
            pd = json.load(fh)
        missing = required_page_fields - set(pd.keys())
        if missing:
            errors.append(f"PAGE_MISSING_FIELDS: {p} -> {missing}")

# 8. Check visual.json has required fields
required_visual_fields = {"$schema", "name", "position", "visual"}
for p in page_order:
    vd = os.path.join(pages_dir, p, "visuals")
    if not os.path.isdir(vd):
        continue
    for v in os.listdir(vd):
        vjp = os.path.join(vd, v, "visual.json")
        if os.path.exists(vjp):
            with open(vjp, "r", encoding="utf-8") as fh:
                vdata = json.load(fh)
            missing = required_visual_fields - set(vdata.keys())
            if missing:
                errors.append(f"VISUAL_MISSING_FIELDS: {p}/visuals/{v} -> {missing}")
            pos = vdata.get("position", {})
            for k in ("x", "y", "width", "height"):
                if k not in pos:
                    errors.append(f"VISUAL_POSITION: {p}/visuals/{v} -> missing {k}")

# 9. Check TMDL table declarations match filenames
for f in sorted(os.listdir(tmdl_dir)):
    fp = os.path.join(tmdl_dir, f)
    with open(fp, "r", encoding="utf-8") as fh:
        first_line = fh.readline().strip()
    m = re.match(r"table\s+'?([^']+)'?\s*$", first_line)
    if m:
        tbl_name = m.group(1)
        expected = os.path.splitext(f)[0]
        if tbl_name != expected:
            errors.append(f"TMDL_NAME_VS_FILE: {f} declares '{tbl_name}' but file is '{expected}'")
    else:
        errors.append(f"TMDL_BAD_HEADER: {f} -> {first_line!r}")

# 10. Check expressions.tmdl and database.tmdl
for check_file in ["expressions.tmdl", "database.tmdl"]:
    fp = os.path.join(sm_dir, check_file)
    if not os.path.exists(fp):
        errors.append(f"MISSING_SM_FILE: {check_file}")

# 11. Check .platform files
for plat_path in [
    os.path.join(base, "MigrationReport.Report", ".platform"),
    os.path.join(base, "MigrationReport.SemanticModel", ".platform"),
]:
    if os.path.exists(plat_path):
        with open(plat_path, "r", encoding="utf-8") as fh:
            pd = json.load(fh)
        for req in ["$schema", "metadata", "config"]:
            if req not in pd:
                errors.append(f"PLATFORM_MISSING: {os.path.relpath(plat_path, base)} -> {req}")

# 12. Check perspectives reference existing tables
with open(os.path.join(sm_dir, "perspectives.tmdl"), "r", encoding="utf-8") as fh:
    persp = fh.read()
persp_tables = re.findall(r"perspectiveTable\s+(?:'([^']+)'|([A-Za-z_]\w*))", persp)
for pt in persp_tables:
    tname = pt[0] or pt[1]
    if tname not in ref_names:
        errors.append(f"PERSPECTIVE_BAD_TABLE: perspectiveTable '{tname}' not in model")

print("=== PBIR DIAGNOSTIC RESULTS ===")
print(f"Total issues: {len(errors)}")
print()
for e in sorted(errors):
    print(f"  {e}")
