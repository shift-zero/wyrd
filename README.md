# wyrd — Generative Fantasy Sandbox 🏔️

A terminal-native generative fantasy sandbox. Build worlds, explore them,
and watch them grow.

```
wyrd generate --seed 42    # Generate a world
wyrd generate --seed 42 --brief  # One-line summary
```

## Quick Start

```bash
pip install -e .
wyrd generate --seed 42
```

Or run without installing:
```bash
python3 -m src.__main__ generate --seed 42
```

## Project Status

**Phase 1 — ASCII World Generator** ✅
- [x] Seed-based terrain generation (value noise + octaves)
- [x] Topography: oceans, beaches, grasslands, forests, hills, mountains, snowy peaks
- [x] Procedural rivers flowing downhill from highlands to coast
- [x] Named regions with biome assignment
- [x] Named settlements (hamlet/village/town/city) with population
- [x] ANSI-colored terminal output with legend
- [x] CLI with `--seed`, `--width`, `--height`, `--brief` flags
- [x] Seed-deterministic: same seed = same world, always

**Phase 2 — Lore Engine** ✅
- [x] Region descriptions and culture names
- [x] Named geographical features (mountains, rivers, bays, forests)
- [x] History snippets per region
- [x] Conflicts and relationships between settlements
- [x] `wyrd generate --lore` and `wyrd describe --seed N` commands

## Design

wyrd follows a seed-deterministic approach: the same seed always produces
the same world. Share seeds, not world files.

| Symbol | Terrain      |
|--------|--------------|
| `~`    | Ocean        |
| `.`    | Beach/sand   |
| `,`    | Grassland    |
| `*`    | Forest       |
| `^`    | Hills        |
| `▲`    | Mountains    |
| `◌`    | Snowy peaks  |
| `≈`    | River        |
| `◉●∘·` | Settlements  |

## Examples

```bash
# A world with generous proportions
wyrd generate --seed 12345 --width 100 --height 50

# Just the stats
wyrd generate --seed 42 --brief
> wyrd #42 — 80×40 | 53% land | 3 regions | 9,450 souls
```
