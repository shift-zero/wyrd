# Terrain Generation

All in `src/generate.py`. Pure Python, no deps.

## Algorithm

1. **Elevation map** via seeded 2D value noise with 4 octaves
2. **Rivers** flow downhill from highlands (elevation 0.55-0.9) to coast
3. **Moisture** map (3 octaves) with river proximity bonus
4. **Terrain classification** from elevation + moisture thresholds:

   ```
   e < 0.30: deep_water     |  e < 0.55: grass (swamp if m>0.55)
   e < 0.38: shallow        |  e < 0.68: forest/m:0.4/grass (desert if m<0.15)
   e < 0.42: sand           |  e < 0.82: hills/m:0.6/forest (desert if m<0.15)
                             |  e < 0.93: mountains
                             |  >= 0.93: snow
   ```

   - **Swamp** (`≡`, dark green) — high moisture (m > 0.55), low elevation (0.38-0.55). Wetlands where rivers meet flat ground.
   - **Desert** (`:`, tan) — very low moisture (m < 0.15), mid elevation (0.42-0.82). Arid wastelands in the rain shadow.
5. **Regions** — 3-6 randomly placed with shuffled biomes
6. **Settlements** — 1-4 per region, unique names from pool
7. **Lore generation** (calls `lore.py`)
8. **Narrative generation** (calls `narrative.py`)
9. **Chronicles generation** (calls `chronicles.py`)

## Noise System

```python
class Noise:
    def __init__(self, seed):    # builds permutation table
    def sample(x, y):           # single octave
    def octave(x, y, octaves=3):# multiple octaves with persistence
```

Uses `_hash_coord()` as the primitive — deterministic integer hash into `[0, 1)`.

## Seed Offsets

| Component | Offset |
|-----------|--------|
| Terrain | `seed` |
| Lore | `seed + 1_000_000` |
| Narrative | `seed + 2_000_000` |
| Chronicles | `seed + 3_000_000` |

Each sub-generator creates its own `random.Random(offset)`.

## See also

- [World Model](world.md) — data structures produced
- [Lore Engine](lore.md) — cultures, features, histories
