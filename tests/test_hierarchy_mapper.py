"""Tests for hierarchy mapper — RPD hierarchies → TMDL hierarchies."""

from __future__ import annotations

import pytest

from src.agents.semantic.hierarchy_mapper import (
    TMDLHierarchy,
    TMDLLevel,
    _detect_date_hierarchy,
    hierarchy_to_tmdl,
    map_all_hierarchies,
    map_hierarchy,
)
from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    Hierarchy,
    HierarchyLevel,
    LogicalColumn,
    LogicalTable,
    SemanticModelIR,
)


# ---------------------------------------------------------------------------
# map_hierarchy
# ---------------------------------------------------------------------------


class TestMapHierarchy:
    def test_basic_mapping(self):
        h = Hierarchy(
            name="Geography",
            table_name="Sales",
            levels=[
                HierarchyLevel(name="Country", column_name="Country", ordinal=0),
                HierarchyLevel(name="Region", column_name="Region", ordinal=1),
                HierarchyLevel(name="City", column_name="City", ordinal=2),
            ],
        )
        table = LogicalTable(
            name="Sales",
            columns=[
                LogicalColumn(name="Country"),
                LogicalColumn(name="Region"),
                LogicalColumn(name="City"),
            ],
        )
        result = map_hierarchy(h, table)
        assert result.name == "Geography"
        assert len(result.levels) == 3
        assert result.requires_review is False

    def test_missing_column_flagged(self):
        h = Hierarchy(
            name="Geo",
            table_name="T",
            levels=[HierarchyLevel(name="State", column_name="State", ordinal=0)],
        )
        table = LogicalTable(name="T", columns=[LogicalColumn(name="Country")])
        result = map_hierarchy(h, table)
        assert result.requires_review is True
        assert any("State" in w for w in result.warnings)

    def test_case_insensitive_column_match(self):
        h = Hierarchy(
            name="H",
            table_name="T",
            levels=[HierarchyLevel(name="Country", column_name="country", ordinal=0)],
        )
        table = LogicalTable(name="T", columns=[LogicalColumn(name="Country")])
        result = map_hierarchy(h, table)
        assert result.requires_review is False
        assert result.levels[0].column_name == "Country"

    def test_single_level_warning(self):
        h = Hierarchy(
            name="H",
            table_name="T",
            levels=[HierarchyLevel(name="Level1", column_name="Col1", ordinal=0)],
        )
        result = map_hierarchy(h, table=None)
        assert any("Single-level" in w for w in result.warnings)

    def test_ordinals_resequenced(self):
        h = Hierarchy(
            name="H",
            table_name="T",
            levels=[
                HierarchyLevel(name="B", column_name="B", ordinal=5),
                HierarchyLevel(name="A", column_name="A", ordinal=2),
            ],
        )
        result = map_hierarchy(h, table=None)
        assert result.levels[0].ordinal == 0
        assert result.levels[1].ordinal == 1
        # Sorted by original ordinal (A=2 before B=5)
        assert result.levels[0].name == "A"


# ---------------------------------------------------------------------------
# Date hierarchy auto-detection
# ---------------------------------------------------------------------------


class TestDetectDateHierarchy:
    def test_detects_year_month_day(self):
        table = LogicalTable(
            name="Calendar",
            columns=[
                LogicalColumn(name="year"),
                LogicalColumn(name="month"),
                LogicalColumn(name="day"),
            ],
            is_date_table=True,
        )
        h = _detect_date_hierarchy(table)
        assert h is not None
        assert h.is_auto_generated is True
        level_names = [lv.name for lv in h.levels]
        assert "Year" in level_names
        assert "Month" in level_names
        assert "Day" in level_names

    def test_detects_year_quarter_month(self):
        table = LogicalTable(
            name="DateDim",
            columns=[
                LogicalColumn(name="year"),
                LogicalColumn(name="quarter"),
                LogicalColumn(name="month"),
            ],
            is_date_table=True,
        )
        h = _detect_date_hierarchy(table)
        assert h is not None
        assert len(h.levels) == 3

    def test_insufficient_columns(self):
        table = LogicalTable(
            name="DateDim",
            columns=[LogicalColumn(name="year")],
            is_date_table=True,
        )
        h = _detect_date_hierarchy(table)
        assert h is None


# ---------------------------------------------------------------------------
# map_all_hierarchies
# ---------------------------------------------------------------------------


class TestMapAllHierarchies:
    def test_explicit_and_auto_generated(self):
        sales = LogicalTable(
            name="Sales",
            columns=[LogicalColumn(name="Country"), LogicalColumn(name="Region")],
            hierarchies=[
                Hierarchy(
                    name="Geo",
                    table_name="Sales",
                    levels=[
                        HierarchyLevel(name="Country", column_name="Country", ordinal=0),
                        HierarchyLevel(name="Region", column_name="Region", ordinal=1),
                    ],
                ),
            ],
        )
        date = LogicalTable(
            name="Date",
            columns=[
                LogicalColumn(name="year"),
                LogicalColumn(name="month"),
                LogicalColumn(name="day"),
            ],
            is_date_table=True,
        )
        ir = SemanticModelIR(tables=[sales, date])
        result = map_all_hierarchies(ir)
        assert len(result) == 2  # 1 explicit + 1 auto-generated
        auto = [h for h in result if h.is_auto_generated]
        assert len(auto) == 1
        assert auto[0].table_name == "Date"


# ---------------------------------------------------------------------------
# TMDL rendering
# ---------------------------------------------------------------------------


class TestHierarchyToTMDL:
    def test_renders_hierarchy(self):
        h = TMDLHierarchy(
            name="Geography",
            table_name="Sales",
            levels=[
                TMDLLevel(name="Country", column_name="Country", ordinal=0),
                TMDLLevel(name="City", column_name="City", ordinal=1),
            ],
        )
        tmdl = hierarchy_to_tmdl(h)
        assert "hierarchy Geography" in tmdl
        assert "level Country" in tmdl
        assert "column: Country" in tmdl
        assert "level City" in tmdl
