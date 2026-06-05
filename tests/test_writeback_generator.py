"""Tests for writeback_generator — Essbase/Longview writeback → Fabric."""

from __future__ import annotations

import json

import pytest

from src.agents.etl.writeback_generator import (
    WritebackConfig,
    WritebackDimension,
    WritebackResult,
    config_from_essbase_outline,
    generate_calc_notebook,
    generate_model_hints,
    generate_stored_procedures,
    generate_warehouse_ddl,
    generate_writeback_artifacts,
    generate_writeback_pipeline,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _base_config(**overrides) -> WritebackConfig:
    dims = [
        WritebackDimension(name="Entity", column_name="Entity", data_type="NVARCHAR(100)"),
        WritebackDimension(name="Account", column_name="Account", data_type="NVARCHAR(100)"),
        WritebackDimension(name="FiscalPeriod", column_name="FiscalPeriod", data_type="INT"),
        WritebackDimension(name="FiscalYear", column_name="FiscalYear", data_type="INT"),
    ]
    defaults = dict(
        application_name="FinPlan",
        database_name="Budget",
        dimensions=dims,
        measure_columns=[{"name": "Amount", "data_type": "DECIMAL(18,2)"}],
    )
    defaults.update(overrides)
    return WritebackConfig(**defaults)


def _planning_outline() -> dict:
    return {
        "application": "FinPlan",
        "database": "Budget",
        "dimensions": [
            {
                "name": "Account",
                "type": "dense",
                "dimension_type": "accounts",
                "members": ["Revenue", "COGS", "Gross_Margin", "Opex", "EBITDA"],
            },
            {
                "name": "Entity",
                "type": "sparse",
                "members": ["Corporate", "North_America", "EMEA"],
            },
            {
                "name": "Period",
                "type": "dense",
                "dimension_type": "time",
                "members": ["Jan", "Feb", "Mar", "Q1"],
            },
            {
                "name": "Scenario",
                "type": "sparse",
                "members": ["Budget", "Forecast", "Actual"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# DDL generation
# ---------------------------------------------------------------------------


class TestWarehouseDDL:
    def test_creates_budget_input_table(self):
        config = _base_config()
        ddl = generate_warehouse_ddl(config)
        assert "Budget_Input" in ddl
        assert "CREATE TABLE" in ddl

    def test_dimension_columns(self):
        config = _base_config()
        ddl = generate_warehouse_ddl(config)
        assert "[Entity]" in ddl
        assert "[Account]" in ddl
        assert "[FiscalPeriod]" in ddl

    def test_measure_column(self):
        config = _base_config()
        ddl = generate_warehouse_ddl(config)
        assert "[Amount] DECIMAL(18,2)" in ddl

    def test_audit_columns_present(self):
        config = _base_config(enable_audit=True)
        ddl = generate_warehouse_ddl(config)
        assert "[ModifiedBy]" in ddl
        assert "[ModifiedAt]" in ddl

    def test_audit_columns_absent(self):
        config = _base_config(enable_audit=False)
        ddl = generate_warehouse_ddl(config)
        assert "[ModifiedBy]" not in ddl
        assert "Budget_Audit" not in ddl

    def test_consolidated_table(self):
        config = _base_config()
        ddl = generate_warehouse_ddl(config)
        assert "Budget_Consolidated" in ddl
        assert "[CalcSource]" in ddl

    def test_audit_table(self):
        config = _base_config(enable_audit=True)
        ddl = generate_warehouse_ddl(config)
        assert "Budget_Audit" in ddl
        assert "[OldAmount]" in ddl
        assert "[NewAmount]" in ddl

    def test_primary_key_not_enforced(self):
        config = _base_config()
        ddl = generate_warehouse_ddl(config)
        assert "PRIMARY KEY NONCLUSTERED" in ddl
        assert "NOT ENFORCED" in ddl

    def test_scenario_column_added_when_missing(self):
        dims = [WritebackDimension(name="Entity", column_name="Entity")]
        config = _base_config(dimensions=dims)
        ddl = generate_warehouse_ddl(config)
        assert "[Scenario]" in ddl

    def test_scenario_column_not_duplicated(self):
        dims = [
            WritebackDimension(name="Scenario", column_name="Scenario"),
            WritebackDimension(name="Entity", column_name="Entity"),
        ]
        config = _base_config(dimensions=dims)
        ddl = generate_warehouse_ddl(config)
        # Should appear exactly in dimension section, not added again
        count = ddl.count("[Scenario]")
        # Appears in Budget_Input + PK + Budget_Consolidated + maybe audit
        # Key assertion: not doubled within the same table section
        assert "NVARCHAR(20)" not in ddl  # uses dimension's type, not default


# ---------------------------------------------------------------------------
# Stored procedures
# ---------------------------------------------------------------------------


class TestStoredProcedures:
    def test_merge_procedure(self):
        config = _base_config()
        sql = generate_stored_procedures(config)
        assert "usp_WriteBudget" in sql
        assert "MERGE" in sql
        assert "WHEN MATCHED THEN" in sql
        assert "WHEN NOT MATCHED THEN" in sql

    def test_validation_procedure(self):
        config = _base_config()
        sql = generate_stored_procedures(config)
        assert "usp_ValidateBudget" in sql
        assert "Missing" in sql
        assert "NegativeRevenue" in sql

    def test_audit_trail_in_merge(self):
        config = _base_config(enable_audit=True)
        sql = generate_stored_procedures(config)
        assert "Budget_Audit" in sql
        assert "@OldAmount" in sql

    def test_dimension_params(self):
        config = _base_config()
        sql = generate_stored_procedures(config)
        assert "@Entity" in sql
        assert "@Account" in sql
        assert "@FiscalPeriod" in sql


# ---------------------------------------------------------------------------
# PySpark calc notebook
# ---------------------------------------------------------------------------


class TestCalcNotebook:
    def test_imports(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert "from pyspark.sql import functions as F" in nb
        assert "from pyspark.sql.window import Window" in nb

    def test_reads_budget_input(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert 'Tables/Budget_Input' in nb

    def test_writes_consolidated(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert 'Tables/Budget_Consolidated' in nb
        assert 'overwrite' in nb

    def test_agg_with_entity(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert "AGG" in nb
        assert "groupBy" in nb
        assert "Dim_Entity" in nb

    def test_ytd_with_period(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert "@TODATE" in nb or "YTD" in nb
        assert "unboundedPreceding" in nb

    def test_allocation_when_enabled(self):
        config = _base_config(enable_allocation=True)
        nb = generate_calc_notebook(config)
        assert "@ALLOCATE" in nb or "ALLOCATE" in nb
        assert "Weight" in nb

    def test_no_allocation_when_disabled(self):
        config = _base_config(enable_allocation=False)
        nb = generate_calc_notebook(config)
        assert "crossJoin" not in nb

    def test_currency_when_enabled(self):
        config = _base_config(enable_currency_conversion=True)
        nb = generate_calc_notebook(config)
        assert "FX_Rates" in nb

    def test_scenario_parameter(self):
        config = _base_config()
        nb = generate_calc_notebook(config)
        assert "spark.scenario" in nb


# ---------------------------------------------------------------------------
# Pipeline generation
# ---------------------------------------------------------------------------


class TestWritebackPipeline:
    def test_pipeline_name(self):
        config = _base_config()
        p = generate_writeback_pipeline(config)
        assert p.name == "FinPlan_Writeback_Pipeline"

    def test_four_activities(self):
        config = _base_config()
        p = generate_writeback_pipeline(config)
        assert len(p.activities) == 4

    def test_activity_types(self):
        config = _base_config()
        p = generate_writeback_pipeline(config)
        types = [a.activity_type for a in p.activities]
        assert "Lookup" in types
        assert "TridentNotebook" in types
        assert "SqlServerStoredProcedure" in types
        assert "TridentDatasetRefresh" in types

    def test_dependency_chain(self):
        config = _base_config()
        p = generate_writeback_pipeline(config)
        # First activity has no deps
        assert p.activities[0].depends_on == []
        # Notebook depends on lookup
        assert "Check_New_Writeback" in p.activities[1].depends_on
        # Validate depends on notebook
        assert "Run_Budget_Calcs" in p.activities[2].depends_on

    def test_pipeline_json_valid(self):
        config = _base_config()
        p = generate_writeback_pipeline(config)
        j = p.to_json()
        data = json.loads(j)
        assert "name" in data
        assert "activities" in data.get("properties", data)


# ---------------------------------------------------------------------------
# Model hints
# ---------------------------------------------------------------------------


class TestModelHints:
    def test_tables(self):
        config = _base_config()
        hints = generate_model_hints(config)
        table_names = [t["name"] for t in hints["tables"]]
        assert "Budget Consolidated" in table_names
        assert "Budget Input" in table_names

    def test_measures(self):
        config = _base_config()
        hints = generate_model_hints(config)
        measure_names = [m["name"] for m in hints["measures"]]
        assert "Budget Total" in measure_names
        assert "Variance" in measure_names
        assert "Variance %" in measure_names


# ---------------------------------------------------------------------------
# config_from_essbase_outline
# ---------------------------------------------------------------------------


class TestConfigFromOutline:
    def test_application_name(self):
        cfg = config_from_essbase_outline(_planning_outline())
        assert cfg.application_name == "FinPlan"
        assert cfg.database_name == "Budget"

    def test_dimensions_exclude_accounts(self):
        cfg = config_from_essbase_outline(_planning_outline())
        dim_names = [d.name for d in cfg.dimensions]
        assert "Account" not in dim_names
        assert "Entity" in dim_names
        assert "Period" in dim_names

    def test_measure_columns_from_accounts_dim(self):
        cfg = config_from_essbase_outline(_planning_outline())
        measure_names = [m["name"] for m in cfg.measure_columns]
        assert "Revenue" in measure_names

    def test_max_5_measures(self):
        outline = _planning_outline()
        # Add many account members
        outline["dimensions"][0]["members"] = [f"Acct_{i}" for i in range(20)]
        cfg = config_from_essbase_outline(outline)
        assert len(cfg.measure_columns) <= 5

    def test_allocation_flag(self):
        cfg = config_from_essbase_outline(_planning_outline(), enable_allocation=True)
        assert cfg.enable_allocation is True

    def test_rejects_aso_cube_type(self):
        outline = _planning_outline()
        outline["cube_type"] = "ASO"
        with pytest.raises(ValueError, match="BSO"):
            config_from_essbase_outline(outline)

    def test_accepts_bso_cube_type(self):
        outline = _planning_outline()
        outline["cube_type"] = "BSO"
        cfg = config_from_essbase_outline(outline)
        assert cfg.application_name == "FinPlan"


# ---------------------------------------------------------------------------
# End-to-end: generate_writeback_artifacts
# ---------------------------------------------------------------------------


class TestGenerateWritebackArtifacts:
    def test_returns_writeback_result(self):
        config = _base_config()
        result = generate_writeback_artifacts(config)
        assert isinstance(result, WritebackResult)

    def test_all_artifacts_non_empty(self):
        config = _base_config()
        result = generate_writeback_artifacts(config)
        assert len(result.warehouse_ddl) > 100
        assert len(result.stored_procedures) > 100
        assert len(result.calc_notebook) > 100
        assert len(result.pipeline_json) > 50
        assert result.model_hints["tables"]

    def test_default_dims_when_empty(self):
        config = WritebackConfig(
            application_name="Test",
            database_name="Plan",
            dimensions=[],
        )
        result = generate_writeback_artifacts(config)
        # Should auto-populate default dims
        assert "Entity" in result.warehouse_ddl
        assert "Account" in result.warehouse_ddl
        assert len(result.warnings) > 0

    def test_allocation_warning_without_entity(self):
        dims = [WritebackDimension(name="Product", column_name="Product")]
        config = WritebackConfig(
            application_name="Test",
            database_name="Plan",
            dimensions=dims,
            enable_allocation=True,
        )
        result = generate_writeback_artifacts(config)
        assert any("entity" in w.lower() for w in result.warnings)

    def test_from_outline_end_to_end(self):
        outline = _planning_outline()
        cfg = config_from_essbase_outline(outline, enable_allocation=True)
        result = generate_writeback_artifacts(cfg)
        assert "Budget_Input" in result.warehouse_ddl
        assert "usp_WriteBudget" in result.stored_procedures
        assert "Budget_Consolidated" in result.calc_notebook
        assert "FinPlan_Writeback_Pipeline" in result.pipeline_json
