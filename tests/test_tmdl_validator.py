"""Tests for tmdl_validator (TMDL structural validation + readiness assessment)."""

from __future__ import annotations

import json

import pytest

from src.agents.validation.tmdl_validator import (
    ReadinessAssessment,
    ReadinessCheck,
    TMDLValidationResult,
    assess_migration_readiness,
    validate_tmdl_structure,
)


# ---------------------------------------------------------------------------
# TMDL structural validation
# ---------------------------------------------------------------------------

class TestValidateTMDLStructure:
    def _valid_files(self) -> dict[str, str]:
        return {
            "model.tmdl": "model Model\n    culture: en-US",
            ".platform": json.dumps({
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel"},
                "config": {"logicalId": "abc"},
            }),
            "definition/tables/sales.tmdl": "table 'Sales'\n    lineageTag: abc\n    column ID\n        dataType: int64",
        }

    def test_valid_structure_passes(self):
        result = validate_tmdl_structure(self._valid_files())
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.table_count == 1

    def test_missing_model_tmdl(self):
        files = self._valid_files()
        del files["model.tmdl"]
        result = validate_tmdl_structure(files)
        assert result.valid is False
        assert any("model.tmdl" in e for e in result.errors)

    def test_missing_platform(self):
        files = self._valid_files()
        del files[".platform"]
        result = validate_tmdl_structure(files)
        assert result.valid is False

    def test_missing_tables_dir(self):
        files = {
            "model.tmdl": "model Model\n    culture: en-US",
            ".platform": json.dumps({"$schema": "x", "metadata": {}, "config": {}}),
        }
        result = validate_tmdl_structure(files)
        assert result.valid is False
        assert any("tables" in e for e in result.errors)

    def test_invalid_platform_json(self):
        files = self._valid_files()
        files[".platform"] = "not json"
        result = validate_tmdl_structure(files)
        assert result.valid is False

    def test_platform_missing_keys(self):
        files = self._valid_files()
        files[".platform"] = json.dumps({"$schema": "x"})
        result = validate_tmdl_structure(files)
        assert result.valid is False

    def test_model_missing_declaration(self):
        files = self._valid_files()
        files["model.tmdl"] = "culture: en-US"
        result = validate_tmdl_structure(files)
        assert result.valid is False

    def test_table_missing_declaration(self):
        files = self._valid_files()
        files["definition/tables/bad.tmdl"] = "column ID\n    dataType: int64"
        result = validate_tmdl_structure(files)
        assert result.valid is False

    def test_culture_warning(self):
        files = self._valid_files()
        files["model.tmdl"] = "model Model"
        result = validate_tmdl_structure(files)
        assert any("culture" in w for w in result.warnings)

    def test_lineage_tag_warning(self):
        files = self._valid_files()
        files["definition/tables/no_lineage.tmdl"] = "table 'NoLineage'\n    column ID"
        result = validate_tmdl_structure(files)
        assert any("lineageTag" in w for w in result.warnings)

    def test_empty_table_warning(self):
        files = self._valid_files()
        files["definition/tables/empty.tmdl"] = "table 'Empty'\n    lineageTag: x"
        result = validate_tmdl_structure(files)
        assert any("no columns" in w for w in result.warnings)

    def test_file_count(self):
        files = self._valid_files()
        result = validate_tmdl_structure(files)
        assert result.file_count == 3


# ---------------------------------------------------------------------------
# Pre-migration readiness assessment
# ---------------------------------------------------------------------------

class TestMigrationReadiness:
    def test_all_supported(self):
        inventory = {
            "connections": ["oracle", "postgresql"],
            "chart_types": ["table", "line"],
            "expressions": ["SUM(Sales[Amount])"],
            "parameters": [],
            "data_blending": [],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.is_ready is True
        assert result.passed == 8

    def test_unsupported_connector_fails(self):
        inventory = {
            "connections": ["oracle", "sap_hana_custom"],
            "chart_types": [],
            "expressions": [],
            "parameters": [],
            "data_blending": [],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.is_ready is False
        assert result.failures >= 1

    def test_unsupported_charts_warn(self):
        inventory = {
            "connections": [],
            "chart_types": ["table", "mysteryChart"],
            "expressions": [],
            "parameters": [],
            "data_blending": [],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.warnings >= 1

    def test_blocked_functions_fail(self):
        inventory = {
            "connections": [],
            "chart_types": [],
            "expressions": ["EVALUATE_PREDICATE(something)"],
            "parameters": [],
            "data_blending": [],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.is_ready is False

    def test_many_parameters_warn(self):
        inventory = {
            "connections": [],
            "chart_types": [],
            "expressions": [],
            "parameters": list(range(15)),
            "data_blending": [],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.warnings >= 1

    def test_data_blending_warns(self):
        inventory = {
            "connections": [],
            "chart_types": [],
            "expressions": [],
            "parameters": [],
            "data_blending": [{"src": "A", "dst": "B"}],
            "dashboard_features": {},
            "security_roles": [],
            "filters": [],
        }
        result = assess_migration_readiness(inventory)
        assert result.warnings >= 1

    def test_empty_inventory(self):
        result = assess_migration_readiness({})
        assert result.is_ready is True
        assert len(result.checks) == 8
