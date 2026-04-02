"""Discovery Agent — Agent 01.

Implements the full discovery lifecycle:
  1. Authenticate to OAC (OAuth2)
  2. Crawl catalog recursively (paginated)
  3. Parse RPD XML export
  4. Build dependency graph
  5. Calculate complexity scores
  6. Write inventory to Lakehouse Delta table
  7. Generate summary report
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.base_agent import MigrationAgent
from src.core.config import settings
from src.core.models import (
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    ValidationReport,
)

from .ai_assessor import AIAssessor, AssessmentResult
from .assessment_narrator import AssessmentNarrator
from .complexity_scorer import score_all
from .dependency_graph import DependencyGraph
from .oac_client import OACClient
from .rpd_parser import RPDParser

logger = logging.getLogger(__name__)


class DiscoveryAgent(MigrationAgent):
    """Agent 01 — Discovery & Inventory."""

    def __init__(
        self,
        oac_client: OACClient | None = None,
        rpd_xml_path: str | None = None,
        lakehouse_client: Any | None = None,
    ) -> None:
        super().__init__(agent_id="agent-01", agent_name="Discovery & Inventory Agent")
        self._oac = oac_client or OACClient()
        self._rpd_path = rpd_xml_path or settings.rpd_xml_path
        self._lakehouse = lakehouse_client
        self._dep_graph = DependencyGraph()
        self._assessment: AssessmentResult | None = None
        self._ai_assessor = AIAssessor()

    # ------------------------------------------------------------------
    # MigrationAgent interface
    # ------------------------------------------------------------------

    async def discover(self, scope: MigrationScope) -> Inventory:
        """Run the complete OAC discovery.

        Steps:
          1. Crawl OAC catalog API
          2. Parse RPD XML (if available)
          3. Merge, deduplicate
          4. Build dependency graph
          5. Score complexity
        """
        all_items: list[InventoryItem] = []

        # --- 1. OAC REST API catalog crawl ---
        async with self._oac as client:
            for include_path in scope.include_paths or ["/shared"]:
                api_items = await client.discover_catalog_assets(path=include_path)
                all_items.extend(api_items)

            # Connections
            conn_items = await client.discover_connections()
            all_items.extend(conn_items)

        logger.info("API discovery: %d items", len(all_items))

        # --- 2. RPD XML ---
        if self._rpd_path and Path(self._rpd_path).exists():
            try:
                rpd = RPDParser(self._rpd_path)
                rpd_items = rpd.parse()
                all_items.extend(rpd_items)
                logger.info("RPD discovery: %d items", len(rpd_items))
            except Exception:
                logger.exception("RPD parsing failed — continuing with API items only")
        else:
            logger.info("No RPD XML path configured — skipping RPD parsing")

        # --- 3. Deduplicate by id ---
        seen: dict[str, InventoryItem] = {}
        for item in all_items:
            existing = seen.get(item.id)
            if existing is None:
                seen[item.id] = item
            else:
                # Merge: prefer API metadata, keep RPD dependencies
                existing.dependencies.extend(item.dependencies)
                existing.metadata.update(item.metadata)
        all_items = list(seen.values())
        logger.info("After dedup: %d unique items", len(all_items))

        # --- 4. Apply scope filters ---
        if scope.asset_types:
            all_items = [i for i in all_items if i.asset_type in scope.asset_types]
        if scope.exclude_paths:
            all_items = [
                i
                for i in all_items
                if not any(i.source_path.startswith(ex) for ex in scope.exclude_paths)
            ]

        # --- 5. Build dependency graph ---
        self._dep_graph = DependencyGraph()
        self._dep_graph.build(all_items)
        logger.info("Dependency graph: %s", self._dep_graph.summary())

        # --- 6. Score complexity ---
        all_items = score_all(all_items)

        # --- 7. AI-powered assessment (Phase 71) ---
        try:
            # Flatten adjacency list to {id: [dep_ids]} for assessor
            raw_adj = self._dep_graph.to_adjacency_list()
            dep_adj: dict[str, list[str]] = {
                src: [d["target_id"] for d in deps]
                for src, deps in raw_adj.items()
            }
            self._assessment = self._ai_assessor.assess(
                Inventory(items=all_items), dep_adj
            )
            logger.info(
                "AI assessment: %d risks, %d anomalies, %d strategies",
                len(self._assessment.risk_heatmap),
                self._assessment.anomaly_count,
                len(self._assessment.strategy_recommendations),
            )
        except Exception:
            logger.exception("AI assessment failed — continuing without enrichment")
            self._assessment = None

        # --- 8. Build inventory ---
        inventory = Inventory(items=all_items)
        logger.info(
            "Discovery complete: %d items, graph: %d nodes / %d edges",
            inventory.count,
            self._dep_graph.node_count,
            self._dep_graph.edge_count,
        )
        return inventory

    async def plan(self, inventory: Inventory) -> MigrationPlan:
        """For the discovery agent, the 'plan' is to write everything to Lakehouse."""
        return MigrationPlan(
            agent_id=self.agent_id,
            items=inventory.items,
            estimated_duration_minutes=max(1, inventory.count // 50),
        )

    async def execute(self, plan: MigrationPlan) -> MigrationResult:
        """Write the discovered inventory to the Lakehouse Delta table."""
        result = MigrationResult(agent_id=self.agent_id, total=len(plan.items))

        if self._lakehouse is None:
            logger.warning("No Lakehouse client — skipping persistence. Returning dry-run result.")
            result.succeeded = len(plan.items)
            result.completed_at = datetime.now(timezone.utc)
            return result

        try:
            written = self._lakehouse.write_inventory(plan.items)
            result.succeeded = written
            logger.info("Wrote %d items to migration_inventory", written)
        except Exception as exc:
            logger.exception("Lakehouse write failed")
            result.failed = len(plan.items)
            result.errors.append({"error": str(exc)})

        result.completed_at = datetime.now(timezone.utc)
        return result

    async def validate(self, result: MigrationResult) -> ValidationReport:
        """Validate that inventory was written correctly."""
        report = ValidationReport(agent_id=self.agent_id)

        # Check 1: all items written
        report.total_checks += 1
        if result.failed == 0:
            report.passed += 1
        else:
            report.failed += 1
            report.details.append({"check": "all_items_written", "status": "FAIL", "errors": result.errors})

        # Check 2: dependency graph is acyclic
        report.total_checks += 1
        if not self._dep_graph.has_cycles():
            report.passed += 1
        else:
            report.warnings += 1
            report.details.append({"check": "no_cycles", "status": "WARN", "message": "Dependency graph has cycles"})

        # Check 3: verify counts in Lakehouse (if available)
        if self._lakehouse is not None:
            report.total_checks += 1
            lh_count = self._lakehouse.count_inventory()
            if lh_count >= result.succeeded:
                report.passed += 1
            else:
                report.failed += 1
                report.details.append({
                    "check": "lakehouse_count",
                    "status": "FAIL",
                    "expected": result.succeeded,
                    "actual": lh_count,
                })

        return report

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def dependency_graph(self) -> DependencyGraph:
        return self._dep_graph

    @property
    def assessment(self) -> AssessmentResult | None:
        """AI assessment result from Phase 71 (None if not yet run)."""
        return self._assessment

    def generate_summary_report(self, inventory: Inventory) -> str:
        """Generate a Markdown summary report."""
        graph_info = self._dep_graph.summary()

        lines = [
            "# Discovery Summary Report",
            "",
            f"**Generated at:** {datetime.now(timezone.utc).isoformat()}Z",
            f"**Total assets discovered:** {inventory.count}",
            "",
            "## Asset Breakdown by Type",
            "",
            "| Asset Type | Count |",
            "|---|---|",
        ]

        type_counts: dict[str, int] = {}
        for item in inventory.items:
            type_counts[item.asset_type.value] = type_counts.get(item.asset_type.value, 0) + 1
        for at, cnt in sorted(type_counts.items()):
            lines.append(f"| {at} | {cnt} |")

        lines.extend([
            "",
            "## Complexity Distribution",
            "",
            "| Category | Count |",
            "|---|---|",
        ])
        complexity_counts: dict[str, int] = {}
        for item in inventory.items:
            complexity_counts[item.complexity_category.value] = (
                complexity_counts.get(item.complexity_category.value, 0) + 1
            )
        for cat in ("Low", "Medium", "High"):
            lines.append(f"| {cat} | {complexity_counts.get(cat, 0)} |")

        lines.extend([
            "",
            "## Dependency Graph",
            "",
            f"- **Nodes:** {graph_info['total_nodes']}",
            f"- **Edges:** {graph_info['total_edges']}",
            f"- **Connected components:** {graph_info['connected_components']}",
            f"- **Has cycles:** {graph_info['has_cycles']}",
            f"- **Root assets (no deps):** {graph_info['root_count']}",
            f"- **Leaf assets:** {graph_info['leaf_count']}",
            "",
            "## High-Complexity Assets (score > 6.0)",
            "",
            "| Name | Type | Score | Path |",
            "|---|---|---|---|",
        ])
        for item in sorted(inventory.items, key=lambda i: i.complexity_score, reverse=True):
            if item.complexity_score > 6.0:
                lines.append(f"| {item.name} | {item.asset_type.value} | {item.complexity_score} | {item.source_path} |")

        # --- AI Assessment section (Phase 71) ---
        if self._assessment is not None:
            narrator = AssessmentNarrator()
            narrative = narrator.generate(self._assessment)
            lines.extend(["", "---", "", narrative.markdown])

        lines.append("")
        return "\n".join(lines)
