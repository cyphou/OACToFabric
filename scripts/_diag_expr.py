"""Diagnose Lakehouse expression syntax error."""
content = open('output/migration_report/MigrationReport.SemanticModel/definition/expressions.tmdl', 'r', encoding='utf-8').read()

print("Full file with line numbers:")
for i, line in enumerate(content.split('\n'), 1):
    print(f'{i:3}: {repr(line)}')

# PBI reports error at (1,64) in the expression - this means
# line 1, column 64 of the M expression body itself.
# The expression body for 'Lakehouse' starts after the = sign.
# With triple backticks, the body starts after ```
# But PBI might be treating the whole thing differently.

# Check: does PBI expect the expression on a SINGLE line for simple expressions?
# The ServerName expression is single-line and probably works.
# The error position (1,64) suggests PBI is reading the Lakehouse expression
# as line 1 starting from "expression 'Lakehouse' = ..."
expr_line = "expression 'Lakehouse' ="
print(f"\nExpression declaration: {repr(expr_line)}")
print(f"Length of declaration: {len(expr_line)}")

# Position 64 from the start of the line after expression name
# "expression 'Lakehouse' = " is 25 chars
# Then the triple backtick starts...
full_line = None
for line in content.split('\n'):
    if 'Lakehouse' in line and 'expression' in line:
        full_line = line
        break
if full_line:
    print(f"\nFull Lakehouse line: {repr(full_line)}")
    print(f"Length: {len(full_line)}")
