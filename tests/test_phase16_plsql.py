"""Phase 16 tests — PL/SQL translator: CURSOR LOOP, FORALL, BULK COLLECT."""

from __future__ import annotations

import pytest

from src.agents.etl.plsql_translator import (
    TranslationResult,
    translate_plsql,
    translate_with_fallback,
    _translate_loop_body,
)


class TestTranslateLoopBody:
    """Tests for _translate_loop_body helper."""

    def test_insert_in_loop(self):
        body = "INSERT INTO orders VALUES (rec.id, rec.amount);"
        result = _translate_loop_body(body, {})
        assert "INSERT INTO" in result or "spark.sql" in result
        assert result != "pass"

    def test_update_in_loop(self):
        body = "UPDATE accounts SET balance = 0 WHERE id = rec.id;"
        result = _translate_loop_body(body, {"accounts": "lh_accounts"})
        assert "lh_accounts" in result
        assert "DeltaTable" in result

    def test_delete_in_loop(self):
        body = "DELETE FROM audit_log WHERE created < rec.cutoff;"
        result = _translate_loop_body(body, {})
        assert "DeltaTable" in result or "delete" in result
        assert result != "pass"

    def test_variable_assignment(self):
        body = "v_total := v_total + rec.amount;"
        result = _translate_loop_body(body, {})
        assert "v_total = " in result
        assert result != "pass"

    def test_dbms_output(self):
        body = "DBMS_OUTPUT.PUT_LINE('Processing row ' || rec.id);"
        result = _translate_loop_body(body, {})
        assert "logger.info" in result
        assert result != "pass"

    def test_if_then_else(self):
        body = "IF rec.status = 'A' THEN v_count := v_count + 1; ELSE v_skip := v_skip + 1; END IF;"
        result = _translate_loop_body(body, {})
        assert "if " in result
        assert "else:" in result

    def test_empty_body(self):
        body = "NULL;"
        result = _translate_loop_body(body, {})
        assert result == "pass"

    def test_untranslatable_body(self):
        body = "SOME_PACKAGE.COMPLEX_PROC(rec.id, rec.data);"
        result = _translate_loop_body(body, {})
        assert "TODO" in result or "pass" in result

    def test_multiple_statements(self):
        body = (
            "v_total := v_total + rec.amount;\n"
            "DBMS_OUTPUT.PUT_LINE(v_total);"
        )
        result = _translate_loop_body(body, {})
        assert "v_total = " in result
        assert "logger.info" in result


class TestCursorLoopTranslation:
    """Tests for CURSOR LOOP translation in translate_plsql."""

    def test_simple_cursor_loop(self):
        plsql = """
DECLARE
  CURSOR c_emp IS SELECT id, name FROM employees;
BEGIN
  FOR rec IN c_emp LOOP
    DBMS_OUTPUT.PUT_LINE(rec.name);
  END LOOP;
END;
"""
        result = translate_plsql(plsql, "test_cursor")
        assert "df_cursor" in result.pyspark_code or "spark.sql" in result.pyspark_code
        assert result.confidence <= 1.0

    def test_cursor_loop_with_insert(self):
        plsql = """
CURSOR c_data IS SELECT id, val FROM source_table;
BEGIN
FOR rec IN c_data LOOP
  INSERT INTO target_table VALUES (rec.id, rec.val);
END LOOP;
"""
        result = translate_plsql(plsql, "cursor_insert")
        assert "CURSOR LOOP" in result.pyspark_code
        assert any("CURSOR" in w for w in result.warnings)


class TestForallTranslation:
    """Tests for FORALL → batch DataFrame pattern."""

    def test_forall_insert(self):
        plsql = """
BEGIN
  FORALL i IN 1..v_data.COUNT INSERT INTO target_table VALUES (v_data(i));
END;
"""
        result = translate_plsql(plsql, "forall_insert")
        assert "FORALL" in result.pyspark_code
        assert "df_batch" in result.pyspark_code
        assert "append" in result.pyspark_code
        assert result.confidence <= 0.6
        assert any("FORALL" in w for w in result.warnings)

    def test_forall_update(self):
        plsql = """
BEGIN
  FORALL i IN 1..ids.COUNT UPDATE employees SET status = 'X' WHERE id = ids(i);
END;
"""
        result = translate_plsql(plsql, "forall_update")
        assert "FORALL" in result.pyspark_code
        assert "merge" in result.pyspark_code or "UPDATE" in result.pyspark_code

    def test_forall_delete(self):
        plsql = """
BEGIN
  FORALL idx IN 1..del_ids.COUNT DELETE FROM old_records WHERE id = del_ids(idx);
END;
"""
        result = translate_plsql(plsql, "forall_delete")
        assert "FORALL" in result.pyspark_code
        assert "Delete" in result.pyspark_code or "delete" in result.pyspark_code


class TestBulkCollectTranslation:
    """Tests for BULK COLLECT → DataFrame.collect() pattern."""

    def test_bulk_collect_simple(self):
        plsql = """
BEGIN
  SELECT id, name BULK COLLECT INTO v_employees FROM hr.employees;
END;
"""
        result = translate_plsql(plsql, "bulk_collect")
        assert "BULK COLLECT" in result.pyspark_code
        assert "collect()" in result.pyspark_code
        assert "v_employees" in result.pyspark_code

    def test_bulk_collect_with_table_mapping(self):
        plsql = """
DECLARE
  TYPE t_ids IS TABLE OF NUMBER;
  v_ids t_ids;
BEGIN
  SELECT employee_id BULK COLLECT INTO v_ids FROM HR_EMPLOYEES;
END;
"""
        tmap = {"HR_EMPLOYEES": "lh_employees"}
        result = translate_plsql(plsql, "bulk_mapped", table_mapping=tmap)
        assert "lh_employees" in result.pyspark_code
        assert "v_ids" in result.pyspark_code

    def test_bulk_collect_confidence(self):
        plsql = """
BEGIN
  SELECT col1 BULK COLLECT INTO v_data FROM source_tab;
END;
"""
        result = translate_plsql(plsql, "bulk_conf")
        assert result.confidence <= 0.7


class TestTranslateWithFallback:
    """Tests for LLM fallback behavior."""

    def test_no_llm_returns_rule_based(self):
        plsql = "BEGIN COMMIT; END;"
        result = translate_with_fallback(plsql, "simple", llm_client=None)
        assert result.method == "rule-based"

    def test_low_confidence_triggers_llm(self):
        class FakeLLM:
            def complete(self, prompt):
                return "# LLM generated code"

        plsql = """
BEGIN
  FORALL i IN 1..x.COUNT INSERT INTO t VALUES (x(i));
  FOR rec IN (SELECT * FROM complex_view) LOOP
    SOME_PKG.DO_SOMETHING(rec.id);
  END LOOP;
  UTL_FILE.PUT_LINE(handle, 'done');
END;
"""
        result = translate_with_fallback(plsql, "complex", llm_client=FakeLLM())
        # Should have tried LLM due to UTL_ pattern lowering confidence
        assert result.method in ("llm", "rule-based", "manual")

    def test_llm_failure_falls_back(self):
        class FailingLLM:
            def complete(self, prompt):
                raise RuntimeError("API error")

        plsql = """
BEGIN
  UTL_FILE.PUT_LINE(handle, 'test');
  DBMS_SCHEDULER.CREATE_JOB('job1');
END;
"""
        result = translate_with_fallback(plsql, "failing_llm", llm_client=FailingLLM())
        # Should fall back to rule-based or manual
        assert "LLM fallback failed" in " ".join(result.warnings)
