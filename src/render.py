"""
wyrd — Terminal renderer. ANSI-colored map output.
"""

from .world import World, TERRAIN


ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"
ANSI_ITALIC = "\033[3m"


def _color(code: int, bg: bool = False) -> str:
    """Return ANSI escape for a 256-color code."""
    prefix = 48 if bg else 38
    return f"\033[{prefix};5;{code}m"


def render_map(world: World, show_settlements: bool = True) -> str:
    """Render the world as an ANSI-colored string."""
    lines = []

    # Title bar
    lines.append(f"{ANSI_BOLD}wyrd — seed {world.seed}{ANSI_RESET}")
    lines.append(f"{world.width}×{world.height} | {len(world.regions)} regions\n")

    # Map body
    for y in range(world.height):
        row_chars = []
        for x in range(world.width):
            terrain_key = world.terrain[y][x]
            info = TERRAIN[terrain_key]

            # Check for settlement at this position
            settlement_char = None
            for region in world.regions:
                for s in region.settlements:
                    if s.x == x and s.y == y and show_settlements:
                        settlement_char = s.char
                        break
                if settlement_char:
                    break

            if settlement_char:
                row_chars.append(f"{_color(226)}{ANSI_BOLD}{settlement_char}{ANSI_RESET}")
            else:
                row_chars.append(f"{_color(info['color'])}{info['char']}{ANSI_RESET}")
        lines.append("".join(row_chars))

    # Legend
    lines.append("")
    for key, info in TERRAIN.items():
        lines.append(f"  {_color(info['color'])}{info['char']}{ANSI_RESET}  {info['desc']}")

    lines.append(f"\n  {_color(226)}{ANSI_BOLD}●{ANSI_RESET}  Settlement (size: · hamlet ∘ village ● town ◉ city)")

    # Region list
    lines.append(f"\n{ANSI_BOLD}Regions:{ANSI_RESET}")
    for region in world.regions:
        settlements = ", ".join(
            f"{s.name} ({s.kind})" for s in region.settlements
        )
        lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET} — {settlements}")

    return "\n".join(lines)


def render_brief(world: World) -> str:
    """Render a compact one-line summary."""
    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    land = sum(1 for row in world.terrain for t in row
               if t not in ("deep_water", "shallow"))
    return (
        f"wyrd #{world.seed} — "
        f"{world.width}×{world.height} | "
        f"{land / world.tiles * 100:.0f}% land | "
        f"{len(world.regions)} regions | "
        f"{total_pop:,} souls"
    )


def render_lore(world: World) -> str:
    """Render the lore of a world."""
    if not world.lore:
        return "(no lore generated)"

    lines = []
    lore = world.lore

    lines.append(f"{ANSI_BOLD}═══ Lore of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    for region in world.regions:
        rname = region.name
        biome_colors = {
            "temperate": _color(28),
            "arid": _color(172),
            "tundra": _color(250),
            "tropical": _color(35),
        }
        bcolor = biome_colors.get(region.biome, _color(255))

        lines.append(f"{ANSI_BOLD}{rname}{ANSI_RESET}  {bcolor}({region.biome}){ANSI_RESET}")

        # Culture
        if rname in lore.cultures:
            lines.append(f"  {ANSI_DIM}Culture:{ANSI_RESET} {ANSI_ITALIC}{lore.cultures[rname]}{ANSI_RESET}")
        if rname in lore.culture_descriptions:
            for desc in lore.culture_descriptions[rname]:
                lines.append(f"    {desc}")

        # Region description
        if rname in lore.region_descriptions:
            lines.append(f"  {ANSI_DIM}Land:{ANSI_RESET} {lore.region_descriptions[rname]}")

        # History
        if rname in lore.histories:
            lines.append(f"  {ANSI_DIM}History:{ANSI_RESET} {lore.histories[rname]}")

        lines.append("")

    # Geographical features
    if lore.features:
        lines.append(f"{ANSI_BOLD}Notable Features:{ANSI_RESET}")
        for feat in lore.features:
            fcolor = {
                "mountain_range": _color(130),
                "river": _color(45),
                "bay": _color(33),
                "forest": _color(22),
            }.get(feat["type"], _color(255))
            feat_icon = {
                "mountain_range": "▲",
                "river": "≈",
                "bay": "~",
                "forest": "*",
            }.get(feat["type"], "·")
            lines.append(f"  {fcolor}{ANSI_BOLD}{feat_icon}{ANSI_RESET} {feat['name']}")
            lines.append(f"    {feat['desc']}")
        lines.append("")

    # Settlement relationships
    if lore.relationships:
        lines.append(f"{ANSI_BOLD}Relationships:{ANSI_RESET}")
        rel_colors = {
            "trade": _color(28),
            "rivalry": _color(196),
            "alliance": _color(33),
            "feud": _color(160),
            "vassalage": _color(130),
            "marriage_tie": _color(205),
            "religious": _color(99),
            "cultural": _color(213),
        }
        for rel in lore.relationships:
            color = rel_colors.get(rel["type"], _color(255))
            icon = {
                "trade": "⇄",
                "rivalry": "⚔",
                "alliance": "⚝",
                "feud": "✗",
                "vassalage": "→",
                "marriage_tie": "♡",
                "religious": "†",
                "cultural": "♫",
            }.get(rel["type"], "·")
            lines.append(f"  {color}{icon}{ANSI_RESET} {rel['description']}")
        lines.append("")

    return "\n".join(lines)
