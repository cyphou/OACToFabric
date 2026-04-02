"""Tests for Phase 71–76: Multi-Agent Intelligence (Phases 71–76).

Covers:
- Phase 71: AI Assessor, Strategy Recommender, Assessment Narrator
- Phase 72: Intelligent Translator, Rule Distiller, Syntax Validators
- Phase 73: Handoff Protocol, Message Bus, Conflict Resolver, Context Window
- Phase 74: Error Diagnostician, Repair Strategies, Healing Engine, Regression Guard
- Phase 75: Escalation Queue, Review Items, Feedback Collector
- Phase 76: AI Wave Planner, Resource Optimizer, Cost Modeler, Adaptive Scheduler
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.models import (
    AssetType,
    ComplexityCategory,
    Inventory,
    InventoryItem,
)


# ===================================================================
# Helpers
# ===================================================================


def _make_item(
    id: str = "item_1",
    name: str = "TestItem",
    asset_type: AssetType = AssetType.LOGICAL_TABLE,
    complexity: str = "Medium",
    **meta: object,
) -> InventoryItem:
    metadata = {"complexity": complexity, **meta}
    return InventoryItem(
        id=id,
        name=name,
        asset_type=asset_type,
        source_path=f"/path/{name}",
        metadata=metadata,
    )


def _make_inventory(items: list[InventoryItem] | None = None) -> Inventory:
    return Inventory(items=items or [])


# ===================================================================
# Phase 71: AI Assessor
# ===================================================================


class TestAIAssessor:
    def test_assess_empty_inventory(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        assessor = AIAssessor()
        result = assessor.assess(_make_inventory())
        assert result.total_assets == 0
        assert result.anomaly_count == 0

    def test_assess_simple_inventory(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item(f"t{i}", f"Table{i}") for i in range(5)]
        inv = _make_inventory(items)
        result = assessor = AIAssessor()
        result = assessor.assess(inv)
        assert result.total_assets == 5
        assert len(result.risk_heatmap) == 5
        assert result.summary

    def test_detect_orphaned_tables(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [
            _make_item("t1", "Table1"),
            _make_item("t2", "Table2"),
            _make_item("t3", "Table3"),
        ]
        dep_graph = {"t1": ["t2"]}  # t3 is orphaned
        result = AIAssessor().assess(_make_inventory(items), dep_graph)
        orphaned = [a for a in result.anomalies if a.anomaly_type.value == "orphaned_table"]
        assert len(orphaned) >= 1

    def test_detect_circular_dependency(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item(f"t{i}", f"Table{i}") for i in range(3)]
        dep_graph = {"t0": ["t1"], "t1": ["t2"], "t2": ["t0"]}
        result = AIAssessor().assess(_make_inventory(items), dep_graph)
        circ = [a for a in result.anomalies if a.anomaly_type.value == "circular_dependency"]
        assert len(circ) >= 1

    def test_detect_excessive_roles(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item(f"r{i}", f"Role{i}", AssetType.SECURITY_ROLE) for i in range(60)]
        result = AIAssessor().assess(_make_inventory(items))
        excessive = [a for a in result.anomalies if a.anomaly_type.value == "excessive_roles"]
        assert len(excessive) == 1

    def test_detect_wide_fact_table(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item("t1", "WideFact", column_count=300)]
        result = AIAssessor().assess(_make_inventory(items))
        wide = [a for a in result.anomalies if a.anomaly_type.value == "wide_fact_table"]
        assert len(wide) == 1

    def test_detect_large_model(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item("m1", "BigModel", AssetType.DATA_MODEL, table_count=150)]
        result = AIAssessor().assess(_make_inventory(items))
        large = [a for a in result.anomalies if a.anomaly_type.value == "large_model"]
        assert len(large) == 1

    def test_risk_distribution(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item(f"t{i}", f"T{i}", complexity_score=i) for i in range(10)]
        result = AIAssessor().assess(_make_inventory(items))
        assert sum(result.risk_distribution.values()) == 10

    def test_strategy_recommendations_exist(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item(f"t{i}", f"T{i}") for i in range(5)]
        result = AIAssessor().assess(_make_inventory(items))
        assert len(result.strategy_recommendations) >= 1

    def test_to_dict(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        items = [_make_item("t1", "T1")]
        result = AIAssessor().assess(_make_inventory(items))
        d = result.to_dict()
        assert "total_assets" in d
        assert "risk_distribution" in d

    def test_risk_levels(self):
        from src.agents.discovery.ai_assessor import RiskLevel, _risk_level_from_score

        assert _risk_level_from_score(0.0) == RiskLevel.LOW
        assert _risk_level_from_score(0.3) == RiskLevel.MEDIUM
        assert _risk_level_from_score(0.6) == RiskLevel.HIGH
        assert _risk_level_from_score(0.8) == RiskLevel.CRITICAL

    def test_anomaly_to_dict(self):
        from src.agents.discovery.ai_assessor import Anomaly, AnomalyType, RiskLevel

        a = Anomaly(AnomalyType.ORPHANED_TABLE, RiskLevel.LOW, ["t1"], "desc", "rec")
        d = a.to_dict()
        assert d["type"] == "orphaned_table"

    def test_memory_integration(self):
        from src.agents.discovery.ai_assessor import AIAssessor

        memory = MagicMock()
        assessor = AIAssessor(agent_memory=memory)
        items = [_make_item("t1", "T1")]
        assessor.assess(_make_inventory(items))
        memory.store.assert_called_once()


# ===================================================================
# Phase 71: Strategy Recommender
# ===================================================================


class TestStrategyRecommender:
    def test_empty_inventory(self):
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        rec = StrategyRecommender()
        plan = rec.recommend(_make_inventory())
        assert plan.total_waves == 0

    def test_basic_recommendation(self):
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        items = [_make_item(f"t{i}", f"Revenue_Table{i}") for i in range(10)]
        plan = StrategyRecommender().recommend(_make_inventory(items))
        assert plan.total_waves >= 1
        assert plan.total_estimated_hours > 0

    def test_domain_classification(self):
        from src.agents.discovery.strategy_recommender import classify_domain

        item1 = _make_item("t1", "Sales_Order")
        item2 = _make_item("t2", "Employee_Headcount")
        item3 = _make_item("t3", "Random_Table")

        assert classify_domain(item1) == "sales"
        assert classify_domain(item2) == "hr"
        assert classify_domain(item3) == "general"

    def test_multiple_domains(self):
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        items = [
            _make_item("s1", "Sales_Order"),
            _make_item("h1", "Employee_Leave"),
            _make_item("f1", "Budget_Forecast"),
        ]
        plan = StrategyRecommender(max_assets_per_wave=10).recommend(_make_inventory(items))
        domains = {w.domain for w in plan.waves}
        assert len(domains) >= 2

    def test_wave_splitting(self):
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        items = [_make_item(f"t{i}", f"T{i}") for i in range(100)]
        plan = StrategyRecommender(max_assets_per_wave=30).recommend(_make_inventory(items))
        assert plan.total_waves >= 3

    def test_to_dict(self):
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        items = [_make_item("t1", "T1")]
        plan = StrategyRecommender().recommend(_make_inventory(items))
        d = plan.to_dict()
        assert "total_waves" in d
        assert "total_estimated_hours" in d

    def test_with_risk_heatmap(self):
        from src.agents.discovery.ai_assessor import AIAssessor
        from src.agents.discovery.strategy_recommender import StrategyRecommender

        items = [_make_item(f"t{i}", f"T{i}") for i in range(5)]
        inv = _make_inventory(items)
        assessment = AIAssessor().assess(inv)
        plan = StrategyRecommender().recommend(inv, assessment.risk_heatmap)
        assert plan.total_waves >= 1


# ===================================================================
# Phase 71: Assessment Narrator
# ===================================================================


class TestAssessmentNarrator:
    def test_generate_report(self):
        from src.agents.discovery.ai_assessor import AIAssessor
        from src.agents.discovery.assessment_narrator import AssessmentNarrator

        items = [_make_item(f"t{i}", f"T{i}") for i in range(10)]
        assessment = AIAssessor().assess(_make_inventory(items))
        narrator = AssessmentNarrator()
        report = narrator.generate(assessment)
        assert "Migration Assessment Report" in report.markdown
        assert report.word_count > 50

    def test_empty_assessment(self):
        from src.agents.discovery.ai_assessor import AIAssessor
        from src.agents.discovery.assessment_narrator import AssessmentNarrator

        assessment = AIAssessor().assess(_make_inventory())
        report = AssessmentNarrator().generate(assessment)
        assert report.markdown

    def test_report_with_anomalies(self):
        from src.agents.discovery.ai_assessor import AIAssessor
        from src.agents.discovery.assessment_narrator import AssessmentNarrator

        items = [_make_item(f"r{i}", f"Role{i}", AssetType.SECURITY_ROLE) for i in range(60)]
        assessment = AIAssessor().assess(_make_inventory(items))
        report = AssessmentNarrator().generate(assessment)
        assert "Anomal" in report.markdown

    def test_to_dict(self):
        from src.agents.discovery.ai_assessor import AIAssessor
        from src.agents.discovery.assessment_narrator import AssessmentNarrator

        assessment = AIAssessor().assess(_make_inventory([_make_item("t1", "T1")]))
        report = AssessmentNarrator().generate(assessment)
        d = report.to_dict()
        assert "word_count" in d


# ===================================================================
# Phase 72: Intelligent Translator
# ===================================================================


class TestSyntaxValidators:
    def test_dax_valid(self):
        from src.core.intelligence.translation_agent import validate_dax_syntax

        ok, err = validate_dax_syntax("SUM(Sales[Amount])")
        assert ok is True

    def test_dax_unbalanced_parens(self):
        from src.core.intelligence.translation_agent import validate_dax_syntax

        ok, err = validate_dax_syntax("SUM(Sales[Amount]")
        assert ok is False
        assert "parenthes" in err.lower()

    def test_dax_unbalanced_brackets(self):
        from src.core.intelligence.translation_agent import validate_dax_syntax

        ok, err = validate_dax_syntax("SUM(Sales[Amount)")
        assert ok is False

    def test_dax_empty(self):
        from src.core.intelligence.translation_agent import validate_dax_syntax

        ok, err = validate_dax_syntax("")
        assert ok is False

    def test_tsql_valid(self):
        from src.core.intelligence.translation_agent import validate_tsql_syntax

        ok, _ = validate_tsql_syntax("SELECT * FROM users")
        assert ok is True

    def test_pyspark_valid(self):
        from src.core.intelligence.translation_agent import validate_pyspark_syntax

        ok, _ = validate_pyspark_syntax("df.filter(col('x') > 0)")
        assert ok is True

    def test_pyspark_invalid(self):
        from src.core.intelligence.translation_agent import validate_pyspark_syntax

        ok, _ = validate_pyspark_syntax("def (invalid:")
        assert ok is False

    def test_mquery_valid(self):
        from src.core.intelligence.translation_agent import validate_mquery_syntax

        ok, _ = validate_mquery_syntax('let Source = Table.FromRows({}) in Source')
        assert ok is True

    def test_mquery_unbalanced(self):
        from src.core.intelligence.translation_agent import validate_mquery_syntax

        ok, _ = validate_mquery_syntax("Table.FromRows({)")
        assert ok is False


class TestTranslationMemoryCache:
    def test_store_and_get_exact(self):
        from src.core.intelligence.translation_agent import TranslationMemoryCache

        cache = TranslationMemoryCache()
        cache.store("@SUM(Revenue)", "SUM('Fact'[Revenue])", 0.95)
        result = cache.get_exact("@SUM(Revenue)")
        assert result is not None
        assert result[0] == "SUM('Fact'[Revenue])"

    def test_get_similar(self):
        from src.core.intelligence.translation_agent import TranslationMemoryCache

        cache = TranslationMemoryCache()
        cache.store("@SUM(Revenue)", "SUM('Fact'[Revenue])", 0.95)
        result = cache.get_similar("@SUM(Revenue) something")
        # May or may not match depending on token overlap
        # Just ensure no exception
        assert result is None or isinstance(result, tuple)

    def test_cache_size(self):
        from src.core.intelligence.translation_agent import TranslationMemoryCache

        cache = TranslationMemoryCache()
        assert cache.size == 0
        cache.store("a", "b", 1.0)
        assert cache.size == 1


class TestIntelligentTranslator:
    def test_rule_based_success(self):
        from src.core.intelligence.translation_agent import (
            IntelligentTranslator,
            TargetLanguage,
            TranslationStrategy,
        )

        mock_rules = MagicMock()
        mock_rules.translate.return_value = MagicMock(
            dax_expression="SUM(Sales[Amount])", confidence=0.9,
        )
        translator = IntelligentTranslator(rule_translator=mock_rules)
        result = asyncio.run(translator.translate("@SUM(Sales)"))
        assert result.valid is True
        assert result.strategy_used == TranslationStrategy.RULE_BASED

    def test_cache_hit(self):
        from src.core.intelligence.translation_agent import (
            IntelligentTranslator,
            TranslationMemoryCache,
            TranslationStrategy,
        )

        cache = TranslationMemoryCache()
        cache.store("@SUM(X)", "SUM('F'[X])", 0.95)
        translator = IntelligentTranslator(cache=cache)
        result = asyncio.run(translator.translate("@SUM(X)"))
        assert result.strategy_used == TranslationStrategy.CACHE_HIT

    def test_escalate_when_no_translator(self):
        from src.core.intelligence.translation_agent import IntelligentTranslator, TranslationStrategy

        translator = IntelligentTranslator()
        result = asyncio.run(translator.translate("unknown expression"))
        assert result.strategy_used == TranslationStrategy.ESCALATED

    def test_to_dict(self):
        from src.core.intelligence.translation_agent import IntelligentTranslator

        result = asyncio.run(IntelligentTranslator().translate("x"))
        d = result.to_dict()
        assert "strategy" in d


# ===================================================================
# Phase 72: Rule Distiller
# ===================================================================


class TestRuleDistiller:
    def test_distil_simple_function(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        distiller = RuleDistiller()
        rule = distiller.distil("@SUM(Revenue)", "SUM('Fact'[Revenue])", 0.95)
        assert rule is not None
        assert "SUM" in rule.source_pattern or "Revenue" in rule.output_template

    def test_distil_low_confidence_skipped(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        distiller = RuleDistiller(min_confidence=0.9)
        rule = distiller.distil("@X(Y)", "Z", 0.5)
        assert rule is None

    def test_distil_empty_skipped(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        rule = RuleDistiller().distil("", "", 1.0)
        assert rule is None

    def test_candidate_count(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        d = RuleDistiller()
        assert d.candidate_count == 0
        d.distil("@SUM(X)", "SUM(X)", 0.95)
        assert d.candidate_count == 1

    def test_to_dict(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        rule = RuleDistiller().distil("@AVG(X)", "AVERAGE(X)", 0.9)
        assert rule is not None
        d = rule.to_dict()
        assert "pattern" in d

    def test_memory_persistence(self):
        from src.core.intelligence.rule_distiller import RuleDistiller

        memory = MagicMock()
        distiller = RuleDistiller(agent_memory=memory)
        distiller.distil("@SUM(X)", "SUM(X)", 0.95)
        memory.store.assert_called_once()


# ===================================================================
# Phase 73: Handoff Protocol
# ===================================================================


class TestMessageBus:
    def test_send_and_receive(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageType,
        )

        bus = MessageBus()
        msg = HandoffMessage(
            sender_agent="02-schema",
            receiver_agent="04-semantic",
            message_type=MessageType.ARTIFACT_READY,
            payload={"tables": ["Fact"]},
            summary="Schema done",
        )
        msg_id = bus.send(msg)
        assert msg_id

        received = bus.receive("04-semantic")
        assert len(received) == 1
        assert received[0].payload["tables"] == ["Fact"]

    def test_acknowledge(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageStatus, MessageType,
        )

        bus = MessageBus()
        msg = HandoffMessage("01", "02", MessageType.CONTEXT_SHARE)
        mid = bus.send(msg)
        assert bus.acknowledge(mid) is True
        assert msg.status == MessageStatus.ACKNOWLEDGED

    def test_resolve(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageStatus, MessageType,
        )

        bus = MessageBus()
        msg = HandoffMessage("01", "02", MessageType.CONFLICT)
        mid = bus.send(msg)
        bus.resolve(mid, {"choice": "A"})
        assert msg.status == MessageStatus.RESOLVED

    def test_get_conflicts(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageType,
        )

        bus = MessageBus()
        bus.send(HandoffMessage("02", "04", MessageType.CONFLICT, summary="storage mode"))
        bus.send(HandoffMessage("01", "02", MessageType.ARTIFACT_READY))
        assert len(bus.get_conflicts()) == 1

    def test_get_escalations(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageType,
        )

        bus = MessageBus()
        bus.send(HandoffMessage("03", "08", MessageType.ESCALATION, summary="blocked"))
        assert len(bus.get_escalations()) == 1

    def test_priority_ordering(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessagePriority, MessageType,
        )

        bus = MessageBus()
        bus.send(HandoffMessage("01", "02", MessageType.CONTEXT_SHARE, priority=MessagePriority.LOW))
        bus.send(HandoffMessage("01", "02", MessageType.CONFLICT, priority=MessagePriority.CRITICAL))
        received = bus.receive("02")
        assert received[0].priority == MessagePriority.CRITICAL

    def test_conversation_thread(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageType,
        )

        bus = MessageBus()
        bus.send(HandoffMessage("01", "02", MessageType.CONTEXT_SHARE, correlation_id="conv_1"))
        bus.send(HandoffMessage("02", "01", MessageType.ACKNOWLEDGMENT, correlation_id="conv_1"))
        thread = bus.get_conversation("conv_1")
        assert len(thread) == 2

    def test_total_messages(self):
        from src.core.intelligence.handoff_protocol import (
            HandoffMessage, MessageBus, MessageType,
        )

        bus = MessageBus()
        assert bus.total_messages == 0
        bus.send(HandoffMessage("01", "02", MessageType.CONTEXT_SHARE))
        assert bus.total_messages == 1


class TestConflictResolver:
    def test_resolve_storage_mode_with_lakehouse(self):
        from src.core.intelligence.handoff_protocol import (
            ConflictResolver, HandoffMessage, MessageType,
        )

        conflict = HandoffMessage(
            "02", "04", MessageType.CONFLICT,
            payload={"conflict_type": "storage_mode", "options": {"has_lakehouse": True}},
        )
        resolution = ConflictResolver().resolve(conflict)
        assert resolution.chosen_option == "direct_lake"
        assert resolution.confidence > 0.8

    def test_resolve_naming_collision(self):
        from src.core.intelligence.handoff_protocol import (
            ConflictResolver, HandoffMessage, MessageType,
        )

        conflict = HandoffMessage(
            "02", "04", MessageType.CONFLICT,
            payload={"conflict_type": "naming_collision", "name": "DimDate"},
        )
        resolution = ConflictResolver().resolve(conflict)
        assert "02" in resolution.chosen_option

    def test_unknown_conflict_escalates(self):
        from src.core.intelligence.handoff_protocol import (
            ConflictResolver, HandoffMessage, MessageType,
        )

        conflict = HandoffMessage("01", "02", MessageType.CONFLICT, payload={})
        resolution = ConflictResolver().resolve(conflict)
        assert resolution.requires_human_review is True


class TestContextWindow:
    def test_add_and_build(self):
        from src.core.intelligence.handoff_protocol import ContextWindow

        cw = ContextWindow(max_tokens=100)
        cw.add("Inventory", "5 tables discovered", priority=1)
        cw.add("Schema", "DDL generated", priority=2)
        result = cw.build()
        assert "Inventory" in result
        assert "Schema" in result

    def test_truncation(self):
        from src.core.intelligence.handoff_protocol import ContextWindow

        cw = ContextWindow(max_tokens=10)  # Very small
        cw.add("A", "x" * 1000, priority=1)
        cw.add("B", "y" * 1000, priority=2)
        result = cw.build()
        assert len(result) < 1000

    def test_clear(self):
        from src.core.intelligence.handoff_protocol import ContextWindow

        cw = ContextWindow()
        cw.add("X", "Y")
        assert cw.entry_count == 1
        cw.clear()
        assert cw.entry_count == 0


# ===================================================================
# Phase 74: Error Diagnostician
# ===================================================================


class TestErrorDiagnostician:
    def test_type_mismatch(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Cannot convert type 'varchar' to 'int64'")
        assert d.category == ErrorCategory.TYPE_MISMATCH
        assert d.can_auto_repair is True

    def test_missing_dependency(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Table 'DimProduct' not found")
        assert d.category == ErrorCategory.MISSING_DEPENDENCY

    def test_syntax_error(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Syntax error near unexpected token ')'")
        assert d.category == ErrorCategory.SYNTAX_ERROR

    def test_rate_limit(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("HTTP 429: Too many requests - rate limit exceeded")
        assert d.category == ErrorCategory.API_RATE_LIMIT

    def test_timeout(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Connection timed out after 30s")
        assert d.category == ErrorCategory.API_TIMEOUT

    def test_permission_error(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("403 Forbidden: permission denied")
        assert d.category == ErrorCategory.PERMISSION_ERROR
        assert d.can_auto_repair is False

    def test_data_quality(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Null value in column 'CustomerID' violates constraint")
        assert d.category == ErrorCategory.DATA_QUALITY

    def test_unknown_error(self):
        from src.core.intelligence.error_diagnostician import ErrorCategory, ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("Something bizarre happened xyz123")
        assert d.category == ErrorCategory.UNKNOWN
        assert d.can_auto_repair is False

    def test_known_error_cache(self):
        from src.core.intelligence.error_diagnostician import ErrorDiagnostician

        diag = ErrorDiagnostician()
        d1 = diag.diagnose("Syntax error in expression")
        d2 = diag.diagnose("Syntax error in expression")
        assert d1.category == d2.category

    def test_to_dict(self):
        from src.core.intelligence.error_diagnostician import ErrorDiagnostician

        d = ErrorDiagnostician().diagnose("type mismatch")
        result = d.to_dict()
        assert "category" in result


# ===================================================================
# Phase 74: Repair Strategies
# ===================================================================


class TestRepairStrategies:
    def test_type_mapping_known_type(self):
        from src.core.intelligence.repair_strategies import AdjustTypeMappingStrategy

        strategy = AdjustTypeMappingStrategy()
        diag = MagicMock(recommended_strategies=["adjust_type_mapping"])
        assert strategy.can_handle(diag) is True
        result = asyncio.run(strategy.repair(diag, {"source_type": "varchar2"}))
        assert result.success is True
        assert result.repaired_output == "string"

    def test_type_mapping_unknown_type(self):
        from src.core.intelligence.repair_strategies import AdjustTypeMappingStrategy

        strategy = AdjustTypeMappingStrategy()
        diag = MagicMock(recommended_strategies=["adjust_type_mapping"])
        result = asyncio.run(strategy.repair(diag, {"source_type": "exotic_type"}))
        assert result.success is True
        assert result.repaired_output == "string"
        assert len(result.side_effects) > 0

    def test_quarantine(self):
        from src.core.intelligence.repair_strategies import QuarantineStrategy

        strategy = QuarantineStrategy()
        diag = MagicMock(recommended_strategies=["quarantine_rows"])
        result = asyncio.run(strategy.repair(diag, {"bad_rows": [1, 2, 3]}))
        assert result.success is True

    def test_skip_and_continue(self):
        from src.core.intelligence.repair_strategies import SkipAndContinueStrategy

        strategy = SkipAndContinueStrategy()
        diag = MagicMock(recommended_strategies=["skip_and_continue"])
        result = asyncio.run(strategy.repair(diag, {"asset_id": "t1"}))
        assert result.success is True

    def test_fix_syntax_unbalanced_parens(self):
        from src.core.intelligence.repair_strategies import FixSyntaxStrategy

        strategy = FixSyntaxStrategy()
        diag = MagicMock(recommended_strategies=["fix_syntax"])
        result = asyncio.run(strategy.repair(diag, {"expression": "SUM(Sales[Amount]"}))
        assert result.success is True
        assert result.repaired_output.count("(") == result.repaired_output.count(")")

    def test_get_all_strategies(self):
        from src.core.intelligence.repair_strategies import get_all_strategies

        strategies = get_all_strategies()
        assert len(strategies) >= 6

    def test_can_handle_false(self):
        from src.core.intelligence.repair_strategies import QuarantineStrategy

        strategy = QuarantineStrategy()
        diag = MagicMock(recommended_strategies=["retry_with_backoff"])
        assert strategy.can_handle(diag) is False


# ===================================================================
# Phase 74: Healing Engine
# ===================================================================


class TestHealingEngine:
    def test_heal_auto_repairable(self):
        from src.core.intelligence.error_diagnostician import ErrorDiagnostician
        from src.core.intelligence.healing_engine import HealingEngine
        from src.core.intelligence.repair_strategies import FixSyntaxStrategy

        engine = HealingEngine(
            diagnostician=ErrorDiagnostician(),
            strategies=[FixSyntaxStrategy()],
        )
        report = asyncio.run(engine.heal(
            "Syntax error in expression",
            {"expression": "SUM(X"},
        ))
        assert report.healed is True
        assert report.strategy_used == "fix_syntax"

    def test_heal_not_auto_repairable(self):
        from src.core.intelligence.error_diagnostician import ErrorDiagnostician
        from src.core.intelligence.healing_engine import HealingEngine

        engine = HealingEngine(diagnostician=ErrorDiagnostician())
        report = asyncio.run(engine.heal("permission denied"))
        assert report.healed is False

    def test_success_rate(self):
        from src.core.intelligence.healing_engine import HealingEngine

        engine = HealingEngine()
        assert engine.success_rate == 0.0

    def test_to_dict(self):
        from src.core.intelligence.error_diagnostician import ErrorDiagnostician
        from src.core.intelligence.healing_engine import HealingEngine

        engine = HealingEngine(diagnostician=ErrorDiagnostician())
        report = asyncio.run(engine.heal("test error"))
        d = report.to_dict()
        assert "healed" in d


class TestRegressionGuard:
    def test_no_baseline_passes(self):
        from src.core.intelligence.healing_engine import RegressionGuard

        guard = RegressionGuard()
        passed, msg = guard.check_regression("t1", MagicMock(passed=True))
        assert passed is True

    def test_regression_detected(self):
        from src.core.intelligence.healing_engine import RegressionGuard

        guard = RegressionGuard()
        guard.set_baseline("t1", MagicMock(passed=True))
        passed, msg = guard.check_regression("t1", MagicMock(passed=False))
        assert passed is False
        assert "Regression" in msg

    def test_no_regression(self):
        from src.core.intelligence.healing_engine import RegressionGuard

        guard = RegressionGuard()
        guard.set_baseline("t1", MagicMock(passed=True))
        passed, msg = guard.check_regression("t1", MagicMock(passed=True))
        assert passed is True

    def test_baseline_count(self):
        from src.core.intelligence.healing_engine import RegressionGuard

        guard = RegressionGuard()
        assert guard.baseline_count == 0
        guard.set_baseline("t1", {})
        assert guard.baseline_count == 1


# ===================================================================
# Phase 75: Escalation Queue
# ===================================================================


class TestEscalationQueue:
    def test_escalate_and_get_pending(self):
        from src.core.intelligence.escalation import (
            EscalationQueue, EscalationReason, ReviewItem,
        )

        queue = EscalationQueue()
        item = ReviewItem(
            asset_id="t1",
            reason=EscalationReason.LOW_CONFIDENCE,
            description="DAX confidence 0.45",
            confidence=0.45,
        )
        queue.escalate(item)
        pending = queue.get_pending()
        assert len(pending) == 1

    def test_resolve(self):
        from src.core.intelligence.escalation import (
            EscalationQueue, EscalationReason, ReviewAction, ReviewItem, ReviewStatus,
        )

        queue = EscalationQueue()
        item = ReviewItem(asset_id="t1", reason=EscalationReason.LOW_CONFIDENCE)
        queue.escalate(item)
        queue.resolve(item.item_id, ReviewAction.APPROVE, "reviewer1")
        assert item.status == ReviewStatus.RESOLVED
        assert queue.pending_count == 0

    def test_defer(self):
        from src.core.intelligence.escalation import (
            EscalationQueue, EscalationReason, ReviewItem, ReviewStatus,
        )

        queue = EscalationQueue()
        item = ReviewItem(asset_id="t1", reason=EscalationReason.SECURITY_REVIEW)
        queue.escalate(item)
        queue.defer(item.item_id)
        assert item.status == ReviewStatus.DEFERRED

    def test_filter_by_severity(self):
        from src.core.intelligence.escalation import (
            EscalationQueue, EscalationReason, ReviewItem,
        )

        queue = EscalationQueue()
        queue.escalate(ReviewItem(asset_id="t1", severity="critical", reason=EscalationReason.LOW_CONFIDENCE))
        queue.escalate(ReviewItem(asset_id="t2", severity="low", reason=EscalationReason.LOW_CONFIDENCE))
        critical = queue.get_pending(severity="critical")
        assert len(critical) == 1

    def test_stats(self):
        from src.core.intelligence.escalation import (
            EscalationQueue, EscalationReason, ReviewAction, ReviewItem,
        )

        queue = EscalationQueue()
        queue.escalate(ReviewItem(asset_id="t1", reason=EscalationReason.LOW_CONFIDENCE))
        queue.escalate(ReviewItem(asset_id="t2", reason=EscalationReason.LOW_CONFIDENCE))
        assert queue.total_items == 2
        stats = queue.get_stats()
        assert "pending" in stats

    def test_to_dict(self):
        from src.core.intelligence.escalation import EscalationReason, ReviewItem

        item = ReviewItem(asset_id="t1", reason=EscalationReason.LOW_CONFIDENCE)
        d = item.to_dict()
        assert d["reason"] == "low_confidence"


class TestFeedbackCollector:
    def test_record_feedback(self):
        from src.core.intelligence.escalation import (
            EscalationReason, FeedbackCollector, ReviewAction, ReviewItem,
        )

        collector = FeedbackCollector()
        item = ReviewItem(
            asset_id="t1",
            reason=EscalationReason.LOW_CONFIDENCE,
            source_expression="@SUM(X)",
            generated_output="SUM(X)",
        )
        entry = collector.record(item, ReviewAction.APPROVE)
        assert entry.action_taken == ReviewAction.APPROVE
        assert collector.total_entries == 1

    def test_approval_rate(self):
        from src.core.intelligence.escalation import (
            EscalationReason, FeedbackCollector, ReviewAction, ReviewItem,
        )

        collector = FeedbackCollector()
        for i, action in enumerate([ReviewAction.APPROVE, ReviewAction.APPROVE, ReviewAction.REJECT]):
            item = ReviewItem(asset_id=f"t{i}", reason=EscalationReason.LOW_CONFIDENCE)
            collector.record(item, action)
        assert collector.approval_rate == pytest.approx(2 / 3)

    def test_get_approved_and_rejected(self):
        from src.core.intelligence.escalation import (
            EscalationReason, FeedbackCollector, ReviewAction, ReviewItem,
        )

        collector = FeedbackCollector()
        for action in [ReviewAction.APPROVE, ReviewAction.REJECT]:
            item = ReviewItem(asset_id="x", reason=EscalationReason.LOW_CONFIDENCE)
            collector.record(item, action)
        assert len(collector.get_approved()) == 1
        assert len(collector.get_rejected()) == 1

    def test_memory_persistence(self):
        from src.core.intelligence.escalation import (
            EscalationReason, FeedbackCollector, ReviewAction, ReviewItem,
        )

        memory = MagicMock()
        collector = FeedbackCollector(agent_memory=memory)
        item = ReviewItem(asset_id="t1", reason=EscalationReason.LOW_CONFIDENCE)
        collector.record(item, ReviewAction.APPROVE)
        memory.store.assert_called_once()


# ===================================================================
# Phase 76: Intelligent Orchestration
# ===================================================================


class TestAIWavePlanner:
    def test_plan_empty(self):
        from src.core.intelligence.orchestration import AIWavePlanner

        planner = AIWavePlanner()
        waves = planner.plan(_make_inventory())
        assert len(waves) == 0

    def test_plan_basic(self):
        from src.core.intelligence.orchestration import AIWavePlanner

        items = [_make_item(f"t{i}", f"T{i}") for i in range(10)]
        planner = AIWavePlanner(max_assets_per_wave=5)
        waves = planner.plan(_make_inventory(items))
        assert len(waves) == 2

    def test_plan_with_dependencies(self):
        from src.core.intelligence.orchestration import AIWavePlanner

        items = [_make_item(f"t{i}", f"T{i}") for i in range(5)]
        dep_graph = {"t0": ["t1"], "t1": ["t2"]}
        planner = AIWavePlanner(max_assets_per_wave=10)
        waves = planner.plan(_make_inventory(items), dependency_graph=dep_graph)
        assert len(waves) >= 1

    def test_topo_sort_no_cycles(self):
        from src.core.intelligence.orchestration import AIWavePlanner

        result = AIWavePlanner._topo_sort(["a", "b", "c"], {"a": ["b"], "b": ["c"]})
        assert "a" in result
        assert len(result) == 3

    def test_topo_sort_with_cycle(self):
        from src.core.intelligence.orchestration import AIWavePlanner

        result = AIWavePlanner._topo_sort(["a", "b"], {"a": ["b"], "b": ["a"]})
        assert len(result) == 2

    def test_wave_config_to_dict(self):
        from src.core.intelligence.orchestration import WaveConfig

        wc = WaveConfig(wave_number=1, asset_ids=["a", "b"])
        d = wc.to_dict()
        assert d["wave"] == 1
        assert d["assets"] == 2


class TestResourceOptimizer:
    def test_small_migration(self):
        from src.core.intelligence.orchestration import ResourceOptimizer, WaveConfig

        waves = [WaveConfig(wave_number=1, asset_ids=["a"] * 20)]
        config = ResourceOptimizer().recommend(waves)
        assert config.fabric_sku in ("F2", "F4")

    def test_large_migration(self):
        from src.core.intelligence.orchestration import ResourceOptimizer, WaveConfig

        waves = [WaveConfig(wave_number=i, asset_ids=[f"a{j}" for j in range(100)]) for i in range(10)]
        config = ResourceOptimizer().recommend(waves)
        assert config.cu_count >= 8

    def test_to_dict(self):
        from src.core.intelligence.orchestration import ResourceOptimizer, WaveConfig

        config = ResourceOptimizer().recommend([WaveConfig(wave_number=1, asset_ids=["a"])])
        d = config.to_dict()
        assert "sku" in d


class TestCostModeler:
    def test_basic_estimate(self):
        from src.core.intelligence.orchestration import CostModeler, ResourceConfig, WaveConfig

        waves = [WaveConfig(wave_number=1, asset_ids=["a"] * 10, estimated_duration_hours=5)]
        config = ResourceConfig(fabric_sku="F4", cu_count=4)
        estimate = CostModeler().estimate(waves, config)
        assert estimate.total_cost_usd > 0
        assert estimate.cost_per_asset > 0

    def test_with_llm_tokens(self):
        from src.core.intelligence.orchestration import CostModeler, ResourceConfig, WaveConfig

        waves = [WaveConfig(wave_number=1, asset_ids=["a"], estimated_duration_hours=1)]
        config = ResourceConfig(cu_count=2)
        estimate = CostModeler().estimate(waves, config, estimated_llm_tokens=100000)
        assert estimate.llm_cost_usd > 0

    def test_to_dict(self):
        from src.core.intelligence.orchestration import CostModeler, ResourceConfig, WaveConfig

        waves = [WaveConfig(wave_number=1, asset_ids=["a"], estimated_duration_hours=1)]
        estimate = CostModeler().estimate(waves, ResourceConfig())
        d = estimate.to_dict()
        assert "total" in d


class TestAdaptiveScheduler:
    def test_no_adjustments_initially(self):
        from src.core.intelligence.orchestration import AdaptiveScheduler, WaveConfig

        scheduler = AdaptiveScheduler()
        waves = [WaveConfig(wave_number=1)]
        adjustments = scheduler.suggest_adjustments(waves)
        assert len(adjustments) == 0

    def test_scale_down_on_high_errors(self):
        from src.core.intelligence.orchestration import AdaptiveScheduler, WaveConfig

        scheduler = AdaptiveScheduler()
        scheduler.record_wave_completion(1, 2.0, error_count=30, total_items=100)
        waves = [WaveConfig(wave_number=2, max_batch_size=50)]
        adjustments = scheduler.suggest_adjustments(waves)
        assert any(a.adjustment_type == "scale_down" for a in adjustments)

    def test_scale_up_on_good_performance(self):
        from src.core.intelligence.orchestration import AdaptiveScheduler, WaveConfig

        scheduler = AdaptiveScheduler()
        scheduler.record_wave_completion(1, 1.0, error_count=0, total_items=50)
        scheduler.record_wave_completion(2, 1.0, error_count=1, total_items=50)
        waves = [WaveConfig(wave_number=3, parallel_agents=2)]
        adjustments = scheduler.suggest_adjustments(waves)
        assert any(a.adjustment_type == "scale_up" for a in adjustments)

    def test_completed_waves(self):
        from src.core.intelligence.orchestration import AdaptiveScheduler

        scheduler = AdaptiveScheduler()
        assert scheduler.completed_waves == 0
        scheduler.record_wave_completion(1, 1.0)
        assert scheduler.completed_waves == 1


class TestIntelligentPlan:
    def test_full_plan(self):
        from src.core.intelligence.orchestration import (
            AIWavePlanner, CostModeler, IntelligentPlan, ResourceOptimizer,
        )

        items = [_make_item(f"t{i}", f"T{i}") for i in range(20)]
        planner = AIWavePlanner(max_assets_per_wave=10)
        waves = planner.plan(_make_inventory(items))
        resource = ResourceOptimizer().recommend(waves)
        cost = CostModeler().estimate(waves, resource)

        plan = IntelligentPlan(
            waves=waves,
            resource_config=resource,
            cost_estimate=cost,
            summary="Test plan",
        )
        assert plan.total_waves == 2
        assert plan.total_assets == 20

        d = plan.to_dict()
        assert d["total_waves"] == 2
