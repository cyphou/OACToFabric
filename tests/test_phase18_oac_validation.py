"""Phase 18 tests — Live OAC validation infrastructure.

Since we can't run against a real OAC instance in CI, these tests:
1. Generate anonymized RPD fixtures and validate parsers handle them.
2. Test the fixture generator itself for correctness.
3. Validate connection/auth helpers handle error scenarios.
4. Test schema agent DDL generation against generated RPD data.
5. Test the streaming parser against larger generated fixtures.
6. Validate type mapper handles all Oracle types found in fixtures.

Target: ≥ 15 new tests (per DEV_PLAN_V3 Phase 18 exit criteria).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.testing.rpd_fixture_gen import generate_rpd_fixture


# ===================================================================
# RPD fixture generator tests
# ===================================================================


class TestRPDFixtureGenerator:
    """Tests for the anonymized RPD XML fixture generator."""

    def test_generate_small_fixture(self, tmp_path):
        """Generate a small RPD fixture and verify file is created."""
        out = generate_rpd_fixture(tmp_path / "small.xml", num_tables=5, cols_per_table=4)
        assert out.exists()
        content = out.read_text(encoding="utf-8")
        assert "<Repository" in content
        assert "<PhysicalLayer" in content
        assert "<BusinessModel" in content
        assert "<PresentationLayer" in content
        assert "<SecurityLayer" in content

    def test_deterministic_with_seed(self, tmp_path):
        """Same seed produces identical output."""
        out1 = generate_rpd_fixture(tmp_path / "a.xml", num_tables=3, seed=123)
        out2 = generate_rpd_fixture(tmp_path / "b.xml", num_tables=3, seed=123)
        assert out1.read_text() == out2.read_text()

    def test_different_seeds_differ(self, tmp_path):
        """Different seeds produce different output."""
        out1 = generate_rpd_fixture(tmp_path / "a.xml", num_tables=5, seed=1)
        out2 = generate_rpd_fixture(tmp_path / "b.xml", num_tables=5, seed=2)
        assert out1.read_text() != out2.read_text()

    def test_table_count(self, tmp_path):
        """Generated fixture has the requested number of physical tables."""
        from lxml import etree

        out = generate_rpd_fixture(tmp_path / "tables.xml", num_tables=12, seed=42)
        tree = etree.parse(str(out))
        tables = tree.findall(".//PhysicalTable")
        assert len(tables) == 12

    def test_columns_per_table(self, tmp_path):
        """Each table has at least the requested number of columns."""
        from lxml import etree

        out = generate_rpd_fixture(tmp_path / "cols.xml", num_tables=3, cols_per_table=6, seed=42)
        tree = etree.parse(str(out))
        for table in tree.findall(".//PhysicalTable"):
            cols = table.findall("PhysicalColumn")
            assert len(cols) == 6, f"Table {table.get('name')} has {len(cols)} cols"

    def test_logical_tables_match_physical(self, tmp_path):
        """Logical layer has one logical table per physical table."""
        from lxml import etree

        out = generate_rpd_fixture(tmp_path / "logical.xml", num_tables=8, seed=42)
        tree = etree.parse(str(out))
        physical = tree.findall(".//PhysicalTable")
        logical = tree.findall(".//LogicalTable")
        assert len(logical) == len(physical)

    def test_security_roles_created(self, tmp_path):
        """Security layer has the requested number of roles."""
        from lxml import etree

        out = generate_rpd_fixture(tmp_path / "sec.xml", num_tables=2, num_roles=4, seed=42)
        tree = etree.parse(str(out))
        roles = tree.findall(".//ApplicationRole")
        assert len(roles) == 4

    def test_joins_created_for_multi_table(self, tmp_path):
        """Joins exist when there are multiple tables."""
        from lxml import etree

        out = generate_rpd_fixture(tmp_path / "joins.xml", num_tables=5, seed=42)
        tree = etree.parse(str(out))
        joins = tree.findall(".//LogicalJoin")
        assert len(joins) > 0


# ===================================================================
# Parser integration with generated fixtures
# ===================================================================


class TestRPDParserIntegration:
    """Test rpd_parser.py against generated fixtures."""

    def test_rpd_parser_on_generated_fixture(self, tmp_path):
        """Standard RPD parser can parse generated fixture without errors."""
        from src.agents.discovery.rpd_parser import RPDParser

        out = generate_rpd_fixture(tmp_path / "test.xml", num_tables=10, seed=42)
        parser = RPDParser(str(out))
        items = parser.parse()

        # Should find physical tables, logical tables, presentation tables, and roles
        assert len(items) > 0
        types_found = {item.asset_type.value for item in items}
        assert "physicalTable" in types_found

    def test_streaming_parser_on_generated_fixture(self, tmp_path):
        """Streaming parser can parse generated fixture without errors."""
        from src.core.streaming_parser import StreamingRPDParser

        out = generate_rpd_fixture(tmp_path / "stream.xml", num_tables=20, seed=42)
        parser = StreamingRPDParser(str(out))
        items = parser.parse()

        assert len(items) > 0
        assert parser.items_yielded == len(items)


class TestStreamingParserScale:
    """Test streaming parser handles larger generated fixtures."""

    def test_streaming_parser_100_tables(self, tmp_path):
        """Streaming parser handles 100-table fixture."""
        out = generate_rpd_fixture(tmp_path / "large.xml", num_tables=100, seed=42)
        from src.core.streaming_parser import StreamingRPDParser

        parser = StreamingRPDParser(str(out))
        items = parser.parse()

        # At minimum, 100 physical tables should be found
        physical = [i for i in items if i.asset_type.value == "physicalTable"]
        assert len(physical) >= 100

    def test_streaming_iter_vs_parse(self, tmp_path):
        """iter_items and parse produce the same count."""
        out = generate_rpd_fixture(tmp_path / "iter.xml", num_tables=15, seed=42)
        from src.core.streaming_parser import StreamingRPDParser

        p1 = StreamingRPDParser(str(out))
        items_list = p1.parse()

        p2 = StreamingRPDParser(str(out))
        items_iter = list(p2.iter_items())

        assert len(items_list) == len(items_iter)


# ===================================================================
# OAC auth/connection validation tests
# ===================================================================


class TestOACAuthErrorHandling:
    """Test OAC auth module handles error scenarios gracefully."""

    @pytest.mark.asyncio
    async def test_auth_invalid_credentials_raises(self):
        """OACAuth raises on invalid credentials."""
        from src.clients.oac_auth import OACAuth, OACAuthError
        import httpx

        auth = OACAuth(
            client_id="bad-id",
            client_secret="bad-secret",
            token_url="https://invalid.example.com/oauth2/v1/token",
        )

        # Should fail to get token (connection error)
        with pytest.raises((OACAuthError, httpx.ConnectError, Exception)):
            await auth.get_token()

    def test_token_expiry_check(self):
        """TokenInfo.is_expired works correctly."""
        from src.clients.oac_auth import TokenInfo
        import time

        # Not expired (1 hour in the future)
        fresh = TokenInfo(
            access_token="tok",
            expires_at=time.time() + 3600,
        )
        assert not fresh.is_expired

        # Expired (in the past)
        stale = TokenInfo(
            access_token="tok",
            expires_at=time.time() - 60,
        )
        assert stale.is_expired


# ===================================================================
# Type mapper gap detection
# ===================================================================


class TestTypeMapperGaps:
    """Validate type mapper handles all Oracle types found in generated fixtures."""

    def test_all_generated_types_mapped(self, tmp_path):
        """Every data type in the generated fixture has a type mapping."""
        from lxml import etree
        from src.agents.schema.type_mapper import map_oracle_type, TargetPlatform

        out = generate_rpd_fixture(tmp_path / "types.xml", num_tables=20, seed=42)
        tree = etree.parse(str(out))

        data_types_found = set()
        for dt_elem in tree.findall(".//DataType"):
            if dt_elem.text:
                data_types_found.add(dt_elem.text.strip())

        # Reconstruct full types: pair DataType with sibling Length
        for dt_elem in tree.findall(".//DataType"):
            dt = dt_elem.text.strip() if dt_elem.text else ""
            length_elem = dt_elem.getnext() if hasattr(dt_elem, "getnext") else None
            # For types like VARCHAR2 that need a length, use the Length sibling
            if length_elem is not None and length_elem.tag == "Length" and length_elem.text:
                full_type = f"{dt}({length_elem.text})"
            else:
                full_type = dt
            if full_type:
                data_types_found.add(full_type)

        for oracle_type in data_types_found:
            mapping = map_oracle_type(oracle_type, TargetPlatform.LAKEHOUSE)
            assert mapping.fabric_type, f"No mapping for Oracle type: {oracle_type}"

    def test_edge_case_oracle_types(self):
        """Verify mapper handles additional Oracle-specific types."""
        from src.agents.schema.type_mapper import map_oracle_type, TargetPlatform

        edge_cases = [
            "NUMBER(10,2)",
            "VARCHAR2(255)",
            "DATE",
            "TIMESTAMP",
            "INTEGER",
            "CLOB",
            "NUMBER(18,4)",
            "NUMBER(12,0)",
        ]

        for ot in edge_cases:
            mapping = map_oracle_type(ot, TargetPlatform.LAKEHOUSE)
            assert mapping.fabric_type, f"No mapping for: {ot}"
