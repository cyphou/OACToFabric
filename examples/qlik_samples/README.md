# Qlik Load Script Samples

Sample Qlik Sense load scripts (`.qvs`) at three complexity levels.

## Files

| File | Complexity | LOAD Stmts | SQL Stmts | Variables | Description |
|------|-----------|-----------|-----------|-----------|-------------|
| `simple_load.qvs` | Simple | 2 | 1 | 1 | Basic SQL SELECT and QVD load |
| `medium_etl.qvs` | Medium | 5 | 2 | 4 | Variables, inline data, resident loads, GROUP BY |
| `complex_pipeline.qvs` | Complex | 10+ | 3 | 8+ | Full ETL with expressions, NOCONCATENATE, multiple sources |

## Script Structure

Qlik scripts are plain text with these constructs:

- `CONNECT TO 'connection_name'` — Data source connections
- `SET/LET variable = value;` — Variable definitions
- `LOAD ... FROM ...;` — Load from file/QVD
- `LOAD ... RESIDENT ...;` — Load from in-memory table
- `LOAD ... INLINE [...];` — Inline data
- `SQL SELECT ... FROM ...;` — SQL passthrough to database
- `NOCONCATENATE LOAD` — Prevent auto-concatenation

## Usage

```python
from src.connectors.qlik_connector import QlikLoadScriptParser

parser = QlikLoadScriptParser()
with open("examples/qlik_samples/simple_load.qvs") as f:
    app_model = parser.parse(f.read())

for table in app_model.get("tables", []):
    print(table["name"], table["fields"])
```
