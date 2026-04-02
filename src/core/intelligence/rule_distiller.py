"""Rule distiller — extract deterministic rules from LLM translations — Phase 72.

When the LLM successfully translates an expression that no rule covers, the
distiller analyses the source→output pair and tries to extract a reusable
pattern that can be added to the rule catalog — growing coverage automatically.

Distilled rules are stored in the agent memory and periodically reviewed by
humans before being promoted to the production rule set.

Usage::

    distiller = RuleDistiller()
    candidate = distiller.distil(source="@SUM(Revenue)", output="SUM('Fact'[Revenue])")
    if candidate:
        print(candidate.pattern)  # r"@SUM\\((\\w+)\\)"
        print(candidate.template) # "SUM('Fact'[{1}])"
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DistilledRule:
    """A candidate rule extracted from a successful LLM translation."""

    source_pattern: str  # Regex matching the source expression pattern
    output_template: str  # Output template with {1}, {2} placeholders
    source_example: str  # The original source expression
    output_example: str  # The original LLM output
    confidence: float = 0.0
    description: str = ""
    validated: bool = False  # True after human review
    test_cases: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.source_pattern,
            "template": self.output_template,
            "example_source": self.source_example,
            "example_output": self.output_example,
            "confidence": self.confidence,
            "validated": self.validated,
            "test_count": len(self.test_cases),
        }


# ---------------------------------------------------------------------------
# Pattern extraction heuristics
# ---------------------------------------------------------------------------


def _extract_function_pattern(source: str) -> tuple[str, list[str]] | None:
    """Try to extract a function-call pattern from the source.

    Returns (function_name, args) if a simple f(a, b, ...) pattern is found.
    """
    match = re.match(r"^(@?\w+)\s*\((.+)\)$", source.strip(), re.DOTALL)
    if not match:
        return None
    func = match.group(1)
    raw_args = match.group(2)

    # Split by comma at top level (simple heuristic)
    args: list[str] = []
    depth = 0
    current = ""
    for ch in raw_args:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(current.strip())
            current = ""
            continue
        current += ch
    if current.strip():
        args.append(current.strip())

    return func, args


def _extract_output_template(output: str, source_args: list[str]) -> str:
    """Replace source argument values in the output with placeholders."""
    template = output
    for i, arg in enumerate(source_args, 1):
        # Escape special regex chars in arg before replacement
        escaped = re.escape(arg)
        template = re.sub(escaped, f"{{{i}}}", template, count=1)
    return template


# ---------------------------------------------------------------------------
# Rule distiller
# ---------------------------------------------------------------------------


class RuleDistiller:
    """Extract deterministic rules from successful LLM translations.

    Parameters
    ----------
    agent_memory
        Optional agent memory for storing distilled rules.
    min_confidence
        Minimum translation confidence to attempt distillation.
    """

    def __init__(
        self,
        agent_memory: Any = None,
        min_confidence: float = 0.8,
    ) -> None:
        self._memory = agent_memory
        self._min_confidence = min_confidence
        self._candidates: list[DistilledRule] = []

    @property
    def candidate_count(self) -> int:
        return len(self._candidates)

    def distil(
        self,
        source: str,
        output: str,
        confidence: float = 0.9,
    ) -> DistilledRule | None:
        """Attempt to distil a reusable rule from a source→output pair.

        Returns a ``DistilledRule`` if a pattern can be extracted, else *None*.
        """
        if confidence < self._min_confidence:
            return None

        if not source.strip() or not output.strip():
            return None

        # Try function pattern extraction
        parsed = _extract_function_pattern(source)
        if not parsed:
            return None

        func_name, args = parsed
        if not args:
            # Simple zero-arg function — direct mapping
            rule = DistilledRule(
                source_pattern=re.escape(source.strip()),
                output_template=output.strip(),
                source_example=source,
                output_example=output,
                confidence=confidence,
                description=f"Direct mapping: {func_name}() → {output.strip()[:50]}",
                test_cases=[{"source": source, "expected": output}],
            )
            self._candidates.append(rule)
            self._persist(rule)
            return rule

        # Build pattern with capture groups
        arg_patterns = [r"(.+?)" if len(args) > 1 else r"(.+)"]
        if len(args) > 1:
            arg_patterns = [r"(.+?)"] * (len(args) - 1) + [r"(.+)"]

        pattern = re.escape(func_name) + r"\s*\(" + r",\s*".join(arg_patterns) + r"\)"

        # Build output template
        template = _extract_output_template(output, args)

        rule = DistilledRule(
            source_pattern=pattern,
            output_template=template,
            source_example=source,
            output_example=output,
            confidence=confidence,
            description=f"Pattern: {func_name}({', '.join(f'arg{i+1}' for i in range(len(args)))}) → {template[:50]}",
            test_cases=[{"source": source, "expected": output}],
        )

        self._candidates.append(rule)
        self._persist(rule)

        logger.info("Distilled rule: %s → %s (confidence=%.2f)", pattern, template, confidence)
        return rule

    def validate_rule(self, rule: DistilledRule, test_input: str, expected_output: str) -> bool:
        """Validate a distilled rule against a test case."""
        match = re.match(rule.source_pattern, test_input.strip(), re.DOTALL)
        if not match:
            return False

        # Apply template
        result = rule.output_template
        for i, group in enumerate(match.groups(), 1):
            result = result.replace(f"{{{i}}}", group)

        if result.strip() == expected_output.strip():
            rule.test_cases.append({"source": test_input, "expected": expected_output})
            return True
        return False

    def get_candidates(self, validated_only: bool = False) -> list[DistilledRule]:
        """Return distilled rule candidates."""
        if validated_only:
            return [r for r in self._candidates if r.validated]
        return list(self._candidates)

    def _persist(self, rule: DistilledRule) -> None:
        """Persist rule to agent memory."""
        if self._memory:
            self._memory.store(
                "distilled_rule",
                key=rule.source_pattern[:100],
                value=rule.to_dict(),
                confidence=rule.confidence,
            )
