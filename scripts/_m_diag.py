"""Scan TMDL partition M expressions for syntax issues."""
import os
import re

tables_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "migration_report", "MigrationReport",
    "MigrationReport.SemanticModel", "definition", "tables",
)

# Also check expressions.tmdl
sm_dir = os.path.dirname(tables_dir)
files_to_check = []
for fname in sorted(os.listdir(tables_dir)):
    if fname.endswith(".tmdl"):
        files_to_check.append(os.path.join(tables_dir, fname))
expr_path = os.path.join(sm_dir, "expressions.tmdl")
if os.path.exists(expr_path):
    files_to_check.append(expr_path)

total_issues = 0

for fpath in files_to_check:
    fname = os.path.basename(fpath)
    content = open(fpath, encoding="utf-8").read()
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        # Find partition source lines with M code
        stripped = line.strip()

        # Check expression declarations (expressions.tmdl)
        if fname == "expressions.tmdl":
            # expression Name = "value" meta [...]
            m = re.match(r'^expression\s+\w+\s*=\s*(.+?)(\s+meta\s+.*)?$', stripped)
            if m:
                val = m.group(1).strip()
                # Value must be a quoted string like "localhost"
                if val and not val.startswith('"'):
                    print(f"  {fname}:{i} expression value not quoted: {stripped[:120]}")
                    total_issues += 1

    # Extract all M partition source blocks
    # Match: source =\n\t\t\t\tlet\n...in\n\t\t\t\tResult
    # or: source = \n\t\t\t\t#table(...)
    partition_blocks = re.finditer(
        r'partition\s+[^\n]+\s*=\s*m\n(.*?)(?=\n\t(?:annotation|column|measure|hierarchy|partition)\s|\Z)',
        content, re.DOTALL,
    )

    for pmatch in partition_blocks:
        block = pmatch.group(1)
        block_start = content[:pmatch.start()].count("\n") + 1

        # Extract the source = ... part
        source_match = re.search(r'source\s*=\s*\n(.*)', block, re.DOTALL)
        if not source_match:
            # Single-line source
            source_match = re.search(r'source\s*=\s*(.+)', block)
            if source_match:
                m_code = source_match.group(1).strip()
            else:
                continue
        else:
            raw = source_match.group(1)
            m_lines = []
            for ml in raw.split("\n"):
                s = ml.strip()
                if not s:
                    continue
                # Stop at next TMDL directive
                if re.match(r'^(annotation|column|measure|hierarchy|partition|table)\s', s):
                    break
                m_lines.append(s)
            m_code = "\n".join(m_lines)

        if not m_code:
            continue

        issues = []

        # 1. Unmatched double quotes
        dq = m_code.count('"')
        if dq % 2 != 0:
            issues.append(f"unmatched double-quotes ({dq})")

        # 2. Unmatched parens
        op = m_code.count("(")
        cp = m_code.count(")")
        if op != cp:
            issues.append(f"unmatched parens ({op} open, {cp} close)")

        # 3. Unmatched braces
        ob = m_code.count("{")
        cb = m_code.count("}")
        if ob != cb:
            issues.append(f"unmatched braces ({ob} open, {cb} close)")

        # 4. Unmatched brackets
        osq = m_code.count("[")
        csq = m_code.count("]")
        if osq != csq:
            issues.append(f"unmatched brackets ({osq} open, {csq} close)")

        # 5. let without in
        has_let = bool(re.search(r'\blet\b', m_code, re.IGNORECASE))
        has_in = bool(re.search(r'\bin\b', m_code))
        if has_let and not has_in:
            issues.append("let without in")

        # 6. Empty #table with bad syntax
        if "#table" in m_code:
            # #table(type table [...], {...}) is valid
            # #table(type table [], {}) is valid
            pass

        # 7. Trailing comma before closing paren/brace
        if re.search(r',\s*\)', m_code):
            issues.append("trailing comma before )")
        if re.search(r',\s*\}', m_code):
            issues.append("trailing comma before }")

        # 8. Missing comma between let bindings
        let_match = re.search(r'let\s*\n(.*?)\n\s*in\b', m_code, re.DOTALL)
        if let_match:
            bindings = let_match.group(1)
            blines = [bl.strip() for bl in bindings.split("\n") if bl.strip()]
            for bi, bline in enumerate(blines[:-1]):  # all but last should end with comma
                if not bline.endswith(","):
                    issues.append(f"let binding missing comma: {bline[:80]}")

        if issues:
            total_issues += len(issues)
            # Find partition name
            pname_match = re.search(r"partition\s+'([^']+)'|partition\s+(\S+)", content[pmatch.start():pmatch.start()+200])
            pname = (pname_match.group(1) or pname_match.group(2)) if pname_match else "unknown"
            print(f"  {fname} partition '{pname}':")
            for issue in issues:
                print(f"    - {issue}")
            print(f"    M code: {m_code[:300]}")
            print()

# Also print ALL M expressions for manual review
print("=" * 70)
print("ALL PARTITION M EXPRESSIONS:")
print("=" * 70)
for fpath in files_to_check:
    fname = os.path.basename(fpath)
    content = open(fpath, encoding="utf-8").read()

    for pmatch in re.finditer(
        r"(partition\s+[^\n]+\s*=\s*m\n.*?source\s*=\s*\n?(.*?))(?=\n\t(?:annotation|column|measure|hierarchy|partition)\s|\Z)",
        content, re.DOTALL,
    ):
        src = pmatch.group(2).strip()
        # Get just the M code lines
        m_lines = []
        for ml in src.split("\n"):
            s = ml.strip()
            if not s or re.match(r'^(annotation|column|measure|hierarchy|partition|table)\s', s):
                break
            m_lines.append(s)
        m_code = "\n".join(m_lines)
        if m_code:
            pname_match = re.search(r"partition\s+'([^']+)'|partition\s+(\S+)", pmatch.group(1)[:200])
            pname = (pname_match.group(1) or pname_match.group(2)) if pname_match else "unknown"
            print(f"\n{fname} :: {pname}")
            print(f"  {m_code[:400]}")

print(f"\n\nTotal issues: {total_issues}")
