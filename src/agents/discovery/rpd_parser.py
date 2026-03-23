"""RPD XML parser — extract physical, logical, presentation layers and security objects.

Oracle BI RPD (Repository) files exported as XML (UDML/XUDML format) contain
the full metadata model.  This parser uses lxml to walk the XML tree and
produce InventoryItem objects for each physical table, logical table,
presentation table / subject area, security role, and init block.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lxml import etree

from src.core.models import (
    AssetType,
    Dependency,
    InventoryItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _id(asset_type: str, name: str) -> str:
    slug = name.strip().replace("/", "__").replace(" ", "_").lower()
    return f"{asset_type}__{slug}"


def _text(elem: etree._Element | None) -> str:
    if elem is None:
        return ""
    return (elem.text or "").strip()


def _attr(elem: etree._Element, name: str, default: str = "") -> str:
    return (elem.get(name) or default).strip()


# ---------------------------------------------------------------------------
# RPDParser
# ---------------------------------------------------------------------------

class RPDParser:
    """Parse an RPD XML export and yield InventoryItem objects."""

    def __init__(self, xml_path: str | Path) -> None:
        self._path = Path(xml_path)
        if not self._path.exists():
            raise FileNotFoundError(f"RPD XML file not found: {self._path}")
        self._tree: etree._ElementTree | None = None

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def parse(self) -> list[InventoryItem]:
        """Parse the entire RPD XML and return all items."""
        logger.info("Parsing RPD XML: %s", self._path)
        try:
            self._tree = etree.parse(str(self._path))  # noqa: S320
        except etree.XMLSyntaxError as exc:
            logger.error("RPD XML parse error: %s", exc)
            raise

        items: list[InventoryItem] = []

        items.extend(self._parse_physical_layer())
        items.extend(self._parse_logical_layer())
        items.extend(self._parse_presentation_layer())
        items.extend(self._parse_security())

        logger.info("RPD parsing complete — %d items extracted", len(items))
        return items

    # ------------------------------------------------------------------
    # Physical layer
    # ------------------------------------------------------------------

    def _parse_physical_layer(self) -> list[InventoryItem]:
        """Extract physical databases, tables, and columns."""
        assert self._tree is not None
        root = self._tree.getroot()
        items: list[InventoryItem] = []

        # Try common XUDML paths for physical tables
        for tag_path in (
            ".//PhysicalTable",
            ".//physicalTable",
            ".//PHYSICAL_TABLE",
            ".//Table[@type='physical']",
        ):
            for elem in root.iter() if tag_path == "" else root.findall(tag_path):
                name = _attr(elem, "name") or _attr(elem, "mdsid") or _text(elem.find("Name"))
                if not name:
                    continue

                # Extract columns
                columns = []
                for col_elem in elem.findall(".//Column") + elem.findall(".//PhysicalColumn"):
                    col_name = _attr(col_elem, "name") or _text(col_elem.find("Name"))
                    col_type = _attr(col_elem, "dataType") or _text(col_elem.find("DataType"))
                    if col_name:
                        columns.append({"name": col_name, "data_type": col_type})

                # Database / schema context
                db_name = self._ancestor_attr(elem, ("Database", "PhysicalDatabase"), "name")

                items.append(
                    InventoryItem(
                        id=_id("physicalTable", name),
                        asset_type=AssetType.PHYSICAL_TABLE,
                        source_path=f"/physical/{db_name}/{name}" if db_name else f"/physical/{name}",
                        name=name,
                        metadata={"columns": columns, "database": db_name},
                        source="rpd",
                    )
                )

        logger.info("Physical layer: %d tables", len(items))
        return items

    # ------------------------------------------------------------------
    # Logical (business) layer
    # ------------------------------------------------------------------

    def _parse_logical_layer(self) -> list[InventoryItem]:
        assert self._tree is not None
        root = self._tree.getroot()
        items: list[InventoryItem] = []

        for tag_path in (".//LogicalTable", ".//logicalTable", ".//LOGICAL_TABLE"):
            for elem in root.findall(tag_path):
                name = _attr(elem, "name") or _text(elem.find("Name"))
                if not name:
                    continue

                # Logical columns
                columns = []
                for col_elem in (
                    elem.findall(".//LogicalColumn")
                    + elem.findall(".//Column")
                ):
                    col_name = _attr(col_elem, "name") or _text(col_elem.find("Name"))
                    expr = _text(col_elem.find("Expression")) or _text(col_elem.find("DerivedExpression"))
                    columns.append({"name": col_name, "expression": expr})

                # Hierarchies
                hierarchies = []
                for h in elem.findall(".//Hierarchy") + elem.findall(".//LogicalHierarchy"):
                    h_name = _attr(h, "name") or _text(h.find("Name"))
                    levels = [
                        _attr(lv, "name") or _text(lv.find("Name"))
                        for lv in h.findall(".//Level") + h.findall(".//HierarchyLevel")
                    ]
                    hierarchies.append({"name": h_name, "levels": levels})

                # Dependencies to physical tables
                deps: list[Dependency] = []
                for src in (
                    elem.findall(".//PhysicalTableSource")
                    + elem.findall(".//LogicalTableSource")
                ):
                    phys_name = _attr(src, "physicalTable") or _text(src.find("PhysicalTable"))
                    if phys_name:
                        deps.append(
                            Dependency(
                                source_id=_id("logicalTable", name),
                                target_id=_id("physicalTable", phys_name),
                                dependency_type="maps_to_physical",
                            )
                        )

                items.append(
                    InventoryItem(
                        id=_id("logicalTable", name),
                        asset_type=AssetType.LOGICAL_TABLE,
                        source_path=f"/logical/{name}",
                        name=name,
                        metadata={
                            "columns": columns,
                            "hierarchies": hierarchies,
                            "custom_calc_count": sum(1 for c in columns if c.get("expression")),
                        },
                        dependencies=deps,
                        source="rpd",
                    )
                )

        logger.info("Logical layer: %d tables", len(items))
        return items

    # ------------------------------------------------------------------
    # Presentation layer
    # ------------------------------------------------------------------

    def _parse_presentation_layer(self) -> list[InventoryItem]:
        assert self._tree is not None
        root = self._tree.getroot()
        items: list[InventoryItem] = []

        # Subject areas
        for tag_path in (".//SubjectArea", ".//subjectArea", ".//PresentationCatalog"):
            for elem in root.findall(tag_path):
                name = _attr(elem, "name") or _text(elem.find("Name"))
                if not name:
                    continue

                tables: list[dict[str, Any]] = []
                deps: list[Dependency] = []
                for pt in (
                    elem.findall(".//PresentationTable")
                    + elem.findall(".//presentationTable")
                ):
                    pt_name = _attr(pt, "name") or _text(pt.find("Name"))
                    cols = [
                        _attr(c, "name") or _text(c.find("Name"))
                        for c in pt.findall(".//PresentationColumn")
                    ]
                    tables.append({"name": pt_name, "columns": cols})

                    # Dependency: presentation table → logical table
                    logical_ref = _attr(pt, "logicalTable") or _text(pt.find("LogicalTable"))
                    if logical_ref:
                        deps.append(
                            Dependency(
                                source_id=_id("subjectArea", name),
                                target_id=_id("logicalTable", logical_ref),
                                dependency_type="presents_logical",
                            )
                        )

                items.append(
                    InventoryItem(
                        id=_id("subjectArea", name),
                        asset_type=AssetType.SUBJECT_AREA,
                        source_path=f"/presentation/{name}",
                        name=name,
                        metadata={"tables": tables, "table_count": len(tables)},
                        dependencies=deps,
                        source="rpd",
                    )
                )

        # Also emit individual presentation tables for completeness
        for tag_path in (".//PresentationTable", ".//presentationTable"):
            for elem in root.findall(tag_path):
                name = _attr(elem, "name") or _text(elem.find("Name"))
                if not name:
                    continue
                cols = [
                    _attr(c, "name") or _text(c.find("Name"))
                    for c in elem.findall(".//PresentationColumn")
                ]
                items.append(
                    InventoryItem(
                        id=_id("presentationTable", name),
                        asset_type=AssetType.PRESENTATION_TABLE,
                        source_path=f"/presentation/{name}",
                        name=name,
                        metadata={"columns": cols},
                        source="rpd",
                    )
                )

        logger.info("Presentation layer: %d items", len(items))
        return items

    # ------------------------------------------------------------------
    # Security objects
    # ------------------------------------------------------------------

    def _parse_security(self) -> list[InventoryItem]:
        assert self._tree is not None
        root = self._tree.getroot()
        items: list[InventoryItem] = []

        # Application roles
        for tag_path in (".//ApplicationRole", ".//Role", ".//SecurityRole"):
            for elem in root.findall(tag_path):
                name = _attr(elem, "name") or _text(elem.find("Name"))
                if not name:
                    continue
                members = [
                    _attr(m, "name") or _text(m)
                    for m in elem.findall(".//Member") + elem.findall(".//RoleMember")
                ]
                permissions = [
                    _attr(p, "object") or _text(p)
                    for p in elem.findall(".//Permission") + elem.findall(".//ObjectPermission")
                ]
                items.append(
                    InventoryItem(
                        id=_id("securityRole", name),
                        asset_type=AssetType.SECURITY_ROLE,
                        source_path=f"/security/roles/{name}",
                        name=name,
                        metadata={"members": members, "permissions": permissions},
                        source="rpd",
                    )
                )

        # Session variable init blocks (RLS)
        for tag_path in (".//SessionInitBlock", ".//InitBlock", ".//InitializationBlock"):
            for elem in root.findall(tag_path):
                name = _attr(elem, "name") or _text(elem.find("Name"))
                if not name:
                    continue
                sql = _text(elem.find("SQL")) or _text(elem.find("Query"))
                variables = [
                    _attr(v, "name") or _text(v)
                    for v in elem.findall(".//Variable") + elem.findall(".//SessionVariable")
                ]
                items.append(
                    InventoryItem(
                        id=_id("initBlock", name),
                        asset_type=AssetType.INIT_BLOCK,
                        source_path=f"/security/initblocks/{name}",
                        name=name,
                        metadata={"sql": sql, "variables": variables},
                        source="rpd",
                    )
                )

        logger.info("Security objects: %d items", len(items))
        return items

    # ------------------------------------------------------------------
    # XML helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ancestor_attr(
        elem: etree._Element,
        ancestor_tags: tuple[str, ...],
        attr_name: str,
    ) -> str:
        """Walk up the tree to find an ancestor by any of the given tag names."""
        parent = elem.getparent()
        while parent is not None:
            local = etree.QName(parent.tag).localname if "}" in str(parent.tag) else str(parent.tag)
            if local in ancestor_tags:
                return _attr(parent, attr_name)
            parent = parent.getparent()
        return ""
