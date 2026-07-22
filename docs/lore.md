# Lore Engine

`src/lore.py` — Phase 2. Generates culture names, geographical features, history snippets, and settlement relationships.

## Data Model

```python
@dataclass
class Lore:
    seed: int
    region_descriptions: dict[str, str]
    cultures: dict[str, str]          # region → culture name
    culture_descriptions: dict[str, list[str]]
    features: list[dict]              # named geography
    histories: dict[str, str]
    relationships: list[dict]
```

## Culture Templates

Four biomes with distinct naming patterns:
- **Temperate** — "The Green Valley", "Meadowfolk"
- **Arid** — "The Scorched Sands", "Dune Expanse"
- **Tundra** — "The Frozen Reach", "Snow Clans"
- **Tropical** — "The Emerald Dominion", "Jungle Coast"

Each biome has 7 descriptor templates for cultural flavour.

## Named Features

Four feature types: mountain ranges, rivers, bays, forests. Each with their own adjective/noun pools and naming templates.

## Relationships

7 types: trade, rivalry, alliance, feud, vassalage, marriage_tie, religious, cultural. Each with unique sentence templates and custom word pools.

## See also

- [Narrative Engine](narrative.md) — builds on lore cultures
- [Rendering](rendering.md) — `render_lore()` ANSI output
