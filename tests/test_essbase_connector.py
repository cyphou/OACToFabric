"""Tests for Oracle Essbase connector stub.

Tests cover:
- EssbaseConnector info (is_stub, supported asset types)
- EssbaseConnector lifecycle (connect, discover, extract, disconnect)
- Essbase calc script → DAX translation rules catalog
- Essbase MDX → DAX translation rules catalog
- Essbase → TMDL concept mapping
- EssbaseDimension data model
- Registration in default registry
"""

from __future__ import annotations

import pytest

from src.connectors.essbase_connector import (
    ESSBASE_MDX_TO_DAX,
    ESSBASE_TO_DAX_RULES,
    ESSBASE_TO_TMDL_MAPPING,
    EssbaseCalcRule,
    EssbaseConnector,
    EssbaseDimension,
)


# ===================================================================
# EssbaseConnector — info
# ===================================================================


class TestEssbaseConnectorInfo:
    """Tests for connector metadata."""

    def test_is_stub(self):
        c = EssbaseConnector()
        info = c.info()
        assert info.is_stub is True

    def test_platform_is_essbase(self):
        c = EssbaseConnector()
        assert c.info().platform == "essbase"

    def test_name_contains_essbase(self):
        c = EssbaseConnector()
        assert "Essbase" in c.info().name

    def test_version(self):
        c = EssbaseConnector()
        assert c.info().version == "0.1.0"

    def test_supported_asset_types(self):
        c = EssbaseConnector()
        types = c.info().supported_asset_types
        assert "cube" in types
        assert "dimension" in types
        assert "calcScript" in types
        assert "businessRule" in types
        assert "filter" in types
        assert "substitutionVariable" in types
        assert "mdxQuery" in types
        assert len(types) == 7


# ===================================================================
# EssbaseConnector — lifecycle
# ===================================================================


class TestEssbaseConnectorLifecycle:
    """Tests for connect/discover/extract/disconnect."""

    @pytest.mark.asyncio
    async def test_connect(self):
        c = EssbaseConnector()
        result = await c.connect({"host": "localhost", "port": 9000})
        assert result is True

    @pytest.mark.asyncio
    async def test_discover_returns_empty(self):
        c = EssbaseConnector()
        await c.connect({})
        assets = await c.discover()
        assert assets == []

    @pytest.mark.asyncio
    async def test_extract_returns_empty(self):
        c = EssbaseConnector()
        await c.connect({})
        result = await c.extract_metadata()
        assert result.platform == "essbase"
        assert result.count == 0
        assert result.success is True

    @pytest.mark.asyncio
    async def test_extract_with_ids(self):
        c = EssbaseConnector()
        await c.connect({})
        result = await c.extract_metadata(asset_ids=["cube1"])
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_disconnect(self):
        c = EssbaseConnector()
        await c.connect({})
        await c.disconnect()
        # No error expected


# ===================================================================
# EssbaseDimension data model
# ===================================================================


class TestEssbaseDimension:
    """Tests for the dimension data model."""

    def test_default_values(self):
        dim = EssbaseDimension(name="Year")
        assert dim.name == "Year"
        assert dim.dimension_type == "regular"
        assert dim.members == []
        assert dim.generation_count == 0
        assert dim.storage_type == "dense"

    def test_accounts_dimension(self):
        dim = EssbaseDimension(
            name="Accounts",
            dimension_type="accounts",
            storage_type="dense",
            members=["Revenue", "COGS", "Profit"],
            generation_count=3,
        )
        assert dim.dimension_type == "accounts"
        assert len(dim.members) == 3

    def test_time_dimension(self):
        dim = EssbaseDimension(
            name="Period",
            dimension_type="time",
            storage_type="dense",
        )
        assert dim.dimension_type == "time"


# ===================================================================
# Calc script → DAX translation rules
# ===================================================================


class TestEssbaseCalcRules:
    """Tests for the Essbase calc → DAX rule catalog."""

    def test_rules_not_empty(self):
        assert len(ESSBASE_TO_DAX_RULES) > 0

    def test_all_rules_are_calc_rules(self):
        for rule in ESSBASE_TO_DAX_RULES:
            assert isinstance(rule, EssbaseCalcRule)

    def test_direct_math_functions(self):
        direct = [r for r in ESSBASE_TO_DAX_RULES if r.difficulty == "direct"]
        names = {r.essbase_function for r in direct}
        assert "@SUM" in names
        assert "@AVG" in names
        assert "@MIN" in names
        assert "@MAX" in names
        assert "@ABS" in names
        assert "@ROUND" in names

    def test_complex_cross_dimensional(self):
        complex_rules = [r for r in ESSBASE_TO_DAX_RULES if r.difficulty == "complex"]
        names = {r.essbase_function for r in complex_rules}
        assert "@SUMRANGE" in names
        assert "@PARENTVAL" in names
        assert "@CHILDREN" in names

    def test_parametric_rules_exist(self):
        parametric = [r for r in ESSBASE_TO_DAX_RULES if r.difficulty == "parametric"]
        assert len(parametric) > 0

    def test_all_rules_have_dax_equivalent(self):
        for rule in ESSBASE_TO_DAX_RULES:
            assert rule.dax_equivalent, f"{rule.essbase_function} missing DAX equivalent"

    def test_rule_count(self):
        assert len(ESSBASE_TO_DAX_RULES) >= 30


# ===================================================================
# MDX → DAX translation rules
# ===================================================================


class TestEssbaseMdxRules:
    """Tests for the Essbase MDX → DAX rule catalog."""

    def test_rules_not_empty(self):
        assert len(ESSBASE_MDX_TO_DAX) > 0

    def test_all_tuples_have_three_elements(self):
        for rule in ESSBASE_MDX_TO_DAX:
            assert len(rule) == 3

    def test_iif_maps_to_if(self):
        iif_rules = [r for r in ESSBASE_MDX_TO_DAX if "IIF" in r[0]]
        assert len(iif_rules) >= 1
        assert "IF" in iif_rules[0][1]

    def test_time_intelligence_rules(self):
        time_rules = [r for r in ESSBASE_MDX_TO_DAX if "YTD" in r[0] or "QTD" in r[0] or "MTD" in r[0]]
        assert len(time_rules) >= 3

    def test_rule_count(self):
        assert len(ESSBASE_MDX_TO_DAX) >= 15


# ===================================================================
# Essbase → TMDL concept mapping
# ===================================================================


class TestEssbaseToTmdlMapping:
    """Tests for the Essbase → TMDL concept mapping."""

    def test_mapping_not_empty(self):
        assert len(ESSBASE_TO_TMDL_MAPPING) > 0

    def test_cube_maps_to_semantic_model(self):
        assert ESSBASE_TO_TMDL_MAPPING["Cube"] == "Semantic Model"

    def test_accounts_dimension(self):
        assert "Measures" in ESSBASE_TO_TMDL_MAPPING["Dimension (Accounts)"]

    def test_time_dimension(self):
        assert "Date Table" in ESSBASE_TO_TMDL_MAPPING["Dimension (Time)"]

    def test_dynamic_calc_maps_to_measure(self):
        assert "DAX Measure" in ESSBASE_TO_TMDL_MAPPING["Dynamic Calc Member"]

    def test_filter_maps_to_rls(self):
        assert "RLS" in ESSBASE_TO_TMDL_MAPPING["Essbase Filter (Security)"]

    def test_substitution_variable(self):
        assert "Parameter" in ESSBASE_TO_TMDL_MAPPING["Substitution Variable"]

    def test_shared_member(self):
        assert "hierarchy" in ESSBASE_TO_TMDL_MAPPING["Shared Member"].lower()

    def test_mapping_count(self):
        assert len(ESSBASE_TO_TMDL_MAPPING) >= 20


# ===================================================================
# Registry integration
# ===================================================================


class TestEssbaseRegistration:
    """Tests for Essbase registration in default registry."""

    def test_essbase_registered(self):
        from src.connectors.base_connector import build_default_registry
        registry = build_default_registry()
        assert registry.is_registered("essbase")

    def test_can_create_essbase(self):
        from src.connectors.base_connector import build_default_registry
        registry = build_default_registry()
        connector = registry.create("essbase")
        assert connector is not None

    def test_registry_has_six_platforms(self):
        from src.connectors.base_connector import build_default_registry
        registry = build_default_registry()
        assert len(registry.list_platforms()) == 6

    def test_essbase_platform_enum(self):
        from src.connectors.base_connector import SourcePlatform
        assert SourcePlatform.ESSBASE.value == "essbase"

    def test_platform_count(self):
        from src.connectors.base_connector import SourcePlatform
        assert len(SourcePlatform) == 6
