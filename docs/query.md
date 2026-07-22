# Query Engine

`src/query.py` — Phase 3, Milestone 5. Natural-language world queries via pattern matching (no LLM).

## Query Types

| Type | Example | Handles |
|------|---------|---------|
| `overview` | "tell me about this world" | Stats, terrain breakdown, regions |
| `region_info` | "tell me about Greendale" | Region culture, settlements, history |
| `settlement_locate` | "where is Fairhaven" | Location, terrain, relationships |
| `settlements_in_region` | "what settlements are in Greendale" | Filtered list |
| `feature_search` | "find rivers" | Named geographical features |
| `population_query` | "what is the total population" | Souls count |
| `culture_search` | "tell me about the cultures" | Per-region culture info |
| `history_query` | "history of Blackland" | Region history snippets |
| `relationship_search` | "who trades with Fairhaven" | Settlement relationships |
| `terrain_query` | "what biomes exist" | Terrain breakdown |

## Pattern Matching

Regex-based with 9 pattern categories. Each category has multiple regex patterns. Matched targets are fuzzy-matched against region and settlement names using substring and word scoring.

## Result Rendering

`QueryResult` objects with `render(color=True)` for ANSI terminal output.

## See also

- [Lore Engine](lore.md) — the data queried
- [CLI Reference](cli.md) — `wyrd query` command
