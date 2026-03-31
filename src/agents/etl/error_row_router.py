"""Error Row Router — route failed rows to quarantine tables.

Generates PySpark and pipeline configuration for capturing rows that
fail data quality checks or transformation errors during ETL, routing
them to dedicated error/quarantine Delta tables for later review.

Handles:
  - Schema validation failures (type mismatches, null violations)
  - Transformation errors (division by zero, parse failures)
  - Business rule violations (range checks, referential integrity)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error routing types
# ---------------------------------------------------------------------------


@dataclass
class ErrorRule:
    """A data quality rule that routes failures to quarantine."""

    rule_name: str
    rule_type: str          # schema, transform, business
    column: str = ""
    condition: str = ""     # PySpark filter expression
    severity: str = "error"  # error, warning, info
    description: str = ""


@dataclass
class QuarantineTableDef:
    """Definition of a quarantine table for error rows."""

    table_name: str
    source_table: str
    error_columns: list[str] = field(default_factory=lambda: [
        "error_rule",
        "error_message",
        "error_timestamp",
        "source_row_id",
    ])

    def to_ddl(self) -> str:
        """Generate Fabric Lakehouse DDL for the quarantine table."""
        lines = [f"CREATE TABLE IF NOT EXISTS {self.table_name} ("]
        lines.append(f"    _source_table STRING DEFAULT '{self.source_table}',")
        for col in self.error_columns:
            lines.append(f"    {col} STRING,")
        lines.append("    _raw_data STRING,")
        lines.append("    _ingested_at TIMESTAMP DEFAULT current_timestamp()")
        lines.append(") USING DELTA")
        return "\n".join(lines)


@dataclass
class ErrorRoutingConfig:
    """Complete error routing configuration for a table."""

    source_table: str
    rules: list[ErrorRule] = field(default_factory=list)
    quarantine_table: str = ""
    max_error_pct: float = 5.0      # max % of rows that can error before failing
    continue_on_error: bool = True

    def __post_init__(self) -> None:
        if not self.quarantine_table:
            self.quarantine_table = f"{self.source_table}_quarantine"


@dataclass
class ErrorRoutingResult:
    """Generated error routing artifacts."""

    pyspark_code: str = ""
    quarantine_ddl: str = ""
    pipeline_json: dict[str, Any] = field(default_factory=dict)
    rule_count: int = 0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# PySpark generation
# ---------------------------------------------------------------------------


def _generate_pyspark(config: ErrorRoutingConfig) -> str:
    """Generate PySpark code for error routing."""
    lines: list[str] = [
        f"# Error routing for {config.source_table}",
        f"from pyspark.sql import functions as F",
        f"from datetime import datetime",
        f"",
        f"error_rows = spark.createDataFrame([], schema=df.schema.add('error_rule', 'string').add('error_message', 'string'))",
        f"clean_df = df",
        f"",
    ]

    for rule in config.rules:
        safe_name = rule.rule_name.replace(" ", "_").replace("-", "_")
        if rule.condition:
            lines.extend([
                f"# Rule: {rule.rule_name} ({rule.severity})",
                f"_bad_{safe_name} = clean_df.filter({rule.condition})",
                f"_bad_{safe_name} = _bad_{safe_name}.withColumn('error_rule', F.lit('{rule.rule_name}'))",
                f"_bad_{safe_name} = _bad_{safe_name}.withColumn('error_message', F.lit('{rule.description}'))",
                f"error_rows = error_rows.unionByName(_bad_{safe_name}, allowMissingColumns=True)",
                f"clean_df = clean_df.filter(~({rule.condition}))",
                f"",
            ])
        elif rule.rule_type == "schema" and rule.column:
            lines.extend([
                f"# Rule: {rule.rule_name} — null check on {rule.column}",
                f"_bad_{safe_name} = clean_df.filter(F.col('{rule.column}').isNull())",
                f"_bad_{safe_name} = _bad_{safe_name}.withColumn('error_rule', F.lit('{rule.rule_name}'))",
                f"_bad_{safe_name} = _bad_{safe_name}.withColumn('error_message', F.lit('NULL value in {rule.column}'))",
                f"error_rows = error_rows.unionByName(_bad_{safe_name}, allowMissingColumns=True)",
                f"clean_df = clean_df.filter(F.col('{rule.column}').isNotNull())",
                f"",
            ])

    lines.extend([
        f"# Write quarantine rows",
        f"error_count = error_rows.count()",
        f"total_count = df.count()",
        f"error_pct = (error_count / total_count * 100) if total_count > 0 else 0",
        f"",
        f"if error_count > 0:",
        f"    error_rows = error_rows.withColumn('error_timestamp', F.current_timestamp())",
        f"    error_rows.write.mode('append').format('delta').saveAsTable('{config.quarantine_table}')",
        f"    print(f'Routed {{error_count}} error rows ({{error_pct:.1f}}%) to {config.quarantine_table}')",
        f"",
    ])

    if not config.continue_on_error:
        lines.extend([
            f"if error_pct > {config.max_error_pct}:",
            f"    raise RuntimeError(",
            f"        f'Error rate {{error_pct:.1f}}% exceeds threshold {config.max_error_pct}% for {config.source_table}'",
            f"    )",
            f"",
        ])

    lines.append(f"# clean_df contains only valid rows")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Pipeline JSON generation
# ---------------------------------------------------------------------------


def _generate_pipeline_json(config: ErrorRoutingConfig) -> dict[str, Any]:
    """Generate Fabric pipeline activity for error routing."""
    return {
        "name": f"ErrorRoute_{config.source_table}",
        "type": "TridentNotebook",
        "typeProperties": {
            "notebookId": f"ErrorRouting_{config.source_table}",
            "parameters": {
                "source_table": config.source_table,
                "quarantine_table": config.quarantine_table,
                "max_error_pct": str(config.max_error_pct),
                "continue_on_error": str(config.continue_on_error),
            },
        },
        "policy": {
            "timeout": "0.02:00:00",
            "retry": 1,
            "retryIntervalInSeconds": 60,
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_error_routing(config: ErrorRoutingConfig) -> ErrorRoutingResult:
    """Generate error routing artifacts for a table.

    Parameters
    ----------
    config : ErrorRoutingConfig
        Error routing configuration.

    Returns
    -------
    ErrorRoutingResult
        Generated PySpark code, DDL, and pipeline JSON.
    """
    quarantine = QuarantineTableDef(
        table_name=config.quarantine_table,
        source_table=config.source_table,
    )

    result = ErrorRoutingResult(
        pyspark_code=_generate_pyspark(config),
        quarantine_ddl=quarantine.to_ddl(),
        pipeline_json=_generate_pipeline_json(config),
        rule_count=len(config.rules),
    )

    logger.info(
        "Generated error routing for '%s': %d rules, quarantine='%s'",
        config.source_table,
        len(config.rules),
        config.quarantine_table,
    )
    return result


def generate_default_rules(
    table_name: str,
    not_null_columns: list[str] | None = None,
    numeric_columns: list[str] | None = None,
) -> ErrorRoutingConfig:
    """Generate default error routing rules for a table.

    Parameters
    ----------
    table_name : str
        Source table name.
    not_null_columns : list[str] | None
        Columns that must not be NULL.
    numeric_columns : list[str] | None
        Numeric columns to validate.

    Returns
    -------
    ErrorRoutingConfig
        Configuration with default rules.
    """
    rules: list[ErrorRule] = []

    for col in (not_null_columns or []):
        rules.append(ErrorRule(
            rule_name=f"not_null_{col}",
            rule_type="schema",
            column=col,
            severity="error",
            description=f"Column '{col}' must not be NULL",
        ))

    for col in (numeric_columns or []):
        rules.append(ErrorRule(
            rule_name=f"numeric_valid_{col}",
            rule_type="transform",
            column=col,
            condition=f"F.col('{col}').cast('double').isNull() & F.col('{col}').isNotNull()",
            severity="error",
            description=f"Column '{col}' contains non-numeric values",
        ))

    return ErrorRoutingConfig(
        source_table=table_name,
        rules=rules,
    )
