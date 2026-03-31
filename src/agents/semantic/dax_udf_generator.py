"""DAX UDF Generator — complex OAC expressions → reusable DAX user-defined functions.

Generates DAX ``DEFINE FUNCTION`` blocks for expressions that are too complex
for a single measure (confidence < 0.7 or used in multiple measures).

Uses DAX UDF features (Preview, March 2026):
  - Typed parameters: Scalar, Table, ColumnRef, MeasureRef, AnyVal
  - JSDoc ``///`` documentation blocks
  - Up to 256 parameters
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class DAXParameter:
    """A parameter for a DAX user-defined function."""

    name: str
    type_hint: str = "Scalar"  # Scalar, Table, ColumnRef, MeasureRef, AnyVal
    description: str = ""


@dataclass
class DAXUserDefinedFunction:
    """A DAX UDF definition."""

    name: str
    parameters: list[DAXParameter] = field(default_factory=list)
    body: str = ""
    return_type: str = "Scalar"
    description: str = ""
    source_expression: str = ""
    warnings: list[str] = field(default_factory=list)

    def to_dax(self) -> str:
        """Emit DAX DEFINE FUNCTION text."""
        lines: list[str] = []

        # JSDoc block
        lines.append(f"/// {self.description}")
        for p in self.parameters:
            lines.append(f"/// @param {p.name} {p.description}")
        lines.append("")

        # Parameter list
        params = ", ".join(
            f"{p.name} AS {p.type_hint}" for p in self.parameters
        )
        lines.append(f"DEFINE FUNCTION {self.name}({params}) =")
        for body_line in self.body.split("\n"):
            lines.append(f"    {body_line}")

        return "\n".join(lines)

    def to_tmdl(self) -> str:
        """Emit TMDL expression for embedding in model."""
        lines: list[str] = []
        lines.append(f"expression {self.name} =")
        for body_line in self.to_dax().split("\n"):
            lines.append(f"\t{body_line}")
        return "\n".join(lines)


@dataclass
class UDFGenerationResult:
    """Result of generating UDFs from complex expressions."""

    udfs: list[DAXUserDefinedFunction] = field(default_factory=list)
    measure_rewrites: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Pattern detection for UDF candidates
# ---------------------------------------------------------------------------

_COMPLEX_PATTERNS = [
    re.compile(r"CALCULATE\s*\(.*CALCULATE\s*\(", re.IGNORECASE | re.DOTALL),
    re.compile(r"SUMX\s*\(.*FILTER\s*\(", re.IGNORECASE | re.DOTALL),
    re.compile(r"VAR\s+\w+.*VAR\s+\w+.*VAR\s+\w+", re.IGNORECASE | re.DOTALL),
    re.compile(r"SWITCH\s*\(.*SWITCH\s*\(", re.IGNORECASE | re.DOTALL),
]


def _is_complex_expression(expression: str) -> bool:
    """Check if a DAX expression is complex enough to warrant a UDF."""
    if len(expression) > 500:
        return True
    return any(p.search(expression) for p in _COMPLEX_PATTERNS)


def _extract_parameters(expression: str, table_name: str) -> list[DAXParameter]:
    """Extract likely parameters from a DAX expression."""
    params: list[DAXParameter] = []
    seen: set[str] = set()

    col_refs = re.findall(r"'([^']+)'\[([^\]]+)\]", expression)
    for tbl, col in col_refs:
        param_name = f"_{col.replace(' ', '_')}"
        if param_name not in seen:
            params.append(DAXParameter(
                name=param_name,
                type_hint="ColumnRef",
                description=f"Column [{col}] from '{tbl}'",
            ))
            seen.add(param_name)

    measure_refs = re.findall(r"\[([A-Z][^\]]*)\]", expression)
    for m in measure_refs:
        param_name = f"_{m.replace(' ', '_')}"
        if param_name not in seen and not any(param_name == p.name for p in params):
            params.append(DAXParameter(
                name=param_name,
                type_hint="MeasureRef",
                description=f"Measure [{m}]",
            ))
            seen.add(param_name)

    return params[:10]  # Limit to reasonable count


# ---------------------------------------------------------------------------
# UDF generation
# ---------------------------------------------------------------------------


def generate_udfs(
    measures: list[dict[str, Any]],
    confidence_threshold: float = 0.7,
    min_reuse_count: int = 2,
) -> UDFGenerationResult:
    """Generate DAX UDFs for complex or low-confidence expressions.

    Parameters
    ----------
    measures : list[dict]
        Each dict has ``name``, ``expression`` (DAX), ``table_name``,
        and optionally ``confidence`` (float 0–1).
    confidence_threshold : float
        Expressions below this confidence get UDF extraction.
    min_reuse_count : int
        Minimum number of similar patterns to justify a UDF.

    Returns
    -------
    UDFGenerationResult
        Generated UDFs and measure rewrite mappings.
    """
    udfs: list[DAXUserDefinedFunction] = []
    rewrites: dict[str, str] = {}
    warnings: list[str] = []

    for measure in measures:
        expr = measure.get("expression", "")
        name = measure.get("name", "")
        table = measure.get("table_name", "Table")
        confidence = measure.get("confidence", 1.0)

        if confidence >= confidence_threshold and not _is_complex_expression(expr):
            continue

        udf_name = f"_UDF_{re.sub(r'[^a-zA-Z0-9]', '_', name)}"
        params = _extract_parameters(expr, table)

        udf = DAXUserDefinedFunction(
            name=udf_name,
            parameters=params,
            body=expr,
            description=f"Auto-extracted from measure [{name}] (confidence: {confidence:.2f})",
            source_expression=expr,
        )

        if confidence < 0.5:
            udf.warnings.append("Very low confidence — manual review recommended")
            warnings.append(f"UDF {udf_name}: confidence {confidence:.2f} — needs manual review")

        udfs.append(udf)

        # Rewrite the measure to call the UDF
        param_args = ", ".join(
            f"'{table}'[{p.name.lstrip('_')}]" if p.type_hint == "ColumnRef"
            else f"[{p.name.lstrip('_')}]"
            for p in params
        )
        rewrites[name] = f"{udf_name}({param_args})"

    logger.info("Generated %d DAX UDFs from complex expressions", len(udfs))
    return UDFGenerationResult(udfs=udfs, measure_rewrites=rewrites, warnings=warnings)
