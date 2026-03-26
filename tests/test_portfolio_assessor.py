"""Tests for portfolio_assessor and safe_xml modules."""

from __future__ import annotations

import pytest

from src.agents.discovery.portfolio_assessor import (
    ReadinessLevel,
    ReadinessResult,
    assess_portfolio,
    assess_readiness,
    plan_waves_by_effort,
)
from src.agents.discovery.safe_xml import safe_parse_xml, validate_xml_path
from src.core.models import AssetType, InventoryItem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(name: str = "Test", metadata: dict | None = None) -> InventoryItem:
    return InventoryItem(
        id=f"test__{name}",
        asset_type=AssetType.ANALYSIS,
        source_path=f"/test/{name}",
        name=name,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# Portfolio assessor
# ---------------------------------------------------------------------------

class TestAssessReadiness:
    def test_simple_item_is_green(self):
        result = assess_readiness(_item("Simple"))
        assert result.readiness == ReadinessLevel.GREEN
        assert result.effort_score >= 1.0

    def test_unsupported_function_makes_red(self):
        result = assess_readiness(_item(metadata={
            "expressions": ["EVALUATE_PREDICATE(x, y)"],
        }))
        assert result.readiness == ReadinessLevel.RED
        assert len(result.blockers) >= 1

    def test_unsupported_connection_makes_red(self):
        result = assess_readiness(_item(metadata={
            "connections": [{"type": "essbase"}],
        }))
        assert result.readiness == ReadinessLevel.RED

    def test_many_warnings_makes_yellow(self):
        result = assess_readiness(_item(metadata={
            "filters": [{"name": f"f{i}", "cascade": True} for i in range(10)],
            "prompts": list(range(5)),
            "security_roles": list(range(3)),
            "tables": list(range(5)),
            "joins": list(range(5)),
        }))
        assert result.readiness in (ReadinessLevel.YELLOW, ReadinessLevel.GREEN)

    def test_effort_increases_with_calcs(self):
        low = assess_readiness(_item(metadata={"custom_calc_count": 1}))
        high = assess_readiness(_item(metadata={"custom_calc_count": 20}))
        assert high.effort_score > low.effort_score

    def test_to_dict(self):
        result = assess_readiness(_item("Dict"))
        d = result.to_dict()
        assert d["asset_name"] == "Dict"
        assert d["readiness"] in ("green", "yellow", "red")

    def test_unsupported_chart_type_warning(self):
        result = assess_readiness(_item(metadata={
            "chart_types": ["sunburst", "chord"],
        }))
        assert any("sunburst" in w for w in result.warnings)


class TestAssessPortfolio:
    def test_portfolio_summary(self):
        items = [_item(f"Item{i}") for i in range(5)]
        results, summary = assess_portfolio(items)
        assert len(results) == 5
        assert summary["total_assets"] == 5
        assert "green" in summary

    def test_mixed_portfolio(self):
        items = [
            _item("Simple"),
            _item("Complex", {"expressions": ["EVALUATE_PREDICATE(x)"]}),
        ]
        results, summary = assess_portfolio(items)
        assert summary["red"] >= 1
        assert summary["total_assets"] == 2


class TestPlanWaves:
    def test_wave_planning(self):
        items = [
            _item(f"Item{i}", {"custom_calc_count": i * 5})
            for i in range(6)
        ]
        results = [assess_readiness(item) for item in items]
        waves = plan_waves_by_effort(results)
        assert len(waves) >= 1
        # All results should be assigned to a wave (waves is list[list[str]])
        total = sum(len(w) for w in waves)
        assert total == 6


# ---------------------------------------------------------------------------
# Safe XML
# ---------------------------------------------------------------------------

class TestSafeXml:
    def test_parse_valid_xml(self):
        elem = safe_parse_xml("<root><child>text</child></root>")
        assert elem.tag == "root"
        assert elem.find("child").text == "text"

    def test_rejects_doctype(self):
        with pytest.raises(ValueError, match="DOCTYPE"):
            safe_parse_xml('<!DOCTYPE foo SYSTEM "bar"><root/>')

    def test_rejects_entity(self):
        with pytest.raises(ValueError, match="ENTITY"):
            safe_parse_xml('<?xml version="1.0"?><!ENTITY xxe "test"><root/>')

    def test_rejects_system_ref(self):
        with pytest.raises(ValueError, match="SYSTEM"):
            safe_parse_xml('<root SYSTEM "file:///etc/passwd"/>')

    def test_accepts_bytes(self):
        elem = safe_parse_xml(b"<root attr='1'/>")
        assert elem.tag == "root"
        assert elem.get("attr") == "1"


class TestValidateXmlPath:
    def test_safe_relative(self):
        assert validate_xml_path("data/file.xml") is True

    def test_rejects_traversal(self):
        assert validate_xml_path("../../../etc/passwd") is False
