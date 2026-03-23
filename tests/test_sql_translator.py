"""Tests for Oracle SQL → Fabric SQL function translator."""

from __future__ import annotations

import pytest

from src.agents.schema.sql_translator import translate_sql
from src.agents.schema.type_mapper import TargetPlatform


# ---------------------------------------------------------------------------
# Spark SQL translations
# ---------------------------------------------------------------------------

class TestSparkTranslation:
    """Oracle → Spark SQL translations."""

    def test_nvl(self):
        result = translate_sql("SELECT NVL(a, b) FROM t", TargetPlatform.LAKEHOUSE)
        assert "COALESCE(a, b)" in result
        assert "NVL" not in result.upper().replace("COALESCE", "")

    def test_nvl2(self):
        result = translate_sql("SELECT NVL2(a, b, c) FROM t", TargetPlatform.LAKEHOUSE)
        assert "CASE WHEN" in result
        assert "IS NOT NULL" in result

    def test_decode_4args(self):
        result = translate_sql("SELECT DECODE(status, 1, 'Active', 'Inactive') FROM t", TargetPlatform.LAKEHOUSE)
        assert "CASE WHEN" in result
        assert "DECODE" not in result.upper()

    def test_sysdate(self):
        result = translate_sql("SELECT SYSDATE FROM DUAL", TargetPlatform.LAKEHOUSE)
        assert "CURRENT_TIMESTAMP()" in result
        assert "SYSDATE" not in result.upper().replace("CURRENT_TIMESTAMP()", "")

    def test_from_dual_removed(self):
        result = translate_sql("SELECT 1 FROM DUAL", TargetPlatform.LAKEHOUSE)
        assert "DUAL" not in result.upper()

    def test_substr(self):
        result = translate_sql("SELECT SUBSTR(name, 1, 3) FROM t", TargetPlatform.LAKEHOUSE)
        assert "SUBSTRING(" in result

    def test_instr(self):
        result = translate_sql("SELECT INSTR(name, 'a') FROM t", TargetPlatform.LAKEHOUSE)
        assert "LOCATE(" in result

    def test_length(self):
        result = translate_sql("SELECT LENGTH(name) FROM t", TargetPlatform.LAKEHOUSE)
        assert "LENGTH(" in result

    def test_to_number(self):
        result = translate_sql("SELECT TO_NUMBER(val) FROM t", TargetPlatform.LAKEHOUSE)
        assert "CAST(" in result
        assert "DOUBLE" in result

    def test_trunc_date(self):
        result = translate_sql("SELECT TRUNC(created_date) FROM t", TargetPlatform.LAKEHOUSE)
        assert "DATE_TRUNC" in result

    def test_to_char(self):
        result = translate_sql("SELECT TO_CHAR(dt, 'YYYY-MM-DD') FROM t", TargetPlatform.LAKEHOUSE)
        assert "DATE_FORMAT" in result

    def test_months_between_spark(self):
        result = translate_sql("SELECT MONTHS_BETWEEN(a, b) FROM t", TargetPlatform.LAKEHOUSE)
        # Spark has native MONTHS_BETWEEN — should stay as-is
        assert "MONTHS_BETWEEN" in result

    def test_rownum_flagged(self):
        result = translate_sql("SELECT * FROM t WHERE ROWNUM <= 10", TargetPlatform.LAKEHOUSE)
        assert "ROW_NUMBER" in result or "REVIEW" in result

    def test_outer_join_flagged(self):
        result = translate_sql("SELECT * FROM a, b WHERE a.id = b.id(+)", TargetPlatform.LAKEHOUSE)
        assert "REVIEW" in result

    def test_concat_operator(self):
        result = translate_sql("SELECT first_name || ' ' || last_name FROM t", TargetPlatform.LAKEHOUSE)
        assert "CONCAT(" in result


# ---------------------------------------------------------------------------
# T-SQL translations
# ---------------------------------------------------------------------------

class TestTSQLTranslation:
    """Oracle → T-SQL translations."""

    def test_nvl(self):
        result = translate_sql("SELECT NVL(a, b) FROM t", TargetPlatform.WAREHOUSE)
        assert "COALESCE(a, b)" in result

    def test_sysdate(self):
        result = translate_sql("SELECT SYSDATE FROM DUAL", TargetPlatform.WAREHOUSE)
        assert "GETDATE()" in result

    def test_length(self):
        result = translate_sql("SELECT LENGTH(name) FROM t", TargetPlatform.WAREHOUSE)
        assert "LEN(" in result

    def test_instr(self):
        result = translate_sql("SELECT INSTR(name, 'a') FROM t", TargetPlatform.WAREHOUSE)
        assert "CHARINDEX(" in result

    def test_months_between_tsql(self):
        result = translate_sql("SELECT MONTHS_BETWEEN(a, b) FROM t", TargetPlatform.WAREHOUSE)
        assert "DATEDIFF" in result

    def test_to_number(self):
        result = translate_sql("SELECT TO_NUMBER(val) FROM t", TargetPlatform.WAREHOUSE)
        assert "CAST(" in result
        assert "FLOAT" in result

    def test_trunc_date(self):
        result = translate_sql("SELECT TRUNC(dt) FROM t", TargetPlatform.WAREHOUSE)
        assert "CAST(" in result
        assert "DATE" in result
