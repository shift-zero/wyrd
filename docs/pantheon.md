# Pantheon / Religion System

## Overview

Every wyrd world has a pantheon. `wyrd pantheon --seed 42` generates the full religious landscape:

- **Deities** — Named gods/goddesses with domains, alignment, sacred symbols, holy animals, and TTRPG stat arrays
- **Religions** — One or two organized faiths grouping related deities, with tenets, clergy titles, and holy days
- **Holy Sites** — Temples, shrines, monasteries, oracles, groves, and sanctuaries tied to actual settlements
- **Regional Faith** — Every world region is assigned a religion based on biome and alignment affinity

## Usage

```bash
# Generate and display pantheon
wyrd pantheon --seed 42

# Save world with pantheon
wyrd pantheon --seed 42 --save wyrd-42.json

# Include in TTRPG export
wyrd export --seed 42 --year 150 --format ttrpg
```

## CLI Output

Annotated ANSI rendering organized by religion:

```
═══ The Pantheon of wyrd #42 ═══

  †  High Faith  [3 regions]
    Description of the religion

    ★ Caelia the Gate-Opener  [lawful]  Primary Deity
      Caelia description...

    ◇ Yrdin the Shadow-Walker  [neutral] (Death)
      Yrdin description...

    Core Tenets
      • Honor the earth that sustains you
      • Speak truth even when it burns
      ...

    Clergy: Dusk-Warden, Grave-Warden, Dawn-Singer

    Holy Days
      ✦ The Spring Conclave
      ✦ Feast of Caelia

    Holy Sites
      🏛 Crystal Temple of Caelia  📍Ravengard, Blackland
      ...
```

## TTRPG Export Section

Included as `pantheon` in the TTRPG JSON export:

```json
{
  "pantheon": {
    "religions": [...],
    "region_religion_map": {...},
    "total_deities": 6,
    "total_holy_sites": 17,
    "dominant_religion": "High Faith"
  }
}
```

Each deity includes `ttrpg_stats` (6-attribute arrays, 18-30 range). Each holy site includes `suggested_encounter_level`.

## Deity Domains

12 domains, each with associated alignments, symbols, holy animals, and biome affinities:

| Domain | Alignment | Biome Affinity |
|--------|-----------|----------------|
| War | neutral | arid |
| Nature | neutral | tropical |
| Knowledge | good | temperate |
| Death | neutral | tundra, arid |
| Trickery | chaotic | tropical |
| Forge | good | temperate |
| Life | good | temperate |
| Tempest | chaotic | arid |
| Twilight | lawful | temperate, tundra |
| Wealth | neutral | arid |
| Fate | lawful | tundra |
| Wilderness | neutral | tropical, tundra |

## Seed Determinism

Same seed + same world → identical pantheon. Every deity name, surname, domain, symbol, holy animal, and holy site name is fully determined by the generation seed.

## See Also

- [CLI Reference](cli.md) — full command reference
- [Export](export.md) — TTRPG export format details
