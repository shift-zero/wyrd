# Simulation Engine

`src/sim.py` — Phase 6: The Turning of the World. Year-by-year Dwarf Fortress-style world evolution.

## Data Model

```python
@dataclass class SettlementSnapshot:
    name, region, x, y, population, kind
    is_active, founded_year
    prosperity: float (0-1)
    food_stores: float
    health: float (0-1)

@dataclass class SimState:
    year, settlements: dict[name→Snapshot]
    events: list[SimEvent]
    world_modifiers: list[str]
    population_record: list[dict]
```

## Per-Year Tick

Each year processes every active settlement:

1. **Resource calc** — carrying capacity from surrounding terrain (5-cell radius)
2. **Food dynamics** — production vs consumption, store tracking
3. **Health** — degrades from overcrowding
4. **Population** — logistic growth or decline from famine/disease
5. **Event triggers** — plague, famine, war, prosperity, founding, abandonment

## Events

10 event types: plague, famine, war, discovery, prosperity, disaster, exodus, founding, abandonment, trade_boom. Each triggers based on simulation conditions (not pure random).

## Snapshots

- Every 50 years the sim state is captured
- `--snapshot-year` on explore/query/export loads any snapshot
- Compact mode saves as gzipped JSON

## See also

- [World Model](world.md) — base terrain data used for capacity
- [CLI Reference](cli.md) — `wyrd run` command flags
