"""wyrd — Gateway TUI (Phase 15: The Weirding).

The unified curses interface. Run `wyrd` with no subcommand to enter here.
From the gateway you can:
  - List & select recently generated worlds
  - Generate a new world
  - Load a world from file
  - Enter explore, viewer, or any other view
  - Press ? for help from anywhere
"""

import curses
import glob
import json
import locale
import os
import random
import re
import time as time_module

from .world import TERRAIN, World
from .generate import generate_world
from .serialize import load_world

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return ANSI_RE.sub('', text)

CP = {
    "title": 1,
    "accent": 2,
    "dim": 3,
    "normal": 4,
    "highlight": 5,
    "border": 6,
    "error": 7,
    "warning": 8,
    "seed": 9,
    "badge_l": 10,
    "badge_n": 11,
    "badge_c": 12,
    "badge_s": 13,
    "badge_m": 14,
    "badge_p": 15,  # Player/saved character
    "info": 16,     # Stats info text
}


# ── ASCII splash ─────────────────────────────────────────────────────

SPLASH = [
    "",
    "       ▄████████  ▄█   ▄█          ▄████████ ████████▄ ",
    "      ███    ███ ███  ███         ███    ███ ███   ▀███",
    "      ███    █▀  ███▌ ███         ███    ███ ███    ███",
    "      ███        ███▌ ███        ▄███▄▄▄▄██▀ ███    ███",
    "    ▀███████████ ███▌ ███       ▀▀███▀▀▀▀▀   ███    ███",
    "             ███ ███  ███         ███    ███ ███    ███",
    "       ▄█    ███ ███  ███▌    ▄   ███    ███ ███   ▄███",
    "     ▄████████▀  █▀   █████▄▄██   ██████████ ████████▀ ",
    "                     ▀           ▀                     ",
    "━━━ generative fantasy sandbox ━━━",
    "",
]


def _init_colors():
    """Initialize curses colour pairs for the gateway."""
    curses.init_pair(CP["title"], 45, -1)      # cyan
    curses.init_pair(CP["accent"], 46, -1)     # green
    curses.init_pair(CP["dim"], 240, -1)       # grey
    curses.init_pair(CP["normal"], -1, -1)     # default
    curses.init_pair(CP["highlight"], -1, 236)  # dark grey bg
    curses.init_pair(CP["border"], 242, -1)    # border grey
    curses.init_pair(CP["error"], 196, -1)     # red
    curses.init_pair(CP["warning"], 226, -1)   # yellow
    curses.init_pair(CP["seed"], 99, -1)       # magenta
    curses.init_pair(CP["badge_l"], 28, -1)    # green
    curses.init_pair(CP["badge_n"], 33, -1)    # blue
    curses.init_pair(CP["badge_c"], 226, -1)   # yellow
    curses.init_pair(CP["badge_s"], 196, -1)   # red
    curses.init_pair(CP["badge_m"], 99, -1)    # magenta
    curses.init_pair(CP["badge_p"], 220, -1)   # gold — player/saved character
    # Pairs 16-27: mini-map terrain colors
    curses.init_pair(16, 27, -1)    # deep_water
    curses.init_pair(17, 33, -1)    # shallow
    curses.init_pair(18, 223, -1)   # sand
    curses.init_pair(19, 28, -1)    # grass
    curses.init_pair(20, 22, -1)    # forest
    curses.init_pair(21, 94, -1)    # hills
    curses.init_pair(22, 130, -1)   # mountains
    curses.init_pair(23, 255, -1)   # snow
    curses.init_pair(24, 45, -1)    # river
    curses.init_pair(25, 226, -1)   # settlement
    curses.init_pair(26, 64, -1)    # swamp
    curses.init_pair(27, 179, -1)   # desert
    # Pairs 28-34: trade route overlay colors
    curses.init_pair(28, 226, -1)   # route_trade / settlement (yellow)
    curses.init_pair(29, 220, -1)   # route_road (gold)
    curses.init_pair(30, 220, -1)   # economy_farming (gold)
    curses.init_pair(31, 28, -1)    # economy_logging (green)
    curses.init_pair(32, 130, -1)   # economy_mining (brown)
    curses.init_pair(33, 33, -1)    # economy_fishing (blue)
    curses.init_pair(34, 40, -1)    # economy_pastoral (lime)


_MINI_TERRAIN_CP = {
    "deep_water": 16, "shallow": 17, "sand": 18, "grass": 19,
    "forest": 20, "hills": 21, "mountains": 22, "snow": 23,
    "river": 24, "swamp": 26, "desert": 27,
}

_ROUTE_CP = {
    "trading": 28,    # yellow
    "farming": 30,    # gold
    "logging": 31,    # green
    "mining": 32,     # brown
    "fishing": 33,    # blue
    "pastoral": 34,   # lime
}

_ROUTE_ICONS = {
    "trading": "$", "farming": "W", "logging": "T",
    "mining": "&", "fishing": "~", "pastoral": "P",
}


def _draw(stdscr, y, x, text, cp, bold=False):
    h, w = stdscr.getmaxyx()
    if y >= h or y < 0 or x >= w:
        return
    style = curses.color_pair(cp) | (curses.A_BOLD if bold else 0)
    try:
        stdscr.addstr(y, x, text[:max(0, w - x - 1)], style)
    except curses.error:
        pass


def _fill_line(stdscr, y, cp):
    h, w = stdscr.getmaxyx()
    if y >= h or y < 0:
        return
    try:
        stdscr.addstr(y, 0, " " * w, curses.color_pair(cp))
    except curses.error:
        pass


# ── World scanning ─────────────────────────────────────────────────────

def scan_worlds(search_dir: str = ".") -> list[dict]:
    """Scan for wyrd world files and return metadata list."""
    pattern = os.path.join(search_dir, "wyrd-*.json")
    world_files = sorted(glob.glob(pattern))
    world_files = [
        wf for wf in world_files
        if not re.search(r'-sim\.json', wf)
        and not re.search(r'-chronicles\.html', wf)
        and not re.search(r'\.ttrpg\.json', wf)
    ]

    results = []
    for wf in world_files:
        try:
            with open(wf) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        seed = data.get("seed", 0)
        results.append({
            "seed": seed,
            "file": os.path.basename(wf),
            "path": wf,
            "dimensions": f'{data.get("width", 0)}x{data.get("height", 0)}',
            "regions": len(data.get("regions", [])),
            "population": sum(
                s.get("population", 0)
                for r in data.get("regions", [])
                for s in r.get("settlements", [])
            ),
            "has_lore": "lore" in data and data["lore"] is not None,
            "has_narrative": "narrative" in data and data["narrative"] is not None,
            "has_chronicles": "chronicles" in data and data["chronicles"] is not None,
            "has_magic": "magic" in data and data["magic"] is not None,
            "has_save": os.path.exists(f"wyrd-{seed}-char.json"),
        })
    return results


def _has_sim_file(seed: int) -> bool:
    """Check if a sim file exists for the given seed."""
    return any(
        os.path.exists(f) for f in [
            f"wyrd-{seed}-sim.json",
            f"wyrd-{seed}-sim.json.gz",
        ]
    )


# ── Help panels ─────────────────────────────────────────────────────────

GATEWAY_HELP = [
    "wyrd — Gateway Help  (press any key to close)",
    "",
    "  Navigation",
    "    ↑ ↓ / k j         Move selection up/down",
    "    Enter / Space      Select highlighted item (load world)",
    "",
    "  Actions",
    "    g                  Generate a new world",
    "    l                  Load world from JSON file",
    "    e                  Explore selected world (interactive map)",
    "    v                  View sim evolution (watch world grow)",
    "    p                  Play — embodied mode (live as a character)",
    "    d                  Describe / show lore for world",
    "    c                  Show chronicles (history)",
    "    s                  Run simulation (year-by-year text)",
    "    x                  Export world to HTML",
    "    t                  Show trade route map",
    "    r                  Refresh the world list",
    "",
    "  General",
    "    ? / h              Toggle this help screen",
    "    q / ESC            Quit wyrd",
    "",
    "  Gazetteer",
    "    G                  Open gazetteer — browse all entities",
    "",
    "  Tip: Select a world and press 'e' to explore its terrain.",
    "       Press 'v' to watch centuries pass in real-time.",
]


def draw_help_panel(stdscr, lines: list[str]):
    """Draw a generic help/overlay box centered on screen."""
    h, w = stdscr.getmaxyx()
    box_h = min(len(lines) + 2, h - 1)
    box_w = min(max(len(l) for l in lines) + 4, w - 2)
    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(CP["border"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(CP["normal"]))
            except curses.error:
                pass

    for i, line in enumerate(lines):
        y = start_y + 1 + i
        if y >= h:
            break
        if not line:
            continue
        if line.startswith("  ") and not line.startswith("    "):
            _draw(stdscr, y, start_x + 2, line, CP["accent"], bold=True)
        elif line.startswith("    "):
            _draw(stdscr, y, start_x + 2, line, CP["normal"])
        else:
            _draw(stdscr, y, start_x + 2, line, CP["title"], bold=True)


# ── World detail card helpers (Phase 21) ─────────────────────────────────


def _load_world_for_detail(path: str) -> dict | None:
    """Load world data for the detail card. Returns cached metadata + terrain."""
    try:
        with open(path) as f:
            data = json.load(f)
        w = data.get("width", 0)
        h = data.get("height", 0)
        terrain = data.get("terrain", [])
        regions = data.get("regions", [])
        total_pop = sum(
            s.get("population", 0)
            for r in regions
            for s in r.get("settlements", [])
        )
        total_settlements = sum(
            len(r.get("settlements", []))
            for r in regions
        )
        # Count feature flags
        features = []
        if data.get("lore"): features.append("📜 Lore")
        if data.get("narrative"): features.append("🎭 Narrative")
        if data.get("chronicles"): features.append("📖 Chronicles")
        if data.get("magic"): features.append("🔮 Magic")
        if data.get("pantheon"): features.append("⛪ Pantheon")
        if data.get("factions"): features.append("🏴 Factions")
        if data.get("bestiary"): features.append("🐾 Bestiary")
        if data.get("adventure_zones"): features.append("⚔ Zones")
        return {
            "seed": data.get("seed", 0),
            "terrain": terrain,
            "width": w,
            "height": h,
            "regions_count": len(regions),
            "settlements_count": total_settlements,
            "total_population": total_pop,
            "features": features,
            "has_landmarks": bool(data.get("landmarks")),
        }
    except Exception:
        return None


def _render_mini_map(stdscr, terrain: list[list[str]],
                     detail_y: int, detail_x: int,
                     max_h: int, max_w: int) -> int:
    """Render a mini ASCII terrain map at (detail_y, detail_x).

    Scales the full terrain to fit within max_h x max_w.
    Returns the number of rows actually rendered.
    """
    if not terrain or not terrain[0]:
        return 0

    full_h = len(terrain)
    full_w = len(terrain[0])
    map_h = min(max_h, full_h)
    map_w = min(max_w, full_w)

    # Sampling step to scale down if needed
    step_y = max(1, full_h // map_h) if full_h > map_h else 1
    step_x = max(1, full_w // map_w) if full_w > map_w else 1

    rendered_rows = 0
    for ty in range(0, full_h, step_y):
        if rendered_rows >= map_h:
            break
        row = ""
        colors = []
        for tx in range(0, full_w, step_x):
            t = terrain[ty][tx]
            ch = TERRAIN.get(t, {}).get("char", " ")
            cp = _MINI_TERRAIN_CP.get(t, 19)
            row += ch
            colors.append(cp)
        # Trim to fit
        if len(row) > map_w:
            row = row[:map_w]
            colors = colors[:map_w]
        # Draw the row
        for ci, ch in enumerate(row):
            try:
                stdscr.addch(detail_y + rendered_rows, detail_x + ci, ch,
                             curses.color_pair(colors[ci]))
            except curses.error:
                break
        rendered_rows += 1
    return rendered_rows


def _draw_world_detail_panel(stdscr, data: dict | None,
                              start_y: int, start_x: int,
                              max_h: int, max_w: int):
    """Draw a world detail card with mini-map and stats."""
    if not data:
        return

    # ── Frame ────────────────────────────────────────────────────────
    map_w = min(30, max_w - 2)
    map_h = min(12, max_h - 6)

    # Draw a border around the detail card
    card_h = map_h + 7 + max(0, len(data.get("features", [])) - 2)
    card_h = min(card_h, max_h)
    card_w = map_w + 4
    card_w = min(card_w, max_w)

    for y in range(card_h):
        for x in range(card_w):
            try:
                if y == 0 or y == card_h - 1 or x == 0 or x == card_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(CP["border"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(CP["normal"]))
            except curses.error:
                pass

    # ── Title ─────────────────────────────────────────────────────────
    title = f" wyrd #{data['seed']} "
    _draw(stdscr, start_y + 1, start_x + 2, title,
          CP["seed"], bold=True)
    _draw(stdscr, start_y + 1, start_x + 2 + len(title),
          f"({data['width']}×{data['height']})",
          CP["dim"])

    # ── Mini-map ──────────────────────────────────────────────────────
    rows = _render_mini_map(stdscr, data["terrain"],
                            start_y + 2, start_x + 2,
                            map_h, map_w)

    # ── Stats ─────────────────────────────────────────────────────────
    stats_y = start_y + 2 + rows + 1
    pop_str = f"{data['total_population']:,}" if data['total_population'] else "—"
    _draw(stdscr, stats_y, start_x + 2,
          f"  🏘 {data['settlements_count']} settlements  👥 {pop_str} souls  🌍 {data['regions_count']} regions",
          CP["info"])

    # ── Features list ─────────────────────────────────────────────────
    feat_y = stats_y + 1
    if data.get("features"):
        feat_str = "  " + " ".join(data["features"][:6])
        _draw(stdscr, feat_y, start_x + 2, feat_str, CP["accent"])



# ── Trade route curses overlay (Phase 23.5) ────────────────────────────

def _trade_routes_curses_overlay(stdscr, world):
    """Show trade route map as a full-screen curses overlay. No endwin needed."""
    h, w = stdscr.getmaxyx()

    # ── Run sim to get trade routes ────────────────────────────
    msg = " Simulating trade routes… "
    _draw(stdscr, h // 2, max(0, (w - len(msg)) // 2), msg, CP["accent"])
    stdscr.refresh()

    from .sim import run_simulation
    from .serialize import save_sim_state
    from .economy import reconstruct_routes
    sim_chars = world.narrative.characters if world.narrative else None
    result = run_simulation(world, num_years=100, seed_offset=0,
                            chaos_factor=0.1, snapshot_interval=50,
                            characters=sim_chars)
    save_sim_state(result, f"wyrd-{world.seed}-sim.json")
    routes = reconstruct_routes(result.trade_routes)

    # ── Build settlement lookup ─────────────────────────────────
    s_info: dict[str, tuple[int, int, str]] = {}
    for name, snap in result.settlements.items():
        s_info[name] = (snap.x, snap.y, getattr(snap, 'economy_type', None) or "unknown")

    connected: set[str] = set()
    for r in routes:
        if getattr(r, 'is_active', True):
            connected.add(getattr(r, 'source', ''))
            connected.add(getattr(r, 'destination', ''))

    # ── Build terrain grid with TERRAIN char + CP mapping ───────
    grid_chars: list[list[str]] = []
    grid_cp: list[list[int]] = []
    for y in range(world.height):
        rc: list[str] = []
        rcp: list[int] = []
        for x in range(world.width):
            tk = world.terrain[y][x]
            info = TERRAIN.get(tk, {"char": "?", "color": 240})
            rc.append(info["char"])
            rcp.append(_MINI_TERRAIN_CP.get(tk, 19))
        grid_chars.append(rc)
        grid_cp.append(rcp)

    # ── Overlay settlements with economy icons ──────────────────
    settlement_positions: set[tuple[int, int]] = set()
    for region in world.regions:
        for s in region.settlements:
            settlement_positions.add((s.x, s.y))
            if 0 <= s.y < world.height and 0 <= s.x < world.width:
                if s.name in connected and s.name in s_info:
                    _, _, etype = s_info[s.name]
                    icon = _ROUTE_ICONS.get(etype, "S")
                    grid_chars[s.y][s.x] = icon
                    grid_cp[s.y][s.x] = _ROUTE_CP.get(etype, 28)
                else:
                    grid_chars[s.y][s.x] = s.char
                    grid_cp[s.y][s.x] = 28  # yellow

    # ── Draw route lines (Bresenham dots, skip water & settlements) ─
    route_layer: dict[tuple[int, int], tuple[int, str]] = {}
    for r in routes:
        if not getattr(r, 'is_active', True):
            continue
        src = getattr(r, 'source', '')
        dst = getattr(r, 'destination', '')
        if src not in s_info or dst not in s_info:
            continue
        sx, sy, stype = s_info[src]
        dx, dy, dtype = s_info[dst]
        etype = stype if stype in _ROUTE_CP else (dtype if dtype in _ROUTE_CP else "trading")
        dot_cp = _ROUTE_CP.get(etype, 28)
        is_road = getattr(r, 'is_road', False)
        dot_char = "=" if is_road else "·"

        for px, py in _bresenham_line(sx, sy, dx, dy):
            if (px, py) in [(sx, sy), (dx, dy)]:
                continue
            if 0 <= py < world.height and 0 <= px < world.width:
                tk = world.terrain[py][px]
                if tk in ("deep_water", "shallow", "ocean"):
                    continue
                clr = 29 if is_road else dot_cp
                if (px, py) not in settlement_positions:
                    route_layer[(px, py)] = (clr, dot_char)

    for (x, y), (clr, ch) in route_layer.items():
        if 0 <= y < world.height and 0 <= x < world.width:
            grid_chars[y][x] = ch
            grid_cp[y][x] = clr

    # ── Build legend + route listing ────────────────────────────
    title = f" wyrd #{world.seed} — Trade Routes (Year {result.year}) "
    subtitle = f" {world.width}×{world.height} | {sum(1 for r in routes if getattr(r, 'is_active', True))} active routes "
    legend_lines = []
    legend_lines.append(("", 0, False))
    seen_types: set[str] = set()
    for r in routes:
        for name in (getattr(r, 'source', ''), getattr(r, 'destination', '')):
            if name in s_info:
                et = s_info[name][2]
                if et in _ROUTE_ICONS:
                    seen_types.add(et)
    if seen_types:
        legend_lines.append((" Economy Types:", CP["title"], True))
        for etype in ["farming", "logging", "mining", "fishing", "trading", "pastoral"]:
            if etype in seen_types:
                icon = _ROUTE_ICONS[etype]
                cp = _ROUTE_CP[etype]
                legend_lines.append((f"  {icon}  {etype}", cp, False))
        legend_lines.append(("  ·  Trade route path", 28, False))
        legend_lines.append(("  =  Road (persistent route, 50+ years)", 29, False))
        legend_lines.append(("", 0, False))

    # Route listings (top 20)
    active = [r for r in routes if getattr(r, 'is_active', True)]
    if active:
        legend_lines.append((" Active Routes:", CP["title"], True))
        for r in active[:20]:
            src = getattr(r, 'source', '?')
            dst = getattr(r, 'destination', '?')
            st = s_info.get(src, ("?", "?", "?"))[2]
            dt = s_info.get(dst, ("?", "?", "?"))[2]
            si = _ROUTE_ICONS.get(st, "?")
            di = _ROUTE_ICONS.get(dt, "?")
            sicp = _ROUTE_CP.get(st, 28)
            dicp = _ROUTE_CP.get(dt, 28)
            road_flag = " =road" if getattr(r, 'is_road', False) else ""
            legend_lines.append((f"  {si} {src} ↔ {di} {dst}{road_flag}", CP["normal"], False))
            goods_str = getattr(r, 'goods', 'goods')
            vol = getattr(r, 'volume', 0.5)
            dist = getattr(r, 'distance', 0)
            legend_lines.append((f"    {goods_str}  (vol: {vol:.0%}, dist: {dist:.0f})", CP["dim"], False))
        if len(active) > 20:
            legend_lines.append((f"  … and {len(active) - 20} more", CP["dim"], False))

    pad_total_h = 1 + 1 + 1 + world.height + len(legend_lines) + 2

    # ── Event loop ─────────────────────────────────────────────
    scroll_y = 0
    running = True
    while running:
        stdscr.erase()

        # Title bar
        _draw(stdscr, 0, 0, title, CP["seed"], bold=True)
        _draw(stdscr, 1, 0, subtitle, CP["dim"])

        # Map viewport
        view_h = h - 3  # leave room for footer
        
        # Draw map rows
        map_row = 0
        while map_row < world.height and map_row < view_h:
            sy = scroll_y + map_row
            if sy >= world.height:
                break
            line = ""
            col_cps: list[int] = []
            for x in range(min(world.width, w - 1)):
                line += grid_chars[sy][x]
                col_cps.append(grid_cp[sy][x])
            # Draw with correct colors
            try:
                for ci, ch in enumerate(line):
                    if map_row + 2 < h and ci < w:
                        stdscr.addch(map_row + 2, ci, ch, curses.color_pair(col_cps[ci]) | curses.A_BOLD)
            except curses.error:
                pass
            map_row += 1

        # Legend below map
        legend_start = min(map_row + 2, h - 1)
        legend_y = legend_start
        li = scroll_y - world.height
        if li < 0:
            li = 0
        while li < len(legend_lines) and legend_y < h - 1:
            text, cp, bold = legend_lines[li]
            _draw(stdscr, legend_y, 0, text, cp, bold=bold)
            legend_y += 1
            li += 1

        # Footer
        footer = " ↑↓ scroll | q/ESC close "
        _draw(stdscr, h - 1, max(0, (w - len(footer)) // 2), footer, CP["dim"])
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27, ord('\n')):
            running = False
        elif key == curses.KEY_DOWN:
            scroll_y = min(scroll_y + 1, max(0, pad_total_h - view_h))
        elif key == curses.KEY_UP:
            scroll_y = max(0, scroll_y - 1)
        elif key == curses.KEY_NPAGE:
            scroll_y = min(scroll_y + view_h, max(0, pad_total_h - view_h))
        elif key == curses.KEY_PPAGE:
            scroll_y = max(0, scroll_y - view_h)
        elif key == ord('g'):  # top
            scroll_y = 0
        elif key == ord('G'):  # bottom
            scroll_y = max(0, pad_total_h - view_h)


def _bresenham_line(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Bresenham's line algorithm — returns points on the line."""
    points: list[tuple[int, int]] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return points


# ── Sub-view launchers (end/restart curses) ────────────────────────────

def _launch_terminal_view(stdscr, title: str, render_fn, *args, **kwargs):
    """Launch a terminal-only view: end curses, print output, wait for key."""
    curses.endwin()
    text = render_fn(*args, **kwargs)
    print(text)
    input(f"\n── {title} ── Press Enter to return to wyrd gateway...")
    # Restart curses for the gateway
    stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    _init_colors()
    stdscr.keypad(True)
    curses.curs_set(0)
    return stdscr


def _launch_curses_view(stdscr, title: str, view_fn, *args, **kwargs):
    """Launch a curses sub-view: end gateway curses, run view, restart curses.

    The view function is expected to call its own curses.wrapper() internally.
    We just end the gateway's curses session, let the view run, then restart.
    """
    curses.endwin()
    try:
        view_fn(*args, **kwargs)
    except Exception:
        pass
    # Restart curses for the gateway
    new_stdscr = curses.initscr()
    curses.start_color()
    curses.use_default_colors()
    _init_colors()
    new_stdscr.keypad(True)
    curses.curs_set(0)
    return new_stdscr


def _resolve_world(world_in_session, sorted_worlds, selected_idx):
    """Resolve a world reference — from session state, or by loading the selected world.

    Returns (world | None, error_msg | None).
    """
    world = world_in_session
    if world is None and sorted_worlds and 0 <= selected_idx < len(sorted_worlds):
        try:
            from .serialize import load_world
            world = load_world(sorted_worlds[selected_idx]["path"])
        except Exception:
            return None, "Could not load world"
    if world is None:
        return None, "No world loaded — generate or select one first"
    return world, None


# ── Gazetteer mode (Phase 20 — Living Gazetteer) ──────────────────────


def _collect_gazetteer_entities(world) -> list[dict]:
    """Collect all entities from a world into a unified gazetteer list."""
    entities = []

    # 1. Settlements (from world regions)
    for region in world.regions:
        for s in region.settlements:
            entities.append({
                "type": "settlement",
                "name": s.name,
                "subtitle": f"{s.kind.title()} in {region.name} — Pop {s.population:,}",
                "detail_lines": [
                    f"  Kind:       {s.kind.title()}",
                    f"  Region:     {region.name}",
                    f"  Population: {s.population:,}",
                    f"  Position:   ({s.x}, {s.y})",
                ],
                "badge_color": CP["badge_l"],
                "badge": "S",
                "sort_key": f"settlement_{s.name.lower()}",
            })

    # 2. Characters (from world.narrative)
    if world.narrative and world.narrative.characters:
        for c in world.narrative.characters:
            status_icon = "✓" if c.status == "alive" else "✗"
            entities.append({
                "type": "character",
                "name": c.full_name,
                "subtitle": f"{c.occupation.title()} from {c.home_settlement} — {c.status}",
                "detail_lines": [
                    f"  Name:       {c.full_name}",
                    f"  Occupation: {c.occupation.title()}",
                    f"  Home:       {c.home_settlement}, {c.home_region}",
                    f"  Age:        {c.age}",
                    f"  Traits:     {', '.join(c.personality_traits)}",
                    f"  Status:     {c.status}",
                    f"  Backstory:  {c.backstory[:200]}",
                ],
                "badge_color": CP["badge_n"],
                "badge": "C",
                "sort_key": f"character_{c.surname.lower()}_{c.name.lower()}",
            })

    # 3. Factions
    if world.factions:
        for f in world.factions:
            power = f.power_score
            entities.append({
                "type": "faction",
                "name": f.name,
                "subtitle": f"{f.faction_type.replace('_', ' ').title()} — Power {power} — {f.reputation}",
                "detail_lines": [
                    f"  Type:       {f.faction_type.replace('_', ' ').title()}",
                    f"  Leader:     {f.leader_title} {f.leader_name}",
                    f"  Reputation: {f.reputation}",
                    f"  Power:      {power}/300  (Inf {f.influence} + Wel {f.wealth} + Mil {f.military})",
                    f"  Stability:  {f.stability}/100",
                    f"  Territory:  {', '.join(f.territory) if f.territory else 'None'}",
                    f"  Goals:      {'; '.join(f.goals[:3])}",
                    f"  {f.description}",
                ],
                "badge_color": CP["accent"],
                "badge": "F",
                "sort_key": f"faction_{f.name.lower()}",
            })

        # Relationships
        if world.faction_relationships:
            for rel in world.faction_relationships:
                entities.append({
                    "type": "faction_rel",
                    "name": f"{rel.faction_a} ↔ {rel.faction_b}",
                    "subtitle": f"Relationship: {rel.rel_type.replace('_', ' ').title()}",
                    "detail_lines": [
                        f"  {rel.faction_a} ↔ {rel.faction_b}",
                        f"  Type: {rel.rel_type.replace('_', ' ').title()}",
                        f"  {rel.description}",
                    ],
                    "badge_color": CP["badge_p"],
                    "badge": "R",
                    "sort_key": f"faction_rel_{rel.faction_a.lower()}_{rel.faction_b.lower()}",
                })

    # 4. Creatures (bestiary)
    if world.bestiary:
        for c in world.bestiary:
            entities.append({
                "type": "creature",
                "name": c.name,
                "subtitle": f"Tier {c.tier} {c.creature_type.replace('_', ' ').title()} — {c.habitat} — CR {c.challenge_rating}",
                "detail_lines": [
                    f"  Name:        {c.name}",
                    f"  Type:        {c.creature_type.replace('_', ' ').title()}",
                    f"  Tier:        {c.tier} (CR {c.challenge_rating})",
                    f"  Habitat:     {c.habitat}",
                    f"  Body Plan:   {c.body_plan}",
                    f"  Behavior:    {c.behavior.replace('_', ' ').title()}",
                    f"  Abilities:   {'; '.join(c.special_abilities[:4])}" if c.special_abilities else "",
                    f"  Loot:        {'; '.join(c.loot[:4])}" if c.loot else "",
                    f"  {c.description[:200]}",
                ],
                "badge_color": CP["badge_s"],
                "badge": "B",
                "sort_key": f"creature_{c.name.lower()}",
            })

    # 5. Adventure zones
    if world.adventure_zones:
        for z in world.adventure_zones:
            from .world import ADVENTURE_ZONE_TYPES
            zt = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
            entities.append({
                "type": "zone",
                "name": z.name,
                "subtitle": f"{z.zone_type.title()} in {z.region} — {z.difficulty} — {zt.get('desc', '')}",
                "detail_lines": [
                    f"  Name:        {z.name}",
                    f"  Type:        {z.zone_type.title()} — {zt.get('desc', '')}",
                    f"  Region:      {z.region}  ({z.x}, {z.y})",
                    f"  Difficulty:  {z.difficulty}",
                    f"  Inhabitants: {z.inhabitants or 'Unknown'}",
                    f"  Treasure:    Tier {z.treasure_tier}",
                    f"  Status:      {'Cleared' if z.is_cleared else 'Undisturbed'}",
                    f"  {z.description[:200]}",
                ],
                "badge_color": CP["badge_m"],
                "badge": "Z",
                "sort_key": f"zone_{z.name.lower()}",
            })

    # 6. Deities (from pantheon)
    if world.pantheon and world.pantheon.deities:
        for d in world.pantheon.deities:
            domains_str = ", ".join(d.domains) if hasattr(d, 'domains') and d.domains else ""
            entities.append({
                "type": "deity",
                "name": d.name,
                "subtitle": f"{d.title or ''} — {domains_str} — {d.alignment if hasattr(d, 'alignment') else ''}",
                "detail_lines": [
                    f"  Name:    {d.name}",
                    f"  Title:   {d.title or 'Unknown'}",
                    f"  Domains: {domains_str or 'Unknown'}",
                    f"  Symbols: {d.symbol if hasattr(d, 'symbol') and d.symbol else 'Unknown'}",
                ],
                "badge_color": CP["badge_c"],
                "badge": "D",
                "sort_key": f"deity_{d.name.lower()}",
            })

    entities.sort(key=lambda e: e["sort_key"])
    return entities


GAZETTEER_TYPE_FILTERS = {
    ord("1"): None,       # All
    ord("2"): "settlement",
    ord("3"): "character",
    ord("4"): "faction",
    ord("5"): "creature",
    ord("6"): "zone",
    ord("7"): "deity",
}

GAZETTEER_FILTER_NAMES = {
    None: "All",
    "settlement": "Settlements",
    "character": "Characters",
    "faction": "Factions",
    "creature": "Creatures",
    "zone": "Adventure Zones",
    "deity": "Deities",
}


def _gazetteer_mode(stdscr, world):
    """Interactive gazetteer browser — browse all world entities."""
    curses.curs_set(0)
    stdscr.nodelay(False)

    entities = _collect_gazetteer_entities(world)
    if not entities:
        return

    selected_idx = 0
    scroll_offset = 0
    active_filter = None  # None = all
    show_detail = False
    detail_entity = None
    running = True
    status_msg = ""
    status_time = 0

    while running:
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        # Apply filter
        if active_filter is None:
            filtered = entities
        else:
            filtered = [e for e in entities if e["type"] == active_filter]

        if not filtered:
            filtered = entities
            active_filter = None

        selected_idx = min(selected_idx, max(0, len(filtered) - 1))

        # ── Header ──────────────────────────────────────────────────
        title = f"  wyrd Gazetteer  —  {len(entities)} entities  "
        _fill_line(stdscr, 0, CP["title"])
        _draw(stdscr, 0, 0, title, CP["title"], bold=True)
        _draw(stdscr, 0, max(0, w - 20), " [q] close  [G] close ", CP["dim"])

        # ── Filter bar ──────────────────────────────────────────────
        filter_y = 1
        _fill_line(stdscr, filter_y, CP["dim"])
        filter_text = " [1] All  [2] S  [3] C  [4] F  [5] B  [6] Z  [7] D"
        active_name = GAZETTEER_FILTER_NAMES.get(active_filter, "All")
        filter_str = f" Filter: {active_name} ({len(filtered)} shown) {filter_text}"
        _draw(stdscr, filter_y, 0, filter_str, CP["info"])

        # ── Column headers ──────────────────────────────────────────
        header_y = 2
        _fill_line(stdscr, header_y, CP["border"])
        _draw(stdscr, header_y, 2, " Type Name                       Details", CP["dim"])

        # ── Entity list ─────────────────────────────────────────────
        list_y = 3
        max_visible = h - list_y - 3
        scroll_offset = max(0, min(scroll_offset, max(0, len(filtered) - max_visible)))

        # Auto-scroll to keep selected visible
        if selected_idx < scroll_offset:
            scroll_offset = selected_idx
        if selected_idx >= scroll_offset + max_visible:
            scroll_offset = selected_idx - max_visible + 1

        visible = filtered[scroll_offset:scroll_offset + max_visible]

        for i, ent in enumerate(visible):
            y = list_y + i
            abs_idx = scroll_offset + i
            is_sel = (abs_idx == selected_idx)

            if is_sel:
                _fill_line(stdscr, y, CP["highlight"])

            marker = "▸ " if is_sel else "  "

            # Badge
            badge = f" {ent['badge']}"
            badge_cp = ent["badge_color"]

            # Name
            name_col = f" {ent['name'][:max(20, w - 60)]}"

            # Subtitle
            sub_col = f" {ent['subtitle'][:max(10, w - len(name_col) - 10)]}" if ent['subtitle'] else ""

            _draw(stdscr, y, 2, marker, CP["accent"], bold=True)
            _draw(stdscr, y, 5, badge, badge_cp, bold=True)
            _draw(stdscr, y, 8, name_col, CP["normal"], bold=is_sel)
            _draw(stdscr, y, 8 + len(name_col), sub_col[:max(0, w - len(name_col) - 10)], CP["dim"])

        # ── Status message ──────────────────────────────────────────
        if status_msg and time_module.monotonic() - status_time < 3:
            _fill_line(stdscr, h - 2, CP["border"])
            _draw(stdscr, h - 2, 2, f"  {status_msg}", CP["accent"])
        else:
            status_msg = ""

        # ── Status bar ──────────────────────────────────────────────
        status_y = h - 1
        mode_str = f" Gazetteer — {active_name} ({len(filtered)} items)"
        hints = " [↑↓] nav  [Enter] detail  [1-7] filter  [q/G] close"
        _fill_line(stdscr, status_y, CP["border"])
        _draw(stdscr, status_y, 0, mode_str, CP["accent"], bold=True)
        _draw(stdscr, status_y, max(0, w - len(hints) - 1), hints[:w - 3], CP["dim"])

        stdscr.refresh()

        # ── Detail popup ────────────────────────────────────────────
        if show_detail and detail_entity:
            detail_lines = detail_entity["detail_lines"]
            # Build popup with header and close instruction
            popup_lines = [
                f" {detail_entity['badge']}  {detail_entity['name']}",
                "",
            ]
            popup_lines.extend(detail_lines)
            popup_lines.append("")
            popup_lines.append(" [Enter] or [Esc] close ")

            box_h = min(len(popup_lines) + 2, h - 1)
            box_w = min(max(len(l) for l in popup_lines) + 4, w - 2)
            start_y = max(0, (h - box_h) // 2)
            start_x = max(0, (w - box_w) // 2)

            # Background
            for by in range(box_h):
                for bx in range(box_w):
                    try:
                        if by in (0, box_h - 1) or bx in (0, box_w - 1):
                            stdscr.addch(start_y + by, start_x + bx, " ",
                                         curses.color_pair(CP["title"]))
                        else:
                            stdscr.addch(start_y + by, start_x + bx, " ",
                                         curses.color_pair(CP["normal"]))
                    except curses.error:
                        pass

            # Text
            for i, line in enumerate(popup_lines):
                y = start_y + 1 + i
                if y >= h:
                    break
                if i == 0:
                    _draw(stdscr, y, start_x + 2, line[:box_w - 2], CP["title"], bold=True)
                elif "close" in line:
                    _draw(stdscr, y, start_x + 2, line[:box_w - 2], CP["dim"])
                else:
                    _draw(stdscr, y, start_x + 2, line[:box_w - 2], CP["normal"])

            stdscr.refresh()

        # ── Input ──────────────────────────────────────────────────
        key = stdscr.getch()

        if show_detail:
            if key in (10, 13, curses.KEY_ENTER, 27, ord("q"), ord("G")):
                show_detail = False
                detail_entity = None
            continue

        if key in (ord("q"), 27, ord("G")):
            running = False

        elif key in (curses.KEY_UP, ord("k")):
            if filtered:
                selected_idx = max(0, selected_idx - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            if filtered:
                selected_idx = min(len(filtered) - 1, selected_idx + 1)

        elif key in (10, 13, curses.KEY_ENTER):
            if filtered and 0 <= selected_idx < len(filtered):
                detail_entity = filtered[selected_idx]
                show_detail = True

        elif key in GAZETTEER_TYPE_FILTERS:
            new_filter = GAZETTEER_TYPE_FILTERS[key]
            if new_filter != active_filter:
                active_filter = new_filter
                selected_idx = 0
                scroll_offset = 0
                filter_name = GAZETTEER_FILTER_NAMES.get(new_filter, "All")
                status_msg = f"Filter: {filter_name} ({len([e for e in entities if new_filter is None or e['type'] == new_filter])} items)"
                status_time = time_module.monotonic()

        elif key == ord("r"):
            entities = _collect_gazetteer_entities(world)
            status_msg = f"Refreshed — {len(entities)} entities"
            status_time = time_module.monotonic()


# ── Gateway main loop ──────────────────────────────────────────────────

def _gateway_loop(stdscr):
    """Core curses loop for the gateway TUI."""
    curses.start_color()
    curses.use_default_colors()
    _init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.nodelay(False)

    worlds = scan_worlds(".")
    selected_idx = 0
    show_help = False
    status_msg = ""
    status_time = 0
    running = True
    world_in_session = None
    # Phase 21: sort state & detail cache
    sort_key = "seed"  # "seed", "population", "name"
    sort_reverse = False
    sorted_worlds = list(worlds)
    detail_cache: dict = {}  # path -> detail data
    update_sort = True

    while running:
        h, w = stdscr.getmaxyx()
        if h < 12 or w < 50:
            stdscr.clear()
            _draw(stdscr, h // 2, max(0, (w - 30) // 2),
                  "Terminal too small. Resize to 50x12+", CP["error"], bold=True)
            stdscr.refresh()
            time_module.sleep(0.5)
            key = stdscr.getch()
            continue

        stdscr.erase()

        # ── Draw splash ──────────────────────────────────────────────
        # Compact splash when worlds exist — just the title line
        if worlds:
            for i, line in enumerate(SPLASH):
                if i == 10:  # Only show "generative fantasy sandbox" line
                    x = max(0, (w - len(line)) // 2)
                    _draw(stdscr, 0, x, line, CP["accent"], bold=True)
                elif i == 11:  # The blank line after
                    pass
                else:
                    pass  # Skip ASCII art
            splash_bottom = 1
        else:
            for i, line in enumerate(SPLASH):
                x = max(0, (w - len(line)) // 2)
                cp = CP["accent"] if "━━━" in line else CP["title"]
                _draw(stdscr, i, x, line, cp, bold=True)
            splash_bottom = len(SPLASH)

        # ── Session indicator ────────────────────────────────────────
        if world_in_session:
            ws_line = f"  ▶ Session: wyrd #{world_in_session.seed} ({world_in_session.width}\u00d7{world_in_session.height})"
            _fill_line(stdscr, splash_bottom, CP["dim"])
            _draw(stdscr, splash_bottom, 0, ws_line, CP["accent"], bold=True)

        list_start_y = splash_bottom + (2 if not world_in_session else 1)

        # ── Sort worlds ────────────────────────────────────────────────
        if update_sort and worlds:
            if sort_key == "seed":
                sorted_worlds = sorted(worlds, key=lambda w: w["seed"], reverse=sort_reverse)
            elif sort_key == "population":
                sorted_worlds = sorted(worlds, key=lambda w: w["population"], reverse=not sort_reverse)
            elif sort_key == "name":
                sorted_worlds = sorted(worlds, key=lambda w: str(w["seed"]), reverse=sort_reverse)
            else:
                sorted_worlds = list(worlds)
            update_sort = False
            # Keep selection in bounds
            if selected_idx >= len(sorted_worlds):
                selected_idx = max(0, len(sorted_worlds) - 1)

        # ── World list ───────────────────────────────────────────────
        if not worlds:
            _draw(stdscr, list_start_y, 2, "No worlds found. Press [g] to generate one.", CP["dim"])
        else:
            # Section header with separator
            _fill_line(stdscr, list_start_y, CP["dim"])
            title = f"  Recent Worlds  ({len(worlds)} found)  "
            _draw(stdscr, list_start_y, 0, title, CP["title"], bold=True)
            list_start_y += 1
            _fill_line(stdscr, list_start_y, CP["dim"])
            # Build header with sort direction arrows inline
            # Adjust spacing so column alignment stays consistent
            if sort_key == "seed" or sort_key == "name":
                seed_label = "Seed↑" if not sort_reverse else "Seed↓"
                seed_pad = 4  # one fewer space to compensate for extra arrow char
            else:
                seed_label = "Seed"
                seed_pad = 5
            if sort_key == "population":
                pop_label = "Population↑" if sort_reverse else "Population↓"
                pop_pad = 4
            else:
                pop_label = "Population"
                pop_pad = 5
            header = f" {seed_label}{' '*seed_pad}Size{pop_pad*' '}{pop_label}     Settlements     Features"
            _draw(stdscr, list_start_y, 2, header, CP["dim"])
            list_start_y += 1

            max_visible = h - list_start_y - 3  # Reserve 2 lines for msg + 1 for status bar
            scroll_offset = max(0, selected_idx - max_visible + 1) if max_visible > 0 else 0
            visible_worlds = sorted_worlds[scroll_offset:scroll_offset + max_visible]

            for i, w_info in enumerate(visible_worlds):
                abs_idx = scroll_offset + i
                y = list_start_y + i
                is_selected = (abs_idx == selected_idx)

                if is_selected:
                    _fill_line(stdscr, y, CP["highlight"])

                marker = "▸ " if is_selected else "  "
                _draw(stdscr, y, 2, marker, CP["accent"], bold=True)

                # Seed column (left-aligned)
                seed_str = f"#{w_info['seed']:<6}"
                _draw(stdscr, y, 5, seed_str, CP["seed"], bold=True)

                # Size column
                dim_str = f"{w_info['dimensions']:<8}"
                _draw(stdscr, y, 16, dim_str, CP["dim"])

                # Population column with compact formatting
                pop = w_info["population"]
                if pop >= 1_000_000:
                    pop_str = f"{pop/1_000_000:.1f}M"
                elif pop >= 1_000:
                    pop_str = f"{pop/1_000:.1f}k"
                else:
                    pop_str = str(pop)
                pop_str = f"{pop_str:>9}"
                _draw(stdscr, y, 25, pop_str, CP["normal"])

                # Settlement count
                s_count = f"{w_info['regions']} regions"
                _draw(stdscr, y, 35, s_count, CP["dim"])

                # Badges (right-aligned, last 10 cols)
                bx = w - 14
                if _has_sim_file(w_info["seed"]):
                    _draw(stdscr, y, bx, "S", CP["badge_s"], bold=True); bx += 2
                if w_info["has_save"]:
                    _draw(stdscr, y, bx, "P", CP["badge_p"], bold=True); bx += 2
                if w_info["has_magic"]:
                    _draw(stdscr, y, bx, "M", CP["badge_m"], bold=True); bx += 2
                if w_info["has_chronicles"]:
                    _draw(stdscr, y, bx, "C", CP["badge_c"], bold=True); bx += 2
                if w_info["has_narrative"]:
                    _draw(stdscr, y, bx, "N", CP["badge_n"], bold=True); bx += 2
                if w_info["has_lore"]:
                    _draw(stdscr, y, bx, "L", CP["badge_l"], bold=True)

        # ── World detail card (right side, if space permits) ───────────
        if worlds and 0 <= selected_idx < len(sorted_worlds) and w >= 70:
            w_info = sorted_worlds[selected_idx]
            # Lazy-load detail data for the selected world
            if w_info["path"] not in detail_cache:
                detail_cache[w_info["path"]] = _load_world_for_detail(w_info["path"])
            detail_data = detail_cache.get(w_info["path"])
            if detail_data and w >= 70:
                # Position the detail card to the right of the world list
                detail_x = min(55, w - 36)
                detail_y = list_start_y - 2  # Start above the list header
                _draw_world_detail_panel(stdscr, detail_data,
                                          detail_y, detail_x,
                                          h - list_start_y - 1, w - detail_x - 1)

        # ── Status message (one line above status bar) ────────────────
        if status_msg and time_module.monotonic() - status_time < 4:
            _fill_line(stdscr, h - 2, CP["border"])
            _draw(stdscr, h - 2, 2, f"  {status_msg}", CP["accent"])
        else:
            status_msg = ""

        # ── Status bar (persistent mode indicator + context-aware hints) ─
        status_y = h - 1
        # Determine mode indicator
        if world_in_session:
            mode_str = f" ▶ Session: wyrd #{world_in_session.seed}"
        elif sorted_worlds and 0 <= selected_idx < len(sorted_worlds):
            w_info = sorted_worlds[selected_idx]
            mode_str = f" wyrd #{w_info['seed']} — {w_info['population']:,} souls"
        else:
            mode_str = " No world selected"

        # Build context-sensitive key hints (right-aligned)
        # Calculate actual sort direction per key
        if sort_key == "population":
            actual_descending = not sort_reverse  # population inverts
        else:
            actual_descending = sort_reverse
        sort_hint = f"  [Tab] sort:{sort_key}"
        sort_hint += " ↑" if not actual_descending else " ↓"
        if worlds:
            hints = " [↑↓/k j] sel  [g] gen  [l] load  [e] explore  [v] view  [p] play  [G] gazetteer"
        else:
            hints = " [g] generate  [l] load"
        hints += sort_hint + "  [?] help  [q] quit"

        _fill_line(stdscr, status_y, CP["border"])
        _draw(stdscr, status_y, 0, mode_str, CP["accent"], bold=True)
        _draw(stdscr, status_y, max(0, w - len(hints) - 1), hints[:w - len(mode_str) - 2], CP["dim"])

        # ── Help overlay ─────────────────────────────────────────────
        if show_help:
            draw_help_panel(stdscr, GATEWAY_HELP)

        curses.doupdate()

        # ── Input ────────────────────────────────────────────────────
        key = stdscr.getch()

        if show_help:
            show_help = False
            continue

        if key == ord("q") or key == 27:
            # Confirm-on-quit safeguard
            confirm_msg = "Quit wyrd? Press q again to confirm, any other key to cancel."
            confirm_x = max(0, (w - len(confirm_msg)) // 2)
            confirm_y = h // 2
            # Draw a compact confirmation popup
            popup_w = len(confirm_msg) + 4
            popup_x = max(0, (w - popup_w) // 2)
            for py in range(confirm_y - 1, confirm_y + 2):
                if 0 <= py < h:
                    _fill_line(stdscr, py, CP["border"])
                    _draw(stdscr, py, popup_x, " " * popup_w, CP["normal"])
            _draw(stdscr, confirm_y, confirm_x, confirm_msg, CP["warning"], bold=True)
            curses.doupdate()
            confirm_key = stdscr.getch()
            if confirm_key == ord("q"):
                running = False
            # else: continue without quitting

        elif key == ord("?") or key == ord("h"):
            show_help = True

        elif key == 9:  # Tab: cycle sort key
            sort_keys = ["seed", "population", "name"]
            try:
                idx = sort_keys.index(sort_key)
                sort_key = sort_keys[(idx + 1) % len(sort_keys)]
            except ValueError:
                sort_key = "seed"
            sort_reverse = False  # Natural order for each key
            update_sort = True
            selected_idx = 0
            status_msg = f"Sort: {sort_key}"
            status_time = time_module.monotonic()

        elif key == curses.KEY_BTAB:  # Shift+Tab: toggle sort direction
            sort_reverse = not sort_reverse
            update_sort = True
            direction = "descending" if sort_reverse else "ascending"
            status_msg = f"Sort reverse: {direction}"
            status_time = time_module.monotonic()

        elif key == ord("r"):
            worlds = scan_worlds(".")
            selected_idx = min(selected_idx, max(0, len(worlds) - 1))
            update_sort = True
            status_msg = f"\u231b Scanned {len(worlds)} worlds"
            status_time = time_module.monotonic()

        elif key == ord("g"):
            seed = random.randint(0, 999999)
            world_in_session = generate_world(seed)
            from .serialize import save_world
            save_world(world_in_session, f"wyrd-{seed}.json")
            status_msg = f"\u2705 Generated wyrd #{seed} \u2014 press [e] to explore"
            status_time = time_module.monotonic()
            worlds = scan_worlds(".")
            update_sort = True
            for i, w in enumerate(worlds):
                if w["seed"] == seed:
                    selected_idx = i
                    break

        elif key == ord("l"):
            stdscr.clear()
            prompt = "Enter path to world JSON file: "
            _draw(stdscr, h // 2, max(0, (w - len(prompt)) // 2),
                  prompt, CP["accent"], bold=True)
            stdscr.refresh()
            curses.echo()
            curses.curs_set(1)
            try:
                raw = stdscr.getstr(h // 2 + 1, (w - 30) // 2, 60)
                fname = raw.decode("utf-8").strip() if isinstance(raw, bytes) else raw.strip()
            except Exception:
                fname = ""
            curses.noecho()
            curses.curs_set(0)
            if fname and os.path.exists(fname):
                try:
                    world_in_session = load_world(fname)
                    status_msg = f"\u2705 Loaded {os.path.basename(fname)}"
                except Exception as e:
                    status_msg = f"\u274c Load failed: {e}"
                status_time = time_module.monotonic()
                worlds = scan_worlds(".")
            elif fname:
                status_msg = f"\u274c File not found: {fname}"
                status_time = time_module.monotonic()

        elif key in (curses.KEY_UP, ord("k")):
            if sorted_worlds:
                selected_idx = max(0, selected_idx - 1)

        elif key in (curses.KEY_DOWN, ord("j")):
            if sorted_worlds:
                selected_idx = min(len(sorted_worlds) - 1, selected_idx + 1)

        elif key in (10, 13, ord(" "), curses.KEY_ENTER):
            if sorted_worlds and 0 <= selected_idx < len(sorted_worlds):
                w_info = sorted_worlds[selected_idx]
                try:
                    world_in_session = load_world(w_info["path"])
                    status_msg = f"\u2705 Loaded wyrd #{world_in_session.seed}"
                except Exception as e:
                    status_msg = f"\u274c Load failed: {e}"
                status_time = time_module.monotonic()

        elif key == ord("e"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .explore import explore_world
            stdscr = _launch_curses_view(stdscr, "Explorer", explore_world, world)

        elif key == ord("v"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .viewer import view_simulation
            stdscr = _launch_curses_view(stdscr, "Simulation Viewer",
                                         view_simulation, world, None, 0.3)

        elif key == ord("d"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .render import render_lore
            lore_text = _strip_ansi(render_lore(world))
            draw_help_panel(stdscr, ["wyrd — World Lore  (press any key to close)", ""] +
                            [f"  {l}" for l in lore_text.split("\n")])
            stdscr.refresh()
            stdscr.getch()

        elif key == ord("c"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .chronicles import generate_chronicles
            from .render import render_chronicles
            if not world.chronicles:
                world.chronicles = generate_chronicles(world, world.narrative)
            chron_text = _strip_ansi(render_chronicles(world))
            lines = ["wyrd — Chronicles  (press any key to close)", ""]
            for l in chron_text.split("\n"):
                lines.append(f"  {l}")
            draw_help_panel(stdscr, lines)
            stdscr.refresh()
            stdscr.getch()

        elif key == ord("s"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            curses.endwin()
            from .sim import run_simulation, render_sim_detailed
            from .serialize import save_sim_state
            sim_chars = world.narrative.characters if world.narrative else None
            result = run_simulation(world, num_years=100, seed_offset=0,
                                    chaos_factor=0.1, snapshot_interval=50,
                                    characters=sim_chars)
            save_sim_state(result, f"wyrd-{world.seed}-sim.json")
            print(render_sim_detailed(result, world))
            input("\n\u2014\u2014 Simulation Complete \u2014\u2014 Press Enter to return to wyrd gateway...")
            stdscr = curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            _init_colors()
            stdscr.keypad(True)
            curses.curs_set(0)

        elif key == ord("x"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .export_html import export_world_html
            output = f"wyrd-{world.seed}.html"
            html = export_world_html(world)
            with open(output, "w") as f:
                f.write(html)
            status_msg = f"\U0001f310 Exported to {output}"
            status_time = time_module.monotonic()

        elif key == ord("t"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"❌ {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            _trade_routes_curses_overlay(stdscr, world)
            stdscr.erase()

        elif key == ord("G"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"\u274c {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            _gazetteer_mode(stdscr, world)
            stdscr.erase()

        elif key == ord("p"):
            world, err = _resolve_world(world_in_session, sorted_worlds, selected_idx)
            if err:
                status_msg = f"\u274c {err}"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            curses.endwin()
            from .embody_tui import embody_tui_play
            embody_tui_play(world, years=100, chaos=0.3, load_save=True)
            print("\n── Press Enter to return to wyrd gateway...")
            input()
            stdscr = curses.initscr()
            curses.start_color()
            curses.use_default_colors()
            _init_colors()
            stdscr.keypad(True)
            curses.curs_set(0)

        if key == ord("q"):
            break


def gateway_main():
    """Entry point for the gateway TUI."""
    locale.setlocale(locale.LC_ALL, '')
    try:
        curses.wrapper(_gateway_loop)
    except KeyboardInterrupt:
        pass
