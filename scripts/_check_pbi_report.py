"""Quick PBI report validator — finds JSON + TMDL errors."""
import json
import os
import re

base = "output/migration_report/MigrationReport"
errors = []

# 1. Check all JSON files
for root, dirs, files in os.walk(base):
    for f in files:
        if f.endswith((".json", ".pbip", ".pbir", ".pbism")) or f == ".platform":
            fp = os.path.join(root, f)
            try:
                json.load(open(fp, encoding="utf-8"))
            except Exception as e:
                rel = fp.replace(base + os.sep, "")
                errors.append((rel, str(e)))

print(f"JSON files with errors: {len(errors)}")
for path, err in errors:
    print(f"  {path}: {err}")

# 2. Check TMDL files
sm_def = os.path.join(base, "MigrationReport.SemanticModel", "definition")
tmdl_issues = []
for root, dirs, files in os.walk(sm_def):
    for f in files:
        if f.endswith(".tmdl"):
            fp = os.path.join(root, f)
            content = open(fp, encoding="utf-8").read()
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                sq = line.count("'")
                if sq % 2 != 0:
                    tmdl_issues.append((f, i, "unbalanced quotes", line.strip()[:100]))
                # Check for empty expression blocks
                if "= ```" in line and line.strip() == "= ```":
                    tmdl_issues.append((f, i, "empty expression", line.strip()[:100]))

print(f"\nTMDL quote issues: {len(tmdl_issues)}")
for fname, line, issue, text in tmdl_issues[:30]:
    print(f"  {fname}:{line} {issue}: {text}")

# 3. Check report.json structure
rpt = os.path.join(base, "MigrationReport.Report", "definition", "report.json")
if os.path.exists(rpt):
    d = json.load(open(rpt, encoding="utf-8"))
    print(f"\nreport.json keys: {list(d.keys())}")

# 4. Check pages.json references
pages_json = os.path.join(base, "MigrationReport.Report", "definition", "pages", "pages.json")
if os.path.exists(pages_json):
    pj = json.load(open(pages_json, encoding="utf-8"))
    page_refs = []
    if isinstance(pj, list):
        page_refs = pj
    elif isinstance(pj, dict):
        page_refs = pj.get("pages", pj.get("pageOrder", []))
    pages_dir = os.path.join(base, "MigrationReport.Report", "definition", "pages")
    actual_dirs = [d for d in os.listdir(pages_dir) if os.path.isdir(os.path.join(pages_dir, d))]
    print(f"\npages.json refs: {len(page_refs)}, actual page dirs: {len(actual_dirs)}")
    # Check each page dir has a page.json
    for d in sorted(actual_dirs):
        pj_path = os.path.join(pages_dir, d, "page.json")
        if not os.path.exists(pj_path):
            print(f"  MISSING page.json in {d}")
        else:
            try:
                pg = json.load(open(pj_path, encoding="utf-8"))
                vis_dir = os.path.join(pages_dir, d, "visuals")
                vis_count = 0
                if os.path.isdir(vis_dir):
                    vis_count = len([v for v in os.listdir(vis_dir)
                                     if os.path.isdir(os.path.join(vis_dir, v))])
                name = pg.get("displayName", pg.get("name", d))
                print(f"  {d}: {name} ({vis_count} visuals)")
            except Exception as e:
                print(f"  {d}: ERROR {e}")

# 5. Check definition.pbir
pbir = os.path.join(base, "MigrationReport.Report", "definition.pbir")
if os.path.exists(pbir):
    d = json.load(open(pbir, encoding="utf-8"))
    print(f"\ndefinition.pbir: {json.dumps(d, indent=2)[:500]}")

# 6. Check model.tmdl ref tables match table files
model_path = os.path.join(sm_def, "model.tmdl")
tables_dir = os.path.join(sm_def, "tables")
if os.path.exists(model_path) and os.path.isdir(tables_dir):
    model = open(model_path, encoding="utf-8").read()
    ref_tables = re.findall(r"^ref table\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE)
    ref_names = [g[0] or g[1] for g in ref_tables]
    table_files = [f.replace(".tmdl", "") for f in os.listdir(tables_dir) if f.endswith(".tmdl")]
    # Check actual table names from file content
    actual_names = set()
    for fname in os.listdir(tables_dir):
        if fname.endswith(".tmdl"):
            content = open(os.path.join(tables_dir, fname), encoding="utf-8").read()
            m = re.match(r"^table\s+(?:'([^']+)'|(\w+))", content)
            if m:
                actual_names.add(m.group(1) or m.group(2))
    missing = [r for r in ref_names if r not in actual_names]
    if missing:
        print(f"\nmodel.tmdl refs missing table files: {missing}")
    else:
        print(f"\nmodel.tmdl: all {len(ref_names)} ref tables have matching files")
