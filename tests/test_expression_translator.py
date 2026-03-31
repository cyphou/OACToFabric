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


# ---------------------------------------------------------------------------
# New analytic / window functions
# ---------------------------------------------------------------------------


class TestAnalyticWindowFunctions:
    def test_dense_rank(self):
        tx = translate_expression("DENSE_RANK(Revenue)", table_name="Sales")
        assert "RANKX" in tx.dax_expression
        assert "DENSE" in tx.dax_expression

    def test_row_number(self):
        tx = translate_expression("ROW_NUMBER()", table_name="Sales")
        assert "RANKX" in tx.dax_expression

    def test_ntile(self):
        tx = translate_expression("NTILE(4)", table_name="Sales")
        assert "RANKX" in tx.dax_expression
        assert "4" in tx.dax_expression

    def test_lead_single_arg(self):
        tx = translate_expression("LEAD(Amount)", table_name="Orders")
        assert "OFFSET" in tx.dax_expression
        assert "1" in tx.dax_expression

    def test_lead_with_offset(self):
        tx = translate_expression("LEAD(Amount, 3)", table_name="Orders")
        assert "OFFSET" in tx.dax_expression
        assert "3" in tx.dax_expression

    def test_lag_single_arg(self):
        tx = translate_expression("LAG(Price)", table_name="Products")
        assert "OFFSET" in tx.dax_expression
        assert "-1" in tx.dax_expression

    def test_lag_with_offset(self):
        tx = translate_expression("LAG(Price, 2)", table_name="Products")
        assert "OFFSET" in tx.dax_expression
        assert "-2" in tx.dax_expression

    def test_cume_dist(self):
        tx = translate_expression("CUME_DIST()", table_name="Sales")
        assert "DIVIDE" in tx.dax_expression
        assert "RANKX" in tx.dax_expression
        assert "COUNTROWS" in tx.dax_expression

    def test_percent_rank(self):
        tx = translate_expression("PERCENT_RANK()", table_name="Sales")
        assert "DIVIDE" in tx.dax_expression
        assert "- 1" in tx.dax_expression

    def test_ratio_to_report(self):
        tx = translate_expression("RATIO_TO_REPORT(SUM(Revenue))", table_name="Sales")
        assert "DIVIDE" in tx.dax_expression
        assert "ALL" in tx.dax_expression


# ---------------------------------------------------------------------------
# Additional string functions
# ---------------------------------------------------------------------------


class TestStringFunctions:
    def test_substring(self):
        tx = translate_expression("SUBSTRING(name, 1, 5)", table_name="T")
        assert "MID" in tx.dax_expression

    def test_substr(self):
        tx = translate_expression("SUBSTR(code, 2, 3)", table_name="T")
        assert "MID" in tx.dax_expression

    def test_upper(self):
        tx = translate_expression("UPPER(name)", table_name="T")
        assert "UPPER" in tx.dax_expression

    def test_lower(self):
        tx = translate_expression("LOWER(name)", table_name="T")
        assert "LOWER" in tx.dax_expression

    def test_trim(self):
        tx = translate_expression("TRIM(notes)", table_name="T")
        assert "TRIM" in tx.dax_expression

    def test_ltrim(self):
        tx = translate_expression("LTRIM(notes)", table_name="T")
        assert "TRIM" in tx.dax_expression

    def test_rtrim(self):
        tx = translate_expression("RTRIM(notes)", table_name="T")
        assert "TRIM" in tx.dax_expression

    def test_replace(self):
        tx = translate_expression("REPLACE(phone, '-', '')", table_name="T")
        assert "SUBSTITUTE" in tx.dax_expression

    def test_length(self):
        tx = translate_expression("LENGTH(name)", table_name="T")
        assert "LEN" in tx.dax_expression

    def test_instr(self):
        tx = translate_expression("INSTR(email, '@')", table_name="T")
        assert "FIND" in tx.dax_expression

    def test_lpad(self):
        tx = translate_expression("LPAD(code, 8, '0')", table_name="T")
        assert "REPT" in tx.dax_expression

    def test_rpad(self):
        tx = translate_expression("RPAD(code, 10, ' ')", table_name="T")
        assert "REPT" in tx.dax_expression

    def test_left(self):
        tx = translate_expression("LEFT(name, 3)", table_name="T")
        assert "LEFT" in tx.dax_expression

    def test_right(self):
        tx = translate_expression("RIGHT(name, 3)", table_name="T")
        assert "RIGHT" in tx.dax_expression

    def test_initcap(self):
        tx = translate_expression("INITCAP(name)", table_name="T")
        assert "UPPER" in tx.dax_expression
        assert "MID" in tx.dax_expression

    def test_ascii(self):
        tx = translate_expression("ASCII(letter)", table_name="T")
        assert "UNICODE" in tx.dax_expression

    def test_chr(self):
        tx = translate_expression("CHR(65)", table_name="T")
        assert "UNICHAR" in tx.dax_expression

    def test_translate(self):
        tx = translate_expression("TRANSLATE(status, 'A', 'Active')", table_name="T")
        assert "SUBSTITUTE" in tx.dax_expression

    def test_reverse(self):
        tx = translate_expression("REVERSE(name)", table_name="T")
        assert "REVERSE" in tx.dax_expression


# ---------------------------------------------------------------------------
# Regex / unsupported string patterns
# ---------------------------------------------------------------------------


class TestUnsupportedRegex:
    def test_regexp_replace(self):
        tx = translate_expression("REGEXP_REPLACE(phone, '[^0-9]', '')", table_name="T")
        assert "manual" in tx.dax_expression.lower() or "REGEXP_REPLACE" in tx.dax_expression

    def test_regexp_substr(self):
        tx = translate_expression("REGEXP_SUBSTR(email, '[^@]+')", table_name="T")
        assert "manual" in tx.dax_expression.lower() or "REGEXP_SUBSTR" in tx.dax_expression

    def test_regexp_instr(self):
        tx = translate_expression("REGEXP_INSTR(txt, '[0-9]')", table_name="T")
        assert "manual" in tx.dax_expression.lower() or "REGEXP_INSTR" in tx.dax_expression

    def test_regexp_like(self):
        tx = translate_expression("REGEXP_LIKE(name, '^A.*')", table_name="T")
        assert "manual" in tx.dax_expression.lower() or "REGEXP_LIKE" in tx.dax_expression

    def test_soundex(self):
        tx = translate_expression("SOUNDEX(name)", table_name="T")
        assert "SOUNDEX" in tx.dax_expression or "manual" in tx.dax_expression.lower()


# ---------------------------------------------------------------------------
# Logical / null-handling functions
# ---------------------------------------------------------------------------


class TestLogicalFunctions:
    def test_nvl2(self):
        tx = translate_expression("NVL2(dept, dept, 'N/A')", table_name="T")
        assert "ISBLANK" in tx.dax_expression

    def test_coalesce(self):
        tx = translate_expression("COALESCE(a, b, c)", table_name="T")
        assert "COALESCE" in tx.dax_expression

    def test_nullif(self):
        tx = translate_expression("NULLIF(status, '')", table_name="T")
        assert "BLANK" in tx.dax_expression

    def test_greatest(self):
        tx = translate_expression("GREATEST(salary, 50000)", table_name="T")
        assert ">=" in tx.dax_expression

    def test_least(self):
        tx = translate_expression("LEAST(salary, 200000)", table_name="T")
        assert "<=" in tx.dax_expression

    def test_decode(self):
        tx = translate_expression(
            "DECODE(status, 'A', 'Active', 'I', 'Inactive', 'Unknown')",
            table_name="T",
        )
        assert "SWITCH" in tx.dax_expression
        assert "Active" in tx.dax_expression
        assert "Unknown" in tx.dax_expression


# ---------------------------------------------------------------------------
# Date functions
# ---------------------------------------------------------------------------


class TestDateFunctions:
    def test_extract_year(self):
        tx = translate_expression("EXTRACT(YEAR FROM hire_date)", table_name="T")
        assert "YEAR" in tx.dax_expression

    def test_extract_month(self):
        tx = translate_expression("EXTRACT(MONTH FROM order_date)", table_name="T")
        assert "MONTH" in tx.dax_expression

    def test_extract_quarter(self):
        tx = translate_expression("EXTRACT(QUARTER FROM ship_date)", table_name="T")
        assert "QUARTER" in tx.dax_expression

    def test_extract_day(self):
        tx = translate_expression("EXTRACT(DAY FROM order_date)", table_name="T")
        assert "DAY" in tx.dax_expression

    def test_current_date(self):
        tx = translate_expression("CURRENT_DATE", table_name="T")
        assert "TODAY()" in tx.dax_expression

    def test_current_timestamp(self):
        tx = translate_expression("CURRENT_TIMESTAMP", table_name="T")
        assert "NOW()" in tx.dax_expression

    def test_sysdate(self):
        tx = translate_expression("SYSDATE", table_name="T")
        assert "NOW()" in tx.dax_expression

    def test_add_months(self):
        tx = translate_expression("ADD_MONTHS(hire_date, 12)", table_name="T")
        assert "EDATE" in tx.dax_expression

    def test_months_between(self):
        tx = translate_expression("MONTHS_BETWEEN(end_date, start_date)", table_name="T")
        assert "DATEDIFF" in tx.dax_expression
        assert "MONTH" in tx.dax_expression

    def test_timestampadd(self):
        tx = translate_expression("TIMESTAMPADD(SQL_TSI_DAY, 7, order_date)", table_name="T")
        assert "DATEADD" in tx.dax_expression

    def test_timestampdiff(self):
        tx = translate_expression("TIMESTAMPDIFF(SQL_TSI_MONTH, start_date, end_date)", table_name="T")
        assert "DATEDIFF" in tx.dax_expression

    def test_to_date(self):
        tx = translate_expression("TO_DATE('2025-01-01', 'YYYY-MM-DD')", table_name="T")
        assert "DATEVALUE" in tx.dax_expression

    def test_to_char(self):
        tx = translate_expression("TO_CHAR(hire_date, 'YYYY-MM-DD')", table_name="T")
        assert "FORMAT" in tx.dax_expression

    def test_to_number(self):
        tx = translate_expression("TO_NUMBER(code)", table_name="T")
        assert "VALUE" in tx.dax_expression

    def test_last_day(self):
        tx = translate_expression("LAST_DAY(hire_date)", table_name="T")
        assert "EOMONTH" in tx.dax_expression


# ---------------------------------------------------------------------------
# Math functions
# ---------------------------------------------------------------------------


class TestMathFunctions:
    def test_abs(self):
        tx = translate_expression("ABS(profit)", table_name="T")
        assert "ABS" in tx.dax_expression

    def test_round(self):
        tx = translate_expression("ROUND(price, 2)", table_name="T")
        assert "ROUND" in tx.dax_expression

    def test_ceil(self):
        tx = translate_expression("CEIL(value)", table_name="T")
        assert "CEILING" in tx.dax_expression

    def test_floor(self):
        tx = translate_expression("FLOOR(value)", table_name="T")
        assert "FLOOR" in tx.dax_expression

    def test_power(self):
        tx = translate_expression("POWER(base, 2)", table_name="T")
        assert "POWER" in tx.dax_expression

    def test_sqrt(self):
        tx = translate_expression("SQRT(value)", table_name="T")
        assert "SQRT" in tx.dax_expression

    def test_log(self):
        tx = translate_expression("LOG(value)", table_name="T")
        assert "LN" in tx.dax_expression

    def test_log10(self):
        tx = translate_expression("LOG10(value)", table_name="T")
        assert "LOG" in tx.dax_expression
        assert "10" in tx.dax_expression

    def test_exp(self):
        tx = translate_expression("EXP(1)", table_name="T")
        assert "EXP" in tx.dax_expression

    def test_mod(self):
        tx = translate_expression("MOD(key, 10)", table_name="T")
        assert "MOD" in tx.dax_expression

    def test_sign(self):
        tx = translate_expression("SIGN(diff)", table_name="T")
        assert "SIGN" in tx.dax_expression


# ---------------------------------------------------------------------------
# Special OAC functions
# ---------------------------------------------------------------------------


class TestSpecialFunctions:
    def test_evaluate(self):
        tx = translate_expression("EVALUATE(select 1 from dual)", table_name="T")
        assert "EVALUATE" in tx.dax_expression or "manual" in tx.dax_expression.lower()

    def test_lookup(self):
        tx = translate_expression("LOOKUP(Revenue, Region)", table_name="Sales")
        assert "LOOKUPVALUE" in tx.dax_expression

    def test_rand(self):
        tx = translate_expression("RAND()", table_name="T")
        assert "RAND()" in tx.dax_expression

    def test_between(self):
        tx = translate_expression("amount BETWEEN 100 AND 500", table_name="T")
        assert ">=" in tx.dax_expression
        assert "<=" in tx.dax_expression

    def test_in_list(self):
        tx = translate_expression("status IN ('A', 'B', 'C')", table_name="T")
        assert "IN" in tx.dax_expression


# ---------------------------------------------------------------------------
# Additional time intelligence
# ---------------------------------------------------------------------------


class TestAdditionalTimeIntelligence:
    def test_todate_week(self):
        tx = translate_expression("TODATE(Revenue, WEEK)", table_name="Sales")
        assert "DATESINPERIOD" in tx.dax_expression

    def test_mavg(self):
        tx = translate_expression("MAVG(Revenue, 7)", table_name="Sales")
        assert "DATESINPERIOD" in tx.dax_expression
        assert "7" in tx.dax_expression

    def test_msum(self):
        tx = translate_expression("MSUM(Revenue, 30)", table_name="Sales")
        assert "DATESINPERIOD" in tx.dax_expression
        assert "30" in tx.dax_expression

    def test_rcount(self):
        tx = translate_expression("RCOUNT(qty)", table_name="Sales")
        assert "COUNTROWS" in tx.dax_expression

    def test_rmax(self):
        tx = translate_expression("RMAX(Revenue)", table_name="Sales")
        assert "MAX" in tx.dax_expression
        assert "ALL" in tx.dax_expression

    def test_rmin(self):
        tx = translate_expression("RMIN(Revenue)", table_name="Sales")
        assert "MIN" in tx.dax_expression
        assert "ALL" in tx.dax_expression

    def test_parallelperiod(self):
        tx = translate_expression("PARALLELPERIOD(Revenue, -1, YEAR)", table_name="Sales")
        assert "PARALLELPERIOD" in tx.dax_expression

    def test_openingbalanceyear(self):
        tx = translate_expression("OPENINGBALANCEYEAR(Revenue)", table_name="Sales")
        assert "OPENINGBALANCEYEAR" in tx.dax_expression

    def test_closingbalanceyear(self):
        tx = translate_expression("CLOSINGBALANCEYEAR(Revenue)", table_name="Sales")
        assert "CLOSINGBALANCEYEAR" in tx.dax_expression


# ---------------------------------------------------------------------------
# Advanced aggregates
# ---------------------------------------------------------------------------


class TestAdvancedAggregates:
    def test_stddev(self):
        tx = translate_expression("STDDEV(Revenue)", table_name="Sales")
        assert "STDEV.S" in tx.dax_expression

    def test_stddev_pop(self):
        tx = translate_expression("STDDEV_POP(Revenue)", table_name="Sales")
        assert "STDEV.P" in tx.dax_expression

    def test_variance(self):
        tx = translate_expression("VARIANCE(Revenue)", table_name="Sales")
        assert "VAR.S" in tx.dax_expression

    def test_var_pop(self):
        tx = translate_expression("VAR_POP(Revenue)", table_name="Sales")
        assert "VAR.P" in tx.dax_expression

    def test_median(self):
        tx = translate_expression("MEDIAN(Revenue)", table_name="Sales")
        assert "MEDIAN" in tx.dax_expression

    def test_percentile(self):
        tx = translate_expression("PERCENTILE(Revenue, 0.9)", table_name="Sales")
        assert "PERCENTILEX.INC" in tx.dax_expression

    def test_countif(self):
        tx = translate_expression("COUNTIF(Revenue, Revenue > 10000)", table_name="Sales")
        assert "CALCULATE" in tx.dax_expression
        assert "COUNT" in tx.dax_expression

    def test_sumif(self):
        tx = translate_expression("SUMIF(Revenue, Discount > 0)", table_name="Sales")
        assert "CALCULATE" in tx.dax_expression
        assert "SUM" in tx.dax_expression

    def test_first(self):
        tx = translate_expression("FIRST(order_date)", table_name="Orders")
        assert "FIRSTNONBLANK" in tx.dax_expression

    def test_last(self):
        tx = translate_expression("LAST(order_date)", table_name="Orders")
        assert "LASTNONBLANK" in tx.dax_expression
