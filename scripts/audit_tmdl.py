"""Full TMDL model audit — finds all broken references."""
import os
import re
import json
import sys
from collections import Counter

sm_dir = "output/migration_report/MigrationReport/MigrationReport.SemanticModel/definition"
tables_dir = os.path.join(sm_dir, "tables")
issues = []

# 1. Parse all table files
table_names = set()
table_cols = {}
table_measures = {}
table_hiers = {}
for fname in os.listdir(tables_dir):
    if not fname.endswith(".tmdl"):
        continue
    content = open(os.path.join(tables_dir, fname), encoding="utf-8").read()
    tm = re.match(r"^table\s+(?:'([^']+)'|(\w+))", content)
    if not tm:
        continue
    tname = tm.group(1) or tm.group(2)
    table_names.add(tname)
    cols, measures, hiers = set(), set(), set()
    for m in re.finditer(r"^\tcolumn\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        cols.add(m.group(1) or m.group(2))
    for m in re.finditer(r"^\tmeasure\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        measures.add(m.group(1) or m.group(2))
    for m in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        hiers.add(m.group(1) or m.group(2))
    table_cols[tname] = cols
    table_measures[tname] = measures
    table_hiers[tname] = hiers

# 2. model.tmdl ref tables
model = open(os.path.join(sm_dir, "model.tmdl"), encoding="utf-8").read()
for m in re.finditer(r"^ref table\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE):
    ref_name = m.group(1) or m.group(2)
    if ref_name not in table_names:
        issues.append(f"model.tmdl: ref table '{ref_name}' has no .tmdl file")

# 3. Relationships
rel_path = os.path.join(sm_dir, "relationships.tmdl")
if os.path.exists(rel_path):
    rel = open(rel_path, encoding="utf-8").read()
    for m in re.finditer(
        r"(fromColumn|toColumn):\s+(?:'([^']+)'|(\w+))\.(?:'([^']+)'|(\w+))", rel
    ):
        kind = m.group(1)
        tbl = m.group(2) or m.group(3)
        col = m.group(4) or m.group(5)
        if tbl not in table_names:
            issues.append(f"relationships.tmdl: {kind} references unknown table '{tbl}'")
        elif col not in table_cols.get(tbl, set()):
            issues.append(f"relationships.tmdl: {kind} {tbl}.{col} column not found")

# 4. Perspectives
persp_path = os.path.join(sm_dir, "perspectives.tmdl")
if os.path.exists(persp_path):
    persp = open(persp_path, encoding="utf-8").read()
    current_persp = current_table = None
    for line in persp.split("\n"):
        pm = re.match(r"^perspective\s+(?:'([^']+)'|(\w+))", line)
        if pm:
            current_persp = pm.group(1) or pm.group(2)
            continue
        tm = re.match(r"^\tperspectiveTable\s+(?:'([^']+)'|(\w+))", line)
        if tm:
            current_table = tm.group(1) or tm.group(2)
            if current_table not in table_names:
                issues.append(f"perspectives [{current_persp}]: table '{current_table}' not found")
            continue
        cm = re.match(r"^\t\tperspectiveColumn\s+(?:'([^']+)'|(\w+))", line)
        if cm:
            col = cm.group(1) or cm.group(2)
            if current_table in table_cols and col not in table_cols[current_table]:
                issues.append(f"perspectives [{current_persp}]: {current_table}.{col} — perspectiveColumn but not a column")
            continue
        mm = re.match(r"^\t\tperspectiveMeasure\s+(?:'([^']+)'|(\w+))", line)
        if mm:
            meas = mm.group(1) or mm.group(2)
            if current_table in table_measures and meas not in table_measures[current_table]:
                issues.append(f"perspectives [{current_persp}]: {current_table}.{meas} — perspectiveMeasure but not a measure")

# 5. model.tmdl ref perspectives
if os.path.exists(persp_path):
    actual_persps = set()
    for m in re.finditer(r"^perspective\s+(?:'([^']+)'|(\w+))", persp, re.MULTILINE):
        actual_persps.add(m.group(1) or m.group(2))
    model_persps = set()
    for m in re.finditer(r"^ref perspective\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE):
        model_persps.add(m.group(1) or m.group(2))
    for p in model_persps - actual_persps:
        issues.append(f"model.tmdl: ref perspective '{p}' not in perspectives.tmdl")
    for p in actual_persps - model_persps:
        issues.append(f"perspectives.tmdl: '{p}' missing ref in model.tmdl")

# 6. Hierarchy levels
for fname in os.listdir(tables_dir):
    if not fname.endswith(".tmdl"):
        continue
    content = open(os.path.join(tables_dir, fname), encoding="utf-8").read()
    tm = re.match(r"^table\s+(?:'([^']+)'|(\w+))", content)
    if not tm:
        continue
    tname = tm.group(1) or tm.group(2)
    cols = table_cols.get(tname, set())
    for hm in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|(\w+))", content, re.MULTILINE):
        hier_name = hm.group(1) or hm.group(2)
        hier_start = hm.end()
        for lm in re.finditer(r"^\t\tlevel\s+(?:'([^']+)'|(\w+))", content[hier_start:], re.MULTILINE):
            level_end = lm.end() + hier_start
            col_match = re.search(r"^\t\t\tcolumn:\s+(?:'([^']+)'|(\w+))", content[level_end:], re.MULTILINE)
            if col_match:
                col_ref = col_match.group(1) or col_match.group(2)
                if col_ref not in cols:
                    issues.append(f"{fname}: hierarchy {hier_name} level references missing column {col_ref}")

# 7. Empty tables
empty = [t for t in table_names if not table_cols[t] and not table_measures.get(t, set())]
for t in empty:
    issues.append(f"Empty table (no columns/measures): '{t}'")

# 8. Orphaned /// and description:
for root, dirs, files in os.walk(sm_dir):
    for fname in files:
        if not fname.endswith(".tmdl"):
            continue
        content = open(os.path.join(root, fname), encoding="utf-8").read()
        lines = content.strip().split("\n")
        for i, line in enumerate(lines[-5:], len(lines) - 5):
            stripped = line.strip()
            if stripped.startswith("///") and not stripped.startswith("/// <"):
                issues.append(f"{fname}: orphaned /// comment at line {i+1}")
        if re.search(r"^\t+description:", content, re.MULTILINE):
            issues.append(f"{fname}: invalid 'description:' property")

# 9. definition.pbir SM path
pbir_path = "output/migration_report/MigrationReport/MigrationReport.Report/definition.pbir"
if os.path.exists(pbir_path):
    pbir = json.load(open(pbir_path))
    path = pbir.get("datasetReference", {}).get("byPath", {}).get("path", "")
    if "MigrationReport.SemanticModel" not in path:
        issues.append(f"definition.pbir: SM path '{path}' is wrong")

# 10. Duplicate ref entries in model.tmdl
ref_tables = [g[0] or g[1] for g in re.findall(r"^ref table\s+(?:'([^']+)'|(\w+))", model, re.MULTILINE)]
dupes = {k: v for k, v in Counter(ref_tables).items() if v > 1}
if dupes:
    issues.append(f"model.tmdl: duplicate ref table entries: {dupes}")

if issues:
    print(f"ISSUES FOUND: {len(issues)}")
    for i in sorted(issues):
        print(f"  {i}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED!")
