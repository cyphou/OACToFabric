"""Example: Custom ConnectorPlugin for SAP Business Warehouse.

Demonstrates how to build a custom source connector plugin that
integrates with the OAC-to-Fabric migration framework.

This is a **template** — replace the stub implementations with real
SAP BW API calls for production use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data models (minimal stubs for illustration)
# ---------------------------------------------------------------------------


@dataclass
class SAPBWQuery:
    """Represents a SAP BW BEx query or InfoProvider."""

    name: str
    info_provider: str
    key_figures: list[str] = field(default_factory=list)
    characteristics: list[str] = field(default_factory=list)
    filters: list[str] = field(default_factory=list)


@dataclass
class SAPBWInventory:
    """Discovered SAP BW assets."""

    queries: list[SAPBWQuery] = field(default_factory=list)
    info_providers: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Connector plugin
# ---------------------------------------------------------------------------


class SAPBWConnectorPlugin:
    """ConnectorPlugin implementation for SAP Business Warehouse.

    Subclass ``ConnectorPlugin`` from
    ``src.plugins.plugin_manager`` in production code.

    Required methods:
    - ``platform_name()`` → str
    - ``create_connector(config)`` → connector instance

    This example shows the pattern without importing framework internals,
    so it can be read standalone.
    """

    name = "sap-bw-connector"
    version = "1.0.0"

    # -- ConnectorPlugin interface ------------------------------------------

    @property
    def platform_name(self) -> str:
        return "sap_bw"

    async def create_connector(self, config: dict[str, Any]) -> "SAPBWConnector":
        """Create and return a configured SAP BW connector."""
        return SAPBWConnector(
            server=config.get("server", "localhost"),
            client=config.get("client", "100"),
            system_id=config.get("system_id", "BWP"),
        )


class SAPBWConnector:
    """SAP BW source connector (stub implementation).

    In production, this would use the SAP RFC SDK or OData APIs
    to extract BEx queries, InfoProviders, and data.
    """

    def __init__(self, server: str, client: str, system_id: str) -> None:
        self.server = server
        self.client = client
        self.system_id = system_id

    async def discover(self) -> SAPBWInventory:
        """Discover all BEx queries and InfoProviders."""
        # Stub: return synthetic inventory for demonstration
        return SAPBWInventory(
            queries=[
                SAPBWQuery(
                    name="ZSA_SALES_01",
                    info_provider="0SD_C03",
                    key_figures=["Revenue", "Quantity", "Discount"],
                    characteristics=["Material", "Customer", "CalDay"],
                    filters=["CompanyCode = '1000'"],
                ),
                SAPBWQuery(
                    name="ZFI_PNL_01",
                    info_provider="0FI_GL_14",
                    key_figures=["Amount", "DebitCredit"],
                    characteristics=["GLAccount", "CostCenter", "FiscalPeriod"],
                ),
            ],
            info_providers=["0SD_C03", "0FI_GL_14", "0HR_PA_1"],
            data_sources=["2LIS_11_VAHDR", "2LIS_11_VAITM", "0FI_GL_4"],
        )

    async def extract_query(self, query_name: str) -> dict[str, Any]:
        """Extract metadata for a specific BEx query."""
        return {
            "query_name": query_name,
            "columns": [],
            "row_count_estimate": 0,
        }
