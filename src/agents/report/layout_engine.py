"""Layout engine — OAC grid/section layout → PBI pixel-based canvas.

OAC dashboards use a grid/section-based layout where content is placed
in relative-sized sections.  Power BI uses a fixed pixel canvas
(default 1280×720 at 16:9 ratio).

This module:
  1. Parses OAC layout metadata (sections, rows, columns, view positions)
  2. Translates relative coordinates → absolute pixel coordinates
  3. Handles overflow by auto-paginating to additional PBI pages
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_CANVAS_WIDTH = 1280
DEFAULT_CANVAS_HEIGHT = 720

# Minimum visual dimensions (pixels)
MIN_VISUAL_WIDTH = 100
MIN_VISUAL_HEIGHT = 80

# Padding between visuals
VISUAL_PADDING = 8

# Maximum visuals per page before auto-pagination
MAX_VISUALS_PER_PAGE = 20


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class VisualPosition:
    """Absolute pixel position of a visual on a PBI canvas page."""

    x: int
    y: int
    width: int
    height: int
    page_index: int = 0             # 0-based page number
    visual_name: str = ""           # Reference back to the OAC view name
    visual_type: str = ""           # PBI visual type id
    z_order: int = 0


@dataclass
class OACSection:
    """An OAC dashboard section (a rectangular region containing views)."""

    name: str = ""
    relative_x: float = 0.0        # 0.0–1.0 (fraction of canvas width)
    relative_y: float = 0.0        # 0.0–1.0 (fraction of canvas height)
    relative_width: float = 1.0
    relative_height: float = 1.0
    views: list[dict[str, Any]] = field(default_factory=list)
    # Each view dict: {"name": str, "type": str, …}


@dataclass
class OACPageLayout:
    """Layout metadata for a single OAC dashboard page."""

    page_name: str = ""
    page_index: int = 0
    sections: list[OACSection] = field(default_factory=list)
    # If sections are not available, raw views with positions:
    views: list[dict[str, Any]] = field(default_factory=list)
    canvas_width: int = DEFAULT_CANVAS_WIDTH
    canvas_height: int = DEFAULT_CANVAS_HEIGHT


@dataclass
class PBIPage:
    """A single Power BI report page with positioned visuals."""

    name: str = "Page 1"
    display_name: str = "Page 1"
    page_index: int = 0
    width: int = DEFAULT_CANVAS_WIDTH
    height: int = DEFAULT_CANVAS_HEIGHT
    visuals: list[VisualPosition] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Layout translation
# ---------------------------------------------------------------------------


def translate_sections(
    sections: list[OACSection],
    canvas_width: int = DEFAULT_CANVAS_WIDTH,
    canvas_height: int = DEFAULT_CANVAS_HEIGHT,
) -> list[VisualPosition]:
    """Convert OAC sections with relative coordinates to PBI pixel positions.

    Each section may contain multiple views; views within a section are
    stacked vertically.
    """
    positions: list[VisualPosition] = []
    z = 0

    for section in sections:
        sx = int(section.relative_x * canvas_width) + VISUAL_PADDING
        sy = int(section.relative_y * canvas_height) + VISUAL_PADDING
        sw = int(section.relative_width * canvas_width) - 2 * VISUAL_PADDING
        sh = int(section.relative_height * canvas_height) - 2 * VISUAL_PADDING

        sw = max(sw, MIN_VISUAL_WIDTH)
        sh = max(sh, MIN_VISUAL_HEIGHT)

        if not section.views:
            # Section as one visual placeholder
            positions.append(
                VisualPosition(
                    x=sx, y=sy, width=sw, height=sh,
                    visual_name=section.name, z_order=z,
                )
            )
            z += 1
        else:
            # Stack views vertically within the section
            n_views = len(section.views)
            view_height = max(MIN_VISUAL_HEIGHT, (sh - (n_views - 1) * VISUAL_PADDING) // n_views)
            for i, view in enumerate(section.views):
                vy = sy + i * (view_height + VISUAL_PADDING)
                positions.append(
                    VisualPosition(
                        x=sx,
                        y=vy,
                        width=sw,
                        height=view_height,
                        visual_name=view.get("name", f"view_{i}"),
                        visual_type=view.get("type", ""),
                        z_order=z,
                    )
                )
                z += 1

    return positions


def translate_flat_views(
    views: list[dict[str, Any]],
    canvas_width: int = DEFAULT_CANVAS_WIDTH,
    canvas_height: int = DEFAULT_CANVAS_HEIGHT,
) -> list[VisualPosition]:
    """Lay out a flat list of views in a grid pattern.

    Used when OAC layout metadata doesn't provide section-level positions.
    Arranges views in a responsive grid (2–3 columns).
    """
    if not views:
        return []

    n = len(views)
    cols = min(3, n)  # up to 3 columns
    rows = math.ceil(n / cols)

    vw = (canvas_width - (cols + 1) * VISUAL_PADDING) // cols
    vh = (canvas_height - (rows + 1) * VISUAL_PADDING) // rows
    vw = max(vw, MIN_VISUAL_WIDTH)
    vh = max(vh, MIN_VISUAL_HEIGHT)

    positions: list[VisualPosition] = []
    for i, view in enumerate(views):
        row = i // cols
        col = i % cols
        x = VISUAL_PADDING + col * (vw + VISUAL_PADDING)
        y = VISUAL_PADDING + row * (vh + VISUAL_PADDING)
        positions.append(
            VisualPosition(
                x=x, y=y, width=vw, height=vh,
                visual_name=view.get("name", f"view_{i}"),
                visual_type=view.get("type", ""),
                z_order=i,
            )
        )

    return positions


# ---------------------------------------------------------------------------
# Auto-pagination
# ---------------------------------------------------------------------------


def paginate(
    positions: list[VisualPosition],
    max_per_page: int = MAX_VISUALS_PER_PAGE,
    canvas_height: int = DEFAULT_CANVAS_HEIGHT,
) -> list[VisualPosition]:
    """Assign page indices to visuals, splitting overflow to new pages.

    Two criteria trigger a new page:
      1. More than ``max_per_page`` visuals on the current page.
      2. A visual's bottom edge (y + height) exceeds canvas height.
    """
    if not positions:
        return positions

    page = 0
    count_on_page = 0
    y_cursor = VISUAL_PADDING
    result: list[VisualPosition] = []

    for pos in positions:
        # Smart page break: count exceeded OR visual bottom overflows canvas
        needs_new_page = (
            count_on_page >= max_per_page
            or (count_on_page > 0 and pos.y + pos.height > canvas_height)
        )
        if needs_new_page:
            page += 1
            count_on_page = 0
            y_cursor = VISUAL_PADDING

        # Re-flow: shift y to stack properly on new pages
        if pos.page_index != page or needs_new_page:
            pos = VisualPosition(
                x=pos.x,
                y=y_cursor,
                width=pos.width,
                height=pos.height,
                visual_name=pos.visual_name,
                visual_type=pos.visual_type,
                z_order=pos.z_order,
                page_index=page,
            )
        else:
            pos = VisualPosition(
                x=pos.x,
                y=pos.y,
                width=pos.width,
                height=pos.height,
                visual_name=pos.visual_name,
                visual_type=pos.visual_type,
                z_order=pos.z_order,
                page_index=page,
            )

        result.append(pos)
        count_on_page += 1
        y_cursor = max(y_cursor, pos.y + pos.height + VISUAL_PADDING)

    return result


# ---------------------------------------------------------------------------
# Full page layout
# ---------------------------------------------------------------------------


def compute_page_layouts(
    oac_page: OACPageLayout,
) -> list[PBIPage]:
    """Compute PBI page layouts from an OAC page layout.

    Returns one or more PBI pages (auto-pagination if needed).
    """
    cw = oac_page.canvas_width
    ch = oac_page.canvas_height

    # Calculate positions
    if oac_page.sections:
        positions = translate_sections(oac_page.sections, cw, ch)
    else:
        positions = translate_flat_views(oac_page.views, cw, ch)

    # Paginate
    positions = paginate(positions, canvas_height=ch)

    # Group by page
    pages_map: dict[int, list[VisualPosition]] = {}
    for pos in positions:
        pages_map.setdefault(pos.page_index, []).append(pos)

    pages: list[PBIPage] = []
    for page_idx in sorted(pages_map.keys()):
        page_name = oac_page.page_name or "Page"
        suffix = f" ({page_idx + 1})" if page_idx > 0 or len(pages_map) > 1 else ""
        pages.append(
            PBIPage(
                name=f"page_{oac_page.page_index}_{page_idx}",
                display_name=f"{page_name}{suffix}",
                page_index=oac_page.page_index * 100 + page_idx,
                width=cw,
                height=ch,
                visuals=pages_map[page_idx],
            )
        )

    logger.info(
        "Layout for '%s': %d visuals → %d page(s)",
        oac_page.page_name, len(positions), len(pages),
    )
    return pages


# ---------------------------------------------------------------------------
# Z-order / overlap detection (Phase 49)
# ---------------------------------------------------------------------------


def assign_z_order(positions: list[VisualPosition]) -> list[VisualPosition]:
    """Assign z-order to visuals based on area (smaller on top).

    Detects overlapping visuals and assigns z_order so that
    smaller visuals render on top of larger ones.

    Args:
        positions: List of visual positions

    Returns:
        Updated list with z_order assigned
    """
    # Sort by area descending — larger visuals get lower z-order
    sorted_pos = sorted(
        positions,
        key=lambda p: p.width * p.height,
        reverse=True,
    )
    for z, pos in enumerate(sorted_pos):
        pos.z_order = z

    return positions


def detect_overlaps(positions: list[VisualPosition]) -> list[tuple[str, str]]:
    """Detect pairs of overlapping visuals.

    Args:
        positions: List of visual positions

    Returns:
        List of (visual_a, visual_b) name pairs that overlap
    """
    overlaps: list[tuple[str, str]] = []
    for i, a in enumerate(positions):
        for b in positions[i + 1:]:
            if _rects_overlap(a, b):
                overlaps.append((a.visual_name, b.visual_name))
    return overlaps


def _rects_overlap(a: VisualPosition, b: VisualPosition) -> bool:
    """Check if two rectangles overlap."""
    return not (
        a.x + a.width <= b.x
        or b.x + b.width <= a.x
        or a.y + a.height <= b.y
        or b.y + b.height <= a.y
    )


# ---------------------------------------------------------------------------
# Mobile / phone layout generation (Phase 49)
# ---------------------------------------------------------------------------

PHONE_WIDTH = 360
PHONE_HEIGHT = 640
PHONE_PADDING = 4
PHONE_VISUAL_HEIGHT = 180


def generate_mobile_layout(
    visuals: list[VisualPosition],
    max_visuals: int = 10,
) -> list[VisualPosition]:
    """Generate a single-column phone layout from desktop visuals.

    Stacks visuals vertically in a mobile-friendly layout.
    Prioritizes visuals by area (larger = more important → shown first).

    Args:
        visuals: Desktop visual positions
        max_visuals: Maximum visuals in mobile view (default 10)

    Returns:
        New list of VisualPosition for mobile layout
    """
    # Prioritize by area
    ranked = sorted(
        visuals,
        key=lambda v: v.width * v.height,
        reverse=True,
    )[:max_visuals]

    mobile: list[VisualPosition] = []
    y = PHONE_PADDING
    for vpos in ranked:
        mobile.append(
            VisualPosition(
                x=PHONE_PADDING,
                y=y,
                width=PHONE_WIDTH - 2 * PHONE_PADDING,
                height=PHONE_VISUAL_HEIGHT,
                page_index=vpos.page_index,
                visual_name=vpos.visual_name,
                visual_type=vpos.visual_type,
                z_order=len(mobile),
            )
        )
        y += PHONE_VISUAL_HEIGHT + PHONE_PADDING

    logger.info("Mobile layout: %d visuals (of %d desktop)", len(mobile), len(visuals))
    return mobile
