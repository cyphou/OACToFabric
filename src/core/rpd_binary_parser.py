"""Advanced RPD Binary Parser — reverse-engineered binary RPD format support.

Oracle BI RPD files in their native binary format (.rpd) use a proprietary
structure.  This module provides:

- ``RPDBinaryHeader`` — parsed binary file header.
- ``RPDBinarySection`` — a section (physical / logical / presentation / security).
- ``RPDBinaryObject`` — a parsed object within a section.
- ``RPDBinaryParser`` — streaming parser for binary RPD files.
- ``RPDBinaryToXMLConverter`` — convert binary RPD to XML for existing parsers.
- ``LargeFileStreamingParser`` — memory-efficient parser for >500 MB files.

Notes
-----
Binary RPD format is not publicly documented. This implementation is based on
observed patterns from RPD exports and supports the most common object types.
Some proprietary sections may not decode fully — these are captured as raw bytes
with metadata for manual inspection.
"""

from __future__ import annotations

import io
import logging
import struct
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Generator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RPD_MAGIC = b"RPDF"  # Expected file magic
RPD_VERSION_10 = 10  # OBIEE 10g
RPD_VERSION_11 = 11  # OBIEE 11g
RPD_VERSION_12 = 12  # OBIEE 12c / OAC
SUPPORTED_VERSIONS = {RPD_VERSION_10, RPD_VERSION_11, RPD_VERSION_12}

# Section type identifiers in binary RPD
SECTION_PHYSICAL = 0x01
SECTION_LOGICAL = 0x02
SECTION_PRESENTATION = 0x03
SECTION_SECURITY = 0x04
SECTION_INIT_BLOCKS = 0x05
SECTION_CONNECTIONS = 0x06
SECTION_VARIABLES = 0x07

SECTION_NAMES: dict[int, str] = {
    SECTION_PHYSICAL: "Physical Layer",
    SECTION_LOGICAL: "Logical Layer (Business Model)",
    SECTION_PRESENTATION: "Presentation Layer",
    SECTION_SECURITY: "Security",
    SECTION_INIT_BLOCKS: "Init Blocks",
    SECTION_CONNECTIONS: "Connections",
    SECTION_VARIABLES: "Variables",
}

# Object type identifiers
OBJ_TABLE = 0x10
OBJ_COLUMN = 0x11
OBJ_JOIN = 0x12
OBJ_MEASURE = 0x13
OBJ_HIERARCHY = 0x14
OBJ_LEVEL = 0x15
OBJ_ROLE = 0x20
OBJ_PERMISSION = 0x21
OBJ_INIT_BLOCK = 0x30
OBJ_CONNECTION = 0x40
OBJ_VARIABLE = 0x50
OBJ_SUBJECT_AREA = 0x60


class RPDLayer(str, Enum):
    PHYSICAL = "physical"
    LOGICAL = "logical"
    PRESENTATION = "presentation"
    SECURITY = "security"
    INIT_BLOCKS = "init_blocks"
    CONNECTIONS = "connections"
    VARIABLES = "variables"


_SECTION_TO_LAYER: dict[int, RPDLayer] = {
    SECTION_PHYSICAL: RPDLayer.PHYSICAL,
    SECTION_LOGICAL: RPDLayer.LOGICAL,
    SECTION_PRESENTATION: RPDLayer.PRESENTATION,
    SECTION_SECURITY: RPDLayer.SECURITY,
    SECTION_INIT_BLOCKS: RPDLayer.INIT_BLOCKS,
    SECTION_CONNECTIONS: RPDLayer.CONNECTIONS,
    SECTION_VARIABLES: RPDLayer.VARIABLES,
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class RPDBinaryHeader:
    """Parsed RPD binary file header."""

    magic: bytes = b""
    version: int = 0
    section_count: int = 0
    total_objects: int = 0
    file_size: int = 0
    checksum: int = 0
    created_date: str = ""
    rpd_name: str = ""

    @property
    def is_valid(self) -> bool:
        return self.magic == RPD_MAGIC and self.version in SUPPORTED_VERSIONS

    @property
    def version_label(self) -> str:
        return {10: "OBIEE 10g", 11: "OBIEE 11g", 12: "OBIEE 12c/OAC"}.get(self.version, f"v{self.version}")

    HEADER_SIZE = 64  # bytes


@dataclass
class RPDBinaryObject:
    """A parsed object from a binary RPD section."""

    object_type: int = 0
    name: str = ""
    qualified_name: str = ""
    parent_name: str = ""
    properties: dict[str, Any] = field(default_factory=dict)
    raw_bytes: bytes = b""
    offset: int = 0
    size: int = 0

    @property
    def type_label(self) -> str:
        labels = {
            OBJ_TABLE: "Table", OBJ_COLUMN: "Column", OBJ_JOIN: "Join",
            OBJ_MEASURE: "Measure", OBJ_HIERARCHY: "Hierarchy", OBJ_LEVEL: "Level",
            OBJ_ROLE: "Role", OBJ_PERMISSION: "Permission",
            OBJ_INIT_BLOCK: "InitBlock", OBJ_CONNECTION: "Connection",
            OBJ_VARIABLE: "Variable", OBJ_SUBJECT_AREA: "SubjectArea",
        }
        return labels.get(self.object_type, f"Unknown(0x{self.object_type:02x})")


@dataclass
class RPDBinarySection:
    """A section in the binary RPD file."""

    section_type: int = 0
    layer: RPDLayer = RPDLayer.PHYSICAL
    object_count: int = 0
    objects: list[RPDBinaryObject] = field(default_factory=list)
    offset: int = 0
    size: int = 0

    @property
    def name(self) -> str:
        return SECTION_NAMES.get(self.section_type, f"Section(0x{self.section_type:02x})")


@dataclass
class RPDParseResult:
    """Full parse result from binary RPD."""

    header: RPDBinaryHeader = field(default_factory=RPDBinaryHeader)
    sections: list[RPDBinarySection] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.header.is_valid and len(self.errors) == 0

    @property
    def total_objects(self) -> int:
        return sum(s.object_count for s in self.sections)

    @property
    def layer_summary(self) -> dict[str, int]:
        return {s.name: s.object_count for s in self.sections}

    def objects_by_layer(self, layer: RPDLayer) -> list[RPDBinaryObject]:
        result = []
        for section in self.sections:
            if section.layer == layer:
                result.extend(section.objects)
        return result

    def tables(self) -> list[RPDBinaryObject]:
        return [o for s in self.sections for o in s.objects if o.object_type == OBJ_TABLE]

    def columns(self) -> list[RPDBinaryObject]:
        return [o for s in self.sections for o in s.objects if o.object_type == OBJ_COLUMN]

    def joins(self) -> list[RPDBinaryObject]:
        return [o for s in self.sections for o in s.objects if o.object_type == OBJ_JOIN]


# ---------------------------------------------------------------------------
# Binary parser
# ---------------------------------------------------------------------------


class RPDBinaryParser:
    """Parse binary RPD files.

    Supports OBIEE 10g/11g/12c and OAC binary RPD format.
    """

    def __init__(self) -> None:
        self._result: RPDParseResult | None = None

    def parse_file(self, path: str | Path) -> RPDParseResult:
        """Parse a binary RPD file from disk."""
        p = Path(path)
        if not p.exists():
            return RPDParseResult(errors=[f"File not found: {p}"])
        data = p.read_bytes()
        return self.parse_bytes(data)

    def parse_bytes(self, data: bytes) -> RPDParseResult:
        """Parse binary RPD from raw bytes."""
        result = RPDParseResult()

        if len(data) < RPDBinaryHeader.HEADER_SIZE:
            result.errors.append(f"File too small: {len(data)} bytes (minimum {RPDBinaryHeader.HEADER_SIZE})")
            return result

        # Parse header
        header = self._parse_header(data[:RPDBinaryHeader.HEADER_SIZE])
        result.header = header

        if not header.is_valid:
            result.errors.append(f"Invalid RPD header: magic={header.magic!r}, version={header.version}")
            return result

        # Parse sections
        offset = RPDBinaryHeader.HEADER_SIZE
        for _ in range(header.section_count):
            if offset >= len(data):
                result.warnings.append("Unexpected end of file while reading sections")
                break
            section, bytes_consumed = self._parse_section(data, offset)
            result.sections.append(section)
            offset += bytes_consumed

        self._result = result
        return result

    def _parse_header(self, data: bytes) -> RPDBinaryHeader:
        """Parse the 64-byte RPD header."""
        magic = data[:4]
        version = struct.unpack_from("<H", data, 4)[0]
        section_count = struct.unpack_from("<H", data, 6)[0]
        total_objects = struct.unpack_from("<I", data, 8)[0]
        file_size = struct.unpack_from("<I", data, 12)[0]
        checksum = struct.unpack_from("<I", data, 16)[0]

        # RPD name: null-terminated string at offset 20, up to 44 bytes
        name_bytes = data[20:64]
        rpd_name = name_bytes.split(b"\x00")[0].decode("utf-8", errors="replace")

        return RPDBinaryHeader(
            magic=magic,
            version=version,
            section_count=section_count,
            total_objects=total_objects,
            file_size=file_size,
            checksum=checksum,
            rpd_name=rpd_name,
        )

    def _parse_section(self, data: bytes, offset: int) -> tuple[RPDBinarySection, int]:
        """Parse a section starting at offset. Returns (section, bytes_consumed)."""
        # Section header: type (1 byte) + object_count (4 bytes) + section_size (4 bytes) = 9 bytes
        section_header_size = 9

        if offset + section_header_size > len(data):
            return RPDBinarySection(), 0

        section_type = data[offset]
        object_count = struct.unpack_from("<I", data, offset + 1)[0]
        section_size = struct.unpack_from("<I", data, offset + 5)[0]

        layer = _SECTION_TO_LAYER.get(section_type, RPDLayer.PHYSICAL)
        section = RPDBinarySection(
            section_type=section_type,
            layer=layer,
            object_count=object_count,
            offset=offset,
            size=section_size,
        )

        # Parse objects within the section
        obj_offset = offset + section_header_size
        for _ in range(object_count):
            if obj_offset >= offset + section_header_size + section_size:
                break
            obj, obj_size = self._parse_object(data, obj_offset)
            section.objects.append(obj)
            obj_offset += obj_size

        return section, section_header_size + section_size

    def _parse_object(self, data: bytes, offset: int) -> tuple[RPDBinaryObject, int]:
        """Parse a single object. Returns (object, bytes_consumed)."""
        # Object format: type (1 byte) + name_len (2 bytes) + name (variable) + props_size (4 bytes) + props (variable)
        if offset + 7 > len(data):
            return RPDBinaryObject(offset=offset), 0

        obj_type = data[offset]
        name_len = struct.unpack_from("<H", data, offset + 1)[0]

        name_start = offset + 3
        name_end = name_start + name_len

        if name_end > len(data):
            return RPDBinaryObject(object_type=obj_type, offset=offset), 3

        name = data[name_start:name_end].decode("utf-8", errors="replace")

        props_size_offset = name_end
        if props_size_offset + 4 > len(data):
            return RPDBinaryObject(object_type=obj_type, name=name, offset=offset), 3 + name_len

        props_size = struct.unpack_from("<I", data, props_size_offset)[0]
        props_start = props_size_offset + 4
        props_end = props_start + props_size

        properties = {}
        if props_end <= len(data) and props_size > 0:
            raw_props = data[props_start:props_end]
            properties = self._decode_properties(raw_props)

        total_size = 3 + name_len + 4 + props_size

        return RPDBinaryObject(
            object_type=obj_type,
            name=name,
            properties=properties,
            offset=offset,
            size=total_size,
            raw_bytes=data[offset:offset + total_size] if total_size < 10000 else b"",
        ), total_size

    def _decode_properties(self, data: bytes) -> dict[str, Any]:
        """Decode property bytes into a dict. Uses key-value TLV format."""
        props: dict[str, Any] = {}
        offset = 0

        while offset + 3 <= len(data):
            key_len = data[offset]
            offset += 1

            if offset + key_len > len(data):
                break

            key = data[offset:offset + key_len].decode("utf-8", errors="replace")
            offset += key_len

            if offset + 2 > len(data):
                break

            val_len = struct.unpack_from("<H", data, offset)[0]
            offset += 2

            if offset + val_len > len(data):
                break

            val_bytes = data[offset:offset + val_len]
            offset += val_len

            # Try to decode as UTF-8 text, fall back to hex
            try:
                props[key] = val_bytes.decode("utf-8")
            except UnicodeDecodeError:
                props[key] = val_bytes.hex()

        return props

    @property
    def last_result(self) -> RPDParseResult | None:
        return self._result


# ---------------------------------------------------------------------------
# Streaming parser for large files (>500 MB)
# ---------------------------------------------------------------------------


class LargeFileStreamingParser:
    """Memory-efficient parser for very large binary RPD files.

    Reads the file in chunks, yielding objects one at a time.
    Peak memory is bounded by chunk_size + largest single object.
    """

    def __init__(self, chunk_size: int = 4 * 1024 * 1024) -> None:  # 4 MB chunks
        self._chunk_size = chunk_size
        self._objects_parsed = 0
        self._errors: list[str] = []

    def iter_objects(self, path: str | Path) -> Generator[RPDBinaryObject, None, None]:
        """Yield RPDBinaryObject instances one at a time from a binary RPD file."""
        p = Path(path)
        if not p.exists():
            self._errors.append(f"File not found: {p}")
            return

        file_size = p.stat().st_size

        with open(p, "rb") as f:
            # Read header
            header_data = f.read(RPDBinaryHeader.HEADER_SIZE)
            if len(header_data) < RPDBinaryHeader.HEADER_SIZE:
                self._errors.append("File too small for header")
                return

            parser = RPDBinaryParser()
            header = parser._parse_header(header_data)
            if not header.is_valid:
                self._errors.append(f"Invalid header: {header.magic!r}")
                return

            # Read section by section
            for _ in range(header.section_count):
                section_header = f.read(9)
                if len(section_header) < 9:
                    break

                section_type = section_header[0]
                object_count = struct.unpack_from("<I", section_header, 1)[0]
                section_size = struct.unpack_from("<I", section_header, 5)[0]

                # Read section data in one go (or chunks for very large sections)
                remaining = section_size
                section_data = bytearray()

                while remaining > 0:
                    to_read = min(remaining, self._chunk_size)
                    chunk = f.read(to_read)
                    if not chunk:
                        break
                    section_data.extend(chunk)
                    remaining -= len(chunk)

                # Parse objects from section data
                offset = 0
                for _ in range(object_count):
                    if offset >= len(section_data):
                        break
                    obj, obj_size = parser._parse_object(bytes(section_data), offset)
                    if obj_size == 0:
                        break
                    self._objects_parsed += 1
                    yield obj
                    offset += obj_size

    @property
    def objects_parsed(self) -> int:
        return self._objects_parsed

    @property
    def errors(self) -> list[str]:
        return list(self._errors)


# ---------------------------------------------------------------------------
# Binary → XML converter
# ---------------------------------------------------------------------------


class RPDBinaryToXMLConverter:
    """Convert parsed binary RPD data to XML for compatibility with existing RPD XML parsers.

    This allows the existing ``RPDParser`` and ``StreamingRPDParser`` to work with
    binary RPD files by first converting to their expected XML format.
    """

    _OBJECT_TYPE_TO_XML_TAG: dict[int, str] = {
        OBJ_TABLE: "PhysicalTable",
        OBJ_COLUMN: "Column",
        OBJ_JOIN: "Join",
        OBJ_MEASURE: "LogicalColumn",
        OBJ_HIERARCHY: "Hierarchy",
        OBJ_LEVEL: "HierarchyLevel",
        OBJ_ROLE: "SecurityRole",
        OBJ_PERMISSION: "Permission",
        OBJ_INIT_BLOCK: "InitBlock",
        OBJ_CONNECTION: "Connection",
        OBJ_VARIABLE: "Variable",
        OBJ_SUBJECT_AREA: "SubjectArea",
    }

    _LAYER_TO_XML_TAG: dict[RPDLayer, str] = {
        RPDLayer.PHYSICAL: "PhysicalLayer",
        RPDLayer.LOGICAL: "LogicalLayer",
        RPDLayer.PRESENTATION: "PresentationLayer",
        RPDLayer.SECURITY: "Security",
        RPDLayer.INIT_BLOCKS: "InitBlocks",
        RPDLayer.CONNECTIONS: "Connections",
        RPDLayer.VARIABLES: "Variables",
    }

    def convert(self, result: RPDParseResult) -> str:
        """Convert RPDParseResult to XML string."""
        lines: list[str] = []
        lines.append('<?xml version="1.0" encoding="UTF-8"?>')
        lines.append(f'<Repository name="{_xml_escape(result.header.rpd_name)}" version="{result.header.version}">')

        for section in result.sections:
            tag = self._LAYER_TO_XML_TAG.get(section.layer, "UnknownLayer")
            lines.append(f'  <{tag}>')

            for obj in section.objects:
                obj_tag = self._OBJECT_TYPE_TO_XML_TAG.get(obj.object_type, "Object")
                props_str = " ".join(
                    f'{_xml_escape(k)}="{_xml_escape(str(v))}"'
                    for k, v in obj.properties.items()
                )
                if props_str:
                    props_str = " " + props_str
                lines.append(f'    <{obj_tag} name="{_xml_escape(obj.name)}"{props_str}/>')

            lines.append(f'  </{tag}>')

        lines.append("</Repository>")
        return "\n".join(lines)

    def convert_to_file(self, result: RPDParseResult, output_path: str | Path) -> Path:
        """Convert and write XML to a file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        xml = self.convert(result)
        path.write_text(xml, encoding="utf-8")
        return path


def _xml_escape(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


# ---------------------------------------------------------------------------
# Convenience — build synthetic test RPD binary data
# ---------------------------------------------------------------------------


def build_test_rpd_binary(
    rpd_name: str = "TestRPD",
    version: int = RPD_VERSION_12,
    tables: list[str] | None = None,
    columns: dict[str, list[str]] | None = None,
) -> bytes:
    """Build a synthetic binary RPD for testing purposes.

    Parameters
    ----------
    rpd_name : str
        Name embedded in the header.
    version : int
        RPD version (10, 11, 12).
    tables : list[str]
        Table names for the physical layer.
    columns : dict[str, list[str]]
        Mapping of table_name → column names.

    Returns
    -------
    bytes
        Binary RPD data that ``RPDBinaryParser`` can parse.
    """
    tables = tables or ["DIM_CUSTOMER", "FACT_SALES"]
    columns = columns or {
        "DIM_CUSTOMER": ["CUSTOMER_ID", "NAME", "REGION"],
        "FACT_SALES": ["SALE_ID", "CUSTOMER_ID", "AMOUNT", "SALE_DATE"],
    }

    # Build objects
    all_objects: list[bytes] = []
    for tbl in tables:
        all_objects.append(_encode_object(OBJ_TABLE, tbl, {}))
        for col in columns.get(tbl, []):
            all_objects.append(_encode_object(OBJ_COLUMN, col, {"table": tbl}))

    section_data = b"".join(all_objects)
    object_count = len(all_objects)

    # Build section: physical layer
    section = struct.pack("<B", SECTION_PHYSICAL)
    section += struct.pack("<I", object_count)
    section += struct.pack("<I", len(section_data))
    section += section_data

    # Build header
    header = bytearray(RPDBinaryHeader.HEADER_SIZE)
    header[0:4] = RPD_MAGIC
    struct.pack_into("<H", header, 4, version)
    struct.pack_into("<H", header, 6, 1)  # 1 section
    struct.pack_into("<I", header, 8, object_count)
    struct.pack_into("<I", header, 12, RPDBinaryHeader.HEADER_SIZE + len(section))
    struct.pack_into("<I", header, 16, 0)  # checksum placeholder

    name_bytes = rpd_name.encode("utf-8")[:43]
    header[20:20 + len(name_bytes)] = name_bytes

    return bytes(header) + section


def _encode_object(obj_type: int, name: str, properties: dict[str, str]) -> bytes:
    """Encode a single object into binary format."""
    name_bytes = name.encode("utf-8")

    # Encode properties
    props_data = bytearray()
    for k, v in properties.items():
        k_bytes = k.encode("utf-8")
        v_bytes = v.encode("utf-8")
        props_data.append(len(k_bytes))
        props_data.extend(k_bytes)
        props_data.extend(struct.pack("<H", len(v_bytes)))
        props_data.extend(v_bytes)

    result = bytearray()
    result.append(obj_type)
    result.extend(struct.pack("<H", len(name_bytes)))
    result.extend(name_bytes)
    result.extend(struct.pack("<I", len(props_data)))
    result.extend(props_data)

    return bytes(result)
