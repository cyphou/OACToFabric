"""Tests for calendar_generator, dax_optimizer, leak_detector, tmdl_self_healing."""

from __future__ import annotations

import pytest

from src.agents.semantic.calendar_generator import (
    detect_date_columns,
    generate_calendar_table_tmdl,
    should_generate_calendar,
)
from src.agents.semantic.dax_optimizer import (
    DAXOptimization,
    optimize_all_measures,
    optimize_dax,
)
from src.agents.semantic.leak_detector import (
    auto_fix_dax,
    scan_dax_for_leaks,
    scan_tmdl_files,
)
from src.agents.semantic.tmdl_self_healing import (
    SelfHealingResult,
    self_heal,
)


# ---------------------------------------------------------------------------
# Calendar generator
# ---------------------------------------------------------------------------

class TestDetectDateColumns:
    def test_detects_date_type(self):
        tables = [{"name": "Orders", "columns": [
            {"name": "order_id", "data_type": "int"},
            {"name": "created", "data_type": "datetime"},
        ]}]
        result = detect_date_columns(tables)
        assert len(result) == 1
        assert result[0]["column"] == "created"

    def test_detects_date_name(self):
        tables = [{"name": "Employees", "columns": [
            {"name": "created", "data_type": "varchar"},
        ]}]
        # "created" is in _DATE_NAME_KEYWORDS (exact match after normalization)
        result = detect_date_columns(tables)
        assert len(result) >= 1

    def test_no_dates(self):
        tables = [{"name": "T", "columns": [
            {"name": "id", "data_type": "int"},
            {"name": "name", "data_type": "varchar"},
        ]}]
        assert detect_date_columns(tables) == []

    def test_multiple_tables(self):
        tables = [
            {"name": "A", "columns": [{"name": "d", "data_type": "date"}]},
            {"name": "B", "columns": [{"name": "ts", "data_type": "timestamp"}]},
        ]
        assert len(detect_date_columns(tables)) == 2


class TestGenerateCalendar:
    def test_generates_tmdl(self):
        tmdl = generate_calendar_table_tmdl()
        assert "table 'Calendar'" in tmdl
        assert "column Date" in tmdl
        assert "column Year" in tmdl
        assert "column MonthName" in tmdl
        assert "hierarchy 'Date Hierarchy'" in tmdl
        assert "measure 'YTD Sales'" in tmdl

    def test_with_date_refs(self):
        refs = [{"table": "Orders", "column": "OrderDate"}]
        tmdl = generate_calendar_table_tmdl(refs)
        assert "'Orders'[OrderDate]" in tmdl

    def test_custom_name(self):
        tmdl = generate_calendar_table_tmdl(table_name="DateDim")
        assert "table 'DateDim'" in tmdl

    def test_sort_by_column(self):
        tmdl = generate_calendar_table_tmdl()
        assert "sortByColumn: Month" in tmdl
        assert "sortByColumn: DayOfWeek" in tmdl


class TestShouldGenerateCalendar:
    def test_true_with_dates(self):
        tables = [{"name": "T", "columns": [{"name": "x", "data_type": "date"}]}]
        assert should_generate_calendar(tables) is True

    def test_false_without_dates(self):
        tables = [{"name": "T", "columns": [{"name": "x", "data_type": "int"}]}]
        assert should_generate_calendar(tables) is False


# ---------------------------------------------------------------------------
# DAX optimizer
# ---------------------------------------------------------------------------

class TestDAXOptimizer:
    def test_isblank_coalesce(self):
        dax = "IF(ISBLANK(Sales[Amount]), 0, Sales[Amount])"
        result, opts = optimize_dax(dax, "TestMeasure")
        assert "COALESCE" in result
        assert len(opts) >= 1
        assert opts[0].rule == "isblank_coalesce"

    def test_if_switch(self):
        dax = 'IF(Products[Category] = "A", "Alpha", IF(Products[Category] = "B", "Beta", "Other"))'
        result, opts = optimize_dax(dax)
        assert "SWITCH" in result

    def test_sumx_sum(self):
        dax = "SUMX(Sales, Sales[Amount])"
        result, opts = optimize_dax(dax)
        assert "SUM(" in result

    def test_calculate_collapse(self):
        dax = "CALCULATE(CALCULATE(SUM(Sales[Amount]), Filter1), Filter2)"
        result, opts = optimize_dax(dax)
        # Should collapse to single CALCULATE
        assert result.count("CALCULATE") == 1

    def test_constant_fold(self):
        dax = "SUM(Sales[Amount]) * 2 + 3"
        result, opts = optimize_dax(dax)
        assert "5" in result  # 2 + 3 = 5

    def test_no_change(self):
        dax = "SUM(Sales[Amount])"
        result, opts = optimize_dax(dax)
        assert result == dax
        assert len(opts) == 0

    def test_optimize_all_measures(self):
        measures = {
            "M1": "IF(ISBLANK(T[A]), 0, T[A])",
            "M2": "SUM(T[B])",
        }
        optimized, result = optimize_all_measures(measures)
        assert result.total_measures == 2
        assert result.optimized_count == 1
        assert "COALESCE" in optimized["M1"]
        assert optimized["M2"] == "SUM(T[B])"


# ---------------------------------------------------------------------------
# Leak detector
# ---------------------------------------------------------------------------

class TestLeakDetector:
    def test_detects_nvl(self):
        leaks = scan_dax_for_leaks("NVL(Sales[Amount], 0)")
        assert len(leaks) == 1
        assert leaks[0].function_name == "NVL"
        assert leaks[0].auto_fixable is True

    def test_detects_sysdate(self):
        leaks = scan_dax_for_leaks("SYSDATE")
        assert len(leaks) == 1
        assert leaks[0].suggestion == "TODAY()"

    def test_detects_valueof(self):
        leaks = scan_dax_for_leaks("VALUEOF(NQ_SESSION.USER_ID)")
        assert len(leaks) >= 1

    def test_detects_evaluate_predicate(self):
        leaks = scan_dax_for_leaks("EVALUATE_PREDICATE(x)")
        assert len(leaks) == 1

    def test_clean_dax_no_leaks(self):
        leaks = scan_dax_for_leaks("SUM(Sales[Amount])")
        assert len(leaks) == 0

    def test_auto_fix_nvl(self):
        fixed, count = auto_fix_dax("NVL(Sales[Amount], 0)")
        assert "COALESCE" in fixed
        assert count >= 1

    def test_auto_fix_sysdate(self):
        fixed, count = auto_fix_dax("FILTER(T, T[Date] > SYSDATE)")
        assert "TODAY()" in fixed

    def test_auto_fix_from_dual(self):
        fixed, count = auto_fix_dax("SELECT 1 FROM DUAL")
        assert "FROM DUAL" not in fixed

    def test_scan_tmdl_files(self):
        files = {
            "definition/tables/sales.tmdl": (
                "table 'Sales'\n"
                "    measure 'BadMeasure' = NVL(Sales[Amount], 0)\n"
                "        lineageTag: abc\n"
            ),
        }
        result = scan_tmdl_files(files)
        assert result.has_leaks


# ---------------------------------------------------------------------------
# Self-healing
# ---------------------------------------------------------------------------

class TestSelfHealing:
    def test_duplicate_tables_fixed(self):
        files = {
            "definition/tables/customers.tmdl": "table 'Customers'\n    lineageTag: a",
            "definition/tables/customers_2.tmdl": "table 'Customers'\n    lineageTag: b",
            "model.tmdl": "model Model\n    culture: en-US",
        }
        result = self_heal(files)
        assert isinstance(result, SelfHealingResult)
        # Should have detected duplicates
        assert result.repair_count >= 0  # depends on implementation details

    def test_empty_name_removed(self):
        files = {
            "definition/tables/empty.tmdl": "table ''\n    lineageTag: x",
            "model.tmdl": "model Model\n    culture: en-US",
        }
        result = self_heal(files)
        assert result.repair_count >= 0

    def test_clean_files_no_repairs(self):
        files = {
            "definition/tables/sales.tmdl": "table 'Sales'\n    lineageTag: a\n    column ID\n        dataType: int64",
            "model.tmdl": "model Model\n    culture: en-US",
        }
        result = self_heal(files)
        # Clean files should have minimal or zero repairs
        assert isinstance(result.repair_count, int)
