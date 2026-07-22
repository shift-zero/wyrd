# Export Formats

Three export formats, all in `src/export_*.py`.

## HTML (`export_html.py`)

Self-contained HTML page with:
- Dark theme, monospace font
- Color-coded terrain map
- Legend, region list, lore section
- Simulation snapshot banner (if `--snapshot-year` set)
- Responsive layout

Output: `wyrd-{seed}.html`

## SVG (not shown, but referenced in `__main__.py`)

`export_svg.py` — vector map output.

## TTRPG JSON (`export_ttrpg.py`)

Foundry/WorldAnvil-ready JSON with:
- Campaign settings (name, seed, world description)
- Settlement statblocks (population, governance, defenses, economy)
- NPC rosters with TTRPG stat arrays derived from occupation
- Faction relationships with disposition labels
- Terrain-driven encounter tables (d10 per terrain type)
- Random tables (settlement names, character names, rumours, weather, tavern names)

Output: `wyrd-{seed}.ttrpg.json`

### NPC Stat Mapping

Occupation → stat bonuses (STR/DEX/CON/INT/WIS/CHA). Example:
- `blacksmith` → STR+3, CON+2
- `bard` → CHA+3, DEX+1
- `hunter` → DEX+2, WIS+2

## See also

- [Serialization](serialization.md) — internal JSON format
- [CLI Reference](cli.md) — export command flags
