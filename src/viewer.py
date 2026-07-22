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
                mh: int, mw: int, new_founds: set):
    """Render terrain + settlements into the map area (starting at line 2)."""
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
                elif info.get("active", True):
                    c = _CP["settlement"]
                else:
                    c = _CP["abandoned"]
            else:
                if wx < world.width and wy < world.height:
                    t = world.terrain[wy][wx]
                    char = TERRAIN[t]["char"]
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
    fmt = f" wyrd — Seed {seed}  [{year:,}/{total:,}]  "
    fmt += "⏸ PAUSED" if paused else "▶ RUNNING"
    fmt += f"  {speed:.1f}x/yr"
    _draw(stdscr, 0, 0, fmt, _CP["header"], bold=True)
    hint = " [Space]pause [+/-]speed [→]step [p]chart [q]quit "
    _draw(stdscr, 0, max(0, w - len(hint) - 1), hint, _CP["dim"])


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


def _draw_footer(stdscr, h, w):
    controls = (
        " [Space] pause/resume  [+/-] speed  [→] step  "
        "[p] pop chart  [q] quit"
    )
    _fill_line(stdscr, h - 1, _CP["dim"])
    _draw(stdscr, h - 1, 0, controls[:w - 1], _CP["dim"])


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


# ── Input ────────────────────────────────────────────────────────────

def _handle_key(key, state):
    """Process a keypress. Returns (action, value) tuple.

    Actions: 'quit', 'toggle_pause', 'speed', 'step', 'toggle_chart'
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
    running = True
    last = time.monotonic()
    accum = 0.0
    new_founds: set = set()
    total_simmed = 0

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
                tick_events = _simulate_tick(world, state, rng,
                                             cur_year, chaos)
                events.extend(tick_events)
                total_simmed += 1
                # Track new foundings
                new_founds = set()
                for ev in tick_events:
                    if ev.event_type == "founding":
                        for sn in ev.affected_settlements:
                            ss = state.settlements.get(sn)
                            if ss:
                                new_founds.add((ss.x, ss.y))

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
        _render_map(stdscr, sim_world, smap, map_h, w, new_founds)

        ev_start = 2 + map_h
        _draw_events(stdscr, events, events_h, ev_start, w)
        _draw_footer(stdscr, h, w)

        if show_chart:
            _draw_chart(stdscr, state, h, w)

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
                    tick_events = _simulate_tick(world, state, rng,
                                                 cur_year, chaos)
                    events.extend(tick_events)
            elif act == "toggle_chart":
                show_chart = not show_chart
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
