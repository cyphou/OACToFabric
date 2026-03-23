"""Shared fixtures for integration tests."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio

from src.core.models import (
    AssetType,
    Inventory,
    InventoryItem,
    MigrationScope,
    MigrationPlan,
    MigrationResult,
    ValidationReport,
)


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    d = tmp_path / "integration_output"
    d.mkdir()
    return d


@pytest.fixture
def sample_scope() -> MigrationScope:
    return MigrationScope(
        include_paths=["/shared/sales"],
        exclude_paths=[],
        asset_types=[AssetType.ANALYSIS, AssetType.DASHBOARD],
        wave=1,
    )


@pytest.fixture
def sample_inventory() -> Inventory:
    items = [
        InventoryItem(
            id=f"item-{i}",
            name=f"Item {i}",
            asset_type=AssetType.ANALYSIS,
            source_path=f"/shared/sales/analysis_{i}",
            dependencies=[],
        )
        for i in range(5)
    ]
    return Inventory(items=items)


@pytest.fixture
def small_inventory() -> Inventory:
    return Inventory(
        items=[
            InventoryItem(
                id="single-item",
                name="Single Item",
                asset_type=AssetType.PHYSICAL_TABLE,
                source_path="/schema/table1",
                dependencies=[],
            )
        ]
    )
