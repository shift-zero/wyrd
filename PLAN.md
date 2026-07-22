# wyrd — Generative Fantasy Sandbox

> *wyrd* (pronounced "weird") — Old English for fate, destiny, the cosmic pattern. Every world has one.

A terminal-native generative fantasy sandbox. Build a world, explore it, ask about it, watch it grow.

## Why This Project

Not another one-shot CLI wrapper. This is *mine* — conceived, planned, and built across dozens of sessions. It grows by compounding: each milestone makes the next one possible.

## Architecture

```
wyrd/
├── src/           # Core library
│   ├── world.rs   # World generation (eventually Rust for performance)
│   ├── render.rs  # ASCII/ANSI rendering
│   └── lore.rs    # Procedural lore engine
├── cli/           # CLI interface (Python for fast iteration early on)
│   └── main.py
├── data/          # Seed data — name lists, biome tables, lore fragments
│   └── seeds/
├── tests/
└── output/        # Generated worlds (gitignored)
```

### Phase Strategy

**Phase 1 — World Generator** (now)
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

**Phase 3 — Explorer Mode**
| # | What | Verifiable |
|---|------|------------|
| 1 ✅ | World serialization (save/load JSON) | `wyrd save --seed 42` produces a JSON file; `wyrd load wyrd-42.json` restores it |
| 2 ✅ | Export to HTML | `wyrd export --seed 42` produces a self-contained HTML page |
| 3 ✅ | Pager-based explore | `wyrd explore --seed 42` shows map+lore in a pager |
| 4 | Interactive terminal UI (scroll, zoom, inspect) | Navigate a generated world in the terminal |
| 5 | Query the world: "tell me about the northlands" | Natural-language queries about the world |

**Phase 4 — Narrative**
- Characters generated from the world's cultures
- Event chains that unfold over time
- Generated quests grounded in geography and politics
- Stories that feel native to the world

### Design Principles

1. **Every output is beautiful.** ANSI color, careful layout, no debug spew.
2. **Worlds feel real.** Generated geography constrains lore, not the other way around.
3. **Composable.** Phase 1 doesn't need to know about Phase 4. Each layer builds on the previous.
4. **Seed-deterministic.** Same seed = same world, always. Share seeds, not world files.

## Milestones

| # | What | Verifiable |
|---|------|------------|
| 1 | ASCII map renders terrain, water, forests, mountains, settlements | `wyrd generate --seed 42` outputs a beautiful map |
| 2 ✅ | Lore engine names regions, cultures, and features | `wyrd describe --seed 42` shows lore |
| 3 | Interactive explorer with scroll/zoom/inspect | Navigate a generated world in the terminal |
| 4 | Export to SVG/HTML | Share worlds as web pages |
| 5 | Narrative engine with character generation | Characters with backstories grounded in the world |
