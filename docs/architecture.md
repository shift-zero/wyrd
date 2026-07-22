# Architecture

## Module Dependency Graph

```
    world.py  (data types — no deps)
       │
       ├── generate.py  (terrain + settlement placement)
       ├── lore.py      (cultures, features, histories)
       ├── narrative.py (characters, events, quests)
       ├── chronicles.py(era-based history)
       ├── sim.py       (year-by-year simulation)
       │
       ├── render.py    (ANSI terminal output)
       ├── serialize.py (JSON save/load)
       ├── query.py     (natural language)
       ├── explore.py   (curses interactive UI)
       │
       └── export_*.py  (HTML, SVG, TTRPG JSON)
```

## Data Flow

```
seed → generate_world() → World object
                              ├── .lore        → render_lore()
                              ├── .narrative   → render_narrative()
                              ├── .chronicles  → render_chronicles()
                              └── sim.py       → SimState → snapshots
```

## Key Design Choices

- **No external deps for core generation** — pure Python + stdlib
- **Late imports** for circular dependency avoidance (chronicles imports narrative helpers at call time)
- **All generation seeded** via `random.Random(seed + offset)` — lore/narrative/chronicles use different offsets from terrain seed

## See also

- [World Model](world.md) — core data types
- [Seed Determinism](design.md) — how determinism works
