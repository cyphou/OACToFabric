"""Phase 40 — Tableau Connector.

Tests cover:
1. TWB/TWBX XML parser — datasources, worksheets, dashboards, calc fields, parameters
2. Calculated-field → DAX translator — all rule categories, batch translation
3. Data-source mapper — connection-type and data-type mapping
4. Tableau REST client — connect, list, download, disconnect
5. Full TableauConnector — info, lifecycle, discover, extract_metadata
6. Error handling — malformed XML, bad zip, missing .twb, disconnected calls
"""

from __future__ import annotations

import io
import zipfile
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from src.connectors.tableau_connector import (
    CalcField,
    CalcTranslationResult,
    FullTableauConnector,
    ParsedWorkbook,
    TableauApiConfig,
    TableauCalcTranslator,
    TableauDashboard,
    TableauDataSource,
    TableauRestClient,
    TableauSiteInfo,
    TableauWorkbookParser,
    TableauWorksheet,
    map_connection_type,
    map_data_type,
    TABLEAU_TO_FABRIC_SOURCE,
    TABLEAU_TO_FABRIC_TYPE,
)
from src.connectors.base_connector import (
    ConnectorInfo,
    ExtractedAsset,
    ExtractionResult,
    SourcePlatform,
    TableauConnector,
    build_default_registry,
)


# ===================================================================
# Sample TWB XML for testing
# ===================================================================


SAMPLE_TWB_XML = """\
<?xml version="1.0" encoding="utf-8"?>
<workbook version="2023.1">
  <datasources>
    <datasource name="sqlserver.demo" caption="Sales Data">
      <connection class="sqlserver" server="db.example.com"
                  dbname="SalesDB" schema="dbo">
        <relation table="[Orders]" name="Orders" type="table" />
        <relation table="[Customers]" name="Customers" type="table" />
      </connection>
      <column name="[Revenue]" caption="Total Revenue" datatype="real" role="measure">
        <calculation formula="SUM([Sales Amount])" />
      </column>
      <column name="[Profit Margin]" caption="Profit Margin" datatype="real" role="measure">
        <calculation formula="SUM([Profit]) / SUM([Sales Amount])" />
      </column>
      <column name="[Customer Name]" caption="" datatype="string" role="dimension" />
      <column name="[Order Date]" caption="" datatype="date" role="dimension" />
    </datasource>
    <datasource name="Parameters">
      <column name="[Date Range]" caption="Date Range" datatype="date" role="dimension">
        <calculation formula="TODAY()" />
      </column>
    </datasource>
  </datasources>
  <worksheets>
    <worksheet name="Sales Overview">
      <table>
        <datasource-dependencies datasource="sqlserver.demo">
          <column name="[Revenue]" />
          <column name="[Customer Name]" />
        </datasource-dependencies>
      </table>
      <mark class="bar" />
      <filter column="[Order Date]" />
    </worksheet>
    <worksheet name="Trend Analysis">
      <table>
        <datasource-dependencies datasource="sqlserver.demo">
          <column name="[Revenue]" />
          <column name="[Order Date]" />
        </datasource-dependencies>
      </table>
      <mark class="line" />
    </worksheet>
  </worksheets>
  <dashboards>
    <dashboard name="Executive Dashboard">
      <size maxwidth="1200" maxheight="800" />
      <zones>
        <zone name="Sales Overview" type="viz" />
        <zone name="Trend Analysis" type="viz" />
        <zone name="Title" type="layout-basic" />
      </zones>
    </dashboard>
  </dashboards>
</workbook>
"""


def _make_twbx(twb_xml: str = SAMPLE_TWB_XML, twb_name: str = "workbook.twb") -> bytes:
    """Create a .twbx (zip) from TWB XML for testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(twb_name, twb_xml)
    return buf.getvalue()


# ===================================================================
# TableauWorkbookParser — TWB
# ===================================================================


class TestTableauWorkbookParserTWB:
    """Tests for parsing .twb XML files."""

    def setup_method(self):
        self.parser = TableauWorkbookParser()

    def test_parse_workbook_version(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML, filename="demo.twb")
        assert result.workbook_version == "2023.1"
        assert result.filename == "demo.twb"
        assert result.is_valid

    def test_parse_datasources(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        # 2 datasources: sqlserver.demo + Parameters
        assert len(result.datasources) == 2
        ds = result.datasources[0]
        assert ds.name == "sqlserver.demo"
        assert ds.caption == "Sales Data"

    def test_parse_connection_info(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        ds = result.datasources[0]
        assert ds.connection_type == "sqlserver"
        assert ds.server == "db.example.com"
        assert ds.database == "SalesDB"
        assert ds.schema == "dbo"

    def test_parse_tables(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        ds = result.datasources[0]
        assert "[Orders]" in ds.tables
        assert "[Customers]" in ds.tables

    def test_parse_columns(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        ds = result.datasources[0]
        col_names = [c["name"] for c in ds.columns]
        assert "[Customer Name]" in col_names
        assert "[Order Date]" in col_names

    def test_parse_calc_fields(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        ds = result.datasources[0]
        assert len(ds.calc_fields) == 2
        names = {f.name for f in ds.calc_fields}
        assert "[Revenue]" in names
        assert "[Profit Margin]" in names

    def test_calc_field_formula(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        revenue = [f for f in result.datasources[0].calc_fields if f.name == "[Revenue]"][0]
        assert revenue.formula == "SUM([Sales Amount])"
        assert revenue.datatype == "real"
        assert revenue.role == "measure"

    def test_parse_parameters(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        assert len(result.parameters) == 1
        assert result.parameters[0].name == "[Date Range]"
        assert result.parameters[0].formula == "TODAY()"

    def test_total_calc_fields(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        # 2 calc fields in sqlserver.demo + 1 in Parameters datasource + 1 parameter (same ref)
        assert result.total_calc_fields == 4

    def test_parse_worksheets(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        assert len(result.worksheets) == 2
        ws_names = [ws.name for ws in result.worksheets]
        assert "Sales Overview" in ws_names
        assert "Trend Analysis" in ws_names

    def test_worksheet_datasource_ref(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        sales_ws = [ws for ws in result.worksheets if ws.name == "Sales Overview"][0]
        assert sales_ws.datasource_ref == "sqlserver.demo"

    def test_worksheet_columns_used(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        sales_ws = [ws for ws in result.worksheets if ws.name == "Sales Overview"][0]
        assert len(sales_ws.columns_used) >= 2

    def test_worksheet_mark_type(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        sales_ws = [ws for ws in result.worksheets if ws.name == "Sales Overview"][0]
        assert sales_ws.mark_type == "bar"
        trend_ws = [ws for ws in result.worksheets if ws.name == "Trend Analysis"][0]
        assert trend_ws.mark_type == "line"

    def test_worksheet_filters(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        sales_ws = [ws for ws in result.worksheets if ws.name == "Sales Overview"][0]
        assert "[Order Date]" in sales_ws.filters

    def test_parse_dashboards(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        assert len(result.dashboards) == 1
        db = result.dashboards[0]
        assert db.name == "Executive Dashboard"

    def test_dashboard_size(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        db = result.dashboards[0]
        assert db.size_width == 1200
        assert db.size_height == 800

    def test_dashboard_worksheets(self):
        result = self.parser.parse_twb(SAMPLE_TWB_XML)
        db = result.dashboards[0]
        # layout-basic zones should be excluded
        assert "Sales Overview" in db.worksheets
        assert "Trend Analysis" in db.worksheets
        assert "Title" not in db.worksheets

    def test_invalid_xml(self):
        result = self.parser.parse_twb("<not valid xml!!!><<>")
        assert not result.is_valid
        assert any("XML parse error" in e for e in result.errors)

    def test_empty_workbook(self):
        result = self.parser.parse_twb('<workbook version="1.0"></workbook>')
        assert result.is_valid
        assert result.workbook_version == "1.0"
        assert len(result.datasources) == 0
        assert len(result.worksheets) == 0
        assert len(result.dashboards) == 0


# ===================================================================
# TableauWorkbookParser — TWBX
# ===================================================================


class TestTableauWorkbookParserTWBX:
    """Tests for parsing .twbx zip files."""

    def setup_method(self):
        self.parser = TableauWorkbookParser()

    def test_parse_twbx(self):
        data = _make_twbx()
        result = self.parser.parse_twbx(data, filename="demo.twbx")
        assert result.is_valid
        assert result.filename == "demo.twbx"
        assert len(result.datasources) == 2

    def test_twbx_no_twb_inside(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "not a twb")
        result = self.parser.parse_twbx(buf.getvalue())
        assert not result.is_valid
        assert any("No .twb" in e for e in result.errors)

    def test_twbx_invalid_zip(self):
        result = self.parser.parse_twbx(b"this is not a zip file")
        assert not result.is_valid
        assert any("not a valid zip" in e for e in result.errors)


# ===================================================================
# TableauCalcTranslator
# ===================================================================


class TestTableauCalcTranslator:
    """Tests for Tableau → DAX formula translation."""

    def setup_method(self):
        self.translator = TableauCalcTranslator()

    def test_rule_count(self):
        """Translator should have a large set of built-in rules."""
        assert self.translator.rule_count >= 50

    # --- Direct mappings ---

    @pytest.mark.parametrize("tab_func,dax_func", [
        ("SUM([Sales])", "SUM([Sales])"),
        ("MIN([Price])", "MIN([Price])"),
        ("MAX([Qty])", "MAX([Qty])"),
        ("COUNT([Orders])", "COUNT([Orders])"),
        ("UPPER([Name])", "UPPER([Name])"),
        ("LOWER([Name])", "LOWER([Name])"),
        ("LEN([Code])", "LEN([Code])"),
        ("LEFT([S], 3)", "LEFT([S], 3)"),
        ("RIGHT([S], 3)", "RIGHT([S], 3)"),
        ("MID([S], 1, 3)", "MID([S], 1, 3)"),
        ("TRIM([S])", "TRIM([S])"),
        ("ABS([X])", "ABS([X])"),
        ("ROUND([X], 2)", "ROUND([X], 2)"),
        ("POWER([X], 2)", "POWER([X], 2)"),
        ("SQRT([X])", "SQRT([X])"),
        ("LOG([X])", "LOG([X])"),
        ("EXP([X])", "EXP([X])"),
        ("YEAR([D])", "YEAR([D])"),
        ("MONTH([D])", "MONTH([D])"),
        ("DAY([D])", "DAY([D])"),
        ("TODAY()", "TODAY()"),
        ("NOW()", "NOW()"),
        ("INT([X])", "INT([X])"),
    ])
    def test_direct_mapping(self, tab_func, dax_func):
        calc = CalcField(name="test", formula=tab_func)
        result = self.translator.translate(calc)
        assert result.dax_expression == dax_func
        assert result.confidence == 1.0

    # --- Renamed mappings ---

    @pytest.mark.parametrize("tab_func,expected_substring", [
        ("AVG([Sales])", "AVERAGE("),
        ("COUNTD([Customers])", "DISTINCTCOUNT("),
        ("CONTAINS([S], 'x')", "CONTAINSSTRING("),
        ("ISNULL([X])", "ISBLANK("),
        ("IIF([X]>0, 'Y', 'N')", "IF("),
    ])
    def test_renamed_mapping(self, tab_func, expected_substring):
        calc = CalcField(name="test", formula=tab_func)
        result = self.translator.translate(calc)
        assert expected_substring in result.dax_expression

    # --- Unsupported mappings (LOD, window) ---

    @pytest.mark.parametrize("tab_func", [
        "{FIXED [Region] : SUM([Sales])}",
        "{INCLUDE [Category] : AVG([Price])}",
        "{EXCLUDE [Date] : COUNT([Orders])}",
        "RUNNING_SUM(SUM([Sales]))",
        "RUNNING_AVG(AVG([X]))",
        "INDEX()",
        "FIRST()",
        "LAST()",
        "SIZE()",
        "LOOKUP(SUM([X]), -1)",
    ])
    def test_unsupported_flagged(self, tab_func):
        calc = CalcField(name="test", formula=tab_func)
        result = self.translator.translate(calc)
        assert result.confidence <= 0.2
        assert result.method == "unsupported"
        assert len(result.warnings) > 0

    # --- Complex mappings ---

    def test_complex_rank(self):
        calc = CalcField(name="test", formula="RANK(SUM([Sales]))")
        result = self.translator.translate(calc)
        assert "RANKX(" in result.dax_expression
        assert result.confidence <= 0.5

    def test_complex_datepart(self):
        calc = CalcField(name="test", formula="DATEPART('month', [Date])")
        result = self.translator.translate(calc)
        assert result.confidence <= 0.5

    # --- Batch ---

    def test_translate_batch(self):
        calcs = [
            CalcField(name="c1", formula="SUM([A])"),
            CalcField(name="c2", formula="AVG([B])"),
            CalcField(name="c3", formula="{FIXED [X] : SUM([Y])}"),
        ]
        results = self.translator.translate_batch(calcs)
        assert len(results) == 3
        assert results[0].confidence == 1.0
        assert results[2].method == "unsupported"

    # --- Result fields ---

    def test_result_fields(self):
        calc = CalcField(name="Revenue", formula="SUM([Sales])")
        result = self.translator.translate(calc)
        assert result.source_name == "Revenue"
        assert result.source_formula == "SUM([Sales])"


# ===================================================================
# Data-source mapper
# ===================================================================


class TestDataSourceMapper:
    """Tests for Tableau → Fabric data-source and type mapping."""

    @pytest.mark.parametrize("tab_type,expected", [
        ("sqlserver", "Fabric SQL Endpoint"),
        ("postgres", "Fabric SQL Endpoint"),
        ("oracle", "Fabric SQL Endpoint"),
        ("bigquery", "Fabric Lakehouse (Delta)"),
        ("snowflake", "Fabric Lakehouse (Delta)"),
        ("excel-direct", "Fabric Lakehouse (file import)"),
        ("textscan", "Fabric Lakehouse (file import)"),
        ("hyper", "Fabric Lakehouse (Delta)"),
    ])
    def test_connection_type_mapping(self, tab_type, expected):
        assert map_connection_type(tab_type) == expected

    def test_unknown_connection_type(self):
        assert map_connection_type("teradata") == "Fabric SQL Endpoint"

    @pytest.mark.parametrize("tab_type,expected", [
        ("integer", "Int64"),
        ("real", "Double"),
        ("string", "String"),
        ("boolean", "Boolean"),
        ("date", "DateTime"),
        ("datetime", "DateTime"),
    ])
    def test_data_type_mapping(self, tab_type, expected):
        assert map_data_type(tab_type) == expected

    def test_unknown_data_type(self):
        assert map_data_type("blob") == "String"

    def test_all_connection_types_have_values(self):
        for k, v in TABLEAU_TO_FABRIC_SOURCE.items():
            assert isinstance(v, str) and len(v) > 0

    def test_all_data_types_have_values(self):
        for k, v in TABLEAU_TO_FABRIC_TYPE.items():
            assert isinstance(v, str) and len(v) > 0


# ===================================================================
# TableauRestClient
# ===================================================================


class TestTableauRestClient:
    """Tests for the REST API client (mocked HTTP)."""

    @pytest.fixture
    def client(self):
        return TableauRestClient()

    @pytest.fixture
    def config(self):
        return TableauApiConfig(
            server_url="https://tableau.example.com",
            site_name="MySite",
            token_name="my-pat",
            token_value="secret-token",
        )

    @pytest.mark.asyncio
    async def test_connect_pat_auth(self, client, config):
        """Connect with Personal Access Token."""
        async def mock_post(url, json):
            return {
                "credentials": {
                    "token": "session-abc",
                    "site": {"id": "site-123", "contentUrl": "MySite"},
                }
            }
        client._http_post = mock_post

        site = await client.connect(config)
        assert isinstance(site, TableauSiteInfo)
        assert site.site_id == "site-123"
        assert client.is_connected

    @pytest.mark.asyncio
    async def test_connect_username_password(self, client):
        """Connect with username/password."""
        config = TableauApiConfig(
            server_url="https://tableau.example.com",
            site_name="MySite",
            username="admin",
            password="pass123",
        )
        async def mock_post(url, json):
            assert "name" in json or "personalAccessTokenName" not in json
            return {
                "credentials": {
                    "token": "sess-xyz",
                    "site": {"id": "site-456", "contentUrl": "MySite"},
                }
            }
        client._http_post = mock_post

        site = await client.connect(config)
        assert site.site_id == "site-456"

    @pytest.mark.asyncio
    async def test_list_workbooks(self, client, config):
        """List workbooks after connecting."""
        async def mock_post(url, json):
            return {"credentials": {"token": "t", "site": {"id": "s1", "contentUrl": ""}}}
        client._http_post = mock_post
        await client.connect(config)

        async def mock_get(url, params=None):
            return {
                "workbooks": {
                    "workbook": [
                        {"id": "wb1", "name": "Sales Dashboard", "contentUrl": "sales"},
                    ]
                }
            }
        client._http_get = mock_get

        result = await client.list_workbooks()
        wb_list = result["workbooks"]["workbook"]
        assert len(wb_list) == 1
        assert wb_list[0]["name"] == "Sales Dashboard"

    @pytest.mark.asyncio
    async def test_list_datasources(self, client, config):
        async def mock_post(url, json):
            return {"credentials": {"token": "t", "site": {"id": "s1", "contentUrl": ""}}}
        client._http_post = mock_post
        await client.connect(config)

        async def mock_get(url, params=None):
            return {"datasources": {"datasource": [{"id": "ds1", "name": "SalesDB"}]}}
        client._http_get = mock_get

        result = await client.list_datasources()
        assert len(result["datasources"]["datasource"]) == 1

    @pytest.mark.asyncio
    async def test_list_views(self, client, config):
        async def mock_post(url, json):
            return {"credentials": {"token": "t", "site": {"id": "s1", "contentUrl": ""}}}
        client._http_post = mock_post
        await client.connect(config)

        async def mock_get(url, params=None):
            return {"views": {"view": [{"id": "v1", "name": "Sheet1"}]}}
        client._http_get = mock_get

        result = await client.list_views()
        assert len(result["views"]["view"]) == 1

    @pytest.mark.asyncio
    async def test_download_workbook(self, client, config):
        async def mock_post(url, json):
            return {"credentials": {"token": "t", "site": {"id": "s1", "contentUrl": ""}}}
        client._http_post = mock_post
        await client.connect(config)

        twbx_data = _make_twbx()
        async def mock_get_bytes(url):
            return twbx_data
        client._http_get_bytes = mock_get_bytes

        result = await client.download_workbook("wb1")
        assert isinstance(result, bytes)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_disconnect(self, client, config):
        async def mock_post(url, json):
            return {"credentials": {"token": "t", "site": {"id": "s1", "contentUrl": ""}}}
        client._http_post = mock_post
        await client.connect(config)
        assert client.is_connected

        await client.disconnect()
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_require_connected(self, client):
        """Calling list_workbooks before connect should raise."""
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.list_workbooks()

    def test_api_config_base_url(self):
        config = TableauApiConfig(
            server_url="https://tableau.example.com/",
            api_version="3.21",
        )
        assert config.base_url == "https://tableau.example.com/api/3.21"

    def test_api_config_no_trailing_slash(self):
        config = TableauApiConfig(
            server_url="https://tableau.example.com",
            api_version="3.21",
        )
        assert config.base_url == "https://tableau.example.com/api/3.21"


# ===================================================================
# FullTableauConnector
# ===================================================================


class TestFullTableauConnector:
    """Tests for the full SourceConnector implementation."""

    def test_info_not_stub(self):
        c = FullTableauConnector()
        info = c.info()
        assert info.is_stub is False
        assert info.platform == SourcePlatform.TABLEAU
        assert info.version == "1.0.0"
        assert "calculated_field" in info.supported_asset_types

    def test_info_has_all_asset_types(self):
        c = FullTableauConnector()
        info = c.info()
        for t in ["workbook", "datasource", "dashboard", "view", "calculated_field"]:
            assert t in info.supported_asset_types

    @pytest.mark.asyncio
    async def test_connect_success(self):
        c = FullTableauConnector()
        async def mock_connect(cfg):
            return TableauSiteInfo(site_id="s1", site_name="test", content_url="test")
        c._client.connect = mock_connect

        result = await c.connect({
            "server_url": "https://tab.example.com",
            "site_name": "test",
            "token_name": "pat",
            "token_value": "secret",
        })
        assert result is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        c = FullTableauConnector()
        async def mock_connect(cfg):
            raise ConnectionError("refused")
        c._client.connect = mock_connect

        result = await c.connect({"server_url": "bad"})
        assert result is False

    @pytest.mark.asyncio
    async def test_discover_not_connected_raises(self):
        c = FullTableauConnector()
        with pytest.raises(RuntimeError, match="Not connected"):
            await c.discover()

    @pytest.mark.asyncio
    async def test_discover_workbooks(self):
        c = FullTableauConnector()
        c._connected = True

        async def mock_wb(page_size=100, page=1):
            return {"workbooks": {"workbook": [
                {"id": "wb1", "name": "Sales", "contentUrl": "sales",
                 "project": {"name": "P1"}, "owner": {"name": "admin"},
                 "createdAt": "2024-01-01", "updatedAt": "2024-06-01"},
            ]}}
        async def mock_ds(page_size=100, page=1):
            return {"datasources": {"datasource": []}}
        async def mock_views(page_size=100, page=1):
            return {"views": {"view": []}}

        c._client.list_workbooks = mock_wb
        c._client.list_datasources = mock_ds
        c._client.list_views = mock_views

        assets = await c.discover()
        assert len(assets) == 1
        assert assets[0].asset_type == "workbook"
        assert assets[0].name == "Sales"
        assert assets[0].platform == "tableau"
        assert assets[0].metadata["project"] == "P1"

    @pytest.mark.asyncio
    async def test_discover_all_types(self):
        c = FullTableauConnector()
        c._connected = True

        async def mock_wb(page_size=100, page=1):
            return {"workbooks": {"workbook": [{"id": "wb1", "name": "WB", "contentUrl": ""}]}}
        async def mock_ds(page_size=100, page=1):
            return {"datasources": {"datasource": [
                {"id": "ds1", "name": "DS", "contentUrl": "", "type": "sqlserver",
                 "project": {"name": "P"}, "owner": {"name": "o"}},
            ]}}
        async def mock_views(page_size=100, page=1):
            return {"views": {"view": [
                {"id": "v1", "name": "V", "contentUrl": "", "workbook": {"id": "wb1"}},
            ]}}

        c._client.list_workbooks = mock_wb
        c._client.list_datasources = mock_ds
        c._client.list_views = mock_views

        assets = await c.discover()
        types = {a.asset_type for a in assets}
        assert types == {"workbook", "datasource", "view"}
        assert len(assets) == 3

    @pytest.mark.asyncio
    async def test_view_dependency_on_workbook(self):
        c = FullTableauConnector()
        c._connected = True

        async def mock_wb(page_size=100, page=1):
            return {"workbooks": {"workbook": []}}
        async def mock_ds(page_size=100, page=1):
            return {"datasources": {"datasource": []}}
        async def mock_views(page_size=100, page=1):
            return {"views": {"view": [
                {"id": "v1", "name": "V", "contentUrl": "", "workbook": {"id": "wb99"}},
            ]}}

        c._client.list_workbooks = mock_wb
        c._client.list_datasources = mock_ds
        c._client.list_views = mock_views

        assets = await c.discover()
        view = assets[0]
        assert "wb99" in view.dependencies

    @pytest.mark.asyncio
    async def test_extract_metadata_parses_twbx(self):
        """Full extract_metadata should download, parse, and translate."""
        c = FullTableauConnector()
        c._connected = True
        c._discovered = [
            ExtractedAsset(
                asset_id="wb1", asset_type="workbook", name="Sales",
                source_path="sales", platform="tableau", metadata={},
            ),
        ]

        twbx_data = _make_twbx()
        async def mock_download(workbook_id):
            return twbx_data
        c._client.download_workbook = mock_download

        result = await c.extract_metadata()
        assert isinstance(result, ExtractionResult)
        assert result.platform == "tableau"
        assert result.count == 1
        asset = result.assets[0]
        assert "worksheets" in asset.metadata
        assert "Sales Overview" in asset.metadata["worksheets"]
        assert "dashboards" in asset.metadata
        assert "Executive Dashboard" in asset.metadata["dashboards"]
        assert asset.metadata["calc_field_count"] == 4
        assert "translations" in asset.metadata
        assert asset.metadata["connection_type"] == "sqlserver"
        assert asset.metadata["fabric_target"] == "Fabric SQL Endpoint"

    @pytest.mark.asyncio
    async def test_extract_metadata_filter_by_id(self):
        c = FullTableauConnector()
        c._connected = True
        c._discovered = [
            ExtractedAsset("wb1", "workbook", "W1", "/", "tableau", metadata={}),
            ExtractedAsset("ds1", "datasource", "D1", "/", "tableau", metadata={}),
        ]

        twbx_data = _make_twbx()
        async def mock_download(workbook_id):
            return twbx_data
        c._client.download_workbook = mock_download

        result = await c.extract_metadata(asset_ids=["ds1"])
        # Only datasource should be returned (no download since it's not a workbook)
        assert result.count == 1
        assert result.assets[0].asset_id == "ds1"

    @pytest.mark.asyncio
    async def test_extract_metadata_handles_download_error(self):
        c = FullTableauConnector()
        c._connected = True
        c._discovered = [
            ExtractedAsset("wb1", "workbook", "Bad", "/", "tableau", metadata={}),
        ]

        async def mock_download(workbook_id):
            raise ConnectionError("timeout")
        c._client.download_workbook = mock_download

        result = await c.extract_metadata()
        assert len(result.errors) > 0
        assert "Failed to parse workbook" in result.errors[0]

    @pytest.mark.asyncio
    async def test_disconnect(self):
        c = FullTableauConnector()
        c._connected = True

        disconnected = []
        async def mock_disconnect():
            disconnected.append(True)
        c._client.disconnect = mock_disconnect

        await c.disconnect()
        assert not c._connected
        assert len(disconnected) == 1


# ===================================================================
# Integration with base_connector registry
# ===================================================================


class TestRegistryIntegration:
    """Verify the full Tableau connector integrates with the registry."""

    def test_registry_creates_full_connector(self):
        registry = build_default_registry()
        connector = registry.create("tableau")
        assert connector is not None
        info = connector.info()
        assert info.is_stub is False
        assert info.version == "1.0.0"

    def test_tableau_import_from_base(self):
        """TableauConnector imported from base_connector is the full impl."""
        c = TableauConnector()
        assert c.info().is_stub is False

    def test_all_registry_platforms_still_work(self):
        registry = build_default_registry()
        for platform in ["oac", "obiee", "tableau", "cognos", "qlik"]:
            connector = registry.create(platform)
            assert connector is not None
            info = connector.info()
            assert info.platform.value == platform


# ===================================================================
# Data classes
# ===================================================================


class TestDataClasses:
    """Tests for data classes used by the connector."""

    def test_calc_field_defaults(self):
        cf = CalcField(name="test", formula="SUM([X])")
        assert cf.datatype == "string"
        assert cf.role == "measure"
        assert cf.caption == ""

    def test_calc_translation_result_defaults(self):
        r = CalcTranslationResult(source_name="x", source_formula="y", dax_expression="z")
        assert r.method == "rules"
        assert r.confidence == 1.0
        assert r.warnings == []

    def test_tableau_datasource_defaults(self):
        ds = TableauDataSource(name="ds1")
        assert ds.tables == []
        assert ds.columns == []
        assert ds.calc_fields == []
        assert ds.connection_type == ""

    def test_tableau_worksheet_defaults(self):
        ws = TableauWorksheet(name="ws1")
        assert ws.datasource_ref == ""
        assert ws.columns_used == []
        assert ws.filters == []
        assert ws.mark_type == ""

    def test_tableau_dashboard_defaults(self):
        db = TableauDashboard(name="db1")
        assert db.worksheets == []
        assert db.size_width == 0

    def test_parsed_workbook_defaults(self):
        pw = ParsedWorkbook()
        assert pw.is_valid
        assert pw.total_calc_fields == 0
        assert pw.filename == ""

    def test_tableau_site_info(self):
        si = TableauSiteInfo(site_id="s1", site_name="Main", content_url="main")
        assert si.site_id == "s1"

    def test_tableau_api_config_defaults(self):
        cfg = TableauApiConfig()
        assert cfg.server_url == ""
        assert cfg.api_version == "3.21"
