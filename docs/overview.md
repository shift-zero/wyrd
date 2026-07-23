# Overview

**wyrd** is a terminal-native generative fantasy sandbox by [shift-zero](https://github.com/shift-zero/wyrd). It builds complete fantasy worlds from a single integer seed — terrain, cultures, history, characters, centuries of simulated evolution, and living pantheons of gods.

## Phases

| Phase | What | Status |
|-------|------|--------|
| 1 | ASCII world generator (terrain, rivers, settlements) | ✅ |
| 2 | Lore engine (cultures, features, histories) | ✅ |
| 3 | Explorer mode (save/load, HTML, curses UI, queries) | ✅ |
| 4 | Narrative engine (characters, events, quests) | ✅ |
| 5 | Chronicles (era-based world history) | ✅ |
| 6 | Simulation (year-by-year world evolution) | ✅ |
| 7 | The Living World (interactive sim viewer, character integration) | ✅ |
| 8 | The Web Awakens (web dashboard, magic system, world management) | ✅ |
| 9 | The Pantheon (religion system, deity generation, holy sites) | ✅ |
| 10 | Adventure Zones (dungeons, caves, ruins on the world map) | ✅ |
| 11 | Faction System (political entities, relationships, power stats) | ✅ |
| 12 | Political Simulation (faction wars, alliances, power drift in sim) | ✅ |
| 13 | Cataclysmic Events (terrain mutation, landmark system, cascades) | ✅ |
| 14 | Trade & Economy (trade routes, prosperity, disruption) | ✅ |
| 15 | The Weirding (gateway TUI, unified curses interface) | ✅ |
| 16 | Trade Route Map Visualization (roads, specialization titles) | ✅ |
|| 17 | Living Worlds (animated maps, TUI overhaul, embodied play) | ✅ |

## Philosophy

- **Every output is beautiful.** ANSI color, careful layout, no debug spew.
- **Worlds feel real.** Geography constrains lore, not vice versa.
- **Composable.** Phase 1 doesn't know about Phase 4.
- **Seed-deterministic.** Same seed → same world. Share seeds, not files.

## Where to go next

- [Architecture](architecture.md) — how the modules fit together
- [Design](design.md) — design principles in depth
- [CLI Reference](cli.md) — all commands in one place
