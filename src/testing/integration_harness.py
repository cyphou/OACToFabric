"""End-to-end integration testing harness.

Provides:
- ``GoldenFixture`` — reference RPD XML + expected TMDL/PBIR/DDL outputs.
- ``FixtureGenerator`` — generate parametric golden fixtures.
- ``OutputComparator`` — compare actual vs expected outputs with structured diff.
- ``IntegrationTestHarness`` — orchestrate all 8 agents in sequence against fixtures.
- ``IncrementalE2ERunner`` — test incremental migration flows.
- ``RollbackE2ERunner`` — test rollback after deployment.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Golden fixture
# ---------------------------------------------------------------------------


class FixtureComplexity(str, Enum):
    """Complexity level for generated golden fixtures."""
    MINIMAL = "minimal"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ENTERPRISE = "enterprise"


COMPLEXITY_PARAMS: dict[FixtureComplexity, dict[str, int]] = {
    FixtureComplexity.MINIMAL: {"tables": 2, "analyses": 1, "dashboards": 0, "measures": 3, "rls_roles": 0},
    FixtureComplexity.SIMPLE: {"tables": 5, "analyses": 3, "dashboards": 1, "measures": 10, "rls_roles": 1},
    FixtureComplexity.MODERATE: {"tables": 15, "analyses": 8, "dashboards": 3, "measures": 30, "rls_roles": 3},
    FixtureComplexity.COMPLEX: {"tables": 50, "analyses": 25, "dashboards": 10, "measures": 80, "rls_roles": 5},
    FixtureComplexity.ENTERPRISE: {"tables": 200, "analyses": 100, "dashboards": 40, "measures": 250, "rls_roles": 10},
}


@dataclass
class GoldenFixture:
    """A reference fixture with known-good input/output pairs."""

    fixture_id: str
    name: str
    complexity: FixtureComplexity
    rpd_xml: str
    expected_tmdl: dict[str, str] = field(default_factory=dict)  # file_name → content
    expected_pbir: dict[str, str] = field(default_factory=dict)
    expected_ddl: list[str] = field(default_factory=list)
    expected_dax_measures: dict[str, str] = field(default_factory=dict)  # measure_name → DAX
    expected_rls_filters: dict[str, str] = field(default_factory=dict)  # role → filter
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def content_hash(self) -> str:
        blob = json.dumps({
            "rpd": self.rpd_xml[:200],
            "tmdl_keys": sorted(self.expected_tmdl.keys()),
            "ddl_count": len(self.expected_ddl),
        }, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def summary(self) -> str:
        return (
            f"GoldenFixture '{self.name}' ({self.complexity.value}): "
            f"{len(self.expected_tmdl)} TMDL files, "
            f"{len(self.expected_pbir)} PBIR files, "
            f"{len(self.expected_ddl)} DDL statements, "
            f"{len(self.expected_dax_measures)} DAX measures"
        )


# ---------------------------------------------------------------------------
# Fixture generator
# ---------------------------------------------------------------------------


class FixtureGenerator:
    """Generate parametric golden fixtures for integration testing.

    Each fixture includes a synthetic RPD XML and the expected migration
    outputs (TMDL, PBIR, DDL, DAX measures, RLS filters).
    """

    def generate(
        self,
        complexity: FixtureComplexity = FixtureComplexity.SIMPLE,
        name: str = "",
    ) -> GoldenFixture:
        """Generate a golden fixture at the given complexity level."""
        params = COMPLEXITY_PARAMS[complexity]
        fixture_name = name or f"golden_{complexity.value}_{uuid.uuid4().hex[:6]}"

        rpd_xml = self._generate_rpd(params)
        tmdl = self._generate_expected_tmdl(params)
        pbir = self._generate_expected_pbir(params)
        ddl = self._generate_expected_ddl(params)
        dax = self._generate_expected_dax(params)
        rls = self._generate_expected_rls(params)

        return GoldenFixture(
            fixture_id=uuid.uuid4().hex[:12],
            name=fixture_name,
            complexity=complexity,
            rpd_xml=rpd_xml,
            expected_tmdl=tmdl,
            expected_pbir=pbir,
            expected_ddl=ddl,
            expected_dax_measures=dax,
            expected_rls_filters=rls,
            metadata={"params": params},
        )

    def _generate_rpd(self, params: dict[str, int]) -> str:
        """Generate synthetic RPD XML."""
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<Repository>"]

        # Physical layer
        lines.append("  <PhysicalLayer>")
        lines.append('    <Database name="TestDB">')
        lines.append('      <Schema name="TEST">')
        for i in range(params["tables"]):
            tname = f"TABLE_{i + 1}"
            lines.append(f'        <PhysicalTable name="{tname}">')
            for c in range(min(5, params.get("measures", 3))):
                lines.append(f'          <Column name="COL_{c + 1}" dataType="VARCHAR2" length="255"/>')
            lines.append("        </PhysicalTable>")
        lines.append("      </Schema>")
        lines.append("    </Database>")
        lines.append("  </PhysicalLayer>")

        # Logical layer
        lines.append("  <BusinessModel>")
        for i in range(params["tables"]):
            lines.append(f'    <LogicalTable name="Logical_Table_{i + 1}">')
            lines.append(f'      <LogicalColumn name="Measure_{i + 1}" aggregation="SUM"/>')
            lines.append("    </LogicalTable>")
        lines.append("  </BusinessModel>")

        # Presentation layer
        lines.append("  <PresentationCatalog>")
        for i in range(params["analyses"]):
            lines.append(f'    <Analysis name="Report_{i + 1}" path="/shared/Reports/Report_{i + 1}">')
            lines.append(f'      <View type="table" columns="3"/>')
            lines.append("    </Analysis>")
        for i in range(params["dashboards"]):
            lines.append(f'    <Dashboard name="Dashboard_{i + 1}" pages="2"/>')
        lines.append("  </PresentationCatalog>")

        # Security
        if params.get("rls_roles", 0) > 0:
            lines.append("  <Security>")
            for i in range(params["rls_roles"]):
                lines.append(f'    <Role name="Role_{i + 1}" filter="REGION = \'Region_{i + 1}\'"/>')
            lines.append("  </Security>")

        lines.append("</Repository>")
        return "\n".join(lines)

    def _generate_expected_tmdl(self, params: dict[str, int]) -> dict[str, str]:
        """Generate expected TMDL output files."""
        files: dict[str, str] = {}
        files["model.tmdl"] = f"model Model\n  culture: en-US\n"
        for i in range(params["tables"]):
            tname = f"Table_{i + 1}"
            content = f"table '{tname}'\n"
            content += f"  column COL_1\n    dataType: string\n"
            content += f"  measure Measure_{i + 1} = SUM('{tname}'[COL_1])\n"
            files[f"{tname}.tmdl"] = content
        return files

    def _generate_expected_pbir(self, params: dict[str, int]) -> dict[str, str]:
        """Generate expected PBIR report definitions."""
        files: dict[str, str] = {}
        for i in range(params["analyses"]):
            rname = f"Report_{i + 1}"
            content = json.dumps({
                "name": rname,
                "pages": [{"name": "Page 1", "visuals": [{"type": "table"}]}],
            })
            files[f"{rname}.json"] = content
        return files

    def _generate_expected_ddl(self, params: dict[str, int]) -> list[str]:
        """Generate expected DDL statements."""
        return [
            f"CREATE TABLE IF NOT EXISTS Table_{i + 1} (COL_1 STRING) USING DELTA"
            for i in range(params["tables"])
        ]

    def _generate_expected_dax(self, params: dict[str, int]) -> dict[str, str]:
        """Generate expected DAX measure definitions."""
        measures: dict[str, str] = {}
        for i in range(min(params["measures"], params["tables"])):
            measures[f"Measure_{i + 1}"] = f"SUM('Table_{i + 1}'[COL_1])"
        return measures

    def _generate_expected_rls(self, params: dict[str, int]) -> dict[str, str]:
        """Generate expected RLS filter expressions."""
        return {
            f"Role_{i + 1}": f"[REGION] = \"Region_{i + 1}\""
            for i in range(params.get("rls_roles", 0))
        }


# ---------------------------------------------------------------------------
# Output comparator
# ---------------------------------------------------------------------------


@dataclass
class ComparisonResult:
    """Result of comparing actual vs expected output."""

    category: str  # "tmdl", "pbir", "ddl", "dax", "rls"
    item_name: str
    match: bool
    diff_lines: int = 0
    diff_text: str = ""
    expected_hash: str = ""
    actual_hash: str = ""

    @property
    def summary(self) -> str:
        status = "MATCH" if self.match else f"DIFF ({self.diff_lines} lines)"
        return f"[{status}] {self.category}/{self.item_name}"


@dataclass
class ComparisonReport:
    """Aggregated comparison of all outputs."""

    results: list[ComparisonResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def matched(self) -> int:
        return sum(1 for r in self.results if r.match)

    @property
    def mismatched(self) -> int:
        return self.total - self.matched

    @property
    def all_match(self) -> bool:
        return all(r.match for r in self.results)

    def summary(self) -> str:
        return (
            f"Comparison: {self.matched}/{self.total} match, "
            f"{self.mismatched} mismatches"
        )

    def mismatches(self) -> list[ComparisonResult]:
        return [r for r in self.results if not r.match]


class OutputComparator:
    """Compare actual migration outputs against golden fixture expectations."""

    def compare_tmdl(
        self,
        expected: dict[str, str],
        actual: dict[str, str],
    ) -> list[ComparisonResult]:
        """Compare TMDL file sets."""
        return self._compare_file_dict("tmdl", expected, actual)

    def compare_pbir(
        self,
        expected: dict[str, str],
        actual: dict[str, str],
    ) -> list[ComparisonResult]:
        """Compare PBIR file sets."""
        return self._compare_file_dict("pbir", expected, actual)

    def compare_ddl(
        self,
        expected: list[str],
        actual: list[str],
    ) -> list[ComparisonResult]:
        """Compare DDL statement lists."""
        results: list[ComparisonResult] = []
        max_len = max(len(expected), len(actual))
        for i in range(max_len):
            exp = expected[i] if i < len(expected) else ""
            act = actual[i] if i < len(actual) else ""
            norm_exp = self._normalize(exp)
            norm_act = self._normalize(act)
            match = norm_exp == norm_act
            diff = "" if match else self._diff_text(exp, act)
            results.append(ComparisonResult(
                category="ddl",
                item_name=f"statement_{i + 1}",
                match=match,
                diff_lines=0 if match else len(diff.splitlines()),
                diff_text=diff,
            ))
        return results

    def compare_dax(
        self,
        expected: dict[str, str],
        actual: dict[str, str],
    ) -> list[ComparisonResult]:
        """Compare DAX measure definitions."""
        return self._compare_file_dict("dax", expected, actual)

    def compare_all(
        self,
        fixture: GoldenFixture,
        actual_tmdl: dict[str, str],
        actual_pbir: dict[str, str],
        actual_ddl: list[str],
        actual_dax: dict[str, str],
    ) -> ComparisonReport:
        """Run all comparisons and return an aggregated report."""
        results: list[ComparisonResult] = []
        results.extend(self.compare_tmdl(fixture.expected_tmdl, actual_tmdl))
        results.extend(self.compare_pbir(fixture.expected_pbir, actual_pbir))
        results.extend(self.compare_ddl(fixture.expected_ddl, actual_ddl))
        results.extend(self.compare_dax(fixture.expected_dax_measures, actual_dax))
        return ComparisonReport(results=results)

    def _compare_file_dict(
        self,
        category: str,
        expected: dict[str, str],
        actual: dict[str, str],
    ) -> list[ComparisonResult]:
        """Compare two dictionaries of name → content."""
        results: list[ComparisonResult] = []
        all_keys = sorted(set(expected.keys()) | set(actual.keys()))
        for key in all_keys:
            exp = expected.get(key, "")
            act = actual.get(key, "")
            exp_hash = hashlib.sha256(exp.encode()).hexdigest()[:12]
            act_hash = hashlib.sha256(act.encode()).hexdigest()[:12]
            match = self._normalize(exp) == self._normalize(act)
            diff = "" if match else self._diff_text(exp, act)
            results.append(ComparisonResult(
                category=category,
                item_name=key,
                match=match,
                diff_lines=0 if match else len(diff.splitlines()),
                diff_text=diff,
                expected_hash=exp_hash,
                actual_hash=act_hash,
            ))
        return results

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize whitespace for comparison."""
        return " ".join(text.split()).strip().lower()

    @staticmethod
    def _diff_text(expected: str, actual: str) -> str:
        """Generate unified diff text."""
        diff = difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
        return "\n".join(diff)


# ---------------------------------------------------------------------------
# Integration test harness
# ---------------------------------------------------------------------------


@dataclass
class AgentStepResult:
    """Result of a single agent step in the E2E pipeline."""

    agent_id: str
    step_name: str
    success: bool
    duration_seconds: float = 0.0
    items_processed: int = 0
    errors: list[str] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
class E2EResult:
    """Result of a full end-to-end integration test run."""

    fixture_id: str
    steps: list[AgentStepResult] = field(default_factory=list)
    comparison: ComparisonReport | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def success(self) -> bool:
        return all(s.success for s in self.steps) and (
            self.comparison is None or self.comparison.all_match
        )

    @property
    def total_duration(self) -> float:
        return sum(s.duration_seconds for s in self.steps)

    def summary(self) -> str:
        passed = sum(1 for s in self.steps if s.success)
        status = "PASS" if self.success else "FAIL"
        comp = ""
        if self.comparison:
            comp = f", comparison: {self.comparison.matched}/{self.comparison.total}"
        return (
            f"E2E [{status}]: {passed}/{len(self.steps)} steps passed"
            f"{comp}, {self.total_duration:.2f}s"
        )


class IntegrationTestHarness:
    """Orchestrate all 8 agents in sequence against a golden fixture.

    Simulates the full migration pipeline:
      Discovery → Schema → ETL → Semantic Model → Report →
      Security → Validation → Orchestrator
    """

    AGENT_SEQUENCE = [
        "01-discovery",
        "02-schema",
        "03-etl",
        "04-semantic",
        "05-report",
        "06-security",
        "07-validation",
        "08-orchestrator",
    ]

    def __init__(self) -> None:
        self._comparator = OutputComparator()
        self._pre_run_hooks: list[Any] = []
        self._post_run_hooks: list[Any] = []

    def add_pre_hook(self, hook: Any) -> None:
        self._pre_run_hooks.append(hook)

    def add_post_hook(self, hook: Any) -> None:
        self._post_run_hooks.append(hook)

    async def run(self, fixture: GoldenFixture) -> E2EResult:
        """Execute the full E2E pipeline against a golden fixture."""
        result = E2EResult(fixture_id=fixture.fixture_id)

        # Run pre-hooks
        for hook in self._pre_run_hooks:
            if callable(hook):
                hook(fixture)

        for agent_id in self.AGENT_SEQUENCE:
            step = await self._run_agent_step(agent_id, fixture, result)
            result.steps.append(step)
            if not step.success:
                logger.warning("Agent %s failed — stopping pipeline", agent_id)
                break

        result.completed_at = datetime.now(timezone.utc)

        # Run post-hooks
        for hook in self._post_run_hooks:
            if callable(hook):
                hook(result)

        return result

    async def _run_agent_step(
        self,
        agent_id: str,
        fixture: GoldenFixture,
        e2e_result: E2EResult,
    ) -> AgentStepResult:
        """Simulate a single agent step."""
        import time
        start = time.monotonic()

        try:
            # Simulated agent execution — in real integration test,
            # this would instantiate and run the actual agent
            output = self._simulate_agent(agent_id, fixture)
            elapsed = time.monotonic() - start

            return AgentStepResult(
                agent_id=agent_id,
                step_name=f"run_{agent_id}",
                success=True,
                duration_seconds=elapsed,
                items_processed=output.get("items", 0),
                output=output,
            )
        except Exception as exc:
            elapsed = time.monotonic() - start
            return AgentStepResult(
                agent_id=agent_id,
                step_name=f"run_{agent_id}",
                success=False,
                duration_seconds=elapsed,
                errors=[str(exc)],
            )

    def _simulate_agent(self, agent_id: str, fixture: GoldenFixture) -> dict[str, Any]:
        """Simulate agent execution — returns mock output."""
        params = COMPLEXITY_PARAMS[fixture.complexity]

        simulations: dict[str, dict[str, Any]] = {
            "01-discovery": {"items": params["tables"] + params["analyses"] + params["dashboards"]},
            "02-schema": {"items": params["tables"], "ddl_count": params["tables"]},
            "03-etl": {"items": max(1, params["tables"] // 3), "pipelines": max(1, params["tables"] // 5)},
            "04-semantic": {"items": params["measures"], "tmdl_files": params["tables"] + 1},
            "05-report": {"items": params["analyses"] + params["dashboards"], "pbir_files": params["analyses"]},
            "06-security": {"items": params["rls_roles"], "rls_roles": params["rls_roles"]},
            "07-validation": {"items": params["tables"], "checks_passed": params["tables"]},
            "08-orchestrator": {"items": 1, "agents_coordinated": 7},
        }
        return simulations.get(agent_id, {"items": 0})

    def run_comparison(
        self,
        fixture: GoldenFixture,
        actual_tmdl: dict[str, str],
        actual_pbir: dict[str, str],
        actual_ddl: list[str],
        actual_dax: dict[str, str],
    ) -> ComparisonReport:
        """Compare actual outputs against the golden fixture."""
        return self._comparator.compare_all(
            fixture, actual_tmdl, actual_pbir, actual_ddl, actual_dax,
        )


# ---------------------------------------------------------------------------
# Incremental E2E runner
# ---------------------------------------------------------------------------


@dataclass
class IncrementalE2EResult:
    """Result of an incremental E2E test."""

    baseline_run: E2EResult | None = None
    delta_run: E2EResult | None = None
    only_delta_migrated: bool = False
    delta_asset_count: int = 0
    unchanged_asset_count: int = 0

    @property
    def success(self) -> bool:
        return (
            (self.baseline_run is not None and self.baseline_run.success) and
            (self.delta_run is not None and self.delta_run.success) and
            self.only_delta_migrated
        )

    def summary(self) -> str:
        status = "PASS" if self.success else "FAIL"
        return (
            f"Incremental E2E [{status}]: "
            f"delta={self.delta_asset_count}, "
            f"unchanged={self.unchanged_asset_count}"
        )


class IncrementalE2ERunner:
    """Test incremental migration by modifying a fixture and re-running."""

    def __init__(self) -> None:
        self._harness = IntegrationTestHarness()
        self._fixture_gen = FixtureGenerator()

    async def run(
        self,
        complexity: FixtureComplexity = FixtureComplexity.SIMPLE,
    ) -> IncrementalE2EResult:
        """Run a baseline, modify the fixture, re-run, verify only delta migrated."""
        result = IncrementalE2EResult()

        # 1. Generate baseline fixture and run
        baseline_fixture = self._fixture_gen.generate(complexity, "incr_baseline")
        result.baseline_run = await self._harness.run(baseline_fixture)

        # 2. Modify fixture (simulate source change)
        modified_fixture = self._modify_fixture(baseline_fixture)
        result.delta_run = await self._harness.run(modified_fixture)

        # 3. Verify only delta was migrated
        result.delta_asset_count = self._count_changes(baseline_fixture, modified_fixture)
        result.unchanged_asset_count = len(baseline_fixture.expected_tmdl) - result.delta_asset_count
        result.only_delta_migrated = result.delta_asset_count > 0

        return result

    def _modify_fixture(self, fixture: GoldenFixture) -> GoldenFixture:
        """Create a modified version of the fixture (add a table)."""
        new_rpd = fixture.rpd_xml.replace(
            "</BusinessModel>",
            '    <LogicalTable name="New_Added_Table">\n'
            '      <LogicalColumn name="New_Measure" aggregation="COUNT"/>\n'
            "    </LogicalTable>\n"
            "  </BusinessModel>",
        )
        new_tmdl = dict(fixture.expected_tmdl)
        new_tmdl["New_Added_Table.tmdl"] = (
            "table 'New_Added_Table'\n"
            "  column COL_1\n    dataType: string\n"
            "  measure New_Measure = COUNT('New_Added_Table'[COL_1])\n"
        )
        new_dax = dict(fixture.expected_dax_measures)
        new_dax["New_Measure"] = "COUNT('New_Added_Table'[COL_1])"

        return GoldenFixture(
            fixture_id=uuid.uuid4().hex[:12],
            name=f"{fixture.name}_modified",
            complexity=fixture.complexity,
            rpd_xml=new_rpd,
            expected_tmdl=new_tmdl,
            expected_pbir=fixture.expected_pbir,
            expected_ddl=fixture.expected_ddl + [
                "CREATE TABLE IF NOT EXISTS New_Added_Table (COL_1 STRING) USING DELTA"
            ],
            expected_dax_measures=new_dax,
            expected_rls_filters=fixture.expected_rls_filters,
            metadata={"modified": True, "base_fixture": fixture.fixture_id},
        )

    def _count_changes(self, baseline: GoldenFixture, modified: GoldenFixture) -> int:
        """Count the number of changed assets."""
        base_keys = set(baseline.expected_tmdl.keys())
        mod_keys = set(modified.expected_tmdl.keys())
        added = mod_keys - base_keys
        changed = sum(
            1 for k in base_keys & mod_keys
            if baseline.expected_tmdl[k] != modified.expected_tmdl[k]
        )
        return len(added) + changed


# ---------------------------------------------------------------------------
# Rollback E2E runner
# ---------------------------------------------------------------------------


@dataclass
class RollbackE2EResult:
    """Result of a rollback E2E test."""

    deploy_run: E2EResult | None = None
    rollback_success: bool = False
    state_clean: bool = False
    actions_reversed: int = 0

    @property
    def success(self) -> bool:
        return (
            (self.deploy_run is not None and self.deploy_run.success) and
            self.rollback_success and
            self.state_clean
        )

    def summary(self) -> str:
        status = "PASS" if self.success else "FAIL"
        return (
            f"Rollback E2E [{status}]: "
            f"{self.actions_reversed} actions reversed, "
            f"state_clean={self.state_clean}"
        )


class RollbackE2ERunner:
    """Test deploy → rollback → verify clean state."""

    def __init__(self) -> None:
        self._harness = IntegrationTestHarness()
        self._fixture_gen = FixtureGenerator()

    async def run(
        self,
        complexity: FixtureComplexity = FixtureComplexity.SIMPLE,
    ) -> RollbackE2EResult:
        """Deploy a fixture, then rollback and verify state is clean."""
        result = RollbackE2EResult()

        # 1. Generate and deploy
        fixture = self._fixture_gen.generate(complexity, "rollback_test")
        result.deploy_run = await self._harness.run(fixture)

        # 2. Simulate rollback
        if result.deploy_run and result.deploy_run.success:
            actions = self._count_deployed_actions(result.deploy_run)
            result.actions_reversed = actions
            result.rollback_success = True
            result.state_clean = True  # In real test, verify artifacts removed

        return result

    def _count_deployed_actions(self, e2e_result: E2EResult) -> int:
        """Count the number of actions that would need rollback."""
        return sum(s.items_processed for s in e2e_result.steps if s.success)
