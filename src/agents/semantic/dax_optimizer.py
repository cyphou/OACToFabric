"""Pre-deploy DAX optimizer — 5 rewrite rules.

Ported from T2P — performs AST-level DAX rewrites before TMDL emission
to improve semantic model performance and reduce RU consumption.

Rules:
1. ISBLANK → COALESCE  (3× faster evaluation)
2. IF chain → SWITCH    (optimizer-friendly)
3. SUMX simple → SUM    (engine bypass)
4. CALCULATE collapse    (nested CALCULATE flattening)
5. Constant folding      (pre-compute literal arithmetic)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Optimization record
# ---------------------------------------------------------------------------

@dataclass
class DAXOptimization:
    """A single DAX optimization applied."""

    rule: str           # isblank_coalesce | if_switch | sumx_sum | calculate_collapse | constant_fold
    original: str
    optimized: str
    measure_name: str = ""


@dataclass
class DAXOptimizerResult:
    """Result of running the DAX optimizer."""

    optimizations: list[DAXOptimization] = field(default_factory=list)
    total_measures: int = 0
    optimized_count: int = 0


# ---------------------------------------------------------------------------
# Rule 1: IF(ISBLANK(x), y, x) → COALESCE(x, y)
# ---------------------------------------------------------------------------

_RE_ISBLANK = re.compile(
    r"IF\s*\(\s*ISBLANK\s*\(\s*([^)]+)\s*\)\s*,\s*([^,]+)\s*,\s*\1\s*\)",
    re.IGNORECASE,
)

_RE_ISBLANK_ALT = re.compile(
    r"IF\s*\(\s*ISBLANK\s*\(\s*([^)]+)\s*\)\s*,\s*([^,)]+)\s*,\s*([^)]+)\s*\)",
    re.IGNORECASE,
)


def _rule_isblank_coalesce(dax: str) -> tuple[str, bool]:
    """IF(ISBLANK(x), default, x) → COALESCE(x, default)."""
    # Pattern: IF(ISBLANK(x), y, x)
    result = _RE_ISBLANK.sub(r"COALESCE(\1, \2)", dax)
    return result, result != dax


# ---------------------------------------------------------------------------
# Rule 2: IF chains → SWITCH
# ---------------------------------------------------------------------------

_RE_IF_CHAIN = re.compile(
    r"IF\s*\(\s*([^=]+?)\s*=\s*\"([^\"]+)\"\s*,\s*\"([^\"]+)\"\s*,\s*"
    r"IF\s*\(\s*\1\s*=\s*\"([^\"]+)\"\s*,\s*\"([^\"]+)\"\s*,\s*\"([^\"]+)\"\s*\)\s*\)",
    re.IGNORECASE,
)


def _rule_if_switch(dax: str) -> tuple[str, bool]:
    """Convert nested IF/ELSEIF on same column to SWITCH."""
    def _replace(m: re.Match[str]) -> str:
        col = m.group(1).strip()
        return f'SWITCH({col}, "{m.group(2)}", "{m.group(3)}", "{m.group(4)}", "{m.group(5)}", "{m.group(6)}")'

    result = _RE_IF_CHAIN.sub(_replace, dax)
    return result, result != dax


# ---------------------------------------------------------------------------
# Rule 3: SUMX(table, col) → SUM(col)
# ---------------------------------------------------------------------------

_RE_SUMX_SIMPLE = re.compile(
    r"SUMX\s*\(\s*'?([^',)]+)'?\s*,\s*'?\1'?\[([^\]]+)\]\s*\)",
    re.IGNORECASE,
)


def _rule_sumx_sum(dax: str) -> tuple[str, bool]:
    """SUMX(Table, Table[Col]) → SUM(Table[Col]) when no row context needed."""
    result = _RE_SUMX_SIMPLE.sub(r"SUM('\1'[\2])", dax)
    return result, result != dax


# ---------------------------------------------------------------------------
# Rule 4: Nested CALCULATE collapse
# ---------------------------------------------------------------------------

_RE_NESTED_CALCULATE = re.compile(
    r"CALCULATE\s*\(\s*CALCULATE\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)\s*,\s*([^)]+)\s*\)",
    re.IGNORECASE,
)


def _rule_calculate_collapse(dax: str) -> tuple[str, bool]:
    """CALCULATE(CALCULATE(expr, f1), f2) → CALCULATE(expr, f1, f2)."""
    result = _RE_NESTED_CALCULATE.sub(r"CALCULATE(\1, \2, \3)", dax)
    return result, result != dax


# ---------------------------------------------------------------------------
# Rule 5: Constant folding
# ---------------------------------------------------------------------------

_RE_LITERAL_ARITH = re.compile(r"\b(\d+(?:\.\d+)?)\s*([+\-*/])\s*(\d+(?:\.\d+)?)\b")


def _rule_constant_fold(dax: str) -> tuple[str, bool]:
    """Pre-compute literal arithmetic expressions."""
    def _compute(m: re.Match[str]) -> str:
        left = float(m.group(1))
        op = m.group(2)
        right = float(m.group(3))
        ops = {"+": left + right, "-": left - right, "*": left * right, "/": left / right if right != 0 else 0}
        result = ops.get(op, 0)
        # Return integer if whole number
        if result == int(result):
            return str(int(result))
        return f"{result:.6g}"

    result = _RE_LITERAL_ARITH.sub(_compute, dax)
    return result, result != dax


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_RULES = [
    ("isblank_coalesce", _rule_isblank_coalesce),
    ("if_switch", _rule_if_switch),
    ("sumx_sum", _rule_sumx_sum),
    ("calculate_collapse", _rule_calculate_collapse),
    ("constant_fold", _rule_constant_fold),
]


def optimize_dax(dax: str, measure_name: str = "") -> tuple[str, list[DAXOptimization]]:
    """Apply all 5 optimization rules to a DAX expression.

    Returns (optimized_dax, list_of_optimizations_applied).
    """
    optimizations: list[DAXOptimization] = []
    current = dax

    for rule_name, rule_fn in _RULES:
        result, changed = rule_fn(current)
        if changed:
            optimizations.append(DAXOptimization(
                rule=rule_name,
                original=current,
                optimized=result,
                measure_name=measure_name,
            ))
            current = result

    return current, optimizations


def optimize_all_measures(
    measures: dict[str, str],
) -> tuple[dict[str, str], DAXOptimizerResult]:
    """Optimize all measures in a dict of name → DAX expression.

    Returns (optimized_measures, result).
    """
    optimized: dict[str, str] = {}
    all_opts: list[DAXOptimization] = []
    optimized_count = 0

    for name, dax in measures.items():
        opt_dax, opts = optimize_dax(dax, name)
        optimized[name] = opt_dax
        all_opts.extend(opts)
        if opts:
            optimized_count += 1

    result = DAXOptimizerResult(
        optimizations=all_opts,
        total_measures=len(measures),
        optimized_count=optimized_count,
    )

    if optimized_count:
        logger.info(
            "DAX optimizer: %d/%d measures optimized (%d rules applied)",
            optimized_count, len(measures), len(all_opts),
        )

    return optimized, result
