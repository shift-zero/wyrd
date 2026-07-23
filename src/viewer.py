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
    initialize_sim_state, _simulate_tick, simulate_years,
    apply_sim_state_to_world, SimState, SimEvent,
)

# ── Color pairs (1-22) ───────────────────────────────────────────────

_CP = {
    "deep_water": 1, "shallow": 2, "sand": 3, "grass": 4,
    "forest": 5, "hills": 6, "mountains": 7, "snow": 8, "river": 9,
    "settlement": 10, "abandoned": 11, "new_found": 12,
    "header": 13, "status": 14, "dim": 15, "accent": 17,
    "info": 18, "war": 19, "famine": 20, "plague": 21, "good": 22,
}

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
                flash_tiles: dict | None = None):
    """Render terrain + settlements into the map area (starting at line 2)."""
    flash_tiles = flash_tiles or {}
    for sy in range(mh):
        wy = sy  # no vertical offset in viewer — show top-left
        if wy >= world.height:
            break
        line = ""
        colors = []
        for sx in range(min(mw, world.width)):
            wx = sx
            key = (wx, wy)
            if key in smap:
                info = smap[key]
                char = info["char"]
                if key in new_founds:
                    c = _CP["new_found"]
                elif key in flash_tiles:
                    # Flash between yellow and bright green
                    frames = flash_tiles[key]
                    if frames % 3 < 2:
                        c = _CP["new_found"]  # bright green flash
                    else:
                        c = _CP["settlement"]  # normal yellow
                elif info.get("active", True):
                    c = _CP["settlement"]
                else:
                    c = _CP["abandoned"]
            else:
                if wx < world.width and wy < world.height:
                    t = world.terrain[wy][wx]
                    char = TERRAIN[t]["char"]
                    # Terrain flash animation (cataclysm-changed tiles)
                    if key in flash_tiles:
                        frames = flash_tiles[key]
                        if frames % 3 < 2:
                            c = _CP["accent"]  # bright flash for terrain
                        else:
                            c = _cp(t)
                    else:
                        c = _cp(t)
                else:
                    char = " "
                    c = 4
            line += char
            colors.append(c)
        # Write line char by char (curses handles individual attrs)
        for i, ch in enumerate(line):
            try:
                stdscr.addch(2 + sy, i, ch, curses.color_pair(colors[i]))
            except curses.error:
                break


def _draw_header(stdscr, seed, year, total, paused, speed, w):
    """Clean header bar with wyrd title and sim status."""
    fmt = f" wyrd — Seed {seed}  "
    mode = "⏸ PAUSED" if paused else "▶ RUNNING"
    mode_color = _CP["status"] if paused else _CP["accent"]
    yr_str = f" Year {year:,}/{total:,}"
    speed_str = f" {speed:.1f}x"
    _fill_line(stdscr, 0, _CP["header"])
    _draw(stdscr, 0, 0, fmt, _CP["header"], bold=True)
    _draw(stdscr, 0, len(fmt), mode, mode_color, bold=True)
    _draw(stdscr, 0, max(0, w - len(speed_str) - 2), speed_str, _CP["dim"])
    _draw(stdscr, 0, max(0, w - len(speed_str) - len(yr_str) - 4), yr_str, _CP["info"])


def _draw_stats(stdscr, state: SimState):
    active = state.num_settlements
    abandoned = state.num_abandoned
    pop = state.total_population
    text = (f" Settlements: {active} active"
            f"{f', {abandoned} abandoned' if abandoned else ''}"
            f"  │  Pop: {pop:,}  │  Year {state.year}")
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


def _draw_status_bar(stdscr, h, w, seed, year, total, paused, speed):
    """Persistent status bar showing mode, progress, and keybind hints."""
    # Left: mode indicator
    if paused:
        mode_str = f" ⏸ PAUSED  Seed {seed}  Year {year:,}/{total:,}  {speed:.1f}x"
    else:
        mode_str = f" ▶ RUNNING  Seed {seed}  Year {year:,}/{total:,}  {speed:.1f}x"

    # Right: context-sensitive key hints
    if paused:
        hints = " [Space] resume  [→] step  [+/-] speed  [p] chart  [d] diff  [?] help  [q] quit"
    else:
        hints = " [Space] pause  [+/-] speed  [→] step  [p] chart  [d] diff  [?] help  [q] quit"

    _fill_line(stdscr, h - 1, _CP["dim"])
    _draw(stdscr, h - 1, 0, mode_str, _CP["accent"] if not paused else _CP["status"], bold=not paused)
    _draw(stdscr, h - 1, max(0, w - len(hints) - 1), hints[:w - len(mode_str) - 3], _CP["dim"])


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
    "    d              Toggle year-diff overlay",
    "    p              Toggle population chart overlay",
    "",
    "  General",
    "    h / ?          Toggle this help screen",
    "    q / ESC        Quit viewer",
    "",
    "  Tip: Watch the map evolve as centuries pass.",
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
    return None, None


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

    # Year-diff tracking
    prev_snapshot: dict | None = None
    last_diff: dict | None = None

    # Tile animation state: (x,y) -> remaining frames
    flash_tiles: dict[tuple[int, int], int] = {}
    FLASH_DURATION = 12  # frames to flash

    # Cache terrain for fast map rendering
    terrain = [[TERRAIN[world.terrain[y][x]]["char"]
                for x in range(world.width)]
               for y in range(world.height)]

    while running:
        h, w = stdscr.getmaxyx()
        if h < 10 or w < 50:
            time.sleep(0.5)
            continue

        # ── Advance sim ──────────────────────────────────────────────
        if not paused and cur_year < years:
            now = time.monotonic()
            dt = now - last
            last = now
            accum += dt * speed
            while accum >= 1.0 and cur_year < years:
                accum -= 1.0
                cur_year += 1
                # Snapshot before tick for diff computation
                if prev_snapshot is None:
                    prev_snapshot = _snapshot_populations(state)
                tick_events = _simulate_tick(world, state, rng,
                                             cur_year, chaos)
                events.extend(tick_events)
                total_simmed += 1
                # Compute diff after tick
                last_diff = _compute_diff(prev_snapshot, state)
                prev_snapshot = _snapshot_populations(state)

                # Track new foundings and changed settlements for animation
                new_founds = set()
                for ev in tick_events:
                    if ev.event_type == "founding":
                        for sn in ev.affected_settlements:
                            ss = state.settlements.get(sn)
                            if ss:
                                new_founds.add((ss.x, ss.y))
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION

                # Add growing/shrinking settlements to flash animation
                if last_diff:
                    for name, old, new_, delta in last_diff["grew"]:
                        ss = state.settlements.get(name)
                        if ss:
                            flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    for name, old, new_, delta in last_diff["shrank"]:
                        ss = state.settlements.get(name)
                        if ss:
                            flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    for name in last_diff["abandoned"]:
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

        # ── Build render world ───────────────────────────────────────
        sim_world = apply_sim_state_to_world(world, state)
        smap = _build_smap(sim_world)

        # ── Layout ──────────────────────────────────────────────────
        events_h = max(3, h - 7 - 2)  # header(1)+stats(1)+map+events+footer(1)
        map_h = max(1, h - 7 - events_h - 1)

        # ── Draw ─────────────────────────────────────────────────────
        stdscr.clear()
        _draw_header(stdscr, world.seed, cur_year, years,
                     paused, speed, w)
        _draw_stats(stdscr, state)
        _render_map(stdscr, sim_world, smap, map_h, w, new_founds, flash_tiles)

        ev_start = 2 + map_h
        _draw_events(stdscr, events, events_h, ev_start, w)
        _draw_status_bar(stdscr, h, w, world.seed, cur_year, years, paused, speed)

        # Overlays (last = on top)
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
                speed = min(speed * 2, 64.0) if val else max(speed / 2, 0.125)
            elif act == "step":
                if not paused:
                    paused = True
                if cur_year < years:
                    cur_year += 1
                    # Snapshot before tick
                    prev_snapshot = _snapshot_populations(state)
                    tick_events = _simulate_tick(world, state, rng,
                                                 cur_year, chaos)
                    events.extend(tick_events)
                    # Compute diff
                    last_diff = _compute_diff(prev_snapshot, state)
                    # Track new foundings for flash
                    for ev in tick_events:
                        if ev.event_type == "founding":
                            for sn in ev.affected_settlements:
                                ss = state.settlements.get(sn)
                                if ss:
                                    flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                    if last_diff:
                        for name, old, new_, delta in last_diff["grew"]:
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                        for name, old, new_, delta in last_diff["shrank"]:
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
                        for name in last_diff["abandoned"]:
                            ss = state.settlements.get(name)
                            if ss:
                                flash_tiles[(ss.x, ss.y)] = FLASH_DURATION
            elif act == "toggle_chart":
                show_chart = not show_chart
            elif act == "toggle_diff":
                show_diff = not show_diff
            elif act == "help":
                show_help = not show_help
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
