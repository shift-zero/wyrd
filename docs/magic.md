# Magic System

Phase 8 magic generation — `src/magic.py`.

## Data Model

```python
@dataclass MagicSystem:
    name, source, description, practitioners
    schools: list[MagicSchool]
    traditions: list[MagicTradition]

@dataclass MagicSchool:
    name, description, spell_examples, alignment

@dataclass MagicTradition:
    name, description, origin, region, practitioners
```

## Generation

1. **Source selection** — the magic source (arcane, divine, natural, elemental, shadow, blood, celestial) is chosen by biome affinity. Tundra-heavy worlds lean divine/arcane; tropical worlds lean natural; arid worlds lean elemental/blood.
2. **Naming** — `"{adjective} {noun} of {culture}"` using world culture names from the lore engine.
3. **School selection** — 3-6 schools picked from 12, scored by biome affinity.
4. **Traditions** — 2-5 traditions rooted in world regions, using origin types (ancient, secret, forgotten, etc.)

## CLI

```bash
wyrd magic --seed 42           # Show magic system
wyrd magic --seed 42 --save    # Save world with magic to JSON
```

## Serialization

`world.magic` survives save/load roundtrip. `world_to_dict` / `dict_to_world` in `serialize.py` handle `magic` section.

## See also

- [World Model](world.md) — biomes that influence source selection
- [Lore Engine](lore.md) — culture names used in tradition naming
- [CLI Reference](cli.md) — `wyrd magic` command flags
