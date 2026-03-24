"""Tests for the Qlik Sense / QlikView connector.

Covers:
- Data models (QlikField, QlikTable, QlikApp, QlikMeasure, QlikDimension, etc.)
- QlikExpressionTranslator (55+ rules, confidence scoring)
- QlikLoadScriptParser (load script parsing)
- QlikEngineClient (mock HTTP)
- FullQlikConnector (lifecycle, discovery, extraction)
- Rule catalogs and mappings
- Qlik semantic bridge (QlikApp → SemanticModelIR)
"""

from __future__ import annotations

import pytest

from src.connectors.qlik_connector import (
    QLIK_TO_DAX_RULES,
    QLIK_TO_FABRIC_SOURCE,
    QLIK_TO_FABRIC_TYPE,
    QLIK_TO_TMDL_MAPPING,
    QLIK_VISUAL_TO_PBI,
    CalcTranslationResult,
    FullQlikConnector,
    ParsedLoadScript,
    QlikApp,
    QlikBookmark,
    QlikCalcRule,
    QlikDimension,
    QlikEngineClient,
    QlikEngineConfig,
    QlikExpressionTranslator,
    QlikField,
    QlikLoadScriptParser,
    QlikMeasure,
    QlikSheet,
    QlikTable,
    QlikVariable,
)
from src.connectors.qlik_semantic_bridge import (
    QlikConversionResult,
    QlikToSemanticModelConverter,
    QlikWhatsIfParameter,
)


# ===================================================================
# Helpers
# ===================================================================

SAMPLE_LOAD_SCRIPT = """\
LIB CONNECT TO 'DataWarehouse';
SET vCurrentYear = 2024;
LET vThreshold = 1000;

Sales:
LOAD
    OrderID,
    CustomerID,
    Revenue AS SalesAmount,
    Cost
FROM [lib://DataFiles/Sales.qvd] (qvd)
WHERE Revenue > 0;

Customers:
SQL SELECT CustomerID, CustomerName, Region, Country
FROM dbo.Customers
WHERE IsActive = 1;
"""


class _MockQlikEngineClient(QlikEngineClient):
    """Mock Qlik Engine API client for testing."""

    async def _http_get(self, url: str) -> dict:
        if "users/me" in url:
            return {"id": "user1", "userId": "user1"}
        if "items?type=app" in url:
            return {"data": [
                {"resourceId": "a1", "name": "Sales App", "resourceType": "app"},
                {"resourceId": "a2", "name": "HR App", "resourceType": "app"},
            ]}
        if "/script" in url:
            return {"script": SAMPLE_LOAD_SCRIPT}
        if "/measures" in url:
            return {"data": [
                {"qMeasure": {"qDef": "Sum(Revenue)", "qLabel": "Total Revenue"}, "title": "Revenue"},
            ]}
        if "/dimensions" in url:
            return {"data": []}
        if "/objects" in url:
            return {"data": []}
        if "/data/model" in url:
            return {"tables": []}
        return {}

    async def _http_post(self, url: str, data: dict) -> dict:
        return {}


def _make_connector_with_mock():
    connector = FullQlikConnector()
    mock_client = _MockQlikEngineClient()
    mock_client._config = QlikEngineConfig(server_url="http://mock-qlik")
    mock_client._connected = True
    connector._engine_client = mock_client
    connector._connected = True
    return connector


def _sample_app() -> QlikApp:
    return QlikApp(
        name="SalesApp",
        app_id="a1",
        tables=[
            QlikTable(
                name="Sales",
                fields=[
                    QlikField(name="OrderID", is_key=True),
                    QlikField(name="CustomerID"),
                    QlikField(name="Revenue", data_type="numeric"),
                    QlikField(name="Cost", data_type="numeric"),
                ],
                source_type="sql",
            ),
            QlikTable(
                name="Customers",
                fields=[
                    QlikField(name="CustomerID", is_key=True),
                    QlikField(name="CustomerName", data_type="text"),
                    QlikField(name="Region", data_type="text"),
                ],
                source_type="sql",
            ),
        ],
        measures=[
            QlikMeasure(name="Total Revenue", expression="Sum(Revenue)"),
            QlikMeasure(name="Profit", expression="Sum(Revenue) - Sum(Cost)"),
            QlikMeasure(name="YTD Sales", expression="Sum({$<Year={$(vCurrentYear)}>} Revenue)"),
        ],
        dimensions=[
            QlikDimension(name="Region", field_name="Region"),
            QlikDimension(
                name="Geography",
                is_drill_down=True,
                drill_down_fields=["Region", "Country"],
            ),
        ],
        variables=[
            QlikVariable(name="vCurrentYear", definition="2024"),
            QlikVariable(name="vThreshold", definition="1000"),
        ],
    )


# ===================================================================
# Data models
# ===================================================================


class TestQlikDataModels:
    def test_field_defaults(self):
        f = QlikField(name="Revenue")
        assert f.name == "Revenue"
        assert not f.is_key
        assert f.data_type == ""

    def test_table_with_fields(self):
        t = QlikTable(name="Sales", fields=[QlikField(name="A"), QlikField(name="B")])
        assert len(t.fields) == 2

    def test_measure(self):
        m = QlikMeasure(name="Rev", expression="Sum(Revenue)")
        assert m.expression == "Sum(Revenue)"

    def test_dimension(self):
        d = QlikDimension(name="Region", field_name="Region")
        assert d.field_name == "Region"
        assert not d.is_drill_down

    def test_drill_down_dimension(self):
        d = QlikDimension(name="Geo", is_drill_down=True, drill_down_fields=["Region", "Country"])
        assert d.is_drill_down
        assert len(d.drill_down_fields) == 2

    def test_variable(self):
        v = QlikVariable(name="vYear", definition="2024")
        assert v.definition == "2024"

    def test_bookmark(self):
        b = QlikBookmark(name="Q1 Sales", selections={"Region": ["East", "West"]})
        assert len(b.selections["Region"]) == 2

    def test_sheet(self):
        s = QlikSheet(name="Dashboard", objects=[{"type": "barchart"}])
        assert len(s.objects) == 1

    def test_app(self):
        app = _sample_app()
        assert app.field_count == 7  # 4 + 3
        assert app.table_names == ["Sales", "Customers"]

    def test_parsed_load_script_empty(self):
        p = ParsedLoadScript()
        assert p.is_valid
        assert p.table_count == 0

    def test_parsed_load_script_with_tables(self):
        p = ParsedLoadScript(tables=[QlikTable(name="T1"), QlikTable(name="T2")])
        assert p.table_count == 2
        assert p.table_names == ["T1", "T2"]


# ===================================================================
# Expression translator
# ===================================================================


class TestQlikExpressionTranslator:
    def test_rule_count(self):
        t = QlikExpressionTranslator()
        assert t.rule_count >= 65

    def test_catalog(self):
        t = QlikExpressionTranslator()
        cat = t.catalog()
        assert len(cat) >= 55
        assert all(isinstance(r, QlikCalcRule) for r in cat)

    def test_sum(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Sum(Revenue)", "Rev")
        assert "SUM(" in r.dax_expression

    def test_avg(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Avg(Price)", "AvgPrice")
        assert "AVERAGE(" in r.dax_expression

    def test_count(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Count(OrderID)", "Cnt")
        assert "COUNTROWS(" in r.dax_expression

    def test_if(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("If(Sales > 100, 'High', 'Low')", "Cat")
        assert "IF(" in r.dax_expression
        assert r.confidence <= 0.7

    def test_string_functions(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Upper(Trim(Name))")
        assert "UPPER(" in r.dax_expression
        assert "TRIM(" in r.dax_expression

    def test_left_right(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Left(Code, 3)")
        assert "LEFT(" in r.dax_expression

    def test_date_functions(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Year(Today())")
        assert "YEAR(" in r.dax_expression
        assert "TODAY(" in r.dax_expression

    def test_math_functions(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Round(Abs(Margin), 2)")
        assert "ROUND(" in r.dax_expression
        assert "ABS(" in r.dax_expression

    def test_set_analysis(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Sum({$<Year={2024}>} Revenue)")
        assert "CALCULATE" in r.dax_expression
        assert r.confidence <= 0.5

    def test_only(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Only(Status)")
        assert "SELECTEDVALUE(" in r.dax_expression

    def test_null_count(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("NullCount(Email)")
        assert "COUNTBLANK(" in r.dax_expression

    def test_mode_unsupported(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Mode(Category)")
        assert r.confidence <= 0.2
        assert r.method == "unsupported"

    def test_direct_confidence(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Abs(42)")
        assert r.confidence == 1.0

    def test_complex_confidence(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Above(Sum(Sales))")
        assert r.confidence <= 0.5

    def test_batch(self):
        t = QlikExpressionTranslator()
        measures = [
            QlikMeasure(name="A", expression="Sum(X)"),
            QlikMeasure(name="B", expression="Avg(Y)"),
        ]
        results = t.translate_batch(measures)
        assert len(results) == 2

    def test_translate_measure(self):
        t = QlikExpressionTranslator()
        m = QlikMeasure(name="Rev", expression="Sum(Revenue)")
        r = t.translate(m)
        assert r.source_name == "Rev"

    def test_dollar_sign_expansion(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Sum({$<Year={$(vYear)}>} Sales)")
        assert "CALCULATE" in r.dax_expression

    def test_rank(self):
        t = QlikExpressionTranslator()
        r = t.translate_expression("Rank(Sum(Sales))")
        assert "RANKX" in r.dax_expression


# ===================================================================
# Load script parser
# ===================================================================


class TestQlikLoadScriptParser:
    def test_parse_sample(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        assert result.is_valid
        assert result.table_count >= 2

    def test_parse_connections(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        assert "DataWarehouse" in result.connections

    def test_parse_variables(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        names = [v.name for v in result.variables]
        assert "vCurrentYear" in names
        assert "vThreshold" in names

    def test_parse_load_statement(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        sales = next((t for t in result.tables if t.name == "Sales"), None)
        assert sales is not None
        assert len(sales.fields) >= 3

    def test_parse_sql_select(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        cust = next((t for t in result.tables if t.name == "Customers"), None)
        assert cust is not None
        assert cust.source_type == "sql"

    def test_parse_field_as_alias(self):
        parser = QlikLoadScriptParser()
        result = parser.parse(SAMPLE_LOAD_SCRIPT)
        sales = next(t for t in result.tables if t.name == "Sales")
        names = [f.name for f in sales.fields]
        assert "SalesAmount" in names

    def test_parse_empty_script(self):
        parser = QlikLoadScriptParser()
        result = parser.parse("")
        assert result.is_valid
        assert result.table_count == 0

    def test_parse_inline(self):
        script = """
InlineTable:
LOAD * INLINE [
  ID, Name
  1, Alice
  2, Bob
];
"""
        parser = QlikLoadScriptParser()
        result = parser.parse(script)
        assert result.table_count >= 1


# ===================================================================
# Engine client
# ===================================================================


class TestQlikEngineClient:
    @pytest.mark.asyncio
    async def test_mock_connect(self):
        client = _MockQlikEngineClient()
        ok = await client.connect(QlikEngineConfig(server_url="http://mock"))
        assert ok

    @pytest.mark.asyncio
    async def test_list_apps(self):
        client = _MockQlikEngineClient()
        client._config = QlikEngineConfig(server_url="http://mock")
        apps = await client.list_apps()
        assert len(apps) == 2

    @pytest.mark.asyncio
    async def test_get_app_script(self):
        client = _MockQlikEngineClient()
        client._config = QlikEngineConfig(server_url="http://mock")
        script = await client.get_app_script("a1")
        assert "LOAD" in script

    @pytest.mark.asyncio
    async def test_get_app_measures(self):
        client = _MockQlikEngineClient()
        client._config = QlikEngineConfig(server_url="http://mock")
        measures = await client.get_app_measures("a1")
        assert len(measures) == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        client = _MockQlikEngineClient()
        client._connected = True
        await client.disconnect()
        assert not client._connected

    def test_config_base_url(self):
        c = QlikEngineConfig(server_url="http://qlik.example.com")
        assert c.base_url == "http://qlik.example.com/api/v1"

    def test_auth_headers(self):
        client = QlikEngineClient()
        client._config = QlikEngineConfig(server_url="http://x", api_key="mykey")
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer mykey"


# ===================================================================
# Full connector
# ===================================================================


class TestFullQlikConnector:
    def test_info_not_stub(self):
        c = _make_connector_with_mock()
        info = c.info()
        assert not info.is_stub
        assert info.version == "1.0.0"
        assert "qlik" in info.platform.value

    @pytest.mark.asyncio
    async def test_discover(self):
        c = _make_connector_with_mock()
        assets = await c.discover()
        assert len(assets) == 2  # 2 apps

    @pytest.mark.asyncio
    async def test_extract_enriches_apps(self):
        c = _make_connector_with_mock()
        await c.discover()
        result = await c.extract_metadata()
        app_assets = [a for a in result.assets if a.asset_type == "app"]
        assert any("parsed_script" in a.metadata for a in app_assets)

    @pytest.mark.asyncio
    async def test_extract_with_ids(self):
        c = _make_connector_with_mock()
        await c.discover()
        result = await c.extract_metadata(asset_ids=["a1"])
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        c = _make_connector_with_mock()
        await c.disconnect()
        assert not c._connected


# ===================================================================
# Rule catalogs and mappings
# ===================================================================


class TestQlikRuleCatalogs:
    def test_dax_rules_count(self):
        assert len(QLIK_TO_DAX_RULES) >= 55

    def test_rules_have_fields(self):
        for rule in QLIK_TO_DAX_RULES:
            assert rule.qlik_function
            assert rule.dax_equivalent
            assert rule.difficulty in ("direct", "parametric", "complex", "unsupported")

    def test_fabric_source_mapping(self):
        assert QLIK_TO_FABRIC_SOURCE["oracle"] == "OracleDatabase"
        assert QLIK_TO_FABRIC_SOURCE["qvd"] == "File"

    def test_fabric_type_mapping(self):
        assert QLIK_TO_FABRIC_TYPE["numeric"] == "double"
        assert QLIK_TO_FABRIC_TYPE["text"] == "string"

    def test_visual_mapping(self):
        assert QLIK_VISUAL_TO_PBI["barchart"] == "clusteredBarChart"
        assert QLIK_VISUAL_TO_PBI["pivot-table"] == "matrix"
        assert len(QLIK_VISUAL_TO_PBI) >= 17

    def test_tmdl_mapping(self):
        assert QLIK_TO_TMDL_MAPPING["App"] == "Semantic Model + Report"
        assert QLIK_TO_TMDL_MAPPING["Field"] == "Column"
        assert len(QLIK_TO_TMDL_MAPPING) >= 20


# ===================================================================
# Registration
# ===================================================================


class TestQlikRegistration:
    def test_registry_contains_qlik(self):
        from src.connectors.base_connector import build_default_registry
        reg = build_default_registry()
        assert reg.is_registered("qlik")

    def test_connector_is_not_stub(self):
        from src.connectors.base_connector import build_default_registry
        reg = build_default_registry()
        connector = reg.create("qlik")
        assert connector is not None
        assert not connector.info().is_stub


# ===================================================================
# Qlik semantic bridge
# ===================================================================


class TestQlikSemanticBridge:
    def test_basic_conversion(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        assert isinstance(result, QlikConversionResult)
        assert result.table_count >= 2

    def test_model_name(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        assert result.ir.model_name == "SalesApp"

    def test_model_name_override(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app(), model_name="Custom")
        assert result.ir.model_name == "Custom"

    def test_tables_created(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        names = [t.name for t in result.ir.tables]
        assert "Sales" in names
        assert "Customers" in names

    def test_fields_become_columns(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        sales = result.ir.table_by_name("Sales")
        col_names = [c.name for c in sales.columns]
        assert "OrderID" in col_names
        assert "Revenue" in col_names

    def test_measures_translated(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        assert result.measure_count >= 3
        assert len(result.calc_translations) >= 3

    def test_drill_down_creates_hierarchy(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        # Find the table with the Geography hierarchy
        found = False
        for table in result.ir.tables:
            for h in table.hierarchies:
                if h.name == "Geography":
                    assert len(h.levels) == 2
                    found = True
        assert found

    def test_variables_become_whatif(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        assert len(result.whatif_parameters) == 2
        names = [p.name for p in result.whatif_parameters]
        assert "vCurrentYear" in names

    def test_joins_inferred(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        # Sales.CustomerID ↔ Customers.CustomerID
        assert result.relationship_count >= 1

    def test_subject_area(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(_sample_app())
        assert len(result.ir.subject_areas) == 1
        assert result.ir.subject_areas[0].name == "SalesApp"

    def test_empty_app(self):
        converter = QlikToSemanticModelConverter()
        result = converter.convert(QlikApp(name="Empty"))
        assert result.table_count >= 1  # at least measures table

    def test_low_confidence_in_review(self):
        app = QlikApp(
            name="Test",
            measures=[QlikMeasure(name="Weird", expression="Mode(Category)")],
        )
        converter = QlikToSemanticModelConverter()
        result = converter.convert(app)
        assert len(result.review_items) >= 1
