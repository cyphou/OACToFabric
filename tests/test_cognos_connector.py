"""Tests for the IBM Cognos Analytics connector.

Covers:
- Data models (CognosDataItem, CognosQuery, CognosReport, CognosPrompt, etc.)
- CognosExpressionTranslator (50+ rules, confidence scoring)
- CognosReportSpecParser (XML parsing)
- CognosRestClient (mock HTTP)
- FullCognosConnector (lifecycle, discovery, extraction)
- Rule catalogs and mappings
- Cognos semantic bridge (ParsedReportSpec → SemanticModelIR)
"""

from __future__ import annotations

import pytest

from src.connectors.cognos_connector import (
    COGNOS_PROMPT_TO_PBI,
    COGNOS_TO_DAX_RULES,
    COGNOS_TO_FABRIC_SOURCE,
    COGNOS_TO_FABRIC_TYPE,
    COGNOS_TO_TMDL_MAPPING,
    COGNOS_VISUAL_TO_PBI,
    CalcTranslationResult,
    CognosApiConfig,
    CognosCalcRule,
    CognosDataItem,
    CognosDataSource,
    CognosExpressionTranslator,
    CognosPackage,
    CognosPrompt,
    CognosQuery,
    CognosReport,
    CognosReportPage,
    CognosReportSpecParser,
    CognosRestClient,
    CognosVisualization,
    FullCognosConnector,
    ParsedReportSpec,
)
from src.connectors.cognos_semantic_bridge import (
    CognosConversionResult,
    CognosRlsRole,
    CognosSlicerDefinition,
    CognosToSemanticModelConverter,
)


# ===================================================================
# Helpers
# ===================================================================

SAMPLE_REPORT_XML = """\
<report name="SalesReport">
  <query name="SalesQuery">
    <dataItem name="Revenue" aggregate="total" label="Revenue">
      <expression>total([Sales].[Revenue])</expression>
    </dataItem>
    <dataItem name="Region" label="Region" usage="attribute">
      <expression>[Geography].[Region]</expression>
    </dataItem>
    <detailFilter>
      <filterExpression>[Geography].[Country] = 'USA'</filterExpression>
    </detailFilter>
  </query>
  <page name="Page1">
    <list name="SalesList" refQuery="SalesQuery">
      <dataItemRef refDataItem="Revenue" />
      <dataItemRef refDataItem="Region" />
    </list>
    <chart name="SalesChart" chartType="bar" refQuery="SalesQuery">
      <dataItemRef refDataItem="Revenue" />
    </chart>
  </page>
  <selectValue name="RegionPrompt" parameter="p_region" required="true" multiSelect="true" />
  <datePrompt name="DatePrompt" parameter="p_date" />
</report>
"""


class _MockCognosRestClient(CognosRestClient):
    """Mock Cognos REST client for testing."""

    async def _http_get(self, url: str) -> dict:
        if "content?type=report" in url:
            return {"content": [
                {"id": "r1", "name": "Sales Report", "path": "/Reports/Sales"},
                {"id": "r2", "name": "HR Report", "path": "/Reports/HR"},
            ]}
        if "content?type=exploration" in url:
            return {"content": [
                {"id": "d1", "name": "Executive Dashboard", "path": "/Dashboards/Exec"},
            ]}
        if "content?type=package" in url:
            return {"content": [
                {"id": "p1", "name": "Sales Package", "path": "/Packages/Sales"},
            ]}
        if "specification" in url:
            return {"specification": SAMPLE_REPORT_XML}
        if "datasources" in url:
            return {"dataSources": [{"name": "OracleDB", "type": "oracle"}]}
        return {}

    async def _http_put(self, url: str, data: dict) -> dict:
        return {"session_id": "mock-session"}

    async def _http_post(self, url: str, data: dict) -> dict:
        return {}

    async def _http_delete(self, url: str) -> dict:
        return {}


def _make_connector_with_mock():
    connector = FullCognosConnector()
    mock_client = _MockCognosRestClient()
    mock_client._config = CognosApiConfig(server_url="http://mock-cognos")
    mock_client._connected = True
    connector._rest_client = mock_client
    connector._connected = True
    return connector


# ===================================================================
# Data models
# ===================================================================


class TestCognosDataModels:
    def test_data_item_defaults(self):
        item = CognosDataItem(name="Revenue")
        assert item.name == "Revenue"
        assert item.aggregate == ""
        assert item.usage == "fact"

    def test_query_with_items(self):
        q = CognosQuery(
            name="Q1",
            data_items=[CognosDataItem(name="Sales"), CognosDataItem(name="Cost")],
        )
        assert len(q.data_items) == 2

    def test_report_structure(self):
        r = CognosReport(
            name="Test",
            queries=[CognosQuery(name="Q1")],
            pages=[CognosReportPage(name="P1")],
            prompts=[CognosPrompt(name="Pr1")],
        )
        assert len(r.queries) == 1
        assert len(r.pages) == 1
        assert len(r.prompts) == 1

    def test_package(self):
        pkg = CognosPackage(name="Sales", query_subjects=["Orders", "Products"])
        assert len(pkg.query_subjects) == 2

    def test_data_source(self):
        ds = CognosDataSource(name="DB", connection_type="oracle", database="ORCL")
        assert ds.connection_type == "oracle"

    def test_visualization(self):
        viz = CognosVisualization(viz_type="chart", chart_type="bar")
        assert viz.viz_type == "chart"

    def test_prompt(self):
        p = CognosPrompt(name="Region", prompt_type="select", required=True, multi_select=True)
        assert p.required
        assert p.multi_select

    def test_parsed_report_spec_empty(self):
        spec = ParsedReportSpec()
        assert not spec.is_valid
        assert spec.total_queries == 0

    def test_parsed_report_spec_valid(self):
        spec = ParsedReportSpec(reports=[CognosReport(name="R1", queries=[CognosQuery(name="Q1")])])
        assert spec.is_valid
        assert spec.total_queries == 1
        assert spec.report_names == ["R1"]


# ===================================================================
# Expression translator
# ===================================================================


class TestCognosExpressionTranslator:
    def test_rule_count(self):
        t = CognosExpressionTranslator()
        assert t.rule_count >= 55

    def test_catalog(self):
        t = CognosExpressionTranslator()
        cat = t.catalog()
        assert len(cat) >= 50
        assert all(isinstance(r, CognosCalcRule) for r in cat)

    def test_total(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("total([Sales].[Revenue])", "Rev")
        assert "SUM(" in r.dax_expression

    def test_average(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("average([Sales].[Price])", "AvgPrice")
        assert "AVERAGE(" in r.dax_expression

    def test_count(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("count([Orders].[OrderID])", "Cnt")
        assert "COUNTROWS(" in r.dax_expression

    def test_string_functions(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("upper(trim([Customer].[Name]))", "Name")
        assert "UPPER(" in r.dax_expression
        assert "TRIM(" in r.dax_expression

    def test_date_functions(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("_year([Order].[Date])", "Yr")
        assert "YEAR(" in r.dax_expression

    def test_math_functions(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("round(abs([Sales].[Margin]), 2)", "M")
        assert "ROUND(" in r.dax_expression
        assert "ABS(" in r.dax_expression

    def test_conditional(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("if([Sales].[Amount] > 100, 'High', 'Low')", "Cat")
        assert "IF(" in r.dax_expression

    def test_case_when(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("case when x > 0 then 'pos' else 'neg' end", "Sign")
        assert "SWITCH(" in r.dax_expression
        assert r.confidence <= 0.5

    def test_is_null(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("is-null([Customer].[Email])", "Chk")
        assert "ISBLANK(" in r.dax_expression

    def test_data_item_refs(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("[Sales].[Revenue]", "Rev")
        assert "'Sales'[Revenue]" in r.dax_expression

    def test_three_part_ref(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("[model].[Sales].[Revenue]", "Rev")
        assert "'Sales'[Revenue]" in r.dax_expression

    def test_direct_confidence(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("abs(42)", "X")
        assert r.confidence == 1.0

    def test_complex_confidence(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("running-total([Sales].[Revenue])", "RT")
        assert r.confidence <= 0.7

    def test_batch(self):
        t = CognosExpressionTranslator()
        items = [
            CognosDataItem(name="A", expression="total(x)"),
            CognosDataItem(name="B", expression="abs(y)"),
        ]
        results = t.translate_batch(items)
        assert len(results) == 2

    def test_translate_data_item(self):
        t = CognosExpressionTranslator()
        item = CognosDataItem(name="Rev", expression="total([Sales].[Revenue])")
        r = t.translate(item)
        assert r.source_name == "Rev"
        assert "SUM(" in r.dax_expression

    def test_olap_rolevalue(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("roleValue('_businessKey', [Product])")
        assert "RELATED" in r.dax_expression
        assert r.confidence <= 0.5

    def test_current_date(self):
        t = CognosExpressionTranslator()
        r = t.translate_expression("current_date")
        assert "TODAY()" in r.dax_expression


# ===================================================================
# Report spec parser
# ===================================================================


class TestCognosReportSpecParser:
    def test_parse_sample_xml(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        assert result.is_valid
        assert len(result.reports) == 1
        assert result.reports[0].name == "SalesReport"

    def test_parse_queries(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        report = result.reports[0]
        assert len(report.queries) == 1
        assert report.queries[0].name == "SalesQuery"
        assert len(report.queries[0].data_items) == 2

    def test_parse_data_items(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        items = result.reports[0].queries[0].data_items
        rev = next(i for i in items if i.name == "Revenue")
        assert "total" in rev.expression
        assert rev.aggregate == "total"

    def test_parse_pages(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        assert len(result.reports[0].pages) == 1
        page = result.reports[0].pages[0]
        assert page.name == "Page1"

    def test_parse_visualizations(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        page = result.reports[0].pages[0]
        assert len(page.visualizations) == 2  # list + chart

    def test_parse_prompts(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        assert len(result.reports[0].prompts) == 2  # selectValue + datePrompt

    def test_parse_detail_filters(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        q = result.reports[0].queries[0]
        assert len(q.detail_filters) == 1
        assert "USA" in q.detail_filters[0]

    def test_parse_invalid_xml(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml("<broken>>")
        assert not result.is_valid
        assert len(result.errors) > 0

    def test_parse_bytes(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML.encode("utf-8"))
        assert result.is_valid

    def test_parse_multiple(self):
        parser = CognosReportSpecParser()
        result = parser.parse_multiple([SAMPLE_REPORT_XML, SAMPLE_REPORT_XML])
        assert len(result.reports) == 2

    def test_total_props(self):
        parser = CognosReportSpecParser()
        result = parser.parse_xml(SAMPLE_REPORT_XML)
        assert result.total_queries == 1
        assert result.total_prompts == 2
        assert result.total_visualizations == 2


# ===================================================================
# REST client
# ===================================================================


class TestCognosRestClient:
    @pytest.mark.asyncio
    async def test_mock_connect(self):
        client = _MockCognosRestClient()
        ok = await client.connect(CognosApiConfig(server_url="http://mock"))
        assert ok

    @pytest.mark.asyncio
    async def test_list_reports(self):
        client = _MockCognosRestClient()
        client._config = CognosApiConfig(server_url="http://mock")
        reports = await client.list_reports()
        assert len(reports) == 2

    @pytest.mark.asyncio
    async def test_list_dashboards(self):
        client = _MockCognosRestClient()
        client._config = CognosApiConfig(server_url="http://mock")
        dashboards = await client.list_dashboards()
        assert len(dashboards) == 1

    @pytest.mark.asyncio
    async def test_list_packages(self):
        client = _MockCognosRestClient()
        client._config = CognosApiConfig(server_url="http://mock")
        packages = await client.list_packages()
        assert len(packages) == 1

    @pytest.mark.asyncio
    async def test_get_report_spec(self):
        client = _MockCognosRestClient()
        client._config = CognosApiConfig(server_url="http://mock")
        spec = await client.get_report_spec("r1")
        assert "SalesReport" in spec

    @pytest.mark.asyncio
    async def test_disconnect(self):
        client = _MockCognosRestClient()
        client._connected = True
        client._config = CognosApiConfig(server_url="http://mock")
        await client.disconnect()
        assert not client._connected

    def test_api_config_base_url(self):
        c = CognosApiConfig(server_url="http://cognos.example.com")
        assert c.base_url == "http://cognos.example.com/api/v1"

    def test_auth_headers_with_api_key(self):
        client = CognosRestClient()
        client._config = CognosApiConfig(server_url="http://x", api_key="mykey")
        headers = client._auth_headers()
        assert headers["IBM-BA-Authorization"] == "mykey"


# ===================================================================
# Full connector
# ===================================================================


class TestFullCognosConnector:
    def test_info_not_stub(self):
        c = _make_connector_with_mock()
        info = c.info()
        assert not info.is_stub
        assert info.version == "1.0.0"
        assert "cognos" in info.platform.value

    @pytest.mark.asyncio
    async def test_discover(self):
        c = _make_connector_with_mock()
        assets = await c.discover()
        assert len(assets) == 4  # 2 reports + 1 dashboard + 1 package

    @pytest.mark.asyncio
    async def test_extract_enriches_reports(self):
        c = _make_connector_with_mock()
        await c.discover()
        result = await c.extract_metadata()
        report_assets = [a for a in result.assets if a.asset_type == "report"]
        assert any("parsed_spec" in a.metadata for a in report_assets)

    @pytest.mark.asyncio
    async def test_extract_with_ids(self):
        c = _make_connector_with_mock()
        await c.discover()
        result = await c.extract_metadata(asset_ids=["r1"])
        assert result.count == 1

    @pytest.mark.asyncio
    async def test_disconnect(self):
        c = _make_connector_with_mock()
        await c.disconnect()
        assert not c._connected


# ===================================================================
# Rule catalogs and mappings
# ===================================================================


class TestCognosRuleCatalogs:
    def test_dax_rules_count(self):
        assert len(COGNOS_TO_DAX_RULES) >= 50

    def test_rules_have_fields(self):
        for rule in COGNOS_TO_DAX_RULES:
            assert rule.cognos_function
            assert rule.dax_equivalent
            assert rule.difficulty in ("direct", "parametric", "complex", "unsupported")

    def test_fabric_source_mapping(self):
        assert COGNOS_TO_FABRIC_SOURCE["oracle"] == "OracleDatabase"
        assert COGNOS_TO_FABRIC_SOURCE["sqlserver"] == "Sql"

    def test_fabric_type_mapping(self):
        assert COGNOS_TO_FABRIC_TYPE["numeric"] == "double"
        assert COGNOS_TO_FABRIC_TYPE["string"] == "string"

    def test_visual_mapping(self):
        assert COGNOS_VISUAL_TO_PBI["list"] == "table"
        assert COGNOS_VISUAL_TO_PBI["crosstab"] == "matrix"
        assert len(COGNOS_VISUAL_TO_PBI) >= 14

    def test_prompt_mapping(self):
        assert COGNOS_PROMPT_TO_PBI["select"] == "slicer"
        assert COGNOS_PROMPT_TO_PBI["date"] == "dateRangeSlicer"

    def test_tmdl_mapping(self):
        assert COGNOS_TO_TMDL_MAPPING["Package"] == "Semantic Model"
        assert COGNOS_TO_TMDL_MAPPING["Report"] == "Report (.pbir)"
        assert len(COGNOS_TO_TMDL_MAPPING) >= 20


# ===================================================================
# Registration
# ===================================================================


class TestCognosRegistration:
    def test_registry_contains_cognos(self):
        from src.connectors.base_connector import build_default_registry
        reg = build_default_registry()
        assert reg.is_registered("cognos")

    def test_connector_is_not_stub(self):
        from src.connectors.base_connector import build_default_registry
        reg = build_default_registry()
        connector = reg.create("cognos")
        assert connector is not None
        assert not connector.info().is_stub


# ===================================================================
# Cognos semantic bridge
# ===================================================================


class TestCognosSemanticBridge:
    def _sample_spec(self) -> ParsedReportSpec:
        parser = CognosReportSpecParser()
        return parser.parse_xml(SAMPLE_REPORT_XML)

    def test_basic_conversion(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert isinstance(result, CognosConversionResult)
        assert result.table_count >= 1

    def test_model_name_from_report(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert result.ir.model_name == "SalesReport"

    def test_model_name_override(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec(), model_name="Custom")
        assert result.ir.model_name == "Custom"

    def test_query_becomes_table(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        names = [t.name for t in result.ir.tables]
        assert "SalesQuery" in names

    def test_data_items_become_columns(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        table = result.ir.table_by_name("SalesQuery")
        col_names = [c.name for c in table.columns]
        assert "Revenue" in col_names
        assert "Region" in col_names

    def test_prompts_become_slicers(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert len(result.slicers) == 2
        names = [s.name for s in result.slicers]
        assert "RegionPrompt" in names

    def test_filters_become_rls(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert len(result.rls_roles) == 1
        assert "USA" in result.rls_roles[0].filter_expression

    def test_calc_translations_tracked(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert len(result.calc_translations) >= 1  # at least Revenue expression

    def test_subject_area(self):
        converter = CognosToSemanticModelConverter()
        result = converter.convert(self._sample_spec())
        assert len(result.ir.subject_areas) == 1
