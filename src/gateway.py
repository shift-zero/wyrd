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
import os
import random
import re
import time as time_module

from .world import World
from .generate import generate_world
from .serialize import load_world

# ── Color palette ─────────────────────────────────────────────────────

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


# ── Sub-view launchers (end/restart curses) ────────────────────────────

def _launch_terminal_view(stdscr, title: str, render_fn, *args, **kwargs):
    """Launch a terminal-only view: end curses, print output, wait for key."""
    curses.endwin()
    text = render_fn(*args, **kwargs)
    print(text)
    input(f"\n── {title} ── Press Enter to return to wyrd gateway...")
    # Restart curses for the gateway
    curses.start_color()
    curses.use_default_colors()
    _init_colors()
    stdscr.keypad(True)
    curses.curs_set(0)
    return stdscr


def _launch_curses_view(stdscr, title: str, view_fn, *args, **kwargs):
    """Launch a curses sub-view: end gateway curses, run view, restart curses."""
    curses.endwin()
    try:
        curses.wrapper(view_fn, *args, **kwargs)
    except Exception:
        pass
    # Restart curses for the gateway
    curses.start_color()
    curses.use_default_colors()
    _init_colors()
    new_stdscr.keypad(True)
    curses.curs_set(0)
    return new_stdscr


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

        stdscr.clear()

        # ── Draw splash ──────────────────────────────────────────────
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

        # ── World list ───────────────────────────────────────────────
        if not worlds:
            _draw(stdscr, list_start_y, 2, "No worlds found. Press [g] to generate one.", CP["dim"])
        else:
            _draw(stdscr, list_start_y, 2,
                  f"Recent Worlds ({len(worlds)} found)", CP["title"], bold=True)
            list_start_y += 1

            max_visible = h - list_start_y - 5
            scroll_offset = max(0, selected_idx - max_visible + 1) if max_visible > 0 else 0
            visible_worlds = worlds[scroll_offset:scroll_offset + max_visible]

            for i, w_info in enumerate(visible_worlds):
                abs_idx = scroll_offset + i
                y = list_start_y + i
                is_selected = (abs_idx == selected_idx)

                if is_selected:
                    _fill_line(stdscr, y, CP["highlight"])

                marker = "\u25b8 " if is_selected else "  "
                _draw(stdscr, y, 2, marker, CP["accent"], bold=True)

                x_pos = 4
                seed_str = f"#{w_info['seed']}"
                _draw(stdscr, y, x_pos, seed_str, CP["seed"], bold=True)
                x_pos += len(seed_str) + 1

                info = (f"  {w_info['dimensions']}  "
                        f"{w_info['population']:,} souls \u00b7 {w_info['regions']} regions")
                _draw(stdscr, y, x_pos, info, CP["dim"])

                # Badges (right-aligned)
                bx = w - 20
                if _has_sim_file(w_info["seed"]):
                    _draw(stdscr, y, bx, "S", CP["badge_s"], bold=True); bx += 2
                if w_info["has_magic"]:
                    _draw(stdscr, y, bx, "M", CP["badge_m"], bold=True); bx += 2
                if w_info["has_chronicles"]:
                    _draw(stdscr, y, bx, "C", CP["badge_c"], bold=True); bx += 2
                if w_info["has_narrative"]:
                    _draw(stdscr, y, bx, "N", CP["badge_n"], bold=True); bx += 2
                if w_info["has_lore"]:
                    _draw(stdscr, y, bx, "L", CP["badge_l"], bold=True)

        # ── Status message ────────────────────────────────────────────
        if status_msg and time_module.monotonic() - status_time < 4:
            _fill_line(stdscr, h - 3, CP["border"])
            _draw(stdscr, h - 3, 2, f"  {status_msg}", CP["accent"])
        else:
            status_msg = ""

        # ── Footer ────────────────────────────────────────────────────
        footer_y = h - 2
        footer = (" [\u2191\u2193] select  [g] generate  [l] load  [e] explore  "
                  "[v] view sim  [d] describe  [s] run  [t] routes  [?] help  [q] quit")
        _fill_line(stdscr, footer_y, CP["dim"])
        _draw(stdscr, footer_y, 0, footer[:w - 1], CP["dim"])

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
            running = False

        elif key == ord("?") or key == ord("h"):
            show_help = True

        elif key == ord("r"):
            worlds = scan_worlds(".")
            selected_idx = min(selected_idx, max(0, len(worlds) - 1))
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
            if worlds:
                selected_idx = max(0, selected_idx - 1)

        elif key in (curses.KEY_DOWN, ord("j")):
            if worlds:
                selected_idx = min(len(worlds) - 1, selected_idx + 1)

        elif key in (10, 13, ord(" "), curses.KEY_ENTER):
            if worlds and 0 <= selected_idx < len(worlds):
                w_info = worlds[selected_idx]
                try:
                    world_in_session = load_world(w_info["path"])
                    status_msg = f"\u2705 Loaded wyrd #{world_in_session.seed}"
                except Exception as e:
                    status_msg = f"\u274c Load failed: {e}"
                status_time = time_module.monotonic()

        elif key == ord("e"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded \u2014 generate or select one first"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .explore import explore_world
            stdscr = _launch_curses_view(stdscr, "Explorer", explore_world, world)

        elif key == ord("v"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .viewer import view_simulation
            stdscr = _launch_curses_view(stdscr, "Simulation Viewer",
                                         view_simulation, world, 100, 0.3)

        elif key == ord("d"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .render import render_lore
            draw_help_panel(stdscr, ["wyrd — World Lore  (press any key to close)", ""] +
                            [f"  {l}" for l in render_lore(world).split("\n")])
            stdscr.refresh()
            stdscr.getch()

        elif key == ord("c"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            from .chronicles import generate_chronicles
            from .render import render_chronicles
            if not world.chronicles:
                world.chronicles = generate_chronicles(world, world.narrative)
            chron_text = render_chronicles(world)
            lines = ["wyrd — Chronicles  (press any key to close)", ""]
            for l in chron_text.split("\n"):
                lines.append(f"  {l}")
            draw_help_panel(stdscr, lines)
            stdscr.refresh()
            stdscr.getch()

        elif key == ord("s"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
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
            _init_colors()
            stdscr.keypad(True)
            curses.curs_set(0)

        elif key == ord("x"):
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
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
            world = world_in_session
            if world is None and worlds and 0 <= selected_idx < len(worlds):
                try:
                    world = load_world(worlds[selected_idx]["path"])
                except Exception:
                    status_msg = "\u274c Could not load world"
                    status_time = time_module.monotonic()
                    continue
            if world is None:
                status_msg = "\u274c No world loaded"
                status_time = time_module.monotonic()
                continue
            world_in_session = world
            curses.endwin()
            # Run a quick sim to get trade routes
            from .sim import run_simulation
            from .serialize import save_sim_state
            from .economy import reconstruct_routes
            from .render import render_trade_route_map
            sim_chars = world.narrative.characters if world.narrative else None
            result = run_simulation(world, num_years=100, seed_offset=0,
                                    chaos_factor=0.1, snapshot_interval=50,
                                    characters=sim_chars)
            save_sim_state(result, f"wyrd-{world.seed}-sim.json")
            routes = reconstruct_routes(result.trade_routes)
            print(render_trade_route_map(world, routes, result.settlements,
                                         title=f"wyrd {world.seed} — Trade Routes (Year {result.year})"))
            input(f"\n── Press Enter to return to wyrd gateway...")
            stdscr = curses.initscr()
            _init_colors()
            stdscr.keypad(True)
            curses.curs_set(0)

        if key == ord("q"):
            break


def gateway_main():
    """Entry point for the gateway TUI."""
    try:
        curses.wrapper(_gateway_loop)
    except KeyboardInterrupt:
        pass
