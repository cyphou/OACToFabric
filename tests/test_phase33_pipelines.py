"""Tests for Phase 33 — Data Pipeline Execution & Deployment.

Covers:
- PipelineDeployer (deploy, batch deploy, dry run)
- DataCopyOrchestrator (copy tables, plan partitions)
- PartitionStrategy (should_partition, compute)
- PipelineMonitor (start/complete/retry runs)
- LandingZoneManager (create/list/cleanup folders)
- WatermarkTracker (set/get/build queries)
"""

from __future__ import annotations

import pytest

from src.deployers.pipeline_deployer import (
    CopyResult,
    CopyStrategy,
    CopyTask,
    DataCopyOrchestrator,
    LandingZoneFolder,
    LandingZoneManager,
    PartitionSpec,
    PartitionStrategy,
    PipelineDefinition,
    PipelineDeployer,
    PipelineDeployResult,
    PipelineMonitor,
    PipelineRun,
    PipelineStatus,
    WatermarkEntry,
    WatermarkTracker,
)


# ===================================================================
# PipelineDeployer
# ===================================================================

class TestPipelineDeployer:
    def setup_method(self):
        self.deployer = PipelineDeployer(workspace_id="ws-123", dry_run=False)

    @pytest.mark.asyncio
    async def test_deploy_pipeline(self):
        pipeline = PipelineDefinition(
            pipeline_id="p1", name="Sales_Copy",
            activities=[{"type": "Copy", "source": "Oracle", "sink": "OneLake"}],
        )
        result = await self.deployer.deploy(pipeline)
        assert result.status == PipelineStatus.DEPLOYED
        assert result.remote_id
        assert result.name == "Sales_Copy"

    @pytest.mark.asyncio
    async def test_deploy_dry_run(self):
        deployer = PipelineDeployer(dry_run=True)
        pipeline = PipelineDefinition(pipeline_id="p2", name="Test")
        result = await deployer.deploy(pipeline)
        assert result.status == PipelineStatus.DEPLOYED
        assert "dry-run" in result.remote_id

    @pytest.mark.asyncio
    async def test_deploy_batch(self):
        pipelines = [
            PipelineDefinition(pipeline_id=f"p{i}", name=f"Pipeline_{i}")
            for i in range(5)
        ]
        results = await self.deployer.deploy_batch(pipelines)
        assert len(results) == 5
        assert all(r.status == PipelineStatus.DEPLOYED for r in results)

    @pytest.mark.asyncio
    async def test_get_deployed(self):
        pipeline = PipelineDefinition(pipeline_id="p3", name="Test")
        await self.deployer.deploy(pipeline)
        got = self.deployer.get_deployed("p3")
        assert got is not None
        assert got.name == "Test"

    def test_deployed_count(self):
        assert self.deployer.deployed_count == 0

    def test_pipeline_definition_json(self):
        p = PipelineDefinition(
            pipeline_id="p1", name="Test",
            activities=[{"type": "Copy"}],
            parameters={"env": "prod"},
        )
        j = p.to_json()
        assert j["name"] == "Test"
        assert len(j["properties"]["activities"]) == 1

    def test_pipeline_activity_count(self):
        p = PipelineDefinition(pipeline_id="x", name="x", activities=[{}, {}, {}])
        assert p.activity_count == 3


# ===================================================================
# DataCopyOrchestrator
# ===================================================================

class TestDataCopyOrchestrator:
    def setup_method(self):
        self.orch = DataCopyOrchestrator(landing_zone="landing", max_parallel=4)

    @pytest.mark.asyncio
    async def test_copy_tables(self):
        specs = [
            {"source": "ORA.SALES", "target": "lh.Sales", "estimated_rows": 1000},
            {"source": "ORA.PRODUCTS", "target": "lh.Products", "estimated_rows": 500},
        ]
        result = await self.orch.copy_tables(specs)
        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.total_rows == 1500

    @pytest.mark.asyncio
    async def test_copy_tables_empty(self):
        result = await self.orch.copy_tables([])
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_copy_incremental(self):
        specs = [{"source": "T1", "target": "T1_LH", "estimated_rows": 100}]
        result = await self.orch.copy_tables(specs, strategy=CopyStrategy.INCREMENTAL)
        assert result.succeeded == 1

    def test_plan_partitions_small_table(self):
        parts = self.orch.plan_partitions("small_table", 100_000)
        assert len(parts) == 1
        assert parts[0]["rows"] == 100_000

    def test_plan_partitions_large_table(self):
        parts = self.orch.plan_partitions("big_table", 5_000_000, "id")
        assert len(parts) == 5
        assert all(p["column"] == "id" for p in parts)

    def test_plan_partitions_exact_boundary(self):
        parts = self.orch.plan_partitions("t", 2_000_000)
        assert len(parts) == 2

    def test_copy_result_summary(self):
        result = CopyResult(tasks=[
            CopyTask(task_id="1", source_table="A", target_table="B", status=PipelineStatus.SUCCEEDED, row_count=100),
            CopyTask(task_id="2", source_table="C", target_table="D", status=PipelineStatus.FAILED, error="timeout"),
        ])
        assert result.succeeded == 1
        assert result.failed == 1
        assert "1/2" in result.summary()


# ===================================================================
# PartitionStrategy
# ===================================================================

class TestPartitionStrategy:
    def setup_method(self):
        self.strategy = PartitionStrategy()

    def test_should_not_partition_small(self):
        assert not self.strategy.should_partition(100_000)

    def test_should_partition_large(self):
        assert self.strategy.should_partition(1_000_000)

    def test_compute_single_partition(self):
        spec = self.strategy.compute("small", 500_000)
        assert spec.partition_count == 1
        assert spec.rows_per_partition == 500_000

    def test_compute_multiple_partitions(self):
        spec = self.strategy.compute("big", 5_000_000, "created_at")
        assert spec.partition_count == 5
        assert spec.column == "created_at"
        assert spec.total_rows == 5_000_000

    def test_compute_custom_partition_size(self):
        spec = self.strategy.compute("t", 3_000_000, target_partition_size=500_000)
        assert spec.partition_count == 6


# ===================================================================
# PipelineMonitor
# ===================================================================

class TestPipelineMonitor:
    def setup_method(self):
        self.monitor = PipelineMonitor(max_retries=3)

    def test_start_run(self):
        run = self.monitor.start_run("p1")
        assert run.status == PipelineStatus.RUNNING
        assert run.pipeline_id == "p1"

    def test_complete_run_success(self):
        run = self.monitor.start_run("p1")
        completed = self.monitor.complete_run(run.run_id, success=True)
        assert completed.status == PipelineStatus.SUCCEEDED
        assert completed.completed_at is not None

    def test_complete_run_failure(self):
        run = self.monitor.start_run("p1")
        completed = self.monitor.complete_run(run.run_id, success=False, error="timeout")
        assert completed.status == PipelineStatus.FAILED
        assert completed.error == "timeout"

    def test_should_retry(self):
        run = self.monitor.start_run("p1")
        self.monitor.complete_run(run.run_id, success=False)
        assert self.monitor.should_retry(run.run_id)

    def test_should_not_retry_success(self):
        run = self.monitor.start_run("p1")
        self.monitor.complete_run(run.run_id, success=True)
        assert not self.monitor.should_retry(run.run_id)

    def test_retry_limit(self):
        run = self.monitor.start_run("p1")
        for _ in range(3):
            self.monitor.complete_run(run.run_id, success=False)
            self.monitor.record_retry(run.run_id)
        self.monitor.complete_run(run.run_id, success=False)
        assert not self.monitor.should_retry(run.run_id)

    def test_get_runs(self):
        self.monitor.start_run("p1")
        self.monitor.start_run("p1")
        self.monitor.start_run("p2")
        assert len(self.monitor.get_runs("p1")) == 2
        assert len(self.monitor.get_runs("p2")) == 1

    def test_active_runs(self):
        self.monitor.start_run("p1")
        run2 = self.monitor.start_run("p2")
        self.monitor.complete_run(run2.run_id, success=True)
        assert len(self.monitor.active_runs) == 1

    def test_should_retry_nonexistent(self):
        assert not self.monitor.should_retry("nonexistent")


# ===================================================================
# LandingZoneManager
# ===================================================================

class TestLandingZoneManager:
    def setup_method(self):
        self.mgr = LandingZoneManager(base_path="Files/staging")

    def test_create_folder(self):
        folder = self.mgr.create_folder("sales")
        assert folder.path == "Files/staging/sales"
        assert folder.table_name == "sales"

    def test_create_folders(self):
        folders = self.mgr.create_folders(["t1", "t2", "t3"])
        assert len(folders) == 3
        assert self.mgr.folder_count == 3

    def test_get_folder(self):
        self.mgr.create_folder("products")
        assert self.mgr.get_folder("products") is not None
        assert self.mgr.get_folder("nonexistent") is None

    def test_list_folders(self):
        self.mgr.create_folders(["a", "b"])
        folders = self.mgr.list_folders()
        assert len(folders) == 2

    def test_cleanup(self):
        self.mgr.create_folder("temp")
        assert self.mgr.cleanup("temp")
        assert self.mgr.folder_count == 0

    def test_cleanup_nonexistent(self):
        assert not self.mgr.cleanup("nope")


# ===================================================================
# WatermarkTracker
# ===================================================================

class TestWatermarkTracker:
    def setup_method(self):
        self.tracker = WatermarkTracker()

    def test_set_watermark(self):
        wm = self.tracker.set_watermark("sales", "updated_at", "2026-01-01T00:00:00Z")
        assert wm.table_name == "sales"
        assert wm.last_value == "2026-01-01T00:00:00Z"

    def test_get_watermark(self):
        self.tracker.set_watermark("sales", "updated_at", "2026-01-01")
        wm = self.tracker.get_watermark("sales")
        assert wm is not None
        assert wm.column_name == "updated_at"

    def test_get_nonexistent(self):
        assert self.tracker.get_watermark("nope") is None

    def test_has_watermark(self):
        self.tracker.set_watermark("t1", "col", "val")
        assert self.tracker.has_watermark("t1")
        assert not self.tracker.has_watermark("t2")

    def test_clear(self):
        self.tracker.set_watermark("t1", "col", "val")
        assert self.tracker.clear("t1")
        assert not self.tracker.has_watermark("t1")

    def test_clear_nonexistent(self):
        assert not self.tracker.clear("nope")

    def test_build_incremental_query(self):
        self.tracker.set_watermark("sales", "modified_at", "2026-01-01")
        q = self.tracker.build_incremental_query("sales")
        assert "modified_at > '2026-01-01'" in q

    def test_build_query_with_existing_where(self):
        self.tracker.set_watermark("sales", "ts", "2026-01-01")
        q = self.tracker.build_incremental_query("sales", "SELECT * FROM sales WHERE active = 1")
        assert "AND ts > '2026-01-01'" in q

    def test_build_query_no_watermark(self):
        q = self.tracker.build_incremental_query("orders")
        assert q == "SELECT * FROM orders"

    def test_tracked_tables(self):
        self.tracker.set_watermark("t1", "c", "v")
        self.tracker.set_watermark("t2", "c", "v")
        assert self.tracker.tracked_tables == 2

    def test_get_all(self):
        self.tracker.set_watermark("t1", "c1", "v1")
        self.tracker.set_watermark("t2", "c2", "v2")
        all_wm = self.tracker.get_all()
        assert len(all_wm) == 2

    def test_update_watermark(self):
        self.tracker.set_watermark("t1", "ts", "2026-01-01")
        self.tracker.set_watermark("t1", "ts", "2026-02-01")
        wm = self.tracker.get_watermark("t1")
        assert wm.last_value == "2026-02-01"
