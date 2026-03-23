"""Tests for OAC expression → DAX translator."""

from __future__ import annotations

import pytest

from src.agents.semantic.expression_translator import (
    DAXTranslation,
    _translate_case_when,
    _translate_cast,
    build_dax_llm_prompt,
    translate_all_expressions,
    translate_expression,
    translate_with_llm_fallback,
)


# ---------------------------------------------------------------------------
# Aggregate functions
# ---------------------------------------------------------------------------


class TestAggregateTranslation:
    def test_sum(self):
        tx = translate_expression("SUM(Revenue)", table_name="Sales", column_name="TotalRev")
        assert "SUM" in tx.dax_expression
        assert "'Sales'" in tx.dax_expression
        assert tx.is_measure is True

    def test_count(self):
        tx = translate_expression("COUNT(OrderID)", table_name="Orders")
        assert "COUNT" in tx.dax_expression

    def test_countdistinct(self):
        tx = translate_expression("COUNTDISTINCT(CustomerID)", table_name="Sales")
        assert "DISTINCTCOUNT" in tx.dax_expression

    def test_avg(self):
        tx = translate_expression("AVG(Price)", table_name="Products")
        assert "AVERAGE" in tx.dax_expression

    def test_min_max(self):
        tx_min = translate_expression("MIN(Amount)", table_name="T")
        tx_max = translate_expression("MAX(Amount)", table_name="T")
        assert "MIN" in tx_min.dax_expression
        assert "MAX" in tx_max.dax_expression


# ---------------------------------------------------------------------------
# Time intelligence
# ---------------------------------------------------------------------------


class TestTimeIntelligence:
    def test_ago(self):
        tx = translate_expression("AGO(TotalRevenue, YEAR, 1)", table_name="Sales")
        assert "DATEADD" in tx.dax_expression
        assert "-1" in tx.dax_expression
        assert tx.is_measure is True

    def test_todate_year(self):
        tx = translate_expression("TODATE(Revenue, YEAR)", table_name="Sales")
        assert "DATESYTD" in tx.dax_expression

    def test_todate_quarter(self):
        tx = translate_expression("TODATE(Revenue, QUARTER)", table_name="Sales")
        assert "DATESQTD" in tx.dax_expression

    def test_todate_month(self):
        tx = translate_expression("TODATE(Revenue, MONTH)", table_name="Sales")
        assert "DATESMTD" in tx.dax_expression

    def test_periodrolling(self):
        tx = translate_expression("PERIODROLLING(Revenue, -30)", table_name="Sales")
        assert "DATESINPERIOD" in tx.dax_expression

    def test_rsum(self):
        tx = translate_expression("RSUM(Revenue)", table_name="Sales")
        assert "CALCULATE" in tx.dax_expression
        assert "ALL" in tx.dax_expression

    def test_time_intel_display_folder(self):
        tx = translate_expression("AGO(Rev, YEAR, 1)", table_name="Sales")
        assert tx.display_folder == "Time Intelligence"


# ---------------------------------------------------------------------------
# Scalar functions
# ---------------------------------------------------------------------------


class TestScalarFunctions:
    def test_ifnull(self):
        tx = translate_expression("IFNULL(discount, 0)", table_name="Sales")
        assert "ISBLANK" in tx.dax_expression
        assert "IF" in tx.dax_expression

    def test_nvl(self):
        tx = translate_expression("NVL(status, 'unknown')", table_name="T")
        assert "ISBLANK" in tx.dax_expression

    def test_concat(self):
        tx = translate_expression("CONCAT(first_name, last_name)", table_name="T")
        assert "&" in tx.dax_expression

    def test_rank(self):
        tx = translate_expression("RANK(Revenue)", table_name="Sales")
        assert "RANKX" in tx.dax_expression

    def test_topn(self):
        tx = translate_expression("TOPN(10, Revenue)", table_name="Sales")
        assert "TOPN" in tx.dax_expression
        assert "10" in tx.dax_expression

    def test_filter_using(self):
        tx = translate_expression("FILTER(Revenue USING (Region = 'West'))", table_name="Sales")
        assert "CALCULATE" in tx.dax_expression

    def test_session_variable(self):
        tx = translate_expression("VALUEOF(NQ_SESSION.USER)", table_name="T")
        assert "USERPRINCIPALNAME" in tx.dax_expression

    def test_string_concatenation_operator(self):
        tx = translate_expression("col_a || col_b", table_name="T")
        assert "&" in tx.dax_expression


# ---------------------------------------------------------------------------
# CASE WHEN
# ---------------------------------------------------------------------------


class TestCaseWhen:
    def test_simple_case(self):
        result = _translate_case_when(
            "CASE WHEN status = 1 THEN 'Active' WHEN status = 0 THEN 'Inactive' ELSE 'Unknown' END"
        )
        assert "SWITCH(TRUE()" in result
        assert "Active" in result
        assert "Unknown" in result

    def test_full_expression(self):
        tx = translate_expression(
            "CASE WHEN amount > 100 THEN 'High' ELSE 'Low' END",
            table_name="Orders",
        )
        assert "SWITCH" in tx.dax_expression
        assert tx.confidence <= 0.8


# ---------------------------------------------------------------------------
# CAST
# ---------------------------------------------------------------------------


class TestCast:
    def test_cast_int(self):
        assert _translate_cast("col", "INT") == "INT(col)"

    def test_cast_number(self):
        assert _translate_cast("col", "NUMBER") == "VALUE(col)"

    def test_cast_varchar(self):
        assert "FORMAT" in _translate_cast("col", "VARCHAR")

    def test_cast_date(self):
        assert "DATEVALUE" in _translate_cast("col", "DATE")

    def test_cast_expression(self):
        tx = translate_expression("CAST(amount AS INTEGER)", table_name="T")
        assert "INT" in tx.dax_expression


# ---------------------------------------------------------------------------
# Confidence and review
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_simple_aggregate_high_confidence(self):
        tx = translate_expression("SUM(Revenue)", table_name="Sales")
        assert tx.confidence >= 0.8
        assert tx.requires_review is False

    def test_complex_unknown_low_confidence(self):
        tx = translate_expression(
            "CONNECT BY PRIOR parent_id = child_id START WITH root = 1",
            table_name="Hierarchy",
        )
        assert tx.confidence < 0.5
        assert tx.requires_review is True

    def test_unmatched_expression_lower_confidence(self):
        tx = translate_expression(
            "some_custom_function(a, b, c, d, e, f)",
            table_name="T",
        )
        assert tx.confidence < 1.0


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_prompt_contains_expression(self):
        prompt = build_dax_llm_prompt("SUM(Revenue)", "Sales", "TotalRev")
        assert "SUM(Revenue)" in prompt
        assert "Sales" in prompt
        assert "DAX" in prompt

    def test_prompt_includes_mapping(self):
        prompt = build_dax_llm_prompt("SUM(x)", "T", "M", table_mapping={"OLD": "NEW"})
        assert "OLD" in prompt
        assert "NEW" in prompt


# ---------------------------------------------------------------------------
# LLM fallback
# ---------------------------------------------------------------------------


class TestLLMFallback:
    def test_high_confidence_skips_llm(self):
        tx = translate_with_llm_fallback("SUM(Revenue)", "Sales", "Rev", llm_client=None)
        assert tx.method == "rule-based"

    def test_low_confidence_with_mock_llm(self):
        class MockLLM:
            def complete(self, prompt: str) -> str:
                return "CALCULATE(SUM(Sales[Revenue]), FILTER(ALL(Region), Region[Name] = \"West\"))\n// notes"

        tx = translate_with_llm_fallback(
            "CONNECT BY PRIOR parent = child",
            "T", "Col",
            llm_client=MockLLM(),
        )
        assert tx.method == "llm"
        assert "CALCULATE" in tx.dax_expression

    def test_low_confidence_without_llm(self):
        tx = translate_with_llm_fallback(
            "CONNECT BY PRIOR parent = child",
            "T", "Col",
            llm_client=None,
        )
        assert tx.requires_review is True


# ---------------------------------------------------------------------------
# Batch
# ---------------------------------------------------------------------------


class TestBatchTranslation:
    def test_translate_all(self):
        exprs = [
            {"expression": "SUM(Revenue)", "table_name": "Sales", "column_name": "Rev"},
            {"expression": "COUNT(OrderID)", "table_name": "Orders", "column_name": "Cnt"},
        ]
        results = translate_all_expressions(exprs)
        assert len(results) == 2
        assert all(isinstance(r, DAXTranslation) for r in results)
