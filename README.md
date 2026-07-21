# wyrd — Generative Fantasy Sandbox 🏔️

A terminal-native generative fantasy sandbox. Build worlds, explore them,
and watch them grow.

```
wyrd generate --seed 42    # Generate a world
wyrd explore --seed 42     # Explore a world interactively (coming soon)
```

## Quick Start

```bash
pip install -e .
wyrd generate --seed 42
```

## Project Status

**Phase 1 — ASCII World Generator** (in progress)
- [x] Seed-based terrain generation
- [x] Biomes, elevation, rivers
- [ ] Settlements with names
- [ ] ANSI-colored output

## Design

wyrd follows a seed-deterministic approach: the same seed always produces
the same world. Share seeds, not world files.
