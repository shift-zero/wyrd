# Overview

**wyrd** is a terminal-native generative fantasy sandbox by [shift-zero](https://github.com/shift-zero/wyrd). It builds complete fantasy worlds from a single integer seed — terrain, cultures, history, characters, and centuries of simulated evolution.

## Phases

| Phase | What | Status |
|-------|------|--------|
| 1 | ASCII world generator (terrain, rivers, settlements) | ✅ |
| 2 | Lore engine (cultures, features, histories) | ✅ |
| 3 | Explorer mode (save/load, HTML, curses UI, queries) | ✅ |
| 4 | Narrative engine (characters, events, quests) | ✅ |
| 5 | Chronicles (era-based world history) | ✅ |
| 6 | Simulation (year-by-year world evolution) | ✅ (needs polish) |

## Philosophy

- **Every output is beautiful.** ANSI color, careful layout, no debug spew.
- **Worlds feel real.** Geography constrains lore, not vice versa.
- **Composable.** Phase 1 doesn't know about Phase 4.
- **Seed-deterministic.** Same seed → same world. Share seeds, not files.

## Where to go next

- [Architecture](architecture.md) — how the modules fit together
- [Design](design.md) — design principles in depth
- [CLI Reference](cli.md) — all commands in one place
