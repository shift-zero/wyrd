# Export Formats

Three export formats, all in `src/export_*.py`.

## HTML (`export_html.py`)

Self-contained HTML page with:
- Dark theme, monospace font
- Color-coded terrain map
- Legend, region list, lore section
- Simulation snapshot banner (if `--snapshot-year` set)
- Population timeline chart (if sim data available)
- Abandoned settlement markers (⁂)
- Responsive layout

Output: `wyrd-{seed}.html`

## SVG (`export_svg.py`)

Vector map output as standalone SVG.

Output: `wyrd-{seed}.svg`

## TTRPG JSON (`export_ttrpg.py`)

Foundry/WorldAnvil-ready JSON with:

| Section | Content |
|---------|---------|
| meta | Format version, seed, snapshot year, description |
| campaign_settings | Total population, settlement count, region count, current era |
| geography | Region list with biomes, settlements, terrain distribution, map stats |
| chronicles | Era timeline from the chronicles engine |
| settlements | Statblocks with population, governance, defenses, economy |
| npcs | Full NPC rosters with TTRPG stat arrays derived from occupation |
| factions | Settlement relationships with disposition labels |
| quests | Active quests with difficulty, giver, location, rewards |
| history | Recent sim events or narrative events (last 30) |
| encounters | Terrain-driven d10 encounter tables |
| random_tables | Settlement name generator, NPC name generator, weather, rumours, tavern names |
| pantheon | Full pantheon section with deities, religions, holy sites, deity stat blocks |

### NPC Stat Mapping

Occupation → stat bonuses (STR/DEX/CON/INT/WIS/CHA). Example:
- `blacksmith` → STR+3, CON+2
- `bard` → CHA+3, DEX+1
- `hunter` → DEX+2, WIS+2

### Deity Stat Mapping

Domain → stat bonuses for deities. Base stats 18 across all attributes, domain bonuses raise key attributes toward 30 cap. Deities are always superhuman.

## See also

- [Serialization](serialization.md) — internal JSON format
- [Pantheon](pantheon.md) — religion system details
- [CLI Reference](cli.md) — export command flags
