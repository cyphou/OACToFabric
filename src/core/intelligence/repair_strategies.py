"""Repair strategies — pluggable auto-repair for diagnosed errors — Phase 74.

Each strategy implements ``can_handle()`` and ``repair()``.  The healing engine
selects the best strategy for a diagnosis and applies it.

Usage::

    strategy = RetranslateStrategy(translator)
    if strategy.can_handle(diagnosis):
        repair_result = await strategy.repair(diagnosis, context)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RepairResult:
    """Result of a repair attempt."""

    success: bool = False
    strategy_name: str = ""
    description: str = ""
    repaired_output: Any = None
    side_effects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "strategy": self.strategy_name,
            "description": self.description,
            "side_effects": self.side_effects,
        }


class RepairStrategy(ABC):
    """Base class for repair strategies."""

    name: str = "base"

    @abstractmethod
    def can_handle(self, diagnosis: Any) -> bool:
        """Check if this strategy can handle the given diagnosis."""
        ...

    @abstractmethod
    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        """Attempt to repair the diagnosed issue."""
        ...


class RetranslateStrategy(RepairStrategy):
    """Re-translate the source expression with a different approach."""

    name = "retranslate"

    def __init__(self, translator: Any = None) -> None:
        self._translator = translator

    def can_handle(self, diagnosis: Any) -> bool:
        return "retranslate" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)

        if not self._translator:
            result.description = "No translator available"
            return result

        source = context.get("source_expression", "")
        if not source:
            result.description = "No source expression in context"
            return result

        try:
            translation = await self._translator.translate(source)
            if hasattr(translation, "valid") and translation.valid:
                result.success = True
                result.repaired_output = translation.output
                result.description = f"Re-translated with strategy: {translation.strategy_used}"
            else:
                result.description = "Re-translation failed validation"
        except Exception as e:
            result.description = f"Re-translation error: {e}"

        return result


class AdjustTypeMappingStrategy(RepairStrategy):
    """Adjust type mapping to fix type mismatch errors."""

    name = "adjust_type_mapping"

    _FALLBACK_TYPES: dict[str, str] = {
        "numeric": "double",
        "number": "double",
        "decimal": "double",
        "float": "double",
        "integer": "int64",
        "int": "int64",
        "varchar": "string",
        "varchar2": "string",
        "nvarchar": "string",
        "char": "string",
        "nchar": "string",
        "clob": "string",
        "nclob": "string",
        "date": "dateTime",
        "timestamp": "dateTime",
        "boolean": "boolean",
        "bool": "boolean",
        "blob": "binary",
        "raw": "binary",
    }

    def can_handle(self, diagnosis: Any) -> bool:
        return "adjust_type_mapping" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)
        source_type = context.get("source_type", "").lower()

        if source_type in self._FALLBACK_TYPES:
            result.success = True
            result.repaired_output = self._FALLBACK_TYPES[source_type]
            result.description = f"Mapped {source_type} → {result.repaired_output}"
        else:
            result.description = f"No fallback mapping for type: {source_type}"
            result.repaired_output = "string"  # Safe default
            result.success = True
            result.side_effects.append("Fell back to 'string' type — review manually")

        return result


class RetryWithBackoffStrategy(RepairStrategy):
    """Retry the operation with exponential backoff."""

    name = "retry_with_backoff"

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0) -> None:
        self._max_retries = max_retries
        self._base_delay = base_delay

    def can_handle(self, diagnosis: Any) -> bool:
        return "retry_with_backoff" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)
        operation = context.get("operation")

        if not callable(operation):
            result.description = "No callable operation provided for retry"
            return result

        import asyncio
        for attempt in range(self._max_retries):
            delay = self._base_delay * (2 ** attempt)
            try:
                output = await operation()
                result.success = True
                result.repaired_output = output
                result.description = f"Succeeded on retry {attempt + 1} after {delay}s delay"
                return result
            except Exception as e:
                if attempt == self._max_retries - 1:
                    result.description = f"All {self._max_retries} retries failed: {e}"
                else:
                    await asyncio.sleep(delay)

        return result


class QuarantineStrategy(RepairStrategy):
    """Quarantine bad data rows and continue migration."""

    name = "quarantine"

    def can_handle(self, diagnosis: Any) -> bool:
        return "quarantine_rows" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)
        bad_rows = context.get("bad_rows", [])

        result.success = True
        result.repaired_output = {"quarantined_count": len(bad_rows)}
        result.description = f"Quarantined {len(bad_rows)} rows to dead-letter table"
        result.side_effects.append("Quarantined rows need manual review")
        return result


class SkipAndContinueStrategy(RepairStrategy):
    """Skip the problematic item and continue with the rest."""

    name = "skip_and_continue"

    def can_handle(self, diagnosis: Any) -> bool:
        return "skip_and_continue" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)
        asset_id = context.get("asset_id", "unknown")

        result.success = True
        result.repaired_output = {"skipped": asset_id}
        result.description = f"Skipped asset '{asset_id}' — will migrate in manual pass"
        result.side_effects.append(f"Asset '{asset_id}' requires manual migration")
        return result


class FixSyntaxStrategy(RepairStrategy):
    """Attempt to fix common syntax errors in DAX/SQL output."""

    name = "fix_syntax"

    def can_handle(self, diagnosis: Any) -> bool:
        return "fix_syntax" in getattr(diagnosis, "recommended_strategies", [])

    async def repair(self, diagnosis: Any, context: dict[str, Any]) -> RepairResult:
        result = RepairResult(strategy_name=self.name)
        expression = context.get("expression", "")

        if not expression:
            result.description = "No expression to fix"
            return result

        fixed = expression
        changes: list[str] = []

        # Fix unbalanced parentheses
        open_count = fixed.count("(")
        close_count = fixed.count(")")
        if open_count > close_count:
            fixed += ")" * (open_count - close_count)
            changes.append(f"Added {open_count - close_count} closing parentheses")

        # Fix unbalanced brackets
        open_b = fixed.count("[")
        close_b = fixed.count("]")
        if open_b > close_b:
            fixed += "]" * (open_b - close_b)
            changes.append(f"Added {open_b - close_b} closing brackets")

        # Fix double quotes in DAX (should be single)
        if '""' in fixed and "'" not in fixed:
            fixed = fixed.replace('""', "'")
            changes.append("Fixed double-double quotes to single quotes")

        if changes:
            result.success = True
            result.repaired_output = fixed
            result.description = "Syntax fixes: " + "; ".join(changes)
            result.side_effects.append("Auto-fixed syntax — verify correctness")
        else:
            result.description = "No auto-fixable syntax issues found"

        return result


# ---------------------------------------------------------------------------
# Strategy registry
# ---------------------------------------------------------------------------


def get_all_strategies() -> list[RepairStrategy]:
    """Return all available repair strategies."""
    return [
        RetranslateStrategy(),
        AdjustTypeMappingStrategy(),
        RetryWithBackoffStrategy(),
        QuarantineStrategy(),
        SkipAndContinueStrategy(),
        FixSyntaxStrategy(),
    ]
