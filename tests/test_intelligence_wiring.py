"""Integration tests for Phase 71-76 intelligence wiring into agents.

Validates that:
  - Discovery Agent runs AI assessment after scoring (Phase 71).
  - Expression translator falls through to IntelligentTranslator (Phase 72).
  - Orchestrator uses MessageBus, HealingEngine, EscalationQueue (Phase 73-76).
  - Base agent handoff/healing helpers work correctly.
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.base_agent import MigrationAgent
from src.core.intelligence.escalation import EscalationQueue, ReviewStatus
from src.core.intelligence.handoff_protocol import MessageBus, MessageType
from src.core.intelligence.healing_engine import HealingEngine, HealingReport
from src.core.intelligence.orchestration import AIWavePlanner, WaveConfig
from src.core.models import (
    AgentState,
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
    MigrationPlan,
    MigrationResult,
    MigrationScope,
    RollbackResult,
    ValidationReport,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class StubAgent(MigrationAgent):
    """Concrete test agent for base_agent wiring tests."""

    async def discover(self, scope):
        return Inventory(items=[])

    async def plan(self, inventory):
        return MigrationPlan(agent_id=self.agent_id, items=[])

    async def execute(self, plan):
        return MigrationResult(agent_id=self.agent_id, total=0, succeeded=0)

    async def validate(self, result):
        return ValidationReport(agent_id=self.agent_id, total_checks=1, passed=1)


def _make_items(n: int = 5) -> list[InventoryItem]:
    return [
        InventoryItem(
            id=f"item_{i}",
            asset_type=AssetType.PHYSICAL_TABLE,
            source_path=f"/shared/table_{i}",
            name=f"Table_{i}",
            complexity_category=ComplexityCategory.LOW,
            complexity_score=2.0 + i,
        )
        for i in range(n)
    ]


# ===================================================================
# 1. Discovery Agent — AI Assessment wiring (Phase 71)
# ===================================================================


class TestDiscoveryAgentAssessment(unittest.TestCase):
    """Test that DiscoveryAgent invokes AIAssessor after scoring."""

    def test_assessment_stored_after_discover(self):
        """Assessment result is populated after discover()."""
        from src.agents.discovery.discovery_agent import DiscoveryAgent

        items = _make_items(3)
        oac_client = MagicMock()
        oac_client.__aenter__ = AsyncMock(return_value=oac_client)
        oac_client.__aexit__ = AsyncMock(return_value=False)
        oac_client.discover_catalog_assets = AsyncMock(return_value=items)
        oac_client.discover_connections = AsyncMock(return_value=[])

        agent = DiscoveryAgent(
            oac_client=oac_client,
            rpd_xml_path="",
            lakehouse_client=None,
        )

        scope = MigrationScope(include_paths=["/shared"], wave=1)
        inventory = asyncio.run(agent.discover(scope))

        # Assessment should be populated
        self.assertIsNotNone(agent.assessment)
        self.assertGreater(len(agent.assessment.risk_heatmap), 0)

    def test_assessment_none_when_assessor_fails(self):
        """Assessment is None when AIAssessor raises an exception."""
        from src.agents.discovery.discovery_agent import DiscoveryAgent

        items = _make_items(2)
        oac_client = MagicMock()
        oac_client.__aenter__ = AsyncMock(return_value=oac_client)
        oac_client.__aexit__ = AsyncMock(return_value=False)
        oac_client.discover_catalog_assets = AsyncMock(return_value=items)
        oac_client.discover_connections = AsyncMock(return_value=[])

        agent = DiscoveryAgent(
            oac_client=oac_client,
            rpd_xml_path="",
            lakehouse_client=None,
        )

        # Force the assessor to fail
        with patch.object(agent._ai_assessor, "assess", side_effect=RuntimeError("boom")):
            scope = MigrationScope(include_paths=["/shared"], wave=1)
            inventory = asyncio.run(agent.discover(scope))

        self.assertIsNone(agent.assessment)
        self.assertGreater(inventory.count, 0)

    def test_summary_report_includes_assessment(self):
        """Summary report includes AI assessment section when available."""
        from src.agents.discovery.discovery_agent import DiscoveryAgent
        from src.agents.discovery.ai_assessor import AssessmentResult, AssetRisk, RiskLevel, MigrationStrategy

        oac_client = MagicMock()
        oac_client.__aenter__ = AsyncMock(return_value=oac_client)
        oac_client.__aexit__ = AsyncMock(return_value=False)
        oac_client.discover_catalog_assets = AsyncMock(return_value=_make_items(2))
        oac_client.discover_connections = AsyncMock(return_value=[])

        agent = DiscoveryAgent(oac_client=oac_client, rpd_xml_path="", lakehouse_client=None)
        scope = MigrationScope(include_paths=["/shared"], wave=1)
        inventory = asyncio.run(agent.discover(scope))

        report = agent.generate_summary_report(inventory)
        self.assertIn("Assessment Report", report)


# ===================================================================
# 2. Expression Translator — Intelligent fallback (Phase 72)
# ===================================================================


class TestExpressionTranslatorIntelligent(unittest.TestCase):
    """Test intelligent translator wiring in expression_translator."""

    def test_high_confidence_skips_intelligent(self):
        """When rule-based confidence is high, IntelligentTranslator is not called."""
        from src.agents.semantic.expression_translator import translate_with_intelligence

        mock_intel = MagicMock()
        result = asyncio.run(translate_with_intelligence(
            expression="SUM(amount)",
            table_name="Sales",
            column_name="Total",
            intelligent_translator=mock_intel,
            confidence_threshold=0.7,
        ))
        # SUM is a known rule — should NOT call intelligent translator
        self.assertEqual(result.method, "rule-based")
        self.assertGreaterEqual(result.confidence, 0.7)
        mock_intel.translate.assert_not_called()

    def test_low_confidence_routes_to_intelligent(self):
        """When rule-based confidence is low, IntelligentTranslator is invoked."""
        from src.agents.semantic.expression_translator import translate_with_intelligence
        from src.core.intelligence.translation_agent import (
            IntelligentTranslationResult,
            TargetLanguage,
            TranslationStrategy,
        )

        # Mock the intelligent translator
        intel_result = IntelligentTranslationResult(
            source="CUSTOM_ORACLE_FUNC(x, y, z)",
            target_language=TargetLanguage.DAX,
            output="CALCULATE(SUM(x), FILTER(y, z))",
            confidence=0.85,
            strategy_used=TranslationStrategy.LLM_PRIMARY,
            valid=True,
        )
        mock_intel = MagicMock()
        mock_intel.translate = AsyncMock(return_value=intel_result)

        result = asyncio.run(translate_with_intelligence(
            expression="CUSTOM_ORACLE_FUNC(x, y, z)",
            table_name="T",
            column_name="C",
            intelligent_translator=mock_intel,
            confidence_threshold=0.7,
        ))

        mock_intel.translate.assert_called_once()
        self.assertIn("intelligent", result.method)
        self.assertEqual(result.dax_expression, "CALCULATE(SUM(x), FILTER(y, z))")
        self.assertAlmostEqual(result.confidence, 0.85)

    def test_no_intelligent_translator_returns_rule_result(self):
        """Without an IntelligentTranslator, low-confidence results are returned as-is."""
        from src.agents.semantic.expression_translator import translate_with_intelligence

        result = asyncio.run(translate_with_intelligence(
            expression="CUSTOM_ORACLE_FUNC(x, y, z)",
            table_name="T",
            column_name="C",
            intelligent_translator=None,
        ))
        self.assertEqual(result.method, "rule-based")
        self.assertLess(result.confidence, 0.7)

    def test_intelligent_translator_failure_falls_back(self):
        """If IntelligentTranslator raises, falls back to rule result."""
        from src.agents.semantic.expression_translator import translate_with_intelligence

        mock_intel = MagicMock()
        mock_intel.translate = AsyncMock(side_effect=RuntimeError("LLM down"))

        result = asyncio.run(translate_with_intelligence(
            expression="CUSTOM_ORACLE_FUNC(x, y, z)",
            table_name="T",
            column_name="C",
            intelligent_translator=mock_intel,
        ))
        self.assertEqual(result.method, "rule-based")


# ===================================================================
# 3. Base Agent — Handoff and Healing helpers (Phase 73-74)
# ===================================================================


class TestBaseAgentHandoff(unittest.TestCase):
    """Test MigrationAgent handoff integration."""

    def test_send_handoff_without_bus(self):
        """send_handoff is a no-op when no bus is attached."""
        agent = StubAgent("test-01", "Test Agent")
        result = agent.send_handoff("test-02", summary="hello")
        self.assertIsNone(result)

    def test_send_handoff_with_bus(self):
        """send_handoff sends a message via the attached bus."""
        bus = MessageBus()
        agent = StubAgent("test-01", "Test Agent")
        agent.attach_bus(bus)

        msg_id = agent.send_handoff(
            "test-02",
            message_type="artifact_ready",
            payload={"tables": 5},
            summary="Tables ready",
        )

        self.assertIsNotNone(msg_id)
        messages = bus.receive("test-02")
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender_agent, "test-01")
        self.assertEqual(messages[0].message_type, MessageType.ARTIFACT_READY)

    def test_receive_handoffs_without_bus(self):
        """receive_handoffs returns empty list when no bus."""
        agent = StubAgent("test-01", "Test Agent")
        self.assertEqual(agent.receive_handoffs(), [])

    def test_receive_handoffs_with_bus(self):
        """receive_handoffs returns messages from bus."""
        from src.core.intelligence.handoff_protocol import HandoffMessage

        bus = MessageBus()
        agent = StubAgent("test-02", "Test Agent 2")
        agent.attach_bus(bus)

        bus.send(HandoffMessage(
            sender_agent="test-01",
            receiver_agent="test-02",
            message_type=MessageType.CONTEXT_SHARE,
            payload={"info": "context"},
        ))

        messages = agent.receive_handoffs()
        self.assertEqual(len(messages), 1)


class TestBaseAgentHealing(unittest.TestCase):
    """Test MigrationAgent healing integration."""

    def test_try_heal_without_engine(self):
        """_try_heal returns False when no engine attached."""
        agent = StubAgent("test-01", "Test Agent")
        result = asyncio.run(agent._try_heal(RuntimeError("fail")))
        self.assertFalse(result)

    def test_try_heal_with_successful_healing(self):
        """_try_heal returns True when engine heals the error."""
        engine = MagicMock(spec=HealingEngine)
        engine.heal = AsyncMock(return_value=HealingReport(
            healed=True, strategy_used="retry_with_backoff",
        ))

        agent = StubAgent("test-01", "Test Agent")
        agent.attach_healing(engine)

        result = asyncio.run(agent._try_heal(RuntimeError("temp error")))
        self.assertTrue(result)
        engine.heal.assert_awaited_once()

    def test_try_heal_with_failed_healing(self):
        """_try_heal returns False when engine cannot heal."""
        engine = MagicMock(spec=HealingEngine)
        engine.heal = AsyncMock(return_value=HealingReport(
            healed=False, error_message="Cannot auto-repair",
        ))

        agent = StubAgent("test-01", "Test Agent")
        agent.attach_healing(engine)

        result = asyncio.run(agent._try_heal(RuntimeError("perm error")))
        self.assertFalse(result)

    def test_try_heal_with_engine_exception(self):
        """_try_heal returns False when engine raises."""
        engine = MagicMock(spec=HealingEngine)
        engine.heal = AsyncMock(side_effect=RuntimeError("engine crash"))

        agent = StubAgent("test-01", "Test Agent")
        agent.attach_healing(engine)

        result = asyncio.run(agent._try_heal(RuntimeError("error")))
        self.assertFalse(result)


# ===================================================================
# 4. Orchestrator — Intelligence wiring (Phase 73-76)
# ===================================================================


class TestOrchestratorIntelligence(unittest.TestCase):
    """Test orchestrator intelligence wiring."""

    def _make_orchestrator(self, runner=None, **kwargs):
        from src.agents.orchestrator.orchestrator_agent import (
            OrchestratorAgent,
            OrchestratorConfig,
        )

        config = OrchestratorConfig(
            max_retries=1,
            retry_backoff_seconds=[0],
            output_dir="output/test_orchestrator",
        )
        return OrchestratorAgent(
            config=config,
            agent_runner=runner,
            **kwargs,
        )

    def test_message_bus_available(self):
        """Orchestrator has a message bus by default."""
        orch = self._make_orchestrator()
        self.assertIsInstance(orch.message_bus, MessageBus)

    def test_escalation_queue_available(self):
        """Orchestrator has an escalation queue by default."""
        orch = self._make_orchestrator()
        self.assertIsInstance(orch.escalation_queue, EscalationQueue)

    def test_custom_bus_injected(self):
        """Custom MessageBus is used when provided."""
        bus = MessageBus()
        orch = self._make_orchestrator(message_bus=bus)
        self.assertIs(orch.message_bus, bus)

    def test_healing_engine_injected(self):
        """HealingEngine is stored when provided."""
        engine = HealingEngine()
        orch = self._make_orchestrator(healing_engine=engine)
        self.assertIs(orch._healing_engine, engine)

    def test_ai_wave_planner_injected(self):
        """AIWavePlanner is stored when provided."""
        planner = AIWavePlanner()
        orch = self._make_orchestrator(ai_wave_planner=planner)
        self.assertIs(orch._ai_wave_planner, planner)

    def test_run_migration_sends_handoff(self):
        """run_migration broadcasts discovery-complete handoff."""
        bus = MessageBus()

        call_count = 0
        async def mock_runner(agent_id, scope):
            nonlocal call_count
            call_count += 1
            return ValidationReport(agent_id=agent_id, total_checks=1, passed=1)

        orch = self._make_orchestrator(runner=mock_runner, message_bus=bus)

        scope = MigrationScope(include_paths=["/shared"], wave=1)
        asyncio.run(orch.run_migration(scope))

        # Should have at least the discovery-complete broadcast
        all_msgs = bus._all_messages
        discovery_msgs = [
            m for m in all_msgs
            if m.message_type == MessageType.ARTIFACT_READY
            and "Discovery" in (m.summary or "")
        ]
        self.assertGreater(len(discovery_msgs), 0)

    def test_escalation_on_max_retries(self):
        """Agent failure after max retries creates escalation item."""
        from src.agents.orchestrator.orchestrator_agent import (
            AgentExecutionResult,
            OrchestratorAgent,
            OrchestratorConfig,
        )
        from src.agents.orchestrator.dag_engine import NodeStatus

        queue = EscalationQueue()

        async def failing_runner(agent_id, scope):
            return ValidationReport(
                agent_id=agent_id, total_checks=1, passed=0, failed=1,
            )

        config = OrchestratorConfig(
            max_retries=1,
            retry_backoff_seconds=[0],
            output_dir="output/test_orch_esc",
        )
        orch = OrchestratorAgent(
            config=config,
            agent_runner=failing_runner,
            escalation_queue=queue,
        )

        # Directly test the retry+escalation path
        scope = MigrationScope(include_paths=["/shared"], wave=1)
        result = asyncio.run(
            orch._execute_agent_with_retry("agent-99", scope)
        )

        self.assertEqual(result.status, NodeStatus.FAILED)
        # Should have escalation items for the failed agent
        pending = queue.get_pending()
        self.assertGreater(len(pending), 0)
        self.assertEqual(pending[0].asset_id, "agent-99")


# ===================================================================
# 5. End-to-end: Assess → Translate → Heal → Escalate
# ===================================================================


class TestIntelligenceEndToEnd(unittest.TestCase):
    """End-to-end test of the intelligence pipeline."""

    def test_assess_then_escalate_critical(self):
        """Critical assessment anomalies can be escalated."""
        from src.agents.discovery.ai_assessor import (
            AIAssessor,
            AnomalyType,
            RiskLevel,
        )

        assessor = AIAssessor()
        items = _make_items(3)
        result = assessor.assess(Inventory(items=items), {})

        # Escalate any critical/high risk items
        queue = EscalationQueue()
        for risk in result.risk_heatmap:
            if risk.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                from src.core.intelligence.escalation import (
                    EscalationReason,
                    ReviewItem,
                )
                queue.escalate(ReviewItem(
                    asset_id=risk.asset_id,
                    agent_id="agent-01",
                    reason=EscalationReason.LOW_CONFIDENCE,
                    description=f"Risk score: {risk.risk_score}",
                    severity=risk.risk_level.value,
                ))

        # All items should be properly tracked
        self.assertEqual(queue.total_items, queue.pending_count)

    def test_translate_then_heal_then_escalate(self):
        """Translation failure → heal → escalate pipeline."""
        from src.agents.semantic.expression_translator import translate_expression

        # Translate something with low confidence
        result = translate_expression(
            expression="CONNECT BY hierarchical query with PRIOR parent_id",
            table_name="Employees",
            column_name="Level",
        )
        self.assertLess(result.confidence, 0.5)

        # Simulate heal attempt
        engine = HealingEngine()  # No strategies = cannot heal
        heal_report = asyncio.run(engine.heal(
            error=f"Low confidence translation: {result.confidence}",
            context={"expression": result.original_expression},
        ))
        self.assertFalse(heal_report.healed)

        # Escalate
        queue = EscalationQueue()
        from src.core.intelligence.escalation import EscalationReason, ReviewItem
        queue.escalate(ReviewItem(
            asset_id="Employees.Level",
            agent_id="agent-04",
            reason=EscalationReason.LOW_CONFIDENCE,
            description=f"DAX confidence {result.confidence:.0%}",
            confidence=result.confidence,
            source_expression=result.original_expression,
            generated_output=result.dax_expression,
        ))

        self.assertEqual(queue.pending_count, 1)
        item = queue.get_pending()[0]
        self.assertLess(item.confidence, 0.5)

    def test_bus_full_round_trip(self):
        """Messages flow from sender → bus → receiver → acknowledge → resolve."""
        bus = MessageBus()

        sender = StubAgent("agent-02", "Schema Agent")
        sender.attach_bus(bus)

        receiver = StubAgent("agent-04", "Semantic Agent")
        receiver.attach_bus(bus)

        # Send
        msg_id = sender.send_handoff(
            "agent-04",
            message_type="artifact_ready",
            payload={"tables": ["Fact_Sales"]},
            summary="Schema migration complete",
        )
        self.assertIsNotNone(msg_id)

        # Receive
        messages = receiver.receive_handoffs()
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].payload["tables"], ["Fact_Sales"])

        # Acknowledge & resolve
        bus.acknowledge(msg_id)
        bus.resolve(msg_id, {"status": "processed"})

        unresolved = bus.get_unresolved("agent-04")
        self.assertEqual(len(unresolved), 0)


if __name__ == "__main__":
    unittest.main()
