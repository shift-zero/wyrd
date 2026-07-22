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

        # Separator between religions
        if i < len(pantheon.religions) - 1:
            lines.append(f"  {ANSI_DIM}──{ANSI_RESET}\n")

    # Summary
    total_sites = pantheon.total_holy_sites
    total_deities = pantheon.total_deities
    lines.append(
        f"{ANSI_DIM}── {total_deities} deities across {len(pantheon.religions)} religion{'s' if len(pantheon.religions) != 1 else ''}"
        f" · {total_sites} holy sites ──{ANSI_RESET}"
    )

    return "\n".join(lines)
