"""Error diagnostician — classify migration failures — Phase 74.

Analyses error context (traceback, input, agent state) to classify the root
cause into one of 15+ diagnostic categories and recommend repair strategies.

Usage::

    diag = ErrorDiagnostician()
    diagnosis = diag.diagnose(error, context)
    print(diagnosis.category)    # "type_mismatch"
    print(diagnosis.strategies)  # ["adjust_type_mapping", "retry_with_fallback"]
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    TYPE_MISMATCH = "type_mismatch"
    MISSING_DEPENDENCY = "missing_dependency"
    SYNTAX_ERROR = "syntax_error"
    PERMISSION_ERROR = "permission_error"
    API_RATE_LIMIT = "api_rate_limit"
    API_TIMEOUT = "api_timeout"
    DATA_QUALITY = "data_quality"
    SCHEMA_DRIFT = "schema_drift"
    TRANSLATION_FAILURE = "translation_failure"
    DEPLOYMENT_ERROR = "deployment_error"
    NETWORK_ERROR = "network_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    CONCURRENCY_ERROR = "concurrency_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN = "unknown"


@dataclass
class Diagnosis:
    """Result of error diagnosis."""

    category: ErrorCategory
    confidence: float = 0.0
    description: str = ""
    root_cause: str = ""
    recommended_strategies: list[str] = field(default_factory=list)
    affected_assets: list[str] = field(default_factory=list)
    severity: str = "medium"  # low / medium / high / critical
    can_auto_repair: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "confidence": self.confidence,
            "description": self.description,
            "root_cause": self.root_cause,
            "strategies": self.recommended_strategies,
            "severity": self.severity,
            "auto_repair": self.can_auto_repair,
        }


# ---------------------------------------------------------------------------
# Pattern matchers
# ---------------------------------------------------------------------------

_ERROR_PATTERNS: list[tuple[re.Pattern[str], ErrorCategory, str, list[str]]] = [
    # Type mismatches
    (re.compile(r"type.*mismatch|cannot.*convert.*type|data.*type.*incompatible", re.I),
     ErrorCategory.TYPE_MISMATCH,
     "Data type incompatibility between source and target",
     ["adjust_type_mapping", "coerce_type"]),

    # Missing dependencies
    (re.compile(r"not found|missing.*table|missing.*column|undefined.*reference|no.*such", re.I),
     ErrorCategory.MISSING_DEPENDENCY,
     "Required dependency (table, column, function) not found",
     ["create_missing_dependency", "skip_and_continue"]),

    # Syntax errors
    (re.compile(r"syntax.*error|unexpected.*token|parse.*error|malformed", re.I),
     ErrorCategory.SYNTAX_ERROR,
     "Invalid syntax in generated artifact",
     ["retranslate", "fix_syntax"]),

    # Permission errors
    (re.compile(r"permission.*denied|403|unauthorized|forbidden|access.*denied", re.I),
     ErrorCategory.PERMISSION_ERROR,
     "Insufficient permissions for the operation",
     ["refresh_credentials", "escalate_to_admin"]),

    # Rate limits
    (re.compile(r"429|rate.*limit|too.*many.*requests|throttl", re.I),
     ErrorCategory.API_RATE_LIMIT,
     "API rate limit exceeded",
     ["retry_with_backoff", "reduce_concurrency"]),

    # Timeouts
    (re.compile(r"timeout|timed.*out|deadline.*exceeded", re.I),
     ErrorCategory.API_TIMEOUT,
     "Operation timed out",
     ["retry_with_backoff", "increase_timeout"]),

    # Data quality
    (re.compile(r"null.*value|constraint.*violation|duplicate.*key|data.*truncat", re.I),
     ErrorCategory.DATA_QUALITY,
     "Data quality issue in source or target",
     ["quarantine_rows", "skip_and_continue"]),

    # Schema drift
    (re.compile(r"schema.*changed|column.*removed|table.*altered|incompatible.*schema", re.I),
     ErrorCategory.SCHEMA_DRIFT,
     "Source schema has changed since discovery",
     ["rediscover", "adapt_schema"]),

    # Translation failures
    (re.compile(r"translation.*failed|cannot.*translate|unsupported.*expression", re.I),
     ErrorCategory.TRANSLATION_FAILURE,
     "Expression or construct could not be translated",
     ["retranslate_with_llm", "escalate_to_human"]),

    # Deployment
    (re.compile(r"deploy.*failed|publish.*error|upload.*failed|workspace.*error", re.I),
     ErrorCategory.DEPLOYMENT_ERROR,
     "Deployment to Fabric/Power BI failed",
     ["retry_deployment", "validate_and_fix"]),

    # Network
    (re.compile(r"connection.*refused|network.*unreachable|dns.*error|connection.*reset", re.I),
     ErrorCategory.NETWORK_ERROR,
     "Network connectivity issue",
     ["retry_with_backoff", "check_network"]),

    # Resource exhaustion
    (re.compile(r"out.*of.*memory|disk.*full|capacity.*exceeded|quota.*exceeded", re.I),
     ErrorCategory.RESOURCE_EXHAUSTION,
     "System resource limits exceeded",
     ["reduce_batch_size", "increase_capacity"]),

    # Concurrency
    (re.compile(r"deadlock|lock.*timeout|concurrent.*modification|conflict.*detected", re.I),
     ErrorCategory.CONCURRENCY_ERROR,
     "Concurrency or locking conflict",
     ["retry_with_jitter", "serialize_operations"]),

    # Configuration
    (re.compile(r"config.*error|invalid.*config|missing.*setting|environment.*variable", re.I),
     ErrorCategory.CONFIGURATION_ERROR,
     "Configuration or environment issue",
     ["fix_configuration", "escalate_to_admin"]),
]

# Strategies that can be auto-repaired
_AUTO_REPAIRABLE = {
    ErrorCategory.TYPE_MISMATCH,
    ErrorCategory.SYNTAX_ERROR,
    ErrorCategory.API_RATE_LIMIT,
    ErrorCategory.API_TIMEOUT,
    ErrorCategory.DATA_QUALITY,
    ErrorCategory.TRANSLATION_FAILURE,
    ErrorCategory.CONCURRENCY_ERROR,
}


class ErrorDiagnostician:
    """Classify migration errors and recommend repair strategies.

    Parameters
    ----------
    agent_memory
        Optional memory for recalling prior error resolutions.
    reasoning_loop
        Optional LLM for diagnosing novel errors.
    """

    def __init__(
        self,
        agent_memory: Any = None,
        reasoning_loop: Any = None,
    ) -> None:
        self._memory = agent_memory
        self._reasoning = reasoning_loop
        self._known_errors: dict[str, Diagnosis] = {}

    def diagnose(
        self,
        error: Exception | str,
        context: dict[str, Any] | None = None,
    ) -> Diagnosis:
        """Diagnose an error using pattern matching.

        Parameters
        ----------
        error
            The exception or error message.
        context
            Additional context (agent_id, task, input_data, traceback).
        """
        error_str = str(error)
        ctx = context or {}

        # Check known errors first
        known = self._known_errors.get(error_str[:200])
        if known:
            return known

        # Pattern match
        for pattern, category, description, strategies in _ERROR_PATTERNS:
            if pattern.search(error_str):
                diagnosis = Diagnosis(
                    category=category,
                    confidence=0.85,
                    description=description,
                    root_cause=error_str[:500],
                    recommended_strategies=strategies,
                    affected_assets=ctx.get("affected_assets", []),
                    severity=self._severity_for(category),
                    can_auto_repair=category in _AUTO_REPAIRABLE,
                )
                self._known_errors[error_str[:200]] = diagnosis
                return diagnosis

        # No pattern matched
        diagnosis = Diagnosis(
            category=ErrorCategory.UNKNOWN,
            confidence=0.3,
            description="Unrecognized error pattern",
            root_cause=error_str[:500],
            recommended_strategies=["escalate_to_human"],
            affected_assets=ctx.get("affected_assets", []),
            severity="high",
            can_auto_repair=False,
        )
        return diagnosis

    async def diagnose_with_llm(
        self,
        error: Exception | str,
        context: dict[str, Any] | None = None,
    ) -> Diagnosis:
        """Diagnose with optional LLM for novel errors."""
        diagnosis = self.diagnose(error, context)

        if diagnosis.category == ErrorCategory.UNKNOWN and self._reasoning:
            try:
                result = await self._reasoning.run(
                    task="diagnose_error",
                    source=str(error)[:1000],
                    context=context,
                )
                if result.success and result.output:
                    diagnosis.description = str(result.output)[:500]
                    diagnosis.confidence = result.confidence
            except Exception:
                pass

        return diagnosis

    @staticmethod
    def _severity_for(category: ErrorCategory) -> str:
        critical = {ErrorCategory.PERMISSION_ERROR, ErrorCategory.RESOURCE_EXHAUSTION}
        high = {ErrorCategory.SCHEMA_DRIFT, ErrorCategory.DEPLOYMENT_ERROR, ErrorCategory.NETWORK_ERROR}
        low = {ErrorCategory.API_RATE_LIMIT, ErrorCategory.CONCURRENCY_ERROR}
        if category in critical:
            return "critical"
        if category in high:
            return "high"
        if category in low:
            return "low"
        return "medium"
