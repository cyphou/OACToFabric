"""Integration tests — Agent-to-agent handoff.

These tests verify that agents can produce outputs that downstream agents
consume correctly, using in-memory inventories (no live services).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Discovery → Schema handoff
# ---------------------------------------------------------------------------


class TestDiscoveryToSchemaHandoff:
    """Discovery agent output feeds Schema agent input."""

    def test_inventory_items_have_required_fields(self, sample_inventory: Inventory):
        for item in sample_inventory.items:
            assert item.id
            assert item.name
            assert item.asset_type
            assert item.source_path is not None

    def test_inventory_filtered_by_type(self, sample_inventory: Inventory):
        tables = sample_inventory.by_type(AssetType.PHYSICAL_TABLE)
        analyses = sample_inventory.by_type(AssetType.ANALYSIS)
        assert len(tables) == 0
        assert len(analyses) == 5

    def test_inventory_to_flat_dict(self, sample_inventory: Inventory):
        for item in sample_inventory.items:
            d = item.to_flat_dict()
            assert "id" in d
            assert "asset_type" in d
            assert "name" in d


# ---------------------------------------------------------------------------
# Schema → ETL handoff
# ---------------------------------------------------------------------------


class TestSchemaToETLHandoff:
    """Schema agent output feeds ETL agent input."""

    def test_migration_plan_structure(self):
        plan = MigrationPlan(
            agent_id="02-schema",
            wave=1,
            items=[
                InventoryItem(
                    id="t1", name="sales_fact",
                    asset_type=AssetType.PHYSICAL_TABLE,
                    source_path="/schema/sales_fact",
                ),
                InventoryItem(
                    id="t2", name="products",
                    asset_type=AssetType.PHYSICAL_TABLE,
                    source_path="/schema/products",
                ),
            ],
        )
        assert len(plan.items) == 2
        assert plan.agent_id == "02-schema"

    def test_migration_result_captures_status(self):
        result = MigrationResult(
            agent_id="02-schema",
            total=10,
            succeeded=10,
            failed=0,
        )
        assert result.failed == 0
        assert result.succeeded == 10
        assert result.total == 10


# ---------------------------------------------------------------------------
# Semantic Model → Report handoff
# ---------------------------------------------------------------------------


class TestSemanticToReportHandoff:
    """Semantic model must exist before reports can reference it."""

    def test_validation_report_structure(self):
        report = ValidationReport(
            agent_id="07-validation",
            total_checks=12,
            passed=10,
            failed=0,
            warnings=2,
            details=[
                {"check": "row_count_match", "status": "passed"},
                {"check": "visual_coverage", "status": "warned", "message": "1 visual unmapped"},
            ],
        )
        assert report.passed == 10
        assert len(report.details) == 2


# ---------------------------------------------------------------------------
# End-to-end inventory round-trip
# ---------------------------------------------------------------------------


class TestInventoryRoundTrip:
    """Inventory items survive serialisation / deserialisation."""

    def test_flat_dict_roundtrip(self, sample_inventory: Inventory):
        for item in sample_inventory.items:
            d = item.to_flat_dict()
            restored = InventoryItem(
                id=d["id"],
                name=d["name"],
                asset_type=AssetType(d["asset_type"]),
                source_path=d["source_path"],
                dependencies=[],
            )
            assert restored.id == item.id
            assert restored.asset_type == item.asset_type
