"""Diagnose M expression syntax issues in generated TMDL files."""
import os
import re
import sys

SM_DEF = "output/migration_report/MigrationReport/MigrationReport.SemanticModel/definition"
TABLES_DIR = os.path.join(SM_DEF, "tables")
EXPR_PATH = os.path.join(SM_DEF, "expressions.tmdl")

issues = []


def check_m_block(fname, m_code):
    """Check a single M expression block for syntax issues."""
    lines = m_code.strip().split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("//"):
            continue

        # 1. M identifiers with & (operator in M, not valid in identifiers)
        if re.search(r"\w_&_\w", stripped):
            issues.append(f"{fname}: M identifier contains &: {stripped[:100]}")

        # 2. M identifiers with spaces (need #"..." quoting)
        # Check assignments like:  SomeName With Spaces = ...
        m = re.match(r"^([A-Za-z]\w*(?:\s+\w+)+)\s*=\s", stripped)
        if m and not stripped.startswith("Source") and "type table" not in stripped:
            issues.append(f"{fname}: M identifier with spaces needs #\"...\": {stripped[:100]}")

        # 3. Check for unquoted special chars in identifiers
        if re.search(r"\w[\-\+]_\w+\s*=", stripped):
            issues.append(f"{fname}: M identifier with operator: {stripped[:100]}")


def extract_m_blocks(fname, content):
    """Extract and check M source blocks from a TMDL file."""
    lines = content.split("\n")
    in_source = False
    m_lines = []

    for line in lines:
        if re.match(r"\t+source\s*=\s*$", line):
            in_source = True
            m_lines = []
            continue
        if in_source:
            # Source block continues while indented at 3+ tabs or backtick
            if line.startswith("\t\t\t") or line.strip() == "":
                m_lines.append(line)
            else:
                if m_lines:
                    check_m_block(fname, "\n".join(m_lines))
                in_source = False
                m_lines = []

    # Check trailing block
    if m_lines:
        check_m_block(fname, "\n".join(m_lines))


# Check all table TMDL files
for fname in sorted(os.listdir(TABLES_DIR)):
    if not fname.endswith(".tmdl"):
        continue
    path = os.path.join(TABLES_DIR, fname)
    content = open(path, encoding="utf-8").read()
    extract_m_blocks(fname, content)

# Check expressions.tmdl
if os.path.exists(EXPR_PATH):
    content = open(EXPR_PATH, encoding="utf-8").read()
    # Check expression format
    for line_num, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if not stripped:
            continue
        # Each expression should be: expression Name = value meta [...]
        if stripped.startswith("expression "):
            # Validate format
            m = re.match(r'^expression\s+(\w+)\s*=\s*(.+)$', stripped)
            if not m:
                issues.append(f"expressions.tmdl:{line_num}: bad format: {stripped[:100]}")

# Print ALL partition blocks (full content) for manual review
print("=" * 70)
print("  ALL M SOURCE BLOCKS")
print("=" * 70)

for fname in sorted(os.listdir(TABLES_DIR)):
    if not fname.endswith(".tmdl"):
        continue
    path = os.path.join(TABLES_DIR, fname)
    content = open(path, encoding="utf-8").read()
    lines = content.split("\n")
    in_source = False
    m_lines = []

    for line in lines:
        if re.match(r"\t+source\s*=", line):
            in_source = True
            m_lines = [line]
            continue
        if in_source:
            if line.startswith("\t\t\t") or line.strip() == "":
                m_lines.append(line)
            else:
                if m_lines:
                    m_text = "\n".join(m_lines)
                    # Only print if it has potential issues
                    has_issue = any(c in m_text for c in "&-+") or "= ```" in m_text
                    if has_issue:
                        print(f"\n--- {fname} ---")
                        for ml in m_lines:
                            print(repr(ml))
                in_source = False
                m_lines = []

print()
print("=" * 70)
print(f"  ISSUES FOUND: {len(issues)}")
print("=" * 70)
for iss in sorted(issues):
    print(f"  {iss}")

# Also check expressions.tmdl full content
print(f"\n--- expressions.tmdl ---")
if os.path.exists(EXPR_PATH):
    for line in open(EXPR_PATH, encoding="utf-8"):
        print(repr(line.rstrip()))
