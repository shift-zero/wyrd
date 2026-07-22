# wyrd — Generative Fantasy Sandbox 🏔️

**wyrd** (pronounced "weird") — Old English for fate, destiny, the cosmic pattern. Every world has one.

A terminal-native generative fantasy sandbox. Build a world, explore it, ask about it, watch it grow over centuries.

## Quick Start

```bash
wyrd generate --seed 42          # Generate and display a world
wyrd generate --seed 42 --lore   # With culture, history, features
wyrd explore --seed 42           # Interactive curses explorer
wyrd run --seed 42 --years 500   # Year-by-year simulation
wyrd chronicles --seed 42        # Era-based history timeline
```

## Architecture

Six composable layers, each building on the last:

```
generate.py  →  lore.py  →  narrative.py  →  chronicles.py  →  sim.py
    ↑              ↑             ↑                ↑               ↑
 world.py     render.py    serialize.py      query.py        export_*.py
```

## Doc Map (this is the hub)

**Convention: docs are always updated after code changes.** See [doc-conventions](docs/doc-conventions.md).

| Doc | What it covers |
|-----|---------------|
| [Overview](docs/overview.md) | What wyrd is, phases, philosophy |
| [Architecture](docs/architecture.md) | Module relationships, data flow |
| [World Model](docs/world.md) | `World`, `Region`, `Settlement`, terrain types |
| [Generation](docs/generation.md) | Value noise, rivers, settlement placement |
| [Lore Engine](docs/lore.md) | Cultures, features, histories, relationships |
| [Narrative Engine](docs/narrative.md) | Characters, events, quests |
| [Chronicles Engine](docs/chronicles.md) | Era-based world history |
| [Simulation Engine](docs/simulation.md) | Year-by-year ticks, settlement evolution |
| [CLI Reference](docs/cli.md) | All commands, flags, subparsers |
| [Rendering](docs/rendering.md) | ANSI terminal output, colors |
| [Export](docs/export.md) | HTML, SVG, TTRPG campaign JSON |
| [Serialization](docs/serialization.md) | JSON save/load, sim state |
| [Explorer](docs/explorer.md) | Interactive curses UI |
| [Query Engine](docs/query.md) | Natural-language pattern matching |
| [Design](docs/design.md) | Principles, conventions, seed determinism |
| [Doc Conventions](docs/doc-conventions.md) | How to write and maintain docs |

## Key Principles

- **Seed-deterministic:** Same seed → same world, always
- **Composable:** Each layer works independently
- **Beautiful output:** ANSI color everywhere, no debug spew
- **File size rule:** Every doc file < 100 lines. If it's longer, split it.
