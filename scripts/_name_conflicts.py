"""Find column/hierarchy name conflicts in TMDL tables."""
import os
import re

tables_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "migration_report", "MigrationReport",
    "MigrationReport.SemanticModel", "definition", "tables",
)

for fname in sorted(os.listdir(tables_dir)):
    if not fname.endswith(".tmdl"):
        continue
    content = open(os.path.join(tables_dir, fname), encoding="utf-8").read()
    cols = set()
    measures = set()
    for m in re.finditer(r"^\tcolumn\s+(?:'([^']+)'|([A-Za-z_]\w*))", content, re.MULTILINE):
        cols.add(m.group(1) or m.group(2))
    for m in re.finditer(r"^\tmeasure\s+(?:'([^']+)'|([A-Za-z_]\w*))", content, re.MULTILINE):
        measures.add(m.group(1) or m.group(2))
    for m in re.finditer(r"^\thierarchy\s+(?:'([^']+)'|([A-Za-z_]\w*))", content, re.MULTILINE):
        hname = m.group(1) or m.group(2)
        if hname in cols:
            print(f"CONFLICT: {fname} — column AND hierarchy both named '{hname}'")
        if hname in measures:
            print(f"CONFLICT: {fname} — measure AND hierarchy both named '{hname}'")
