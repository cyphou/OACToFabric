"""Intelligent translator — multi-strategy LLM-powered translation — Phase 72.

Wraps the existing ``HybridTranslator`` with a cascading fallback strategy:

1. **Rule-based** — deterministic 120+ rules (fast path).
2. **Cache similar** — embedding-based lookup of previously translated patterns.
3. **LLM primary** — Azure OpenAI with domain-specific prompt.
4. **LLM alternate** — different prompt strategy (decompose + translate).
5. **Escalate** — route to human review queue.

After each successful LLM translation, the output is syntax-validated
(DAX, T-SQL, PySpark, M-query) and the result is cached for reuse.

Usage::

    translator = IntelligentTranslator(hybrid_translator, reasoning_loop)
    result = await translator.translate(expression, target_lang="dax")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TranslationStrategy(str, Enum):
    RULE_BASED = "rule_based"
    CACHE_HIT = "cache_hit"
    LLM_PRIMARY = "llm_primary"
    LLM_ALTERNATE = "llm_alternate"
    ESCALATED = "escalated"


class TargetLanguage(str, Enum):
    DAX = "dax"
    TSQL = "tsql"
    PYSPARK = "pyspark"
    MQUERY = "mquery"


@dataclass
class TranslationAttempt:
    """Record of a single translation attempt."""

    strategy: TranslationStrategy
    output: str = ""
    confidence: float = 0.0
    valid: bool = False
    error: str = ""
    tokens_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "output": self.output[:200],
            "confidence": self.confidence,
            "valid": self.valid,
            "error": self.error,
            "tokens_used": self.tokens_used,
        }


@dataclass
class IntelligentTranslationResult:
    """Result of multi-strategy translation."""

    source: str
    target_language: TargetLanguage
    output: str = ""
    confidence: float = 0.0
    strategy_used: TranslationStrategy = TranslationStrategy.ESCALATED
    valid: bool = False
    attempts: list[TranslationAttempt] = field(default_factory=list)
    rule_distilled: bool = False
    error: str = ""

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)

    @property
    def total_tokens(self) -> int:
        return sum(a.tokens_used for a in self.attempts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source[:200],
            "target": self.target_language.value,
            "output": self.output[:200],
            "confidence": self.confidence,
            "strategy": self.strategy_used.value,
            "valid": self.valid,
            "attempts": len(self.attempts),
            "tokens": self.total_tokens,
        }


# ---------------------------------------------------------------------------
# Syntax validators
# ---------------------------------------------------------------------------


def validate_dax_syntax(expression: str) -> tuple[bool, str]:
    """Validate DAX syntax (brackets, parens, keywords)."""
    if not expression or not expression.strip():
        return False, "Empty expression"

    # Balanced parentheses
    depth = 0
    for ch in expression:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False, "Unbalanced parentheses: extra ')'"
    if depth != 0:
        return False, f"Unbalanced parentheses: {depth} unclosed '('"

    # Balanced brackets (DAX column refs)
    in_bracket = False
    for i, ch in enumerate(expression):
        if ch == "[" and not in_bracket:
            in_bracket = True
        elif ch == "]" and in_bracket:
            # Check for escaped ]] (literal bracket in name)
            if i + 1 < len(expression) and expression[i + 1] == "]":
                continue
            in_bracket = False
        elif ch == "]" and not in_bracket:
            # Lone ] outside bracket — check if it's an escape
            if i > 0 and expression[i - 1] == "]":
                continue
            return False, f"Unexpected ']' at position {i}"

    if in_bracket:
        return False, "Unclosed '[' bracket"

    return True, ""


def validate_tsql_syntax(expression: str) -> tuple[bool, str]:
    """Basic T-SQL syntax validation."""
    if not expression or not expression.strip():
        return False, "Empty expression"

    depth = 0
    for ch in expression:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth < 0:
            return False, "Unbalanced parentheses"
    if depth != 0:
        return False, "Unbalanced parentheses"

    return True, ""


def validate_pyspark_syntax(expression: str) -> tuple[bool, str]:
    """Basic PySpark syntax validation via ast."""
    if not expression or not expression.strip():
        return False, "Empty expression"
    try:
        import ast
        ast.parse(expression)
        return True, ""
    except SyntaxError as e:
        return False, f"Python syntax error: {e.msg}"


def validate_mquery_syntax(expression: str) -> tuple[bool, str]:
    """Basic M query bracket/keyword validation."""
    if not expression or not expression.strip():
        return False, "Empty expression"

    # Check balanced brackets and parens
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    for ch in expression:
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in pairs.values():
            if not stack or stack[-1] != ch:
                return False, f"Unbalanced '{ch}'"
            stack.pop()

    if stack:
        return False, f"Unclosed brackets: {''.join(stack)}"

    return True, ""


_VALIDATORS: dict[TargetLanguage, Any] = {
    TargetLanguage.DAX: validate_dax_syntax,
    TargetLanguage.TSQL: validate_tsql_syntax,
    TargetLanguage.PYSPARK: validate_pyspark_syntax,
    TargetLanguage.MQUERY: validate_mquery_syntax,
}


# ---------------------------------------------------------------------------
# Translation cache (embedding-aware)
# ---------------------------------------------------------------------------


class TranslationMemoryCache:
    """In-memory translation cache with exact and similarity matching.

    For similarity matching a simple normalized-token overlap is used.
    When embeddings are available, cosine similarity replaces this.
    """

    def __init__(self) -> None:
        self._exact: dict[str, tuple[str, float]] = {}
        self._tokens: dict[str, tuple[str, str, float]] = {}  # key → (source, output, confidence)

    def get_exact(self, source: str) -> tuple[str, float] | None:
        return self._exact.get(source.strip())

    def get_similar(self, source: str, threshold: float = 0.8) -> tuple[str, float] | None:
        """Find a similar cached translation using token overlap."""
        src_tokens = set(source.lower().split())
        if not src_tokens:
            return None

        best_match: tuple[str, float] | None = None
        best_similarity = 0.0

        for _key, (cached_src, output, conf) in self._tokens.items():
            cached_tokens = set(cached_src.lower().split())
            if not cached_tokens:
                continue
            overlap = len(src_tokens & cached_tokens) / max(len(src_tokens | cached_tokens), 1)
            if overlap >= threshold and overlap > best_similarity:
                best_similarity = overlap
                best_match = (output, conf * overlap)  # Reduce confidence by similarity

        return best_match

    def store(self, source: str, output: str, confidence: float) -> None:
        self._exact[source.strip()] = (output, confidence)
        self._tokens[source.strip()[:200]] = (source.strip(), output, confidence)

    @property
    def size(self) -> int:
        return len(self._exact)


# ---------------------------------------------------------------------------
# Intelligent translator
# ---------------------------------------------------------------------------


class IntelligentTranslator:
    """Multi-strategy translator with LLM fallback and syntax validation.

    Parameters
    ----------
    rule_translator
        Existing rule-based translator (``HybridTranslator`` or similar).
        Must have a ``translate(source)`` method returning an object with
        ``.dax_expression`` and ``.confidence``.
    reasoning_loop
        ``ReasoningLoop`` for LLM-based translation.
    cache
        Translation memory cache (defaults to new in-memory cache).
    confidence_threshold
        Minimum confidence to accept a rule-based translation without LLM.
    max_llm_retries
        Maximum LLM retry attempts per strategy.
    """

    def __init__(
        self,
        rule_translator: Any = None,
        reasoning_loop: Any = None,
        cache: TranslationMemoryCache | None = None,
        confidence_threshold: float = 0.7,
        max_llm_retries: int = 3,
    ) -> None:
        self._rules = rule_translator
        self._reasoning = reasoning_loop
        self._cache = cache or TranslationMemoryCache()
        self._threshold = confidence_threshold
        self._max_retries = max_llm_retries

    async def translate(
        self,
        source: str,
        target_language: TargetLanguage = TargetLanguage.DAX,
        *,
        context: dict[str, Any] | None = None,
    ) -> IntelligentTranslationResult:
        """Translate using cascading strategies.

        Returns the first successful translation, or escalates.
        """
        result = IntelligentTranslationResult(
            source=source,
            target_language=target_language,
        )
        validator = _VALIDATORS.get(target_language)

        # Strategy 1: Rule-based
        attempt = self._try_rules(source, target_language, validator)
        result.attempts.append(attempt)
        if attempt.valid and attempt.confidence >= self._threshold:
            result.output = attempt.output
            result.confidence = attempt.confidence
            result.strategy_used = TranslationStrategy.RULE_BASED
            result.valid = True
            return result

        # Strategy 2: Cache lookup
        attempt = self._try_cache(source, validator)
        result.attempts.append(attempt)
        if attempt.valid and attempt.confidence >= self._threshold:
            result.output = attempt.output
            result.confidence = attempt.confidence
            result.strategy_used = TranslationStrategy.CACHE_HIT
            result.valid = True
            return result

        # Strategy 3: LLM primary
        if self._reasoning:
            attempt = await self._try_llm(
                source, target_language, validator, context, strategy="direct"
            )
            result.attempts.append(attempt)
            if attempt.valid:
                result.output = attempt.output
                result.confidence = attempt.confidence
                result.strategy_used = TranslationStrategy.LLM_PRIMARY
                result.valid = True
                # Cache for future use
                self._cache.store(source, attempt.output, attempt.confidence)
                return result

            # Strategy 4: LLM alternate (decompose)
            attempt = await self._try_llm(
                source, target_language, validator, context, strategy="decompose"
            )
            result.attempts.append(attempt)
            if attempt.valid:
                result.output = attempt.output
                result.confidence = attempt.confidence
                result.strategy_used = TranslationStrategy.LLM_ALTERNATE
                result.valid = True
                self._cache.store(source, attempt.output, attempt.confidence)
                return result

        # Strategy 5: Escalate
        result.strategy_used = TranslationStrategy.ESCALATED
        result.error = "All strategies exhausted — requires human review"

        # Use best partial result if available
        best = max(result.attempts, key=lambda a: a.confidence, default=None)
        if best and best.output:
            result.output = best.output
            result.confidence = best.confidence

        return result

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    def _try_rules(
        self, source: str, target: TargetLanguage, validator: Any,
    ) -> TranslationAttempt:
        """Strategy 1: Rule-based translation."""
        attempt = TranslationAttempt(strategy=TranslationStrategy.RULE_BASED)

        if not self._rules:
            attempt.error = "No rule translator available"
            return attempt

        try:
            rule_result = self._rules.translate(source)
            output = getattr(rule_result, "dax_expression", str(rule_result))
            confidence = getattr(rule_result, "confidence", 0.5)

            attempt.output = output
            attempt.confidence = confidence

            if validator and output:
                valid, err = validator(output)
                attempt.valid = valid
                if not valid:
                    attempt.error = err
            else:
                attempt.valid = bool(output)

        except Exception as e:
            attempt.error = str(e)

        return attempt

    def _try_cache(self, source: str, validator: Any) -> TranslationAttempt:
        """Strategy 2: Cache lookup."""
        attempt = TranslationAttempt(strategy=TranslationStrategy.CACHE_HIT)

        # Try exact match first
        exact = self._cache.get_exact(source)
        if exact:
            output, confidence = exact
            attempt.output = output
            attempt.confidence = confidence
            if validator:
                valid, err = validator(output)
                attempt.valid = valid
                attempt.error = err
            else:
                attempt.valid = True
            return attempt

        # Try similar match
        similar = self._cache.get_similar(source)
        if similar:
            output, confidence = similar
            attempt.output = output
            attempt.confidence = confidence
            if validator:
                valid, err = validator(output)
                attempt.valid = valid
                attempt.error = err
            else:
                attempt.valid = True
            return attempt

        attempt.error = "No cache match"
        return attempt

    async def _try_llm(
        self,
        source: str,
        target: TargetLanguage,
        validator: Any,
        context: dict[str, Any] | None,
        strategy: str = "direct",
    ) -> TranslationAttempt:
        """Strategy 3/4: LLM-based translation."""
        attempt = TranslationAttempt(
            strategy=TranslationStrategy.LLM_PRIMARY
            if strategy == "direct"
            else TranslationStrategy.LLM_ALTERNATE,
        )

        if not self._reasoning:
            attempt.error = "No reasoning loop available"
            return attempt

        task = f"translate_{target.value}"
        if strategy == "decompose":
            task = f"decompose_and_translate_{target.value}"

        for retry in range(self._max_retries):
            try:
                llm_result = await self._reasoning.run(
                    task=task,
                    source=source,
                    context={
                        **(context or {}),
                        "target_language": target.value,
                        "attempt": retry + 1,
                        "prior_error": attempt.error if retry > 0 else "",
                    },
                )
                attempt.tokens_used += getattr(llm_result, "total_tokens", 0)

                if llm_result.success and llm_result.output:
                    output = str(llm_result.output).strip()
                    attempt.output = output
                    attempt.confidence = llm_result.confidence

                    if validator:
                        valid, err = validator(output)
                        if valid:
                            attempt.valid = True
                            return attempt
                        attempt.error = err
                        # Continue retrying with error context
                    else:
                        attempt.valid = True
                        return attempt
                else:
                    attempt.error = llm_result.error or "LLM returned no output"

            except Exception as e:
                attempt.error = str(e)

        return attempt
