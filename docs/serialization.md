# Serialization

`src/serialize.py` — JSON save/load for worlds and simulation state.

## World Format

`save_world(world, path)` / `load_world(path)`

Serializes everything: terrain grid, elevation, moisture, rivers, regions, settlements, lore, narrative, chronicles. Uses a custom `WyrdEncoder` for set→list conversion.

## Simulation Format

`save_sim_state(result, path)` / `load_sim_state(path)`

Stores:
- `initial_state` / `final_state` — full SettlementSnapshot maps
- `snapshots` — dict of year → state (for `--snapshot-year`)
- `events` — all sim events across the run
- `population_record` — year-by-year pop trends

Supports gzip compression via `--compact` flag (adds `.gz` extension).

## Round-Trip Guarantee

Old world formats without narrative/chronicles still load correctly — missing keys default to empty structures.

## See also

- [World Model](world.md) — the data being serialized
- [Simulation](simulation.md) — SimState and snapshots
