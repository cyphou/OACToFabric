# Cognos Report Specification Samples

Sample IBM Cognos report specification XML files at three complexity levels.

## Files

| File | Complexity | Queries | Pages | Visuals | Prompts | Description |
|------|-----------|---------|-------|---------|---------|-------------|
| `simple_list_report.xml` | Simple | 1 | 1 | 1 list | 0 | Basic tabular list report |
| `medium_crosstab.xml` | Medium | 2 | 1 | 2 (list + crosstab) | 2 | Crosstab with filters and prompts |
| `complex_dashboard.xml` | Complex | 4 | 3 | 6 (charts, crosstabs, lists) | 4 | Multi-page dashboard with packages |

## XML Structure

Cognos report specs use a `<report>` root element:

- `<dataSource>` — Connection definition with `connectionType`, `server`, `database`
- `<query>` — Data model query with `<dataItem>` children (columns, measures, expressions)
- `<page>` — Report page containing visual elements
- Visual types: `<list>`, `<crosstab>`, `<chart>`, `<repeater>`, `<map>`
- Prompts: `<selectValue>`, `<textBoxPrompt>`, `<datePrompt>`, `<treePrompt>`
- `<package>` — Cognos package references

## Usage

```python
from src.connectors.cognos_connector import CognosReportSpecParser

parser = CognosReportSpecParser()
with open("examples/cognos_samples/simple_list_report.xml") as f:
    report = parser.parse_xml(f.read())

for query in report.get("queries", []):
    print(query["name"], len(query["data_items"]))
```
