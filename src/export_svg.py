"""
wyrd — SVG Export (Phase 3, Milestone 4).

Generate a self-contained SVG map of a generated world.
Dark-themed vector map with terrain, rivers, settlements, and lore.
"""

import math
from datetime import date
from .world import World, TERRAIN
from .render import render_brief


# ── Terrain color palette (hex) ──────────────────────────────────────

TERRAIN_COLORS = {
    "deep_water": "#005f87",
    "shallow":    "#0087af",
    "sand":       "#d7af87",
    "grass":      "#5f8700",
    "forest":     "#005f00",
    "hills":      "#875f00",
    "mountains":  "#af5f00",
    "snow":       "#e0e0e0",
    "river":      "#00afd7",
}

SETTLEMENT_COLOR = "#ffd700"
BG_COLOR = "#1a1a2e"
TEXT_COLOR = "#e0e0e0"
MUTED_COLOR = "#888888"
ACCENT_COLOR = "#e94560"


def _escape_html(text: str) -> str:
    """Escape special HTML characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _compute_viewbox(world: World, cell_size: int) -> tuple:
    """Compute viewBox dimensions: (x, y, w, h) with padding."""
    pad = 20  # padding around the map
    map_w = world.width * cell_size
    map_h = world.height * cell_size
    return -pad, -pad, map_w + pad * 2, map_h + pad * 2


def _build_terrain_tiles(world: World, cell_size: int) -> list[str]:
    """Generate SVG rects for every terrain tile."""
    elements = []
    for y in range(world.height):
        for x in range(world.width):
            t_key = world.terrain[y][x]
            color = TERRAIN_COLORS.get(t_key, "#444")
            rx = x * cell_size
            ry = y * cell_size

            # Water is rendered as a slightly rounded rect for a cleaner look
            if t_key in ("deep_water", "shallow"):
                elements.append(
                    f'  <rect x="{rx}" y="{ry}" '
                    f'width="{cell_size}" height="{cell_size}" '
                    f'fill="{color}" rx="1" />'
                )
            else:
                elements.append(
                    f'  <rect x="{rx}" y="{ry}" '
                    f'width="{cell_size}" height="{cell_size}" '
                    f'fill="{color}" />'
                )
    return elements


def _build_rivers(world: World, cell_size: int) -> list[str]:
    """Generate SVG path elements for rivers."""
    if not world.rivers:
        return []

    # Build connected segments from river coordinate list
    # Rivers are stored as flat coordinate tuples; group contiguous segments
    river_set = set(world.rivers)
    if not river_set:
        return []

    # Use the terrain grid to identify river cells and build path segments
    # We draw each river cell as a small circle for visibility
    elements = []
    for (rx, ry) in river_set:
        cx = rx * cell_size + cell_size / 2
        cy = ry * cell_size + cell_size / 2
        r = max(1.5, cell_size * 0.35)
        elements.append(
            f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" '
            f'fill="{TERRAIN_COLORS["river"]}" opacity="0.8" />'
        )
    return elements


def _build_settlements(world: World, cell_size: int) -> list[str]:
    """Generate SVG markers for settlements."""
    elements = []
    size_map = {
        "hamlet": 3,
        "village": 4,
        "town": 5,
        "city": 7,
    }

    for region in world.regions:
        for s in region.settlements:
            cx = s.x * cell_size + cell_size / 2
            cy = s.y * cell_size + cell_size / 2
            r = size_map.get(s.kind, 4)

            # Glow effect for larger settlements
            if s.kind in ("town", "city"):
                elements.append(
                    f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 3}" '
                    f'fill="{SETTLEMENT_COLOR}" opacity="0.2" />'
                )

            elements.append(
                f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" '
                f'fill="{SETTLEMENT_COLOR}" stroke="#fff" '
                f'stroke-width="0.5" />'
            )

            # Label for towns and cities
            if s.kind in ("town", "city"):
                elements.append(
                    f'  <text x="{cx + r + 2:.1f}" y="{cy + 3:.1f}" '
                    f'fill="{SETTLEMENT_COLOR}" '
                    f'font-size="{max(8, cell_size)}" '
                    f'font-family="sans-serif">'
                    f'{_escape_html(s.name)}</text>'
                )

    return elements


def _build_legend(world: World, cell_size: int) -> list[str]:
    """Generate the legend as SVG elements."""
    lines = []
    y_offset = 10
    x = 10

    lines.append(
        f'<text x="{x}" y="{y_offset}" fill="{ACCENT_COLOR}" '
        f'font-size="12" font-weight="bold" font-family="sans-serif">'
        f'Legend</text>'
    )
    y_offset += 20

    for t_key, info in TERRAIN.items():
        color = TERRAIN_COLORS.get(t_key, "#444")
        lines.append(
            f'<rect x="{x}" y="{y_offset - 8}" width="12" height="12" '
            f'fill="{color}" rx="1" />'
        )
        lines.append(
            f'<text x="{x + 18}" y="{y_offset + 2}" fill="{TEXT_COLOR}" '
            f'font-size="10" font-family="sans-serif">'
            f'{_escape_html(info["desc"])}</text>'
        )
        y_offset += 16

    # Settlement legend
    lines.append(
        f'<circle cx="{x + 6}" cy="{y_offset - 4}" r="4" '
        f'fill="{SETTLEMENT_COLOR}" />'
    )
    lines.append(
        f'<text x="{x + 18}" y="{y_offset}" fill="{TEXT_COLOR}" '
        f'font-size="10" font-family="sans-serif">'
        f'Settlement (● town ◉ city ∘ village · hamlet)</text>'
    )

    return lines


def _build_regions_list(world: World) -> list[str]:
    """Generate the regions listing as SVG text elements."""
    lines = []
    y_offset = 10

    lines.append(
        f'<text x="10" y="{y_offset}" fill="{ACCENT_COLOR}" '
        f'font-size="12" font-weight="bold" font-family="sans-serif">'
        f'Regions</text>'
    )
    y_offset += 20

    for region in world.regions:
        settlements = ", ".join(
            f"{s.name} ({s.kind})" for s in region.settlements
        )
        lines.append(
            f'<text x="10" y="{y_offset}" fill="{SETTLEMENT_COLOR}" '
            f'font-size="11" font-weight="bold" font-family="sans-serif">'
            f'{_escape_html(region.name)}</text>'
        )
        y_offset += 14
        lines.append(
            f'<text x="14" y="{y_offset}" fill="{MUTED_COLOR}" '
            f'font-size="10" font-family="sans-serif">'
            f'{_escape_html(settlements)}</text>'
        )
        y_offset += 18

    return lines


def _build_lore_text(world: World) -> list[str]:
    """Generate lore text as SVG elements."""
    if not world.lore:
        return []

    lines = []
    y_offset = 10

    lines.append(
        f'<text x="10" y="{y_offset}" fill="{ACCENT_COLOR}" '
        f'font-size="12" font-weight="bold" font-family="sans-serif">'
        f'Lore</text>'
    )
    y_offset += 20

    lore = world.lore

    # Historical snippets
    for region in world.regions:
        rname = region.name
        if rname in lore.histories:
            history = lore.histories[rname][:200]  # truncate for SVG
            lines.append(
                f'<text x="10" y="{y_offset}" fill="{SETTLEMENT_COLOR}" '
                f'font-size="10" font-weight="bold" '
                f'font-family="sans-serif">'
                f'{_escape_html(rname)} — History</text>'
            )
            y_offset += 13
            lines.append(
                f'<text x="14" y="{y_offset}" fill="{TEXT_COLOR}" '
                f'font-size="9" font-family="sans-serif">'
                f'{_escape_html(history)}...</text>'
            )
            y_offset += 16

    # Notable features
    if lore.features:
        lines.append(
            f'<text x="10" y="{y_offset}" fill="{MUTED_COLOR}" '
            f'font-size="10" font-weight="bold" '
            f'font-family="sans-serif">Features</text>'
        )
        y_offset += 13
        for feat in lore.features[:5]:
            lines.append(
                f'<text x="14" y="{y_offset}" fill="{TEXT_COLOR}" '
                f'font-size="9" font-family="sans-serif">'
                f'• {_escape_html(feat["name"])}</text>'
            )
            y_offset += 12

    return lines


def export_world_svg(world: World, cell_size: int = 6) -> str:
    """
    Export a world as a self-contained SVG document.

    Args:
        world: A generated World object.
        cell_size: Pixel size of each terrain tile (default: 6).

    Returns:
        SVG document as a string.
    """
    # Compute layout
    map_w_px = world.width * cell_size
    map_h_px = world.height * cell_size

    # Side panel width for legend + regions + lore
    panel_w = 300

    # Total canvas
    total_w = map_w_px + panel_w + 40  # 20px padding on each side
    total_h = max(map_h_px + 40, 400)

    brief = render_brief(world)
    today = date.today().isoformat()

    # Build SVG parts
    terrain_elements = _build_terrain_tiles(world, cell_size)
    river_elements = _build_rivers(world, cell_size)
    settlement_elements = _build_settlements(world, cell_size)
    legend_elements = _build_legend(world, cell_size)
    regions_elements = _build_regions_list(world)
    lore_elements = _build_lore_text(world)

    terrain_group = "\n".join(terrain_elements)
    river_group = "\n".join(river_elements)
    settlement_group = "\n".join(settlement_elements)
    legend_group = "\n".join(legend_elements)
    regions_group = "\n".join(regions_elements)
    lore_group = "\n".join(lore_elements)

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="0 0 {total_w} {total_h}"
     width="100%" height="100%"
     style="background-color: {BG_COLOR};">

  <defs>
    <filter id="glow">
      <feGaussianBlur stdDeviation="1.5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <!-- Title -->
  <text x="20" y="20" fill="{ACCENT_COLOR}"
        font-size="16" font-weight="bold" font-family="sans-serif">
    wyrd — Seed {world.seed}
  </text>
  <text x="20" y="36" fill="{MUTED_COLOR}"
        font-size="11" font-family="sans-serif">
    {_escape_html(brief)}  |  {today}
  </text>

  <!-- Map area -->
  <g transform="translate(20, 50)">
    <!-- Terrain tiles -->
    {terrain_group}

    <!-- Rivers (drawn on top of terrain) -->
    {river_group}

    <!-- Settlements (drawn on top of everything) -->
    {settlement_group}

    <!-- Map border -->
    <rect x="{-1}" y="{-1}"
          width="{map_w_px + 2}" height="{map_h_px + 2}"
          fill="none" stroke="#333" stroke-width="1" />
  </g>

  <!-- Side panel -->
  <g transform="translate({map_w_px + 40}, 50)">
    {legend_group}

    <text x="10" y="{10 + (len(TERRAIN) + 2) * 16 + 20}"
          fill="{MUTED_COLOR}" font-size="9" font-family="sans-serif"
          dx="0" dy="0">
    </text>

    <!-- Regions -->
    <g transform="translate(0, {(len(TERRAIN) + 3) * 16 + 30})">
      {regions_group}
    </g>

    <!-- Lore -->
    <g transform="translate(0, {(len(TERRAIN) + 3) * 16 + len(world.regions) * 18 + 50})">
      {lore_group}
    </g>
  </g>

  <!-- Footer -->
  <text x="20" y="{total_h - 10}" fill="{MUTED_COLOR}"
        font-size="9" font-family="sans-serif" text-anchor="start">
    Generated by wyrd — github.com/shift-zero/wyrd
  </text>
</svg>"""

    return svg
