# Design Principles

## Seed Determinism

The same seed always produces the same world. This is the contract:

```python
generate_world(42)        # Always the same
generate_world(42, 100, 50)  # Different width → different world
```

Each component uses `random.Random(seed + OFFSET)` to ensure:
- Terrain is seeded by `world.seed`
- Lore is seeded by `world.seed + 1_000_000`
- Narrative by `+ 2_000_000`
- Chronicles by `+ 3_000_000`
- Simulation by `world.seed` (but accepts `seed_offset` for branching)

## Composable Layers

Each layer only depends on the layer before it:
- `generate.py` → `world.py` (terrain grid)
- `lore.py` → `world.py + regions` (culture data)
- `narrative.py` → `world.py + regions` (characters/events)
- `chronicles.py` → `world + narrative` (eras)
- `sim.py` → `world.py + terrain` (tick simulation)

## No External Dependencies

Core terrain generation uses pure Python value noise — no numpy, no PIL, no external libs. Only stdlib `random`, `math`, `json`, `curses`.

## Output Quality

- Every terminal output uses ANSI color
- Legends and labels explain what you're seeing
- Brief mode for scripting/piping
- Exports are self-contained (single HTML file, single JSON)

## See also

- [Architecture](architecture.md) — module relationships
- [Overview](overview.md) — project scope and phases
