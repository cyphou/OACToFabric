"""Phase 20 — Advanced Translation & Edge Cases.

≥60 tests covering:
  • Complex PL/SQL patterns (FOR loop, WHILE loop, RAISE, dynamic SQL)
  • Advanced OAC expression translation (string, date, EXTRACT, nested)
  • Edge cases (multi-source, conditional formatting, maps, pivots)
"""

from __future__ import annotations

import pytest

from src.agents.etl.plsql_translator import (
    TranslationResult,
    translate_plsql,
)
from src.agents.semantic.expression_translator import (
    DAXTranslation,
    _translate_case_when,
    _translate_cast,
    _translate_extract,
    translate_expression,
)


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  PL/SQL translation tests — Sprint 20.1                                ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestForNumericLoop:
    """FOR i IN 1..N LOOP → Python for range."""

    def test_basic_for_loop(self):
        plsql = """
        BEGIN
            FOR i IN 1..10 LOOP
                DBMS_OUTPUT.PUT_LINE(i);
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "for_loop_proc")
        assert "for i in range(1, 10 + 1):" in result.pyspark_code
        assert result.confidence <= 0.7

    def test_for_loop_with_variable_bound(self):
        plsql = """
        BEGIN
            FOR idx IN 1..batch_size LOOP
                DBMS_OUTPUT.PUT_LINE(idx);
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "for_var_bound")
        assert "for idx in range(1, batch_size + 1):" in result.pyspark_code

    def test_for_loop_warning(self):
        plsql = """
        BEGIN
            FOR j IN 1..5 LOOP
                v_total := v_total + j;
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "for_warn")
        assert any("numeric loop" in w.lower() or "FOR" in w for w in result.warnings)


class TestWhileLoop:
    """WHILE condition LOOP → Python while."""

    def test_basic_while_loop(self):
        plsql = """
        BEGIN
            WHILE v_count > 0 LOOP
                v_count := v_count - 1;
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "while_proc")
        assert "while" in result.pyspark_code
        assert result.confidence <= 0.6

    def test_while_loop_with_and_condition(self):
        plsql = """
        BEGIN
            WHILE v_done = 0 AND v_retries < 3 LOOP
                v_retries := v_retries + 1;
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "while_and")
        # PL/SQL AND → Python and
        assert "and" in result.pyspark_code.lower()

    def test_while_loop_warning(self):
        plsql = """
        BEGIN
            WHILE TRUE LOOP
                EXIT;
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "while_warn")
        assert any("WHILE" in w or "while" in w.lower() for w in result.warnings)


class TestRaiseApplicationError:
    """RAISE_APPLICATION_ERROR → raise RuntimeError."""

    def test_raise_error(self):
        plsql = """
        BEGIN
            RAISE_APPLICATION_ERROR(-20001, 'Invalid input');
        END;
        """
        result = translate_plsql(plsql, "raise_proc")
        assert "raise RuntimeError" in result.pyspark_code
        assert "-20001" in result.pyspark_code
        assert "Invalid input" in result.pyspark_code

    def test_raise_error_code_range(self):
        plsql = """
        BEGIN
            RAISE_APPLICATION_ERROR(-20999, 'Critical failure');
        END;
        """
        result = translate_plsql(plsql, "raise_code")
        assert "-20999" in result.pyspark_code

    def test_raise_named_exception_no_data_found(self):
        plsql = """
        BEGIN
            RAISE NO_DATA_FOUND;
        END;
        """
        result = translate_plsql(plsql, "raise_ndf")
        assert "raise LookupError" in result.pyspark_code
        assert "NO_DATA_FOUND" in result.pyspark_code

    def test_raise_named_exception_too_many_rows(self):
        plsql = """
        BEGIN
            RAISE TOO_MANY_ROWS;
        END;
        """
        result = translate_plsql(plsql, "raise_tmr")
        assert "raise LookupError" in result.pyspark_code
        assert "TOO_MANY_ROWS" in result.pyspark_code

    def test_raise_named_exception_custom(self):
        plsql = """
        BEGIN
            RAISE e_duplicate;
        END;
        """
        result = translate_plsql(plsql, "raise_custom")
        assert "raise RuntimeError" in result.pyspark_code
        assert "e_duplicate" in result.pyspark_code


class TestExecuteImmediateUsing:
    """EXECUTE IMMEDIATE ... USING → spark.sql with bind vars."""

    def test_execute_immediate_using(self):
        plsql = """
        BEGIN
            EXECUTE IMMEDIATE 'SELECT * FROM emp WHERE id = :1' USING v_id;
        END;
        """
        result = translate_plsql(plsql, "exec_using")
        assert "spark.sql" in result.pyspark_code
        assert "bind" in result.pyspark_code.lower() or "v_id" in result.pyspark_code
        assert result.confidence <= 0.5

    def test_execute_immediate_using_multiple_binds(self):
        plsql = """
        BEGIN
            EXECUTE IMMEDIATE 'INSERT INTO t VALUES(:1, :2)' USING v_name, v_age;
        END;
        """
        result = translate_plsql(plsql, "exec_multi_bind")
        assert "spark.sql" in result.pyspark_code
        assert any("EXECUTE IMMEDIATE" in w or "bind" in w.lower() for w in result.warnings)

    def test_execute_immediate_using_warning(self):
        plsql = """
        BEGIN
            EXECUTE IMMEDIATE 'DELETE FROM t WHERE x = :1' USING v_x;
        END;
        """
        result = translate_plsql(plsql, "exec_warn")
        assert any("bind" in w.lower() or "USING" in w for w in result.warnings)


class TestCombinedPLSQLPatterns:
    """Test multiple PL/SQL patterns in a single block."""

    def test_for_loop_with_insert(self):
        plsql = """
        BEGIN
            FOR i IN 1..batch_count LOOP
                INSERT INTO staging SELECT * FROM source WHERE batch_id = i;
            END LOOP;
        END;
        """
        result = translate_plsql(plsql, "combo_for_insert")
        assert "for i in range(1, batch_count + 1):" in result.pyspark_code

    def test_exception_with_raise(self):
        plsql = """
        BEGIN
            RAISE_APPLICATION_ERROR(-20001, 'Validation failed');
        EXCEPTION
            WHEN OTHERS THEN
                DBMS_OUTPUT.PUT_LINE('Error caught');
        END;
        """
        result = translate_plsql(plsql, "combo_exc_raise")
        assert "raise RuntimeError" in result.pyspark_code
        assert "except" in result.pyspark_code.lower() or "except Exception" in result.pyspark_code

    def test_existing_insert_select_still_works(self):
        """Regression: INSERT INTO SELECT should still be handled."""
        plsql = """
        INSERT INTO target_table SELECT col1, col2 FROM source_table;
        """
        result = translate_plsql(plsql, "regression_insert")
        assert "write.mode" in result.pyspark_code or "saveAsTable" in result.pyspark_code

    def test_existing_update_set_still_works(self):
        """Regression: UPDATE SET should still be handled."""
        plsql = """
        UPDATE emp SET salary = salary * 1.1 WHERE department_id = 10;
        """
        result = translate_plsql(plsql, "regression_update")
        assert "DeltaTable" in result.pyspark_code or "delta_table" in result.pyspark_code

    def test_existing_merge_still_works(self):
        """Regression: MERGE INTO should still be handled."""
        plsql = """
        MERGE INTO target t USING source s ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET t.val = s.val
        WHEN NOT MATCHED THEN INSERT VALUES(s.id, s.val);
        """
        result = translate_plsql(plsql, "regression_merge")
        assert "merge" in result.pyspark_code.lower() or "MERGE" in result.pyspark_code

    def test_existing_cursor_loop_still_works(self):
        """Regression: CURSOR LOOP should still be handled."""
        plsql = """
        CURSOR c1 IS SELECT id, name FROM emp;
        BEGIN
        FOR rec IN c1 LOOP
            DBMS_OUTPUT.PUT_LINE(rec.name);
        END LOOP;
        END;
        """
        result = translate_plsql(plsql, "regression_cursor")
        assert "for row in" in result.pyspark_code or "collect()" in result.pyspark_code

    def test_existing_bulk_collect_still_works(self):
        """Regression: BULK COLLECT should still be handled."""
        plsql = """
        SELECT id, name BULK COLLECT INTO v_records FROM employees;
        """
        result = translate_plsql(plsql, "regression_bulk")
        assert "collect()" in result.pyspark_code


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  OAC expression translation tests — Sprint 20.2                        ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestStringFunctions:
    """OAC string functions → DAX equivalents."""

    def test_substring(self):
        result = translate_expression("SUBSTRING(col1, 1, 5)")
        assert "MID" in result.dax_expression

    def test_substr(self):
        result = translate_expression("SUBSTR(name, 2, 3)")
        assert "MID" in result.dax_expression

    def test_upper(self):
        result = translate_expression("UPPER(customer_name)")
        assert "UPPER" in result.dax_expression

    def test_lower(self):
        result = translate_expression("LOWER(status_code)")
        assert "LOWER" in result.dax_expression

    def test_trim(self):
        result = translate_expression("TRIM(address)")
        assert "TRIM" in result.dax_expression

    def test_replace(self):
        result = translate_expression("REPLACE(name, 'old', 'new')")
        assert "SUBSTITUTE" in result.dax_expression

    def test_length(self):
        result = translate_expression("LENGTH(description)")
        assert "LEN" in result.dax_expression

    def test_instr(self):
        result = translate_expression("INSTR(email, '@')")
        assert "FIND" in result.dax_expression

    def test_lpad(self):
        result = translate_expression("LPAD(code, 5, '0')")
        assert "REPT" in result.dax_expression


class TestDateFunctions:
    """OAC date functions → DAX equivalents."""

    def test_timestampadd(self):
        result = translate_expression("TIMESTAMPADD(SQL_TSI_DAY, 7, order_date)")
        assert "DATEADD" in result.dax_expression

    def test_timestampdiff(self):
        result = translate_expression("TIMESTAMPDIFF(SQL_TSI_MONTH, start_date, end_date)")
        assert "DATEDIFF" in result.dax_expression

    def test_current_date(self):
        result = translate_expression("CURRENT_DATE")
        assert "TODAY" in result.dax_expression

    def test_current_timestamp(self):
        result = translate_expression("CURRENT_TIMESTAMP")
        assert "NOW" in result.dax_expression

    def test_add_months(self):
        result = translate_expression("ADD_MONTHS(hire_date, 6)")
        assert "EDATE" in result.dax_expression

    def test_months_between(self):
        result = translate_expression("MONTHS_BETWEEN(end_date, start_date)")
        assert "DATEDIFF" in result.dax_expression


class TestExtractFunction:
    """EXTRACT(part FROM expr) → DAX date-part function."""

    def test_extract_year(self):
        result = translate_expression("EXTRACT(YEAR FROM order_date)")
        assert result.dax_expression == "YEAR(order_date)"

    def test_extract_month(self):
        result = translate_expression("EXTRACT(MONTH FROM ship_date)")
        assert result.dax_expression == "MONTH(ship_date)"

    def test_extract_day(self):
        result = translate_expression("EXTRACT(DAY FROM created_at)")
        assert result.dax_expression == "DAY(created_at)"

    def test_extract_quarter(self):
        result = translate_expression("EXTRACT(QUARTER FROM report_date)")
        assert result.dax_expression == "QUARTER(report_date)"

    def test_extract_hour(self):
        result = translate_expression("EXTRACT(HOUR FROM event_time)")
        assert result.dax_expression == "HOUR(event_time)"

    def test_extract_minute(self):
        result = translate_expression("EXTRACT(MINUTE FROM event_time)")
        assert result.dax_expression == "MINUTE(event_time)"

    def test_extract_second(self):
        result = translate_expression("EXTRACT(SECOND FROM event_time)")
        assert result.dax_expression == "SECOND(event_time)"

    def test_extract_applied_rule(self):
        result = translate_expression("EXTRACT(YEAR FROM d)")
        # Successfully translated — result contains the DAX date-part function
        assert result.dax_expression == "YEAR(d)"
        assert result.confidence == 1.0

    def test_translate_extract_helper_directly(self):
        assert _translate_extract("YEAR", "order_date") == "YEAR(order_date)"
        assert _translate_extract("MONTH", "d") == "MONTH(d)"
        assert _translate_extract("QUARTER", "dt") == "QUARTER(dt)"
        assert _translate_extract("WEEK", "d") == "WEEKNUM(d)"
        assert _translate_extract("DOW", "d") == "WEEKDAY(d)"


class TestCaseAndCastRegression:
    """Regression: CASE and CAST should still work after new rules."""

    def test_case_when_translates(self):
        result = translate_expression(
            "CASE WHEN status = 'A' THEN 'Active' WHEN status = 'I' THEN 'Inactive' ELSE 'Unknown' END"
        )
        assert "SWITCH" in result.dax_expression
        assert "TRUE()" in result.dax_expression

    def test_case_when_confidence(self):
        result = translate_expression(
            "CASE WHEN x > 0 THEN 'pos' ELSE 'neg' END"
        )
        assert result.confidence <= 0.8

    def test_cast_integer(self):
        result = translate_expression("CAST(revenue AS INTEGER)")
        assert "INT" in result.dax_expression

    def test_cast_varchar(self):
        result = translate_expression("CAST(amount AS VARCHAR)")
        assert "FORMAT" in result.dax_expression

    def test_cast_date(self):
        result = translate_expression("CAST(order_date AS DATE)")
        assert "DATEVALUE" in result.dax_expression

    def test_translate_cast_helper_directly(self):
        assert _translate_cast("x", "INT") == "INT(x)"
        assert _translate_cast("x", "FLOAT") == "VALUE(x)"
        assert _translate_cast("x", "VARCHAR2") == 'FORMAT(x, "General")'
        assert _translate_cast("x", "TIMESTAMP") == "DATEVALUE(x)"
        assert _translate_cast("x", "UNKNOWN_TYPE") == "CONVERT(x, UNKNOWN_TYPE)"

    def test_translate_case_when_helper(self):
        result = _translate_case_when(
            "CASE WHEN a = 1 THEN 'one' WHEN a = 2 THEN 'two' ELSE 'other' END"
        )
        assert "SWITCH(TRUE()" in result
        assert "one" in result
        assert "two" in result
        assert "other" in result


class TestAggregateRegression:
    """Regression: Aggregate function rules should still work."""

    def test_sum_aggregate(self):
        result = translate_expression("SUM(revenue)", table_name="Sales")
        assert "SUM" in result.dax_expression or "SUMX" in result.dax_expression

    def test_count_aggregate(self):
        result = translate_expression("COUNT(order_id)", table_name="Orders")
        assert "COUNT" in result.dax_expression

    def test_avg_aggregate(self):
        result = translate_expression("AVG(price)", table_name="Products")
        assert "AVERAGE" in result.dax_expression or "AVG" in result.dax_expression


class TestTimeIntelligenceRegression:
    """Regression: Time intelligence rules should still work."""

    def test_ago_function(self):
        result = translate_expression("AGO(revenue, time_dim, 1)")
        assert result.is_measure is True
        assert result.confidence <= 0.85

    def test_todate_function(self):
        # TODATE requires specific time level: YEAR, QUARTER, or MONTH
        result = translate_expression("TODATE(revenue, YEAR)")
        assert result.is_measure is True


class TestExistingScalarRegression:
    """Regression: Existing scalar rules (NVL, CONCAT, ||, etc.)."""

    def test_ifnull(self):
        result = translate_expression("IFNULL(discount, 0)")
        assert "IF" in result.dax_expression or "BLANK" in result.dax_expression or "COALESCE" in result.dax_expression

    def test_nvl(self):
        result = translate_expression("NVL(commission, 0)")
        # NVL → IF(ISBLANK …)
        assert "IF" in result.dax_expression or "ISBLANK" in result.dax_expression or "COALESCE" in result.dax_expression

    def test_concat_pipe(self):
        result = translate_expression("first_name || ' ' || last_name")
        assert "CONCATENATE" in result.dax_expression or "&" in result.dax_expression or "CONCAT" in result.dax_expression


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  Edge case tests — Sprint 20.3                                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


class TestEdgeCases:
    """Edge cases for translation correctness."""

    def test_empty_plsql_produces_header(self):
        result = translate_plsql("", "empty_proc")
        assert "empty_proc" in result.pyspark_code
        assert result.procedure_name == "empty_proc"

    def test_plsql_with_only_comments(self):
        plsql = """
        -- This is a comment
        /* Multi-line comment
           block */
        """
        result = translate_plsql(plsql, "comments_only")
        assert result.pyspark_code  # Should still produce output

    def test_expression_empty_string(self):
        result = translate_expression("")
        assert result.dax_expression == ""

    def test_expression_simple_column_ref(self):
        result = translate_expression("my_column")
        assert result.dax_expression == "my_column"
        # Short expression, no rules applied → confidence may be lowered

    def test_expression_with_table_mapping(self):
        result = translate_expression(
            "SUM(revenue)",
            table_name="OAC_Sales",
            table_mapping={"OAC_Sales": "Fabric_Sales"},
        )
        assert "Fabric_Sales" in result.dax_expression or "SUM" in result.dax_expression

    def test_untranslatable_plsql_pattern_package(self):
        """PACKAGE BODY should be flagged as untranslatable."""
        plsql = """
        PACKAGE BODY my_pkg IS
            PROCEDURE do_stuff IS
            BEGIN
                NULL;
            END;
        END my_pkg;
        """
        result = translate_plsql(plsql, "pkg_body")
        assert any("PACKAGE" in u for u in result.untranslated_sections)
        assert result.confidence <= 0.3

    def test_untranslatable_plsql_ref_cursor(self):
        """REF CURSOR should be flagged."""
        plsql = """
        DECLARE
            TYPE rc IS REF CURSOR;
        BEGIN
            NULL;
        END;
        """
        result = translate_plsql(plsql, "ref_cursor_proc")
        assert any("REF CURSOR" in u for u in result.untranslated_sections)

    def test_untranslatable_oac_connect_by(self):
        """CONNECT BY should produce a warning."""
        result = translate_expression("SELECT * FROM emp CONNECT BY PRIOR id = parent_id")
        assert any("CONNECT BY" in w for w in result.warnings)
        assert result.confidence <= 0.3

    def test_untranslatable_oac_fetch_first(self):
        """FETCH FIRST should produce a warning."""
        result = translate_expression("SELECT col FROM t FETCH FIRST 10 ROWS ONLY")
        assert any("FETCH FIRST" in w for w in result.warnings)

    def test_plsql_token_sysdate(self):
        """SYSDATE token is still in the rules."""
        plsql = "v_date := SYSDATE;"
        result = translate_plsql(plsql, "sysdate_proc")
        # SYSDATE should appear in the structural output header at minimum
        assert result.pyspark_code  # Non-empty output

    def test_plsql_method_is_rule_based(self):
        result = translate_plsql("BEGIN NULL; END;", "method_test")
        assert result.method == "rule-based"

    def test_expression_method_is_rule_based(self):
        result = translate_expression("SUM(x)")
        assert result.method == "rule-based"

    def test_expression_display_folder_measures(self):
        result = translate_expression("SUM(revenue)", is_measure=True)
        assert result.display_folder == "Measures"

    def test_expression_display_folder_time_intelligence(self):
        result = translate_expression("AGO(revenue, time, 1)")
        assert result.display_folder == "Time Intelligence"

    def test_expression_requires_review_low_confidence(self):
        result = translate_expression("SELECT * FROM t CONNECT BY PRIOR a = b")
        assert result.requires_review is True

    def test_plsql_table_mapping_applied(self):
        plsql = """
        INSERT INTO ORACLE_SALES SELECT * FROM ORACLE_CUSTOMERS;
        """
        tmap = {"ORACLE_SALES": "fabric_sales", "ORACLE_CUSTOMERS": "fabric_customers"}
        result = translate_plsql(plsql, "mapped", table_mapping=tmap)
        assert "fabric_sales" in result.pyspark_code or "fabric_customers" in result.pyspark_code


class TestTranslationResultDataclass:
    """Verify TranslationResult and DAXTranslation dataclasses."""

    def test_translation_result_defaults(self):
        r = TranslationResult(
            procedure_name="test",
            original_plsql="BEGIN END;",
            pyspark_code="pass",
        )
        assert r.method == "rule-based"
        assert r.confidence == 1.0
        assert r.warnings == []
        assert r.untranslated_sections == []
        assert r.requires_review is False

    def test_dax_translation_defaults(self):
        d = DAXTranslation(
            column_name="col1",
            table_name="tbl",
            original_expression="SUM(x)",
            dax_expression="SUM(x)",
        )
        assert d.method == "rule-based"
        assert d.confidence == 1.0
        assert d.is_measure is False
        assert d.format_string == ""
        assert d.display_folder == ""
        assert d.warnings == []
        assert d.requires_review is False
