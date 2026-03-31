# Examples

Sample source files for every connector supported by **OAC-to-Fabric Migration Accelerator**.
Each subdirectory contains ready-to-parse files at three complexity levels — **simple**, **medium**, and **complex** — so you can evaluate the migration pipeline end-to-end without access to a live source system.

---

## Directory Layout

```
examples/
├── oac_samples/          # Oracle Analytics Cloud RPD XML exports
├── essbase_samples/      # Essbase Outline XML & JSON (REST API)
├── cognos_samples/       # IBM Cognos Report Specification XML
├── qlik_samples/         # Qlik Sense load scripts (.qvs)
├── tableau_samples/      # Tableau Workbook XML (.twb)
├── plugins/              # Custom plugin connector examples
└── validate_samples.py   # Validation script — parse all samples
```

---

## Sample Matrix

| Connector | Simple | Medium | Complex | Format |
|-----------|--------|--------|---------|--------|
| **OAC RPD** | `simple_sales.xml` | `medium_hr.xml` | `complex_enterprise.xml` | XML (`<Repository>`) |
| **Essbase** | `simple_budget.xml` | `medium_finance.xml` | `complex_planning.xml` | XML (`<outline>`) + JSON |
| **Cognos** | `simple_list_report.xml` | `medium_crosstab.xml` | `complex_dashboard.xml` | XML (`<report>`) |
| **Qlik** | `simple_load.qvs` | `medium_etl.qvs` | `complex_pipeline.qvs` | Qlik Script |
| **Tableau** | `simple_chart.twb` | `medium_dashboard.twb` | `complex_enterprise.twb` | XML (`<workbook>`) |

---

## Feature Coverage

| Feature | OAC | Essbase | Cognos | Qlik | Tableau |
|---------|-----|---------|--------|------|---------|
| Tables / Dimensions | ✅ | ✅ | ✅ | ✅ | ✅ |
| Calculated Fields | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hierarchies | ✅ | ✅ | — | — | — |
| Security / RLS | ✅ | — | — | — | — |
| Prompts / Parameters | — | — | ✅ | ✅ | ✅ |
| Multiple Pages | — | — | ✅ | — | ✅ |
| Dashboards | — | — | ✅ | — | ✅ |
| Visualisation Types | — | — | ✅ | — | ✅ |
| ETL / Load Scripts | — | — | — | ✅ | — |
| Calc Scripts / Formulas | — | ✅ | — | — | — |

---

## Quick Start

### Run the full migration example

```bash
# All samples → HTML + Markdown report in output/migration_report/
python examples/full_migration_example.py

# Custom output directory
python examples/full_migration_example.py -o output/my_report

# Single source file
python examples/full_migration_example.py --samples examples/oac_samples/complex_enterprise.xml
```

The full example runs the complete 8-step pipeline (Discovery → Schema → Semantic → Report → Security → ETL → Validation → Report) and produces:

- `migration_report.html` — Self-contained HTML report with SVG charts, dark mode, 8 sections
- `migration_report.md` — Markdown summary
- `SemanticModel/` — TMDL files
- `generated_ddl.sql` — DDL scripts
- `PBIR/` — Power BI report structure
- `validation/` — Validation reports

### Programmatic usage

```python
import asyncio
from examples.full_migration_example import run_full_migration

result = asyncio.run(run_full_migration())
print(result.summary())
# Open result.html_report_path in a browser
```

### Parse a single sample

```python
from src.agents.discovery.rpd_parser import RPDParser

parser = RPDParser()
with open("examples/oac_samples/simple_sales.xml") as f:
    inventory = parser.parse(f.read())
print(inventory)
```

### Validate all samples at once

```bash
python examples/validate_samples.py
```

The script attempts to parse every sample file through its respective connector and reports success or failure.

---

## Adding Your Own Samples

1. Place files in the appropriate `*_samples/` directory.
2. Follow the XML/JSON/script structure documented in each subdirectory's `README.md`.
3. Run `python examples/validate_samples.py` to confirm the file parses correctly.

---

## License

All sample files are synthetic test data created for demonstration purposes.
No real business data is included.
