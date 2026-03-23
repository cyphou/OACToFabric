"""Tests for Phase 31 — End-to-End Integration Testing Framework.

Covers:
- GoldenFixture model and hashing
- FixtureGenerator at all complexity levels
- OutputComparator (TMDL, PBIR, DDL, DAX, full comparison)
- IntegrationTestHarness (8-agent pipeline)
- IncrementalE2ERunner
- RollbackE2ERunner
"""

from __future__ import annotations

import json

import pytest

from src.testing.integration_harness import (
    AgentStepResult,
    ComparisonReport,
    ComparisonResult,
    E2EResult,
    FixtureComplexity,
    FixtureGenerator,
    GoldenFixture,
    IncrementalE2EResult,
    IncrementalE2ERunner,
    IntegrationTestHarness,
    OutputComparator,
    RollbackE2EResult,
    RollbackE2ERunner,
    COMPLEXITY_PARAMS,
)


# ===================================================================
# GoldenFixture
# ===================================================================

class TestGoldenFixture:
    def test_create_minimal(self):
        f = GoldenFixture(
            fixture_id="fix1",
            name="test",
            complexity=FixtureComplexity.MINIMAL,
            rpd_xml="<Repository/>",
        )
        assert f.fixture_id == "fix1"
        assert f.complexity == FixtureComplexity.MINIMAL

    def test_content_hash_deterministic(self):
        f = GoldenFixture(
            fixture_id="fix1",
            name="test",
            complexity=FixtureComplexity.SIMPLE,
            rpd_xml="<Repository><Table/></Repository>",
            expected_tmdl={"model.tmdl": "model Model"},
        )
        h1 = f.content_hash
        h2 = f.content_hash
        assert h1 == h2
        assert len(h1) == 16

    def test_content_hash_changes(self):
        f1 = GoldenFixture(fixture_id="a", name="a", complexity=FixtureComplexity.SIMPLE, rpd_xml="<A/>")
        f2 = GoldenFixture(fixture_id="b", name="b", complexity=FixtureComplexity.SIMPLE, rpd_xml="<B/>")
        assert f1.content_hash != f2.content_hash

    def test_summary(self):
        f = GoldenFixture(
            fixture_id="x", name="demo", complexity=FixtureComplexity.MODERATE,
            rpd_xml="<R/>",
            expected_tmdl={"a.tmdl": "x", "b.tmdl": "y"},
            expected_pbir={"r.json": "{}"},
            expected_ddl=["CREATE TABLE T1"],
            expected_dax_measures={"M1": "SUM(T[C])"},
        )
        s = f.summary()
        assert "demo" in s
        assert "moderate" in s
        assert "2 TMDL" in s


# ===================================================================
# FixtureGenerator
# ===================================================================

class TestFixtureGenerator:
    def setup_method(self):
        self.gen = FixtureGenerator()

    def test_generate_minimal(self):
        f = self.gen.generate(FixtureComplexity.MINIMAL)
        assert f.complexity == FixtureComplexity.MINIMAL
        assert "<Repository>" in f.rpd_xml
        assert len(f.expected_tmdl) >= 1
        assert len(f.expected_ddl) >= 1

    def test_generate_simple(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE, name="simple_test")
        assert f.name == "simple_test"
        params = COMPLEXITY_PARAMS[FixtureComplexity.SIMPLE]
        assert len(f.expected_ddl) == params["tables"]
        assert len(f.expected_rls_filters) == params["rls_roles"]

    def test_generate_moderate(self):
        f = self.gen.generate(FixtureComplexity.MODERATE)
        params = COMPLEXITY_PARAMS[FixtureComplexity.MODERATE]
        assert len(f.expected_ddl) == params["tables"]
        assert len(f.expected_pbir) == params["analyses"]

    def test_generate_complex(self):
        f = self.gen.generate(FixtureComplexity.COMPLEX)
        params = COMPLEXITY_PARAMS[FixtureComplexity.COMPLEX]
        assert len(f.expected_ddl) == params["tables"]

    def test_generate_enterprise(self):
        f = self.gen.generate(FixtureComplexity.ENTERPRISE)
        params = COMPLEXITY_PARAMS[FixtureComplexity.ENTERPRISE]
        assert len(f.expected_ddl) == params["tables"]

    def test_all_complexities_produce_valid_xml(self):
        for complexity in FixtureComplexity:
            f = self.gen.generate(complexity)
            assert f.rpd_xml.startswith("<?xml")
            assert "</Repository>" in f.rpd_xml

    def test_rpd_contains_physical_layer(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE)
        assert "<PhysicalLayer>" in f.rpd_xml
        assert "<PhysicalTable" in f.rpd_xml

    def test_rpd_contains_business_model(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE)
        assert "<BusinessModel>" in f.rpd_xml
        assert "<LogicalTable" in f.rpd_xml

    def test_rpd_contains_presentation(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE)
        assert "<PresentationCatalog>" in f.rpd_xml
        assert "<Analysis" in f.rpd_xml

    def test_rls_roles_generated(self):
        f = self.gen.generate(FixtureComplexity.MODERATE)
        assert len(f.expected_rls_filters) == COMPLEXITY_PARAMS[FixtureComplexity.MODERATE]["rls_roles"]
        for role, filter_expr in f.expected_rls_filters.items():
            assert "REGION" in filter_expr

    def test_dax_measures_generated(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE)
        assert len(f.expected_dax_measures) > 0
        for name, dax in f.expected_dax_measures.items():
            assert "SUM" in dax

    def test_tmdl_model_file_present(self):
        f = self.gen.generate(FixtureComplexity.SIMPLE)
        assert "model.tmdl" in f.expected_tmdl
        assert "model Model" in f.expected_tmdl["model.tmdl"]

    def test_unique_fixture_ids(self):
        ids = {self.gen.generate(FixtureComplexity.MINIMAL).fixture_id for _ in range(10)}
        assert len(ids) == 10

    def test_custom_name(self):
        f = self.gen.generate(FixtureComplexity.MINIMAL, name="custom_fixture")
        assert f.name == "custom_fixture"


# ===================================================================
# OutputComparator
# ===================================================================

class TestOutputComparator:
    def setup_method(self):
        self.comp = OutputComparator()

    def test_tmdl_exact_match(self):
        expected = {"a.tmdl": "table T\n  col C\n"}
        actual = {"a.tmdl": "table T\n  col C\n"}
        results = self.comp.compare_tmdl(expected, actual)
        assert len(results) == 1
        assert results[0].match

    def test_tmdl_whitespace_match(self):
        expected = {"a.tmdl": "table  T\n  col C"}
        actual = {"a.tmdl": "table T\n  col  C"}
        results = self.comp.compare_tmdl(expected, actual)
        assert results[0].match  # normalized comparison

    def test_tmdl_mismatch(self):
        expected = {"a.tmdl": "table T\n  col C\n"}
        actual = {"a.tmdl": "table T\n  col D\n"}
        results = self.comp.compare_tmdl(expected, actual)
        assert not results[0].match
        assert results[0].diff_lines > 0

    def test_tmdl_missing_file(self):
        expected = {"a.tmdl": "x", "b.tmdl": "y"}
        actual = {"a.tmdl": "x"}
        results = self.comp.compare_tmdl(expected, actual)
        assert len(results) == 2
        assert not results[1].match  # b.tmdl missing in actual

    def test_tmdl_extra_file(self):
        expected = {"a.tmdl": "x"}
        actual = {"a.tmdl": "x", "b.tmdl": "y"}
        results = self.comp.compare_tmdl(expected, actual)
        assert len(results) == 2

    def test_ddl_match(self):
        expected = ["CREATE TABLE T1 (C1 STRING)"]
        actual = ["CREATE TABLE T1 (C1 STRING)"]
        results = self.comp.compare_ddl(expected, actual)
        assert results[0].match

    def test_ddl_mismatch(self):
        expected = ["CREATE TABLE T1 (C1 STRING)"]
        actual = ["CREATE TABLE T2 (C1 STRING)"]
        results = self.comp.compare_ddl(expected, actual)
        assert not results[0].match

    def test_ddl_different_count(self):
        expected = ["CREATE T1", "CREATE T2"]
        actual = ["CREATE T1"]
        results = self.comp.compare_ddl(expected, actual)
        assert len(results) == 2
        assert not results[1].match

    def test_dax_match(self):
        expected = {"M1": "SUM(T[C])"}
        actual = {"M1": "SUM(T[C])"}
        results = self.comp.compare_dax(expected, actual)
        assert results[0].match

    def test_dax_mismatch(self):
        expected = {"M1": "SUM(T[C])"}
        actual = {"M1": "COUNT(T[C])"}
        results = self.comp.compare_dax(expected, actual)
        assert not results[0].match

    def test_compare_all(self):
        gen = FixtureGenerator()
        fixture = gen.generate(FixtureComplexity.MINIMAL)
        report = self.comp.compare_all(
            fixture,
            actual_tmdl=fixture.expected_tmdl,
            actual_pbir=fixture.expected_pbir,
            actual_ddl=fixture.expected_ddl,
            actual_dax=fixture.expected_dax_measures,
        )
        assert report.all_match
        assert report.mismatched == 0

    def test_compare_all_with_mismatch(self):
        gen = FixtureGenerator()
        fixture = gen.generate(FixtureComplexity.SIMPLE)
        bad_dax = {k: "WRONG" for k in fixture.expected_dax_measures}
        report = self.comp.compare_all(
            fixture,
            actual_tmdl=fixture.expected_tmdl,
            actual_pbir=fixture.expected_pbir,
            actual_ddl=fixture.expected_ddl,
            actual_dax=bad_dax,
        )
        assert not report.all_match
        assert report.mismatched > 0
        assert len(report.mismatches()) > 0

    def test_comparison_report_summary(self):
        report = ComparisonReport(results=[
            ComparisonResult(category="tmdl", item_name="a", match=True),
            ComparisonResult(category="tmdl", item_name="b", match=False, diff_lines=3),
        ])
        s = report.summary()
        assert "1/2 match" in s
        assert "1 mismatches" in s

    def test_pbir_comparison(self):
        expected = {"r.json": '{"name": "R1"}'}
        actual = {"r.json": '{"name": "R1"}'}
        results = self.comp.compare_pbir(expected, actual)
        assert results[0].match


# ===================================================================
# IntegrationTestHarness
# ===================================================================

class TestIntegrationTestHarness:
    def setup_method(self):
        self.harness = IntegrationTestHarness()
        self.gen = FixtureGenerator()

    @pytest.mark.asyncio
    async def test_run_minimal_fixture(self):
        fixture = self.gen.generate(FixtureComplexity.MINIMAL)
        result = await self.harness.run(fixture)
        assert result.success
        assert len(result.steps) == 8
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_run_simple_fixture(self):
        fixture = self.gen.generate(FixtureComplexity.SIMPLE)
        result = await self.harness.run(fixture)
        assert result.success
        assert all(s.success for s in result.steps)

    @pytest.mark.asyncio
    async def test_run_moderate_fixture(self):
        fixture = self.gen.generate(FixtureComplexity.MODERATE)
        result = await self.harness.run(fixture)
        assert result.success

    @pytest.mark.asyncio
    async def test_all_agents_in_sequence(self):
        fixture = self.gen.generate(FixtureComplexity.SIMPLE)
        result = await self.harness.run(fixture)
        agent_ids = [s.agent_id for s in result.steps]
        assert agent_ids == IntegrationTestHarness.AGENT_SEQUENCE

    @pytest.mark.asyncio
    async def test_each_step_has_items(self):
        fixture = self.gen.generate(FixtureComplexity.SIMPLE)
        result = await self.harness.run(fixture)
        for step in result.steps:
            assert step.items_processed >= 0
            assert step.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_result_summary(self):
        fixture = self.gen.generate(FixtureComplexity.MINIMAL)
        result = await self.harness.run(fixture)
        s = result.summary()
        assert "PASS" in s
        assert "8/8" in s

    @pytest.mark.asyncio
    async def test_total_duration(self):
        fixture = self.gen.generate(FixtureComplexity.MINIMAL)
        result = await self.harness.run(fixture)
        assert result.total_duration >= 0

    @pytest.mark.asyncio
    async def test_pre_and_post_hooks(self):
        called = {"pre": False, "post": False}
        self.harness.add_pre_hook(lambda f: called.__setitem__("pre", True))
        self.harness.add_post_hook(lambda r: called.__setitem__("post", True))
        fixture = self.gen.generate(FixtureComplexity.MINIMAL)
        await self.harness.run(fixture)
        assert called["pre"]
        assert called["post"]

    def test_run_comparison(self):
        fixture = self.gen.generate(FixtureComplexity.SIMPLE)
        report = self.harness.run_comparison(
            fixture,
            fixture.expected_tmdl,
            fixture.expected_pbir,
            fixture.expected_ddl,
            fixture.expected_dax_measures,
        )
        assert report.all_match

    def test_run_comparison_mismatch(self):
        fixture = self.gen.generate(FixtureComplexity.SIMPLE)
        bad_ddl = ["WRONG DDL" for _ in fixture.expected_ddl]
        report = self.harness.run_comparison(
            fixture,
            fixture.expected_tmdl,
            fixture.expected_pbir,
            bad_ddl,
            fixture.expected_dax_measures,
        )
        assert not report.all_match

    def test_agent_step_result(self):
        step = AgentStepResult(
            agent_id="01-discovery", step_name="run_01", success=True,
            duration_seconds=1.5, items_processed=10,
        )
        assert step.success
        assert step.items_processed == 10


# ===================================================================
# IncrementalE2ERunner
# ===================================================================

class TestIncrementalE2ERunner:
    def setup_method(self):
        self.runner = IncrementalE2ERunner()

    @pytest.mark.asyncio
    async def test_incremental_run(self):
        result = await self.runner.run(FixtureComplexity.SIMPLE)
        assert result.success
        assert result.baseline_run is not None
        assert result.delta_run is not None
        assert result.delta_asset_count > 0
        assert result.unchanged_asset_count >= 0

    @pytest.mark.asyncio
    async def test_incremental_summary(self):
        result = await self.runner.run(FixtureComplexity.MINIMAL)
        s = result.summary()
        assert "Incremental" in s

    @pytest.mark.asyncio
    async def test_incremental_detects_changes(self):
        result = await self.runner.run(FixtureComplexity.SIMPLE)
        # Modified fixture adds 1 new table
        assert result.delta_asset_count >= 1

    def test_incremental_result_model(self):
        r = IncrementalE2EResult()
        assert not r.success  # no runs yet
        s = r.summary()
        assert "FAIL" in s


# ===================================================================
# RollbackE2ERunner
# ===================================================================

class TestRollbackE2ERunner:
    def setup_method(self):
        self.runner = RollbackE2ERunner()

    @pytest.mark.asyncio
    async def test_rollback_run(self):
        result = await self.runner.run(FixtureComplexity.SIMPLE)
        assert result.success
        assert result.deploy_run is not None
        assert result.rollback_success
        assert result.state_clean
        assert result.actions_reversed > 0

    @pytest.mark.asyncio
    async def test_rollback_summary(self):
        result = await self.runner.run(FixtureComplexity.MINIMAL)
        s = result.summary()
        assert "Rollback" in s

    def test_rollback_result_model(self):
        r = RollbackE2EResult()
        assert not r.success  # no deploy yet
        assert r.actions_reversed == 0
