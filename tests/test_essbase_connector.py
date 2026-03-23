"""Tests for Oracle Essbase connector — full implementation.

Tests cover:
- EssbaseConnector info (is_stub=False, platform, supported asset types)
- EssbaseConnector lifecycle (connect, discover, extract, disconnect)
- EssbaseCalcTranslator (direct, parametric, complex, unsupported, batch)
- EssbaseMdxTranslator (direct, parametric, complex, time intelligence)
- EssbaseOutlineParser (XML parsing, JSON parsing, edge cases)
- EssbaseRestClient (mock HTTP, list calls, error handling)
- Essbase calc script → DAX translation rules catalog
- Essbase MDX → DAX translation rules catalog
- Essbase → TMDL concept mapping
- Data models (EssbaseDimension, EssbaseMember, EssbaseCalcScript, etc.)
- ParsedOutline properties
- Registration in default registry
"""

from __future__ import annotations

import pytest

from src.connectors.essbase_connector import (
    ESSBASE_MDX_TO_DAX,
    ESSBASE_TO_DAX_RULES,
    ESSBASE_TO_TMDL_MAPPING,
    CalcTranslationResult,
    EssbaseApiConfig,
    EssbaseCalcRule,
    EssbaseCalcScript,
    EssbaseCalcTranslator,
    EssbaseConnector,
    EssbaseDimension,
    EssbaseFilter,
    EssbaseMdxTranslator,
    EssbaseMember,
    EssbaseOutlineParser,
    EssbaseRestClient,
    EssbaseSubstitutionVar,
    ParsedOutline,
    _ESSBASE_CALC_PATTERNS,
    _ESSBASE_MDX_PATTERNS,
)


# ===================================================================
# EssbaseConnector — info
# ===================================================================


class TestEssbaseConnectorInfo:
    """Tests for connector metadata."""

    def test_is_not_stub(self):
        c = EssbaseConnector()
        info = c.info()
        assert info.is_stub is False

    def test_platform_is_essbase(self):
        c = EssbaseConnector()
        assert str(c.info().platform.value) == "essbase"

    def test_name_contains_essbase(self):
        c = EssbaseConnector()
        assert "Essbase" in c.info().name

    def test_version(self):
        c = EssbaseConnector()
        assert c.info().version == "1.0.0"

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

    def test_description_not_empty(self):
        c = EssbaseConnector()
        assert len(c.info().description) > 0

    def test_description_mentions_full(self):
        c = EssbaseConnector()
        desc = c.info().description
        assert "Full" in desc or "full" in desc or "REST" in desc


# ===================================================================
# EssbaseConnector — lifecycle (mock-based)
# ===================================================================


class _MockEssbaseRestClient(EssbaseRestClient):
    """Mock REST client that returns fake data."""

    def __init__(self, apps=None, dbs=None, outline=None, scripts=None, filters=None, variables=None) -> None:
        super().__init__()
        self._mock_apps = apps or []
        self._mock_dbs = dbs or {}
        self._mock_outline = outline or {}
        self._mock_scripts = scripts or {}
        self._mock_filters = filters or {}
        self._mock_variables = variables or {}
        self._mock_script_content = {}

    async def _http_get(self, url: str, params=None):
        """Return mock data based on URL."""
        if "/about" in url:
            return {"status": "ok", "version": "21.3"}
        if url.endswith("/applications"):
            return {"items": self._mock_apps}
        if "/databases" in url and "/scripts" not in url and "/filters" not in url and "/outline" not in url:
            app = url.split("/applications/")[1].split("/")[0]
            return {"items": self._mock_dbs.get(app, [])}
        if "/outline" in url:
            parts = url.split("/applications/")[1].split("/")
            app, db = parts[0], parts[2]
            return self._mock_outline.get(f"{app}.{db}", {"dimensions": []})
        if "/scripts/" in url:
            script_name = url.split("/scripts/")[1]
            return {"content": self._mock_script_content.get(script_name, "")}
        if "/scripts" in url:
            parts = url.split("/applications/")[1].split("/")
            app, db = parts[0], parts[2]
            return {"items": self._mock_scripts.get(f"{app}.{db}", [])}
        if "/filters" in url:
            parts = url.split("/applications/")[1].split("/")
            app, db = parts[0], parts[2]
            return {"items": self._mock_filters.get(f"{app}.{db}", [])}
        if "/variables" in url:
            app = url.split("/applications/")[1].split("/")[0]
            return {"items": self._mock_variables.get(app, [])}
        return {}


def _make_connector_with_mock(**kwargs):
    """Create an EssbaseConnector with a mock REST client."""
    c = EssbaseConnector()
    mock_client = _MockEssbaseRestClient(**kwargs)
    mock_client._connected = True
    mock_client._config = EssbaseApiConfig(server_url="http://mock-essbase")
    c._client = mock_client
    c._connected = True
    return c


class TestEssbaseConnectorLifecycle:
    """Tests for connect/discover/extract/disconnect."""

    @pytest.mark.asyncio
    async def test_connect_with_mock(self):
        c = EssbaseConnector()
        c._client = _MockEssbaseRestClient()
        result = await c.connect({"server_url": "http://essbase", "username": "admin", "password": "pw"})
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Connection fails if _http_get returns error status."""
        class FailClient(EssbaseRestClient):
            async def _http_get(self, url, params=None):
                return {"status": "error"}
        c = EssbaseConnector()
        c._client = FailClient()
        result = await c.connect({"server_url": "http://bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_exception(self):
        """Connection fails gracefully on exception."""
        class ExcClient(EssbaseRestClient):
            async def _http_get(self, url, params=None):
                raise ConnectionError("timeout")
        c = EssbaseConnector()
        c._client = ExcClient()
        result = await c.connect({"server_url": "http://bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_discover_empty(self):
        c = _make_connector_with_mock(apps=[])
        assets = await c.discover()
        assert assets == []

    @pytest.mark.asyncio
    async def test_discover_single_app_single_cube(self):
        c = _make_connector_with_mock(
            apps=[{"name": "Sample"}],
            dbs={"Sample": [{"name": "Basic", "type": "BSO"}]},
        )
        assets = await c.discover()
        cubes = [a for a in assets if a.asset_type == "cube"]
        assert len(cubes) == 1
        assert cubes[0].asset_id == "Sample.Basic"
        assert cubes[0].metadata["cube_type"] == "BSO"

    @pytest.mark.asyncio
    async def test_discover_with_dimensions(self):
        c = _make_connector_with_mock(
            apps=[{"name": "App1"}],
            dbs={"App1": [{"name": "DB1"}]},
            outline={"App1.DB1": {"dimensions": [
                {"name": "Year", "dimensionType": "time", "storageType": "dense"},
                {"name": "Product", "dimensionType": "regular", "storageType": "sparse"},
            ]}},
        )
        assets = await c.discover()
        dims = [a for a in assets if a.asset_type == "dimension"]
        assert len(dims) == 2
        names = {d.name for d in dims}
        assert "Year" in names
        assert "Product" in names

    @pytest.mark.asyncio
    async def test_discover_with_calc_scripts(self):
        c = _make_connector_with_mock(
            apps=[{"name": "Fin"}],
            dbs={"Fin": [{"name": "Plan"}]},
            scripts={"Fin.Plan": [{"name": "CalcAll"}, {"name": "Agg"}]},
        )
        assets = await c.discover()
        calcs = [a for a in assets if a.asset_type == "calcScript"]
        assert len(calcs) == 2

    @pytest.mark.asyncio
    async def test_discover_with_filters(self):
        c = _make_connector_with_mock(
            apps=[{"name": "Sales"}],
            dbs={"Sales": [{"name": "Budget"}]},
            filters={"Sales.Budget": [{"name": "RegionFilter"}]},
        )
        assets = await c.discover()
        flt = [a for a in assets if a.asset_type == "filter"]
        assert len(flt) == 1
        assert flt[0].name == "RegionFilter"

    @pytest.mark.asyncio
    async def test_discover_with_variables(self):
        c = _make_connector_with_mock(
            apps=[{"name": "App1"}],
            dbs={"App1": [{"name": "DB1"}]},
            variables={"App1": [{"name": "CurMonth", "value": "Jan", "scope": "application"}]},
        )
        assets = await c.discover()
        vars_ = [a for a in assets if a.asset_type == "substitutionVariable"]
        assert len(vars_) == 1
        assert vars_[0].metadata["value"] == "Jan"

    @pytest.mark.asyncio
    async def test_discover_multiple_apps(self):
        c = _make_connector_with_mock(
            apps=[{"name": "Fin"}, {"name": "HR"}],
            dbs={"Fin": [{"name": "Plan"}], "HR": [{"name": "Headcount"}]},
        )
        assets = await c.discover()
        cubes = [a for a in assets if a.asset_type == "cube"]
        assert len(cubes) == 2

    @pytest.mark.asyncio
    async def test_discover_not_connected(self):
        c = EssbaseConnector()
        with pytest.raises(RuntimeError, match="Not connected"):
            await c.discover()

    @pytest.mark.asyncio
    async def test_extract_metadata_empty(self):
        c = _make_connector_with_mock()
        result = await c.extract_metadata()
        assert result.platform == "essbase"
        assert result.count == 0

    @pytest.mark.asyncio
    async def test_extract_enriches_calc_scripts(self):
        c = _make_connector_with_mock(
            apps=[{"name": "App1"}],
            dbs={"App1": [{"name": "DB1"}]},
            scripts={"App1.DB1": [{"name": "Agg"}]},
        )
        c._client._mock_script_content = {"Agg": '@SUM("Sales")'}
        await c.discover()
        result = await c.extract_metadata()
        calcs = [a for a in result.assets if a.asset_type == "calcScript"]
        assert len(calcs) == 1
        assert "dax_translation" in calcs[0].metadata
        assert calcs[0].metadata["translation_confidence"] <= 1.0

    @pytest.mark.asyncio
    async def test_extract_with_specific_ids(self):
        c = _make_connector_with_mock(
            apps=[{"name": "A"}],
            dbs={"A": [{"name": "D"}]},
        )
        await c.discover()
        result = await c.extract_metadata(asset_ids=["A.D"])
        # Should only return the one matching cube
        assert len(result.assets) == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        c = _make_connector_with_mock()
        await c.disconnect()
        assert c._connected is False


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

    def test_alias_table_default(self):
        dim = EssbaseDimension(name="D")
        assert dim.alias_table == "Default"


# ===================================================================
# EssbaseMember data model
# ===================================================================


class TestEssbaseMember:
    """Tests for the member data model."""

    def test_default_values(self):
        m = EssbaseMember(name="Revenue")
        assert m.name == "Revenue"
        assert m.alias == ""
        assert m.consolidation == "+"
        assert m.storage_type == "store"
        assert m.formula == ""
        assert m.uda_list == []

    def test_dynamic_calc_member(self):
        m = EssbaseMember(
            name="Profit",
            storage_type="dynamic_calc",
            formula="Revenue - COGS;",
        )
        assert m.storage_type == "dynamic_calc"
        assert m.formula != ""

    def test_shared_member(self):
        m = EssbaseMember(name="Qtr1_Shared", storage_type="shared", parent="Fiscal")
        assert m.storage_type == "shared"
        assert m.parent == "Fiscal"


# ===================================================================
# EssbaseCalcScript data model
# ===================================================================


class TestEssbaseCalcScript:
    def test_basic(self):
        s = EssbaseCalcScript(name="Agg", content="AGG(Year);")
        assert s.name == "Agg"
        assert "AGG" in s.content

    def test_with_app_db(self):
        s = EssbaseCalcScript(name="Calc", content="FIX(...)", application="Fin", database="Plan")
        assert s.application == "Fin"
        assert s.database == "Plan"


# ===================================================================
# EssbaseFilter data model
# ===================================================================


class TestEssbaseFilter:
    def test_basic(self):
        f = EssbaseFilter(name="RegionFilter")
        assert f.name == "RegionFilter"
        assert f.rows == []

    def test_with_rows(self):
        f = EssbaseFilter(name="F1", rows=[{"member": "West", "access": "read"}])
        assert len(f.rows) == 1


# ===================================================================
# EssbaseSubstitutionVar data model
# ===================================================================


class TestEssbaseSubstitutionVar:
    def test_basic(self):
        v = EssbaseSubstitutionVar(name="CurMonth", value="Jan")
        assert v.name == "CurMonth"
        assert v.scope == "application"


# ===================================================================
# ParsedOutline data model
# ===================================================================


class TestParsedOutline:
    def test_empty(self):
        o = ParsedOutline()
        assert o.application == ""
        assert not o.is_valid
        assert o.total_members == 0
        assert o.dimension_names == []

    def test_valid_with_dimensions(self):
        o = ParsedOutline(
            application="App",
            database="DB",
            dimensions=[EssbaseDimension(name="Year", members=["Q1", "Q2"])],
        )
        assert o.is_valid
        assert o.total_members == 2
        assert o.dimension_names == ["Year"]

    def test_errors_make_invalid(self):
        o = ParsedOutline(
            dimensions=[EssbaseDimension(name="D")],
            errors=["parse error"],
        )
        assert not o.is_valid

    def test_total_dynamic_calcs(self):
        o = ParsedOutline(
            dimensions=[EssbaseDimension(
                name="Acct",
                members=["Rev", "Prof"],
                member_details=[
                    EssbaseMember(name="Rev", storage_type="store"),
                    EssbaseMember(name="Prof", storage_type="dynamic_calc"),
                ],
            )],
        )
        assert o.total_dynamic_calcs == 1


# ===================================================================
# EssbaseCalcTranslator
# ===================================================================


class TestEssbaseCalcTranslator:
    """Tests for the calc script → DAX translator."""

    def test_rule_count(self):
        t = EssbaseCalcTranslator()
        assert t.rule_count == len(_ESSBASE_CALC_PATTERNS)

    def test_catalog(self):
        t = EssbaseCalcTranslator()
        assert t.catalog is ESSBASE_TO_DAX_RULES

    def test_translate_sum(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula('@SUM(Sales)')
        assert "SUM(" in r.dax_expression
        assert r.confidence == 1.0

    def test_translate_avg(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@AVG(Amount)")
        assert "AVERAGE(" in r.dax_expression

    def test_translate_min_max(self):
        t = EssbaseCalcTranslator()
        assert "MIN(" in t.translate_formula("@MIN(x)").dax_expression
        assert "MAX(" in t.translate_formula("@MAX(x)").dax_expression

    def test_translate_math_functions(self):
        t = EssbaseCalcTranslator()
        assert "ABS(" in t.translate_formula("@ABS(x)").dax_expression
        assert "ROUND(" in t.translate_formula("@ROUND(x, 2)").dax_expression
        assert "POWER(" in t.translate_formula("@POWER(x, 3)").dax_expression
        assert "LOG10(" in t.translate_formula("@LOG10(x)").dax_expression
        assert "LOG(" in t.translate_formula("@LOG(x)").dax_expression
        assert "EXP(" in t.translate_formula("@EXP(x)").dax_expression
        assert "SQRT(" in t.translate_formula("@SQRT(x)").dax_expression
        assert "MOD(" in t.translate_formula("@MOD(x, 3)").dax_expression
        assert "TRUNC(" in t.translate_formula("@TRUNCATE(x)").dax_expression
        assert "INT(" in t.translate_formula("@INT(x)").dax_expression

    def test_translate_string_functions(self):
        t = EssbaseCalcTranslator()
        assert "CONCATENATE(" in t.translate_formula("@CONCATENATE(a, b)").dax_expression
        assert "MID(" in t.translate_formula("@SUBSTRING(s, 1, 3)").dax_expression
        assert "SELECTEDVALUE(" in t.translate_formula("@NAME(dim)").dax_expression

    def test_translate_missing(self):
        t = EssbaseCalcTranslator()
        assert "BLANK()" in t.translate_formula("#MISSING").dax_expression
        assert "ISBLANK(" in t.translate_formula("@ISMISSING(x)").dax_expression

    def test_direct_confidence(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@ABS(x)")
        assert r.confidence == 1.0

    def test_parametric_confidence(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@PRIOR(Sales)")
        assert r.confidence == 0.7

    def test_complex_confidence(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@PARENTVAL(Sales)")
        assert r.confidence == 0.5
        assert len(r.warnings) > 0

    def test_unsupported_confidence(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@ALLOCATE(x, y, z)")
        assert r.confidence == 0.2
        assert r.method == "unsupported"

    def test_translate_cross_dim(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@SUMRANGE(Sales, Yr)")
        assert "CALCULATE" in r.dax_expression

    def test_translate_member_functions(self):
        t = EssbaseCalcTranslator()
        assert "FILTER(" in t.translate_formula("@CHILDREN(Market)").dax_expression
        assert "FILTER(" in t.translate_formula("@DESCENDANTS(Year)").dax_expression
        assert "LOOKUPVALUE(" in t.translate_formula("@PARENT(Jan)").dax_expression
        assert "HASONEVALUE(" in t.translate_formula("@ISMBR(East)").dax_expression

    def test_translate_batch(self):
        t = EssbaseCalcTranslator()
        scripts = [
            EssbaseCalcScript(name="S1", content="@SUM(Sales)"),
            EssbaseCalcScript(name="S2", content="@ALLOCATE(Cost)"),
        ]
        results = t.translate_batch(scripts)
        assert len(results) == 2
        assert results[0].confidence == 1.0
        assert results[1].confidence == 0.2

    def test_translate_script_object(self):
        t = EssbaseCalcTranslator()
        script = EssbaseCalcScript(name="MyCalc", content="@ABS(Revenue)")
        r = t.translate(script)
        assert r.source_name == "MyCalc"
        assert "ABS(" in r.dax_expression

    def test_multiple_functions_in_one_formula(self):
        t = EssbaseCalcTranslator()
        r = t.translate_formula("@ABS(@SUM(Sales) - @AVG(Cost))")
        assert "ABS(" in r.dax_expression
        assert "SUM(" in r.dax_expression
        assert "AVERAGE(" in r.dax_expression

    def test_complex_lowers_confidence_for_mixed(self):
        t = EssbaseCalcTranslator()
        # Mixes direct (@ABS) with complex (@PARENTVAL)
        r = t.translate_formula("@ABS(@PARENTVAL(Revenue))")
        assert r.confidence == 0.5


# ===================================================================
# EssbaseMdxTranslator
# ===================================================================


class TestEssbaseMdxTranslator:
    """Tests for the MDX → DAX translator."""

    def test_rule_count(self):
        t = EssbaseMdxTranslator()
        assert t.rule_count == len(_ESSBASE_MDX_PATTERNS)

    def test_translate_measure_ref(self):
        t = EssbaseMdxTranslator()
        r = t.translate("[Measures].[Revenue]")
        assert "[Revenue]" in r.dax_expression

    def test_translate_iif(self):
        t = EssbaseMdxTranslator()
        r = t.translate("IIF(x > 0, x, 0)")
        assert "IF(" in r.dax_expression

    def test_translate_isempty(self):
        t = EssbaseMdxTranslator()
        r = t.translate("IsEmpty(val)")
        assert "ISBLANK(" in r.dax_expression

    def test_translate_ytd(self):
        t = EssbaseMdxTranslator()
        r = t.translate("YTD([Time].[Q4])")
        assert "DATESYTD" in r.dax_expression

    def test_translate_qtd(self):
        t = EssbaseMdxTranslator()
        r = t.translate("QTD([Time].[Mar])")
        assert "DATESQTD" in r.dax_expression

    def test_translate_mtd(self):
        t = EssbaseMdxTranslator()
        r = t.translate("MTD([Time].[Jan])")
        assert "DATESMTD" in r.dax_expression

    def test_translate_union(self):
        t = EssbaseMdxTranslator()
        r = t.translate("Union(set1, set2)")
        assert "UNION(" in r.dax_expression

    def test_translate_intersect(self):
        t = EssbaseMdxTranslator()
        r = t.translate("Intersect(s1, s2)")
        assert "INTERSECT(" in r.dax_expression

    def test_translate_except(self):
        t = EssbaseMdxTranslator()
        r = t.translate("Except(s1, s2)")
        assert "EXCEPT(" in r.dax_expression

    def test_translate_topcount(self):
        t = EssbaseMdxTranslator()
        r = t.translate("TopCount(set, 10, expr)")
        assert "TOPN(" in r.dax_expression

    def test_translate_coalesce_empty(self):
        t = EssbaseMdxTranslator()
        r = t.translate("CoalesceEmpty(val, 0)")
        assert "COALESCE(" in r.dax_expression

    def test_translate_abs_round_int(self):
        t = EssbaseMdxTranslator()
        assert "ABS(" in t.translate("Abs(x)").dax_expression
        assert "ROUND(" in t.translate("Round(x, 2)").dax_expression
        assert "INT(" in t.translate("Int(x)").dax_expression

    def test_complex_aggregate(self):
        t = EssbaseMdxTranslator()
        r = t.translate("Aggregate({[Product].Children})")
        assert r.confidence <= 0.5

    def test_complex_filter(self):
        t = EssbaseMdxTranslator()
        r = t.translate("Filter({members}, condition)")
        assert r.confidence <= 0.5

    def test_case_when(self):
        t = EssbaseMdxTranslator()
        r = t.translate("CASE WHEN x > 0 THEN 1 ELSE 0 END")
        assert "SWITCH(TRUE()," in r.dax_expression

    def test_parallel_period(self):
        t = EssbaseMdxTranslator()
        r = t.translate("ParallelPeriod([Time].[Year], 1, [Time].[Jan])")
        assert "PARALLELPERIOD(" in r.dax_expression

    def test_current_member(self):
        t = EssbaseMdxTranslator()
        r = t.translate("[Product].CurrentMember")
        assert "SELECTEDVALUE" in r.dax_expression

    def test_children(self):
        t = EssbaseMdxTranslator()
        r = t.translate("[Year].Children")
        assert "VALUES" in r.dax_expression


# ===================================================================
# EssbaseOutlineParser — XML
# ===================================================================


class TestEssbaseOutlineParserXml:
    """Tests for XML outline parsing."""

    def test_parse_basic_xml(self):
        xml = """<outline>
            <dimension name="Year" type="time" storageType="dense">
                <member name="Q1" generation="1" level="1" />
                <member name="Q2" generation="1" level="1" />
            </dimension>
            <dimension name="Product" type="regular" storageType="sparse">
                <member name="Cola" />
            </dimension>
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml, app="App", db="DB")
        assert result.application == "App"
        assert len(result.dimensions) == 2
        assert result.dimensions[0].name == "Year"
        assert result.dimensions[0].dimension_type == "time"
        assert result.dimensions[1].name == "Product"

    def test_parse_xml_bytes(self):
        xml = b"""<outline>
            <dimension name="Market" storageType="sparse">
                <member name="East" />
                <member name="West" />
            </dimension>
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        assert len(result.dimensions) == 1
        assert len(result.dimensions[0].members) == 2

    def test_parse_invalid_xml(self):
        parser = EssbaseOutlineParser()
        result = parser.parse_xml("<broken>")
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_parse_xml_member_as_dimension(self):
        xml = """<root>
            <member name="Year" dimension="true" type="time">
                <member name="Q1" />
            </member>
        </root>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        # Should detect member flagged as dimension
        assert len(result.dimensions) >= 1

    def test_parse_xml_accounts_type(self):
        xml = """<outline>
            <dimension name="Acct" type="accounts" />
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        assert result.dimensions[0].dimension_type == "accounts"

    def test_parse_xml_attribute_type(self):
        xml = """<outline>
            <dimension name="Size" type="attribute" />
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        assert result.dimensions[0].dimension_type == "attribute"

    def test_parse_xml_member_details(self):
        xml = """<outline>
            <dimension name="Year">
                <member name="Q1" generation="2" level="1" consolidation="+" storageType="store" />
            </dimension>
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        assert len(result.dimensions[0].member_details) == 1
        m = result.dimensions[0].member_details[0]
        assert m.name == "Q1"
        assert m.generation == 2
        assert m.consolidation == "+"

    def test_parse_xml_dynamic_calc(self):
        xml = """<outline>
            <dimension name="Acct">
                <member name="Profit" storageType="dynamic_calc" formula="Rev - COGS" />
            </dimension>
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        m = result.dimensions[0].member_details[0]
        assert m.storage_type == "dynamic_calc"
        assert m.formula == "Rev - COGS"

    def test_parse_xml_uda(self):
        xml = """<outline>
            <dimension name="Product">
                <member name="Cola" uda="Active,TopSeller" />
            </dimension>
        </outline>"""
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        m = result.dimensions[0].member_details[0]
        assert "Active" in m.uda_list
        assert "TopSeller" in m.uda_list

    def test_empty_outline(self):
        xml = "<outline></outline>"
        parser = EssbaseOutlineParser()
        result = parser.parse_xml(xml)
        assert len(result.dimensions) == 0


# ===================================================================
# EssbaseOutlineParser — JSON
# ===================================================================


class TestEssbaseOutlineParserJson:
    """Tests for JSON outline parsing."""

    def test_parse_json_basic(self):
        data = {
            "dimensions": [
                {"name": "Year", "dimensionType": "time", "storageType": "dense"},
                {"name": "Product", "dimensionType": "regular", "storageType": "sparse"},
            ]
        }
        parser = EssbaseOutlineParser()
        result = parser.parse_json(data, app="App1", db="DB1")
        assert len(result.dimensions) == 2
        assert result.dimensions[0].dimension_type == "time"

    def test_parse_json_with_members(self):
        data = {
            "dimensions": [{
                "name": "Year",
                "dimensionType": "time",
                "storageType": "dense",
                "children": [
                    {"name": "Q1", "generation": 2, "levelNumber": 1},
                    {"name": "Q2", "generation": 2, "levelNumber": 1},
                ],
            }]
        }
        parser = EssbaseOutlineParser()
        result = parser.parse_json(data)
        assert len(result.dimensions[0].members) == 2

    def test_parse_json_recursive_members(self):
        data = {
            "dimensions": [{
                "name": "Year",
                "dimensionType": "time",
                "storageType": "dense",
                "children": [{
                    "name": "Q1",
                    "children": [{"name": "Jan"}, {"name": "Feb"}],
                }],
            }]
        }
        parser = EssbaseOutlineParser()
        result = parser.parse_json(data)
        # Q1 + Jan + Feb = 3 members
        assert len(result.dimensions[0].members) == 3

    def test_parse_json_children_key(self):
        """Test that 'children' at top level also works."""
        data = {
            "children": [
                {"name": "Market", "dimensionType": "regular", "storageType": "sparse"},
            ]
        }
        parser = EssbaseOutlineParser()
        result = parser.parse_json(data)
        assert len(result.dimensions) == 1

    def test_parse_json_empty(self):
        parser = EssbaseOutlineParser()
        result = parser.parse_json({})
        assert len(result.dimensions) == 0

    def test_parse_json_with_aliases(self):
        data = {
            "dimensions": [{
                "name": "Product",
                "dimensionType": "regular",
                "storageType": "sparse",
                "children": [{"name": "P100", "aliases": {"Default": "Cola"}}],
            }]
        }
        parser = EssbaseOutlineParser()
        result = parser.parse_json(data)
        assert result.dimensions[0].member_details[0].alias == "Cola"


# ===================================================================
# EssbaseRestClient
# ===================================================================


class TestEssbaseRestClient:
    """Tests for the REST client (mock HTTP)."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        client = _MockEssbaseRestClient()
        cfg = EssbaseApiConfig(server_url="http://essbase:9000", username="admin", password="pw")
        result = await client.connect(cfg)
        assert result is True
        assert client.is_connected

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        class FailAbout(EssbaseRestClient):
            async def _http_get(self, url, params=None):
                return {"status": "error"}
        client = FailAbout()
        cfg = EssbaseApiConfig(server_url="http://bad")
        result = await client.connect(cfg)
        assert result is False

    @pytest.mark.asyncio
    async def test_list_applications(self):
        client = _MockEssbaseRestClient(apps=[{"name": "Fin"}, {"name": "HR"}])
        client._connected = True
        client._config = EssbaseApiConfig(server_url="http://essbase")
        apps = await client.list_applications()
        assert len(apps) == 2

    @pytest.mark.asyncio
    async def test_list_databases(self):
        client = _MockEssbaseRestClient(dbs={"Fin": [{"name": "Plan"}, {"name": "Actual"}]})
        client._connected = True
        client._config = EssbaseApiConfig(server_url="http://essbase")
        dbs = await client.list_databases("Fin")
        assert len(dbs) == 2

    @pytest.mark.asyncio
    async def test_not_connected_raises(self):
        client = EssbaseRestClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_applications()

    @pytest.mark.asyncio
    async def test_disconnect(self):
        client = _MockEssbaseRestClient()
        client._connected = True
        await client.disconnect()
        assert not client.is_connected

    def test_api_config_base_url(self):
        cfg = EssbaseApiConfig(server_url="http://essbase:9000/")
        assert cfg.base_url == "http://essbase:9000/essbase/rest/v1"

    def test_api_config_no_trailing_slash(self):
        cfg = EssbaseApiConfig(server_url="http://essbase")
        assert cfg.base_url == "http://essbase/essbase/rest/v1"

    def test_auth_headers_basic(self):
        client = EssbaseRestClient()
        client._config = EssbaseApiConfig(username="admin", password="pw")
        headers = client._auth_headers()
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

    def test_auth_headers_empty(self):
        client = EssbaseRestClient()
        client._config = EssbaseApiConfig()
        assert client._auth_headers() == {}


# ===================================================================
# CalcTranslationResult
# ===================================================================


class TestCalcTranslationResult:
    def test_defaults(self):
        r = CalcTranslationResult(
            source_name="test",
            source_formula="@SUM(x)",
            dax_expression="SUM(x)",
        )
        assert r.method == "rules"
        assert r.confidence == 1.0
        assert r.warnings == []


# ===================================================================
# Calc script → DAX translation rules catalog
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

    def test_unsupported_rules_exist(self):
        unsupported = [r for r in ESSBASE_TO_DAX_RULES if r.difficulty == "unsupported"]
        assert len(unsupported) >= 2
        names = {r.essbase_function for r in unsupported}
        assert "@ALLOCATE" in names
        assert "@MDALLOCATE" in names

    def test_all_rules_have_dax_equivalent(self):
        for rule in ESSBASE_TO_DAX_RULES:
            assert rule.dax_equivalent, f"{rule.essbase_function} missing DAX equivalent"

    def test_rule_count_expanded(self):
        assert len(ESSBASE_TO_DAX_RULES) >= 50

    def test_missing_rules(self):
        names = {r.essbase_function for r in ESSBASE_TO_DAX_RULES}
        assert "#MISSING" in names
        assert "@ISMISSING" in names


# ===================================================================
# MDX → DAX translation rules catalog
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

    def test_rule_count_expanded(self):
        assert len(ESSBASE_MDX_TO_DAX) >= 20

    def test_set_operations(self):
        ops = {r[0] for r in ESSBASE_MDX_TO_DAX}
        assert any("Union" in o for o in ops)
        assert any("Intersect" in o for o in ops)
        assert any("Except" in o for o in ops)

    def test_topcount_bottomcount(self):
        names = [r[0] for r in ESSBASE_MDX_TO_DAX]
        assert any("TopCount" in n for n in names)
        assert any("BottomCount" in n for n in names)


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

    def test_created_connector_not_stub(self):
        from src.connectors.base_connector import build_default_registry
        registry = build_default_registry()
        connector = registry.create("essbase")
        assert connector.info().is_stub is False

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
