"""wyrd — Generative Fantasy Sandbox. A single-user MUD."""

import sys


def main():
    args = sys.argv[1:]

    if args and args[0] == "--seed":
        if len(args) < 2:
            print("Usage: wyrd [--seed <number>]")
            sys.exit(1)
        seed = int(args[1])

        # Generate a full world with lore
        from .generate import generate_world
        from .serialize import save_world
        from .lore import generate_lore
        from .narrative import generate_narrative
        from .religion import generate_pantheon
        from .magic import generate_magic
        from .faction import generate_factions
        from .chronicles import generate_chronicles
        from .bestiary import generate_bestiary

        world = generate_world(seed)
        world.lore = generate_lore(world)
        world.narrative = generate_narrative(world)
        world.pantheon = generate_pantheon(world)
        world.magic = generate_magic(world)
        world.factions = generate_factions(world)
        world.chronicles = generate_chronicles(world)
        world.bestiary = generate_bestiary(world)
        save_world(world)

        # Launch Textual gateway
        from .tui_gateway import WyrdGateway

        WyrdGateway().run()

    else:
        # Launch Textual gateway
        from .tui_gateway import WyrdGateway

        WyrdGateway().run()


if __name__ == "__main__":
    main()
