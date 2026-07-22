# Test Suite

All tests in `tests/`, run via pytest.

## Test Files

| File | What it covers |
|------|---------------|
| `test_generate.py` | Terrain generation, noise, river placement, settlement size tiers |
| `test_lore.py` | Culture names, features, history templates, relationships |
| `test_narrative.py` | Character generation, event chains, quests |
| `test_chronicles.py` | Era generation, world modifiers, legendary participants |
| `test_sim.py` | Year ticks, carrying capacity, settlement founding/abandonment |
| `test_phase3.py` | Serialization round-trip, HTML export, query engine |
| `test_explore.py` | Explorer UI helpers (tile info, region lookup) |
| `test_query.py` | Pattern matching, region/settlement finders |

## Running

```bash
cd wyrd && uv run pytest
```

## Key Test Patterns

- **Seed determinism**: run same generator twice → same output
- **Round-trip**: save → load → compare fields
- **Boundary testing**: 0-population settlements, tiny/big worlds, empty lore

## See also

- [Architecture](architecture.md) — module dependencies mirror test organization
