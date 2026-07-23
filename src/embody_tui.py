"""wyrd — Embodied Play TUI (Phase 19: Human-First UX).

Curses TUI for embody mode. Replaces the print/input interactive session
with a proper split-panel interface: stats sidebar, event log, bottom action bar,
and overlay dialogs for choices, travel, and market.

Usage:
    wyrd embody --seed 42                        # Default: print mode
    wyrd embody --seed 42 --tui                   # TUI mode
    wyrd embody --seed 42 --tui --name "Rikard"   # Named character in TUI
"""

import curses
import locale
import math
import os
import random
import sys
import time as time_module
from typing import Optional

from .world import World
from .embody import (
    PlayerCharacter, _OCCUPATIONS,
    _generate_character, _find_settlement_in_world,
    _status_line, _render_welcome, _render_news,
    _render_travel_options,
    _advance_time, _advance_year,
    _handle_interactive_events,
    _handle_market, _handle_travel,
    save_character, load_character,
    _auto_save,
    _record_legacy_event, _record_deed,
    _render_epilogue,
    _get_interactive_events,
    _resolve_choice, _label_for_event,
    _render_interactive_event,
    _maybe_travel_encounter,
    _skill_bonus, _gain_skill_xp,
    _change_reputation,
    _skill_level_from_xp,
)
from .sim import (
    initialize_sim_state, _simulate_month_tick, SimEvent,
    apply_sim_state_to_world,
)

# ── Color pairs ────────────────────────────────────────────────────────

_CP = {
    "title": 1,      # cyan
    "accent": 2,     # green
    "dim": 3,        # grey
    "normal": 4,     # default
    "highlight": 5,  # selected bg
    "border": 6,     # border grey
    "error": 7,      # red
    "warning": 8,    # yellow
    "gold": 9,       # gold
    "health_high": 10,
    "health_mid": 11,
    "health_low": 12,
    "skill": 13,     # blue
    "deed": 14,      # purple-ish
    "location": 15,  # teal
    "event_good": 16,
    "event_bad": 17,
    "event_info": 18,
    "header_bg": 19,
    "status_bar": 20,
}

SEASONS = ["Winter", "Spring", "Summer", "Autumn"]


def _init_colors():
    """Initialize curses color pairs."""
    curses.init_pair(_CP["title"], 45, -1)
    curses.init_pair(_CP["accent"], 46, -1)
    curses.init_pair(_CP["dim"], 240, -1)
    curses.init_pair(_CP["normal"], -1, -1)
    curses.init_pair(_CP["highlight"], -1, 236)
    curses.init_pair(_CP["border"], 242, -1)
    curses.init_pair(_CP["error"], 196, -1)
    curses.init_pair(_CP["warning"], 226, -1)
    curses.init_pair(_CP["gold"], 220, -1)
    curses.init_pair(_CP["health_high"], 46, -1)
    curses.init_pair(_CP["health_mid"], 226, -1)
    curses.init_pair(_CP["health_low"], 196, -1)
    curses.init_pair(_CP["skill"], 45, -1)
    curses.init_pair(_CP["deed"], 99, -1)
    curses.init_pair(_CP["location"], 44, -1)
    curses.init_pair(_CP["event_good"], 46, -1)
    curses.init_pair(_CP["event_bad"], 196, -1)
    curses.init_pair(_CP["event_info"], 45, -1)
    curses.init_pair(_CP["header_bg"], -1, 236)
    curses.init_pair(_CP["status_bar"], 15, 238)


def _draw(stdscr, y, x, text, cp, bold=False):
    """Safe text drawing at (y, x) with color pair."""
    h, w = stdscr.getmaxyx()
    if y >= h or y < 0 or x >= w:
        return
    style = curses.color_pair(cp) | (curses.A_BOLD if bold else 0)
    try:
        stdscr.addstr(y, x, text[:max(0, w - x - 1)], style)
    except curses.error:
        pass


def _fill_line(stdscr, y, cp, ch=" "):
    """Fill a row with a character using the given color pair."""
    h, w = stdscr.getmaxyx()
    if y >= h or y < 0:
        return
    try:
        stdscr.addstr(y, 0, ch * w, curses.color_pair(cp))
    except curses.error:
        pass


def _draw_border_box(stdscr, y, x, height, width, cp):
    """Draw a simple border box."""
    if height < 3 or width < 4:
        return
    for dy in range(height):
        if y + dy >= stdscr.getmaxyx()[0]:
            break
        if dy == 0 or dy == height - 1:
            _draw(stdscr, y + dy, x, "─" * (width - 1), cp)
        else:
            _draw(stdscr, y + dy, x, "│", cp)
            _draw(stdscr, y + dy, x + width - 1, "│", cp)
    _draw(stdscr, y, x, "┌", cp, bold=True)
    _draw(stdscr, y, x + width - 1, "┐", cp, bold=True)
    _draw(stdscr, y + height - 1, x, "└", cp, bold=True)
    _draw(stdscr, y + height - 1, x + width - 1, "┘", cp, bold=True)


def _season_for_month(month: int) -> str:
    """Return season name for month (0-11)."""
    if month in (11, 0, 1):
        return "Winter"
    elif month in (2, 3, 4):
        return "Spring"
    elif month in (5, 6, 7):
        return "Summer"
    return "Autumn"


def _health_bar(health: int, width: int = 10) -> tuple[str, int]:
    """Return (health bar string, color pair) for given health value."""
    filled = max(0, min(width, round(health / 100 * width)))
    bar = "█" * filled + "░" * (width - filled)
    if health >= 60:
        cp = _CP["health_high"]
    elif health >= 30:
        cp = _CP["health_mid"]
    else:
        cp = _CP["health_low"]
    return bar, cp


# ── Help overlay ───────────────────────────────────────────────────────

EMBODY_HELP = [
    "wyrd — Embodied Play  (press any key to close)",
    "",
    "  Navigation",
    "    n / →           Next year (advance 12 months)",
    "    1m               One month",
    "    1w               One week (~.25 months)",
    "",
    "  Actions",
    "    t                Travel to another settlement",
    "    m                Open market / shop",
    "    s                Character status summary",
    "",
    "  Interactive Events",
    "    When events occur, 1/2/3 keys make choices",
    "",
    "  General",
    "    ? / h            Toggle this help",
    "    q                Quit embody mode",
    "",
    "  Tips",
    "    Skills grow with use — fight, trade, persuade, survive, craft.",
    "    Travel takes 1-2 months (simulated in days).",
    "    Age affects health — the old grow frail.",
    "    Your character auto-saves after each time advance.",
]

_EMBODY_LOG_ICONS = {
    "plague": "☠", "famine": "🌾", "war": "⚔", "discovery": "✦",
    "prosperity": "↑", "disaster": "🌋", "exodus": "→",
    "founding": "▲", "abandonment": "✗", "trade_boom": "💰",
    "religious_tension": "✞", "divine_blessing": "✧",
    "holy_pilgrimage": "🚶", "heresy": "🔥",
    "faction_war": "🏴", "faction_alliance": "🤝",
    "faction_power_shift": "⬇", "faction_collapse": "💀",
    "faction_peace_treaty": "☮", "faction_leadership_change": "👑",
    "faction_trade_pact": "📦", "faction_vassal_revolt": "⚡",
    "faction_coup": "🗡",
    "earthquake": "〰", "volcanic_eruption": "🌋",
    "great_plague": "💀", "tsunami": "🌊",
    "meteor_strike": "☄", "great_fire": "🔥",
    "magical_cataclysm": "🌀", "trade_collapse": "📉",
}


def _draw_help_overlay(stdscr):
    """Draw centered help panel."""
    h, w = stdscr.getmaxyx()
    lines = EMBODY_HELP
    box_h = min(len(lines) + 2, h - 2)
    box_w = min(max(len(l) for l in lines) + 4, w - 2)
    start_y = max(0, (h - box_h) // 2)
    start_x = max(0, (w - box_w) // 2)

    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["border"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["normal"]))
            except curses.error:
                pass

    for i, line in enumerate(lines):
        yy = start_y + 1 + i
        if yy >= h:
            break
        if not line:
            continue
        if line.startswith("  ") and not line.startswith("    "):
            _draw(stdscr, yy, start_x + 2, line, _CP["accent"], bold=True)
        elif line.startswith("    "):
            _draw(stdscr, yy, start_x + 2, line, _CP["normal"])
        else:
            _draw(stdscr, yy, start_x + 2, line, _CP["title"], bold=True)


def _draw_choice_overlay(stdscr, choices):
    """Draw interactive event choice overlay."""
    h, w = stdscr.getmaxyx()
    lines = []
    for i, sc in enumerate(choices):
        lines.append(f"  {sc.icon} {sc.prompt}")
        lines.append(f"    1. {_label_for_event(sc.event_type, 0)}")
        lines.append(f"    2. {_label_for_event(sc.event_type, 1)}")
        lines.append(f"    3. {_label_for_event(sc.event_type, 2)}")

    box_h = min(len(lines) + 4, h - 4)
    box_w = min(max(len(l) for l in lines) + 6, w - 4)
    start_y = max(2, (h - box_h) // 2)
    start_x = max(2, (w - box_w) // 2)

    # Dim background behind overlay
    for dy in range(h):
        for dx in range(w):
            try:
                ch = stdscr.inch(dy, dx)
                if ch != -1:
                    stdscr.addch(dy, dx, " ", curses.A_DIM)
            except curses.error:
                pass

    # Draw box
    for y in range(box_h):
        for x in range(box_w):
            try:
                if y == 0 or y == box_h - 1 or x == 0 or x == box_w - 1:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["border"]))
                else:
                    stdscr.addch(start_y + y, start_x + x, " ",
                                 curses.color_pair(_CP["normal"]))
            except curses.error:
                pass

    _draw(stdscr, start_y, start_x, "┌" + "─" * (box_w - 2) + "┐", _CP["border"], bold=True)
    _draw(stdscr, start_y + box_h - 1, start_x, "└" + "─" * (box_w - 2) + "┘", _CP["border"], bold=True)

    # Render lines
    y_offset = 0
    for line in lines:
        yy = start_y + 2 + y_offset
        if yy >= h:
            break
        if line.startswith("    "):
            _draw(stdscr, yy, start_x + 2, line.strip(), _CP["normal"])
        elif line.strip().startswith("1."):
            _draw(stdscr, yy, start_x + 2, line.strip(), _CP["accent"], bold=True)
        elif line.strip().startswith("2."):
            _draw(stdscr, yy, start_x + 2, line.strip(), _CP["warning"], bold=True)
        elif line.strip().startswith("3."):
            _draw(stdscr, yy, start_x + 2, line.strip(), _CP["error"], bold=True)
        else:
            _draw(stdscr, yy, start_x + 2, line.strip(), _CP["title"], bold=True)
        y_offset += 1

    _draw(stdscr, start_y + box_h - 2, start_x + 2, f"Choose (1-3):", _CP["dim"])
    stdscr.refresh()


def _draw_travel_overlay(stdscr, options):
    """Draw travel destinations overlay."""
    h, w = stdscr.getmaxyx()
    lines = []
    for i, opt in enumerate(options[:10]):
        lines.append(f"  {i + 1}. {opt}")
    if len(options) > 10:
        lines.append(f"  ... and {len(options) - 10} more")

    box_h = min(len(lines) + 4, h - 4)
    box_w = min(max(len(l) for l in lines) + 6, w - 4)
    start_y = max(2, (h - box_h) // 2)
    start_x = max(2, (w - box_w) // 2)

    for dy in range(h):
        for dx in range(w):
            try:
                stdscr.addch(dy, dx, " ", curses.A_DIM)
            except curses.error:
                pass

    # Box
    _draw_border_box(stdscr, start_y, start_x, box_h, box_w, _CP["border"])
    _draw(stdscr, start_y + 1, start_x + 2, "Travel Destinations", _CP["location"], bold=True)
    _draw(stdscr, start_y + 2, start_x + 2, "─" * (box_w - 6), _CP["dim"])

    for i, line in enumerate(lines):
        yy = start_y + 3 + i
        if yy >= h:
            break
        _draw(stdscr, yy, start_x + 2, line, _CP["normal"])

    _draw(stdscr, start_y + box_h - 2, start_x + 2,
          "Enter # to travel, 0 or q to cancel", _CP["dim"])


def _draw_choice_result(stdscr, msg: str, duration: float = 2.0):
    """Draw a temporary result message centered on screen."""
    h, w = stdscr.getmaxyx()
    lines = msg.split("\n")
    y = h // 2 - len(lines) // 2
    x = max(0, (w - max(len(l) for l in lines)) // 2)
    for i, line in enumerate(lines):
        _draw(stdscr, y + i, x, line, _CP["normal"])
    stdscr.refresh()
    time_module.sleep(duration)


# ── Main TUI loop ──────────────────────────────────────────────────────

def _render_sidebar(stdscr, char: PlayerCharacter, y: int, x: int,
                    width: int, height: int) -> int:
    """Render the character stats sidebar panel. Returns next y position."""
    if width < 10:
        return y

    # Character name + profession
    _draw(stdscr, y, x, f" {char.name}", _CP["title"], bold=True)
    y += 1
    _draw(stdscr, y, x, f" {char.profession.title()}", _CP["dim"])
    y += 2

    # Health bar
    bar, hcp = _health_bar(char.health, width - 4)
    _draw(stdscr, y, x, f" ❤{bar} {char.health:>3}", hcp, bold=True)
    y += 1

    # Gold
    _draw(stdscr, y, x, f" ✦ Gold: {char.gold}", _CP["gold"], bold=True)
    y += 2

    # Age
    age_color = _CP["dim"] if char.age < 45 else _CP["warning"]
    _draw(stdscr, y, x, f" 🎂 Age: {char.age}", age_color)
    y += 1

    # Season + Year
    season = _season_for_month(char.month)
    season_cp = _CP["accent"] if season == "Spring" else (
        _CP["accent"] if season == "Summer" else (
            _CP["warning"] if season == "Autumn" else _CP["dim"]))
    _draw(stdscr, y, x, f" 📅 {season}, Yr {char.year}", season_cp)
    y += 1

    # Month
    _draw(stdscr, y, x, f"    Month {char.month + 1}", _CP["dim"])
    y += 1

    # Location
    loc = f" {char.settlement}"
    _draw(stdscr, y, x, loc, _CP["location"], bold=True)
    y += 1
    _draw(stdscr, y, x, f" {char.region}", _CP["dim"])
    y += 2

    # Divider
    _draw(stdscr, y, x, " " + "─" * (width - 2), _CP["border"])
    y += 1

    # Skills
    _draw(stdscr, y, x, " Skills:", _CP["skill"], bold=True)
    y += 1
    skill_colors = {"combat": _CP["error"], "trade": _CP["gold"],
                    "persuasion": _CP["accent"], "survival": _CP["location"],
                    "crafting": _CP["deed"]}
    for s_name in ("combat", "trade", "persuasion", "survival", "crafting"):
        level = char.skills.get(s_name, 1)
        xp_needed = max(1, _skill_level_from_xp(
            char.skill_xp.get(s_name, 0) + 1) * 5)
        bar_w = min(width - 6, 12)
        filled = max(0, min(bar_w, level))
        sk_bar = "█" * filled + "░" * (bar_w - filled)
        icon = {"combat": "⚔", "trade": "💰", "persuasion": "🗣",
                "survival": "🏕", "crafting": "🔨"}.get(s_name, "•")
        scp = skill_colors.get(s_name, _CP["normal"])
        _draw(stdscr, y, x, f" {icon} {s_name[:4]:>4} {sk_bar} {level:>2}", scp)
        y += 1

    y += 1
    # Divider
    _draw(stdscr, y, x, " " + "─" * (width - 2), _CP["border"])
    y += 1

    # Deeds (compact)
    if char.deeds:
        _draw(stdscr, y, x, f" ⚜ Deeds: {len(char.deeds)}", _CP["deed"])
        y += 1
        for d in char.deeds[-3:]:
            _draw(stdscr, y, x, f"   {d[:width - 6]}", _CP["dim"])
            y += 1
        y += 1

    # Visited settlements
    visited = len(char.settlements_visited)
    _draw(stdscr, y, x, f" 👣 Visited: {visited} place{'s' if visited != 1 else ''}", _CP["dim"])
    y += 1

    # Reputation
    if char.reputation:
        rep_items = sorted(char.reputation.items(), key=lambda kv: -abs(kv[1]))[:2]
        for s, v in rep_items:
            color = _CP["accent"] if v > 0 else _CP["error"]
            sign = "+" if v > 0 else ""
            _draw(stdscr, y, x, f"   {s[:12]:>12}: {sign}{v}", color)
            y += 1

    return y


def _render_event_log(stdscr, events: list, log_lines: list,
                      y: int, x: int, width: int, height: int,
                      scroll_offset: int) -> list:
    """Render the event log panel. Returns updated log_lines list."""
    h_avail = height - 2  # header + padding
    if h_avail <= 0:
        return log_lines

    # Header
    _fill_line(stdscr, y, _CP["header_bg"])
    title = " Event Log"
    count_info = f" ({len(log_lines)})"
    _draw(stdscr, y, x, title, _CP["title"], bold=True)
    _draw(stdscr, y, x + width - len(count_info) - 1, count_info, _CP["dim"])
    y += 1

    # Render visible portion
    visible = log_lines[scroll_offset:scroll_offset + h_avail]
    for i, line in enumerate(visible):
        yy = y + i
        if yy >= y + h_avail:
            break
        # Color the line based on content
        cp = _CP["normal"]
        if line.startswith("☠") or line.startswith("⚔") or line.startswith("🗡"):
            cp = _CP["event_bad"]
        elif line.startswith("▲") or line.startswith("💰"):
            cp = _CP["event_good"]
        elif line.startswith("✦") or line.startswith("📜"):
            cp = _CP["event_info"]
        truncated = line[:width - 2]
        _draw(stdscr, yy, x + 1, truncated, cp)

    # Scroll indicator
    if scroll_offset > 0:
        _draw(stdscr, y, x + width - 3, "▲", _CP["dim"])
    if scroll_offset + h_avail < len(log_lines):
        _draw(stdscr, y + h_avail - 1, x + width - 3, "▼", _CP["dim"])

    return log_lines


def _render_status_bar(stdscr, char: PlayerCharacter, h: int, w: int):
    """Render the bottom status/action bar."""
    _fill_line(stdscr, h - 1, _CP["status_bar"])
    actions = (
        "[n] Year  [1m] Month  [t] Travel  "
        "[m] Market  [s] Status  [?] Help  [q] Quit"
    )
    season = _season_for_month(char.month)
    right = f" {season}, Yr {char.year}  "
    _draw(stdscr, h - 1, 1, actions, _CP["status_bar"])
    _draw(stdscr, h - 1, w - len(right) - 1, right, _CP["status_bar"],
          bold=True)


def embody_tui_play(world: World,
                    name: str | None = None,
                    years: int = 100,
                    chaos: float = 0.3,
                    load_save: bool = True) -> None:
    """Enter the embodied play mode TUI for a world.

    A curses interface with stats sidebar, event log, and action bar.
    """
    try:
        curses.wrapper(_tui_main, world, name, years, chaos, load_save)
    except KeyboardInterrupt:
        pass


def _tui_main(stdscr, world: World,
              name: str | None, years: int,
              chaos: float, load_save: bool) -> None:
    """Main curses loop for embody TUI."""
    # Setup curses
    locale.setlocale(locale.LC_ALL, '')
    curses.curs_set(0)
    curses.use_default_colors()
    _init_colors()
    stdscr.nodelay(False)
    stdscr.keypad(True)

    rng = random.Random(world.seed + 5000000)

    # Load or generate character
    char: PlayerCharacter | None = None
    loaded = False
    if load_save:
        char = load_character(world.seed)
        if char is not None:
            loaded = True

    if char is None:
        char = _generate_character(world, rng, name=name)

    # Initialize sim state
    from .sim import initialize_sim_state, simulate_years
    state = initialize_sim_state(world)

    # Fast-forward sim to character's year if loading
    if loaded and char.year > 0:
        simulate_years(world, state, rng, char.year, chaos)
        apply_sim_state_to_world(world, state)

    # State
    events: list[SimEvent] = []
    log_lines: list[str] = []
    running = True
    show_help = False
    show_travel = False
    show_market = False
    travel_options: list[str] = []
    log_scroll = 0
    status_msg = ""
    status_time = 0.0
    in_choice = False
    current_choices: list = []
    choice_selected = False
    choice_result = ""

    # Add welcome message to log
    welcome = f"✦ You are {char.name}, a {char.profession} in {char.settlement}."
    log_lines.append(welcome)

    while running and char.alive and char.year < years:
        h, w = stdscr.getmaxyx()
        if h < 12 or w < 40:
            _draw(stdscr, 0, 0, "Terminal too small! Need at least 40x12.", _CP["error"])
            stdscr.refresh()
            time_module.sleep(0.5)
            continue

        stdscr.erase()

        # ── Layout ──────────────────────────────────────────────────────
        sidebar_width = max(20, w // 3)
        sidebar_width = min(sidebar_width, 36)
        log_x = sidebar_width
        log_width = w - sidebar_width - 1
        status_y = h - 1
        header_y = 0

        # ── Header line ─────────────────────────────────────────────────
        _fill_line(stdscr, header_y, _CP["header_bg"])
        title = " ◈ wyrd — Embodied Play "
        _draw(stdscr, header_y, 1, title, _CP["title"], bold=True)
        right_info = f" seed {world.seed} | {char.name} "
        _draw(stdscr, header_y, max(1, w - len(right_info) - 2),
              right_info, _CP["dim"])

        # ── Sidebar ─────────────────────────────────────────────────────
        _render_sidebar(stdscr, char, header_y + 2, 1,
                        sidebar_width - 1, h - 3)

        # ── Vertical divider ────────────────────────────────────────────
        divider_x = sidebar_width
        if divider_x < w:
            for dy in range(header_y + 1, h - 1):
                _draw(stdscr, dy, divider_x, "│", _CP["border"])

        # ── Event log ───────────────────────────────────────────────────
        _render_event_log(stdscr, events, log_lines,
                          header_y + 1, log_x + 1, log_width - 1, h - 2,
                          log_scroll)

        # ── Status bar ──────────────────────────────────────────────────
        _render_status_bar(stdscr, char, h, w)

        # ── Scroll indicator on log ─────────────────────────────────────
        if log_scroll > 0:
            _draw(stdscr, header_y + 2, w - 2, "▲", _CP["dim"])

        # ── Handle overlays ─────────────────────────────────────────────

        # 1. Choice overlay (highest priority)
        if in_choice and current_choices:
            _draw_choice_overlay(stdscr, current_choices)

        # 2. Travel overlay
        elif show_travel:
            _draw_travel_overlay(stdscr, travel_options)

        # 3. Help overlay
        elif show_help:
            _draw_help_overlay(stdscr)

        # 4. Status message bar
        if status_msg and time_module.monotonic() - status_time < 3.0:
            _draw(stdscr, header_y + 1, 1, status_msg[:w - 2], _CP["accent"],
                  bold=True)

        stdscr.refresh()

        # ── Input ──────────────────────────────────────────────────────
        try:
            key = stdscr.getkey()
        except KeyboardInterrupt:
            break
        except Exception:
            continue

        # Handle key by mode
        if in_choice:
            if key in ("1", "2", "3"):
                opt_idx = int(key) - 1
                sc = current_choices[0] if current_choices else None
                if sc and opt_idx < 3:
                    outcome, label = _resolve_choice(sc, opt_idx, char, world, rng)

                    # Apply consequences
                    if outcome.gold_delta > 0:
                        char.total_gold_earned += outcome.gold_delta
                    elif outcome.gold_delta < 0:
                        char.total_gold_spent += abs(outcome.gold_delta)
                    char.gold += outcome.gold_delta
                    char.health = max(0, min(100, char.health + outcome.health_delta))
                    if outcome.inventory_add and outcome.inventory_add not in char.inventory:
                        char.inventory.append(outcome.inventory_add)
                    if outcome.travel_dest:
                        char.settlement = outcome.travel_dest
                        if outcome.travel_dest not in char.settlements_visited:
                            char.settlements_visited.append(outcome.travel_dest)

                    # Record deed
                    et = sc.event_type
                    deed_map = {
                        ("war", 0): "Fought in a war",
                        ("plague", 0): "Helped the sick during a plague",
                        ("discovery", 0): "Explored ancient ruins",
                        ("stranger", 0): "Showed kindness to a stranger",
                        ("exodus", 0): "Joined an exodus to new lands",
                        ("bandit", 0): "Fought off bandits",
                        ("festival", 0): "Joined a festival celebration",
                        ("monster_hunt", 0): "Hunted a deadly creature",
                    }
                    deed_key = (et, opt_idx)
                    if deed_key in deed_map:
                        _record_deed(char, deed_map[deed_key])

                    _record_legacy_event(char,
                                         f"{label} — {outcome.description[:60]}")

                    result_output = f"{label}: {outcome.description}"
                    suffix = ""
                    if outcome.gold_delta > 0:
                        suffix += f" +{outcome.gold_delta}g"
                    elif outcome.gold_delta < 0:
                        suffix += f" {outcome.gold_delta}g"
                    if outcome.health_delta > 0:
                        suffix += f" +{outcome.health_delta}hp"
                    elif outcome.health_delta < 0:
                        suffix += f" {outcome.health_delta}hp"
                    if suffix:
                        result_output += suffix

                    log_lines.append(f"📜 {result_output[:80]}")
                    if outcome.travel_dest:
                        log_lines.append(f"🚶 Arrived in {outcome.travel_dest}")

                    if char.health <= 0:
                        char.alive = False
                        log_lines.append(f"☠ {char.name} has died from their wounds.")

                in_choice = False
                current_choices = []
                continue
            elif key == "q":
                in_choice = False
                current_choices = []
                continue

        elif show_travel:
            if key in ("0", "q", "\x1b"):
                show_travel = False
            elif key.isdigit():
                idx = int(key) - 1
                if 0 <= idx < len(travel_options):
                    dest = travel_options[idx]
                    dest_name = dest.split(" (")[0].strip()
                    log_lines.append(f"🚶 Traveling to {dest_name}...")
                    show_travel = False

                    # Travel logic
                    encounter_happened = _maybe_travel_encounter(char, world)
                    char.settlement = dest_name
                    if dest_name not in char.settlements_visited:
                        char.settlements_visited.append(dest_name)
                        if len(char.settlements_visited) >= 3:
                            _record_deed(char,
                                         f"Visited {len(char.settlements_visited)} settlements")

                    travel_months = 1 + (1 if encounter_happened else 0)
                    new_events = _advance_time(char, world, state, rng,
                                                chaos, months=travel_months)
                    events.extend(new_events)
                    _auto_save(char, world)
                    log_lines.append(
                        f"📅 {travel_months} month{'s' if travel_months > 1 else ''} pass")
                    if encounter_happened:
                        log_lines.append("⚠ Survived a travel encounter!")
                    continue
            continue

        elif show_market:
            stdscr.erase()
            _draw(stdscr, 0, 0, " Market — press q to return", _CP["title"], bold=True)
            _draw(stdscr, 1, 0, f" Gold: {char.gold}g  |  Items: {len(char.inventory)}",
                  _CP["gold"])
            # Quick market: show buy list
            from .shop import shop_items_for_economy
            settlement_data = state.settlements.get(char.settlement)
            economy_type = settlement_data.economy_type if settlement_data else "trading"
            pop = settlement_data.population if settlement_data else 500
            mrng = random.Random(world.seed + 6000000 + hash(char.settlement) % 100000 + char.year)
            items = shop_items_for_economy(economy_type or "trading", mrng, pop)

            y = 3
            for idx, item in enumerate(items):
                if item.get("stock", 0) > 0:
                    name = item.get("name", "?")
                    price = item.get("price", 0)
                    stock = item.get("stock", 1)
                    _draw(stdscr, y, 2, f"{idx + 1:>2}. {name:<20} {price:>6}g  ({stock})",
                          _CP["normal"])
                    y += 1

            _draw(stdscr, y + 1, 2, "[#] buy  [s] sell items  [q] exit market", _CP["dim"])
            stdscr.refresh()

            try:
                mkey = stdscr.getkey()
            except Exception:
                mkey = "q"

            if mkey == "q":
                show_market = False
                continue
            elif mkey == "s":
                # Simple sell: show inventory
                stdscr.erase()
                _draw(stdscr, 0, 0, " Sell Items — press q to return", _CP["title"], bold=True)
                seen = list(dict.fromkeys(char.inventory))
                y = 2
                for idx, name in enumerate(seen):
                    from .shop import estimate_item_value
                    value = estimate_item_value(name)
                    sell_price = max(1, value // 2)
                    _draw(stdscr, y, 2, f"{idx + 1:>2}. {name:<20} → {sell_price:>4}g",
                          _CP["normal"])
                    y += 1
                _draw(stdscr, y + 1, 2, "[#] sell  [q] back", _CP["dim"])
                stdscr.refresh()

                try:
                    skey = stdscr.getkey()
                except Exception:
                    skey = "q"
                if skey.isdigit():
                    idx2 = int(skey) - 1
                    all_names = list(dict.fromkeys(char.inventory))
                    if 0 <= idx2 < len(all_names):
                        item_name = all_names[idx2]
                        if item_name in char.inventory:
                            from .shop import estimate_item_value
                            value = estimate_item_value(item_name)
                            sell_price = max(1, value // 2)
                            char.inventory.remove(item_name)
                            char.gold += sell_price
                            char.total_gold_earned += sell_price
                            log_lines.append(f"💰 Sold {item_name} for {sell_price}g")
            elif mkey.isdigit():
                idx2 = int(mkey) - 1
                if 0 <= idx2 < len(items):
                    item = items[idx2]
                    if item.get("stock", 0) > 0 and char.gold >= item["price"]:
                        char.gold -= item["price"]
                        char.total_gold_spent += item["price"]
                        char.inventory.append(item["name"])
                        item["stock"] = item.get("stock", 1) - 1
                        log_lines.append(f"💰 Bought {item['name']} ({item['price']}g)")
                        _record_deed(char, f"Purchased at {char.settlement} market")
            continue

        elif show_help:
            if key in ("q", "\x1b", "?", "h"):
                show_help = False
            continue

        else:
            # Normal mode input
            if key in ("q", "Q", "\x1b"):
                running = False
            elif key in ("?", "h"):
                show_help = True
            elif key in ("n", "\uf704"):  # n or KEY_RIGHT
                months = 12
                new_events = _advance_time(char, world, state, rng,
                                            chaos, months=months)
                events.extend(new_events)

                # Log events
                season = _season_for_month(char.month)
                log_lines.append(f"📅 Year {char.year} — {season}")
                _add_events_to_log(log_lines, new_events, char)

                _auto_save(char, world)

                # Interactive events
                choices = _get_interactive_events(char, world, rng, events)
                if choices:
                    in_choice = True
                    current_choices = choices
                    for sc in choices:
                        log_lines.append(f"📌 Event: {sc.prompt[:60]}")

                # Check death
                if char.health <= 0:
                    char.alive = False
                    log_lines.append(f"☠ {char.name} has died.")

                # Keep scrolling to latest
                log_scroll = max(0, len(log_lines) - (h - 4))

            elif key == "1":
                # One month
                months = 1
                new_events = _advance_time(char, world, state, rng,
                                            chaos, months=months)
                events.extend(new_events)
                season = _season_for_month(char.month)
                log_lines.append(f"📅 Month {char.month + 1}, Y{char.year} — {season}")
                _add_events_to_log(log_lines, new_events, char)
                _auto_save(char, world)

                if char.health <= 0:
                    char.alive = False
                    log_lines.append(f"☠ {char.name} has died.")

                log_scroll = max(0, len(log_lines) - (h - 4))

            elif key in ("t", "T"):
                options = _render_travel_options(char, world)
                if options:
                    show_travel = True
                    travel_options = options
                else:
                    status_msg = "No destinations available"
                    status_time = time_module.monotonic()

            elif key in ("m", "M"):
                show_market = True

            elif key in ("s", "S"):
                status_msg = (f"{char.name} | HP {char.health}/100 | "
                              f"Gold {char.gold} | Age {char.age} | "
                              f"Inv: {len(char.inventory)} items")
                status_time = time_module.monotonic()

            elif key == "KEY_UP":
                log_scroll = max(0, log_scroll - 3)
            elif key == "KEY_DOWN":
                max_scroll = max(0, len(log_lines) - (h - 4))
                log_scroll = min(max_scroll, log_scroll + 3)
            elif key == "KEY_PPAGE":  # Page Up
                log_scroll = max(0, log_scroll - (h - 6))
            elif key == "KEY_NPAGE":  # Page Down
                max_scroll = max(0, len(log_lines) - (h - 4))
                log_scroll = min(max_scroll, log_scroll + (h - 6))

    # ── Epilogue ────────────────────────────────────────────────────────
    curses.endwin()

    if not char.alive:
        print(_render_epilogue(char))
        path_ = f"wyrd-{world.seed}-char.json"
        if os.path.exists(path_):
            os.remove(path_)
        print(f"\n  The wyrd spins on...")
        try:
            continue_str = input(
                f"  Continue as an heir? (y/n): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            continue_str = "n"
        if continue_str != "n":
            # Generate heir
            rng_heir = random.Random(world.seed + 6000000 + char.year)
            first_names = ["Aldric", "Beorn", "Cedric", "Elara", "Freya",
                           "Gareth", "Hakon", "Ivar", "Kara", "Leif",
                           "Mira", "Nora", "Orin", "Runa", "Sigurd",
                           "Tova", "Ulf", "Vera", "Astrid", "Brynn"]
            surname = char.name.split()[-1] if " " in char.name else "sson"
            heir_name = f"{rng_heir.choice(first_names)} {surname}"
            heir_gold = max(20, char.gold // 2)
            heir_inventory = [
                item for item in char.inventory
                if item not in ("a cryptic note", "an old map")
            ][:3]
            heir = PlayerCharacter(
                name=heir_name,
                settlement=char.settlement,
                region=char.region,
                profession=_OCCUPATIONS[rng_heir.randint(0, len(_OCCUPATIONS) - 1)],
                gold=heir_gold,
                health=100,
                age=rng_heir.randint(16, 25),
                year=char.year,
                inventory=heir_inventory,
                parent_name=char.name,
            )
            heir.settlements_visited = [s for s in char.settlements_visited if s]
            heir.skill_xp = {
                s: max(0, char.skill_xp.get(s, 0) * 2 // 3)
                for s in ("combat", "trade", "persuasion", "survival", "crafting")
            }
            from .embody import SKILL_NAMES
            for s in SKILL_NAMES:
                heir.skills[s] = max(1, _skill_level_from_xp(heir.skill_xp.get(s, 0)))
            heir.reputation = {
                s: max(-10, min(10, v // 2))
                for s, v in char.reputation.items()
            } if char.reputation else {}
            _record_legacy_event(heir, f"Born as heir of {char.name}")
            save_character(heir, world.seed)
            print(f"\n  {heir_name}, a {heir.profession}, carries on the line.")
            print(f"  Child of {char.name}.")
            print(f"  💾 Saved. Run 'wyrd embody --seed {world.seed} --tui' to continue.")
            curses.endwin()
            embody_tui_play(world, name=heir_name, years=years,
                           chaos=chaos, load_save=True)
    else:
        _auto_save(char, world)
        print(f"\n  {char.name} lived to age {char.age} and witnessed {char.year} years.")
        print(f"  💾 Character saved — run 'wyrd embody --seed {world.seed} --tui' to resume.")

    active = state.num_settlements
    pop = state.total_population
    print(f"\n  World at Year {char.year}: {active} settlements, {pop:,} souls")


def _add_events_to_log(log_lines: list, new_events: list, char: PlayerCharacter):
    """Add events to the log with appropriate icons."""
    for ev in new_events[-8:]:  # Last 8 events
        icon = _EMBODY_LOG_ICONS.get(ev.event_type, "•")
        nearby = (char.region in (ev.affected_regions or []) or
                  char.settlement in (ev.affected_settlements or []))
        prefix = "📍" if nearby else "  "
        truncated = ev.description[:70]
        log_lines.append(f"{prefix} {icon} {truncated}")
