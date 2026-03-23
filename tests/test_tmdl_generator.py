"""Tests for TMDL generator — end-to-end TMDL file generation."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    JoinCardinality,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    SemanticModelIR,
    SubjectArea,
    Hierarchy,
    HierarchyLevel,
)
from src.agents.semantic.tmdl_generator import (
    TMDLGenerationResult,
    generate_model_tmdl,
    generate_perspectives_tmdl,
    generate_relationships_tmdl,
    generate_table_tmdl,
    generate_tmdl,
    write_tmdl_to_disk,
)
from src.agents.semantic.hierarchy_mapper import TMDLHierarchy, TMDLLevel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ir() -> SemanticModelIR:
    return SemanticModelIR(
        model_name="TestModel",
        description="Test semantic model",
        tables=[
            LogicalTable(
                name="Sales",
                columns=[
                    LogicalColumn(name="OrderID", data_type="NUMBER", kind=ColumnKind.DIRECT, source_column="OrderID"),
                    LogicalColumn(name="Revenue", data_type="DECIMAL", kind=ColumnKind.DIRECT, source_column="Revenue"),
                    LogicalColumn(name="TotalRevenue", data_type="DECIMAL", kind=ColumnKind.MEASURE, expression="SUM(Revenue)", aggregation="SUM"),
                    LogicalColumn(name="DiscountedPrice", data_type="DECIMAL", kind=ColumnKind.CALCULATED, expression="price * 0.9"),
                ],
                hierarchies=[
                    Hierarchy(
                        name="Geography",
                        table_name="Sales",
                        levels=[
                            HierarchyLevel(name="Country", column_name="Country", ordinal=0),
                            HierarchyLevel(name="City", column_name="City", ordinal=1),
                        ],
                    ),
                ],
            ),
            LogicalTable(
                name="Products",
                columns=[
                    LogicalColumn(name="ProductID", data_type="NUMBER", kind=ColumnKind.DIRECT, source_column="ProductID"),
                    LogicalColumn(name="ProductName", data_type="VARCHAR", kind=ColumnKind.DIRECT, source_column="ProductName"),
                ],
            ),
        ],
        joins=[
            LogicalJoin(
                from_table="Sales",
                to_table="Products",
                from_column="ProductID",
                to_column="ProductID",
                cardinality=JoinCardinality.MANY_TO_ONE,
            ),
        ],
        subject_areas=[
            SubjectArea(
                name="Sales Analysis",
                tables=["Sales", "Products"],
                columns={"Sales": ["OrderID", "Revenue"], "Products": ["ProductName"]},
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Model-level TMDL
# ---------------------------------------------------------------------------


class TestGenerateModelTMDL:
    def test_model_header(self):
        ir = _make_ir()
        content = generate_model_tmdl(ir)
        assert "model TestModel" in content
        assert "culture: en-US" in content
        assert "powerBI_V3" in content


# ---------------------------------------------------------------------------
# Table TMDL
# ---------------------------------------------------------------------------


class TestGenerateTableTMDL:
    def test_table_with_columns(self):
        ir = _make_ir()
        table = ir.tables[0]
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "table Sales" in content
        assert "column OrderID" in content
        assert "column Revenue" in content
        assert "sourceColumn: OrderID" in content

    def test_table_with_measure(self):
        ir = _make_ir()
        table = ir.tables[0]
        tx = {"TotalRevenue": type("TX", (), {"dax_expression": "SUM('Sales'[Revenue])", "display_folder": "Measures"})()}
        content = generate_table_tmdl(table, [], tx, "TestLH")
        assert "measure 'TotalRevenue'" in content
        assert "SUM('Sales'[Revenue])" in content

    def test_table_with_hierarchy(self):
        ir = _make_ir()
        table = ir.tables[0]
        hierarchies = [
            TMDLHierarchy(
                name="Geography",
                table_name="Sales",
                levels=[
                    TMDLLevel(name="Country", column_name="Country", ordinal=0),
                    TMDLLevel(name="City", column_name="City", ordinal=1),
                ],
            ),
        ]
        content = generate_table_tmdl(table, hierarchies, {}, "TestLH")
        assert "hierarchy Geography" in content
        assert "level Country" in content

    def test_partition_expression(self):
        ir = _make_ir()
        table = ir.tables[0]
        content = generate_table_tmdl(table, [], {}, "MyLakehouse")
        assert "partition Sales = m" in content
        assert "MyLakehouse" in content


# ---------------------------------------------------------------------------
# Relationships TMDL
# ---------------------------------------------------------------------------


class TestGenerateRelationshipsTMDL:
    def test_relationship_rendered(self):
        joins = [
            LogicalJoin(
                from_table="Sales",
                to_table="Products",
                from_column="ProductID",
                to_column="ProductID",
                cardinality=JoinCardinality.MANY_TO_ONE,
            ),
        ]
        content = generate_relationships_tmdl(joins)
        assert "relationship" in content
        assert "fromTable: 'Sales'" in content
        assert "toTable: 'Products'" in content
        assert "fromColumn: ProductID" in content
        assert "fromCardinality: many" in content
        assert "toCardinality: one" in content

    def test_inactive_relationship(self):
        joins = [
            LogicalJoin(
                from_table="A",
                to_table="B",
                from_column="id",
                to_column="id",
                is_active=False,
            ),
        ]
        content = generate_relationships_tmdl(joins)
        assert "isActive: false" in content

    def test_full_join_bidirectional(self):
        joins = [
            LogicalJoin(
                from_table="A",
                to_table="B",
                from_column="id",
                to_column="id",
                join_type="full",
            ),
        ]
        content = generate_relationships_tmdl(joins)
        assert "bothDirections" in content


# ---------------------------------------------------------------------------
# Perspectives TMDL
# ---------------------------------------------------------------------------


class TestGeneratePerspectivesTMDL:
    def test_perspective_rendered(self):
        sa = [SubjectArea(name="Sales View", tables=["Sales"], columns={"Sales": ["Revenue"]})]
        content = generate_perspectives_tmdl(sa)
        assert "perspective 'Sales View'" in content
        assert "perspectiveTable 'Sales'" in content
        assert "perspectiveColumn Revenue" in content

    def test_empty_subject_areas(self):
        assert generate_perspectives_tmdl([]) == ""


# ---------------------------------------------------------------------------
# Full TMDL generation
# ---------------------------------------------------------------------------


class TestGenerateTMDL:
    def test_full_generation(self):
        ir = _make_ir()
        result = generate_tmdl(ir, lakehouse_name="TestLH")
        assert isinstance(result, TMDLGenerationResult)
        assert "model.tmdl" in result.files
        assert "definition/tables/Sales.tmdl" in result.files
        assert "definition/tables/Products.tmdl" in result.files
        assert "definition/relationships.tmdl" in result.files
        assert "definition/perspectives.tmdl" in result.files
        assert ".platform" in result.files
        assert result.table_count == 2
        assert result.relationship_count == 1

    def test_translation_log_populated(self):
        ir = _make_ir()
        result = generate_tmdl(ir)
        # Sales table has 1 measure + 1 calculated column with expressions
        assert len(result.translation_log) >= 1

    def test_platform_json_valid(self):
        ir = _make_ir()
        result = generate_tmdl(ir)
        import json
        platform = json.loads(result.files[".platform"])
        assert platform["metadata"]["type"] == "SemanticModel"


class TestWriteTMDLToDisk:
    def test_writes_files(self, tmp_path: Path):
        ir = _make_ir()
        result = generate_tmdl(ir)
        output = tmp_path / "semantic_model"
        write_tmdl_to_disk(result, output)

        assert (output / "model.tmdl").exists()
        assert (output / "definition" / "tables" / "Sales.tmdl").exists()
        assert (output / "definition" / "tables" / "Products.tmdl").exists()
        assert (output / ".platform").exists()

        # Check content is non-empty
        assert (output / "model.tmdl").stat().st_size > 0
