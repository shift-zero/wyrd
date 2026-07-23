"""wyrd — Interactive Simulation Viewer (Phase 7).

Curses-based viewer that shows the world map evolving year by year.
Supports pause/resume, speed control, step-forward, event log,
and population chart.

Usage:
    wyrd view --seed 42 --years 300
    wyrd view --load world.json --years 500
"""

import curses
import random
import time

from .world import World, TERRAIN
from .sim import (
    initialize_sim_state, _simulate_tick, _simulate_month_tick,
    simulate_years,
    apply_sim_state_to_world, SimState, SimEvent,
)
from .economy import reconstruct_routes

# ── Color pairs (1-60) ───────────────────────────────────────────────
# Pairs 1-22: base terrain + UI
# Pairs 23-58: seasonal terrain variants (4 seasons × 9 terrain types)
# Pairs 59-60: trade routes

_CP = {
    "deep_water": 1, "shallow": 2, "sand": 3, "grass": 4,
    "forest": 5, "hills": 6, "mountains": 7, "snow": 8, "river": 9,
    "settlement": 10, "abandoned": 11, "new_found": 12,
    "header": 13, "status": 14, "dim": 15, "accent": 17,
    "info": 18, "war": 19, "famine": 20, "plague": 21, "good": 22,
    # Seasonal variants — each season gets 9 pairs (deep_water..river)
    "spr_deep_water": 23, "spr_shallow": 24, "spr_sand": 25,
    "spr_grass": 26, "spr_forest": 27, "spr_hills": 28,
    "spr_mountains": 29, "spr_snow": 30, "spr_river": 31,
    "sum_deep_water": 32, "sum_shallow": 33, "sum_sand": 34,
    "sum_grass": 35, "sum_forest": 36, "sum_hills": 37,
    "sum_mountains": 38, "sum_snow": 39, "sum_river": 40,
    "aut_deep_water": 41, "aut_shallow": 42, "aut_sand": 43,
    "aut_grass": 44, "aut_forest": 45, "aut_hills": 46,
    "aut_mountains": 47, "aut_snow": 48, "aut_river": 49,
    "win_deep_water": 50, "win_shallow": 51, "win_sand": 52,
    "win_grass": 53, "win_forest": 54, "win_hills": 55,
    "win_mountains": 56, "win_snow": 57, "win_river": 58,
    "trade_route": 59, "trade_dot": 60,
}

SEASONS = ["winter", "spring", "summer", "autumn"]  # N+Earth seasons

def _season_name(month: int) -> str:
    """Map month (0-11) to season name."""
    if month in (11, 0, 1):
        return "winter"
    elif month in (2, 3, 4):
        return "spring"
    elif month in (5, 6, 7):
        return "summer"
    else:
        return "autumn"

def _season_cp(terrain_key: str, month: int | None) -> int:
    """Get color pair for terrain, adjusted for season if month is known."""
    if month is None:
        return _CP.get(terrain_key, 4)
    season = _season_name(month)
    key = f"{season}_{terrain_key}"
    if key in _CP:
        return _CP[key]
    return _CP.get(terrain_key, 4)

_EVENT_ICON = {
    "plague": "☠", "famine": "🌾", "war": "⚔", "discovery": "✦",
    "prosperity": "↑", "disaster": "🌋", "exodus": "→",
    "founding": "▲", "abandonment": "✗", "trade_boom": "💰",
    # Religious events
    "religious_tension": "✞", "divine_blessing": "✧",
    "holy_pilgrimage": "🚶", "heresy": "🔥",
    # Faction events
    "faction_war": "🏴", "faction_alliance": "🤝",
    "faction_power_shift": "⬇", "faction_collapse": "💀",
    "faction_peace_treaty": "☮", "faction_leadership_change": "👑",
    "faction_trade_pact": "📦", "faction_vassal_revolt": "⚡",
    "faction_coup": "🗡",
    # Cataclysm events
    "earthquake": "〰", "volcanic_eruption": "🌋",
    "great_plague": "💀", "tsunami": "🌊",
    "meteor_strike": "☄", "great_fire": "🔥",
    "magical_cataclysm": "🌀",
}

_EVENT_COLOR = {
    "war": "war", "famine": "famine", "plague": "plague",
    "disaster": "war", "abandonment": "dim", "exodus": "dim",
    "founding": "good", "discovery": "good", "prosperity": "good",
    "trade_boom": "good",
    # Religious events
    "religious_tension": "famine", "divine_blessing": "good",
    "holy_pilgrimage": "good", "heresy": "famine",
    # Faction events
    "faction_war": "war", "faction_alliance": "good",
    "faction_power_shift": "famine", "faction_collapse": "war",
    "faction_peace_treaty": "good", "faction_leadership_change": "good",
    "faction_trade_pact": "good", "faction_vassal_revolt": "war",
    "faction_coup": "war",
    # Cataclysm events
    "earthquake": "war", "volcanic_eruption": "war",
    "great_plague": "plague", "tsunami": "war",
    "meteor_strike": "war", "great_fire": "war",
    "magical_cataclysm": "plague",
}


def _init():
    curses.init_pair(1, 27, -1)     # deep_water
    curses.init_pair(2, 33, -1)     # shallow
    curses.init_pair(3, 223, -1)    # sand
    curses.init_pair(4, 28, -1)     # grass
    curses.init_pair(5, 22, -1)     # forest
    curses.init_pair(6, 94, -1)     # hills
    curses.init_pair(7, 130, -1)    # mountains
    curses.init_pair(8, 255, -1)    # snow
    curses.init_pair(9, 45, -1)     # river
    curses.init_pair(10, 226, -1)   # settlement (yellow)
    curses.init_pair(11, 240, -1)   # abandoned (dim grey)
    curses.init_pair(12, 46, -1)    # new founding (green)
    curses.init_pair(13, 45, -1)    # header (cyan)
    curses.init_pair(14, 226, -1)   # status (yellow)
    curses.init_pair(15, 240, -1)   # dim grey
    curses.init_pair(16, 245, -1)   # event label
    curses.init_pair(17, 46, -1)    # accent (green)
    curses.init_pair(18, 188, -1)   # info text (light grey)
    curses.init_pair(19, 196, -1)   # war (red)
    curses.init_pair(20, 130, -1)   # famine (brown)
    curses.init_pair(21, 90, -1)    # plague (magenta)
    curses.init_pair(22, 46, -1)    # good (green)
    # ── Seasonal terrain variants ──
    # Spring: fresh greens, bright
    curses.init_pair(23, 33, -1)    # spr_deep_water — slightly lighter blue
    curses.init_pair(24, 39, -1)    # spr_shallow — brighter shallow
    curses.init_pair(25, 229, -1)   # spr_sand — pale gold
    curses.init_pair(26, 34, -1)    # spr_grass — bright fresh green
    curses.init_pair(27, 28, -1)    # spr_forest — lush green
    curses.init_pair(28, 100, -1)   # spr_hills — green-brown
    curses.init_pair(29, 137, -1)   # spr_mountains — warm grey-brown
    curses.init_pair(30, 255, -1)   # spr_snow — bright white
    curses.init_pair(31, 51, -1)    # spr_river — bright cyan
    # Summer: warm, slightly yellowed
    curses.init_pair(32, 27, -1)    # sum_deep_water
    curses.init_pair(33, 33, -1)    # sum_shallow
    curses.init_pair(34, 230, -1)   # sum_sand — warm sand
    curses.init_pair(35, 106, -1)   # sum_grass — sun-bleached green
    curses.init_pair(36, 64, -1)    # sum_forest — olive green
    curses.init_pair(37, 101, -1)   # sum_hills — warm brown
    curses.init_pair(38, 143, -1)   # sum_mountains — tawny
    curses.init_pair(39, 255, -1)   # sum_snow
    curses.init_pair(40, 45, -1)    # sum_river
    # Autumn: orange, brown, red
    curses.init_pair(41, 26, -1)    # aut_deep_water — darker blue
    curses.init_pair(42, 31, -1)    # aut_shallow — muted
    curses.init_pair(43, 180, -1)   # aut_sand — ochre
    curses.init_pair(44, 142, -1)   # aut_grass — dry yellow-brown
    curses.init_pair(45, 130, -1)   # aut_forest — russet/red-brown
    curses.init_pair(46, 137, -1)   # aut_hills — autumn brown
    curses.init_pair(47, 138, -1)   # aut_mountains — muted grey-brown
    curses.init_pair(48, 250, -1)   # aut_snow — grey-white
    curses.init_pair(49, 37, -1)    # aut_river — steel blue
    # Winter: cool blues, white, grey
    curses.init_pair(50, 25, -1)    # win_deep_water — icy dark blue
    curses.init_pair(51, 31, -1)    # win_shallow — icy blue
    curses.init_pair(52, 188, -1)   # win_sand — pale grey
    curses.init_pair(53, 65, -1)    # win_grass — frosty muted green
    curses.init_pair(54, 59, -1)    # win_forest — dark frost
    curses.init_pair(55, 102, -1)   # win_hills — cold grey-brown
    curses.init_pair(56, 145, -1)   # win_mountains — cold grey
    curses.init_pair(57, 255, -1)   # win_snow — brilliant white
    curses.init_pair(58, 38, -1)    # win_river — icy cyan
    # Trade route pairs (Phase 19)
    curses.init_pair(59, 220, -1)   # trade_route — gold
    curses.init_pair(60, 226, -1)   # trade_dot — bright gold


def _cp(terrain_key: str) -> int:
    return _CP.get(terrain_key, 4)


def _ev_cp(event_type: str) -> int:
    e = _EVENT_COLOR.get(event_type)
    return _CP.get(e, 18) if e else 18


def _build_smap(world: World) -> dict:
    """(x,y) -> {char, is_active} lookup."""
    sm = {}
    for r in world.regions:
        for s in r.settlements:
            sm[(s.x, s.y)] = {"char": s.char, "active": True}
    return sm


# ── Draw helpers ─────────────────────────────────────────────────────

def _draw(stdscr, y, x, text, cp, bold=False):
    """Safe draw with bounds checking."""
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


# ── Rendering ────────────────────────────────────────────────────────

def _render_map(stdscr, world: World, smap: dict,
                mh: int, mw: int, new_founds: set,
                flash_tiles: dict | None = None,
                month: int | None = None):
    """Render terrain + settlements into the map area (starting at line 2).
    
    If month is provided, seasonal color variants are used for terrain.
    Uses batched addstr() for same-color spans to reduce curses API calls."""

    flash_tiles = flash_tiles or {}
    for sy in range(mh):
        wy = sy  # no vertical offset in viewer — show top-left
        if wy >= world.height:
            break
        # Build (char, color_pair) spans for one line
        spans: list[tuple[str, int]] = []
        for sx in range(min(mw, world.width)):
            wx = sx
            key = (wx, wy)
            if key in smap:
                info = smap[key]
                char = info["char"]
                if key in new_founds:
                    c = _CP["new_found"]
                elif key in flash_tiles:
                    frames = flash_tiles[key]
                    c = _CP["new_found"] if frames % 3 < 2 else _CP["settlement"]
                elif info.get("active", True):
                    c = _CP["settlement"]
                else:
                    c = _CP["abandoned"]
            else:
                if wx < world.width and wy < world.height:
                    t = world.terrain[wy][wx]
                    char = TERRAIN[t]["char"]
                    if key in flash_tiles:
                        frames = flash_tiles[key]
                        c = _CP["accent"] if frames % 3 < 2 else (_cp(t) if month is None else _season_cp(t, month))
                    else:
                        c = _cp(t) if month is None else _season_cp(t, month)
                else:
                    char = " "
                    c = 4
            # Merge into same-color span if possible
            if spans and spans[-1][1] == c:
                spans[-1] = (spans[-1][0] + char, c)
            else:
                spans.append((char, c))
        # Write batched spans
        x_pos = 0
        for chars, cp in spans:
            try:
                stdscr.addstr(2 + sy, x_pos, chars, curses.color_pair(cp))
            except curses.error:
                break
            x_pos += len(chars)


def _draw_header(stdscr, seed, year, total, paused, speed, w, month=None):
    """Clean header bar with wyrd title, sim status, season, and speed."""
    fmt = f" wyrd — Seed {seed}  "
    mode = "⏸ PAUSED" if paused else "▶ RUNNING"
    mode_color = _CP["status"] if paused else _CP["accent"]
    season_str = _season_name(month) if month is not None else ""
    yr_str = f" {season_str} Year {year:,}/{total:,}"
    lbl = _speed_label(speed)
    speed_str = f" {lbl} {speed:.1f}x"
    _fill_line(stdscr, 0, _CP["header"])
    _draw(stdscr, 0, 0, fmt, _CP["header"], bold=True)
    _draw(stdscr, 0, len(fmt), mode, mode_color, bold=True)
    _draw(stdscr, 0, max(0, w - len(speed_str) - 2), speed_str, _CP["dim"])
    _draw(stdscr, 0, max(0, w - len(speed_str) - len(yr_str) - 4), yr_str, _CP["info"])


def _draw_stats(stdscr, state: SimState, speed: float = 2.0):
    active = state.num_settlements
    abandoned = state.num_abandoned
    pop = state.total_population
    # Speed bar: 8 chars, fills proportionally
    speed_pct = max(0.0, min(1.0, (speed - 0.125) / 511.875))
    filled = int(speed_pct * 8)
    speed_bar = "█" * filled + "░" * (8 - filled)
    text = (f" Settlements: {active} active"
            f"{f', {abandoned} abandoned' if abandoned else ''}"
            f"  │  Pop: {pop:,}  │  {speed_bar}  {speed:.1f}x")
    _fill_line(stdscr, 1, _CP["info"])
    _draw(stdscr, 1, 0, text, _CP["info"])


def _draw_events(stdscr, events: list, max_events: int, start_y: int, w: int):
    """Draw recent events into the event panel area."""
    if not events:
        _fill_line(stdscr, start_y, _CP["dim"])
        _draw(stdscr, start_y, 0, " (no events yet — sim running...)", _CP["dim"])
        return

    recent = events[-(max_events - 1):]
    row = 0
    for i, ev in enumerate(recent):
        y = start_y + row
        row += 1
        if y >= start_y + max_events:
            break
        icon = _EVENT_ICON.get(ev.event_type, "•")
        cp = _ev_cp(ev.event_type)
        desc = ev.description[:max(10, w - 18)]
        text = f" {icon} Y{ev.year} {desc}"
        _draw(stdscr, y, 0, text[:w - 1], cp)


def _draw_status_bar(stdscr, h, w, seed, year, total, paused, speed, month=None):
    """Persistent status bar showing mode, season, progress, speed label, and keybind hints."""
    season_str = _season_name(month) if month is not None else ""
    lbl = _speed_label(speed)
    # Left: mode indicator
    if paused:
        mode_str = f" ⏸ PAUSED  Seed {seed}  {season_str} Year {year:,}/{total:,}  {lbl} {speed:.1f}x"
    else:
        mode_str = f" ▶ RUNNING  Seed {seed}  {season_str} Year {year:,}/{total:,}  {lbl} {speed:.1f}x"

    # Right: context-sensitive key hints
    if paused:
        hints = " [Space] resume  [→] step  [+/-] speed  [[] []] settle  [i] inspect  [p] chart  [d] diff  [?] help  [q] quit"
    else:
        hints = " [Space] pause  [+/-] speed  [[] []] settle  [i] inspect  [p] chart  [d] diff  [?] help  [q] quit"

    _fill_line(stdscr, h - 1, _CP["dim"])
    _draw(stdscr, h - 1, 0, mode_str, _CP["accent"] if not paused else _CP["status"], bold=not paused)
    _draw(stdscr, h - 1, max(0, w - len(hints) - 1), hints[:w - len(mode_str) - 3], _CP["dim"])


def _draw_pause_notification(stdscr, msg: str | None, frames_left: int, h: int, w: int):
    """Draw a brief auto-pause notification banner near the top of the screen."""
    if msg is None or frames_left <= 0:
        return
    prefix = " ⏸ Auto-paused "
    text = f"{prefix}{msg}"
    text = text[:w - 4]
    # Flash: alternate between accent and status colors
    cp = _CP["status"] if frames_left // 6 % 2 == 0 else _CP["accent"]
    _fill_line(stdscr, 2, _CP["header"])
    _draw(stdscr, 2, 2, text, cp, bold=True)


# ── Trade route animation (Phase 19) ──────────────────────────────────


def _bresenham_line(x0: int, y0: int, x1: int, y1: int):
    """Yield (x, y) points along a line from (x0,y0) to (x1,y1)."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        yield x, y
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _draw_trade_routes(stdscr, state: SimState, smap: dict,
                       frame_count: int, map_h: int, w: int,
                       paused: bool):
    """Draw trade route lines with animated moving dots.

    Active routes show a dotted line between settlements and a
    moving ◆ dot that travels from source to destination.
    Dots only animate when unpaused.
    """
    route_dicts = getattr(state, 'trade_routes', [])
    if not route_dicts:
        return

    routes = reconstruct_routes(route_dicts)
    settlements = state.settlements
    route_cp = _CP["trade_route"]
    dot_cp = _CP["trade_dot"]

    for route in routes:
        if not route.is_active:
            continue

        src_ss = settlements.get(route.source)
        dst_ss = settlements.get(route.destination)
        if not src_ss or not dst_ss:
            continue

        # Screen coordinates: map starts at row 2
        x1, y1 = src_ss.x, 2 + src_ss.y
        x2, y2 = dst_ss.x, 2 + dst_ss.y

        # Skip if off-screen
        if max(y1, y2) > 2 + map_h or min(y1, y2) < 2:
            continue

        # Get all points along the line
        points = list(_bresenham_line(x1, y1, x2, y2))
        if len(points) < 2:
            continue

        # Draw route line (faint dots along the path)
        for px, py in points:
            if (px, py) == (x1, y1) or (px, py) == (x2, y2):
                continue  # Don't draw over settlement chars
            try:
                stdscr.addch(py, px, '·', curses.color_pair(route_cp) | curses.A_DIM)
            except curses.error:
                pass

        # Animated dot position
        # Use a stable hash for phase offset so each route has unique timing
        phase = (hash(route.source + route.destination) & 0xFFFF) / 65536.0
        if paused:
            t = phase  # Static position when paused
        else:
            t = (frame_count * 0.03 + phase) % 1.0

        dot_idx = int(t * (len(points) - 1))
        dot_x, dot_y = points[dot_idx]

        # Don't draw dot over settlement chars
        if (dot_x, dot_y) != (x1, y1) and (dot_x, dot_y) != (x2, y2):
            try:
                stdscr.addch(dot_y, dot_x, '◆', curses.color_pair(dot_cp) | curses.A_BOLD)
            except curses.error:
                pass


# ── Population chart overlay ─────────────────────────────────────────

def _draw_chart(stdscr, state: SimState, h, w):
    """Overlay a population-over-time bar chart."""
    records = state.population_record
    if len(records) < 2:
        return

    cw = min(52, w - 4)
    ch = min(18, h - 6)
    sx = max(0, (w - cw) // 2)
    sy = max(0, (h - ch) // 2)

    # Background box
    for y in range(ch):
        for x in range(cw):
            try:
                if y in (0, ch - 1) or x in (0, cw - 1):
                    stdscr.addch(sy + y, sx + x, " ",
                                 curses.color_pair(13))
                else:
                    stdscr.addch(sy + y, sx + x, " ",
                                 curses.color_pair(18))
            except curses.error:
                pass

    title = " Population Over Time "
    _draw(stdscr, sy, sx + (cw - len(title)) // 2, title, _CP["header"],
          bold=True)

    # Data
    pops = [r["total_population"] for r in records]
    mx = max(pops) or 1
    mn = min(pops) or 0
    rng = max(mx - mn, 1)

    # Sample 15 points for bars
    step = max(1, len(records) // 15)
    sampled = records[::step]
    if records[-1] not in sampled:
        sampled.append(records[-1])

    plot_x = sx + 1
    plot_y = sy + 1
    plot_w = cw - 2
    plot_h = ch - 2

    for i, rec in enumerate(sampled):
        bar = max(1, int((rec["total_population"] - mn) / rng * (plot_h - 1)))
        bx = plot_x + int(i / max(len(sampled) - 1, 1) * (plot_w - 1))
        bx = min(bx, plot_x + plot_w - 1)
        for by in range(bar):
            try:
                stdscr.addch(plot_y + plot_h - 1 - by, bx, "█",
                             curses.color_pair(10))
            except curses.error:
                pass
        # Year label
        lbl = str(rec["year"])
        if len(lbl) > 3:
            lbl = lbl[-3:]
        _draw(stdscr, plot_y + plot_h, bx, lbl[0], _CP["dim"])

    # Axis labels
    for pct, label_pct in [(0, 0.0), (0.5, 0.5), (1.0, 1.0)]:
        val = int(mn + rng * pct)
        y = plot_y + plot_h - 1 - int(plot_h * pct)
        y = max(plot_y, min(plot_y + plot_h - 1, y))
        _draw(stdscr, y, plot_x - 7, f"{val:>6,}", _CP["info"])

    _draw(stdscr, sy + ch, sx, " Press [p] to close ", _CP["dim"])


# ── Change overlay ───────────────────────────────────────────────────
# When paused, overlay colored growth/shrinkage indicators on settlements.


def _draw_change_overlay(stdscr, state, last_diff: dict | None, map_h: int):
    """Draw colored change indicators on settlement positions on the map.

    Green ▲ for grew, red ▼ for shrank, grey · for abandoned.
    Only meaningful when paused — called after _render_map.
    """
    if last_diff is None:
        return
    settlements = state.settlements
    grew_names = {item[0] for item in last_diff.get("grew", [])}
    shrank_names = {item[0] for item in last_diff.get("shrank", [])}
    abandoned_names = set(last_diff.get("abandoned", []))

    for name, ss in settlements.items():
        if name in grew_names:
            ch, cp = "▲", _CP["good"]  # green
        elif name in shrank_names:
            ch, cp = "▼", _CP["war"]  # red
        elif name in abandoned_names:
            ch, cp = "·", _CP["dim"]  # grey
        else:
            continue
        # Screen position: row 2 + y (below header/stats), col x
        sy, sx = 2 + ss.y, ss.x
        if sy > 2 + map_h:  # off-screen below map
            continue
        try:
            stdscr.addch(sy, sx, ch, curses.color_pair(cp))
        except curses.error:
            pass


# ── Year-diff overlay ───────────────────────────────────────────────


def _snapshot_populations(state) -> dict:
    """Snapshot settlement populations and prosperity for diff computation."""
    return {
        name: {"pop": ss.population, "pros": ss.prosperity, "active": ss.is_active}
        for name, ss in state.settlements.items()
    }


def _compute_diff(prev: dict, state) -> dict:
    """Compare prev snapshot to current SimState; return structured diff."""
    grew = []
    shrank = []
    new_settlements = []
    abandoned = []
    rebuilt = []
    pros_up = []
    pros_down = []

    current = {
        name: {"pop": ss.population, "pros": ss.prosperity, "active": ss.is_active}
        for name, ss in state.settlements.items()
    }

    # Settlements in current state
    for name, cur in current.items():
        if name in prev:
            prev_info = prev[name]
            if not prev_info["active"] and cur["active"]:
                rebuilt.append(name)
            elif prev_info["active"] and not cur["active"]:
                abandoned.append(name)
            elif cur["active"]:
                pop_diff = cur["pop"] - prev_info["pop"]
                if pop_diff > 0:
                    grew.append((name, prev_info["pop"], cur["pop"], pop_diff))
                elif pop_diff < 0:
                    shrank.append((name, prev_info["pop"], cur["pop"], pop_diff))
                pros_diff = cur["pros"] - prev_info["pros"]
                if pros_diff > 0.05:
                    pros_up.append((name, cur["pros"], pros_diff))
                elif pros_diff < -0.05:
                    pros_down.append((name, cur["pros"], pros_diff))
        else:
            if cur["active"]:
                new_settlements.append((name, cur["pop"], cur["pros"]))

    # Sort by magnitude (most changed first)
    grew.sort(key=lambda x: -abs(x[3]))
    shrank.sort(key=lambda x: -abs(x[3]))
    pros_up.sort(key=lambda x: -abs(x[2]))
    pros_down.sort(key=lambda x: -abs(x[2]))

    return {
        "grew": grew[:15],
        "shrank": shrank[:15],
        "new": new_settlements[:10],
        "abandoned": abandoned[:10],
        "rebuilt": rebuilt[:10],
        "pros_up": pros_up[:10],
        "pros_down": pros_down[:10],
        "year": state.year,
    }


def _draw_diff(stdscr, diff: dict | None, h: int, w: int):
    """Draw the year-diff overlay panel."""
    if diff is None:
        return

    box_lines = []
    box_lines.append(f" ══ Year {diff['year']} Changes ══")
    box_lines.append("")

    had_any = False

    if diff["new"]:
        had_any = True
        box_lines.append("  ◆ New Settlements:")
        for name, pop, pros in diff["new"][:6]:
            box_lines.append(f"    +{name} (pop {pop:,}, pros {pros:.0%})")
        if len(diff["new"]) > 6:
            box_lines.append(f"    … and {len(diff['new']) - 6} more")

    if diff["grew"]:
        had_any = True
        box_lines.append("  ↑ Population Growth:")
        for name, old, new_, delta in diff["grew"][:6]:
            box_lines.append(f"    {name}: {old:,} → {new_,:} (+{delta:,})")
        if len(diff["grew"]) > 6:
            box_lines.append(f"    … and {len(diff['grew']) - 6} more")

    if diff["shrank"]:
        had_any = True
        box_lines.append("  ↓ Population Decline:")
        for name, old, new_, delta in diff["shrank"][:6]:
            box_lines.append(f"    {name}: {old:,} → {new_:,} ({delta:,})")
        if len(diff["shrank"]) > 6:
            box_lines.append(f"    … and {len(diff['shrank']) - 6} more")

    if diff["abandoned"]:
        had_any = True
        box_lines.append("  ✗ Abandoned Settlements:")
        for name in diff["abandoned"][:4]:
            box_lines.append(f"    ✗ {name}")
        if len(diff["abandoned"]) > 4:
            box_lines.append(f"    … and {len(diff['abandoned']) - 4} more")

    if diff["rebuilt"]:
        had_any = True
        box_lines.append("  ↻ Rebuilt Settlements:")
        for name in diff["rebuilt"][:4]:
            box_lines.append(f"    ↻ {name}")

    if diff["pros_up"]:
        had_any = True
        box_lines.append("  📈 Prosperity Rising:")
        for name, pros, delta in diff["pros_up"][:4]:
            box_lines.append(f"    {name}: {pros:.0%} (+{delta:.0%})")

    if diff["pros_down"]:
        had_any = True
        box_lines.append("  📉 Prosperity Falling:")
        for name, pros, delta in diff["pros_down"][:4]:
            box_lines.append(f"    {name}: {pros:.0%} ({delta:.0%})")

    if not had_any:
        box_lines.append("  (no significant changes this year)")
        box_lines.append("  The world sleeps.")

    box_lines.append("")
    box_lines.append(" [d] close ")

    # Calculate box dimensions
    box_h = len(box_lines) + 2
    box_w = max(len(l) for l in box_lines) + 4
    max_h = h - 2
    max_w = w - 2
    if box_h > max_h:
        box_h = max_h
    if box_w > max_w:
        box_w = max_w

    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    # Draw background box
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y in (0, box_h - 1) or x in (0, box_w - 1):
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["header"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["info"]))
            except curses.error:
                pass

    # Draw text
    for i, line in enumerate(box_lines):
        y = start_y + 1 + i
        if y >= h:
            break
        if i == 0:
            cp = _CP["header"]
            bold = True
        elif line.startswith("  ◆") or line.startswith("  ↑") or \
             line.startswith("  ↓") or line.startswith("  ✗") or \
             line.startswith("  ↻") or line.startswith("  📈") or \
             line.startswith("  📉"):
            cp = _CP["accent"]
            bold = False
        elif "close" in line:
            cp = _CP["dim"]
            bold = False
        else:
            cp = _CP["info"]
            bold = False
        _draw(stdscr, y, start_x + 2, line[:max_w - 2], cp, bold=bold)


# ── Help overlay ─────────────────────────────────────────────────────


VIEWER_HELP = [
    "wyrd — Simulation Viewer Help  (press any key to close)",
    "",
    "  Controls",
    "    Space           Pause / resume simulation",
    "    →              Step one year forward",
    "    + / =          Speed up simulation",
    "    - / _          Slow down simulation",
    "    [ / ]          Cycle through settlements on map",
    "    i              Inspect selected settlement (detail popup)",
    "    d              Toggle year-diff overlay",
    "    p              Toggle population chart overlay",
    "",
    "  General",
    "    h / ?          Toggle this help screen",
    "    q / ESC        Quit viewer",
    "",
    "  Auto-Pause",
    "    The viewer pauses automatically on significant events",
    "    (wars, cataclysms, foundings, discoveries, faction changes).",
    "    A flashing banner shows what triggered the pause.",
    "    Press Space to resume watching.",
    "",
    "  Trade Routes",
    "    Gold dotted lines show active trade between settlements.",
    "    A moving ◆ indicates goods in transit.",
    "    Routes form between complementary economies.",
    "",
    "  Tip: Watch the map evolve as centuries pass.",
    "       Use [ and ] to highlight settlements, then press 'i'.",
    "       New settlements appear in green.",
    "       Press 'd' to see exactly what changed each year.",
]


def _draw_help_overlay(stdscr, h, w):
    """Draw the help overlay centered on screen."""
    # Calculate dimensions
    box_h = len(VIEWER_HELP) + 2
    box_w = max(len(l) for l in VIEWER_HELP) + 4
    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    # Background
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y in (0, box_h - 1) or x in (0, box_w - 1):
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["header"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["info"]))
            except curses.error:
                pass

    # Text
    for i, line in enumerate(VIEWER_HELP):
        y = start_y + 1 + i
        if y >= h:
            break
        if line.startswith("  ") and not line.startswith("    "):
            cp = _CP["header"]
            bold = True
        else:
            cp = _CP["info"]
            bold = False
        _draw(stdscr, y, start_x + 2, line, cp, bold=bold)


# ── Input ────────────────────────────────────────────────────────────

def _handle_key(key, state):
    """Process a keypress. Returns (action, value) tuple.

    Actions: 'quit', 'toggle_pause', 'speed', 'step', 'toggle_chart', 'help'
    """
    if key in (ord("q"), 27):
        return "quit", None
    if key == ord(" "):
        return "toggle_pause", None
    if key in (ord("+"), ord("=")):
        return "speed", True   # up
    if key in (ord("-"), ord("_")):
        return "speed", False  # down
    if key == curses.KEY_RIGHT:
        return "step", None
    if key == ord("p"):
        return "toggle_chart", None
    if key in (ord("?"), ord("h")):
        return "help", None
    if key == ord("d"):
        return "toggle_diff", None
    if key == ord("i"):
        return "inspect", None
    if key == ord("["):
        return "prev_settlement", None
    if key == ord("]"):
        return "next_settlement", None
    return None, None


# ── Settlement detail popup ───────────────────────────────────────────


def _build_settlement_list(state) -> list[dict]:
    """Build a sorted list of active settlements with screen positions."""
    settlements = []
    for name, ss in state.settlements.items():
        if ss.is_active:
            settlements.append({
                "name": name,
                "x": ss.x,
                "y": ss.y,
                "population": ss.population,
                "kind": ss.kind,
                "prosperity": ss.prosperity,
                "food_stores": ss.food_stores,
                "health": ss.health,
                "founded_year": ss.founded_year,
                "region": ss.region,
                "religion": ss.religion,
                "economy_type": ss.economy_type,
            })
    settlements.sort(key=lambda s: s["x"] + s["y"] * 10000)  # row-major order
    return settlements


def _draw_settlement_cursor(stdscr, sel: dict, map_start_y: int):
    """Draw a cursor marker around the selected settlement on the map."""
    sy = map_start_y + sel["y"]
    sx = sel["x"]
    h, w = stdscr.getmaxyx()
    if sy >= h or sx >= w or sy < 0 or sx < 0:
        return
    try:
        # Draw a bright border around the settlement char
        ch = stdscr.inch(sy, sx)
        style = curses.color_pair(_CP["accent"]) | curses.A_REVERSE | curses.A_BOLD
        # Get the original char
        orig_char = chr(ch & 0xFF) if (ch & 0xFF) != 0 else "●"
        stdscr.addstr(sy, sx, orig_char, style)
    except curses.error:
        pass


_SETTLEMENT_HELP = [
    "wyrd — Settlement Detail  (press any key to close)",
    "",
    "  Use [ and ] to cycle through settlements on the map.",
    "  Press 'i' to inspect the highlighted settlement.",
    "",
]


def _draw_settlement_popup(stdscr, sel: dict | None, h: int, w: int):
    """Draw a settlement detail popup overlay."""
    if sel is None:
        return

    lines = []
    name_line = f" {sel['name']}"
    lines.append(name_line)
    lines.append("")
    lines.append(f"  Type:       {sel['kind'].title()}")
    lines.append(f"  Region:     {sel['region']}")
    lines.append(f"  Population: {sel['population']:,}")
    lines.append(f"  Position:   ({sel['x']}, {sel['y']})")
    lines.append("")

    # Prosperity bar
    pros_pct = max(0.0, min(1.0, sel['prosperity']))
    pros_filled = int(pros_pct * 10)
    pros_bar = "█" * pros_filled + "░" * (10 - pros_filled)
    pros_label = f"{pros_pct:.0%}"
    lines.append(f"  Prosperity: {pros_bar} {pros_label}")

    # Health bar
    health_pct = max(0.0, min(1.0, sel['health']))
    health_filled = int(health_pct * 10)
    health_bar = "█" * health_filled + "░" * (10 - health_filled)
    health_label = f"{health_pct:.0%}"
    lines.append(f"  Health:     {health_bar} {health_label}")

    # Food stores
    food_pct = max(0.0, min(1.0, sel['food_stores'] / 100.0))
    food_filled = int(food_pct * 10)
    food_bar = "█" * food_filled + "░" * (10 - food_filled)
    lines.append(f"  Food:       {food_bar} ({sel['food_stores']:.0f})")

    lines.append("")
    if sel.get('economy_type'):
        etype = sel['economy_type'].replace('_', ' ').title()
        lines.append(f"  Economy:    {etype}")
    if sel.get('religion'):
        lines.append(f"  Religion:   {sel['religion']}")
    if sel.get('founded_year', 0) > 0:
        lines.append(f"  Founded:    Year {sel['founded_year']}")
    lines.append("")
    lines.append(" [i] close ")

    # Calculate box dimensions
    box_h = len(lines) + 2
    box_w = max(len(l) for l in lines) + 4
    max_h = h - 2
    max_w = w - 2
    if box_h > max_h:
        box_h = max_h
    if box_w > max_w:
        box_w = max_w

    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    # Draw background box
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y in (0, box_h - 1) or x in (0, box_w - 1):
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["header"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["info"]))
            except curses.error:
                pass

    # Draw text
    for i, line in enumerate(lines):
        y = start_y + 1 + i
        if y >= h:
            break
        if i == 0:
            cp = _CP["header"]
            bold_style = True
        elif " close" in line:
            cp = _CP["dim"]
            bold_style = False
        elif line.startswith("  Type") or line.startswith("  Region") or \
             line.startswith("  Prosperity") or line.startswith("  Health") or \
             line.startswith("  Food") or line.startswith("  Economy") or \
             line.startswith("  Religion") or line.startswith("  Founded") or \
             line.startswith("  Population") or line.startswith("  Position"):
            cp = _CP["info"]
            bold_style = False
        else:
            cp = _CP["info"]
            bold_style = False
        _draw(stdscr, y, start_x + 2, line[:max_w - 2], cp, bold=bold_style)


# ── Speed labels ──────────────────────────────────────────────────────

_SPEED_LABELS = [
    (0.125, "Crawl"), (0.25, "Slow"), (0.5, "Walk"),
    (1, "Flow"), (2, "Trot"), (4, "Run"),
    (8, "Dash"), (16, "Fly"), (32, "Blink"), (64, "Zoom"),
    (128, "Decade"), (256, "Century"), (512, "Epoch"),
]

def _speed_label(speed: float) -> str:
    """Get qualitative label for a speed value."""
    best = "Crawl"
    for s, lbl in _SPEED_LABELS:
        if abs(speed - s) < 0.01 or speed >= s * 0.75:
            best = lbl
    return best


# ── Main loop ────────────────────────────────────────────────────────

def _loop(stdscr, world: World, years: int, chaos: float, offset: int):
    """Core curses loop."""
    _init()
    curses.curs_set(0)
    curses.use_default_colors()
    stdscr.nodelay(True)
    stdscr.keypad(True)

    # Sim state
    state = initialize_sim_state(world)
    rng_seed = world.seed + 4000000 + offset
    rng = random.Random(rng_seed)

    events: list[SimEvent] = []
    cur_year = 0
    cur_month = 0  # 0-11, for seasonal rendering
    paused = False
    speed = 2.0
    show_chart = False
    show_help = False
    show_diff = False
    running = True
    last = time.monotonic()
    accum = 0.0
    new_founds: set = set()
    total_simmed = 0
    frame_count = 0  # for trade route animation

    # Year-diff tracking
    prev_snapshot: dict | None = None
    last_diff: dict | None = None

    # Tile animation state: (x,y) -> remaining frames
    flash_tiles: dict[tuple[int, int], int] = {}
    FLASH_DURATION = 12  # frames to flash

    # Settlement cursor state
    settlement_list: list[dict] = []
    cursor_idx: int = 0
    selected_settlement: dict | None = None
    show_settlement_popup: bool = False

    # ── Pause-on-event ────────────────────────────────────────────
    PAUSE_EVENT_TYPES = {
        "founding", "abandonment",
        "war", "faction_war", "faction_collapse",
        "faction_vassal_revolt", "faction_coup",
        "earthquake", "volcanic_eruption", "great_plague",
        "tsunami", "meteor_strike", "great_fire", "magical_cataclysm",
        "discovery",
    }
    auto_pause_msg: str | None = None
    auto_pause_frames = 0
    AUTO_PAUSE_SHOW_FRAMES = 60  # show notification ~60 frames

    # Cache terrain for fast map rendering
    terrain = [[TERRAIN[world.terrain[y][x]]["char"]
                for x in range(world.width)]
               for y in range(world.height)]

    while running:
        h, w = stdscr.getmaxyx()
        if h < 10 or w < 50:
            time.sleep(0.5)
            continue
        frame_count += 1

        # ── Advance sim (month-level ticks) ────────────────────────────
        if not paused and cur_year < years:
            now = time.monotonic()
            dt = now - last
            last = now
            # Accumulate in months: speed * 12 months/sec
            month_accum = dt * speed * 12.0
            # Clip to avoid huge jumps on resume
            if month_accum > 60.0:
                month_accum = 60.0
            accum += month_accum
            while accum >= 1.0 and cur_year < years:
                accum -= 1.0
                cur_month += 1
                if cur_month >= 12:
                    cur_month = 0
                    cur_year += 1
                    # ── Year boundary: diff snapshot ──
                    if prev_snapshot is None:
                        prev_snapshot = _snapshot_populations(state)
                    last_diff = _compute_diff(prev_snapshot, state)
                    prev_snapshot = _snapshot_populations(state)

                # Month tick (handles year-end subsystems at month 11)
                tick_events = _simulate_month_tick(
                    world, state, rng, cur_year, cur_month, chaos,
                )
                events.extend(tick_events)
                total_simmed += 1

                # Track new foundings for flash animation
                for ev in tick_events:
                    if ev.event_type == "founding":
                        for sn in ev.affected_settlements:
                            ss = state.settlements.get(sn)
                            if ss:
                                new_founds.add((ss.x, ss.y))
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION

                # Flash growing/shrinking settlements (only at year end)
                if cur_month == 0 and last_diff:
                    for name, old, new_, delta in last_diff.get("grew", []):
                        ss = state.settlements.get(name)
                        if ss:
                            flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    for name, old, new_, delta in last_diff.get("shrank", []):
                        ss = state.settlements.get(name)
                        if ss:
                            flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    for name in last_diff.get("abandoned", []):
                        ss = state.settlements.get(name)
                        if ss:
                            flash_tiles[(ss.x, ss.y)] = FLASH_DURATION

        # ── Decay flash animation ────────────────────────────────────
        faded: list[tuple[int, int]] = []
        for pos, frames in flash_tiles.items():
            if frames <= 1:
                faded.append(pos)
        for pos in faded:
            del flash_tiles[pos]
        # Decay remaining
        flash_tiles = {pos: f - 1 for pos, f in flash_tiles.items() if f > 1}

        # ── Auto-pause on significant events ─────────────────────
        if not paused:
            # Check the most recent events for pause-worthy types
            pause_triggered = False
            for ev in reversed(events[-20:]):
                if ev.event_type in PAUSE_EVENT_TYPES:
                    icon = _EVENT_ICON.get(ev.event_type, "●")
                    # Only auto-pause for events in the current year
                    if ev.year == cur_year or (ev.year == cur_year - 1 and cur_month < 3):
                        auto_pause_msg = f" ⏸ {icon} {ev.description[:70]}"
                        pause_triggered = True
                        break
            if pause_triggered:
                paused = True
                auto_pause_frames = AUTO_PAUSE_SHOW_FRAMES
                last = time.monotonic()
                accum = 0.0

        # ── Build render world ───────────────────────────────────────
        sim_world = apply_sim_state_to_world(world, state)
        smap = _build_smap(sim_world)

        # Rebuild settlement list for cursor navigation
        settlement_list = _build_settlement_list(state)
        if settlement_list and cursor_idx >= len(settlement_list):
            cursor_idx = 0
        if not settlement_list:
            cursor_idx = 0

        # ── Layout ──────────────────────────────────────────────────
        events_h = max(3, h - 7 - 2)  # header(1)+stats(1)+map+events+footer(1)
        map_h = max(1, h - 7 - events_h - 1)

        # ── Draw ─────────────────────────────────────────────────────
        stdscr.erase()  # erase() marks dirty without flash-to-blank
        _draw_header(stdscr, world.seed, cur_year, years,
                     paused, speed, w, cur_month)
        _draw_stats(stdscr, state, speed)

        # Auto-pause notification overlay (fades after ~60 frames)
        if auto_pause_frames > 0:
            _draw_pause_notification(stdscr, auto_pause_msg, auto_pause_frames, h, w)
            auto_pause_frames -= 1
            if auto_pause_frames <= 0:
                auto_pause_msg = None

        _render_map(stdscr, sim_world, smap, map_h, w, new_founds, flash_tiles, cur_month)

        # Draw change overlay when paused (growth/shrinkage indicators)
        if paused:
            _draw_change_overlay(stdscr, state, last_diff, map_h)

        # Draw trade route animation (Phase 19)
        _draw_trade_routes(stdscr, state, smap, frame_count, map_h, w, paused)

        # Draw settlement cursor if we have settlements
        if settlement_list and cursor_idx < len(settlement_list) and not show_settlement_popup:
            _draw_settlement_cursor(stdscr, settlement_list[cursor_idx], 2)

        ev_start = 2 + map_h
        _draw_events(stdscr, events, events_h, ev_start, w)
        _draw_status_bar(stdscr, h, w, world.seed, cur_year, years, paused, speed, cur_month)

        # Overlays (last = on top)
        if show_settlement_popup and selected_settlement:
            _draw_settlement_popup(stdscr, selected_settlement, h, w)
        if show_diff:
            _draw_diff(stdscr, last_diff, h, w)
        if show_chart:
            _draw_chart(stdscr, state, h, w)
        if show_help:
            _draw_help_overlay(stdscr, h, w)

        stdscr.refresh()

        # ── Input ───────────────────────────────────────────────────
        key = stdscr.getch()
        while key != -1:
            act, val = _handle_key(key, state)
            if act == "quit":
                running = False
                break
            elif act == "toggle_pause":
                paused = not paused
                last = time.monotonic()
                accum = 0.0
            elif act == "speed":
                speed = min(speed * 2, 512.0) if val else max(speed / 2, 0.125)
            elif act == "step":
                if not paused:
                    paused = True
                if cur_year < years:
                    # Advance 12 months (one full year)
                    for _ in range(12):
                        if cur_year >= years:
                            break
                        cur_month += 1
                        if cur_month >= 12:
                            cur_month = 0
                            cur_year += 1
                            if prev_snapshot is None:
                                prev_snapshot = _snapshot_populations(state)
                            last_diff = _compute_diff(prev_snapshot, state)
                            prev_snapshot = _snapshot_populations(state)
                        tick_events = _simulate_month_tick(
                            world, state, rng, cur_year, cur_month, chaos,
                        )
                        events.extend(tick_events)
                        for ev in tick_events:
                            if ev.event_type == "founding":
                                for sn in ev.affected_settlements:
                                    ss = state.settlements.get(sn)
                                    if ss:
                                        flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    if last_diff:
                        for name, old, new_, delta in last_diff.get("grew", []):
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                        for name, old, new_, delta in last_diff.get("shrank", []):
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                        for name in last_diff.get("abandoned", []):
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION

                    # Show auto-pause banner on step if significant event occurred
                    step_pause_msg = None
                    for ev in reversed(events[-12:]):
                        if ev.event_type in PAUSE_EVENT_TYPES:
                            icon = _EVENT_ICON.get(ev.event_type, "●")
                            step_pause_msg = f" ⏸ {icon} {ev.description[:70]}"
                            break
                    if step_pause_msg:
                        auto_pause_msg = step_pause_msg
                        auto_pause_frames = AUTO_PAUSE_SHOW_FRAMES
            elif act == "toggle_chart":
                show_chart = not show_chart
            elif act == "toggle_diff":
                show_diff = not show_diff
            elif act == "help":
                show_help = not show_help
            elif act == "inspect":
                if settlement_list and cursor_idx < len(settlement_list):
                    if show_settlement_popup and selected_settlement:
                        # Close popup
                        show_settlement_popup = False
                        selected_settlement = None
                    else:
                        # Open popup for current cursor position
                        selected_settlement = settlement_list[cursor_idx]
                        show_settlement_popup = True
            elif act == "next_settlement":
                if settlement_list:
                    show_settlement_popup = False
                    selected_settlement = None
                    cursor_idx = (cursor_idx + 1) % len(settlement_list)
            elif act == "prev_settlement":
                if settlement_list:
                    show_settlement_popup = False
                    selected_settlement = None
                    cursor_idx = (cursor_idx - 1) % len(settlement_list)
            key = stdscr.getch()

        if not paused:
            time.sleep(0.008)


def view_simulation(world: World, num_years: int = 100,
                    chaos_factor: float = 0.3, seed_offset: int = 0):
    """Run the interactive simulation viewer.

    Shows the world map evolving year by year with pause/resume/speed.
    """
    try:
        curses.wrapper(_loop, world, num_years, chaos_factor, seed_offset)
        print("📹 Simulation viewing complete.")
    except Exception as e:
        print(f"⚠ Viewer error: {e}")
        raise
