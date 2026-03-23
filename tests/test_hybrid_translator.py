"""Tests for hybrid translation engine."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.core.hybrid_translator import (
    HybridTranslator,
    TranslationMethod,
    TranslationResult,
    _apply_function_rules,
    _OAC_TO_DAX_RULES,
    _ORACLE_TO_SPARK_RULES,
)
from src.core.llm_client import LLMClient, LLMResponse
from src.core.translation_cache import TranslationCache


# ---------------------------------------------------------------------------
# Rule-based translation
# ---------------------------------------------------------------------------


class TestApplyFunctionRules:
    def test_simple_substitution(self):
        result, full = _apply_function_rules("AVG(col1)", _OAC_TO_DAX_RULES)
        assert "AVERAGE" in result
        assert full is True

    def test_multiple_substitutions(self):
        result, full = _apply_function_rules("SUM(col1) + AVG(col2)", _OAC_TO_DAX_RULES)
        assert "SUM" in result
        assert "AVERAGE" in result

    def test_no_match(self):
        result, full = _apply_function_rules("CUSTOM_FUNC(x)", _OAC_TO_DAX_RULES)
        assert result == "CUSTOM_FUNC(x)"
        assert full is False

    def test_case_insensitive(self):
        result, full = _apply_function_rules("avg(col)", _OAC_TO_DAX_RULES)
        assert "AVERAGE" in result

    def test_oracle_nvl(self):
        result, full = _apply_function_rules("NVL(col, 0)", _ORACLE_TO_SPARK_RULES)
        assert "COALESCE" in result

    def test_oracle_sysdate(self):
        result, full = _apply_function_rules("SELECT SYSDATE FROM DUAL", _ORACLE_TO_SPARK_RULES)
        assert "CURRENT_DATE()" in result


# ---------------------------------------------------------------------------
# HybridTranslator — rules only
# ---------------------------------------------------------------------------


class TestHybridTranslatorRulesOnly:
    @pytest.mark.asyncio
    async def test_simple_rules_translation(self):
        translator = HybridTranslator(enable_llm=False)
        result = await translator.translate_expression("SUM(revenue)")
        assert result.method == TranslationMethod.RULES
        assert "SUM" in result.translated
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_unknown_function_partial_result(self):
        translator = HybridTranslator(enable_llm=False)
        result = await translator.translate_expression("MAGIC_FUNC(x)")
        assert result.method == TranslationMethod.RULES
        assert result.confidence <= 0.5

    @pytest.mark.asyncio
    async def test_batch_translate(self):
        translator = HybridTranslator(enable_llm=False)
        results = await translator.translate_batch(
            ["SUM(a)", "AVG(b)", "COUNT(c)"]
        )
        assert len(results) == 3
        for r in results:
            assert isinstance(r, TranslationResult)


# ---------------------------------------------------------------------------
# HybridTranslator — with LLM
# ---------------------------------------------------------------------------


class TestHybridTranslatorWithLLM:
    @pytest.mark.asyncio
    async def test_llm_fallback_called(self):
        mock_llm = AsyncMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(
            return_value=LLMResponse(
                content="CALCULATE(SUM(Sales[Amount]))",
                prompt_tokens=50,
                completion_tokens=10,
                total_tokens=60,
                model="gpt-4",
            )
        )

        translator = HybridTranslator(llm_client=mock_llm, enable_llm=True)
        result = await translator.translate_expression(
            "MAGIC_UNKNOWN(revenue)",
            context={"table_name": "Sales", "column_mappings": "revenue → Amount"},
        )
        assert result.method == TranslationMethod.LLM
        assert "CALCULATE" in result.translated

    @pytest.mark.asyncio
    async def test_llm_failure_falls_back_to_rules(self):
        mock_llm = AsyncMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(side_effect=Exception("API error"))

        translator = HybridTranslator(llm_client=mock_llm, enable_llm=True)
        result = await translator.translate_expression("CUSTOM(x)")
        assert result.method == TranslationMethod.RULES
        assert result.confidence <= 0.5


# ---------------------------------------------------------------------------
# HybridTranslator — with cache
# ---------------------------------------------------------------------------


class TestHybridTranslatorWithCache:
    @pytest.mark.asyncio
    async def test_cache_stores_rules_result(self):
        cache = TranslationCache(db_path=":memory:")
        translator = HybridTranslator(cache=cache, enable_llm=False)

        await translator.translate_expression("SUM(x)")
        assert cache.count() >= 1
        cache.close()

    @pytest.mark.asyncio
    async def test_cache_hit_avoids_llm_call(self):
        cache = TranslationCache(db_path=":memory:")
        mock_llm = AsyncMock(spec=LLMClient)
        mock_llm.complete = AsyncMock(
            return_value=LLMResponse(
                content="TRANSLATED",
                total_tokens=10,
                model="gpt-4",
            )
        )

        translator = HybridTranslator(
            llm_client=mock_llm, cache=cache, enable_llm=True
        )

        # First call — should hit LLM
        r1 = await translator.translate_expression(
            "UNKNOWN_FUNC(z)",
            context={"table_name": "T", "column_mappings": "z → Z"},
        )
        assert r1.method == TranslationMethod.LLM

        # Second call — should hit cache
        r2 = await translator.translate_expression(
            "UNKNOWN_FUNC(z)",
            context={"table_name": "T", "column_mappings": "z → Z"},
        )
        assert r2.method == TranslationMethod.LLM  # method stays LLM
        assert r2.tokens_used == 0  # but no tokens used

        cache.close()
