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
│   ├── render.py     # ANSI/ASCII rendering + narrative rendering
│   ├── lore.py       # Procedural lore engine
│   ├── narrative.py  # Character, event, and quest generation
│   ├── chronicles.py # Era-based world history
│   ├── sim.py        # Year-by-year world simulation
│   ├── economy.py    # Trade & economy system
│   ├── magic.py      # Magic system generation
│   ├── religion.py   # Pantheon/religion system
│   ├── cataclysm.py  # Cataclysmic events
│   ├── faction.py    # Faction system
│   ├── bestiary.py   # Creature generation
│   ├── serialize.py  # JSON save/load
│   ├── explore.py    # Interactive terminal explorer
│   ├── query.py      # Natural-language query engine
│   ├── export_html.py# HTML export
│   ├── serve.py      # Web dashboard + REST API v1
│   ├── export_chronicles_html.py  # Chronicles HTML export
│   └── __main__.py   # CLI entry point (25 subcommands)
├── tests/         # Test suite (758 tests)
│   ├── test_generate.py
│   ├── test_lore.py
│   ├── test_narrative.py
│   ├── test_chronicles.py
│   ├── test_sim.py
│   ├── test_api.py        # REST API v1 tests (36)
│   ├── test_economy.py
│   └── ...
└── output/        # Generated worlds (gitignored)
```

## Phase 18 — Depth & Quality (in progress)

**Focus:** Making existing systems richer instead of adding new modules.

| # | What | Status | Verified |
|---|------|--------|----------|
| 1 | Bestiary tests + bugfixes + travel encounters | ✅ 2026-07-23 | 65 tests, all pass; `wyrd embody` travel has creature encounters |
| 2 | Shop/market system | ✅ 2026-07-23 | 32 tests, all pass; `m` command in embody opens market |
| 3 | Performance — resource map precomputation + pytest-xdist | ✅ 2026-07-23 | 758 tests in 81s (vs 156s = 48% faster) |
| 4 | **REST API v1 — 15 JSON endpoints + standalone server** | ✅ 2026-07-23 | 36 tests, all pass; `wyrd api --port 9090` |

## Design Principles

1. **Every output is beautiful.** ANSI color, careful layout, no debug spew.
2. **Worlds feel real.** Generated geography constrains lore, not the other way around.
3. **Composable.** Each layer builds on the previous.
4. **Seed-deterministic.** Same seed = same world, always.
