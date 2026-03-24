# OAC RPD XML Samples

Sample Oracle Analytics Cloud Repository (RPD) XML exports at three complexity levels.

## Files

| File | Complexity | Tables | Columns | Hierarchies | Security Roles | Description |
|------|-----------|--------|---------|-------------|----------------|-------------|
| `simple_sales.xml` | Simple | 2 | 8 | 0 | 0 | Two physical tables, one subject area |
| `medium_hr.xml` | Medium | 4 | 16 | 2 | 1 | HR model with hierarchies, init blocks, security |
| `complex_enterprise.xml` | Complex | 8 | 32+ | 3 | 2 | Full enterprise RPD with all features |

## XML Structure

The RPD XML uses a `<Repository>` root element with the following top-level tags:

- `<PhysicalTable>` — Physical database tables with `<PhysicalColumn>` children
- `<LogicalTable>` — Business model tables with `<LogicalColumn>`, `<LogicalHierarchy>`, `<LogicalTableSource>`
- `<SubjectArea>` — Presentation layer groupings with `<PresentationTable>` / `<PresentationColumn>`
- `<SecurityRole>` — Application roles with `<Member>` and `<Permission>`
- `<InitBlock>` — Session variable initialisation blocks with `<SQL>` and `<Variable>`
- `<Connection>` — Database connection definitions
- `<DataFlow>` — Data flow definitions

## Usage

```python
from src.agents.discovery.rpd_parser import RPDParser

parser = RPDParser()
with open("examples/oac_samples/simple_sales.xml") as f:
    inventory = parser.parse(f.read())

for table in inventory.get("physical_tables", []):
    print(table["name"])
```
