# World Data Model

All core types live in `src/world.py`. Zero external dependencies.

## Terrain Types

| Key | Char | Color | Height | Description |
|-----|------|-------|--------|-------------|
| `deep_water` | `~` | 27 | -2 | Deep ocean |
| `shallow` | `~` | 33 | -1 | Shallow water |
| `sand` | `.` | 223 | 0 | Beach / sand |
| `grass` | `,` | 28 | 1 | Grassland |
| `forest` | `*` | 22 | 2 | Forest |
| `hills` | `^` | 94 | 3 | Hills |
| `mountains` | `▲` | 130 | 4 | Mountains |
| `snow` | `◌` | 255 | 5 | Snowy peaks |
| `river` | `≈` | 45 | 0 | River |
| `swamp` | `≡` | 64 | 1 | Swamp / marshland |
| `desert` | `:` | 179 | 1 | Desert / arid waste |

## Key Dataclasses

```python
@dataclass
class Settlement:
    name: str; x: int; y: int
    population: int; kind: str  # hamlet/village/town/city

@dataclass
class Region:
    name: str; biome: str
    settlements: list[Settlement]

@dataclass
class World:
    seed: int; width: int; height: int
    elevation: list[list[float]]  # 0.0-1.0
    moisture: list[list[float]]   # 0.0-1.0
    terrain: list[list[str]]      # terrain keys
    rivers: list[(x, y)]
    regions: list[Region]
    lore: Lore | None
    narrative: Narrative | None
    chronicles: Chronicles | None
```

Settlement marker chars: `·` (hamlet) → `∘` (village) → `●` (town) → `◉` (city)

## See also

- [Generation](generation.md) — how terrain is created from seed
- [Serialization](serialization.md) — how World is saved/loaded
