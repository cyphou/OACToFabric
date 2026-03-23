"""Tests for RPD model parser — inventory → SemanticModelIR."""

from __future__ import annotations

import pytest

from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    Hierarchy,
    HierarchyLevel,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
    _classify_column,
    _detect_aggregation,
    _is_date_table,
    parse_inventory_to_ir,
)
from src.core.models import AssetType, Dependency, Inventory, InventoryItem


# ---------------------------------------------------------------------------
# Column classification
# ---------------------------------------------------------------------------


class TestClassifyColumn:
    def test_direct_column(self):
        assert _classify_column({"name": "id"}) == ColumnKind.DIRECT

    def test_empty_expression(self):
        assert _classify_column({"name": "x", "expression": ""}) == ColumnKind.DIRECT

    def test_sum_is_measure(self):
        assert _classify_column({"expression": "SUM(revenue)"}) == ColumnKind.MEASURE

    def test_count_is_measure(self):
        assert _classify_column({"expression": "COUNT(orders)"}) == ColumnKind.MEASURE

    def test_avg_is_measure(self):
        assert _classify_column({"expression": "AVG(price)"}) == ColumnKind.MEASURE

    def test_countdistinct_is_measure(self):
        assert _classify_column({"expression": "COUNTDISTINCT(customer_id)"}) == ColumnKind.MEASURE

    def test_ago_is_measure(self):
        assert _classify_column({"expression": "AGO(revenue, year, 1)"}) == ColumnKind.MEASURE

    def test_todate_is_measure(self):
        assert _classify_column({"expression": "TODATE(sales, year)"}) == ColumnKind.MEASURE

    def test_non_agg_expression_is_calculated(self):
        assert _classify_column({"expression": "col_a + col_b"}) == ColumnKind.CALCULATED

    def test_case_when_is_calculated(self):
        assert _classify_column({"expression": "CASE WHEN x=1 THEN 'A' ELSE 'B' END"}) == ColumnKind.CALCULATED


class TestDetectAggregation:
    def test_sum(self):
        assert _detect_aggregation("SUM(amount)") == "SUM"

    def test_count(self):
        assert _detect_aggregation("COUNT(id)") == "COUNT"

    def test_no_aggregation(self):
        assert _detect_aggregation("col + 1") == ""


class TestIsDateTable:
    def test_date_in_name(self):
        assert _is_date_table("Date_Dim", []) is True

    def test_calendar_in_name(self):
        assert _is_date_table("Calendar", []) is True

    def test_columns_with_date_fields(self):
        cols = [{"name": "Year"}, {"name": "Month"}, {"name": "Day"}, {"name": "ID"}]
        assert _is_date_table("Periods", cols) is True

    def test_not_a_date_table(self):
        assert _is_date_table("Sales", [{"name": "Amount"}]) is False


# ---------------------------------------------------------------------------
# Inventory → SemanticModelIR
# ---------------------------------------------------------------------------


class TestParseInventoryToIR:
    def _make_inventory(self) -> Inventory:
        return Inventory(items=[
            InventoryItem(
                id="logicalTable__sales",
                asset_type=AssetType.LOGICAL_TABLE,
                source_path="/logical/Sales",
                name="Sales",
                metadata={
                    "columns": [
                        {"name": "OrderID", "data_type": "NUMBER"},
                        {"name": "Revenue", "data_type": "DECIMAL"},
                        {"name": "TotalRevenue", "expression": "SUM(Revenue)"},
                    ],
                    "hierarchies": [
                        {"name": "Geography", "levels": ["Country", "Region", "City"]},
                    ],
                },
                dependencies=[
                    Dependency(
                        source_id="logicalTable__sales",
                        target_id="physicalTable__orders",
                        dependency_type="maps_to_physical",
                    ),
                ],
            ),
            InventoryItem(
                id="logicalTable__date",
                asset_type=AssetType.LOGICAL_TABLE,
                source_path="/logical/Date",
                name="Date",
                metadata={
                    "columns": [
                        {"name": "Year"}, {"name": "Quarter"}, {"name": "Month"}, {"name": "Day"},
                    ],
                },
            ),
            InventoryItem(
                id="subjectArea__sales_analysis",
                asset_type=AssetType.SUBJECT_AREA,
                source_path="/presentation/Sales Analysis",
                name="Sales Analysis",
                metadata={
                    "tables": [
                        {"name": "Sales", "columns": ["OrderID", "Revenue"]},
                    ],
                },
            ),
        ])

    def test_tables_parsed(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        assert len(ir.tables) == 2
        assert ir.tables[0].name == "Sales"

    def test_columns_classified(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        sales = ir.table_by_name("Sales")
        assert sales is not None
        assert len(sales.direct_columns) == 2
        assert len(sales.measures) == 1
        assert sales.measures[0].name == "TotalRevenue"

    def test_hierarchy_parsed(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        sales = ir.table_by_name("Sales")
        assert len(sales.hierarchies) == 1
        assert sales.hierarchies[0].name == "Geography"
        assert len(sales.hierarchies[0].levels) == 3

    def test_physical_sources(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        sales = ir.table_by_name("Sales")
        assert "physicalTable__orders" in sales.physical_sources

    def test_date_table_detected(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        date = ir.table_by_name("Date")
        assert date.is_date_table is True

    def test_subject_areas_parsed(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        assert len(ir.subject_areas) == 1
        assert ir.subject_areas[0].name == "Sales Analysis"
        assert "Sales" in ir.subject_areas[0].tables

    def test_table_by_name_not_found(self):
        ir = parse_inventory_to_ir(self._make_inventory())
        assert ir.table_by_name("NonExistent") is None


class TestLogicalTableProperties:
    def test_measures_property(self):
        t = LogicalTable(
            name="T",
            columns=[
                LogicalColumn(name="A", kind=ColumnKind.DIRECT),
                LogicalColumn(name="B", kind=ColumnKind.MEASURE),
                LogicalColumn(name="C", kind=ColumnKind.CALCULATED),
            ],
        )
        assert len(t.measures) == 1
        assert len(t.calculated_columns) == 1
        assert len(t.direct_columns) == 1
