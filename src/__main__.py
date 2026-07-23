"""wyrd — Generative Fantasy Sandbox CLI."""

import argparse
import os
import sys
from .generate import generate_world
from .render import render_map, render_brief, render_lore, render_characters, render_events, render_quests, render_narrative, render_chronicles, render_magic, render_factions, ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color
from .serialize import save_world, load_world
from .export_html import export_world_html
from .export_svg import export_world_svg
from .export_ttrpg import export_world_ttrpg
from .religion import generate_pantheon
from .adventure import generate_adventure_zones, render_zones, render_zone_detail
from .faction import generate_factions


def _get_world(args) -> 'World':
    """Either load from file or generate from seed."""
    if hasattr(args, 'load') and args.load:
        return load_world(args.load)
    import random
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    return generate_world(seed, width=args.width, height=args.height)


def _get_world_and_state(args):
    """Get world and optionally load sim state."""
    world = _get_world(args)

    # Try to load sim state
    snapshot_year = getattr(args, 'snapshot_year', None)
    from .serialize import load_sim_state
    from .sim import SimState

    sim_file = f"wyrd-{world.seed}-sim.json"
    sim_data = load_sim_state(sim_file)
    if sim_data is None:
        sim_data = load_sim_state(sim_file + ".gz")
    if sim_data is None:
        return world, None

    if snapshot_year is not None:
        # Load specific snapshot year
        raw = sim_data.get("snapshots", {}).get(str(snapshot_year), None)
        if raw is not None:
            state = SimState(year=raw["year"])
            for name, sd in raw.get("settlements", {}).items():
                from .sim import SettlementSnapshot
                state.settlements[name] = SettlementSnapshot(**sd)
            state.world_modifiers = raw.get("world_modifiers", [])
            state.trade_routes = raw.get("trade_routes", [])
            return world, state
        return world, None

    # Load final state
    final = sim_data.get("final_state")
    if final:
        state = SimState(year=final.get("year", 0))
        for name, sd in final.get("settlements", {}).items():
            from .sim import SettlementSnapshot
            try:
                state.settlements[name] = SettlementSnapshot(**sd)
            except TypeError:
                # Handle older save format with missing fields
                ss = SettlementSnapshot(name=sd.get("name", name), region=sd.get("region", ""),
                                        x=sd.get("x", 0), y=sd.get("y", 0),
                                        population=sd.get("population", 0), kind=sd.get("kind", "hamlet"))
                ss.is_active = sd.get("is_active", True)
                ss.founded_year = sd.get("founded_year", 0)
                ss.prosperity = sd.get("prosperity", 0.5)
                ss.food_stores = sd.get("food_stores", 100.0)
                ss.health = sd.get("health", 1.0)
                state.settlements[name] = ss
        state.world_modifiers = final.get("world_modifiers", [])
        state.trade_routes = final.get("trade_routes", [])
        return world, state

    return world, None


def _apply_snapshot_if_needed(world: 'World', args) -> 'World':
    """If the command supports --snapshot-year and it's set, apply sim state."""
    snapshot_year = getattr(args, 'snapshot_year', None)
    if snapshot_year is None:
        return world

    from .sim import apply_sim_state_to_world, SimState, SettlementSnapshot, SimEvent
    from .serialize import load_sim_state

    sim_file = f"wyrd-{world.seed}-sim.json"
    sim_data = load_sim_state(sim_file)
    if sim_data is None:
        # Try gzip-compressed variant
        sim_data = load_sim_state(sim_file + ".gz")
    if sim_data is None:
        print(f"⚠ No simulation data found for wyrd #{world.seed} (expected {sim_file})")
        return world

    # Check for snapshot at the requested year
    raw = sim_data.get("snapshots", {}).get(str(snapshot_year), None)
    if raw is None:
        print(f"⚠ No snapshot at year {snapshot_year}. Available years: "
              f"{sorted(int(k) for k in sim_data.get('snapshots', {}).keys())}")
        return world

    # Reconstruct SimState from the snapshot dict
    state = SimState(year=raw["year"])
    for name, sd in raw.get("settlements", {}).items():
        state.settlements[name] = SettlementSnapshot(**sd)
    state.world_modifiers = raw.get("world_modifiers", [])
    for pr in raw.get("population_record", []):
        state.population_record.append(pr)

    print(f"📂 Loaded wyrd #{world.seed} at year {snapshot_year} from simulation")
    return apply_sim_state_to_world(world, state)


def _add_common_gen_args(parser):
    """Add common world generation arguments to a subparser."""
    parser.add_argument("--seed", type=int, default=None,
                        help="World seed (random if omitted)")
    parser.add_argument("--width", type=int, default=80)
    parser.add_argument("--height", type=int, default=40)


def _add_load_arg(parser):
    """Add --load argument."""
    parser.add_argument("--load", type=str, default=None,
                        help="Load world from JSON file (overrides --seed/generation)")
    _add_common_gen_args(parser)


def main():
    parser = argparse.ArgumentParser(
        prog="wyrd",
        description="Generative fantasy sandbox — build worlds in the terminal."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── generate ───────────────────────────────────────────────────
    gen = sub.add_parser("generate", help="Generate a new world")
    _add_common_gen_args(gen)
    gen.add_argument("--no-settlements", action="store_true",
                     help="Hide settlement markers")
    gen.add_argument("--brief", action="store_true",
                     help="Show one-line summary instead of map")
    gen.add_argument("--lore", action="store_true",
                     help="Show lore (culture, history, features, relationships)")
    gen.add_argument("--narrative", action="store_true",
                     help="Show narrative (characters, events, quests)")
    gen.add_argument("--save", type=str, default=None,
                     help="Save world to a JSON file")

    # ── describe ───────────────────────────────────────────────────
    desc = sub.add_parser("describe", help="Describe a generated world (lore only)")
    _add_load_arg(desc)

    # ── save ───────────────────────────────────────────────────────
    save_cmd = sub.add_parser("save", help="Save a generated world to a JSON file")
    _add_common_gen_args(save_cmd)
    save_cmd.add_argument("--output", "-o", type=str, default=None,
                          help="Output file path (default: wyrd-{seed}.json)")
    save_cmd.add_argument("--snapshot-year", type=int, default=None,
                          help="Apply sim state at a specific year before saving")

    # ── load ───────────────────────────────────────────────────────
    load_cmd = sub.add_parser("load", help="Load and display a saved world")
    load_cmd.add_argument("file", type=str, help="Path to world JSON file")
    load_cmd.add_argument("--brief", action="store_true",
                          help="Show one-line summary")
    load_cmd.add_argument("--lore", action="store_true",
                          help="Show lore only")
    load_cmd.add_argument("--no-settlements", action="store_true",
                          help="Hide settlement markers")

    # ── export ─────────────────────────────────────────────────────
    export_cmd = sub.add_parser("export", help="Export a world to HTML or SVG")
    _add_load_arg(export_cmd)
    export_cmd.add_argument("--output", "-o", type=str, default=None,
                            help="Output file path")
    export_cmd.add_argument("--format", "-f", type=str, default="html",
                            choices=["html", "svg", "ttrpg"],
                            help="Export format (default: html)")
    export_cmd.add_argument("--open", action="store_true",
                            help="Open the HTML file in browser after export")
    export_cmd.add_argument("--snapshot-year", type=int, default=None,
                            help="Load sim state at a specific year (from saved sim file)")

    # ── explore ────────────────────────────────────────────────────
    explore = sub.add_parser("explore", help="Explore a world interactively (pager)")
    _add_load_arg(explore)
    explore.add_argument("--snapshot-year", type=int, default=None,
                         help="Load sim state at a specific year (from saved sim file)")

    # ── query ──────────────────────────────────────────────────────
    query_cmd = sub.add_parser("query", help="Query a world with natural language")
    _add_load_arg(query_cmd)
    query_cmd.add_argument("query_text", type=str, nargs="*",
                           help='Query text, e.g. "tell me about the northlands"')
    query_cmd.add_argument("--no-color", action="store_true",
                           help="Disable ANSI color in output")
    query_cmd.add_argument("--snapshot-year", type=int, default=None,
                           help="Load sim state at a specific year (from saved sim file)")

    # ── characters ─────────────────────────────────────────────────
    chars_cmd = sub.add_parser("characters", help="List characters in a world")
    _add_load_arg(chars_cmd)

    # ── events ─────────────────────────────────────────────────────
    events_cmd = sub.add_parser("events", help="Show event timeline for a world")
    _add_load_arg(events_cmd)

    # ── quests ─────────────────────────────────────────────────────
    quests_cmd = sub.add_parser("quests", help="Show quests available in a world")
    _add_load_arg(quests_cmd)

    # ── narrative ──────────────────────────────────────────────────
    narr_cmd = sub.add_parser("narrative",
                               help="Show complete narrative (characters, events, quests)")
    _add_load_arg(narr_cmd)

    # ── run (simulation) ───────────────────────────────────────────
    run_cmd = sub.add_parser("run",
                              help="Run year-by-year simulation on a world")
    _add_load_arg(run_cmd)
    run_cmd.add_argument("--years", type=int, default=100,
                         help="Number of years to simulate (default: 100)")
    run_cmd.add_argument("--chaos", type=float, default=0.1,
                         help="Chaos factor 0.0-1.0 (default: 0.1)")
    run_cmd.add_argument("--seed-offset", type=int, default=0,
                         help="Seed offset for branching (default: 0)")
    run_cmd.add_argument("--summary", action="store_true",
                         help="Show only summary, not detailed year log")
    run_cmd.add_argument("--snapshot-year", type=int, default=None,
                         help="Load world state at a specific year (from saved sim)")
    run_cmd.add_argument("--compact", action="store_true",
                         help="Save sim state as gzip-compressed JSON (smaller files)")

    # ── view ────────────────────────────────────────────────────────
    view_cmd = sub.add_parser("view",
                              help="Run interactive simulation viewer (curses)")
    _add_load_arg(view_cmd)
    view_cmd.add_argument("--years", type=int, default=100,
                          help="Number of years to simulate (default: 100)")
    view_cmd.add_argument("--chaos", type=float, default=0.3,
                          help="Chaos factor 0.0-1.0 (default: 0.3)")
    view_cmd.add_argument("--seed-offset", type=int, default=0,
                          help="Seed offset for branching (default: 0)")

    # ── branch ─────────────────────────────────────────────────────
    branch_cmd = sub.add_parser("branch",
                                help="Compare branching simulation timelines")
    _add_load_arg(branch_cmd)
    branch_cmd.add_argument("--years", type=int, default=200,
                            help="Number of years to simulate (default: 200)")
    branch_cmd.add_argument("--chaos", type=float, default=0.3,
                            help="Chaos factor 0.0-1.0 (default: 0.3)")
    branch_cmd.add_argument("--offsets", type=int, nargs="+", default=[0, 1],
                            help="Seed offsets to compare (default: 0 1)")

    # ── zones ───────────────────────────────────────────────────────
    zones_cmd = sub.add_parser("zones",
                               help="List adventure zones in a world")
    _add_load_arg(zones_cmd)
    zones_cmd.add_argument("--detail", action="store_true",
                           help="Show full descriptions for each zone")
    zones_cmd.add_argument("--id", type=int, default=None,
                           help="Show detail for a specific zone by index")

    # ── factions ───────────────────────────────────────────────────
    factions_cmd = sub.add_parser("factions",
                                  help="List factions in a world")
    _add_load_arg(factions_cmd)
    factions_cmd.add_argument("--id", type=int, default=None,
                              help="Show detail for a specific faction by index")

    # ── bestiary ────────────────────────────────────────────────────
    bestiary_cmd = sub.add_parser("bestiary",
                                   help="List creatures in the world's bestiary")
    _add_load_arg(bestiary_cmd)
    bestiary_cmd.add_argument("--id", type=int, default=None,
                               help="Show detail for a specific creature by index")
    bestiary_cmd.add_argument("--habitat", type=str, default=None,
                               help="Filter creatures by habitat (temperate, arid, tundra, tropical)")
    bestiary_cmd.add_argument("--tier", type=int, default=None,
                              help="Filter creatures by tier (1-5)")

    # ── economy ────────────────────────────────────────────────────
    economy_cmd = sub.add_parser("economy",
                                 help="Show trade routes and economies")
    _add_load_arg(economy_cmd)
    economy_cmd.add_argument("--routes", action="store_true",
                             help="Show active trade routes")
    economy_cmd.add_argument("--settlement", type=str, default=None,
                             help="Show economy detail for a specific settlement")
    economy_cmd.add_argument("--snapshot-year", type=int, default=None,
                             help="Load sim state at a specific year")

    # ── chronicles ─────────────────────────────────────────────────
    chron_cmd = sub.add_parser("chronicles",
                                help="Show era-based world history (chronicles)")
    _add_load_arg(chron_cmd)
    chron_cmd.add_argument("--format", "-f", type=str, default="text",
                            choices=["text", "html"],
                            help="Output format (default: text)")
    chron_cmd.add_argument("--output", "-o", type=str, default=None,
                            help="Output file path (HTML only)")

    # ── magic ───────────────────────────────────────────────────────
    magic_cmd = sub.add_parser("magic",
                                help="Show the magic system for a world")
    _add_load_arg(magic_cmd)
    magic_cmd.add_argument("--save", type=str, default=None,
                            help="Save world with magic system to JSON file")

    # ── pantheon ────────────────────────────────────────────────────
    pantheon_cmd = sub.add_parser("pantheon",
                                   help="Show the pantheon and religions of a world")
    _add_load_arg(pantheon_cmd)
    pantheon_cmd.add_argument("--save", type=str, default=None,
                               help="Save world with pantheon to JSON file")

    # ── serve ───────────────────────────────────────────────────────
    serve_cmd = sub.add_parser("serve",
                                help="Start web dashboard server")
    serve_cmd.add_argument("--seed", type=int, default=None,
                            help="World seed to show on startup")
    serve_cmd.add_argument("--port", "-p", type=int, default=8080,
                            help="Port to serve on (default: 8080)")
    serve_cmd.add_argument("--no-browser", action="store_true",
                            help="Don't open browser automatically")

    # ── ask ────────────────────────────────────────────────────────
    ask_cmd = sub.add_parser("ask",
                              help="Ask a natural-language question about a world")
    _add_load_arg(ask_cmd)
    ask_cmd.add_argument("question", type=str, nargs="*",
                         help='Natural-language question, e.g. "What is the most powerful city?"')
    ask_cmd.add_argument("--no-llm", action="store_true",
                         help="Force deterministic mode (no API call)")
    ask_cmd.add_argument("--snapshot-year", type=int, default=None,
                         help="Load sim state at a specific year (from saved sim file)")

    # ── worlds ──────────────────────────────────────────────────────
    worlds_cmd = sub.add_parser("worlds",
                                 help="List all generated worlds")
    worlds_cmd.add_argument("--dir", type=str, default=None,
                             help="Directory to scan (default: current directory)")
    worlds_cmd.add_argument("--json", action="store_true",
                             help="Output as JSON for scripting")

    args = parser.parse_args()

    # ── generate ───────────────────────────────────────────────────
    if args.command == "generate":
        import random
        seed = args.seed if args.seed is not None else random.randint(0, 999999)
        world = generate_world(seed, width=args.width, height=args.height)

        if args.save:
            save_world(world, args.save)
            print(f"💾 Saved to {args.save}")

        if args.brief:
            print(render_brief(world))
        elif args.lore:
            print(render_map(world, show_settlements=not args.no_settlements))
            print()
            print(render_lore(world))
            if args.narrative:
                print()
                print(render_narrative(world))
        elif args.narrative:
            print(render_map(world, show_settlements=not args.no_settlements))
            print()
            print(render_narrative(world))
        else:
            print(render_map(world, show_settlements=not args.no_settlements))

    # ── describe / load ────────────────────────────────────────────
    elif args.command == "describe":
        world = _get_world(args)
        print(render_lore(world))

    elif args.command == "load":
        world = load_world(args.file)
        if args.brief:
            print(render_brief(world))
        elif args.lore:
            print(render_lore(world))
        else:
            print(render_map(world, show_settlements=not args.no_settlements))
            print()
            print(render_lore(world))

    # ── characters ─────────────────────────────────────────────────
    elif args.command == "characters":
        world = _get_world(args)
        print(render_characters(world))

    # ── events ─────────────────────────────────────────────────────
    elif args.command == "events":
        world = _get_world(args)
        print(render_events(world))

    # ── quests ─────────────────────────────────────────────────────
    elif args.command == "quests":
        world = _get_world(args)
        print(render_quests(world))

    # ── narrative ──────────────────────────────────────────────────
    elif args.command == "narrative":
        world = _get_world(args)
        print(render_narrative(world))

    # ── run ─────────────────────────────────────────────────────────
    elif args.command == "run":
        world = _get_world(args)
        from .sim import run_simulation, render_sim_summary, render_sim_detailed, SimState
        from .serialize import load_sim_state, save_sim_state
        import os

        # Check if we already have a saved sim state at the requested year
        sim_file = f"wyrd-{world.seed}-sim.json"
        sim_state = None

        if args.snapshot_year is not None and os.path.exists(sim_file):
            sim_data = load_sim_state(sim_file)
            snap_key = str(args.snapshot_year)
            if sim_data and snap_key in sim_data.get("snapshots", {}):
                snap_raw = sim_data["snapshots"][snap_key]
                # Reconstruct SimState from dict
                sim_state = SimState(year=snap_raw["year"])
                for name, sd in snap_raw.get("settlements", {}).items():
                    sim_state.settlements[name] = SettlementSnapshot(**sd)
                sim_state.world_modifiers = snap_raw.get("world_modifiers", [])
                for pr in snap_raw.get("population_record", []):
                    sim_state.population_record.append(pr)
                print(f"📂 Loaded sim state at year {args.snapshot_year}")

        if sim_state is None:
            # Get narrative characters for named event integration
            sim_characters = getattr(world, 'narrative', None)
            sim_chars_list = sim_characters.characters if sim_characters else None

            result = run_simulation(
                world,
                num_years=args.years,
                seed_offset=args.seed_offset,
                chaos_factor=args.chaos,
                snapshot_interval=50,
                characters=sim_chars_list,
            )

            # Save simulation state
            save_sim_state(result, sim_file, compact=args.compact)

            if args.summary:
                print(render_sim_summary(result))
            else:
                print(render_sim_detailed(result, world))
        else:
            # Render from saved state
            from .render import render_map
            print(render_sim_summary_from_state(sim_state, world, world.seed))

    # ── view ─────────────────────────────────────────────────────────
    elif args.command == "view":
        world = _get_world(args)
        from .viewer import view_simulation
        view_simulation(
            world,
            num_years=args.years,
            chaos_factor=args.chaos,
            seed_offset=args.seed_offset,
        )

    # ── branch ────────────────────────────────────────────────────────
    elif args.command == "branch":
        world = _get_world(args)
        if not world.narrative:
            from .narrative import generate_narrative
            world.narrative = generate_narrative(world)
        if not world.chronicles:
            from .chronicles import generate_chronicles
            world.chronicles = generate_chronicles(world, world.narrative)

        from .branch import run_branch_comparison, render_branch_comparison
        # Ensure narrative exists with characters
        sim_characters = world.narrative.characters if world.narrative else None

        results = run_branch_comparison(
            world,
            num_years=args.years,
            chaos_factor=args.chaos,
            offsets=args.offsets,
        )
        print(render_branch_comparison(world, results))

    # ── zones ───────────────────────────────────────────────────────
    elif args.command == "zones":
        world = _get_world(args)
        if not world.adventure_zones:
            world.adventure_zones = generate_adventure_zones(world)
        if args.id is not None:
            idx = args.id
            if 0 <= idx < len(world.adventure_zones):
                print(render_zone_detail(world.adventure_zones[idx]))
            else:
                print(f"Zone #{idx} not found. There are {len(world.adventure_zones)} zones (0-{len(world.adventure_zones)-1}).")
        else:
            from .render import render_map
            print(render_map(world, show_settlements=True))
            print()
            print(render_zones(world, detail=args.detail))

    # ── factions ───────────────────────────────────────────────────
    elif args.command == "factions":
        world = _get_world(args)
        if not world.factions:
            world.factions = generate_factions(world)
        if args.id is not None:
            idx = args.id
            if 0 <= idx < len(world.factions):
                from .render import render_faction_detail
                print(render_faction_detail(world.factions[idx]))
            else:
                print(f"Faction #{idx} not found. There are {len(world.factions)} factions (0-{len(world.factions)-1}).")
        else:
            print(render_factions(world))

    # ── bestiary ────────────────────────────────────────────────────
    elif args.command == "bestiary":
        world = _get_world(args)
        if not world.bestiary:
            from .bestiary import generate_bestiary
            world.bestiary = generate_bestiary(world)
        if args.id is not None:
            idx = args.id
            if 0 <= idx < len(world.bestiary):
                from .render import render_creature_detail
                print(render_creature_detail(world.bestiary[idx]))
            else:
                print(f"Creature #{idx} not found. There are {len(world.bestiary)} creatures (0-{len(world.bestiary)-1}).")
        else:
            from .render import render_bestiary
            creatures = world.bestiary
            if args.habitat:
                creatures = [c for c in creatures if c.habitat == args.habitat]
            if args.tier:
                creatures = [c for c in creatures if c.tier == args.tier]
            # Temporarily replace world.bestiary for filtered rendering
            if args.habitat or args.tier:
                from .world import World
                old = world.bestiary
                world.bestiary = creatures
                print(render_bestiary(world))
                world.bestiary = old
            else:
                print(render_bestiary(world))

    # ── economy ────────────────────────────────────────────────────
    elif args.command == "economy":
        world, state = _get_world_and_state(args)
        from .render import ANSI_RESET, ANSI_BOLD, ANSI_DIM, _color
        from .economy import ECONOMY_ICONS, ECONOMY_COLORS, ECONOMY_TYPES, reconstruct_routes

        if args.settlement:
            # Show economy for a specific settlement
            s = state.settlements.get(args.settlement) if state else None
            if not s:
                # Check world settlements
                found = False
                for region in world.regions:
                    for s_obj in region.settlements:
                        if s_obj.name.lower() == args.settlement.lower():
                            print(f"{ANSI_BOLD}{s_obj.name}{ANSI_RESET}")
                            print(f"  Kind: {s_obj.kind} (pop {s_obj.population})")
                            print(f"  Economy type: no simulation data — run `wyrd run` first")
                            found = True
                            break
                    if found:
                        break
                if not found:
                    print(f"Settlement '{args.settlement}' not found.")
            else:
                econ_type = s.economy_type or "unknown"
                icon = ECONOMY_ICONS.get(econ_type, "?")
                color = _color(ECONOMY_COLORS.get(econ_type, 255))
                print(f"{ANSI_BOLD}{s.name}{ANSI_RESET}")
                print(f"  Kind: {color}{icon} {econ_type}{ANSI_RESET}")
                print(f"  Population: {s.population}")
                print(f"  Prosperity: {s.prosperity:.2f}")
                # Show trade routes to/from this settlement
                if state and state.trade_routes:
                    routes = reconstruct_routes(state.trade_routes)
                    relevant = [r for r in routes if r.is_active and (r.source == s.name or r.destination == s.name)]
                    if relevant:
                        print(f"  Trade routes ({len(relevant)}):")
                        for r in relevant:
                            partner = r.destination if r.source == s.name else r.source
                            print(f"    ↔ {partner}: {r.goods} (vol: {r.volume:.0%}, dist: {r.distance:.0f})")
        elif args.routes:
            # Show all active trade routes
            if not state or not state.trade_routes:
                print("No trade routes available. Run `wyrd run --seed X --years N` first.")
            else:
                routes = reconstruct_routes(state.trade_routes)
                active = [r for r in routes if r.is_active]
                if not active:
                    print(f"{ANSI_DIM}No active trade routes.{ANSI_RESET}")
                else:
                    print(f"{ANSI_BOLD}Trade Routes ({len(active)}):{ANSI_RESET}")
                    for r in active:
                        color = _color(220)
                        print(f"  {color}↔{ANSI_RESET} {r.source} → {r.destination}")
                        print(f"      Goods: {r.goods}  Volume: {r.volume:.0%}  Distance: {r.distance:.0f}")
            # Show economy type summary
            if state:
                type_counts: dict[str, int] = {}
                for s in state.settlements.values():
                    if s.is_active and s.economy_type:
                        type_counts[s.economy_type] = type_counts.get(s.economy_type, 0) + 1
                if type_counts:
                    print(f"\n{ANSI_BOLD}Economy Distribution:{ANSI_RESET}")
                    for etype in ECONOMY_TYPES:
                        count = type_counts.get(etype, 0)
                        icon = ECONOMY_ICONS.get(etype, "?")
                        color = _color(ECONOMY_COLORS.get(etype, 255))
                        bar = "█" * count if count > 0 else "░"
                        print(f"  {color}{icon} {etype:<10}{ANSI_RESET} {bar} {count}")
        else:
            # Default: show economy overview
            if not state:
                print("No simulation data. Run `wyrd run --seed X --years N` first.")
            else:
                type_counts = {}
                for s in state.settlements.values():
                    if s.is_active and s.economy_type:
                        type_counts[s.economy_type] = type_counts.get(s.economy_type, 0) + 1
                print(f"{ANSI_BOLD}Economy Overview (Year {state.year}):{ANSI_RESET}")
                routes = reconstruct_routes(state.trade_routes) if state.trade_routes else []
                active_routes = [r for r in routes if r.is_active]
                print(f"  Active trade routes: {len(active_routes)}")
                print(f"  Settlements with economies: {sum(type_counts.values())}")
                print(f"\n{ANSI_BOLD}Economy Distribution:{ANSI_RESET}")
                for etype in ECONOMY_TYPES:
                    count = type_counts.get(etype, 0)
                    icon = ECONOMY_ICONS.get(etype, "?")
                    color = _color(ECONOMY_COLORS.get(etype, 255))
                    bar = "█" * count if count > 0 else "░"
                    print(f"  {color}{icon} {etype:<10}{ANSI_RESET} {bar} {count}")

    # ── chronicles ─────────────────────────────────────────────────
    elif args.command == "chronicles":
        world = _get_world(args)
        if not world.chronicles:
            from .chronicles import generate_chronicles
            world.chronicles = generate_chronicles(world, world.narrative)

        if args.format == "html":
            from .export_chronicles_html import export_chronicles_html
            html = export_chronicles_html(world)
            output = args.output or f"wyrd-{world.seed}-chronicles.html"
            with open(output, "w") as f:
                f.write(html)
            print(f"📖 wyrd #{world.seed} chronicles exported to {output}")
        else:
            print(render_chronicles(world))

    # ── magic ───────────────────────────────────────────────────────
    elif args.command == "magic":
        world = _get_world(args)
        if not world.magic:
            from .magic import generate_magic_system
            world.magic = generate_magic_system(world)
        if args.save:
            save_world(world, args.save)
            print(f"💾 Saved to {args.save}")
        print(render_magic(world))

    # ── pantheon ────────────────────────────────────────────────────
    elif args.command == "pantheon":
        world = _get_world(args)
        if not world.pantheon:
            world.pantheon = generate_pantheon(world)
        if args.save:
            save_world(world, args.save)
            print(f"💾 Saved to {args.save}")
        from .render import render_pantheon
        print(render_pantheon(world))

    # ── ask ────────────────────────────────────────────────────────
    elif args.command == "ask":
        world = _get_world(args)
        world = _apply_snapshot_if_needed(world, args)
        question = " ".join(args.question) if args.question else ""
        from .ask import ask_about_world
        answer = ask_about_world(world, question, use_llm=not args.no_llm)
        print(answer)

    # ── worlds ──────────────────────────────────────────────────────
    elif args.command == "worlds":
        import glob
        import json as jlib
        import os
        import re

        scan_dir = args.dir or "."
        # Only match actual world files, not sim (-sim) or ttrpg (.ttrpg) files
        pattern = os.path.join(scan_dir, "wyrd-*.json")
        world_files = sorted(glob.glob(pattern))
        world_files = [
            wf for wf in world_files
            if not re.search(r'-sim\.json', wf)
            and not re.search(r'\.ttrpg\.json', wf)
        ]

        # Also check for sim files
        sim_files = set()
        sim_pattern = os.path.join(scan_dir, "wyrd-*-sim.json*")
        for sf in sorted(glob.glob(sim_pattern)):
            base = os.path.basename(sf)
            if base.endswith(".gz"):
                base = base[:-3]
            try:
                with open(sf) as f:
                    sim_data = jlib.load(f)
                seed = sim_data.get("seed", 0)
                sim_files.add(seed)
            except (jlib.JSONDecodeError, OSError):
                pass

        worlds_list = []
        for wf in world_files:
            try:
                with open(wf) as f:
                    data = jlib.load(f)
            except (jlib.JSONDecodeError, OSError):
                continue

            seed = data.get("seed", 0)
            width = data.get("width", 0)
            height = data.get("height", 0)
            regions = len(data.get("regions", []))
            total_pop = sum(
                s.get("population", 0)
                for r in data.get("regions", [])
                for s in r.get("settlements", [])
            )
            has_lore = "lore" in data and data["lore"] is not None
            has_narrative = "narrative" in data and data["narrative"] is not None
            has_chronicles = "chronicles" in data and data["chronicles"] is not None
            has_magic = "magic" in data and data["magic"] is not None
            has_sim = seed in sim_files

            worlds_list.append({
                "seed": seed,
                "dimensions": f"{width}x{height}",
                "regions": regions,
                "population": total_pop,
                "has_lore": has_lore,
                "has_narrative": has_narrative,
                "has_chronicles": has_chronicles,
                "has_magic": has_magic,
                "has_sim": has_sim,
                "file": os.path.basename(wf),
            })

        if args.json:
            print(jlib.dumps(worlds_list, indent=2))
        else:
            if not worlds_list:
                print(f"{ANSI_DIM}No worlds found. Generate one with `wyrd generate --seed 42`{ANSI_RESET}")
            else:
                print(f"{ANSI_BOLD}▒ wyrd worlds — {len(worlds_list)} found{ANSI_RESET}\n")
                for w in worlds_list:
                    seed_str = f"{ANSI_BOLD}#{w['seed']}{ANSI_RESET}"
                    size_str = f"{ANSI_DIM}{w['dimensions']}{ANSI_RESET}"
                    pop_str = f"{w['population']:,} souls"
                    region_str = f"{w['regions']} regions"

                    badges = []
                    if w["has_lore"]:  badges.append(f"{_color(28)}L{ANSI_RESET}")
                    if w["has_narrative"]:  badges.append(f"{_color(33)}N{ANSI_RESET}")
                    if w["has_chronicles"]:  badges.append(f"{_color(226)}C{ANSI_RESET}")
                    if w["has_magic"]:  badges.append(f"{_color(99)}M{ANSI_RESET}")
                    if w["has_sim"]:  badges.append(f"{_color(196)}S{ANSI_RESET}")
                    badge_str = " ".join(badges) if badges else f"{ANSI_DIM}(no extras){ANSI_RESET}"

                    print(f"  {seed_str}  {size_str}  {pop_str} · {region_str}")
                    print(f"       {badge_str}  {ANSI_DIM}{w['file']}{ANSI_RESET}")
                print()

    # ── serve ───────────────────────────────────────────────────────
    elif args.command == "serve":
        from .serve import serve_world
        serve_world(
            seed=args.seed,
            port=args.port,
            open_browser=not args.no_browser,
        )

    # ── save ───────────────────────────────────────────────────────
    elif args.command == "save":
        import random
        seed = args.seed if args.seed is not None else random.randint(0, 999999)
        world = generate_world(seed, width=args.width, height=args.height)
        world = _apply_snapshot_if_needed(world, args)
        output = args.output or f"wyrd-{seed}.json"
        save_world(world, output)
        print(f"💾 wyrd #{seed} saved to {output}")

    # ── export ─────────────────────────────────────────────────────
    elif args.command == "export":
        world = _get_world(args)
        world = _apply_snapshot_if_needed(world, args)
        fmt = args.format

        # Collect sim events if snapshot year was specified
        sim_events = None
        abandoned_settlements = None
        population_record = None
        if getattr(args, 'snapshot_year', None) is not None:
            try:
                from .serialize import load_sim_state
                from .sim import SimEvent
                sim_file = f"wyrd-{world.seed}-sim.json"
                sim_data = load_sim_state(sim_file)
                if sim_data and "events" in sim_data:
                    sim_events = [
                        SimEvent(year=e["year"], event_type=e["event_type"],
                                 description=e["description"],
                                 affected_settlements=e.get("affected_settlements", []),
                                 affected_regions=e.get("affected_regions", []))
                        for e in sim_data["events"]
                    ]

                # Extract abandoned settlements from the snapshot for HTML ruin rendering
                snap_key = str(args.snapshot_year)
                if sim_data and "snapshots" in sim_data and snap_key in sim_data["snapshots"]:
                    snap = sim_data["snapshots"][snap_key]
                    abandoned = []
                    for name, sd in snap.get("settlements", {}).items():
                        if not sd.get("is_active", True):
                            abandoned.append({
                                "name": name,
                                "x": sd.get("x", 0),
                                "y": sd.get("y", 0),
                            })
                    abandoned_settlements = abandoned

                # Extract population record
                if sim_data and "population_record" in sim_data:
                    population_record = sim_data["population_record"]
            except Exception:
                pass

        if fmt == "svg":
            output = args.output or f"wyrd-{world.seed}.svg"
            svg = export_world_svg(world)
            with open(output, "w") as f:
                f.write(svg)
            print(f"🗺️  wyrd #{world.seed} exported to {output}")
        elif fmt == "ttrpg":
            output = args.output or f"wyrd-{world.seed}.ttrpg.json"
            snapshot_year = getattr(args, 'snapshot_year', None)
            json_str = export_world_ttrpg(world, snapshot_year=snapshot_year, sim_events=sim_events)
            with open(output, "w") as f:
                f.write(json_str)
            print(f"📜 wyrd #{world.seed} TTRPG campaign exported to {output}")
        else:
            output = args.output or f"wyrd-{world.seed}.html"
            snapshot_year = getattr(args, 'snapshot_year', None)
            pop_record = None
            if population_record:
                pop_record = population_record
            html = export_world_html(
                world,
                snapshot_year=snapshot_year,
                abandoned_settlements=abandoned_settlements,
                population_record=pop_record,
                sim_events_count=len(sim_events) if sim_events else 0,
            )
            with open(output, "w") as f:
                f.write(html)
            print(f"🌐 wyrd #{world.seed} exported to {output}")
            if args.open:
                import subprocess
                try:
                    subprocess.run(["open", output], check=False)
                except FileNotFoundError:
                    try:
                        subprocess.run(["xdg-open", output], check=False)
                    except FileNotFoundError:
                        print(f"  Open {output} in your browser manually.")

    # ── explore ────────────────────────────────────────────────────
    elif args.command == "explore":
        world = _get_world(args)
        world = _apply_snapshot_if_needed(world, args)
        # Try the interactive curses explorer first
        from .explore import explore_world
        try:
            import curses
            # Check if we're in a real terminal
            if sys.stdout.isatty() and sys.stdin.isatty():
                explore_world(world)
            else:
                raise OSError("not a TTY")
        except (ImportError, OSError, Exception):
            # Fallback: pager-based explore
            lines = []
            lines.append(render_map(world))
            lines.append("")
            lines.append(render_lore(world))
            full_text = "\n".join(lines)
            try:
                import subprocess
                pager = os.environ.get("PAGER", "less")
                proc = subprocess.Popen(
                    [pager, "-R"],
                    stdin=subprocess.PIPE,
                )
                proc.communicate(input=full_text.encode())
            except FileNotFoundError:
                print(full_text)

    # ── query ──────────────────────────────────────────────────────
    elif args.command == "query":
        world = _get_world(args)
        world = _apply_snapshot_if_needed(world, args)
        query_text = " ".join(args.query_text) if args.query_text else "overview"
        from .query import query_world
        result = query_world(world, query_text)
        use_color = not args.no_color
        if result.found:
            print(result.render(color=use_color))
        else:
            print(result.render(color=use_color))


if __name__ == "__main__":
    main()
