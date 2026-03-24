"""Streaming XML parser — memory-efficient RPD parsing for large files.

The standard ``lxml.etree.parse()`` loads the entire XML document into
memory.  For RPD exports > 100 MB this can exhaust available RAM.

This module provides an iterative parser using ``lxml.etree.iterparse``
that processes one element at a time, yielding ``InventoryItem`` objects
as they are encountered.  Peak memory usage stays proportional to the
size of the *largest single element*, not the total file size.

Usage::

    parser = StreamingRPDParser("large_rpd.xml")
    for item in parser.iter_items():
        process(item)  # each item is an InventoryItem

    # Or collect with a cap
    items = parser.parse(max_items=5000)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Generator

from lxml import etree

from src.core.models import (
    AssetType,
    Dependency,
    InventoryItem,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tag → AssetType mapping
# ---------------------------------------------------------------------------

_TAG_ASSET_MAP: dict[str, AssetType] = {
    "PhysicalTable": AssetType.PHYSICAL_TABLE,
    "LogicalTable": AssetType.LOGICAL_TABLE,
    "PresentationTable": AssetType.PRESENTATION_TABLE,
    "SubjectArea": AssetType.SUBJECT_AREA,
    "SecurityRole": AssetType.SECURITY_ROLE,
    "InitBlock": AssetType.INIT_BLOCK,
    "Connection": AssetType.CONNECTION,
    "DataFlow": AssetType.DATA_FLOW,
}

# Set of tags we're interested in (for fast lookups)
_TRACKED_TAGS = set(_TAG_ASSET_MAP.keys())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_id(asset_type: str, name: str) -> str:
    """Generate a deterministic ID from asset type and name."""
    slug = name.strip().replace("/", "__").replace(" ", "_").lower()
    return f"{asset_type}__{slug}"


def _safe_text(elem: etree._Element | None) -> str:
    """Safely extract text content from an element."""
    if elem is None:
        return ""
    return (elem.text or "").strip()


def _safe_attr(elem: etree._Element, name: str, default: str = "") -> str:
    """Safely extract an attribute value."""
    return (elem.get(name) or default).strip()


# ---------------------------------------------------------------------------
# StreamingRPDParser
# ---------------------------------------------------------------------------


class StreamingRPDParser:
    """Memory-efficient, streaming RPD XML parser.

    Uses ``iterparse`` with element cleanup to keep memory usage
    constant regardless of file size.
    """

    def __init__(self, xml_path: str | Path) -> None:
        self._path = Path(xml_path)
        if not self._path.exists():
            raise FileNotFoundError(f"RPD XML file not found: {self._path}")
        self._items_yielded = 0
        self._bytes_processed = 0

    @property
    def items_yielded(self) -> int:
        return self._items_yielded

    # ------------------------------------------------------------------
    # Streaming entry point
    # ------------------------------------------------------------------

    def iter_items(
        self,
        *,
        max_items: int = 0,
        asset_types: list[AssetType] | None = None,
    ) -> Generator[InventoryItem, None, None]:
        """Yield InventoryItem objects one at a time from the RPD XML.

        Parameters
        ----------
        max_items
            Maximum number of items to yield (0 = unlimited).
        asset_types
            If provided, only yield items of these types.
        """
        self._items_yielded = 0
        allowed_types = set(asset_types) if asset_types else None

        logger.info("Streaming RPD XML: %s", self._path)

        source = open(str(self._path), "rb")  # noqa: SIM115
        try:
            context = etree.iterparse(
                source,
                events=("end",),
                tag=list(_TRACKED_TAGS),
            )

            for _event, elem in context:
                item = self._element_to_item(elem)
                if item is None:
                    # Free memory for this element
                    elem.clear()
                    _clear_ancestors(elem)
                    continue

                if allowed_types and item.asset_type not in allowed_types:
                    elem.clear()
                    _clear_ancestors(elem)
                    continue

                self._items_yielded += 1
                yield item

                # Free memory for the processed element
                elem.clear()
                _clear_ancestors(elem)

                if max_items and self._items_yielded >= max_items:
                    logger.info("Reached max_items=%d, stopping", max_items)
                    break

        except etree.XMLSyntaxError as exc:
            logger.error("XML syntax error during streaming parse: %s", exc)
            raise
        finally:
            source.close()

        logger.info(
            "Streaming parse complete — %d items yielded", self._items_yielded
        )

    def parse(
        self,
        *,
        max_items: int = 0,
        asset_types: list[AssetType] | None = None,
    ) -> list[InventoryItem]:
        """Convenience: collect all yielded items into a list."""
        return list(
            self.iter_items(max_items=max_items, asset_types=asset_types)
        )

    # ------------------------------------------------------------------
    # Element → InventoryItem
    # ------------------------------------------------------------------

    def _element_to_item(self, elem: etree._Element) -> InventoryItem | None:
        """Convert an XML element to an InventoryItem, or None if invalid."""
        tag = etree.QName(elem).localname if isinstance(elem.tag, str) and "{" in elem.tag else elem.tag

        asset_type = _TAG_ASSET_MAP.get(tag)
        if asset_type is None:
            return None

        name = _safe_attr(elem, "name") or _safe_attr(elem, "Name") or _safe_text(elem.find("Name"))
        if not name:
            return None

        # Build metadata from child elements and attributes
        metadata: dict = {}
        for child in elem:
            child_tag = child.tag if isinstance(child.tag, str) else ""
            if child_tag and child.text:
                metadata[child_tag] = child.text.strip()

        # Extract dependencies
        dependencies = self._extract_dependencies(elem, name, asset_type)

        return InventoryItem(
            id=_make_id(asset_type.value, name),
            asset_type=asset_type,
            source_path=f"/{asset_type.value}/{name}",
            name=name,
            metadata=metadata,
            dependencies=dependencies,
            source="rpd_streaming",
        )

    def _extract_dependencies(
        self,
        elem: etree._Element,
        name: str,
        asset_type: AssetType,
    ) -> list[Dependency]:
        """Extract dependency references from an element."""
        deps: list[Dependency] = []

        # Look for common dependency patterns in RPD XML
        for ref_elem in elem.iter():
            ref_tag = ref_elem.tag if isinstance(ref_elem.tag, str) else ""
            if "Ref" in ref_tag or "Reference" in ref_tag:
                target = _safe_attr(ref_elem, "name") or _safe_text(ref_elem)
                if target and target != name:
                    deps.append(
                        Dependency(
                            source_id=_make_id(asset_type.value, name),
                            target_id=target,
                            dependency_type=f"references_{ref_tag.lower()}",
                        )
                    )

        return deps


# ---------------------------------------------------------------------------
# Memory management helper
# ---------------------------------------------------------------------------


def _clear_ancestors(elem: etree._Element) -> None:
    """Remove processed elements from their parent to free memory.

    This is the standard ``iterparse`` memory management pattern:
    clear the element and remove it from its parent.
    """
    parent = elem.getparent()
    if parent is not None:
        parent.remove(elem)
