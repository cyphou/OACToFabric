"""OAC theme → Power BI theme JSON converter.

Extracts OAC color palettes and formatting defaults and generates
PBI CY24SU11-compatible theme JSON.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default PBI theme structure (CY24SU11 format)
# ---------------------------------------------------------------------------

_DEFAULT_COLORS = [
    "#118DFF", "#12239E", "#E66C37", "#6B007B",
    "#E044A7", "#744EC2", "#D9B300", "#D64550",
    "#197278", "#1AAB40", "#BF399E", "#4A588A",
]

_DEFAULT_TEXT_CLASSES = {
    "callout": {"fontSize": 45, "fontFace": "DIN", "color": "#252423"},
    "title": {"fontSize": 12, "fontFace": "DIN", "color": "#252423"},
    "header": {"fontSize": 12, "fontFace": "Segoe UI Semibold", "color": "#252423"},
    "label": {"fontSize": 10, "fontFace": "Segoe UI", "color": "#252423"},
}


# ---------------------------------------------------------------------------
# OAC color extraction
# ---------------------------------------------------------------------------

# Common OAC XML/JSON color keys
_OAC_COLOR_KEYS = [
    "seriesColor", "backgroundColor", "borderColor", "fontColor",
    "legendColor", "primaryColor", "secondaryColor", "accentColor",
    "gridColor", "titleColor",
]


@dataclass
class OACTheme:
    """Parsed OAC theme definition."""

    name: str = "OAC Migrated Theme"
    colors: list[str] = field(default_factory=list)
    background_color: str = "#FFFFFF"
    foreground_color: str = "#252423"
    font_family: str = "Segoe UI"
    title_font_size: int = 12
    label_font_size: int = 10
    metadata: dict = field(default_factory=dict)


@dataclass
class PBITheme:
    """Power BI theme definition (CY24SU11 format)."""

    name: str = "Migrated Theme"
    data_colors: list[str] = field(default_factory=lambda: list(_DEFAULT_COLORS))
    background: str = "#FFFFFF"
    foreground: str = "#252423"
    table_accent: str = "#118DFF"
    text_classes: dict = field(default_factory=lambda: dict(_DEFAULT_TEXT_CLASSES))
    visual_styles: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to PBI theme JSON."""
        theme_dict = {
            "name": self.name,
            "dataColors": self.data_colors,
            "background": self.background,
            "foreground": self.foreground,
            "tableAccent": self.table_accent,
            "textClasses": self.text_classes,
        }
        if self.visual_styles:
            theme_dict["visualStyles"] = self.visual_styles
        return json.dumps(theme_dict, indent=2)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_oac_theme(theme_meta: dict) -> OACTheme:
    """Extract OAC theme from analysis/dashboard metadata.

    Args:
        theme_meta: Dict from OAC API containing theme/style info.
                    May contain keys like palette, colors, fonts, etc.

    Returns:
        Parsed OACTheme instance.
    """
    theme = OACTheme()

    theme.name = theme_meta.get("name", theme_meta.get("title", "OAC Migrated Theme"))

    # Extract colors from various OAC formats
    palette = theme_meta.get("palette", theme_meta.get("colorPalette", []))
    if isinstance(palette, list):
        theme.colors = [_normalize_color(c) for c in palette if c]

    # Single-color properties
    for key in _OAC_COLOR_KEYS:
        val = theme_meta.get(key)
        if val and isinstance(val, str) and val not in theme.colors:
            theme.colors.append(_normalize_color(val))

    # Font settings
    theme.font_family = theme_meta.get("fontFamily", theme_meta.get("font", "Segoe UI"))
    theme.background_color = _normalize_color(
        theme_meta.get("backgroundColor", "#FFFFFF")
    )
    theme.foreground_color = _normalize_color(
        theme_meta.get("fontColor", theme_meta.get("foregroundColor", "#252423"))
    )

    return theme


def _normalize_color(color: str) -> str:
    """Normalize color to #RRGGBB hex format."""
    if not color:
        return "#000000"
    color = color.strip()
    if color.startswith("rgb"):
        # rgb(r, g, b) → #RRGGBB
        import re
        nums = re.findall(r"\d+", color)
        if len(nums) >= 3:
            r, g, b = int(nums[0]), int(nums[1]), int(nums[2])
            return f"#{r:02X}{g:02X}{b:02X}"
    if color.startswith("#"):
        if len(color) == 4:
            # #RGB → #RRGGBB
            return f"#{color[1]*2}{color[2]*2}{color[3]*2}"
        return color.upper()
    return f"#{color.upper()}" if len(color) == 6 else color


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def convert_theme(oac_theme: OACTheme) -> PBITheme:
    """Convert an OAC theme to a PBI theme.

    Args:
        oac_theme: Parsed OAC theme

    Returns:
        PBI theme ready for JSON serialization
    """
    pbi = PBITheme(name=oac_theme.name)

    # Use OAC colors if available, pad with defaults
    if oac_theme.colors:
        pbi.data_colors = oac_theme.colors[:12]
        if len(pbi.data_colors) < 6:
            pbi.warnings.append(
                f"Only {len(pbi.data_colors)} colors extracted; "
                f"padded with PBI defaults"
            )
            pbi.data_colors.extend(
                _DEFAULT_COLORS[len(pbi.data_colors):12]
            )

    pbi.background = oac_theme.background_color
    pbi.foreground = oac_theme.foreground_color
    pbi.table_accent = pbi.data_colors[0] if pbi.data_colors else "#118DFF"

    # Text classes with OAC font
    font = oac_theme.font_family
    pbi.text_classes = {
        "callout": {"fontSize": 45, "fontFace": font, "color": pbi.foreground},
        "title": {
            "fontSize": oac_theme.title_font_size,
            "fontFace": font,
            "color": pbi.foreground,
        },
        "header": {
            "fontSize": oac_theme.title_font_size,
            "fontFace": f"{font} Semibold",
            "color": pbi.foreground,
        },
        "label": {
            "fontSize": oac_theme.label_font_size,
            "fontFace": font,
            "color": pbi.foreground,
        },
    }

    logger.info(
        "Converted theme '%s' with %d data colors",
        pbi.name, len(pbi.data_colors),
    )
    return pbi


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------


def generate_pbi_theme(theme_meta: dict) -> tuple[str, list[str]]:
    """Full pipeline: extract OAC theme → convert → return PBI theme JSON.

    Args:
        theme_meta: Raw OAC theme/style dict

    Returns:
        (theme_json_string, list_of_warnings)
    """
    oac = extract_oac_theme(theme_meta)
    pbi = convert_theme(oac)
    return pbi.to_json(), pbi.warnings
