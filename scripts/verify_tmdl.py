"""Quick TMDL output verification script."""
import os
import re
import json
import sys

sm_dir = "output/migration_report/MigrationReport.SemanticModel/definition"
issues = []

# 1. Orphaned /// and description: property
for root, dirs, files in os.walk(sm_dir):
    for fname in files:
        if not fname.endswith(".tmdl"):
            continue
        path = os.path.join(root, fname)
        content = open(path, encoding="utf-8").read()
        lines = content.strip().split("\n")
        for i, line in enumerate(lines[-5:], len(lines) - 5):
            stripped = line.strip()
            if stripped.startswith("///") and not stripped.startswith("/// <"):
                issues.append(f"{fname}:{i+1}: orphaned /// comment")
        if re.search(r"^\t+description:", content, re.MULTILINE):
            issues.append(f"{fname}: contains description: property")

# 2. definition.pbir SM path
pbir_path = "output/migration_report/MigrationReport.Report/definition.pbir"
if os.path.exists(pbir_path):
    pbir = json.load(open(pbir_path))
    path = pbir.get("datasetReference", {}).get("byPath", {}).get("path", "")
    if "MigrationReport.SemanticModel" in path:
        print(f"definition.pbir SM path: {path} OK")
    else:
        issues.append(f"definition.pbir: SM path is {path}")

# 3. Hierarchy level column validation
tables_dir = os.path.join(sm_dir, "tables")
for fname in sorted(os.listdir(tables_dir)):
    if not fname.endswith(".tmdl"):
        continue
    content = open(os.path.join(tables_dir, fname), encoding="utf-8").read()
    col_names = set()
    for m in re.finditer(r"^\tcolumn\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        col_names.add(m.group(1) or m.group(2))
    for hm in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        hier_name = hm.group(1) or hm.group(2)
        hier_start = hm.end()
        for lm in re.finditer(r"^\t\tlevel\s+(?:'([^']+)'|(\w+))", content[hier_start:], re.MULTILINE):
            level_end = lm.end() + hier_start
            col_match = re.search(r"^\t\t\tcolumn:\s+(?:'([^']+)'|(\w+))", content[level_end:], re.MULTILINE)
            if col_match:
                col_ref = col_match.group(1) or col_match.group(2)
                if col_ref not in col_names:
                    issues.append(f"{fname}: hierarchy {hier_name} level references missing column {col_ref}")

# 4. Perspectives referencing non-existent tables
persp_path = os.path.join(sm_dir, "perspectives.tmdl")
if os.path.exists(persp_path):
    persp = open(persp_path, encoding="utf-8").read()
    table_files = {f.replace(".tmdl", "") for f in os.listdir(tables_dir) if f.endswith(".tmdl")}
    for m in re.finditer(r"^\t\tperspectiveTable\s+(?:'([^']+)'|(\w+))", persp, re.MULTILINE):
        tname = m.group(1) or m.group(2)
        safe = re.sub(r'[<>:"/\\|?*]', "_", tname)
        if safe not in table_files:
            issues.append(f"perspectives.tmdl: references non-existent table {tname}")

if issues:
    print(f"\nISSUES FOUND: {len(issues)}")
    for i in issues:
        print(f"  {i}")
    sys.exit(1)
else:
    print("All TMDL checks passed!")
