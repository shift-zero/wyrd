# wyrd — Generative Fantasy Sandbox 🏔️

> *wyrd* (pronounced "weird") — Old English for fate, destiny, the cosmic pattern. Every world has one.

A terminal-native generative fantasy sandbox. Build a world from a single integer seed —
terrain, cultures, characters, centuries of simulated history, living pantheons, and trade
networks. All in beautiful ANSI color.

```bash
wyrd                    # Launch the gateway TUI (no args = menu)
wyrd generate --seed 42 # Generate & display a world
```

## Quick Start

```bash
pip install -e .
wyrd                       # Full curses TUI — worlds list, explore, viewer
```

Or run without installing:
```bash
python3 -m src generate --seed 42
```

## Commands (27 subcommands)

| Command | Description |
|---------|-------------|
| `wyrd` (no args) | Gateway TUI — list, pick, explore saved worlds |
| `generate` | Generate and display a world (`--lore`, `--narrative`) |
| `describe` | Lore-only output for a world |
| `save` | Save world to JSON |
| `load` | Load and display a saved world |
| `export` | Export to HTML / SVG / TTRPG campaign JSON |
| `explore` | Interactive curses explorer — scroll+zoom+inspect |
| `view` | Curses sim viewer — watch centuries pass in real-time |
| `run` | Year-by-year simulation (text output) |
| `embody` | Embodied play mode — live as a character, inherit skills |
| `chronicles` | Era-based world history timeline |
| `query "..."` | Natural-language world query |
| `ask "..."` | Ask an LLM a question about a world |
| `lookup NAME` | Quick entity search across settlements/chars/creatures |
| `characters` | List generated characters |
| `events` | Show event timeline |
| `quests` | Show available quests |
| `narrative` | Full narrative (chars + events + quests) |
| `branch` | Compare branching simulation timelines |
| `worlds` | List all generated worlds |
| `magic` | Show magic system |
| `pantheon` | Show pantheon and religions |
| `factions` | Show faction relationships and holdings |
| `bestiary` | Browse creatures by habitat/tier |
| `economy` | Show trade routes and economy data |
| `zones` | Show adventure zones |
| `serve` | Start web dashboard + REST API |
| `api` | Start REST API server only |

## Architecture

Six composable layers, each building on the last:

```
wyrd generate  →  explore    →  run        →  chronicles  →  view
   ↑                ↑              ↑               ↑            ↑
 terrain          curses         sim tick        history      animated
 + rivers         + inspect      + economy       + eras       + seasons
 + settlements    + zoom         + factions      + cataclysm  + overlays
 + lore           + gazetteer    + magic         + timelines
```

**Deep systems** (each an independent module):

| System | What it does |
|--------|-------------|
| **Economy** (`economy.py`) | Trade routes, prosperity modifiers, resource specialization |
| **Magic** (`magic.py`) | Magic system generation — schools, disciplines, spells |
| **Religion** (`religion.py`) | Pantheon generation, deities, holy sites, clergy |
| **Factions** (`faction.py`) | Political entities, allies/rivals, territory, power drift |
| **Cataclysm** (`cataclysm.py`) | World-changing events, terrain mutation, cascade triggers |
| **Bestiary** (`bestiary.py`) | Creatures by tier/habitat, loot tables, encounter stats |
| **Chronicles** (`chronicles.py`) | Era-based world history, age transitions |
| **Embody** (`embody.py`) | Character mode — skills, journey, inheritance |
| **Shop** (`shop.py`) | Market prices, inventory, buying/selling |
| **Query** (`query.py`) | NL pattern matching across all world data |
| **Trade Routes** (in `economy.py`) | Route simulation, road/sea icons, overlay on maps |

## TUI Surfaces

The curses TUI has multiple integrated views, all accessible from the gateway:

- **Gateway** — world picker with ASCII mini-map previews, sortable columns, detail cards
- **Explorer** — scrollable continent map with settlement inspection (`i`)
- **Viewer** — real-time sim animation with speed control (Crawl→Epoch), seasonal palettes, auto-pause on major events
- **Gazetteer** — browsable index of settlements, characters, factions, creatures, zones, deities
- **Embody** — play as a character, travel between settlements, inherit skills through heirs
- **Trade Route Overlay** — route map with economy type icons and connection dots

## Terrain Legend

| Char | Terrain |
|------|---------|
| `~` | Deep ocean |
| `~` | Shallow water |
| `.` | Beach / sand |
| `,` | Grassland |
| `*` | Forest |
| `^` | Hills |
| `▲` | Mountains |
| `◌` | Snowy peaks |
| `≈` | River |
| `≡` | Swamp / marshland |
| `:` | Desert / arid waste |
| `◉●∘·` | Settlements (city→hamlet) |

## Design

- **Seed-deterministic.** Same seed → same world, always. Share seeds, not files.
- **Beautiful output.** ANSI color everywhere, careful layout, no debug spew.
- **Composable.** Each layer works independently (terrain doesn't know about factions).
- **100% terminal-native.** From generation to simulation to interactive play, all in the terminal.

## Links

- [Architecture](docs/architecture.md) — module relationships, data flow
- [Design](docs/design.md) — principles, conventions, seed determinism
- [CLI Reference](docs/cli.md) — all commands and flags
- [Simulation Engine](docs/simulation.md) — year-by-year ticks, settlement evolution
- [Export](docs/export.md) — HTML, SVG, TTRPG campaign JSON
