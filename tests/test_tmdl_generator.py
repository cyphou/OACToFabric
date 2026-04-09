"""Tests for TMDL generator — end-to-end TMDL file generation."""

from __future__ import annotations

import pytest
from pathlib import Path

from src.agents.semantic.rpd_model_parser import (
    CalculationGroup,
    CalculationItem,
    ColumnKind,
    JoinCardinality,
    LogicalColumn,
    LogicalJoin,
    LogicalTable,
    RefreshPolicy,
    SemanticModelIR,
    SubjectArea,
    Hierarchy,
    HierarchyLevel,
)
from src.agents.semantic.tmdl_generator import (
    TMDLGenerationResult,
    generate_culture_tmdl,
    generate_expressions_tmdl,
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
        assert "model Model" in content
        assert "culture: en-US" in content
        assert "powerBI_V3" in content
        assert "dataAccessOptions" in content
        assert "ref table Sales" in content
        assert "annotation PBI_QueryOrder" in content
        assert "ref expression ServerName" in content
        assert "ref expression DatabaseName" in content


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
        assert "measure TotalRevenue" in content
        assert "SUM('Sales'[Revenue])" in content

    def test_table_with_hierarchy(self):
        ir = _make_ir()
        table = ir.tables[0]
        # Add columns that the hierarchy levels reference
        table.columns.extend([
            LogicalColumn(name="Country", data_type="VARCHAR", kind=ColumnKind.DIRECT, source_column="Country"),
            LogicalColumn(name="City", data_type="VARCHAR", kind=ColumnKind.DIRECT, source_column="City"),
        ])
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
        assert "partition" in content
        assert "= m" in content
        assert "mode: import" in content


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
        assert "fromColumn: Sales.ProductID" in content
        assert "toColumn: Products.ProductID" in content
        assert "crossFilteringBehavior: oneDirection" in content

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
        assert "perspectiveTable Sales" in content
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
        assert "definition/model.tmdl" in result.files
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

        assert (output / "definition" / "model.tmdl").exists()
        assert (output / "definition" / "tables" / "Sales.tmdl").exists()
        assert (output / "definition" / "tables" / "Products.tmdl").exists()
        assert (output / ".platform").exists()

        # Check content is non-empty
        assert (output / "definition" / "model.tmdl").stat().st_size > 0


# ---------------------------------------------------------------------------
# Calculation Groups
# ---------------------------------------------------------------------------


class TestCalculationGroups:
    def test_calc_group_rendered(self):
        cg = CalculationGroup(
            precedence=10,
            items=[
                CalculationItem(name="YTD", expression="CALCULATE(SELECTEDMEASURE(), DATESYTD('Calendar'[Date]))", ordinal=0),
                CalculationItem(name="MTD", expression="CALCULATE(SELECTEDMEASURE(), DATESMTD('Calendar'[Date]))", ordinal=1),
            ],
        )
        table = LogicalTable(
            name="Time Intelligence",
            columns=[LogicalColumn(name="Name", data_type="VARCHAR", kind=ColumnKind.DIRECT, source_column="Name")],
            calculation_group=cg,
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "calculationGroup" in content
        assert "precedence: 10" in content
        assert "calculationItem YTD" in content
        assert "calculationItem MTD" in content
        assert "ordinal: 0" in content
        assert "ordinal: 1" in content
        assert "SELECTEDMEASURE()" in content

    def test_calc_group_partition_type(self):
        cg = CalculationGroup(items=[CalculationItem(name="Default")])
        table = LogicalTable(name="CalcTable", calculation_group=cg)
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "= calculationGroup" in content

    def test_model_with_calc_group_has_discourage(self):
        cg = CalculationGroup(items=[CalculationItem(name="YTD")])
        ir = SemanticModelIR(
            tables=[LogicalTable(name="TI", calculation_group=cg)],
        )
        content = generate_model_tmdl(ir)
        assert "discourageImplicitMeasures" in content


# ---------------------------------------------------------------------------
# Incremental Refresh
# ---------------------------------------------------------------------------


class TestIncrementalRefresh:
    def test_refresh_policy_rendered(self):
        policy = RefreshPolicy(
            incremental_granularity="Day",
            incremental_periods=3,
            rolling_window_granularity="Month",
            rolling_window_periods=12,
        )
        table = LogicalTable(
            name="FactSales",
            columns=[LogicalColumn(name="Amount", data_type="DECIMAL", kind=ColumnKind.DIRECT)],
            refresh_policy=policy,
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "refreshPolicy" in content
        assert "incrementalGranularity: Day" in content
        assert "incrementalPeriods: 3" in content
        assert "rollingWindowGranularity: Month" in content
        assert "rollingWindowPeriods: 12" in content


# ---------------------------------------------------------------------------
# SortByColumn
# ---------------------------------------------------------------------------


class TestSortByColumn:
    def test_explicit_sort_by(self):
        table = LogicalTable(
            name="Calendar",
            columns=[
                LogicalColumn(name="Month Name", data_type="VARCHAR", kind=ColumnKind.DIRECT, sort_by_column="Month Number"),
                LogicalColumn(name="Month Number", data_type="INTEGER", kind=ColumnKind.DIRECT),
            ],
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "sortByColumn: 'Month Number'" in content

    def test_auto_detect_sort_by(self):
        table = LogicalTable(
            name="Calendar",
            columns=[
                LogicalColumn(name="Month Name", data_type="VARCHAR", kind=ColumnKind.DIRECT),
                LogicalColumn(name="Month Number", data_type="INTEGER", kind=ColumnKind.DIRECT),
            ],
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "sortByColumn:" in content


# ---------------------------------------------------------------------------
# Copilot Annotations
# ---------------------------------------------------------------------------


class TestCopilotAnnotations:
    def test_table_description_annotation(self):
        table = LogicalTable(
            name="Sales",
            description="Sales fact table with order details",
            columns=[LogicalColumn(name="Amount", data_type="DECIMAL", kind=ColumnKind.DIRECT)],
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "Copilot_TableDescription = Sales fact table with order details" in content

    def test_date_table_annotation(self):
        table = LogicalTable(
            name="Calendar",
            columns=[LogicalColumn(name="Date", data_type="DATE", kind=ColumnKind.DIRECT)],
            is_date_table=True,
        )
        content = generate_table_tmdl(table, [], {}, "TestLH")
        assert "Copilot_DateTable = true" in content


# ---------------------------------------------------------------------------
# M Parameter Expressions
# ---------------------------------------------------------------------------


class TestMParameterExpressions:
    def test_server_and_database_params(self):
        content = generate_expressions_tmdl("SalesLH", "myserver.database.windows.net")
        assert 'expression ServerName = "myserver.database.windows.net"' in content
        assert 'expression DatabaseName = "SalesLH"' in content
        assert "IsParameterQuery=true" in content

    def test_default_endpoint(self):
        content = generate_expressions_tmdl("LH")
        assert 'ServerName = "localhost"' in content


# ---------------------------------------------------------------------------
# Culture / Multi-language
# ---------------------------------------------------------------------------


class TestCulture:
    def test_culture_with_synonyms(self):
        content = generate_culture_tmdl("fr-FR", linguistic_synonyms={"Order Date": ["Date de commande"]})
        assert "culture 'fr-FR'" in content
        assert "linguisticMetadata" in content
        assert "DynamicImprovement" in content
        assert "Date de commande" in content

    def test_culture_no_synonyms(self):
        content = generate_culture_tmdl("de-DE")
        assert "culture 'de-DE'" in content
        assert "Version" in content

    def test_model_with_cultures(self):
        ir = SemanticModelIR(
            tables=[LogicalTable(name="Sales")],
            cultures=["fr-FR", "de-DE"],
        )
        content = generate_model_tmdl(ir)
        assert "ref culture 'fr-FR'" in content
        assert "ref culture 'de-DE'" in content

    def test_generate_tmdl_with_cultures(self):
        ir = SemanticModelIR(
            tables=[LogicalTable(name="T1")],
            cultures=["fr-FR"],
        )
        result = generate_tmdl(ir)
        assert "definition/cultures/fr-FR.tmdl" in result.files
