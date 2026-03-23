"""Tests for syntax validators (DAX, PySpark, Spark SQL)."""

from __future__ import annotations

import pytest

from src.core.syntax_validator import (
    SyntaxValidationResult,
    ValidationSeverity,
    validate,
    validate_dax,
    validate_pyspark,
    validate_spark_sql,
)


# ---------------------------------------------------------------------------
# DAX Validator
# ---------------------------------------------------------------------------


class TestValidateDAX:
    def test_valid_simple_measure(self):
        r = validate_dax("SUM(Sales[Amount])")
        assert r.valid is True
        assert r.error_count == 0

    def test_valid_calculate(self):
        r = validate_dax("CALCULATE(SUM(Sales[Amount]), ALL(Sales[Region]))")
        assert r.valid is True

    def test_unmatched_paren(self):
        r = validate_dax("SUM(Sales[Amount]")
        assert r.valid is False
        assert r.error_count >= 1

    def test_extra_closing_paren(self):
        r = validate_dax("SUM(Sales[Amount]))")
        assert r.valid is False

    def test_unknown_function_warning(self):
        r = validate_dax("FOOBAR(x)")
        assert r.warning_count >= 1

    def test_unbalanced_brackets(self):
        r = validate_dax("SUM(Sales[Amount)")
        assert r.valid is False

    def test_evaluate_warning(self):
        r = validate_dax("EVALUATE ROW('Total', SUM(Sales[Amount]))")
        assert r.warning_count >= 1

    def test_empty_expression(self):
        r = validate_dax("")
        assert r.valid is True


# ---------------------------------------------------------------------------
# PySpark Validator
# ---------------------------------------------------------------------------


class TestValidatePySpark:
    def test_valid_code(self):
        code = """
df = spark.read.format("delta").load("/data/sales")
result = df.groupBy("region").agg({"amount": "sum"})
result.write.format("delta").save("/output/sales_summary")
"""
        r = validate_pyspark(code)
        assert r.valid is True

    def test_syntax_error(self):
        r = validate_pyspark("def foo(:\n    pass")
        assert r.valid is False
        assert r.error_count >= 1

    def test_collect_warning(self):
        r = validate_pyspark("data = df.collect()")
        assert r.warning_count >= 1

    def test_empty_code(self):
        r = validate_pyspark("")
        assert r.valid is True


# ---------------------------------------------------------------------------
# Spark SQL Validator
# ---------------------------------------------------------------------------


class TestValidateSparkSQL:
    def test_valid_select(self):
        r = validate_spark_sql("SELECT region, SUM(amount) FROM sales GROUP BY region")
        assert r.valid is True

    def test_oracle_nvl_detected(self):
        r = validate_spark_sql("SELECT NVL(col, 0) FROM table1")
        assert r.valid is False
        assert any("NVL" in i.message for i in r.issues)

    def test_oracle_sysdate_detected(self):
        r = validate_spark_sql("SELECT SYSDATE FROM DUAL")
        assert r.valid is False

    def test_oracle_connect_by_detected(self):
        r = validate_spark_sql("SELECT * FROM emp CONNECT BY PRIOR id = parent_id")
        assert r.valid is False

    def test_oracle_rownum_detected(self):
        r = validate_spark_sql("SELECT * FROM t WHERE ROWNUM <= 10")
        assert r.valid is False

    def test_unbalanced_parens(self):
        r = validate_spark_sql("SELECT COALESCE(col, 0 FROM t")
        assert r.valid is False

    def test_create_table_valid(self):
        r = validate_spark_sql("CREATE TABLE sales (id INT, amount DECIMAL)")
        assert r.valid is True

    def test_unknown_start_keyword_warning(self):
        r = validate_spark_sql("FOOBAR something")
        assert r.warning_count >= 1


# ---------------------------------------------------------------------------
# Unified validator
# ---------------------------------------------------------------------------


class TestUnifiedValidator:
    def test_dax(self):
        r = validate("SUM(Sales[Amount])", "dax")
        assert r.language == "dax"
        assert r.valid is True

    def test_pyspark(self):
        r = validate("x = 1 + 2", "pyspark")
        assert r.language == "pyspark"
        assert r.valid is True

    def test_python_alias(self):
        r = validate("x = 1", "python")
        assert r.language == "pyspark"

    def test_sql_alias(self):
        r = validate("SELECT 1", "sql")
        assert r.language == "spark_sql"

    def test_unknown_language(self):
        r = validate("anything", "fortran")
        assert r.valid is True
        assert r.issues[0].severity == ValidationSeverity.INFO
