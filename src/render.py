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
                # Check for landmark at this position (from cataclysms)
                landmark_char = None
                landmark_color = None
                for lm in world.landmarks:
                    if lm.x == x and lm.y == y:
                        landmark_char = lm.char
                        landmark_color = lm.color
                        break
                if landmark_char:
                    row_chars.append(f"{_color(landmark_color)}{ANSI_BOLD}{landmark_char}{ANSI_RESET}")
                else:
                    # Check for adventure zone at this position
                    zone_char = None
                    zone_color = None
                for z in world.adventure_zones:
                    if z.x == x and z.y == y:
                        zone_char = z.char
                        zone_color = z.color
                        break
                if zone_char and show_settlements:
                    row_chars.append(f"{_color(zone_color)}{ANSI_BOLD}{zone_char}{ANSI_RESET}")
                else:
                    row_chars.append(f"{_color(info['color'])}{info['char']}{ANSI_RESET}")
        lines.append("".join(row_chars))

    # Legend
    lines.append("")
    for key, info in TERRAIN.items():
        lines.append(f"  {_color(info['color'])}{info['char']}{ANSI_RESET}  {info['desc']}")

    lines.append(f"\n  {_color(226)}{ANSI_BOLD}●{ANSI_RESET}  Settlement (size: · hamlet ∘ village ● town ◉ city)")

    # Adventure zone legend
    from .world import ADVENTURE_ZONE_TYPES
    for key, info in ADVENTURE_ZONE_TYPES.items():
        lines.append(
            f"  {_color(info['color'])}{ANSI_BOLD}{info['char']}{ANSI_RESET}  {info['desc']}"
        )

    # Landmark legend (from cataclysms)
    if world.landmarks:
        unique_types = sorted(set(lm.landmark_type for lm in world.landmarks))
        landmark_legend = {
            "crater": ("⊙", 130, "Crater"), "chasm": ("≋", 240, "Chasm"),
            "ash_waste": ("▒", 243, "Ash waste"), "magma_field": ("◉", 202, "Magma field"),
            "drowned_coast": ("≈", 33, "Drowned coast"), "sinkhole": ("◎", 94, "Sinkhole"),
            "petrified_forest": ("♧", 240, "Petrified forest"), "rift": ("╳", 196, "Rift"),
            "scar": ("┅", 250, "Scar"),
        }
        lines.append(f"\n{ANSI_BOLD}Landmarks:{ANSI_RESET}")
        for lt in unique_types:
            if lt in landmark_legend:
                ch, clr, desc = landmark_legend[lt]
                lines.append(f"  {_color(clr)}{ANSI_BOLD}{ch}{ANSI_RESET}  {desc}")
        for lm in world.landmarks:
            year_str = f" (Y{lm.cataclysm_year})" if lm.cataclysm_year else ""
            lines.append(
                f"    {_color(lm.color)}{lm.char}{ANSI_RESET}  "
                f"{ANSI_BOLD}{lm.name}{ANSI_RESET}{year_str}"
            )

    # Region list
    lines.append(f"\n{ANSI_BOLD}Regions:{ANSI_RESET}")
    for region in world.regions:
        settlements = ", ".join(
            f"{s.name} ({s.kind})" for s in region.settlements
        )
        lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET} — {settlements}")

    return "\n".join(lines)


def render_landmarks(world: World) -> str:
    """Render a detailed view of all cataclysm-created landmarks."""
    if not world.landmarks:
        return ""

    from .cataclysm import CATASTROPHE_TYPES
    lines = []
    lines.append(f"{ANSI_BOLD}═══════════════════════════════════════════{ANSI_RESET}")
    lines.append(f"{ANSI_BOLD}  Landmarks — Marks of Catastrophe{ANSI_RESET}")
    lines.append(f"{ANSI_BOLD}═══════════════════════════════════════════{ANSI_RESET}")

    cataclysm_icons = {
        "earthquake": "💢", "volcanic_eruption": "🌋", "great_plague": "☠",
        "tsunami": "🌊", "meteor_strike": "☄", "great_fire": "🔥",
        "magical_cataclysm": "⚡",
    }

    for i, lm in enumerate(world.landmarks):
        icon = cataclysm_icons.get(lm.cataclysm_type, "◆")
        year_str = f"Year {lm.cataclysm_year}" if lm.cataclysm_year else "Unknown year"
        region_str = f" in {lm.region}" if lm.region else ""
        lines.append("")
        lines.append(
            f"  {_color(lm.color)}{lm.char}{ANSI_RESET}  "
            f"{ANSI_BOLD}{lm.name}{ANSI_RESET}  "
            f"{ANSI_DIM}({icon} {lm.cataclysm_type}, {year_str}{region_str}){ANSI_RESET}"
        )
        lines.append(f"       {ANSI_DIM}{lm.description}{ANSI_RESET}")
        lines.append(f"       {ANSI_DIM}at ({lm.x}, {lm.y}){ANSI_RESET}")

    lines.append("")
    lines.append(f"{ANSI_DIM}Total: {len(world.landmarks)} landmark{'s' if len(world.landmarks) != 1 else ''}{ANSI_RESET}")
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


# ── Narrative Rendering ──────────────────────────────────────────────


def render_characters(world: World) -> str:
    """Render the characters of a world."""
    if not world.narrative or not world.narrative.characters:
        return f"{ANSI_DIM}(no characters generated){ANSI_RESET}"

    lines = []
    narr = world.narrative

    lines.append(f"{ANSI_BOLD}═══ Characters of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    # Group characters by region
    by_region: dict[str, list] = {}
    for c in narr.characters:
        by_region.setdefault(c.home_region, []).append(c)

    for region in world.regions:
        rname = region.name
        chars = by_region.get(rname, [])
        if not chars:
            continue

        lines.append(f"{ANSI_BOLD}{rname}{ANSI_RESET}  ({_color(240)}{len(chars)} characters{ANSI_RESET})")

        for c in chars:
            age_str = f", {c.age}" if c.age else ""
            lines.append(
                f"  {ANSI_BOLD}{c.full_name}{ANSI_RESET}"
                f"{ANSI_DIM}{age_str}{ANSI_RESET}"
                f" — {_color(28)}⏺{ANSI_RESET} {c.occupation}"
                f"  {_color(240)}📍{c.home_settlement}{ANSI_RESET}"
            )
            trait_str = ", ".join(c.personality_traits)
            lines.append(f"    {ANSI_ITALIC}{trait_str}{ANSI_RESET}")
            lines.append(f"    {ANSI_DIM}{c.backstory}{ANSI_RESET}")

        lines.append("")

    return "\n".join(lines)


def render_events(world: World) -> str:
    """Render the event chains of a world as a timeline."""
    if not world.narrative or not world.narrative.events:
        return f"{ANSI_DIM}(no events recorded){ANSI_RESET}"

    lines = []
    narr = world.narrative

    lines.append(f"{ANSI_BOLD}═══ Timeline of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    # Sort events chronologically
    sorted_events = sorted(narr.events, key=lambda e: e.year)

    event_colors = {
        "conflict": _color(196),
        "discovery": _color(33),
        "natural": _color(130),
        "political": _color(99),
        "cultural": _color(213),
    }
    event_icons = {
        "conflict": "⚔",
        "discovery": "✦",
        "natural": "🌋",
        "political": "⚝",
        "cultural": "♫",
    }

    for e in sorted_events:
        color = event_colors.get(e.event_type, _color(255))
        icon = event_icons.get(e.event_type, "·")
        year_str = f"{e.year} AE" if e.year else "Unknown year"

        lines.append(
            f"  {ANSI_DIM}{year_str}{ANSI_RESET} "
            f"{color}{icon}{ANSI_RESET} "
            f"{ANSI_BOLD}{e.name}{ANSI_RESET}"
        )
        lines.append(f"    {e.description}")
        if e.characters_involved:
            chars_str = ", ".join(e.characters_involved)
            lines.append(f"    {ANSI_DIM}Involved: {chars_str}{ANSI_RESET}")
        if e.consequences:
            for con in e.consequences:
                lines.append(f"    {ANSI_DIM}→ {con}{ANSI_RESET}")
        lines.append("")

    return "\n".join(lines)


def render_quests(world: World) -> str:
    """Render the quests available in a world."""
    if not world.narrative or not world.narrative.quests:
        return f"{ANSI_DIM}(no quests available){ANSI_RESET}"

    lines = []
    narr = world.narrative

    lines.append(f"{ANSI_BOLD}═══ Quests of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    difficulty_colors = {
        "trivial": _color(28),
        "easy": _color(33),
        "moderate": _color(130),
        "hard": _color(196),
        "epic": _color(199),
    }
    quest_icons = {
        "exploration": "🗺",
        "combat": "⚔",
        "diplomacy": "🤝",
        "gathering": "🎒",
        "intrigue": "🔍",
    }

    for q in narr.quests:
        dcolor = difficulty_colors.get(q.difficulty, _color(255))
        icon = quest_icons.get(q.quest_type, "·")
        status_str = f"{ANSI_BOLD}ACTIVE{ANSI_RESET}" if q.is_active else f"{ANSI_DIM}COMPLETED{ANSI_RESET}"

        lines.append(
            f"  {icon} {ANSI_BOLD}{q.name}{ANSI_RESET}"
            f"  {dcolor}[{q.difficulty}]{ANSI_RESET}"
            f"  {status_str}"
        )
        lines.append(f"    {_color(240)}Type:{ANSI_RESET} {q.quest_type}")
        lines.append(f"    {_color(240)}Location:{ANSI_RESET} {q.target_region}")
        if q.giver_character:
            lines.append(f"    {_color(240)}Given by:{ANSI_RESET} {q.giver_character}")
        lines.append(f"    {q.description}")
        if q.rewards:
            reward_str = ", ".join(q.rewards)
            lines.append(f"    {_color(226)}Reward:{ANSI_RESET} {reward_str}")
        lines.append("")

    return "\n".join(lines)


def render_narrative(world: World) -> str:
    """Render complete narrative (characters + timeline + quests)."""
    parts = [
        render_characters(world),
        "",
        render_events(world),
        "",
        render_quests(world),
    ]
    return "\n".join(parts)


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


# ── Chronicles Rendering ─────────────────────────────────────────────


_CHRONICLE_TYPE_ICONS = {
    "founding": "🏛",
    "golden_age": "✦",
    "cataclysm": "🌋",
    "dark_age": "☽",
    "age_of": "◇",
    "decline": "▽",
    "rebirth": "↑",
    "schism": "⚔",
}

_CHRONICLE_TYPE_COLORS = {
    "founding": _color(28),
    "golden_age": _color(226),
    "cataclysm": _color(196),
    "dark_age": _color(240),
    "age_of": _color(33),
    "decline": _color(130),
    "rebirth": _color(213),
    "schism": _color(99),
}


def render_chronicles(world) -> str:
    """Render the chronicles (era-based history) of a world."""
    try:
        from .chronicles import Chronicles
    except ImportError:
        return f"{ANSI_DIM}(chronicles engine not available){ANSI_RESET}"

    chronicles = getattr(world, 'chronicles', None)
    if not chronicles or not chronicles.eras:
        return f"{ANSI_DIM}(no chronicles generated){ANSI_RESET}"

    lines = []
    lines.append(f"{ANSI_BOLD}═══ The Chronicles of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    for i, era in enumerate(chronicles.eras):
        icon = _CHRONICLE_TYPE_ICONS.get(era.era_type, "·")
        color = _CHRONICLE_TYPE_COLORS.get(era.era_type, _color(255))
        era_num = i + 1

        # Era header
        lines.append(
            f"  {color}{icon}{ANSI_RESET} "
            f"{ANSI_BOLD}Era {era_num}: {era.name}{ANSI_RESET}"
            f"  {_color(240)}[{era.era_type.replace('_', ' ')}]{ANSI_RESET}"
        )

        # Date range
        year_str = f"Year {era.start_year} — Year {era.end_year}"
        if era.is_present:
            year_str += f"  {ANSI_BOLD}(Present Age){ANSI_RESET}"
        lines.append(f"  {ANSI_DIM}{year_str}{ANSI_RESET}")

        # Description
        lines.append(f"  {era.description}")
        lines.append("")

        # World modifiers
        if era.world_modifiers:
            for mod in era.world_modifiers:
                lines.append(f"    {_color(94)}◊{ANSI_RESET} {_color(94)}{mod}{ANSI_RESET}")
            lines.append("")

        # Events
        if era.events:
            lines.append(f"    {ANSI_DIM}── Events ──{ANSI_RESET}")
            for ev in era.events:
                ev_year = f"{_color(240)}[{ev['year']}]{ANSI_RESET}"
                ev_icon = ""
                if ev.get("type") == "battle":
                    ev_icon = f"{_color(196)}⚔{ANSI_RESET} "
                elif ev.get("type") == "discovery":
                    ev_icon = f"{_color(33)}✦{ANSI_RESET} "
                elif ev.get("type") == "founding":
                    ev_icon = f"{_color(28)}▲{ANSI_RESET} "
                elif ev.get("type") == "natural":
                    ev_icon = f"{_color(130)}≈{ANSI_RESET} "
                elif ev.get("type") == "pact":
                    ev_icon = f"{_color(99)}⚝{ANSI_RESET} "

                lines.append(f"    {ev_year} {ev_icon}{ANSI_BOLD}{ev['name']}{ANSI_RESET}")
                lines.append(f"      {ev['description']}")

                if ev.get("characters"):
                    chars_str = ", ".join(ev["characters"])
                    lines.append(f"      {_color(240)}Legendary participants: {chars_str}{ANSI_RESET}")
            lines.append("")

    # Summary
    lines.append(f"{ANSI_DIM}── {chronicles.num_eras} eras spanning {chronicles.world_age} years ──{ANSI_RESET}")

    return "\n".join(lines)


# ── Magic System Rendering ──────────────────────────────────────────────

_MAGIC_SOURCE_ICONS = {
    "arcane": "✦",
    "divine": "†",
    "natural": "♣",
    "elemental": "◆",
    "shadow": "◈",
    "blood": "♦",
    "celestial": "☆",
}

_MAGIC_SOURCE_COLORS = {
    "arcane": _color(99),
    "divine": _color(226),
    "natural": _color(28),
    "elemental": _color(196),
    "shadow": _color(240),
    "blood": _color(160),
    "celestial": _color(33),
}


def render_magic(world) -> str:
    """Render the magic system of a world."""
    magic = getattr(world, 'magic', None)
    if not magic:
        return f"{ANSI_DIM}(no magic system generated){ANSI_RESET}"

    lines = []
    icon = _MAGIC_SOURCE_ICONS.get(magic.source, "·")
    color = _MAGIC_SOURCE_COLORS.get(magic.source, _color(255))

    # Header
    lines.append(f"{ANSI_BOLD}═══ The Magic of wyrd #{world.seed} ═══{ANSI_RESET}\n")
    lines.append(f"  {color}{icon}{ANSI_RESET}  {ANSI_BOLD}{magic.name}{ANSI_RESET}")
    lines.append(f"    {ANSI_DIM}Source: {magic.source.title()}{ANSI_RESET}")
    lines.append(f"    {ANSI_DIM}Practitioners: {magic.practitioners}{ANSI_RESET}")
    lines.append("")
    lines.append(f"  {magic.description}")
    lines.append("")

    # Schools
    if magic.schools:
        lines.append(f"  {ANSI_BOLD}Schools of Magic{ANSI_RESET}")
        for s in magic.schools:
            align_color = {
                "good": _color(28),
                "evil": _color(160),
                "lawful": _color(33),
                "chaotic": _color(213),
                "neutral": _color(255),
            }.get(s.alignment, _color(255))
            lines.append(
                f"    {color}◈{ANSI_RESET} "
                f"{ANSI_BOLD}{s.name}{ANSI_RESET} "
                f"({align_color}{s.alignment}{ANSI_RESET})"
            )
            lines.append(f"      {s.description}")
            if s.spell_examples:
                spells = f"{ANSI_DIM}Spells: {', '.join(s.spell_examples[:3])}{'…' if len(s.spell_examples) > 3 else ''}{ANSI_RESET}"
                lines.append(f"      {spells}")
        lines.append("")

    # Traditions
    if magic.traditions:
        lines.append(f"  {ANSI_BOLD}Magical Traditions{ANSI_RESET}")
        for t in magic.traditions:
            lines.append(f"    {_color(94)}⌾{ANSI_RESET} {ANSI_BOLD}{t.name}{ANSI_RESET}")
            lines.append(f"      {t.description}")
            if t.origin:
                lines.append(f"      {ANSI_DIM}Origin: {t.origin} · Region: {t.region}{ANSI_RESET}")
        lines.append("")

    return "\n".join(lines)


# ── Faction Rendering ─────────────────────────────────────────────

_REPUTATION_COLORS = {
    "benevolent": _color(28),
    "respected": _color(33),
    "neutral": _color(255),
    "feared": _color(196),
    "hated": _color(160),
}

_REPUTATION_ICONS = {
    "benevolent": "✦",
    "respected": "★",
    "neutral": "·",
    "feared": "⚠",
    "hated": "✗",
}


def render_factions(world) -> str:
    """Render the factions of a world."""
    factions = getattr(world, 'factions', None)
    if not factions:
        return f"{ANSI_DIM}(no factions generated){ANSI_RESET}"

    lines = []
    lines.append(f"{ANSI_BOLD}═══ The Factions of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    # Sort by power score descending
    sorted_factions = sorted(factions, key=lambda f: f.power_score, reverse=True)

    for f in sorted_factions:
        type_info = f.type_info
        icon = type_info.get("icon", "?")
        color = _color(f.color)

        reputation_color = _REPUTATION_COLORS.get(f.reputation, _color(255))
        reputation_icon = _REPUTATION_ICONS.get(f.reputation, "·")

        # Power bar (visual indicator)
        power = f.power_score
        bar_len = 20
        filled = max(1, int(power / 300 * bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)

        lines.append(
            f"  {color}{icon}{ANSI_RESET}  "
            f"{ANSI_BOLD}{f.name}{ANSI_RESET}"
            f"  {_color(240)}({type_info['desc']}){ANSI_RESET}"
            f"  {reputation_color}{reputation_icon} {f.reputation}{ANSI_RESET}"
        )

        # Leadership
        if f.leader_name:
            lines.append(
                f"    {_color(240)}Leader:{ANSI_RESET} "
                f"{f.leader_title} {ANSI_BOLD}{f.leader_name}{ANSI_RESET}"
            )

        # Territory
        if f.territory:
            terr_str = ", ".join(f.territory)
            lines.append(f"    {_color(240)}Territory:{ANSI_RESET} {terr_str}")

        # Power stats with visual bar
        lines.append(
            f"    {_color(240)}Power:{ANSI_RESET} "
            f"{ANSI_ITALIC}{bar}{ANSI_RESET} "
            f"{_color(240)}({power}/300){ANSI_RESET}"
        )

        # Influence / Wealth / Military
        stats = []
        influence_color = _color(99)
        wealth_color = _color(226)
        military_color = _color(196)
        stats.append(f"{influence_color}◈{ANSI_RESET} Influence {f.influence}")
        stats.append(f"{wealth_color}♦{ANSI_RESET} Wealth {f.wealth}")
        stats.append(f"{military_color}⚔{ANSI_RESET} Military {f.military}")
        stats.append(f"{_color(130)}○{ANSI_RESET} Stability {f.stability}")
        lines.append(f"    {'  '.join(stats)}")

        # Description
        if f.description:
            lines.append(f"    {ANSI_ITALIC}{f.description}{ANSI_RESET}")

        # Goals
        if f.goals:
            lines.append(f"    {ANSI_BOLD}Goals:{ANSI_RESET}")
            for goal in f.goals:
                lines.append(f"      {_color(94)}→{ANSI_RESET} {goal}")

        lines.append("")

    # ── Relationships ────────────────────────────────────────────────
    relationships = getattr(world, 'faction_relationships', [])
    if relationships:
        lines.append(f"{ANSI_BOLD}Inter-Faction Relationships:{ANSI_RESET}")
        from .faction import RELATIONSHIP_ICONS, RELATIONSHIP_COLORS
        for rel in relationships:
            r_icon = RELATIONSHIP_ICONS.get(rel.rel_type, "·")
            r_color = _color(RELATIONSHIP_COLORS.get(rel.rel_type, 250))
            lines.append(f"  {r_color}{r_icon}{ANSI_RESET} {rel.description}")
        lines.append("")

    # Summary
    lines.append(
        f"{ANSI_DIM}── {len(factions)} factions "
        f"· total power: {sum(f.power_score for f in sorted_factions):,}/{len(factions)*300} "
        f"· {len(relationships)} relationships ──{ANSI_RESET}"
    )

    return "\n".join(lines)


def render_faction_detail(faction) -> str:
    """Render detailed information about a single faction."""
    from .faction import RELATIONSHIP_ICONS, RELATIONSHIP_COLORS
    color = _color(faction.color)
    type_info = faction.type_info
    icon = type_info.get("icon", "?")

    lines = []
    lines.append(f"{color}{ANSI_BOLD}{icon}{ANSI_RESET}  {ANSI_BOLD}{faction.name}{ANSI_RESET}")
    lines.append(f"  {ANSI_DIM}Type:{ANSI_RESET} {type_info['desc']}")
    lines.append(f"  {ANSI_DIM}Power Score:{ANSI_RESET} {faction.power_score}/300")

    reputation_color = _REPUTATION_COLORS.get(faction.reputation, _color(255))
    lines.append(f"  {ANSI_DIM}Reputation:{ANSI_RESET} {reputation_color}{faction.reputation}{ANSI_RESET}")
    lines.append(f"  {ANSI_DIM}Influence:{ANSI_RESET} {'█' * (faction.influence // 10)}{'░' * (10 - faction.influence // 10)} {faction.influence}/100")
    lines.append(f"  {ANSI_DIM}Wealth:{ANSI_RESET}     {'█' * (faction.wealth // 10)}{'░' * (10 - faction.wealth // 10)} {faction.wealth}/100")
    lines.append(f"  {ANSI_DIM}Military:{ANSI_RESET}   {'█' * (faction.military // 10)}{'░' * (10 - faction.military // 10)} {faction.military}/100")
    lines.append(f"  {ANSI_DIM}Stability:{ANSI_RESET}  {'█' * (faction.stability // 10)}{'░' * (10 - faction.stability // 10)} {faction.stability}/100")

    if faction.leader_name:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Leadership{ANSI_RESET}")
        lines.append(f"    {faction.leader_title} {faction.leader_name}")

    if faction.territory:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Territory{ANSI_RESET}")
        for t in faction.territory:
            lines.append(f"    {_color(130)}◊{ANSI_RESET} {t}")

    if faction.description:
        lines.append("")
        lines.append(f"  {ANSI_ITALIC}{faction.description}{ANSI_RESET}")

    if faction.goals:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Goals{ANSI_RESET}")
        for g in faction.goals:
            lines.append(f"    {_color(94)}→{ANSI_RESET} {g}")

    return "\n".join(lines)


# ── Pantheon Rendering ───────────────────────────────────────────────────

_PANTHEON_ALIGNMENT_COLORS = {
    "good": _color(28),
    "evil": _color(160),
    "lawful": _color(33),
    "chaotic": _color(213),
    "neutral": _color(255),
}


def render_pantheon(world) -> str:
    """Render the pantheon and religions of a world."""
    pantheon = getattr(world, 'pantheon', None)
    if not pantheon or not pantheon.religions:
        return f"{ANSI_DIM}(no pantheon generated){ANSI_RESET}"

    lines = []
    lines.append(f"{ANSI_BOLD}═══ The Pantheon of wyrd #{world.seed} ═══{ANSI_RESET}\n")

    for i, religion in enumerate(pantheon.religions):
        # Religion header
        icon = "†" if i == 0 else "‡"
        adherent_count = sum(
            1 for rn in pantheon.region_religion.values()
            if rn == religion.name
        )
        lines.append(
            f"  {_color(226)}{ANSI_BOLD}{icon}{ANSI_RESET}  "
            f"{ANSI_BOLD}{religion.name}{ANSI_RESET}"
            f"  {_color(240)}[{adherent_count} region{'s' if adherent_count != 1 else ''}]{ANSI_RESET}"
        )
        lines.append(f"    {religion.description}")
        lines.append("")

        # Primary deity
        if religion.primary_deity:
            prim = next((d for d in religion.pantheon if d.name == religion.primary_deity), None)
            if prim:
                ac = _PANTHEON_ALIGNMENT_COLORS.get(prim.alignment, _color(255))
                lines.append(
                    f"    {ac}★{ANSI_RESET} {ANSI_BOLD}{prim.name} {prim.surname}{ANSI_RESET}"
                    f"  {ac}[{prim.alignment}]{ANSI_RESET}"
                    f"  {_color(240)}Primary Deity{ANSI_RESET}"
                )
                lines.append(f"      {prim.description}")
                lines.append("")

        # Pantheon
        other_deities = [d for d in religion.pantheon if d.name != religion.primary_deity]
        if other_deities:
            lines.append(f"    {ANSI_BOLD}Deities{ANSI_RESET}")
            for deity in other_deities:
                ac = _PANTHEON_ALIGNMENT_COLORS.get(deity.alignment, _color(255))
                domains_str = ", ".join(deity.domains)
                lines.append(
                    f"      {ac}◇{ANSI_RESET} "
                    f"{ANSI_BOLD}{deity.name} {deity.surname}{ANSI_RESET}"
                    f"  {ac}({domains_str}){ANSI_RESET}"
                )
                lines.append(f"        {deity.description}")
            lines.append("")

        # Tenets
        if religion.tenets:
            lines.append(f"    {ANSI_BOLD}Core Tenets{ANSI_RESET}")
            for tenet in religion.tenets:
                lines.append(f"      {_color(94)}•{ANSI_RESET} {tenet}")
            lines.append("")

        # Clergy
        if religion.clergy_titles:
            titles_str = ", ".join(religion.clergy_titles[:4])
            lines.append(f"    {_color(240)}Clergy: {titles_str}{ANSI_RESET}")
            lines.append("")

        # Holy days
        if religion.holy_days:
            lines.append(f"    {ANSI_BOLD}Holy Days{ANSI_RESET}")
            for day in religion.holy_days:
                lines.append(f"      {_color(33)}✦{ANSI_RESET} {day}")
            lines.append("")

        # Holy sites
        if religion.holy_sites:
            lines.append(f"    {ANSI_BOLD}Holy Sites{ANSI_RESET}")
            for site in religion.holy_sites[:5]:
                site_icon = {
                    "temple": "🏛", "shrine": "◈", "monastery": "⌾",
                    "oracle": "◎", "grove": "♣", "sanctuary": "☙",
                }.get(site.site_type, "·")
                lines.append(
                    f"      {site_icon} {ANSI_BOLD}{site.name}{ANSI_RESET}"
                    f"  {_color(240)}📍{site.settlement}, {site.region}{ANSI_RESET}"
                )
                lines.append(f"        {site.description}")
            if len(religion.holy_sites) > 5:
                lines.append(f"        {ANSI_DIM}...and {len(religion.holy_sites) - 5} more sites{ANSI_RESET}")
            lines.append("")

        if i < len(pantheon.religions) - 1:
            lines.append(f"  {ANSI_DIM}──{ANSI_RESET}\\n")

    # Summary
    total_sites = pantheon.total_holy_sites
    total_deities = pantheon.total_deities
    lines.append(
        f"{ANSI_DIM}── {total_deities} deities across {len(pantheon.religions)} religion{'s' if len(pantheon.religions) != 1 else ''}"
        f" · {total_sites} holy sites ──{ANSI_RESET}"
    )

    return "\n".join(lines)


# ── Bestiary Rendering ───────────────────────────────────────────────────


_SPECIAL_ABILITY_COLOR = _color(196)
_BEHAVIOR_COLORS = {
    "aggressive": _color(196), "territorial": _color(172), "ambush": _color(240),
    "pack_hunter": _color(160), "solitary": _color(250), "defensive": _color(28),
    "migratory": _color(33), "nocturnal": _color(99), "docile": _color(34),
    "curious": _color(213), "cunning": _color(130), "patient": _color(94),
}


def render_bestiary(world) -> str:
    """Render the entire bestiary of a world."""
    bestiary = getattr(world, 'bestiary', None)
    if not bestiary:
        return f"{ANSI_DIM}(no bestiary generated){ANSI_RESET}"

    lines = []
    lines.append(f"{ANSI_BOLD}═══ Bestiary of wyrd #{world.seed} ═══{ANSI_RESET}\\n")

    # Group by habitat
    by_habitat: dict[str, list] = {}
    for c in bestiary:
        by_habitat.setdefault(c.habitat, []).append(c)

    for habitat, creatures in sorted(by_habitat.items()):
        creatures.sort(key=lambda c: c.tier, reverse=True)

        habitat_color = {
            "temperate": _color(28), "arid": _color(172),
            "tundra": _color(250), "tropical": _color(35),
            "swamp": _color(64), "desert": _color(179),
            "various": _color(99),
        }.get(habitat, _color(250))
        habitat_label = {
            "temperate": "Temperate Forests", "arid": "Arid Wastes",
            "tundra": "Tundra & Snow", "tropical": "Tropical Jungles",
            "swamp": "Swamps & Marshlands", "desert": "Deserts & Wastes",
            "various": "Various / Faction-Tied",
        }.get(habitat, habitat)

        lines.append(f"{habitat_color}{ANSI_BOLD}⏺ {habitat_label}{ANSI_RESET}  "
                     f"{ANSI_DIM}({len(creatures)} species){ANSI_RESET}")

        for c in creatures:
            type_color = {
                "beast": _color(130), "monstrosity": _color(196),
                "undead": _color(240), "dragon": _color(196),
                "fey": _color(213), "elemental": _color(33),
                "aberration": _color(99), "construct": _color(250),
                "giant": _color(130), "humanoid_bandit": _color(160),
            }.get(c.creature_type, _color(250))

            tier_icons = {1: "✦", 2: "✦✦", 3: "✦✦✦", 4: "✦✦✦✦", 5: "✦✦✦✦✦"}
            tier_display = tier_icons.get(c.tier, "✦")

            unique_mark = f" {ANSI_BOLD}{_color(226)}★{ANSI_RESET}" if c.is_unique else ""

            affiliation = ""
            if c.faction_affiliation:
                affiliation = f"  {ANSI_DIM}⚑ {c.faction_affiliation}{ANSI_RESET}"

            lines.append(
                f"  {type_color}{c.size[0].upper()}{ANSI_RESET} "
                f"{ANSI_BOLD}{c.name}{ANSI_RESET}{unique_mark}"
                f"  {_color(240)}({c.creature_type.replace('_', ' ')}, CR {c.challenge_rating}){ANSI_RESET}"
                f"  {type_color}{tier_display}{ANSI_RESET}"
                f"{affiliation}"
            )

            if c.variant:
                lines.append(f"    {ANSI_DIM}Variant:{ANSI_RESET} {_color(226)}{c.variant}{ANSI_RESET}")

            b_color = _BEHAVIOR_COLORS.get(c.behavior, _color(250))
            lines.append(f"    {ANSI_DIM}Behavior:{ANSI_RESET} {b_color}{c.behavior.replace('_', ' ')}{ANSI_RESET}")

            if c.suggested_level_range:
                lines.append(f"    {ANSI_DIM}Level:{ANSI_RESET} {c.suggested_level_range}  "
                             f"{ANSI_DIM}Encounter:{ANSI_RESET} {c.encounters}")

            desc = c.description[:120]
            if len(c.description) > 120:
                desc += "..."
            lines.append(f"    {ANSI_ITALIC}{desc}{ANSI_RESET}")

            if c.special_abilities:
                for ab in c.special_abilities[:2]:
                    lines.append(f"      {_SPECIAL_ABILITY_COLOR}⚡{ANSI_RESET} {_SPECIAL_ABILITY_COLOR}{ab}{ANSI_RESET}")

            lines.append("")

        lines.append("")

    total = len(bestiary)
    by_type: dict[str, int] = {}
    for c in bestiary:
        by_type[c.creature_type] = by_type.get(c.creature_type, 0) + 1
    type_summary = " · ".join(
        f"{t.replace('_', ' ')} ×{c}" for t, c in sorted(by_type.items(), key=lambda x: -x[1])[:5]
    )
    lines.append(
        f"{ANSI_DIM}── {total} creatures across {len(by_habitat)} habitats — "
        f"{type_summary}{' …' if len(by_type) > 5 else ''} ──{ANSI_RESET}"
    )

    return "\n".join(lines)


def render_creature_detail(creature) -> str:
    """Render detailed information about a single creature."""
    type_color = {
        "beast": _color(130), "monstrosity": _color(196),
        "undead": _color(240), "dragon": _color(196),
        "fey": _color(213), "elemental": _color(33),
        "aberration": _color(99), "construct": _color(250),
        "giant": _color(130), "humanoid_bandit": _color(160),
    }.get(creature.creature_type, _color(250))

    lines = []
    unique_mark = f" {_color(226)}{ANSI_BOLD}★{ANSI_RESET}" if creature.is_unique else ""
    lines.append(
        f"{type_color}{ANSI_BOLD}{creature.size[0].upper()}{ANSI_RESET}  "
        f"{ANSI_BOLD}{creature.name}{ANSI_RESET}{unique_mark}"
    )
    lines.append(f"  {ANSI_DIM}Type:{ANSI_RESET}       {creature.creature_type.replace('_', ' ')}")
    lines.append(f"  {ANSI_DIM}Tier:{ANSI_RESET}       {creature.tier_label} ({creature.tier}/5)")
    lines.append(f"  {ANSI_DIM}CR:{ANSI_RESET}         {creature.cr_label}")
    lines.append(f"  {ANSI_DIM}Size:{ANSI_RESET}       {creature.size}")
    lines.append(f"  {ANSI_DIM}Habitat:{ANSI_RESET}    {creature.habitat}")
    lines.append(f"  {ANSI_DIM}Behavior:{ANSI_RESET}   {creature.behavior.replace('_', ' ')}")
    lines.append(f"  {ANSI_DIM}Body Plan:{ANSI_RESET}  {creature.body_plan}")

    if creature.variant:
        lines.append(f"  {ANSI_DIM}Variant:{ANSI_RESET}   {_color(226)}{creature.variant}{ANSI_RESET}")

    if creature.faction_affiliation:
        lines.append(f"  {ANSI_DIM}Faction:{ANSI_RESET}   {creature.faction_affiliation}")

    if creature.suggested_level_range:
        lines.append(f"  {ANSI_DIM}Suggested Level:{ANSI_RESET} {creature.suggested_level_range}")
        lines.append(f"  {ANSI_DIM}Encounter:{ANSI_RESET}     {creature.encounters}")

    lines.append("")
    lines.append(f"  {creature.description}")
    lines.append("")

    sb = creature.stat_block
    lines.append(f"  {ANSI_BOLD}Stat Block{ANSI_RESET}")
    lines.append(f"    {ANSI_DIM}AC:{ANSI_RESET} {sb['armor_class']}  "
                 f"{ANSI_DIM}HP:{ANSI_RESET} {sb['hit_points']}  "
                 f"{ANSI_DIM}Damage:{ANSI_RESET} {sb['damage_per_round']}")

    if creature.special_abilities:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Special Abilities{ANSI_RESET}")
        for ab in creature.special_abilities:
            lines.append(f"    {_SPECIAL_ABILITY_COLOR}⚡{ANSI_RESET} {ab}")

    lines.append("")
    lines.append(f"  {ANSI_BOLD}Combat Tactics{ANSI_RESET}")
    lines.append(f"    {ANSI_ITALIC}{creature.combat_tactics}{ANSI_RESET}")

    if creature.loot:
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Loot{ANSI_RESET}")
        for loot in creature.loot:
            lines.append(f"    {_color(226)}♦{ANSI_RESET} {loot}")

    return "\n".join(lines)


# ── Trade Route Map ────────────────────────────────────────────────────

_ROUTE_ECON_ICONS = {
    "farming": "🌾", "logging": "🌲", "mining": "⛏",
    "fishing": "🐟", "trading": "💰", "pastoral": "🐄",
}
_ROUTE_ECON_COLORS = {
    "farming": 220, "logging": 28, "mining": 130,
    "fishing": 33, "trading": 226, "pastoral": 40,
}


def _bresenham_line(x0: int, y0: int, x1: int, y1: int) -> list[tuple[int, int]]:
    """Bresenham's line algorithm — returns list of (x, y) points on the line."""
    points: list[tuple[int, int]] = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return points


def render_trade_route_map(
    world: 'World',
    routes: list,
    settlements: dict,
    title: str = "",
    show_settlements: bool = True,
) -> str:
    """Render the world map with trade route connections overlaid.

    Route-connected settlements get economy-type icons; colored path dots
    (·) are drawn between trading partners using Bresenham lines.
    """
    h, w = world.height, world.width

    # Build settlement lookup: name → (x, y, economy_type)
    s_info: dict[str, tuple[int, int, str]] = {}
    for name, snap in settlements.items():
        s_info[name] = (
            snap.x, snap.y,
            getattr(snap, 'economy_type', None) or "unknown",
        )

    # Collect route-connected settlement names
    connected: set[str] = set()
    for r in routes:
        if getattr(r, 'is_active', True):
            connected.add(getattr(r, 'source', ''))
            connected.add(getattr(r, 'destination', ''))

    # Build character + colour grid from terrain
    grid_chars: list[list[str]] = []
    grid_colors: list[list[int]] = []
    for y in range(h):
        rc: list[str] = []
        rcl: list[int] = []
        for x in range(w):
            tk = world.terrain[y][x]
            info = TERRAIN.get(tk, {"char": "?", "color": 240})
            rc.append(info["char"])
            rcl.append(info["color"])
        grid_chars.append(rc)
        grid_colors.append(rcl)

    # Overlay settlements with economy icons for route-connected ones
    settlement_map: dict[tuple[int, int], str] = {}
    for region in world.regions:
        for s in region.settlements:
            settlement_map[(s.x, s.y)] = s.name
            if show_settlements and 0 <= s.y < h and 0 <= s.x < w:
                if s.name in connected and s.name in s_info:
                    _, _, etype = s_info[s.name]
                    icon = _ROUTE_ECON_ICONS.get(etype, "📦")
                    grid_chars[s.y][s.x] = icon
                    grid_colors[s.y][s.x] = _ROUTE_ECON_COLORS.get(etype, 226)
                elif show_settlements:
                    grid_chars[s.y][s.x] = s.char
                    grid_colors[s.y][s.x] = 226

    # Draw route lines (Bresenham dots, skipping settlements & water)
    route_layer: dict[tuple[int, int], tuple[int, str]] = {}
    for r in routes:
        if not getattr(r, 'is_active', True):
            continue
        src = getattr(r, 'source', '')
        dst = getattr(r, 'destination', '')
        if src not in s_info or dst not in s_info:
            continue
        sx, sy, stype = s_info[src]
        dx, dy, dtype = s_info[dst]
        etype = stype if stype in _ROUTE_ECON_COLORS else (
            dtype if dtype in _ROUTE_ECON_COLORS else "trading"
        )
        color = _ROUTE_ECON_COLORS.get(etype, 226)
        is_road = getattr(r, 'is_road', False)
        dot_char = "━" if is_road else "·"

        for px, py in _bresenham_line(sx, sy, dx, dy):
            # Don't overwrite settlement positions
            if (px, py) in [(sx, sy), (dx, dy)]:
                continue
            # Don't draw over open water
            if 0 <= py < h and 0 <= px < w:
                tk = world.terrain[py][px]
                if tk in ("deep_water", "shallow", "ocean"):
                    continue
                # Road routes use a highlight color; regular routes use route color
                if is_road:
                    clr = 220  # golden highlight for roads
                else:
                    clr = color
                route_layer[(px, py)] = (clr, dot_char)

    # Apply route dots onto the grid (skipping settlements)
    for (x, y), (clr, ch) in route_layer.items():
        if 0 <= y < h and 0 <= x < w and (x, y) not in settlement_map:
            grid_chars[y][x] = ch
            grid_colors[y][x] = clr

    # Render title + grid
    title_str = title or f"wyrd — Trade Routes (seed {world.seed})"
    lines: list[str] = [
        f"{ANSI_BOLD}{title_str}{ANSI_RESET}",
        f"{world.width}×{world.height} | {sum(1 for r in routes if getattr(r, 'is_active', True))} active routes\n",
    ]
    for y in range(h):
        lines.append("".join(
            f"{_color(grid_colors[y][x])}{grid_chars[y][x]}{ANSI_RESET}"
            for x in range(w)
        ))

    lines.append("")
    # Economy legend (only types present on the map)
    seen_types: set[str] = set()
    for r in routes:
        for name in (getattr(r, 'source', ''), getattr(r, 'destination', '')):
            if name in s_info:
                et = s_info[name][2]
                if et in _ROUTE_ECON_ICONS:
                    seen_types.add(et)
    if seen_types:
        lines.append(f"{ANSI_BOLD}Economy Types:{ANSI_RESET}")
        for etype in ["farming", "logging", "mining", "fishing", "trading", "pastoral"]:
            if etype in seen_types:
                lines.append(f"  {_color(_ROUTE_ECON_COLORS[etype])}{_ROUTE_ECON_ICONS[etype]}{ANSI_RESET}  {etype}")
        lines.append(f"  {_color(226)}·{ANSI_RESET}  Trade route path")
        lines.append(f"  {_color(220)}━{ANSI_RESET}  Road (persistent route, 50+ years)")
        lines.append("")

    # Route listings (top 10)
    active = [r for r in routes if getattr(r, 'is_active', True)]
    if active:
        lines.append(f"{ANSI_BOLD}Active Routes:{ANSI_RESET}")
        for r in active[:10]:
            src = getattr(r, 'source', '?')
            dst = getattr(r, 'destination', '?')
            st = s_info.get(src, ("?", "?", "?"))[2]
            dt = s_info.get(dst, ("?", "?", "?"))[2]
            si = _ROUTE_ECON_ICONS.get(st, "📦")
            di = _ROUTE_ECON_ICONS.get(dt, "📦")
            road_flag = " 🛤️" if getattr(r, 'is_road', False) else ""
            lines.append(
                f"  {si} {ANSI_BOLD}{src}{ANSI_RESET} ↔ {di} {ANSI_BOLD}{dst}{ANSI_RESET}{road_flag}"
            )
            lines.append(
                f"    {ANSI_DIM}{getattr(r, 'goods', 'goods')}  "
                f"(vol: {getattr(r, 'volume', 0.5):.0%}, "
                f"dist: {getattr(r, 'distance', 0):.0f}"
                f"{', road' if getattr(r, 'is_road', False) else ''}){ANSI_RESET}"
            )
        if len(active) > 10:
            lines.append(f"  {ANSI_DIM}… and {len(active) - 10} more{ANSI_RESET}")

    return "\n".join(lines)
