# Tableau Workbook Samples

Sample Tableau workbook XML files (`.twb`) at three complexity levels.

## Files

| File | Complexity | Datasources | Worksheets | Dashboards | Calc Fields | Description |
|------|-----------|-------------|-----------|------------|-------------|-------------|
| `simple_chart.twb` | Simple | 1 | 1 | 0 | 1 | Single bar chart workbook |
| `medium_dashboard.twb` | Medium | 1 | 3 | 1 | 3 | Multi-worksheet dashboard with filters |
| `complex_enterprise.twb` | Complex | 2 | 6 | 2 | 8+ | Enterprise workbook with parameters, multiple data sources |

## XML Structure

Tableau TWB files use a `<workbook>` root element:

- `<datasource>` — Data connection with `<connection>` (class, server, dbname), `<relation>` (tables), `<column>` (fields)
- `<column>` with `<calculation formula="..."/>` — Calculated fields
- `<datasource name="Parameters">` — Parameter definitions
- `<worksheet>` — Individual views with `<datasource-dependencies>`, `<filter>`, `<mark>`
- `<dashboard>` — Dashboard layout with `<zone>` elements

## Usage

```python
from src.connectors.tableau_connector import TableauWorkbookParser

parser = TableauWorkbookParser()
with open("examples/tableau_samples/simple_chart.twb") as f:
    workbook = parser.parse_twb(f.read(), "simple_chart.twb")

for ds in workbook.get("datasources", []):
    print(ds["name"], len(ds["columns"]))
```
