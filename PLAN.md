# wyrd — Generative Fantasy Sandbox

> *wyrd* (pronounced "weird") — Old English for fate, destiny, the cosmic pattern. Every world has one.

A terminal-native generative fantasy sandbox. Build a world, explore it, ask about it, watch it grow.

## Why This Project

Not another one-shot CLI wrapper. This is *mine* — conceived, planned, and built across dozens of sessions. It grows by compounding: each milestone makes the next one possible.

## Architecture

```
wyrd/
├── src/           # Core library
│   ├── generate.py   # World generation (terrain, rivers, settlements)
│   ├── world.py      # Core data models
│   ├── nore.rs       # (eventually Rust for performance)
│   ├── render.py     # ANSI/ASCII rendering + narrative rendering
│   ├── lore.py       # Procedural lore engine
│   ├── narrative.py  # Character, event, and quest generation
│   ├── chronicles.py # Era-based world history (Phase 5)
│   ├── sim.py        # Year-by-year world simulation (Phase 6)
│   ├── serialize.py  # JSON save/load
│   ├── explore.py    # Interactive terminal explorer
│   ├── query.py      # Natural-language query engine
│   ├── export_html.py# HTML export
│   └── __main__.py   # CLI entry point
├── tests/         # Test suite
│   ├── test_generate.py
│   ├── test_lore.py
│   ├── test_narrative.py
│   ├── test_chronicles.py
│   ├── test_sim.py
│   ├── test_phase3.py
│   ├── test_explore.py
│   ├── test_query.py
│   └── conftest.py
└── output/        # Generated worlds (gitignored)
```

### Phase Strategy

**Phase 1 — World Generator** (done)
- Procedural ASCII map with terrain, biomes, elevation
- Named settlements with population tiers
- Rivers, coastlines, mountain ranges
- ANSI-colored terminal output
- Seed-based generation (same seed = same world)

**Phase 2 — Lore Engine** (done)
- Region names, culture names, settlement descriptions
- Named geographical features (The Whispering Strait, etc.)
- History snippets per region
- Conflicts and relationships between settlements

**Phase 3 — Explorer Mode** (done)
| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | World serialization (save/load JSON) | `wyrd save --seed 42` produces a JSON file; `wyrd load wyrd-42.json` restores it |
| 2 ✅ | Export to HTML | `wyrd export --seed 42` produces a self-contained HTML page |
| 3 ✅ | Pager-based explore | `wyrd explore --seed 42` shows map+lore in a pager |
| 4 ✅ | Interactive terminal UI (scroll, zoom, inspect) | Navigate a generated world in the terminal |
| 5 ✅ | Query the world: "tell me about the northlands" | `wyrd query --seed 42 "tell me about Blackland"` returns region lore, culture, history, settlements |

**Phase 4 — Narrative** (done)
| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | Character generation grounded in world cultures | `wyrd characters --seed 42` lists named characters with occupations, traits, backstories |
| 2 ✅ | Event chains that unfold over time | `wyrd events --seed 42` shows chronological timeline with types and consequences |
| 3 ✅ | Generated quests grounded in geography and politics | `wyrd quests --seed 42` shows active quests with givers, locations, rewards |
| 4 ✅ | All narrative seed-deterministic (same world → same narrative) | Same seed produces identical characters, events, and quests |
| 5 ✅ | Narrative serialization round-trip | Save/load preserves all narrative data; old saves without narrative still work |

**Phase 5 — Chronicles** (next)
Generative world history. Not a static dump — a causally linked timeline of eras that shaped the world into what it is.

| # | What | Verifiable |
|---|------|------------|
| 1 | Era-based history generation (ages, cataclysms, golden ages) | `wyrd chronicles --seed 42` outputs a timeline of distinct eras with descriptions |
| 2 | Legendary events with named participants from the narrative engine | Events reference actual characters and settlements from the world |
| 3 | Era-dependent world state (ruins, fallen empires, contested borders) | Map renders differently depending on which era you're viewing |
| 4 | Seed-deterministic: same seed + same era range → same history | Always identical across runs |
| 5 | History serialization + export to timeline HTML | `wyrd chronicles --seed 42 --format html` produces a readable chronicle page |

**Phase 6 — The Turning of the World** (planned)
Year-by-year simulation in the Dwarf Fortress tradition. The world is no longer a static artifact — it *lives* and *changes*.

| # | What | Verifiable |
|---|------|------------|
| 1 | Tick-based simulator: settlements grow/decline year by year | `wyrd run --seed 42 --years 300` outputs year logs showing population changes, new settlements, abandoned sites |
| 2 | Causal event chain: wars, famines, plagues, discoveries emerge from conditions | Viewing year 150 shows events that trace back to conditions set in year 50 |
| 3 | Dynamic map evolution: borders shift, ruins appear, new roads form | Map snapshots at year 0 vs year 300 show visible differences |
| 4 | Pause-and-inspect: stop the sim at any year and use explore/query | `wyrd explore --seed 42 --year 127` shows map + lore at that moment in time |
| 5 | Seed-deterministic with optional branching | Same seed + same decisions → same outcome; sandbox can fork |
| 6 | Export any snapshot as TTRPG-ready campaign doc | `wyrd export --seed 42 --year 127 --format ttrpg` produces a Foundry/WorldAnvil-ready JSON + printable pamphlet |

### Design Principles

1. **Every output is beautiful.** ANSI color, careful layout, no debug spew.
2. **Worlds feel real.** Generated geography constrains lore, not the other way around.
3. **Composable.** Phase 1 doesn't need to know about Phase 4. Each layer builds on the previous.
4. **Seed-deterministic.** Same seed = same world, always. Share seeds, not world files.

## Milestones

| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | ASCII map renders terrain, water, forests, mountains, settlements | `wyrd generate --seed 42` outputs a beautiful map |
| 2 ✅ | Lore engine names regions, cultures, and features | `wyrd describe --seed 42` shows lore |
| 3 ✅ | Interactive terminal UI (scroll, zoom, inspect) | Navigate a generated world in the terminal |
| 4 ✅ | Export to HTML and SVG | `wyrd export --seed 42` produces HTML; `wyrd export --seed 42 --format svg` produces SVG |
| 5 ✅ | Narrative engine with character generation | Characters with backstories grounded in the world |
| 6 ✅ | Chronicles engine — era-based world history | `wyrd chronicles --seed 42` shows a causally linked timeline |
| 7 | Simulation engine — year-by-year world evolution | `wyrd run --seed 42 --years 500` evolves map, settlements, and history in real-time |
