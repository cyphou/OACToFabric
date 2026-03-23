"""Tests for Essbase → Semantic Model bridge.

Tests cover:
- EssbaseToSemanticModelConverter basic conversion
- Dimension → LogicalTable mapping (sparse, dense, time, accounts, attribute)
- Accounts dimension → DAX measures
- Hierarchy generation from dimensions
- Star-schema join creation
- Calc script → DAX measure integration
- Filter → RLS role conversion
- Substitution variable → What-if parameter
- Subject area / perspective creation
- Edge cases (empty outline, no members, no accounts)
"""

from __future__ import annotations

import pytest

from src.agents.semantic.rpd_model_parser import (
    ColumnKind,
    JoinCardinality,
    SemanticModelIR,
)
from src.connectors.essbase_connector import (
    EssbaseCalcScript,
    EssbaseDimension,
    EssbaseFilter,
    EssbaseMember,
    EssbaseSubstitutionVar,
    ParsedOutline,
)
from src.connectors.essbase_semantic_bridge import (
    ESSBASE_DATA_TYPE_MAP,
    EssbaseConversionResult,
    EssbaseToSemanticModelConverter,
    RlsRoleDefinition,
    WhatsIfParameter,
)


# ===================================================================
# Helpers
# ===================================================================


def _simple_outline(
    app: str = "FinApp",
    db: str = "Plan",
    dimensions: list[EssbaseDimension] | None = None,
) -> ParsedOutline:
    return ParsedOutline(
        application=app,
        database=db,
        dimensions=dimensions or [],
    )


def _make_dim(
    name: str,
    dim_type: str = "regular",
    storage: str = "sparse",
    members: list[str] | None = None,
    member_details: list[EssbaseMember] | None = None,
    gen_count: int = 0,
) -> EssbaseDimension:
    return EssbaseDimension(
        name=name,
        dimension_type=dim_type,
        storage_type=storage,
        members=members or [],
        member_details=member_details or [],
        generation_count=gen_count,
    )


# ===================================================================
# Basic conversion
# ===================================================================


class TestBasicConversion:
    """Tests for basic outline → SemanticModelIR conversion."""

    def test_empty_outline(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=[]))
        assert isinstance(result, EssbaseConversionResult)
        assert isinstance(result.ir, SemanticModelIR)
        # Should at least have a fact table
        assert result.table_count >= 1

    def test_model_name_from_app_db(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(app="Fin", db="Plan"))
        assert result.ir.model_name == "Fin_Plan"

    def test_model_name_override(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(
            _simple_outline(), model_name="CustomModel"
        )
        assert result.ir.model_name == "CustomModel"

    def test_description_set(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(app="X", db="Y"))
        assert "X" in result.ir.description
        assert "Y" in result.ir.description

    def test_single_sparse_dimension(self):
        dims = [_make_dim("Product", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        # Should have fact table + Product dimension table
        names = [t.name for t in result.ir.tables]
        assert any("Product" in n for n in names)
        assert result.table_count >= 2

    def test_single_dense_dimension(self):
        dims = [_make_dim("Scenario", storage="dense")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        # Dense → columns in fact table, no separate table
        fact = result.ir.tables[0]
        col_names = [c.name for c in fact.columns]
        assert "ScenarioKey" in col_names


# ===================================================================
# Dimension → Table mapping
# ===================================================================


class TestDimensionToTable:
    """Tests for sparse dimension → LogicalTable."""

    def test_sparse_creates_table(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        assert market is not None

    def test_table_has_key_column(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        keys = [c for c in market.columns if c.kind == ColumnKind.KEY]
        assert len(keys) >= 1
        assert keys[0].name == "MarketKey"

    def test_table_has_name_column(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "Market" in names

    def test_table_has_parent_column(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "MarketParent" in names

    def test_table_has_level_column(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "MarketLevel" in names

    def test_generation_columns(self):
        dims = [_make_dim("Market", storage="sparse", gen_count=3)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "Gen1_Market" in names
        assert "Gen2_Market" in names
        assert "Gen3_Market" in names

    def test_uda_columns(self):
        mbrs = [
            EssbaseMember(name="East", uda_list=["Active", "Major"]),
            EssbaseMember(name="West", uda_list=["Active"]),
        ]
        dims = [_make_dim("Market", storage="sparse", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "UDA_Active" in names
        assert "UDA_Major" in names

    def test_alias_column(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        names = [c.name for c in market.columns]
        assert "MarketAlias" in names

    def test_metadata_captured(self):
        dims = [_make_dim("Market", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        market = result.ir.table_by_name("Market")
        assert market.metadata["essbase_storage_type"] == "sparse"


# ===================================================================
# Time dimension
# ===================================================================


class TestTimeDimension:
    """Tests for time dimension → date table."""

    def test_time_dim_is_date_table(self):
        dims = [_make_dim("Year", dim_type="time", storage="dense")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        year = result.ir.table_by_name("Year")
        assert year is not None
        assert year.is_date_table is True

    def test_time_dim_has_hierarchy(self):
        dims = [_make_dim("Year", dim_type="time", storage="dense", gen_count=3)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        year = result.ir.table_by_name("Year")
        assert len(year.hierarchies) == 1
        assert len(year.hierarchies[0].levels) == 3


# ===================================================================
# Accounts dimension → measures
# ===================================================================


class TestAccountsDimension:
    """Tests for accounts dimension → DAX measures."""

    def test_stored_members_become_measures(self):
        mbrs = [
            EssbaseMember(name="Revenue", storage_type="store"),
            EssbaseMember(name="COGS", storage_type="store"),
        ]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        measure_names = [m.name for m in fact.measures]
        assert "Revenue" in measure_names
        assert "COGS" in measure_names

    def test_dynamic_calc_with_formula(self):
        mbrs = [
            EssbaseMember(name="Profit", storage_type="dynamic_calc", formula="Revenue - COGS;"),
        ]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        profit = next((m for m in fact.measures if m.name == "Profit"), None)
        assert profit is not None
        assert profit.kind == ColumnKind.MEASURE
        assert len(profit.expression) > 0

    def test_dynamic_calc_without_formula(self):
        mbrs = [
            EssbaseMember(name="Total", storage_type="dynamic_calc", formula=""),
        ]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        total = next((m for m in fact.measures if m.name == "Total"), None)
        assert total is not None
        assert "SUM" in total.expression

    def test_label_only_skipped(self):
        mbrs = [
            EssbaseMember(name="Header", storage_type="label_only"),
            EssbaseMember(name="Rev", storage_type="store"),
        ]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        names = [m.name for m in fact.measures]
        assert "Header" not in names
        assert "Rev" in names

    def test_measures_from_member_names(self):
        """If no member_details, use member names."""
        dims = [_make_dim("Accounts", dim_type="accounts", members=["Sales", "Cost"])]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        names = [m.name for m in fact.measures]
        assert "Sales" in names
        assert "Cost" in names

    def test_measures_have_display_folder(self):
        mbrs = [EssbaseMember(name="Rev", storage_type="store")]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        rev = next(m for m in fact.measures if m.name == "Rev")
        assert rev.display_folder == "Accounts"


# ===================================================================
# Hierarchy generation
# ===================================================================


class TestHierarchyGeneration:
    def test_no_hierarchy_for_gen_1(self):
        dims = [_make_dim("Flat", storage="sparse", gen_count=1)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        flat = result.ir.table_by_name("Flat")
        assert len(flat.hierarchies) == 0

    def test_hierarchy_for_multiple_gens(self):
        dims = [_make_dim("Geo", storage="sparse", gen_count=4)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        geo = result.ir.table_by_name("Geo")
        assert len(geo.hierarchies) == 1
        h = geo.hierarchies[0]
        assert len(h.levels) == 4
        assert h.levels[0].column_name == "Gen1_Geo"

    def test_hierarchy_level_ordinals(self):
        dims = [_make_dim("Prod", storage="sparse", gen_count=3)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        prod = result.ir.table_by_name("Prod")
        h = prod.hierarchies[0]
        for i, level in enumerate(h.levels, start=1):
            assert level.ordinal == i


# ===================================================================
# Star-schema joins
# ===================================================================


class TestStarSchemaJoins:
    def test_sparse_dim_joined_to_fact(self):
        dims = [_make_dim("Product", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert result.relationship_count >= 1
        join = result.ir.joins[0]
        assert join.to_table == "Product"
        assert join.cardinality == JoinCardinality.MANY_TO_ONE

    def test_time_dim_joined_to_fact(self):
        dims = [_make_dim("Year", dim_type="time", storage="dense")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        joins = [j for j in result.ir.joins if j.to_table == "Year"]
        assert len(joins) == 1

    def test_dense_dim_no_join(self):
        dims = [_make_dim("Scenario", storage="dense")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        # Dense dims → columns in fact, no join
        joins = [j for j in result.ir.joins if j.to_table == "Scenario"]
        assert len(joins) == 0

    def test_multiple_dim_joins(self):
        dims = [
            _make_dim("Product", storage="sparse"),
            _make_dim("Market", storage="sparse"),
            _make_dim("Year", dim_type="time", storage="dense"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert result.relationship_count >= 3  # Product, Market, Year


# ===================================================================
# Fact table
# ===================================================================


class TestFactTable:
    def test_fact_table_first(self):
        dims = [_make_dim("Product", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert "Fact" in result.ir.tables[0].name

    def test_fact_has_value_column(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline())
        fact = result.ir.tables[0]
        names = [c.name for c in fact.columns]
        assert "Value" in names

    def test_fact_has_fk_for_sparse_dim(self):
        dims = [_make_dim("Product", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        names = [c.name for c in fact.columns]
        assert "ProductKey" in names

    def test_fact_has_fk_for_time_dim(self):
        dims = [_make_dim("Year", dim_type="time", storage="dense")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        fact = result.ir.tables[0]
        names = [c.name for c in fact.columns]
        assert "YearKey" in names


# ===================================================================
# Calc script integration
# ===================================================================


class TestCalcScriptIntegration:
    def test_calc_scripts_added_as_measures(self):
        dims = [_make_dim("Product", storage="sparse")]
        scripts = [
            EssbaseCalcScript(name="Revenue_YTD", content="@TODATE(Revenue, Year)"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(
            _simple_outline(dimensions=dims), calc_scripts=scripts
        )
        fact = result.ir.tables[0]
        names = [m.name for m in fact.measures]
        assert "Revenue_YTD" in names

    def test_calc_translations_tracked(self):
        scripts = [
            EssbaseCalcScript(name="S1", content="@SUM(Sales)"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), calc_scripts=scripts)
        assert len(result.calc_translations) == 1
        assert result.calc_translations[0].source_name == "S1"

    def test_low_confidence_calc_in_review(self):
        scripts = [
            EssbaseCalcScript(name="AllocCost", content="@ALLOCATE(Cost)"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), calc_scripts=scripts)
        assert len(result.review_items) >= 1
        assert "AllocCost" in result.review_items[0]

    def test_calc_measure_has_display_folder(self):
        scripts = [
            EssbaseCalcScript(name="MyCalc", content="@ABS(Revenue)"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), calc_scripts=scripts)
        fact = result.ir.tables[0]
        calc_measure = next((m for m in fact.measures if m.name == "MyCalc"), None)
        assert calc_measure is not None
        assert calc_measure.display_folder == "Calc Scripts"


# ===================================================================
# Filter → RLS
# ===================================================================


class TestFilterToRls:
    def test_filter_to_rls_role(self):
        flt = EssbaseFilter(
            name="RegionFilter",
            rows=[{"member": "East", "access": "read"}],
        )
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), filters=[flt])
        assert len(result.rls_roles) == 1
        assert result.rls_roles[0].name == "RegionFilter"

    def test_empty_filter_skipped(self):
        flt = EssbaseFilter(name="Empty", rows=[])
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), filters=[flt])
        assert len(result.rls_roles) == 0

    def test_none_access_generates_deny(self):
        flt = EssbaseFilter(
            name="DenyFilter",
            rows=[{"member": "Confidential", "access": "none"}],
        )
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), filters=[flt])
        role = result.rls_roles[0]
        assert "NOT" in role.filter_expression

    def test_read_access_generates_allow(self):
        flt = EssbaseFilter(
            name="AllowFilter",
            rows=[{"member": "Public", "access": "read"}],
        )
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), filters=[flt])
        role = result.rls_roles[0]
        assert "CONTAINSSTRING" in role.filter_expression


# ===================================================================
# Substitution variables → What-if parameters
# ===================================================================


class TestSubstitutionVariables:
    def test_variable_to_whatif(self):
        vars_ = [EssbaseSubstitutionVar(name="CurMonth", value="Jan")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(), substitution_vars=vars_)
        assert len(result.whatif_parameters) == 1
        assert result.whatif_parameters[0].name == "CurMonth"
        assert result.whatif_parameters[0].current_value == "Jan"
        assert "VAR" in result.whatif_parameters[0].dax_variable

    def test_no_variables(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline())
        assert len(result.whatif_parameters) == 0


# ===================================================================
# Subject area / perspective
# ===================================================================


class TestSubjectArea:
    def test_one_perspective_per_cube(self):
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline())
        assert len(result.ir.subject_areas) == 1

    def test_perspective_includes_all_tables(self):
        dims = [
            _make_dim("Product", storage="sparse"),
            _make_dim("Year", dim_type="time"),
        ]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        sa = result.ir.subject_areas[0]
        assert len(sa.tables) == result.table_count


# ===================================================================
# Data type mapping
# ===================================================================


class TestDataTypeMapping:
    def test_numeric_maps_to_double(self):
        assert ESSBASE_DATA_TYPE_MAP["numeric"] == "double"

    def test_text_maps_to_string(self):
        assert ESSBASE_DATA_TYPE_MAP["text"] == "string"

    def test_date_maps_to_datetime(self):
        assert ESSBASE_DATA_TYPE_MAP["date"] == "dateTime"


# ===================================================================
# EssbaseConversionResult properties
# ===================================================================


class TestConversionResultProperties:
    def test_table_count(self):
        dims = [_make_dim("P", storage="sparse"), _make_dim("M", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert result.table_count >= 3  # fact + 2 dims

    def test_measure_count(self):
        mbrs = [EssbaseMember(name="Rev", storage_type="store")]
        dims = [_make_dim("Accounts", dim_type="accounts", member_details=mbrs)]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert result.measure_count >= 1

    def test_relationship_count(self):
        dims = [_make_dim("P", storage="sparse")]
        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(_simple_outline(dimensions=dims))
        assert result.relationship_count >= 1


# ===================================================================
# Complex end-to-end scenario
# ===================================================================


class TestEndToEnd:
    """Full Essbase cube → SemanticModelIR conversion."""

    def test_sample_basicbso_cube(self):
        """Simulate Sample.Basic BSO cube."""
        dims = [
            _make_dim("Year", dim_type="time", storage="dense", gen_count=3,
                       members=["Qtr1", "Qtr2", "Qtr3", "Qtr4", "Jan", "Feb", "Mar"]),
            _make_dim(
                "Measures", dim_type="accounts", storage="dense",
                member_details=[
                    EssbaseMember(name="Sales", storage_type="store"),
                    EssbaseMember(name="COGS", storage_type="store"),
                    EssbaseMember(name="Profit", storage_type="dynamic_calc", formula="Sales - COGS;"),
                    EssbaseMember(name="Margin%", storage_type="dynamic_calc", formula="Profit / Sales;"),
                    EssbaseMember(name="Ratios", storage_type="label_only"),
                ],
            ),
            _make_dim("Product", storage="sparse", gen_count=3,
                       members=["Cola", "Root Beer", "Cream Soda", "Diet"]),
            _make_dim("Market", storage="sparse", gen_count=3,
                       members=["East", "West", "South", "Central"]),
            _make_dim("Scenario", storage="dense",
                       members=["Actual", "Budget", "Variance"]),
        ]

        scripts = [
            EssbaseCalcScript(name="CalcAll", content="AGG(Year); AGG(Product); AGG(Market);"),
            EssbaseCalcScript(name="Revenue_YTD", content="@TODATE(Sales, Year)"),
        ]

        filters = [
            EssbaseFilter(name="EastOnly", rows=[{"member": "East", "access": "read"}]),
        ]

        sub_vars = [
            EssbaseSubstitutionVar(name="CurMonth", value="Mar"),
            EssbaseSubstitutionVar(name="CurYear", value="FY24"),
        ]

        outline = ParsedOutline(
            application="Sample",
            database="Basic",
            dimensions=dims,
        )

        converter = EssbaseToSemanticModelConverter()
        result = converter.convert(
            outline,
            calc_scripts=scripts,
            filters=filters,
            substitution_vars=sub_vars,
        )

        # Model name
        assert result.ir.model_name == "Sample_Basic"

        # Tables: fact + Year (date) + Product + Market = 4
        # (Scenario is dense → columns in fact, Measures is accounts → measures)
        assert result.table_count >= 4

        # Year is date table
        year = result.ir.table_by_name("Year")
        assert year is not None
        assert year.is_date_table

        # Product and Market are dimension tables
        prod = result.ir.table_by_name("Product")
        market = result.ir.table_by_name("Market")
        assert prod is not None
        assert market is not None

        # Measures from accounts
        fact = result.ir.tables[0]
        measure_names = [m.name for m in fact.measures]
        assert "Sales" in measure_names
        assert "COGS" in measure_names
        assert "Profit" in measure_names
        assert "Margin%" in measure_names
        assert "Ratios" not in measure_names  # label_only skipped

        # Calc scripts added
        assert "CalcAll" in measure_names or "Revenue_YTD" in measure_names

        # Joins
        assert result.relationship_count >= 3

        # RLS
        assert len(result.rls_roles) == 1
        assert result.rls_roles[0].name == "EastOnly"

        # What-if params
        assert len(result.whatif_parameters) == 2

        # Calc translations tracked
        assert len(result.calc_translations) == 2

        # Subject area
        assert len(result.ir.subject_areas) == 1
