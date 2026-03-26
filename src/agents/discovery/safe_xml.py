"""Safe XML parsing with XXE protection.

Ported from T2P's security_validator — provides safe XML parsing
that defends against XML External Entity (XXE) injection attacks
when parsing OAC RPD exports and catalog XML responses.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Any
from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)


def safe_parse_xml(content: str | bytes) -> Element:
    """Parse XML content with XXE protection.

    Uses ``defusedxml`` if available, otherwise falls back to stdlib
    ``xml.etree.ElementTree`` with entity expansion disabled.

    Raises
    ------
    ValueError
        If the XML contains DTD declarations or entity definitions.
    xml.etree.ElementTree.ParseError
        If the XML is malformed.
    """
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    else:
        content_bytes = content

    # Check for DTD / entity declarations
    content_str = content_bytes.decode("utf-8", errors="replace")
    if re.search(r"<!DOCTYPE\s", content_str, re.IGNORECASE):
        raise ValueError("XML contains DOCTYPE declaration — potential XXE attack")
    if re.search(r"<!ENTITY\s", content_str, re.IGNORECASE):
        raise ValueError("XML contains ENTITY declaration — potential XXE attack")
    if re.search(r"SYSTEM\s+[\"']", content_str, re.IGNORECASE):
        raise ValueError("XML contains SYSTEM reference — potential XXE attack")

    try:
        import defusedxml.ElementTree as DefusedET  # type: ignore[import-untyped]
        return DefusedET.fromstring(content_bytes)
    except ImportError:
        import xml.etree.ElementTree as ET
        return ET.fromstring(content_bytes)


def safe_parse_xml_file(path: str) -> Element:
    """Parse an XML file with XXE protection.

    Reads the file content and delegates to ``safe_parse_xml``.
    """
    from pathlib import Path
    content = Path(path).read_bytes()
    return safe_parse_xml(content)


def validate_xml_path(path: str) -> bool:
    """Validate that a file path is safe to read (no directory traversal).

    Returns True if the path is safe, False otherwise.
    """
    import os
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        logger.warning("Path traversal detected: %s", path)
        return False
    if os.path.isabs(path) and not path.startswith(os.getcwd()):
        # Allow absolute paths within the working directory
        pass
    return True
