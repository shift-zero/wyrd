"""wyrd — Generative Fantasy Sandbox CLI."""

import argparse
import os
import sys
from .generate import generate_world
from .render import render_map, render_brief, render_lore, render_characters, render_events, render_quests, render_narrative
from .serialize import save_world, load_world
from .export_html import export_world_html


def _get_world(args) -> 'World':
    """Either load from file or generate from seed."""
    if hasattr(args, 'load') and args.load:
        return load_world(args.load)
    import random
    seed = args.seed if args.seed is not None else random.randint(0, 999999)
    return generate_world(seed, width=args.width, height=args.height)


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
    export_cmd = sub.add_parser("export", help="Export a world to HTML")
    _add_load_arg(export_cmd)
    export_cmd.add_argument("--output", "-o", type=str, default=None,
                            help="Output HTML file path")
    export_cmd.add_argument("--open", action="store_true",
                            help="Open the HTML file in browser after export")

    # ── explore ────────────────────────────────────────────────────
    explore = sub.add_parser("explore", help="Explore a world interactively (pager)")
    _add_load_arg(explore)

    # ── query ──────────────────────────────────────────────────────
    query_cmd = sub.add_parser("query", help="Query a world with natural language")
    _add_load_arg(query_cmd)
    query_cmd.add_argument("query_text", type=str, nargs="*",
                           help='Query text, e.g. "tell me about the northlands"')
    query_cmd.add_argument("--no-color", action="store_true",
                           help="Disable ANSI color in output")

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

    # ── save ───────────────────────────────────────────────────────
    elif args.command == "save":
        import random
        seed = args.seed if args.seed is not None else random.randint(0, 999999)
        world = generate_world(seed, width=args.width, height=args.height)
        output = args.output or f"wyrd-{seed}.json"
        save_world(world, output)
        print(f"💾 wyrd #{seed} saved to {output}")

    # ── export ─────────────────────────────────────────────────────
    elif args.command == "export":
        world = _get_world(args)
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
            from .render import render_map, render_lore
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
