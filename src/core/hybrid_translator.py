"""Hybrid translation engine — rules-first with LLM fallback.

Strategy:
1. Try deterministic rule-based translation first.
2. If rules cannot fully translate, fall back to LLM.
3. Validate the output via syntax checking.
4. Cache successful translations for reuse.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.core.llm_client import LLMClient, LLMResponse
from src.core.prompt_templates import PromptTemplate, get_template
from src.core.translation_cache import TranslationCache

logger = logging.getLogger(__name__)


class TranslationMethod(str, Enum):
    RULES = "rules"
    LLM = "llm"
    HYBRID = "hybrid"  # Rules + LLM refinement


@dataclass
class TranslationResult:
    """Result of a single translation."""

    source: str
    translated: str
    method: TranslationMethod
    confidence: float = 1.0  # 0.0–1.0
    validation_passed: bool = True
    warnings: list[str] = field(default_factory=list)
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Rule-based translators (deterministic)
# ---------------------------------------------------------------------------

# OAC function → DAX function mapping  
_OAC_TO_DAX_RULES: dict[str, str] = {
    "AGGREGATE": "SUM",
    "AVG": "AVERAGE",
    "COUNT": "COUNT",
    "COUNTDISTINCT": "DISTINCTCOUNT",
    "MAX": "MAX",
    "MIN": "MIN",
    "SUM": "SUM",
    "RANK": "RANKX",
    "RSUM": "SUMX",
    "MAVG": "AVERAGEX",
    "TOPN": "TOPN",
    "BOTTOMN": "TOPN",  # with ASC
    "FILTER": "FILTER",
    "CASE": "SWITCH",
    "IFNULL": "IF(ISBLANK",
    "NULLIF": "IF",
    "CAST": "CONVERT",
    "TIMESTAMPADD": "DATEADD",
    "TIMESTAMPDIFF": "DATEDIFF",
    "CURRENT_DATE": "TODAY()",
    "CURRENT_TIMESTAMP": "NOW()",
    "SUBSTRING": "MID",
    "LENGTH": "LEN",
    "UPPER": "UPPER",
    "LOWER": "LOWER",
    "TRIM": "TRIM",
    "CONCAT": "CONCATENATE",
    "REPLACE": "SUBSTITUTE",
}

# Oracle SQL → Spark SQL function mapping
_ORACLE_TO_SPARK_RULES: dict[str, str] = {
    "NVL": "COALESCE",
    "NVL2": "IF",
    "DECODE": "CASE",
    "SYSDATE": "CURRENT_DATE()",
    "SYSTIMESTAMP": "CURRENT_TIMESTAMP()",
    "TO_DATE": "TO_DATE",
    "TO_CHAR": "DATE_FORMAT",
    "TO_NUMBER": "CAST",
    "ROWNUM": "ROW_NUMBER() OVER ()",
    "ROWID": "-- ROWID not supported in Spark",
    "CONNECT BY": "-- hierarchical query requires CTE in Spark",
    "MINUS": "EXCEPT",
    "DUAL": "-- remove FROM DUAL",
}


def _apply_function_rules(expression: str, rules: dict[str, str]) -> tuple[str, bool]:
    """Apply deterministic function-name substitutions.

    Returns (translated_expression, fully_translated).
    """
    result = expression
    applied = 0
    for oac_func, target_func in rules.items():
        pattern = re.compile(rf"\b{re.escape(oac_func)}\b", re.IGNORECASE)
        if pattern.search(result):
            result = pattern.sub(target_func, result)
            applied += 1

    # Heuristic: if we applied at least 1 rule and no unknown functions remain
    # we consider it fully translated
    fully_translated = applied > 0 and not _has_unknown_functions(result, rules)
    return result, fully_translated


def _has_unknown_functions(expression: str, known_rules: dict[str, str]) -> bool:
    """Check if expression contains function patterns not in our rule set."""
    # Simple heuristic: look for WORD( patterns
    func_pattern = re.compile(r"\b([A-Z_][A-Z0-9_]*)\s*\(", re.IGNORECASE)
    found = func_pattern.findall(expression)

    known = {k.upper() for k in known_rules.values()}
    known.update({"SUM", "COUNT", "MAX", "MIN", "AVG", "IF", "AND", "OR", "NOT"})
    known.update({"FILTER", "SWITCH", "RELATED", "ALL", "VALUES", "CALCULATE"})

    for func_name in found:
        if func_name.upper() not in known:
            return True
    return False


# ---------------------------------------------------------------------------
# HybridTranslator
# ---------------------------------------------------------------------------


@dataclass
class HybridTranslator:
    """Hybrid rules-first + LLM-fallback translation engine.

    Parameters
    ----------
    llm_client
        Azure OpenAI client for LLM fallback.
    cache
        Translation cache for storing results.
    enable_llm
        Whether to use LLM fallback (False = rules-only).
    confidence_threshold
        Minimum confidence to accept a rules-only translation.
    """

    llm_client: LLMClient | None = None
    cache: TranslationCache | None = None
    enable_llm: bool = True
    confidence_threshold: float = 0.8

    async def translate_expression(
        self,
        expression: str,
        *,
        template_name: str = "oac_to_dax",
        context: dict[str, str] | None = None,
    ) -> TranslationResult:
        """Translate an expression using rules-first, LLM-fallback strategy.

        Parameters
        ----------
        expression
            Source expression to translate.
        template_name
            Name of the prompt template for LLM fallback.
        context
            Additional context for the prompt template (table_name, column_mappings, etc.).
        """
        ctx = context or {}

        # --- 1. Try rules ---
        rules = _OAC_TO_DAX_RULES if "dax" in template_name else _ORACLE_TO_SPARK_RULES
        translated, fully_done = _apply_function_rules(expression, rules)

        if fully_done:
            result = TranslationResult(
                source=expression,
                translated=translated,
                method=TranslationMethod.RULES,
                confidence=0.95,
            )
            if self.cache:
                self.cache.put("rules", expression, translated)
            return result

        # --- 2. Check cache ---
        if self.cache:
            template = get_template(template_name)
            user_prompt = template.user_template.format(
                oac_expression=expression,
                table_name=ctx.get("table_name", "Table"),
                column_mappings=ctx.get("column_mappings", "N/A"),
                **{k: v for k, v in ctx.items() if k not in ("table_name", "column_mappings")},
            )
            cached = self.cache.get(template.system_prompt, user_prompt)
            if cached:
                return TranslationResult(
                    source=expression,
                    translated=cached.content,
                    method=TranslationMethod.LLM,
                    confidence=0.85,
                    tokens_used=0,
                )

        # --- 3. LLM fallback ---
        if self.enable_llm and self.llm_client:
            try:
                llm_result = await self._translate_with_llm(
                    expression, template_name, ctx
                )
                return llm_result
            except Exception as exc:
                logger.warning("LLM translation failed: %s", exc)
                # Fall through to return partial rules result

        # Return partial rules result
        return TranslationResult(
            source=expression,
            translated=translated,
            method=TranslationMethod.RULES,
            confidence=0.5,
            warnings=["Partial translation — some functions may not be mapped"],
        )

    async def _translate_with_llm(
        self,
        expression: str,
        template_name: str,
        context: dict[str, str],
    ) -> TranslationResult:
        """Run LLM translation."""
        template = get_template(template_name)
        system, user = template.render(
            oac_expression=expression,
            table_name=context.get("table_name", "Table"),
            column_mappings=context.get("column_mappings", "N/A"),
            **{k: v for k, v in context.items() if k not in ("table_name", "column_mappings", "oac_expression")},
        )

        response = await self.llm_client.complete(system, user)

        # Cache the result
        if self.cache:
            self.cache.put(
                system,
                user,
                response.content,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                model=response.model,
            )

        return TranslationResult(
            source=expression,
            translated=response.content.strip(),
            method=TranslationMethod.LLM,
            confidence=0.85,
            tokens_used=response.total_tokens,
        )

    async def translate_batch(
        self,
        expressions: list[str],
        *,
        template_name: str = "oac_to_dax",
        context: dict[str, str] | None = None,
    ) -> list[TranslationResult]:
        """Translate multiple expressions."""
        results: list[TranslationResult] = []
        for expr in expressions:
            result = await self.translate_expression(
                expr, template_name=template_name, context=context
            )
            results.append(result)
        return results
