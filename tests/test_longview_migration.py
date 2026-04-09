"""Tests for longview_migration — Phase A: Keep Longview, replace Essbase backend."""

from __future__ import annotations

import json

import pytest

from src.agents.etl.longview_migration import (
    EssbaseComplexity,
    PhaseAResult,
    assess_essbase_complexity,
    generate_cutover_checklist,
    generate_data_migration_notebook,
    generate_dimension_ddl,
    generate_phase_a_artifacts,
    generate_tds_connection_config,
    generate_uat_notebook,
)
from src.agents.etl.writeback_generator import (
    WritebackConfig,
    WritebackDimension,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_config(**overrides) -> WritebackConfig:
    dims = [
        WritebackDimension(name="Entity", column_name="Entity", data_type="NVARCHAR(100)"),
        WritebackDimension(name="Account", column_name="Account", data_type="NVARCHAR(100)"),
        WritebackDimension(name="Period", column_name="Period", data_type="NVARCHAR(20)",
                           is_dense=True),
        WritebackDimension(name="Scenario", column_name="Scenario", data_type="NVARCHAR(20)"),
    ]
    defaults = dict(
        application_name="FinPlan",
        database_name="Budget",
        dimensions=dims,
        measure_columns=[{"name": "Amount", "data_type": "DECIMAL(18,2)"}],
    )
    defaults.update(overrides)
    return WritebackConfig(**defaults)


def _complex_config(**overrides) -> WritebackConfig:
    """Config with allocation, currency, and calc scripts."""
    dims = [
        WritebackDimension(name="Entity", column_name="Entity", data_type="NVARCHAR(100)",
                           members=["Corporate", "NA", "EMEA", "APAC"]),
        WritebackDimension(name="Account", column_name="Account", data_type="NVARCHAR(100)",
                           is_dense=True,
                           members=["Revenue", "COGS", "Gross_Margin", "Opex", "EBITDA"]),
        WritebackDimension(name="Period", column_name="Period", data_type="NVARCHAR(20)",
                           is_dense=True,
                           members=["Jan", "Feb", "Mar", "Q1", "Apr", "May", "Jun", "Q2"]),
        WritebackDimension(name="Product", column_name="Product", data_type="NVARCHAR(100)",
                           members=["Widget_A", "Widget_B", "Services"]),
        WritebackDimension(name="Scenario", column_name="Scenario", data_type="NVARCHAR(20)"),
        WritebackDimension(name="Currency", column_name="Currency", data_type="NVARCHAR(10)",
                           members=["USD", "EUR", "GBP"]),
    ]
    defaults = dict(
        application_name="GlobalPlan",
        database_name="ForecastDB",
        dimensions=dims,
        measure_columns=[{"name": "Amount", "data_type": "DECIMAL(18,2)"}],
        calc_scripts=[
            {"name": "Agg_Budget", "body": "FIX(Budget)\n  AGG(Entity);\n  AGG(Product);\nENDFIX"},
            {"name": "Alloc_OH", "body": "@ALLOCATE(Entity, Amount, @RELATIVE(Total,0))"},
            {"name": "Calc_FX", "body": "@XREF(FXRates, Currency)\nAmount_USD = Amount * Rate"},
            {"name": "Calc_YTD", "body": "@TODATE(Period, Amount)"},
        ],
        enable_allocation=True,
        enable_currency_conversion=True,
    )
    defaults.update(overrides)
    return WritebackConfig(**defaults)


# ---------------------------------------------------------------------------
# Phase 1: Assessment
# ---------------------------------------------------------------------------


class TestAssessment:
    """Tests for assess_essbase_complexity()."""

    def test_basic_assessment_fields(self):
        result = assess_essbase_complexity(_base_config())
        assert result.application_name == "FinPlan"
        assert result.dimension_count == 4
        assert result.calc_script_count == 0

    def test_low_complexity_no_scripts(self):
        result = assess_essbase_complexity(_base_config())
        assert result.complexity == "Low"
        assert result.estimated_weeks == 2.0

    def test_high_complexity_with_features(self):
        result = assess_essbase_complexity(_complex_config())
        assert result.complexity in ("Medium", "High")
        assert result.estimated_weeks >= 3.0

    def test_detects_allocation(self):
        result = assess_essbase_complexity(_complex_config())
        assert result.has_allocation is True

    def test_detects_cross_ref(self):
        result = assess_essbase_complexity(_complex_config())
        assert result.has_cross_ref is True

    def test_dense_sparse_count(self):
        result = assess_essbase_complexity(_complex_config())
        assert result.dense_dimensions == 2
        assert result.sparse_dimensions == 4

    def test_member_count(self):
        result = assess_essbase_complexity(_complex_config())
        assert result.member_count > 0
        # Corporate, NA, EMEA, APAC + Revenue..EBITDA + Jan..Q2 + ...
        assert result.member_count >= 20

    def test_to_dict(self):
        result = assess_essbase_complexity(_base_config())
        d = result.to_dict()
        assert d["application_name"] == "FinPlan"
        assert "complexity" in d
        assert "estimated_weeks" in d


# ---------------------------------------------------------------------------
# Phase 2: Dimension DDL
# ---------------------------------------------------------------------------


class TestDimensionDDL:
    """Tests for generate_dimension_ddl()."""

    def test_creates_dim_tables(self):
        ddl = generate_dimension_ddl(_base_config())
        assert "Dim_Entity" in ddl
        assert "Dim_Account" in ddl
        assert "Dim_Period" in ddl

    def test_dim_table_columns(self):
        ddl = generate_dimension_ddl(_base_config())
        assert "[EntityKey]" in ddl
        assert "[ParentMember]" in ddl
        assert "[Level]" in ddl
        assert "[IsLeaf]" in ddl

    def test_primary_key(self):
        ddl = generate_dimension_ddl(_base_config())
        assert "PK_Dim_Entity" in ddl
        assert "NOT ENFORCED" in ddl

    def test_seed_data_from_members(self):
        ddl = generate_dimension_ddl(_complex_config())
        assert "INSERT INTO" in ddl
        assert "Corporate" in ddl
        assert "Revenue" in ddl

    def test_no_seed_without_members(self):
        ddl = generate_dimension_ddl(_base_config())
        # Base config has no members
        assert "INSERT INTO" not in ddl

    def test_sort_order(self):
        ddl = generate_dimension_ddl(_complex_config())
        assert "[SortOrder]" in ddl

    def test_schema_prefix(self):
        ddl = generate_dimension_ddl(_base_config())
        assert "dbo.Dim_" in ddl


# ---------------------------------------------------------------------------
# Phase 3: Data migration notebook
# ---------------------------------------------------------------------------


class TestDataMigrationNotebook:
    """Tests for generate_data_migration_notebook()."""

    def test_imports(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "from pyspark.sql import functions as F" in nb
        assert "StructType" in nb

    def test_references_app_name(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "FinPlan" in nb

    def test_reads_csv_export(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "csv" in nb
        assert "header" in nb

    def test_schema_includes_dims(self):
        nb = generate_data_migration_notebook(_base_config())
        assert '"Entity"' in nb
        assert '"Account"' in nb
        assert '"Period"' in nb

    def test_writes_to_budget_input(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "Budget_Input" in nb
        assert "delta" in nb

    def test_writes_dimension_tables(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "Dim_Entity" in nb
        assert "Dim_Account" in nb

    def test_data_quality_checks(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "null" in nb.lower() or "isNull" in nb

    def test_validation_step(self):
        nb = generate_data_migration_notebook(_base_config())
        assert "assert" in nb


# ---------------------------------------------------------------------------
# Phase 5: TDS connection config
# ---------------------------------------------------------------------------


class TestTDSConnectionConfig:
    """Tests for generate_tds_connection_config()."""

    def test_tds_endpoint(self):
        cfg = generate_tds_connection_config(_base_config())
        assert cfg["tds_endpoint"] == "BudgetWorkspace.datawarehouse.fabric.microsoft.com"
        assert cfg["port"] == 1433

    def test_custom_workspace(self):
        cfg = generate_tds_connection_config(
            _base_config(), workspace_name="FinanceWS", warehouse_name="FinWH"
        )
        assert "FinanceWS" in cfg["tds_endpoint"]
        assert cfg["database"] == "FinWH"

    def test_jdbc_connection_string(self):
        cfg = generate_tds_connection_config(_base_config())
        jdbc = cfg["connection_string_jdbc"]
        assert "jdbc:sqlserver://" in jdbc
        assert "BudgetWorkspace" in jdbc
        assert "encrypt=true" in jdbc

    def test_odbc_connection_string(self):
        cfg = generate_tds_connection_config(_base_config())
        odbc = cfg["connection_string_odbc"]
        assert "ODBC Driver 18" in odbc
        assert "Encrypt=yes" in odbc

    def test_longview_config(self):
        cfg = generate_tds_connection_config(_base_config())
        lv = cfg["longview_config"]
        assert lv["data_source_type"] == "SQL Server (Fabric TDS)"
        assert lv["sso_enabled"] is True
        assert lv["writeback_procedure"] == "dbo.usp_WriteBudget"

    def test_essbase_mapping(self):
        cfg = generate_tds_connection_config(_base_config())
        mapping = cfg["essbase_to_fabric_mapping"]
        assert mapping["essbase_application"] == "FinPlan"
        assert "Budget_Input" in mapping["fabric_tables"]["writeback_input"]

    def test_migration_notes(self):
        cfg = generate_tds_connection_config(_base_config())
        notes = cfg["migration_notes"]
        assert len(notes) >= 5
        assert any("TDS" in n for n in notes)

    def test_authentication_mode(self):
        cfg = generate_tds_connection_config(_base_config())
        assert cfg["authentication"] == "ActiveDirectoryInteractive"
        assert cfg["longview_config"]["authentication_mode"] == "Entra ID (Azure AD)"


# ---------------------------------------------------------------------------
# Phase 6: UAT notebook
# ---------------------------------------------------------------------------


class TestUATNotebook:
    """Tests for generate_uat_notebook()."""

    def test_imports(self):
        nb = generate_uat_notebook(_base_config())
        assert "from pyspark.sql import functions as F" in nb

    def test_loads_both_datasets(self):
        nb = generate_uat_notebook(_base_config())
        assert "essbase" in nb.lower()
        assert "fabric" in nb

    def test_row_count_test(self):
        nb = generate_uat_notebook(_base_config())
        assert "Row Count" in nb

    def test_grand_total_test(self):
        nb = generate_uat_notebook(_base_config())
        assert "Grand Total" in nb

    def test_dimension_coverage_test(self):
        nb = generate_uat_notebook(_base_config())
        assert "Dim Entity" in nb or "Dim_Entity" in nb

    def test_scenario_totals_test(self):
        nb = generate_uat_notebook(_base_config())
        assert "Scenario" in nb

    def test_writeback_roundtrip_test(self):
        nb = generate_uat_notebook(_base_config())
        assert "Round-trip" in nb or "round-trip" in nb or "roundtrip" in nb

    def test_uat_summary(self):
        nb = generate_uat_notebook(_base_config())
        assert "UAT Results" in nb

    def test_cleanup_test_data(self):
        nb = generate_uat_notebook(_base_config())
        assert "delete" in nb.lower() or "DELETE" in nb

    def test_tolerance_check(self):
        nb = generate_uat_notebook(_base_config())
        assert "tolerance" in nb


# ---------------------------------------------------------------------------
# Phase 7: Cutover checklist
# ---------------------------------------------------------------------------


class TestCutoverChecklist:
    """Tests for generate_cutover_checklist()."""

    def test_markdown_format(self):
        md = generate_cutover_checklist(_base_config())
        assert md.startswith("# Phase A Cutover")

    def test_contains_all_sections(self):
        md = generate_cutover_checklist(_base_config())
        assert "Pre-Cutover" in md
        assert "Cutover Steps" in md
        assert "Post-Cutover" in md
        assert "Rollback Plan" in md

    def test_contains_tds_endpoint(self):
        md = generate_cutover_checklist(_base_config())
        assert "datawarehouse.fabric.microsoft.com" in md

    def test_time_savings_table(self):
        md = generate_cutover_checklist(_base_config())
        assert "Time Savings Summary" in md
        assert "Traditional" in md
        assert "Automated" in md

    def test_custom_workspace(self):
        md = generate_cutover_checklist(
            _base_config(), workspace_name="FinWS", warehouse_name="FinWH"
        )
        assert "FinWS" in md
        assert "FinWH" in md

    def test_smoke_test_checklist(self):
        md = generate_cutover_checklist(_base_config())
        assert "Smoke tests" in md or "smoke" in md.lower()
        assert "Budget_Audit" in md

    def test_rollback_instructions(self):
        md = generate_cutover_checklist(_base_config())
        assert "Revert" in md or "revert" in md
        assert "Essbase" in md


# ---------------------------------------------------------------------------
# End-to-end: generate_phase_a_artifacts
# ---------------------------------------------------------------------------


class TestPhaseAArtifacts:
    """Tests for generate_phase_a_artifacts() — full Phase A orchestrator."""

    def test_returns_phase_a_result(self):
        result = generate_phase_a_artifacts(_base_config())
        assert isinstance(result, PhaseAResult)

    def test_all_fields_non_empty(self):
        result = generate_phase_a_artifacts(_base_config())
        assert result.dimension_ddl
        assert result.data_migration_notebook
        assert result.tds_connection_config
        assert result.uat_notebook
        assert result.cutover_checklist
        assert result.writeback is not None
        assert result.assessment

    def test_assessment_in_result(self):
        result = generate_phase_a_artifacts(_base_config())
        assert result.assessment["application_name"] == "FinPlan"
        assert "complexity" in result.assessment

    def test_writeback_included(self):
        result = generate_phase_a_artifacts(_base_config())
        assert result.writeback.warehouse_ddl
        assert result.writeback.stored_procedures
        assert result.writeback.calc_notebook

    def test_tds_config_matches_params(self):
        result = generate_phase_a_artifacts(
            _base_config(), workspace_name="TestWS", warehouse_name="TestWH"
        )
        assert result.tds_connection_config["database"] == "TestWH"
        assert "TestWS" in result.tds_connection_config["tds_endpoint"]

    def test_complex_config_end_to_end(self):
        result = generate_phase_a_artifacts(_complex_config())
        assert result.assessment["complexity"] in ("Medium", "High")
        assert result.assessment["has_allocation"] is True
        assert len(result.warnings) >= 0  # May or may not have warnings

    def test_default_workspace_names(self):
        result = generate_phase_a_artifacts(_base_config())
        assert "BudgetWorkspace" in result.tds_connection_config["tds_endpoint"]

    def test_dimension_ddl_in_result(self):
        result = generate_phase_a_artifacts(_complex_config())
        assert "Dim_Entity" in result.dimension_ddl
        assert "INSERT INTO" in result.dimension_ddl  # seed data from members

    def test_cutover_checklist_format(self):
        result = generate_phase_a_artifacts(_base_config())
        assert result.cutover_checklist.startswith("# Phase A")
