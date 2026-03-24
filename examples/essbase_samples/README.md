# Essbase Outline Samples

Sample Oracle Essbase outline exports in XML and JSON (REST API) formats.

## Files

| File | Complexity | Dimensions | Members | Calc Scripts | Description |
|------|-----------|------------|---------|-------------|-------------|
| `simple_budget.xml` | Simple | 3 | 12 | 0 | Basic budget cube — Time, Accounts, Product |
| `simple_budget.json` | Simple | 3 | 12 | 0 | Same cube in JSON REST API format |
| `medium_finance.xml` | Medium | 5 | 30+ | 2 | Finance cube with calc formulas, UDAs, aliases |
| `complex_planning.xml` | Complex | 7 | 60+ | 5+ | Planning cube with all storage types, deep hierarchies |

## XML Structure

Essbase outlines use an `<outline>` root element:

- `<dimension>` — Top-level dimension with `name`, `type` (regular|accounts|time|attribute), `storageType` (dense|sparse)
- `<member>` — Hierarchy member (nested) with `name`, `parent`, `generation`, `level`, `consolidation` (+,-,*,/,~,^), `storageType` (store|dynamic_calc|shared|label_only), `formula`, `uda`, `alias`

## Usage

```python
from src.connectors.essbase_connector import EssbaseOutlineParser

parser = EssbaseOutlineParser()
with open("examples/essbase_samples/simple_budget.xml") as f:
    outline = parser.parse_xml(f.read())

for dim in outline["dimensions"]:
    print(dim["name"], dim["type"])
```
