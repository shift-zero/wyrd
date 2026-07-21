"""wyrd — Generative Fantasy Sandbox CLI."""

import argparse
from .generate import generate_world
from .render import render_map, render_brief, render_lore


def main():
    parser = argparse.ArgumentParser(
        prog="wyrd",
        description="Generative fantasy sandbox — build worlds in the terminal."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── generate ───────────────────────────────────────────────────
    gen = sub.add_parser("generate", help="Generate a new world")
    gen.add_argument("--seed", type=int, default=None,
                     help="World seed (random if omitted)")
    gen.add_argument("--width", type=int, default=80)
    gen.add_argument("--height", type=int, default=40)
    gen.add_argument("--no-settlements", action="store_true",
                     help="Hide settlement markers")
    gen.add_argument("--brief", action="store_true",
                     help="Show one-line summary instead of map")
    gen.add_argument("--lore", action="store_true",
                     help="Show lore (culture, history, features, relationships)")

    # ── describe ───────────────────────────────────────────────────
    desc = sub.add_parser("describe", help="Describe a generated world (lore only)")
    desc.add_argument("--seed", type=int, required=True,
                      help="World seed")
    desc.add_argument("--width", type=int, default=80)
    desc.add_argument("--height", type=int, default=40)

    args = parser.parse_args()

    if args.command == "generate":
        import random
        seed = args.seed or random.randint(0, 999999)
        world = generate_world(seed, width=args.width, height=args.height)

        if args.brief:
            print(render_brief(world))
        elif args.lore:
            print(render_map(world, show_settlements=not args.no_settlements))
            print()
            print(render_lore(world))
        else:
            print(render_map(world, show_settlements=not args.no_settlements))

    elif args.command == "describe":
        world = generate_world(args.seed, width=args.width, height=args.height)
        print(render_lore(world))


if __name__ == "__main__":
    main()
