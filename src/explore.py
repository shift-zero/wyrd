"""
wyrd — Interactive Terminal Explorer (Phase 3, Milestone 4).

Curses-based UI for scrolling, zooming, and inspecting generated worlds.
Supports arrow-key navigation, tile inspection, region overview, and lore
viewing — all in the terminal.

Usage:
    wyrd explore --seed 42        # generate + explore interactively
    wyrd explore --load world.json  # load + explore
"""

import curses
import math
from .world import World, TERRAIN, ADVENTURE_ZONE_TYPES

# ── Color palette (256-color) ─────────────────────────────────────────

PALETTE = {
    "deep_water": 27,
    "shallow": 33,
    "sand": 223,
    "grass": 28,
    "forest": 22,
    "hills": 94,
    "mountains": 130,
    "snow": 255,
    "river": 45,
}

SETTLEMENT_COLOR = 226  # bright yellow
CURSOR_COLOR = 196      # bright red
HIGHLIGHT_BG = 236      # dark grey highlight
INFO_BG = 235           # info panel background
INFO_BORDER = 240       # info panel border
HEADER_COLOR = 45       # cyan header
HELP_COLOR = 240        # muted help text
REGION_COLORS = [       # cycling region highlight colors
    28, 172, 33, 130, 99, 205,
]


def _init_colors():
    """Initialize color pairs for curses."""
    curses.init_pair(1, PALETTE["deep_water"], -1)
    curses.init_pair(2, PALETTE["shallow"], -1)
    curses.init_pair(3, PALETTE["sand"], -1)
    curses.init_pair(4, PALETTE["grass"], -1)
    curses.init_pair(5, PALETTE["forest"], -1)
    curses.init_pair(6, PALETTE["hills"], -1)
    curses.init_pair(7, PALETTE["mountains"], -1)
    curses.init_pair(8, PALETTE["snow"], -1)
    curses.init_pair(9, PALETTE["river"], -1)
    curses.init_pair(10, SETTLEMENT_COLOR, -1)  # settlement
    curses.init_pair(11, CURSOR_COLOR, -1)       # cursor
    curses.init_pair(12, -1, HIGHLIGHT_BG)       # highlighted cell
    curses.init_pair(13, INFO_BORDER, INFO_BG)   # info panel border
    curses.init_pair(14, -1, INFO_BG)            # info panel content
    curses.init_pair(15, HEADER_COLOR, -1)       # header
    curses.init_pair(16, HELP_COLOR, -1)         # help text
    # Adventure zone color pairs (17-24)
    zone_colors = [160, 250, 124, 179, 34, 196, 99, 172]  # D, C, R, T, G, L, S, M
    for i, c in enumerate(zone_colors):
        curses.init_pair(17 + i, c, -1)


def _color_pair(terrain_key: str) -> int:
    """Map terrain key to a curses color pair (1-16)."""
    pair_map = {
        "deep_water": 1,
        "shallow": 2,
        "sand": 3,
        "grass": 4,
        "forest": 5,
        "hills": 6,
        "mountains": 7,
        "snow": 8,
        "river": 9,
    }
    return pair_map.get(terrain_key, 4)


def _find_tile_info(world: World, x: int, y: int) -> dict:
    """Get all info about a tile at (x, y)."""
    if x < 0 or x >= world.width or y < 0 or y >= world.height:
        return {"terrain": "unknown", "elevation": 0, "moisture": 0}

    terrain_key = world.terrain[y][x]
    info = {
        "terrain": TERRAIN.get(terrain_key, {}).get("desc", terrain_key),
        "terrain_key": terrain_key,
        "elevation": world.elevation[y][x] if world.elevation else 0,
        "moisture": world.moisture[y][x] if world.moisture else 0,
        "settlement": None,
        "region": None,
    }

    # Find settlement at this position
    for region in world.regions:
        for s in region.settlements:
            if s.x == x and s.y == y:
                info["settlement"] = s
                info["region"] = region
                return info

    # Find adventure zone at this position
    for z in world.adventure_zones:
        if z.x == x and z.y == y:
            info["adventure_zone"] = z
            break

    # Find which region this tile belongs to (rough approximation)
    # Use nearest settlement
    best_dist = float("inf")
    best_region = None
    for region in world.regions:
        for s in region.settlements:
            dist = abs(s.x - x) + abs(s.y - y)
            if dist < best_dist:
                best_dist = dist
                best_region = region
    if best_dist < 15:
        info["region"] = best_region

    return info


# ── Views ─────────────────────────────────────────────────────────────

def _draw_map(stdscr, world: World, offset_x: int, offset_y: int,
              cursor_x: int, cursor_y: int, inspect_mode: bool,
              zoom_level: int, show_cursor: bool) -> None:
    """Draw the map tiles onto the screen."""
    max_y, max_x = stdscr.getmaxyx()
    map_area_h = max_y - 5  # leave room for header + info panel
    map_area_w = max_x - 1

    # Calculate which tiles to render based on offset and zoom
    # zoom: 1 = 1:1, 2 = 2x2 tiles per char, 3 = 3x3, etc.
    chars_per_tile = max(1, zoom_level)

    # Build a dict mapping (wx, wy) -> display char for settlements
    settlement_map = {}
    for region in world.regions:
        for s in region.settlements:
            settlement_map[(s.x, s.y)] = s.char

    for sy in range(map_area_h):
        for sx in range(map_area_w):
            # Map screen position to world position
            wx = offset_x + sx * chars_per_tile
            wy = offset_y + sy * chars_per_tile

            if wx >= world.width or wy >= world.height:
                char = " "
                color_pair = 4
            else:
                t_key = world.terrain[wy][wx]
                char = TERRAIN[t_key]["char"]
                color_pair = _color_pair(t_key)

                # Check for settlement
                if (wx, wy) in settlement_map:
                    char = settlement_map[(wx, wy)]
                    color_pair = 10

                # Check for adventure zone (if not a settlement)
                elif world.adventure_zones:
                    for z in world.adventure_zones:
                        if z.x == wx and z.y == wy:
                            char = z.char
                            # Zone color pairs: 17 + zone type index
                            zone_types = ["dungeon", "cave", "ruin", "tower", "grove", "lair", "shrine", "mine"]
                            try:
                                z_idx = zone_types.index(z.zone_type)
                                color_pair = 17 + z_idx
                            except ValueError:
                                color_pair = 11
                            break

                # Cursor highlight
                if show_cursor and wx == cursor_x and wy == cursor_y:
                    if inspect_mode:
                        color_pair = 11  # red cursor
                    else:
                        char = "█"  # solid block indicator
                        color_pair = 11

            try:
                stdscr.addch(1 + sy, sx, char, curses.color_pair(color_pair))
            except curses.error:
                pass  # off-screen


def _draw_header(stdscr, world: World, inspect_mode: bool,
                 zoom_level: int, cursor_x: int, cursor_y: int) -> None:
    """Draw the top header bar."""
    max_y, max_x = stdscr.getmaxyx()
    header = (
        f" wyrd — seed {world.seed} "
        f"[{world.width}×{world.height}] "
        f"zoom:{zoom_level}× "
        f"{'INSPECT' if inspect_mode else 'scroll'}"
    )
    try:
        stdscr.addstr(0, 0, header[:max_x - 1], curses.color_pair(15) | curses.A_BOLD)
    except curses.error:
        pass

    # Controls hint (right-aligned)
    hint = " q:quit h:help "
    try:
        stdscr.addstr(0, max_x - len(hint) - 1, hint, curses.color_pair(16))
    except curses.error:
        pass


def _draw_info_panel(stdscr, world: World, cursor_x: int, cursor_y: int,
                     inspect_mode: bool) -> None:
    """Draw the bottom info panel showing tile details."""
    max_y, max_x = stdscr.getmaxyx()
    info_y = max_y - 4

    if not inspect_mode:
        # Simple mode: just show position
        line = f" Position: ({cursor_x}, {cursor_y})  Press i to inspect tiles  "
        try:
            stdscr.addstr(info_y, 0, " " * (max_x - 1), curses.color_pair(14))
            stdscr.addstr(info_y, 0, line[:max_x - 1], curses.color_pair(14))
        except curses.error:
            pass
        return

    # Detailed inspect mode
    info = _find_tile_info(world, cursor_x, cursor_y)
    lines = []

    # Line 1: Position + Terrain
    lines.append(
        f" ({cursor_x}, {cursor_y})  "
        f"{info['terrain']}  "
        f"elev:{info['elevation']:.3f}  "
        f"moist:{info['moisture']:.3f}"
    )

    # Line 2: Settlement
    if info["settlement"]:
        s = info["settlement"]
        lines.append(
            f" {s.name} ({s.kind}, pop {s.population:,})"
        )
    else:
        lines.append(" (no settlement)")

    # Line 3: Region
    if info["region"]:
        lines.append(f" {info['region'].name} ({info['region'].biome})")
    else:
        lines.append(" (wilderness)")

    # Line 4: Adventure zone
    if info.get("adventure_zone"):
        z = info["adventure_zone"]
        z_info = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
        z_desc = z_info.get("desc", z.zone_type)
        status = "✦" if not z.is_cleared else "✓"
        lines.append(f" {z.char} {z.name} — [{z.difficulty}] {status}")
        if z.inhabitants:
            lines.append(f" {z.inhabitants}")
        if z.quest_hook:
            lines.append(f" Quest: {z.quest_hook[:60]}")

    # Draw the panel
    for i, line in enumerate(lines):
        y = info_y + i
        if y >= max_y:
            break
        try:
            stdscr.addstr(y, 0, " " * (max_x - 1), curses.color_pair(14))
            stdscr.addstr(y, 0, line[:max_x - 1], curses.color_pair(14))
        except curses.error:
            pass

    # Controls line (after info lines + 1 padding)
    ctrl_y = info_y + len(lines) + 1
    if ctrl_y < max_y:
        ctrl = " [↑↓←→/WASD] pan  [+/-] zoom  [i] inspect toggle  [r] regions  [l] lore  [z] zones  [f] factions  [b] bestiary  [q] quit  [h] help"
        try:
            stdscr.addstr(ctrl_y, 0, " " * (max_x - 1), curses.color_pair(16))
            stdscr.addstr(ctrl_y, 0, ctrl[:max_x - 1], curses.color_pair(16))
        except curses.error:
            pass


def _draw_help(stdscr) -> None:
    """Draw the help overlay."""
    max_y, max_x = stdscr.getmaxyx()
    help_lines = [
        "wyrd — Interactive Explorer  (press any key to close)",
        "",
        "  Navigation",
        "    ← → ↑ ↓  or  W A S D    Pan the map",
        "    + / =                      Zoom in",
        "    - / _                      Zoom out",
        "",
        "  Inspection",
        "    i         Toggle inspect mode (click on tiles)",
        "    r         Show region overview",
        "    l         Show lore",
        "    z         Show adventure zones",
        "    f         Show factions",
        "    b         Show bestiary",
        "",
        "  General",
        "    h / ?     Toggle this help screen",
        "    q / ESC   Quit",
        "",
        "  Tip: INSPECT mode lets you move a cursor over tiles",
        "       and see elevation, moisture, settlements, and regions.",
    ]
    # Calculate centered position
    box_h = len(help_lines) + 2
    box_w = max(len(l) for l in help_lines) + 4
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    # Draw background
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(14))
            except curses.error:
                pass

    # Draw text
    for i, line in enumerate(help_lines):
        y = start_y + 1 + i
        if y >= max_y:
            break
        try:
            if line.startswith("  ") and not line.startswith("    "):
                # Section header
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(15) | curses.A_BOLD)
            else:
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
        except curses.error:
            pass


def _draw_regions_overlay(stdscr, world: World) -> None:
    """Draw the region overview overlay."""
    max_y, max_x = stdscr.getmaxyx()

    # Build lines
    lines = ["wyrd — Regions  (press any key to close)", ""]
    for i, region in enumerate(world.regions):
        color = REGION_COLORS[i % len(REGION_COLORS)]
        settlements = ", ".join(
            f"{s.name} ({s.kind}, {s.population:,})"
            for s in region.settlements
        )
        total_pop = sum(s.population for s in region.settlements)
        lines.append(f"  {region.name}  ({region.biome}) — {len(region.settlements)} settlements, {total_pop:,} souls")
        if settlements:
            lines.append(f"    {settlements}")
        lines.append("")

    lines.append(f"  Total: {sum(len(r.settlements) for r in world.regions)} settlements | "
                  f"{sum(sum(s.population for s in r.settlements) for r in world.regions):,} souls")

    # Calculate box dimensions
    box_h = len(lines) + 2
    box_w = min(max(len(l) for l in lines) + 4, max_x - 2)
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    # Draw background
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(14))
            except curses.error:
                pass

    for i, line in enumerate(lines):
        y = start_y + 1 + i
        if y >= max_y:
            break
        try:
            if line.startswith("  ") and not line.startswith("    "):
                # Region name line
                parts = line.split("  (", 1)
                name_part = parts[0]
                rest = "  (" + parts[1] if len(parts) > 1 else ""
                stdscr.addstr(y, start_x + 2, name_part[:max_x - start_x - 2],
                              curses.color_pair(15) | curses.A_BOLD)
                if rest:
                    stdscr.addstr(y, start_x + 2 + len(name_part),
                                  rest[:max_x - start_x - 2 - len(name_part)],
                                  curses.color_pair(16))
            else:
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
        except curses.error:
            pass


def _draw_lore_overlay(stdscr, world: World) -> None:
    """Draw the lore overlay."""
    max_y, max_x = stdscr.getmaxyx()

    # Build lore text
    lines = ["wyrd — Lore  (press any key to close)", ""]
    if world.lore:
        lore = world.lore
        for region in world.regions:
            rname = region.name
            lines.append(f"  {rname}  ({region.biome})")

            # Culture
            if rname in lore.cultures:
                lines.append(f"    Culture: {lore.cultures[rname]}")
            if rname in lore.culture_descriptions:
                for desc in lore.culture_descriptions[rname]:
                    lines.append(f"      {desc}")
            # History
            if rname in lore.histories:
                lines.append(f"    History: {lore.histories[rname]}")
            lines.append("")

        # Features
        if lore.features:
            lines.append("  Notable Features:")
            for feat in lore.features[:6]:  # limit to 6 in overlay
                lines.append(f"    {feat['name']} — {feat['desc']}")
            if len(lore.features) > 6:
                lines.append(f"    ... and {len(lore.features) - 6} more")
            lines.append("")

        # Relationships (first 8)
        if lore.relationships:
            lines.append("  Relationships:")
            for rel in lore.relationships[:8]:
                lines.append(f"    {rel['description']}")
            if len(lore.relationships) > 8:
                lines.append(f"    ... and {len(lore.relationships) - 8} more")
    else:
        lines.append("  (no lore generated for this world)")

    # Box
    box_h = min(len(lines) + 2, max_y - 1)
    box_w = min(max(len(l) for l in lines) + 4, max_x - 2)
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(14))
            except curses.error:
                pass

    max_lines = min(len(lines), box_h - 1)
    for i in range(max_lines):
        y = start_y + 1 + i
        line = lines[i]
        try:
            if line.startswith("  ") and not line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(15) | curses.A_BOLD)
            elif line.startswith("      "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(16))
            elif line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
            else:
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
        except curses.error:
            pass


def _draw_zones_overlay(stdscr, world: World) -> None:
    """Draw the adventure zones overview overlay."""
    max_y, max_x = stdscr.getmaxyx()

    lines = ["wyrd — Adventure Zones  (press any key to close)", ""]
    zone_types = ["dungeon", "cave", "ruin", "tower", "grove", "lair", "shrine", "mine"]
    from .world import ADVENTURE_ZONE_TYPES

    if not world.adventure_zones:
        lines.append("  (no adventure zones generated)")
    else:
        # Group by region
        by_region: dict[str, list] = {}
        for z in world.adventure_zones:
            by_region.setdefault(z.region, []).append(z)

        for region_name in sorted(by_region.keys()):
            rzones = by_region[region_name]
            lines.append(f"  {region_name}  ({len(rzones)} zones)")
            for z in sorted(rzones, key=lambda z: z.name):
                z_info = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
                z_char = z_info.get("char", "?")
                status = "✦" if not z.is_cleared else "✓"
                lines.append(
                    f"    {z_char} {z.name}  [{z.difficulty}] {status}"
                )
                lines.append(f"      {z.description}")
                if z.inhabitants:
                    lines.append(f"      {z.inhabitants}")
                if z.quest_hook:
                    lines.append(f"      ⚑ {z.quest_hook[:55]}")
            lines.append("")

        # Summary
        total = len(world.adventure_zones)
        by_type = {}
        for z in world.adventure_zones:
            by_type[z.zone_type] = by_type.get(z.zone_type, 0) + 1
        type_summary = " · ".join(f"{ADVENTURE_ZONE_TYPES[t]['char']}×{c}" for t, c in sorted(by_type.items()))
        lines.append(f"  Total: {total} zones — {type_summary}")

    # Box
    box_h = min(len(lines) + 2, max_y - 1)
    box_w = min(max(len(l) for l in lines) + 4, max_x - 2)
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(14))
            except curses.error:
                pass

    for i, line in enumerate(lines):
        y = start_y + 1 + i
        if y >= max_y:
            break
        try:
            if line.startswith("  ") and not line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(15) | curses.A_BOLD)
            elif line.startswith("      "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(16))
            elif line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
            else:
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
        except curses.error:
            pass


def _draw_factions_overlay(stdscr, world: World) -> None:
    """Draw the factions overview overlay."""
    max_y, max_x = stdscr.getmaxyx()

    from .faction import FACTION_TYPES

    lines = ["wyrd — Factions  (press any key to close)", ""]

    if not world.factions:
        lines.append("  (no factions generated for this world)")
    else:
        sorted_factions = sorted(world.factions, key=lambda f: f.power_score, reverse=True)
        for f in sorted_factions:
            type_info = FACTION_TYPES.get(f.faction_type, {"desc": "Unknown", "icon": "?"})
            icon = type_info.get("icon", "?")
            leader = f"{f.leader_title} {f.leader_name}" if f.leader_name else "(no leader)"
            terr_str = ", ".join(f.territory) if f.territory else "(no territory)"
            lines.append(
                f"  {icon} {f.name}  [{type_info['desc']}]"
            )
            lines.append(f"    Leader: {leader}")
            lines.append(f"    Territory: {terr_str}")
            lines.append(f"    Power: {f.power_score}/300  (Inf:{f.influence}  Wlt:{f.wealth}  Mil:{f.military}  Stb:{f.stability})")
            if f.goals:
                lines.append(f"    Goal: {f.goals[0]}")
            lines.append("")

        # Relationships
        if world.faction_relationships:
            from .faction import RELATIONSHIP_ICONS
            lines.append("  Relationships:")
            for rel in world.faction_relationships[:5]:
                r_icon = RELATIONSHIP_ICONS.get(rel.rel_type, "·")
                lines.append(f"    {r_icon} {rel.description[:70]}")
            if len(world.faction_relationships) > 5:
                lines.append(f"    ... and {len(world.faction_relationships) - 5} more")

    # Box
    box_h = min(len(lines) + 2, max_y - 1)
    box_w = min(max(len(l) for l in lines) + 4, max_x - 2)
    start_y = max(0, (max_y - box_h) // 2)
    start_x = max(0, (max_x - box_w) // 2)

    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(14))
            except curses.error:
                pass

    for i, line in enumerate(lines):
        y = start_y + 1 + i
        if y >= max_y:
            break
        try:
            if line.startswith("  ") and not line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(15) | curses.A_BOLD)
            elif line.startswith("      "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(16))
            elif line.startswith("    "):
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
            else:
                stdscr.addstr(y, start_x + 2, line[:max_x - start_x - 2],
                              curses.color_pair(14))
        except curses.error:
            pass


# ── Main Explorer ─────────────────────────────────────────────────────

def _explore_curses(stdscr, world: World) -> None:
    """Main curses explorer loop."""
    # Setup
    curses.curs_set(0)  # hide cursor
    curses.use_default_colors()
    _init_colors()
    stdscr.nodelay(0)
    stdscr.keypad(True)

    # State
    offset_x = 0
    offset_y = 0
    cursor_x = 0
    cursor_y = 0
    inspect_mode = False
    zoom_level = 1
    show_help = False
    show_regions = False
    show_lore = False
    show_zones = False
    show_factions = False
    show_bestiary = False
    running = True

    while running:
        max_y, max_x = stdscr.getmaxyx()
        stdscr.clear()

        # ── Draw map ────────────────────────────────────────────────
        _draw_header(stdscr, world, inspect_mode, zoom_level,
                     cursor_x, cursor_y)
        _draw_map(stdscr, world, offset_x, offset_y,
                  cursor_x, cursor_y, inspect_mode, zoom_level,
                  show_cursor=(inspect_mode or show_help or show_regions or show_lore or show_zones or show_factions or show_bestiary))
        _draw_info_panel(stdscr, world, cursor_x, cursor_y, inspect_mode)

        # ── Overlays ────────────────────────────────────────────────
        if show_help:
            _draw_help(stdscr)
        elif show_regions:
            _draw_regions_overlay(stdscr, world)
        elif show_lore:
            _draw_lore_overlay(stdscr, world)
        elif show_zones:
            _draw_zones_overlay(stdscr, world)
        elif show_factions:
            _draw_factions_overlay(stdscr, world)
        elif show_bestiary:
            _draw_bestiary_overlay(stdscr, world)

        curses.doupdate()

        # ── Handle input ────────────────────────────────────────────
        key = stdscr.getch()

        if show_help or show_regions or show_lore or show_zones or show_factions or show_bestiary:
            # Any key dismisses overlay
            show_help = False
            show_regions = False
            show_lore = False
            show_zones = False
            show_factions = False
            show_bestiary = False
            continue

        if key == ord("q") or key == 27:  # q or ESC
            running = False

        elif key == ord("h") or key == ord("?"):
            show_help = True

        elif key == ord("r"):
            show_regions = True

        elif key == ord("l"):
            show_lore = True

        elif key == ord("z"):
            show_zones = True

        elif key == ord("f"):
            show_factions = True

        elif key == ord("b"):
            show_bestiary = True

        elif key == ord("i"):
            inspect_mode = not inspect_mode
            if inspect_mode:
                # Center cursor on screen
                cursor_x = offset_x + (max_x - 1) // 2
                cursor_y = offset_y + (max_y - 5) // 2
                # Clamp
                cursor_x = max(0, min(world.width - 1, cursor_x))
                cursor_y = max(0, min(world.height - 1, cursor_y))

        elif key == ord("+") or key == ord("="):
            zoom_level = min(5, zoom_level + 1)

        elif key == ord("-") or key == ord("_"):
            zoom_level = max(1, zoom_level - 1)

        # Arrow keys / WASD
        chars_per_tile = max(1, zoom_level)
        step = max(1, chars_per_tile)

        if key == curses.KEY_LEFT or key == ord("a"):
            if inspect_mode:
                cursor_x = max(0, cursor_x - 1)
            else:
                offset_x = max(0, offset_x - step)
        elif key == curses.KEY_RIGHT or key == ord("d"):
            if inspect_mode:
                cursor_x = min(world.width - 1, cursor_x + 1)
            else:
                offset_x = min(world.width - 1, offset_x + step)
        elif key == curses.KEY_UP or key == ord("w"):
            if inspect_mode:
                cursor_y = max(0, cursor_y - 1)
            else:
                offset_y = max(0, offset_y - step)
        elif key == curses.KEY_DOWN or key == ord("s"):
            if inspect_mode:
                cursor_y = min(world.height - 1, cursor_y + 1)
            else:
                offset_y = min(world.height - 1, offset_y + step)

        # Key repeat handling
        if key == ord("q"):
            break


def explore_world(world: World) -> None:
    """Launch the interactive explorer for a world (curses wrapper).

    Falls back to a simple print if curses isn't available.
    """
    try:
        curses.wrapper(_explore_curses, world)
    except Exception as e:
        # Fallback: print the map and a message
        from .render import render_map, render_lore
        print(render_map(world))
        print()
        print(render_lore(world))
        print()
        print(f"[Interactive explorer unavailable: {e}]")
        print("Try 'wyrd explore --seed N' in a terminal for the full experience.")
