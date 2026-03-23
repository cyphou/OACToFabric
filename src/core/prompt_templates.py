"""Prompt templates for LLM-assisted translation.

Each template encapsulates:
- A system prompt (role & constraints)
- A user prompt template with `{placeholders}`
- Extraction logic to parse the LLM response

Translation domains:
- OAC expressions → DAX measures
- PL/SQL procedures → PySpark / Spark SQL
- OAC session variables → RLS DAX filters
- OAC visual XML → Power BI visual JSON
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PromptTemplate:
    """Reusable prompt template."""

    name: str
    system_prompt: str
    user_template: str
    response_format: str = "text"  # "text", "json", "code"

    def render(self, **kwargs: Any) -> tuple[str, str]:
        """Return (system_prompt, user_prompt) with placeholders filled."""
        return self.system_prompt, self.user_template.format(**kwargs)


# ---------------------------------------------------------------------------
# OAC Expression → DAX
# ---------------------------------------------------------------------------

OAC_TO_DAX = PromptTemplate(
    name="oac_to_dax",
    system_prompt="""\
You are an expert in Oracle Analytics Cloud (OAC) and Power BI DAX.
Convert the given OAC logical column expression into an equivalent DAX measure.

Rules:
- Use only standard DAX functions.
- Preserve the business logic exactly.
- Use table[column] notation for column references.
- Return ONLY the DAX expression, no explanation.
- If the expression uses an OAC function with no DAX equivalent, add a comment.
""",
    user_template="""\
Convert this OAC expression to DAX:

Source table: {table_name}
OAC Expression: {oac_expression}

Column mappings:
{column_mappings}

Return the DAX expression only:""",
    response_format="code",
)

# ---------------------------------------------------------------------------
# PL/SQL → PySpark
# ---------------------------------------------------------------------------

PLSQL_TO_PYSPARK = PromptTemplate(
    name="plsql_to_pyspark",
    system_prompt="""\
You are an expert in Oracle PL/SQL and Apache PySpark.
Convert the given PL/SQL stored procedure or ETL logic into PySpark code.

Rules:
- Use PySpark DataFrame API (not spark.sql() unless necessary).
- Preserve the data transformation logic exactly.
- Use Delta Lake format for output tables.
- Handle NULL values consistently.
- Return ONLY the Python/PySpark code, no explanation.
- Add type hints where possible.
""",
    user_template="""\
Convert this PL/SQL to PySpark:

```sql
{plsql_code}
```

Source tables → Delta tables mapping:
{table_mappings}

Return the PySpark code only:""",
    response_format="code",
)

# ---------------------------------------------------------------------------
# Session Variable → RLS DAX Filter
# ---------------------------------------------------------------------------

SESSION_VAR_TO_RLS = PromptTemplate(
    name="session_var_to_rls",
    system_prompt="""\
You are an expert in Oracle Analytics Cloud security and Power BI Row-Level Security (RLS).
Convert the given OAC session variable-based security filter into an equivalent DAX RLS filter expression.

Rules:
- Use USERPRINCIPALNAME() or USERNAME() as appropriate.
- Map OAC session variables to their RLS equivalents.
- Return ONLY the DAX filter expression.
- The filter must return a boolean for table filtering.
""",
    user_template="""\
Convert this OAC session variable filter to a DAX RLS filter:

OAC Filter: {oac_filter}
Session Variable: {session_variable}
Target Table: {table_name}
Target Column: {column_name}

Column context:
{column_context}

Return the DAX RLS filter expression only:""",
    response_format="code",
)

# ---------------------------------------------------------------------------
# OAC Visual → Power BI Visual Config
# ---------------------------------------------------------------------------

OAC_VISUAL_TO_PBI = PromptTemplate(
    name="oac_visual_to_pbi",
    system_prompt="""\
You are an expert in Oracle Analytics Cloud dashboards and Power BI report visuals.
Convert the given OAC visual definition into a Power BI visual configuration.

Rules:
- Map the OAC chart type to the closest Power BI visual type.
- Preserve data bindings (measures, dimensions, filters).
- Map formatting where possible.
- Return a JSON object with the Power BI visual configuration.
""",
    user_template="""\
Convert this OAC visual to Power BI:

OAC Visual Type: {visual_type}
OAC Definition:
```xml
{visual_xml}
```

Available measures: {measures}
Available dimensions: {dimensions}

Return the Power BI visual config as JSON:""",
    response_format="json",
)

# ---------------------------------------------------------------------------
# Generic SQL Translation
# ---------------------------------------------------------------------------

ORACLE_SQL_TO_SPARK_SQL = PromptTemplate(
    name="oracle_sql_to_spark_sql",
    system_prompt="""\
You are an expert in Oracle SQL and Apache Spark SQL.
Convert the given Oracle SQL query to Spark SQL syntax.

Rules:
- Replace Oracle-specific functions with Spark SQL equivalents.
- Handle date functions, string functions, and analytical functions.
- Replace Oracle data types with Spark SQL data types.
- Preserve query logic exactly.
- Return ONLY the Spark SQL query.
""",
    user_template="""\
Convert this Oracle SQL to Spark SQL:

```sql
{oracle_sql}
```

Table mappings:
{table_mappings}

Return the Spark SQL query only:""",
    response_format="code",
)

# ---------------------------------------------------------------------------
# Template registry
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, PromptTemplate] = {
    t.name: t
    for t in [
        OAC_TO_DAX,
        PLSQL_TO_PYSPARK,
        SESSION_VAR_TO_RLS,
        OAC_VISUAL_TO_PBI,
        ORACLE_SQL_TO_SPARK_SQL,
    ]
}


def get_template(name: str) -> PromptTemplate:
    """Retrieve a prompt template by name."""
    if name not in TEMPLATES:
        raise KeyError(f"Unknown prompt template: {name}. Available: {list(TEMPLATES.keys())}")
    return TEMPLATES[name]
