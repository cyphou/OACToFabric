"""PL/SQL → PySpark translator — rule-based + LLM-assisted.

Translates Oracle PL/SQL stored procedures and anonymous blocks
into PySpark notebook code that runs on Microsoft Fabric.

Translation strategy:
  1. Rule-based rewriting for common patterns
  2. LLM-assisted translation (Azure OpenAI GPT-4) for complex logic
  3. Flagged for manual review when confidence is low
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class TranslationResult:
    """Result of translating a single PL/SQL block."""

    procedure_name: str
    original_plsql: str
    pyspark_code: str
    method: str = "rule-based"      # "rule-based" | "llm" | "hybrid" | "manual"
    confidence: float = 1.0         # 0.0–1.0
    warnings: list[str] = field(default_factory=list)
    untranslated_sections: list[str] = field(default_factory=list)
    requires_review: bool = False


# ---------------------------------------------------------------------------
# Rule-based PL/SQL → PySpark rewriting
# ---------------------------------------------------------------------------

# Each rule: (regex_pattern, pyspark_replacement_or_callable, description)
_PLSQL_RULES: list[tuple[re.Pattern[str], str | None, str]] = [
    # DBMS_OUTPUT.PUT_LINE → print / logger
    (
        re.compile(r"DBMS_OUTPUT\.PUT_LINE\s*\(\s*(.+?)\s*\)\s*;", re.IGNORECASE),
        r"logger.info(\1)",
        "DBMS_OUTPUT → logger",
    ),
    # SYSDATE → current_timestamp()
    (
        re.compile(r"\bSYSDATE\b", re.IGNORECASE),
        "F.current_timestamp()",
        "SYSDATE → current_timestamp",
    ),
    # COMMIT; → (no-op in Spark, Delta handles transactions)
    (
        re.compile(r"\bCOMMIT\s*;", re.IGNORECASE),
        "# COMMIT — handled by Delta Lake transactions",
        "COMMIT → no-op",
    ),
    # ROLLBACK; → (no-op / Delta time travel)
    (
        re.compile(r"\bROLLBACK\s*;", re.IGNORECASE),
        "# ROLLBACK — use Delta Lake time travel if needed",
        "ROLLBACK → no-op",
    ),
    # NVL(a, b) → F.coalesce(a, b)
    (
        re.compile(r"\bNVL\s*\(\s*([^,]+),\s*([^)]+)\)", re.IGNORECASE),
        r"F.coalesce(\1, \2)",
        "NVL → coalesce",
    ),
    # TO_DATE → F.to_date
    (
        re.compile(r"\bTO_DATE\s*\(", re.IGNORECASE),
        "F.to_date(",
        "TO_DATE → F.to_date",
    ),
    # TO_CHAR → date_format
    (
        re.compile(r"\bTO_CHAR\s*\(", re.IGNORECASE),
        "F.date_format(",
        "TO_CHAR → F.date_format",
    ),
    # TRUNC(date) → F.date_trunc
    (
        re.compile(r"\bTRUNC\s*\(\s*([^)]+)\)", re.IGNORECASE),
        r"F.date_trunc('day', \1)",
        "TRUNC → date_trunc",
    ),
    # || concatenation → F.concat
    (
        re.compile(r"(\w+)\s*\|\|\s*(\w+)", re.IGNORECASE),
        r"F.concat(\1, \2)",
        "|| → concat",
    ),
]


# Block-level patterns (structural transforms)
_INSERT_SELECT = re.compile(
    r"INSERT\s+INTO\s+(\w+(?:\.\w+)?)\s*(?:\([^)]*\))?\s*SELECT\s+(.+?)(?:;|\bEND\b)",
    re.IGNORECASE | re.DOTALL,
)

_UPDATE_SET = re.compile(
    r"UPDATE\s+(\w+(?:\.\w+)?)\s+SET\s+(.+?)\s+WHERE\s+(.+?)(?:;|\bEND\b)",
    re.IGNORECASE | re.DOTALL,
)

_DELETE_FROM = re.compile(
    r"DELETE\s+FROM\s+(\w+(?:\.\w+)?)\s+WHERE\s+(.+?)(?:;|\bEND\b)",
    re.IGNORECASE | re.DOTALL,
)

_MERGE_INTO = re.compile(
    r"MERGE\s+INTO\s+(\w+(?:\.\w+)?)\s+",
    re.IGNORECASE,
)

_CURSOR_LOOP = re.compile(
    r"(?:CURSOR\s+(\w+)\s+IS\s+)?(SELECT\s+.+?)\s*;\s*(?:BEGIN\s+)?FOR\s+\w+\s+IN\s+(?:\w+|\(.+?\))\s+LOOP\s+(.+?)\s+END\s+LOOP",
    re.IGNORECASE | re.DOTALL,
)

_EXECUTE_IMMEDIATE = re.compile(
    r"EXECUTE\s+IMMEDIATE\s+(.+?)\s*;",
    re.IGNORECASE | re.DOTALL,
)

_EXCEPTION_BLOCK = re.compile(
    r"EXCEPTION\s+WHEN\s+(\w+)\s+THEN\s+(.+?)(?=EXCEPTION|END\s*;|$)",
    re.IGNORECASE | re.DOTALL,
)

# FOR i IN 1..N LOOP ... END LOOP
_FOR_NUMERIC_LOOP = re.compile(
    r"FOR\s+(\w+)\s+IN\s+(\d+)\s*\.\.\s*(\w+)\s+LOOP\s+(.+?)\s+END\s+LOOP",
    re.IGNORECASE | re.DOTALL,
)

# WHILE condition LOOP ... END LOOP
_WHILE_LOOP = re.compile(
    r"WHILE\s+(.+?)\s+LOOP\s+(.+?)\s+END\s+LOOP",
    re.IGNORECASE | re.DOTALL,
)

# RAISE_APPLICATION_ERROR(-20001, 'message');
_RAISE_APP_ERROR = re.compile(
    r"RAISE_APPLICATION_ERROR\s*\(\s*(-?\d+)\s*,\s*(.+?)\s*\)\s*;",
    re.IGNORECASE,
)

# RAISE exception_name;
_RAISE_EXCEPTION = re.compile(
    r"\bRAISE\s+(\w+)\s*;",
    re.IGNORECASE,
)

# EXECUTE IMMEDIATE with USING bind variables
_EXECUTE_IMMEDIATE_USING = re.compile(
    r"EXECUTE\s+IMMEDIATE\s+(.+?)\s+USING\s+(.+?)\s*;",
    re.IGNORECASE | re.DOTALL,
)


def translate_plsql(
    plsql: str,
    procedure_name: str = "unnamed",
    table_mapping: dict[str, str] | None = None,
) -> TranslationResult:
    """Translate a PL/SQL block to PySpark code using rule-based patterns.

    Parameters
    ----------
    plsql : str
        The Oracle PL/SQL source code.
    procedure_name : str
        Name for the procedure (used in output header).
    table_mapping : dict
        Optional Oracle → Fabric table name mapping.
    """
    tmap = table_mapping or {}
    warnings: list[str] = []
    untranslated: list[str] = []
    confidence = 1.0

    lines = [
        f'"""PySpark translation of Oracle procedure: {procedure_name}',
        f'Auto-generated by Agent 03 — ETL Migration Agent',
        f'"""',
        "",
        "import logging",
        "from pyspark.sql import functions as F",
        "from delta.tables import DeltaTable",
        "",
        "logger = logging.getLogger(__name__)",
        "",
    ]

    body = plsql

    # --- Structural transforms (order matters) ---

    # MERGE INTO → DeltaTable.merge
    if _MERGE_INTO.search(body):
        lines.append("# MERGE detected — using Delta Lake merge")
        lines.append("# Review: Ensure merge conditions and update/insert clauses are correct")
        body = _translate_merge(body, tmap)
        warnings.append("MERGE INTO detected — verify Delta merge logic")
        confidence = min(confidence, 0.7)

    # INSERT INTO ... SELECT → df.write.mode("append")
    for m in _INSERT_SELECT.finditer(body):
        target = _map_table(m.group(1), tmap)
        select = m.group(2).strip()
        lines.append(f'# INSERT INTO {m.group(1)} SELECT ...')
        lines.append(f'df_insert = spark.sql("""{select}""")')
        lines.append(f'df_insert.write.mode("append").format("delta").saveAsTable("{target}")')
        lines.append("")

    # UPDATE ... SET ... WHERE → Delta merge (update only)
    for m in _UPDATE_SET.finditer(body):
        target = _map_table(m.group(1), tmap)
        set_clause = m.group(2).strip()
        where_clause = m.group(3).strip()
        lines.append(f"# UPDATE {m.group(1)} SET ... WHERE ...")
        lines.append(f'delta_table = DeltaTable.forName(spark, "{target}")')
        lines.append(f"# Condition: {where_clause}")
        lines.append(f"# Set: {set_clause}")
        lines.append(f'delta_table.update(condition="{where_clause}", set={{{_parse_set_clause(set_clause)}}})')
        lines.append("")
        warnings.append(f"UPDATE on {target} — verify condition and set expressions")
        confidence = min(confidence, 0.8)

    # DELETE FROM ... WHERE → Delta delete
    for m in _DELETE_FROM.finditer(body):
        target = _map_table(m.group(1), tmap)
        where_clause = m.group(2).strip()
        lines.append(f"# DELETE FROM {m.group(1)} WHERE ...")
        lines.append(f'delta_table = DeltaTable.forName(spark, "{target}")')
        lines.append(f'delta_table.delete(condition="{where_clause}")')
        lines.append("")

    # CURSOR ... LOOP → DataFrame collect + Python loop
    for m in _CURSOR_LOOP.finditer(body):
        query = m.group(2).strip()
        loop_body = m.group(3).strip()
        translated_body = _translate_loop_body(loop_body, tmap)
        lines.append(f"# CURSOR LOOP")
        lines.append(f'df_cursor = spark.sql("""{query}""")')
        if translated_body.strip() == "pass":
            # Could not translate — leave comment
            lines.append(f"for row in df_cursor.collect():")
            lines.append(f"    pass  # Manual review: {loop_body[:100]}...")
            warnings.append("CURSOR LOOP body could not be translated — manual review required")
            confidence = min(confidence, 0.4)
        else:
            lines.append(f"for row in df_cursor.collect():")
            for tl in translated_body.splitlines():
                lines.append(f"    {tl}")
            warnings.append("CURSOR LOOP detected — consider DataFrame operations instead of row-by-row")
            confidence = min(confidence, 0.6)
        lines.append("")

    # EXECUTE IMMEDIATE → spark.sql()
    for m in _EXECUTE_IMMEDIATE.finditer(body):
        ddl = m.group(1).strip().strip("'\"")
        lines.append(f'spark.sql("""{ddl}""")')
        lines.append("")

    # FORALL → batch DataFrame write
    forall_pattern = re.compile(
        r"FORALL\s+(\w+)\s+IN\s+(.+?)\s+(INSERT|UPDATE|DELETE)\s+",
        re.IGNORECASE | re.DOTALL,
    )
    for m in forall_pattern.finditer(body):
        idx_var = m.group(1)
        range_expr = m.group(2).strip()
        dml_type = m.group(3).upper()
        lines.append(f"# FORALL {idx_var} IN {range_expr} {dml_type}")
        lines.append(f"# Converted to batch DataFrame operation:")
        lines.append(f'df_batch = spark.createDataFrame(batch_data)  # Populate from source')
        if dml_type == "INSERT":
            lines.append(f'df_batch.write.mode("append").format("delta").saveAsTable("target_table")')
        elif dml_type == "UPDATE":
            lines.append(f'target_dt = DeltaTable.forName(spark, "target_table")')
            lines.append(f'target_dt.alias("t").merge(df_batch.alias("s"), "t.id = s.id").whenMatchedUpdateAll().execute()')
        elif dml_type == "DELETE":
            lines.append(f'target_dt = DeltaTable.forName(spark, "target_table")')
            lines.append(f'target_dt.alias("t").merge(df_batch.alias("s"), "t.id = s.id").whenMatchedDelete().execute()')
        lines.append("")
        warnings.append(f"FORALL {dml_type} converted to batch — verify table name and join condition")
        confidence = min(confidence, 0.6)

    # BULK COLLECT → DataFrame collect
    bulk_pattern = re.compile(
        r"SELECT\s+(.+?)\s+BULK\s+COLLECT\s+INTO\s+(\w+)\s+FROM\s+(\w+(?:\.\w+)?)",
        re.IGNORECASE | re.DOTALL,
    )
    for m in bulk_pattern.finditer(body):
        columns = m.group(1).strip()
        collection_var = m.group(2).strip()
        source_table = _map_table(m.group(3), tmap)
        lines.append(f"# BULK COLLECT INTO {collection_var}")
        lines.append(f'{collection_var} = spark.sql("SELECT {columns} FROM {source_table}").collect()')
        lines.append("")
        confidence = min(confidence, 0.7)

    # EXCEPTION blocks → try/except
    exc_matches = list(_EXCEPTION_BLOCK.finditer(body))
    if exc_matches:
        lines.insert(-1, "try:")
        for em in exc_matches:
            exc_type = em.group(1)
            exc_body = em.group(2).strip()
            py_exc = "Exception" if exc_type.upper() == "OTHERS" else exc_type
            lines.append(f"except {py_exc} as e:")
            lines.append(f"    logger.error(f'Error: {{e}}')")
            lines.append(f"    # Original handler: {exc_body[:80]}...")

    # FOR i IN 1..N LOOP → Python for range
    for m in _FOR_NUMERIC_LOOP.finditer(body):
        var = m.group(1)
        start_val = m.group(2)
        end_val = m.group(3)
        loop_body = m.group(4).strip()
        translated_body = _translate_loop_body(loop_body, tmap)
        lines.append(f"for {var} in range({start_val}, {end_val} + 1):")
        if translated_body.strip() == "pass":
            lines.append(f"    pass  # Manual review: {loop_body[:100]}")
        else:
            for tl in translated_body.splitlines():
                lines.append(f"    {tl}")
        lines.append("")
        warnings.append("FOR numeric loop detected — consider vectorized DataFrame ops")
        confidence = min(confidence, 0.7)

    # WHILE condition LOOP → Python while
    for m in _WHILE_LOOP.finditer(body):
        condition = _plsql_cond_to_python(m.group(1).strip())
        loop_body = m.group(2).strip()
        translated_body = _translate_loop_body(loop_body, tmap)
        lines.append(f"while {condition}:")
        if translated_body.strip() == "pass":
            lines.append(f"    pass  # Manual review: {loop_body[:100]}")
        else:
            for tl in translated_body.splitlines():
                lines.append(f"    {tl}")
        lines.append("")
        warnings.append("WHILE loop detected — consider DataFrame operations")
        confidence = min(confidence, 0.6)

    # RAISE_APPLICATION_ERROR → raise RuntimeError
    for m in _RAISE_APP_ERROR.finditer(body):
        error_code = m.group(1)
        error_msg = m.group(2).strip().strip("'\"")
        lines.append(f'raise RuntimeError(f"Oracle error {error_code}: {error_msg}")')
        lines.append("")

    # RAISE exception_name → raise
    for m in _RAISE_EXCEPTION.finditer(body):
        exc_name = m.group(1)
        if exc_name.upper() in ("NO_DATA_FOUND", "TOO_MANY_ROWS"):
            lines.append(f"raise LookupError('{exc_name}')")
        else:
            lines.append(f"raise RuntimeError('{exc_name}')")
        lines.append("")

    # EXECUTE IMMEDIATE ... USING bind vars → spark.sql parameterized
    for m in _EXECUTE_IMMEDIATE_USING.finditer(body):
        ddl = m.group(1).strip().strip("'\"")
        bind_vars = m.group(2).strip()
        lines.append(f"# EXECUTE IMMEDIATE with bind variables")
        lines.append(f"_sql = f\"\"\"{ddl}\"\"\"  # bind vars: {bind_vars}")
        lines.append(f'spark.sql(_sql)')
        lines.append("")
        warnings.append("EXECUTE IMMEDIATE USING — verify bind variable substitution")
        confidence = min(confidence, 0.5)

    # --- Simple token-level replacements ---
    for pattern, replacement, desc in _PLSQL_RULES:
        if pattern.search(body) and replacement:
            # Just note that we applied the rule; the structural code above
            # is the primary output
            pass

    # --- Check for untranslated PL/SQL constructs ---
    untranslated_patterns = [
        (r"\bPACKAGE\s+BODY\b", "PACKAGE BODY"),
        (r"\bTYPE\s+\w+\s+IS\s+TABLE\b", "PL/SQL collection TYPE"),
        (r"\bPIPELINED\b", "PIPELINED function"),
        (r"\bAUTONOMOUS_TRANSACTION\b", "AUTONOMOUS_TRANSACTION"),
        (r"\bDBMS_(?!OUTPUT)\w+", "DBMS_ package call"),
        (r"\bUTL_\w+", "UTL_ package call"),
        (r"\bREF\s+CURSOR\b", "REF CURSOR"),
    ]
    for pattern_str, desc in untranslated_patterns:
        if re.search(pattern_str, body, re.IGNORECASE):
            untranslated.append(desc)
            confidence = min(confidence, 0.3)
            warnings.append(f"Untranslatable pattern: {desc}")

    if confidence < 0.6:
        lines.append("")
        lines.append("# ⚠️ LOW CONFIDENCE — manual review strongly recommended")
        lines.append(f"# Confidence: {confidence:.0%}")
        lines.append("# Consider using LLM-assisted translation for complex blocks")

    return TranslationResult(
        procedure_name=procedure_name,
        original_plsql=plsql,
        pyspark_code="\n".join(lines),
        method="rule-based",
        confidence=confidence,
        warnings=warnings,
        untranslated_sections=untranslated,
        requires_review=confidence < 0.8,
    )


# ---------------------------------------------------------------------------
# LLM translation prompt builder
# ---------------------------------------------------------------------------


def build_llm_prompt(
    plsql: str,
    procedure_name: str = "unnamed",
    table_mapping: dict[str, str] | None = None,
) -> str:
    """Build an Azure OpenAI prompt for PL/SQL → PySpark translation.

    The actual LLM call is done externally (e.g. via the Azure OpenAI SDK).
    This function just builds the prompt string.
    """
    tmap_json = ""
    if table_mapping:
        import json
        tmap_json = json.dumps(table_mapping, indent=2)

    return f"""You are an expert data engineer. Convert the following Oracle PL/SQL stored procedure
into a PySpark Notebook that runs on Microsoft Fabric.

Rules:
- Use Delta Lake for all table operations
- Use spark.sql() for SQL operations where appropriate
- Use DataFrame API for transformations
- Replace Oracle-specific functions with PySpark equivalents
- Maintain the same business logic and error handling
- Add logging using Python's logging module
- The Lakehouse is already attached; tables are in the default catalog
- Wrap the main logic in a function named `run_{_safe_name(procedure_name)}`
- Include comprehensive error handling with try/except
- Add docstrings explaining the original purpose

Source PL/SQL:
```sql
{plsql}
```

Target table mapping:
```json
{tmap_json or '{}'}
```

Generate the PySpark notebook code:"""


def translate_with_fallback(
    plsql: str,
    procedure_name: str = "unnamed",
    table_mapping: dict[str, str] | None = None,
    llm_client: Any = None,
) -> TranslationResult:
    """Try rule-based translation first; fall back to LLM if confidence is low.

    Parameters
    ----------
    llm_client : optional
        An object with a `complete(prompt: str) -> str` method
        (e.g. an Azure OpenAI wrapper). If None, LLM fallback is skipped.
    """
    # Step 1: rule-based
    result = translate_plsql(plsql, procedure_name, table_mapping)

    # Step 2: if low confidence and LLM is available, try LLM
    if result.confidence < 0.6 and llm_client is not None:
        logger.info("Rule-based confidence %.0f%% for '%s' — trying LLM", result.confidence * 100, procedure_name)
        prompt = build_llm_prompt(plsql, procedure_name, table_mapping)
        try:
            llm_code = llm_client.complete(prompt)
            result = TranslationResult(
                procedure_name=procedure_name,
                original_plsql=plsql,
                pyspark_code=llm_code,
                method="llm",
                confidence=0.7,  # LLM is better but still needs review
                warnings=["Generated by LLM — review recommended"],
                requires_review=True,
            )
        except Exception:
            logger.exception("LLM translation failed for '%s'", procedure_name)
            result.warnings.append("LLM fallback failed — using rule-based output")

    # Step 3: if still low confidence, mark for manual review
    if result.confidence < 0.5:
        result.method = "manual"
        result.requires_review = True
        result.warnings.append("Manual review required — automatic translation insufficient")

    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _translate_merge(body: str, tmap: dict[str, str]) -> str:
    """Best-effort MERGE INTO → DeltaTable.merge skeleton."""
    # Extract target table
    m = re.search(r"MERGE\s+INTO\s+(\w+(?:\.\w+)?)", body, re.IGNORECASE)
    if not m:
        return body
    target = _map_table(m.group(1), tmap)

    # Extract USING
    m2 = re.search(r"USING\s+(\w+(?:\.\w+)?|\(.+?\))\s+(\w+)\s+ON\s+\((.+?)\)", body, re.IGNORECASE | re.DOTALL)
    if not m2:
        return body

    source = m2.group(1)
    alias = m2.group(2)
    condition = m2.group(3).strip()

    lines = [
        f'target_dt = DeltaTable.forName(spark, "{target}")',
        f'source_df = spark.sql("SELECT * FROM {source}")',
        f"target_dt.alias(\"t\").merge(",
        f"    source_df.alias(\"{alias}\"),",
        f'    condition="{condition}"',
        f")",
    ]

    # Check for WHEN MATCHED
    if re.search(r"WHEN\s+MATCHED\s+THEN\s+UPDATE", body, re.IGNORECASE):
        lines.append('.whenMatchedUpdateAll()')
    if re.search(r"WHEN\s+NOT\s+MATCHED\s+THEN\s+INSERT", body, re.IGNORECASE):
        lines.append('.whenNotMatchedInsertAll()')

    lines.append(".execute()")
    return "\n".join(lines)


def _parse_set_clause(set_clause: str) -> str:
    """Parse SET col1=val1, col2=val2 into dict literal."""
    parts = []
    for assignment in set_clause.split(","):
        kv = assignment.strip().split("=", 1)
        if len(kv) == 2:
            col = kv[0].strip().strip('"')
            val = kv[1].strip()
            parts.append(f'"{col}": "{val}"')
    return ", ".join(parts)


def _translate_loop_body(loop_body: str, tmap: dict[str, str]) -> str:
    """Translate the body of a PL/SQL CURSOR LOOP to Python statements.

    Handles common DML and control-flow inside cursor loops:
      - INSERT / UPDATE / DELETE → spark.sql / DeltaTable ops
      - IF / ELSIF / ELSE → Python conditionals
      - Variable assignments (:= ) → Python assignments
      - DBMS_OUTPUT → logger calls
      - Others → comment with original code

    Returns translated Python lines (un-indented; caller adds indent).
    Falls back to ``pass`` if nothing can be translated.
    """
    result_lines: list[str] = []
    remaining = loop_body.strip()

    # --- Simple statement patterns inside loop body ---
    _stmt_insert = re.compile(
        r"INSERT\s+INTO\s+(\w+(?:\.\w+)?)\s+VALUES\s*\((.+?)\)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    _stmt_update = re.compile(
        r"UPDATE\s+(\w+(?:\.\w+)?)\s+SET\s+(.+?)\s+WHERE\s+(.+?)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    _stmt_delete = re.compile(
        r"DELETE\s+FROM\s+(\w+(?:\.\w+)?)\s+WHERE\s+(.+?)\s*;",
        re.IGNORECASE | re.DOTALL,
    )
    _stmt_assign = re.compile(
        r"(\w+)\s*:=\s*(.+?)\s*;",
    )
    _stmt_dbms = re.compile(
        r"DBMS_OUTPUT\.PUT_LINE\s*\(\s*(.+?)\s*\)\s*;",
        re.IGNORECASE,
    )
    _stmt_if = re.compile(
        r"IF\s+(.+?)\s+THEN\s+(.+?)(?:ELSIF\s+(.+?)\s+THEN\s+(.+?))?(?:ELSE\s+(.+?))?\s*END\s+IF\s*;",
        re.IGNORECASE | re.DOTALL,
    )

    translated_something = False

    # IF / ELSIF / ELSE
    for m in _stmt_if.finditer(remaining):
        cond = m.group(1).strip()
        then_body = m.group(2).strip().rstrip(";").strip()
        result_lines.append(f"if {_plsql_cond_to_python(cond)}:")
        result_lines.append(f"    {_simple_stmt(then_body, tmap)}")
        if m.group(3) and m.group(4):
            result_lines.append(f"elif {_plsql_cond_to_python(m.group(3).strip())}:")
            result_lines.append(f"    {_simple_stmt(m.group(4).strip().rstrip(';').strip(), tmap)}")
        if m.group(5):
            result_lines.append("else:")
            result_lines.append(f"    {_simple_stmt(m.group(5).strip().rstrip(';').strip(), tmap)}")
        translated_something = True
    # Remove matched IF blocks from remaining
    remaining = _stmt_if.sub("", remaining)

    # INSERT INTO ... VALUES
    for m in _stmt_insert.finditer(remaining):
        target = _map_table(m.group(1), tmap)
        values = m.group(2).strip()
        result_lines.append(f'spark.sql(f"INSERT INTO {target} VALUES ({values})")')
        translated_something = True
    remaining = _stmt_insert.sub("", remaining)

    # UPDATE ... SET ... WHERE
    for m in _stmt_update.finditer(remaining):
        target = _map_table(m.group(1), tmap)
        set_clause = m.group(2).strip()
        where_clause = m.group(3).strip()
        result_lines.append(f'delta_t = DeltaTable.forName(spark, "{target}")')
        result_lines.append(f'delta_t.update(condition="{where_clause}", set={{{_parse_set_clause(set_clause)}}})')
        translated_something = True
    remaining = _stmt_update.sub("", remaining)

    # DELETE FROM ... WHERE
    for m in _stmt_delete.finditer(remaining):
        target = _map_table(m.group(1), tmap)
        where_clause = m.group(2).strip()
        result_lines.append(f'delta_t = DeltaTable.forName(spark, "{target}")')
        result_lines.append(f'delta_t.delete(condition="{where_clause}")')
        translated_something = True
    remaining = _stmt_delete.sub("", remaining)

    # DBMS_OUTPUT.PUT_LINE
    for m in _stmt_dbms.finditer(remaining):
        result_lines.append(f"logger.info({m.group(1)})")
        translated_something = True
    remaining = _stmt_dbms.sub("", remaining)

    # Variable assignments
    for m in _stmt_assign.finditer(remaining):
        var_name = m.group(1).strip()
        var_val = m.group(2).strip()
        result_lines.append(f"{var_name} = {var_val}")
        translated_something = True
    remaining = _stmt_assign.sub("", remaining)

    # If nothing left after stripping whitespace / keywords, we're done
    leftover = re.sub(r"\b(BEGIN|END|NULL)\s*;?", "", remaining, flags=re.IGNORECASE).strip()
    if leftover and len(leftover) > 5:
        result_lines.append(f"# TODO: Manual review needed for: {leftover[:120]}")

    if not translated_something:
        return "pass"
    return "\n".join(result_lines)


def _plsql_cond_to_python(cond: str) -> str:
    """Convert a PL/SQL boolean condition to Python-esque syntax."""
    result = cond
    result = re.sub(r"\bAND\b", "and", result, flags=re.IGNORECASE)
    result = re.sub(r"\bOR\b", "or", result, flags=re.IGNORECASE)
    result = re.sub(r"\bNOT\b", "not", result, flags=re.IGNORECASE)
    result = re.sub(r"\bIS\s+NULL\b", "is None", result, flags=re.IGNORECASE)
    result = re.sub(r"\bIS\s+NOT\s+NULL\b", "is not None", result, flags=re.IGNORECASE)
    result = re.sub(r"(\w+)\.(\w+)", r"row['\2']", result)  # rec.col → row['col']
    return result


def _simple_stmt(stmt: str, tmap: dict[str, str]) -> str:
    """Translate a single simple PL/SQL statement for use inside an if-block."""
    assign_m = re.match(r"(\w+)\s*:=\s*(.+)", stmt)
    if assign_m:
        return f"{assign_m.group(1)} = {assign_m.group(2)}"
    dbms_m = re.match(r"DBMS_OUTPUT\.PUT_LINE\s*\(\s*(.+?)\s*\)", stmt, re.IGNORECASE)
    if dbms_m:
        return f"logger.info({dbms_m.group(1)})"
    insert_m = re.match(r"INSERT\s+INTO\s+(\w+(?:\.\w+)?)", stmt, re.IGNORECASE)
    if insert_m:
        target = _map_table(insert_m.group(1), tmap)
        return f'spark.sql("INSERT INTO {target} ...")'
    return f"# {stmt}"


def _map_table(oracle_table: str, tmap: dict[str, str]) -> str:
    """Map Oracle table name to Fabric table name."""
    return tmap.get(oracle_table, tmap.get(oracle_table.upper(), oracle_table.lower()))


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w]", "_", name.strip()).lower()
