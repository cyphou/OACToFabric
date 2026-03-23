"""Tableau connector — TWB/TWBX parsing + REST API client.

Provides full support for migrating Tableau content to Microsoft
Fabric & Power BI:

- ``TableauWorkbookParser`` — parse .twb XML and .twbx zip archives
- ``TableauCalcTranslator`` — translate Tableau calculated fields → DAX
- ``TableauRestClient`` — async wrapper around Tableau REST API
- ``TableauConnector`` — SourceConnector implementation
"""

from __future__ import annotations

import io
import logging
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from xml.etree import ElementTree as ET

from src.connectors.base_connector import (
    ConnectorInfo,
    ExtractedAsset,
    ExtractionResult,
    SourceConnector,
    SourcePlatform,
)

logger = logging.getLogger(__name__)


# =====================================================================
# Tableau Calculated-Field → DAX translation
# =====================================================================


@dataclass
class CalcField:
    """A Tableau calculated field extracted from a workbook."""

    name: str
    formula: str
    datatype: str = "string"
    role: str = "measure"   # measure | dimension
    caption: str = ""


@dataclass
class CalcTranslationResult:
    """Result of translating one calculated field."""

    source_name: str
    source_formula: str
    dax_expression: str
    method: str = "rules"   # rules | unsupported
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


# Rule-based Tableau → DAX function mapping
_TABLEAU_TO_DAX: list[tuple[str, str, str]] = [
    # (pattern, replacement, notes)
    # Aggregates
    (r"\bSUM\s*\(", "SUM(", "direct"),
    (r"\bAVG\s*\(", "AVERAGE(", "rename"),
    (r"\bMIN\s*\(", "MIN(", "direct"),
    (r"\bMAX\s*\(", "MAX(", "direct"),
    (r"\bCOUNT\s*\(", "COUNT(", "direct"),
    (r"\bCOUNTD\s*\(", "DISTINCTCOUNT(", "rename"),
    (r"\bMEDIAN\s*\(", "MEDIAN(", "direct"),
    (r"\bATTR\s*\(", "SELECTEDVALUE(", "approx"),
    # String
    (r"\bUPPER\s*\(", "UPPER(", "direct"),
    (r"\bLOWER\s*\(", "LOWER(", "direct"),
    (r"\bLEN\s*\(", "LEN(", "direct"),
    (r"\bLEFT\s*\(", "LEFT(", "direct"),
    (r"\bRIGHT\s*\(", "RIGHT(", "direct"),
    (r"\bMID\s*\(", "MID(", "direct"),
    (r"\bTRIM\s*\(", "TRIM(", "direct"),
    (r"\bREPLACE\s*\(", "SUBSTITUTE(", "rename"),
    (r"\bCONTAINS\s*\(", "CONTAINSSTRING(", "rename"),
    (r"\bSTARTSWITH\s*\(", "-- STARTSWITH unsupported", "unsupported"),
    (r"\bENDSWITH\s*\(", "-- ENDSWITH unsupported", "unsupported"),
    (r"\bSPLIT\s*\(", "-- SPLIT unsupported", "unsupported"),
    # Date
    (r"\bYEAR\s*\(", "YEAR(", "direct"),
    (r"\bMONTH\s*\(", "MONTH(", "direct"),
    (r"\bDAY\s*\(", "DAY(", "direct"),
    (r"\bDATEPART\s*\(", "-- DATEPART (manual)", "complex"),
    (r"\bDATEDIFF\s*\(", "DATEDIFF(", "direct"),
    (r"\bDATEADD\s*\(", "DATEADD(", "direct"),
    (r"\bDATENAME\s*\(", "FORMAT(", "rename"),
    (r"\bDATETRUNC\s*\(", "-- DATETRUNC (manual)", "complex"),
    (r"\bTODAY\s*\(\s*\)", "TODAY()", "direct"),
    (r"\bNOW\s*\(\s*\)", "NOW()", "direct"),
    # Logical
    (r"\bIF\s+", "IF(", "restructure"),
    (r"\bIFNULL\s*\(", "IF(ISBLANK(", "restructure"),
    (r"\bISNULL\s*\(", "ISBLANK(", "rename"),
    (r"\bZN\s*\(", "IF(ISBLANK(", "restructure"),
    (r"\bIIF\s*\(", "IF(", "rename"),
    # Math
    (r"\bABS\s*\(", "ABS(", "direct"),
    (r"\bROUND\s*\(", "ROUND(", "direct"),
    (r"\bCEILING\s*\(", "CEILING(", "direct"),
    (r"\bFLOOR\s*\(", "FLOOR(", "direct"),
    (r"\bPOWER\s*\(", "POWER(", "direct"),
    (r"\bSQRT\s*\(", "SQRT(", "direct"),
    (r"\bLOG\s*\(", "LOG(", "direct"),
    (r"\bEXP\s*\(", "EXP(", "direct"),
    # Type conversion
    (r"\bINT\s*\(", "INT(", "direct"),
    (r"\bFLOAT\s*\(", "CONVERT(", "rename"),
    (r"\bSTR\s*\(", "FORMAT(", "rename"),
    # Table calcs — translated as comments (need manual work)
    (r"\bRUNNING_SUM\s*\(", "-- RUNNING_SUM (window function, manual)", "unsupported"),
    (r"\bRUNNING_AVG\s*\(", "-- RUNNING_AVG (window function, manual)", "unsupported"),
    (r"\bINDEX\s*\(\s*\)", "-- INDEX() (window function, manual)", "unsupported"),
    (r"\bFIRST\s*\(\s*\)", "-- FIRST() (window function, manual)", "unsupported"),
    (r"\bLAST\s*\(\s*\)", "-- LAST() (window function, manual)", "unsupported"),
    (r"\bSIZE\s*\(\s*\)", "-- SIZE() (window function, manual)", "unsupported"),
    (r"\bLOOKUP\s*\(", "-- LOOKUP (window function, manual)", "unsupported"),
    (r"\bRANK\s*\(", "RANKX(", "complex"),
    (r"\bRANK_DENSE\s*\(", "RANKX(", "complex"),
    (r"\bRANK_UNIQUE\s*\(", "RANKX(", "complex"),
    # LOD expressions — flag for manual review
    (r"\{FIXED\s+", "-- {FIXED} LOD expression (manual)", "unsupported"),
    (r"\{INCLUDE\s+", "-- {INCLUDE} LOD expression (manual)", "unsupported"),
    (r"\{EXCLUDE\s+", "-- {EXCLUDE} LOD expression (manual)", "unsupported"),
]


class TableauCalcTranslator:
    """Translate Tableau calculated-field formulas to DAX.

    Uses rule-based regex translation for standard functions
    and flags unsupported patterns (LOD, table calcs) for manual review.
    """

    def __init__(self) -> None:
        self._rules = _TABLEAU_TO_DAX

    @property
    def rule_count(self) -> int:
        return len(self._rules)

    def translate(self, calc: CalcField) -> CalcTranslationResult:
        """Translate a single calculated field."""
        formula = calc.formula.strip()
        warnings: list[str] = []
        confidence = 1.0
        dax = formula

        for pattern, replacement, note in self._rules:
            if re.search(pattern, dax, re.IGNORECASE):
                if note == "unsupported":
                    warnings.append(f"Unsupported: {pattern.strip()}")
                    confidence = min(confidence, 0.2)
                elif note == "complex":
                    warnings.append(f"Complex mapping: {pattern.strip()}")
                    confidence = min(confidence, 0.5)
                elif note == "restructure":
                    confidence = min(confidence, 0.7)
                elif note == "approx":
                    confidence = min(confidence, 0.6)
                dax = re.sub(pattern, replacement, dax, flags=re.IGNORECASE)

        method = "rules"
        if any("Unsupported" in w for w in warnings):
            method = "unsupported"

        return CalcTranslationResult(
            source_name=calc.name,
            source_formula=calc.formula,
            dax_expression=dax,
            method=method,
            confidence=confidence,
            warnings=warnings,
        )

    def translate_batch(self, calcs: list[CalcField]) -> list[CalcTranslationResult]:
        """Translate a batch of calculated fields."""
        return [self.translate(c) for c in calcs]


# =====================================================================
# Tableau workbook XML parser
# =====================================================================


@dataclass
class TableauDataSource:
    """A data source extracted from a Tableau workbook."""

    name: str
    caption: str = ""
    connection_type: str = ""
    server: str = ""
    database: str = ""
    schema: str = ""
    tables: list[str] = field(default_factory=list)
    columns: list[dict[str, str]] = field(default_factory=list)
    calc_fields: list[CalcField] = field(default_factory=list)


@dataclass
class TableauWorksheet:
    """A worksheet extracted from a Tableau workbook."""

    name: str
    datasource_ref: str = ""
    columns_used: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)
    mark_type: str = ""  # bar, line, area, etc.


@dataclass
class TableauDashboard:
    """A dashboard extracted from a Tableau workbook."""

    name: str
    worksheets: list[str] = field(default_factory=list)
    size_width: int = 0
    size_height: int = 0


@dataclass
class ParsedWorkbook:
    """Result of parsing a Tableau .twb / .twbx file."""

    filename: str = ""
    workbook_version: str = ""
    datasources: list[TableauDataSource] = field(default_factory=list)
    worksheets: list[TableauWorksheet] = field(default_factory=list)
    dashboards: list[TableauDashboard] = field(default_factory=list)
    parameters: list[CalcField] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_calc_fields(self) -> int:
        return sum(len(ds.calc_fields) for ds in self.datasources) + len(self.parameters)


class TableauWorkbookParser:
    """Parse Tableau .twb (XML) and .twbx (zip) files.

    Extracts datasources, worksheets, dashboards, calculated fields,
    parameters, and connection information.
    """

    def parse_twbx(self, data: bytes, filename: str = "") -> ParsedWorkbook:
        """Parse a .twbx file (zip containing .twb + extracts)."""
        result = ParsedWorkbook(filename=filename)
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                twb_names = [n for n in zf.namelist() if n.endswith(".twb")]
                if not twb_names:
                    result.errors.append("No .twb file found inside .twbx archive")
                    return result
                twb_xml = zf.read(twb_names[0])
                return self.parse_twb(twb_xml, filename=filename)
        except zipfile.BadZipFile:
            result.errors.append("Invalid .twbx file — not a valid zip archive")
            return result

    def parse_twb(self, data: bytes | str, filename: str = "") -> ParsedWorkbook:
        """Parse a .twb XML file."""
        result = ParsedWorkbook(filename=filename)

        try:
            if isinstance(data, bytes):
                root = ET.fromstring(data)
            else:
                root = ET.fromstring(data.encode("utf-8"))
        except ET.ParseError as exc:
            result.errors.append(f"XML parse error: {exc}")
            return result

        # Workbook version
        result.workbook_version = root.get("version", "")

        # Datasources
        for ds_elem in root.iter("datasource"):
            result.datasources.append(self._parse_datasource(ds_elem))

        # Worksheets
        for ws_elem in root.iter("worksheet"):
            result.worksheets.append(self._parse_worksheet(ws_elem))

        # Dashboards
        for db_elem in root.iter("dashboard"):
            result.dashboards.append(self._parse_dashboard(db_elem))

        # Parameters (top-level datasource named "Parameters")
        for ds in result.datasources:
            if ds.name.lower() == "parameters":
                result.parameters = ds.calc_fields
                break

        return result

    def _parse_datasource(self, elem: ET.Element) -> TableauDataSource:
        """Parse a <datasource> element."""
        ds = TableauDataSource(
            name=elem.get("name", ""),
            caption=elem.get("caption", ""),
        )

        # Connection info
        conn = elem.find(".//connection")
        if conn is not None:
            ds.connection_type = conn.get("class", "")
            ds.server = conn.get("server", "")
            ds.database = conn.get("dbname", "")
            ds.schema = conn.get("schema", "")

        # Tables (relations)
        for rel in elem.iter("relation"):
            table_name = rel.get("table", "") or rel.get("name", "")
            if table_name and table_name not in ds.tables:
                ds.tables.append(table_name)

        # Columns
        for col_elem in elem.iter("column"):
            col_name = col_elem.get("name", "")
            col_caption = col_elem.get("caption", "")
            col_datatype = col_elem.get("datatype", "")
            col_role = col_elem.get("role", "")

            if not col_name:
                continue

            # Calculated fields have a <calculation> child
            calc_elem = col_elem.find("calculation")
            if calc_elem is not None:
                formula = calc_elem.get("formula", "")
                if formula:
                    ds.calc_fields.append(CalcField(
                        name=col_name,
                        formula=formula,
                        datatype=col_datatype,
                        role=col_role,
                        caption=col_caption,
                    ))
            else:
                ds.columns.append({
                    "name": col_name,
                    "caption": col_caption,
                    "datatype": col_datatype,
                    "role": col_role,
                })

        return ds

    def _parse_worksheet(self, elem: ET.Element) -> TableauWorksheet:
        """Parse a <worksheet> element."""
        ws = TableauWorksheet(name=elem.get("name", ""))

        # Datasource reference
        ds_dep = elem.find(".//datasource-dependencies")
        if ds_dep is not None:
            ws.datasource_ref = ds_dep.get("datasource", "")

        # Columns used in the view
        for col_ref in elem.iter("datasource-dependencies"):
            ds_name = col_ref.get("datasource", "")
            for col in col_ref.iter("column"):
                col_name = col.get("name", "")
                if col_name:
                    ws.columns_used.append(f"{ds_name}.{col_name}")

        # Filters
        for flt in elem.iter("filter"):
            col = flt.get("column", "")
            if col:
                ws.filters.append(col)

        # Mark type
        mark_elem = elem.find(".//mark")
        if mark_elem is not None:
            ws.mark_type = mark_elem.get("class", "")

        return ws

    def _parse_dashboard(self, elem: ET.Element) -> TableauDashboard:
        """Parse a <dashboard> element."""
        db = TableauDashboard(name=elem.get("name", ""))

        # Size
        size_elem = elem.find("size")
        if size_elem is not None:
            db.size_width = int(size_elem.get("maxwidth", "0") or "0")
            db.size_height = int(size_elem.get("maxheight", "0") or "0")

        # Worksheet references inside the dashboard
        for zone in elem.iter("zone"):
            ws_name = zone.get("name", "")
            zone_type = zone.get("type", "")
            if ws_name and zone_type != "layout-basic":
                db.worksheets.append(ws_name)

        return db


# =====================================================================
# Tableau REST API client
# =====================================================================


@dataclass
class TableauSiteInfo:
    """Tableau Server/Cloud site information."""

    site_id: str
    site_name: str
    content_url: str


@dataclass
class TableauApiConfig:
    """Configuration for Tableau REST API access."""

    server_url: str = ""
    site_name: str = ""
    api_version: str = "3.21"
    # Auth: personal access token
    token_name: str = ""
    token_value: str = ""
    # Or: username/password
    username: str = ""
    password: str = ""

    @property
    def base_url(self) -> str:
        return f"{self.server_url.rstrip('/')}/api/{self.api_version}"


class TableauRestClient:
    """Async client for Tableau REST API.

    Supports authentication (PAT or username/password),
    listing workbooks/datasources/views, and downloading workbook XML.

    In production, uses httpx for HTTP calls. For testing, all HTTP
    methods can be overridden by providing a mock transport.
    """

    def __init__(self) -> None:
        self._config: TableauApiConfig | None = None
        self._auth_token: str = ""
        self._site_id: str = ""
        self._connected: bool = False
        self._http_client: Any = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self, config: TableauApiConfig) -> TableauSiteInfo:
        """Authenticate and store session credentials.

        Uses Personal Access Token (PAT) auth if token_name is set,
        otherwise falls back to username/password.
        """
        self._config = config

        # Build sign-in payload
        if config.token_name:
            signin_body = {
                "credentials": {
                    "personalAccessTokenName": config.token_name,
                    "personalAccessTokenSecret": config.token_value,
                    "site": {"contentUrl": config.site_name},
                }
            }
        else:
            signin_body = {
                "credentials": {
                    "name": config.username,
                    "password": config.password,
                    "site": {"contentUrl": config.site_name},
                }
            }

        # In production: POST to /auth/signin
        # Here we store the config and let http_post be injected for testing
        response = await self._http_post(
            f"{config.base_url}/auth/signin",
            json={"credentials": signin_body["credentials"]},
        )

        creds = response.get("credentials", {})
        self._auth_token = creds.get("token", "")
        site = creds.get("site", {})
        self._site_id = site.get("id", "")
        self._connected = True

        return TableauSiteInfo(
            site_id=self._site_id,
            site_name=config.site_name,
            content_url=site.get("contentUrl", config.site_name),
        )

    async def list_workbooks(self, page_size: int = 100, page: int = 1) -> dict[str, Any]:
        """GET /sites/{site_id}/workbooks — paginated."""
        self._require_connected()
        return await self._http_get(
            f"{self._config.base_url}/sites/{self._site_id}/workbooks",  # type: ignore[union-attr]
            params={"pageSize": str(page_size), "pageNumber": str(page)},
        )

    async def list_datasources(self, page_size: int = 100, page: int = 1) -> dict[str, Any]:
        """GET /sites/{site_id}/datasources — paginated."""
        self._require_connected()
        return await self._http_get(
            f"{self._config.base_url}/sites/{self._site_id}/datasources",  # type: ignore[union-attr]
            params={"pageSize": str(page_size), "pageNumber": str(page)},
        )

    async def list_views(self, page_size: int = 100, page: int = 1) -> dict[str, Any]:
        """GET /sites/{site_id}/views — paginated."""
        self._require_connected()
        return await self._http_get(
            f"{self._config.base_url}/sites/{self._site_id}/views",  # type: ignore[union-attr]
            params={"pageSize": str(page_size), "pageNumber": str(page)},
        )

    async def download_workbook(self, workbook_id: str) -> bytes:
        """GET /sites/{site_id}/workbooks/{id}/content — returns .twbx bytes."""
        self._require_connected()
        return await self._http_get_bytes(
            f"{self._config.base_url}/sites/{self._site_id}/workbooks/{workbook_id}/content",
        )

    async def disconnect(self) -> None:
        """POST /auth/signout."""
        if self._connected and self._config:
            try:
                await self._http_post(f"{self._config.base_url}/auth/signout", json={})
            except Exception:
                pass
        self._auth_token = ""
        self._site_id = ""
        self._connected = False

    def _require_connected(self) -> None:
        if not self._connected:
            raise RuntimeError("Not connected — call connect() first")

    # --- HTTP transport (overridable for testing) ---

    async def _http_get(self, url: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        """GET request returning JSON. Override for testing."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")
        async with httpx.AsyncClient() as client:
            headers = {"X-Tableau-Auth": self._auth_token} if self._auth_token else {}
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]

    async def _http_get_bytes(self, url: str) -> bytes:
        """GET request returning raw bytes. Override for testing."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")
        async with httpx.AsyncClient() as client:
            headers = {"X-Tableau-Auth": self._auth_token} if self._auth_token else {}
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.content

    async def _http_post(self, url: str, json: dict[str, Any]) -> dict[str, Any]:
        """POST request returning JSON. Override for testing."""
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx required: pip install httpx")
        async with httpx.AsyncClient() as client:
            headers = {"X-Tableau-Auth": self._auth_token} if self._auth_token else {}
            resp = await client.post(url, json=json, headers=headers)
            resp.raise_for_status()
            return resp.json()  # type: ignore[no-any-return]


# =====================================================================
# Tableau data-source → Fabric mapping
# =====================================================================


# Tableau connection type → Fabric equivalent
TABLEAU_TO_FABRIC_SOURCE: dict[str, str] = {
    "sqlserver": "Fabric SQL Endpoint",
    "postgres": "Fabric SQL Endpoint",
    "mysql": "Fabric SQL Endpoint",
    "oracle": "Fabric SQL Endpoint",
    "bigquery": "Fabric Lakehouse (Delta)",
    "snowflake": "Fabric Lakehouse (Delta)",
    "redshift": "Fabric Lakehouse (Delta)",
    "excel-direct": "Fabric Lakehouse (file import)",
    "textscan": "Fabric Lakehouse (file import)",
    "hyper": "Fabric Lakehouse (Delta)",
    "dataengine": "Fabric Lakehouse (Delta)",
    "": "Unknown",
}

# Tableau data type → Fabric/Power BI data type
TABLEAU_TO_FABRIC_TYPE: dict[str, str] = {
    "integer": "Int64",
    "real": "Double",
    "string": "String",
    "boolean": "Boolean",
    "date": "DateTime",
    "datetime": "DateTime",
}


def map_connection_type(tableau_type: str) -> str:
    """Map a Tableau connection class to a Fabric target."""
    return TABLEAU_TO_FABRIC_SOURCE.get(tableau_type, "Fabric SQL Endpoint")


def map_data_type(tableau_type: str) -> str:
    """Map a Tableau data type to a Fabric/PBI column type."""
    return TABLEAU_TO_FABRIC_TYPE.get(tableau_type, "String")


# =====================================================================
# Full Tableau SourceConnector
# =====================================================================


class FullTableauConnector(SourceConnector):
    """Production Tableau connector — REST API + TWB/TWBX parsing.

    Replaces the Phase 26 stub with full functionality.
    """

    def __init__(self) -> None:
        self._client = TableauRestClient()
        self._parser = TableauWorkbookParser()
        self._translator = TableauCalcTranslator()
        self._discovered: list[ExtractedAsset] = []
        self._connected = False

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform=SourcePlatform.TABLEAU,
            name="Tableau Connector",
            version="1.0.0",
            description="Full Tableau connector — REST API + TWB/TWBX parsing + calc field → DAX",
            supported_asset_types=["workbook", "datasource", "dashboard", "view", "calculated_field"],
            is_stub=False,
        )

    async def connect(self, config: dict[str, Any]) -> bool:
        """Connect to Tableau Server/Cloud."""
        api_config = TableauApiConfig(
            server_url=config.get("server_url", ""),
            site_name=config.get("site_name", ""),
            api_version=config.get("api_version", "3.21"),
            token_name=config.get("token_name", ""),
            token_value=config.get("token_value", ""),
            username=config.get("username", ""),
            password=config.get("password", ""),
        )
        try:
            await self._client.connect(api_config)
            self._connected = True
            logger.info("Tableau connector connected to %s", api_config.server_url)
            return True
        except Exception as exc:
            logger.error("Tableau connection failed: %s", exc)
            return False

    async def discover(self) -> list[ExtractedAsset]:
        """Discover all Tableau assets via REST API."""
        if not self._connected:
            raise RuntimeError("Not connected")

        assets: list[ExtractedAsset] = []

        # Workbooks
        wb_resp = await self._client.list_workbooks()
        for wb in wb_resp.get("workbooks", {}).get("workbook", []):
            assets.append(ExtractedAsset(
                asset_id=wb.get("id", ""),
                asset_type="workbook",
                name=wb.get("name", ""),
                source_path=wb.get("contentUrl", ""),
                platform="tableau",
                metadata={
                    "project": wb.get("project", {}).get("name", ""),
                    "owner": wb.get("owner", {}).get("name", ""),
                    "created_at": wb.get("createdAt", ""),
                    "updated_at": wb.get("updatedAt", ""),
                },
            ))

        # Datasources
        ds_resp = await self._client.list_datasources()
        for ds in ds_resp.get("datasources", {}).get("datasource", []):
            assets.append(ExtractedAsset(
                asset_id=ds.get("id", ""),
                asset_type="datasource",
                name=ds.get("name", ""),
                source_path=ds.get("contentUrl", ""),
                platform="tableau",
                metadata={
                    "type": ds.get("type", ""),
                    "project": ds.get("project", {}).get("name", ""),
                    "owner": ds.get("owner", {}).get("name", ""),
                },
            ))

        # Views
        views_resp = await self._client.list_views()
        for v in views_resp.get("views", {}).get("view", []):
            assets.append(ExtractedAsset(
                asset_id=v.get("id", ""),
                asset_type="view",
                name=v.get("name", ""),
                source_path=v.get("contentUrl", ""),
                platform="tableau",
                metadata={
                    "workbook_id": v.get("workbook", {}).get("id", ""),
                },
                dependencies=[v.get("workbook", {}).get("id", "")],
            ))

        self._discovered = assets
        logger.info("Tableau discovery: found %d assets", len(assets))
        return assets

    async def extract_metadata(self, asset_ids: list[str] | None = None) -> ExtractionResult:
        """Extract detailed metadata — download and parse workbooks."""
        errors: list[str] = []
        enriched: list[ExtractedAsset] = []

        targets = self._discovered if asset_ids is None else [
            a for a in self._discovered if a.asset_id in asset_ids
        ]

        for asset in targets:
            if asset.asset_type == "workbook":
                try:
                    twbx_bytes = await self._client.download_workbook(asset.asset_id)
                    parsed = self._parser.parse_twbx(twbx_bytes, filename=asset.name)
                    if not parsed.is_valid:
                        errors.extend(parsed.errors)
                        continue

                    # Translate calc fields
                    all_calcs: list[CalcField] = []
                    for ds in parsed.datasources:
                        all_calcs.extend(ds.calc_fields)
                    all_calcs.extend(parsed.parameters)
                    translations = self._translator.translate_batch(all_calcs)

                    asset.metadata["worksheets"] = [ws.name for ws in parsed.worksheets]
                    asset.metadata["dashboards"] = [db.name for db in parsed.dashboards]
                    asset.metadata["datasources"] = [ds.caption or ds.name for ds in parsed.datasources]
                    asset.metadata["calc_field_count"] = len(all_calcs)
                    asset.metadata["translations"] = [
                        {"name": t.source_name, "dax": t.dax_expression, "confidence": t.confidence}
                        for t in translations
                    ]

                    # Dependency: workbook → datasources
                    for ds in parsed.datasources:
                        if ds.connection_type:
                            asset.metadata["connection_type"] = ds.connection_type
                            asset.metadata["fabric_target"] = map_connection_type(ds.connection_type)

                except Exception as exc:
                    errors.append(f"Failed to parse workbook {asset.name}: {exc}")

            enriched.append(asset)

        return ExtractionResult(platform="tableau", assets=enriched, errors=errors)

    async def disconnect(self) -> None:
        await self._client.disconnect()
        self._connected = False
