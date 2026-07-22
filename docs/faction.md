# Faction System

Political, economic, and cultural entities that shape the world.

## Overview

Factions are auto-generated alongside the world (step 9 in `generate_world()`). Each faction has:
- **Name & Type:** One of 12 faction types (kingdom, duchy, merchant guild, etc.)
- **Territory:** List of region names the faction controls
- **Leader:** Named leader with title appropriate to the faction type
- **Stats:** Influence, Wealth, Military, Stability (0-100)
- **Power Score:** influence + wealth + military (0-300)
- **Reputation:** benevolent, respected, neutral, feared, hated
- **Goals:** 2-3 objectives driving faction behaviour
- **Description:** Procedurally generated flavour text

## Faction Types

| Type | Icon | Description |
|------|------|-------------|
| kingdom | ♛ | Sovereign realm with hereditary ruler |
| duchy | ♚ | Territory ruled by duke/duchess |
| merchant_guild | ⚖ | Trade consortium |
| arcane_order | ✦ | Mages and scholars |
| religious_order | † | Devotees spreading faith |
| druidic_circle | ♣ | Nature guardians |
| thieves_guild | ◈ | Underground network |
| mercenary_company | ⚔ | Soldiers-for-hire |
| cult | ◉ | Secretive sect |
| barbarian_clan | ▲ | Warrior tribe |
| noble_house | ◇ | Aristocratic family |
| mining_consortium | ▣ | Mineral exploiters |

## Relationships

Auto-generated between all faction pairs. Types: alliance, trade agreement, vassalage, rivalry, hostility, non-aggression, cultural ties, religious affinity.

## Political Simulation (Phase 12)

During `wyrd run --years N`, factions evolve dynamically:
- **Power drift:** Stats drift each year based on faction type and territory
- **Wars:** Hostile/rival factions may go to war, affecting settlement populations
- **Alliances:** Peacful factions may form alliances
- **Power shifts:** Rare dramatic changes in faction power
- **Collapse:** Very weak factions may collapse entirely
- **Settlement effects:** Strong factions boost prosperity in their territories

## Commands

- `wyrd factions --seed 42` — List all factions with power bars
- `wyrd factions --seed 42 --id 0` — Detail view for a single faction
- `wyrd run --seed 42 --years 200` — Sim shows political events and end-state faction power
- `wyrd explore --seed 42` — Press `f` for factions overlay
