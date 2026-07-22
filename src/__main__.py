"""wyrd — Generative Fantasy Sandbox CLI."""

import argparse
import os
import sys
from .generate import generate_world
from .render import render_map, render_brief, render_lore, render_characters, render_events, render_quests, render_narrative, render_chronicles
from .serialize import save_world, load_world
from .export_html import export_world_html
from .export_svg import export_world_svg


def _get_world(args) -> 'World':
    """Either load from file or generate from seed."""
    if hasattr(args, 'load') and args.load:
        return load_world(args.load)
    import random
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    return generate_world(seed, width=args.width, height=args.height)


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
                            choices=["html", "svg"],
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

    # ── chronicles ─────────────────────────────────────────────────
    chron_cmd = sub.add_parser("chronicles",
                                help="Show era-based world history (chronicles)")
    _add_load_arg(chron_cmd)
    chron_cmd.add_argument("--format", "-f", type=str, default="text",
                            choices=["text", "html"],
                            help="Output format (default: text)")
    chron_cmd.add_argument("--output", "-o", type=str, default=None,
                            help="Output file path (HTML only)")

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
            result = run_simulation(
                world,
                num_years=args.years,
                seed_offset=args.seed_offset,
                chaos_factor=args.chaos,
                snapshot_interval=50,
            )

            # Save simulation state
            save_sim_state(result, sim_file)

            if args.summary:
                print(render_sim_summary(result))
            else:
                print(render_sim_detailed(result, world))
        else:
            # Render from saved state
            from .render import render_map
            print(render_sim_summary_from_state(sim_state, world, world.seed))

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

        if fmt == "svg":
            output = args.output or f"wyrd-{world.seed}.svg"
            svg = export_world_svg(world)
            with open(output, "w") as f:
                f.write(svg)
            print(f"🗺️  wyrd #{world.seed} exported to {output}")
        else:
            output = args.output or f"wyrd-{world.seed}.html"
            html = export_world_html(world)
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
