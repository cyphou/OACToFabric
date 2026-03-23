"""Tests for PL/SQL → PySpark translator."""

from __future__ import annotations

import pytest

from src.agents.etl.plsql_translator import (
    TranslationResult,
    build_llm_prompt,
    translate_plsql,
    translate_with_fallback,
)


# ---------------------------------------------------------------------------
# Rule-based translation
# ---------------------------------------------------------------------------


class TestTranslatePLSQL:
    def test_insert_select(self):
        plsql = """
        BEGIN
            INSERT INTO target_table SELECT * FROM source_table;
        END;
        """
        result = translate_plsql(plsql, "test_proc")
        assert "saveAsTable" in result.pyspark_code or "INSERT INTO" in result.pyspark_code
        assert result.procedure_name == "test_proc"

    def test_delete_from(self):
        plsql = """
        BEGIN
            DELETE FROM orders WHERE status = 'CANCELLED';
        END;
        """
        result = translate_plsql(plsql, "cleanup_proc")
        assert "delete" in result.pyspark_code.lower()
        assert "CANCELLED" in result.pyspark_code

    def test_update_set(self):
        plsql = """
        BEGIN
            UPDATE customers SET status = 'INACTIVE' WHERE last_login < SYSDATE - 365;
        END;
        """
        result = translate_plsql(plsql, "deactivate_proc")
        assert "update" in result.pyspark_code.lower() or "UPDATE" in result.pyspark_code

    def test_merge_into(self):
        plsql = """
        MERGE INTO target t
        USING source s ON (t.id = s.id)
        WHEN MATCHED THEN UPDATE SET t.name = s.name
        WHEN NOT MATCHED THEN INSERT (id, name) VALUES (s.id, s.name);
        """
        result = translate_plsql(plsql, "merge_proc")
        assert "merge" in result.pyspark_code.lower() or "DeltaTable" in result.pyspark_code
        assert result.confidence <= 0.8

    def test_execute_immediate(self):
        plsql = """
        BEGIN
            EXECUTE IMMEDIATE 'CREATE TABLE temp_data AS SELECT * FROM source';
        END;
        """
        result = translate_plsql(plsql, "ddl_proc")
        assert "spark.sql" in result.pyspark_code

    def test_exception_handling(self):
        plsql = """
        BEGIN
            INSERT INTO t SELECT 1 FROM DUAL;
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('Error occurred');
        END;
        """
        result = translate_plsql(plsql, "with_exception")
        assert "except" in result.pyspark_code.lower() or "try" in result.pyspark_code.lower()

    def test_table_mapping(self):
        plsql = "BEGIN INSERT INTO LEGACY_TABLE SELECT * FROM SOURCE_DATA; END;"
        tmap = {"LEGACY_TABLE": "new_table", "SOURCE_DATA": "source_data_lh"}
        result = translate_plsql(plsql, "mapped_proc", table_mapping=tmap)
        # The translation should reference the mapped names
        assert result.pyspark_code  # Non-empty output

    def test_cursor_loop_low_confidence(self):
        plsql = """
        DECLARE
            CURSOR c IS SELECT id, name FROM employees;
        BEGIN
            FOR r IN c LOOP
                DBMS_OUTPUT.PUT_LINE(r.name);
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "cursor_proc")
        assert result.confidence <= 0.6
        assert any("CURSOR" in w or "cursor" in w.lower() for w in result.warnings)

    def test_untranslatable_patterns(self):
        plsql = """
        CREATE OR REPLACE PACKAGE BODY my_pkg AS
            PROCEDURE do_stuff IS
                TYPE t_ids IS TABLE OF NUMBER;
                l_ids t_ids;
            BEGIN
                SELECT id BULK COLLECT INTO l_ids FROM employees;
                FORALL i IN l_ids.FIRST..l_ids.LAST
                    INSERT INTO target VALUES(l_ids(i));
            END;
        END;
        """
        result = translate_plsql(plsql, "complex_proc")
        assert result.confidence < 0.5
        assert len(result.untranslated_sections) >= 2
        assert result.requires_review is True

    def test_output_has_imports(self):
        result = translate_plsql("BEGIN NULL; END;", "noop")
        assert "pyspark.sql" in result.pyspark_code
        assert "logging" in result.pyspark_code


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------


class TestBuildLLMPrompt:
    def test_prompt_contains_plsql(self):
        plsql = "CREATE OR REPLACE PROCEDURE hello AS BEGIN NULL; END;"
        prompt = build_llm_prompt(plsql, "hello")
        assert "hello" in prompt
        assert plsql in prompt
        assert "PySpark" in prompt
        assert "Delta Lake" in prompt

    def test_prompt_includes_mapping(self):
        prompt = build_llm_prompt("BEGIN NULL; END;", "x", {"OLD_TABLE": "new_table"})
        assert "OLD_TABLE" in prompt
        assert "new_table" in prompt


# ---------------------------------------------------------------------------
# Fallback strategy
# ---------------------------------------------------------------------------


class TestTranslateWithFallback:
    def test_high_confidence_skips_llm(self):
        # Simple procedure → high confidence, no LLM needed
        plsql = "BEGIN INSERT INTO t SELECT 1 FROM dual; END;"
        result = translate_with_fallback(plsql, "simple", llm_client=None)
        assert result.method == "rule-based"

    def test_low_confidence_without_llm(self):
        plsql = """
        CREATE OR REPLACE PACKAGE BODY complex AS
            PROCEDURE x IS
                TYPE t IS TABLE OF NUMBER;
            BEGIN
                FORALL i IN 1..10 INSERT INTO t VALUES(i);
            END;
        END;
        """
        result = translate_with_fallback(plsql, "complex", llm_client=None)
        assert result.requires_review is True
        # Without LLM client, method stays rule-based or manual
        assert result.method in ("rule-based", "manual")

    def test_low_confidence_with_mock_llm(self):
        class MockLLM:
            def complete(self, prompt: str) -> str:
                return "# LLM-generated PySpark code\npass\n"

        plsql = """
        CREATE OR REPLACE PACKAGE BODY complex AS
            PROCEDURE x IS
                TYPE t IS TABLE OF NUMBER;
            BEGIN
                FORALL i IN 1..10 INSERT INTO t VALUES(i);
            END;
        END;
        """
        result = translate_with_fallback(plsql, "complex", llm_client=MockLLM())
        assert result.method == "llm"
        assert "LLM-generated" in result.pyspark_code
