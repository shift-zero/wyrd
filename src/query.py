"""
wyrd — World Query Engine (Phase 3, Milestone 5).

Natural-language querying for generated worlds. Ask about regions,
settlements, features, or anything in the world. No LLM needed —
just smart pattern matching and structured data retrieval.

Usage:
    wyrd query --seed 42 "tell me about the northlands"
    wyrd query --seed 42 "what settlements are in Silverdale"
    wyrd query --seed 42 "find the rivers"
"""

import re
from .world import World, TERRAIN
from .render import ANSI_BOLD, ANSI_RESET, ANSI_DIM, ANSI_ITALIC, _color


# ── Query Patterns ───────────────────────────────────────────────────

PATTERNS = {
    "overview": {
        "patterns": [
            r"(?:overview|summary|describe|tell)\s+(?:me\s+)?(?:about\s+)?(?:this\s+)?(?:world|land)",
            r"what\s+(?:kind|type)\s+(?:of\s+)?(?:world|land)\s+(?:is\s+)?this",
            r"^overview$",
            r"^summary$",
        ],
    },
    "population_query": {
        "patterns": [
            r"(?:what|how many|total)\s+(?:is\s+)?(?:the\s+)?population",
            r"how\s+many\s+(?:people|souls|inhabitants)",
            r"population\s+(?:of\s+)?(.+)",
            r"largest\s+(?:settlement|town|city)",
        ],
    },
    "terrain_query": {
        "patterns": [
            r"(?:where|find|show|what)\s+(?:is\s+)?(?:the\s+)?(.*?)\s+(?:terrain|land|biome|area)s?",
            r"(?:how much|percentage|area)\s+(?:of\s+)?(?:the\s+)?(?:world|land)\s+is\s+(.+)",
            r"what\s+biomes?\s+(?:are\s+there|exist)",
        ],
    },
    "settlements_in_region": {
        "patterns": [
            r"(?:what|list|show)\s+(?:settlements?|towns?|cities?|villages?)\s+(?:are\s+)?(?:located\s+)?(?:in|of|at)\s+(.+)",
            r"settlements?\s+(?:are\s+)?(?:located\s+)?(?:in|of|at)\s+(.+)",
            r"towns?\s+(?:are\s+)?(?:located\s+)?(?:in|of|at)\s+(.+)",
        ],
    },
    "feature_search": {
        "patterns": [
            r"(?:what|find|show|list)\s+(?:are\s+)?(?:the\s+)?(.+)?\s+features?",
            r"(?:what|find|show|list)\s+(?:are\s+)?(?:the\s+)?(?:mountains?|rivers?|forests?|bays?|coasts?)",
            r"natural\s+features?",
            r"^(?:mountains?|rivers?|forests?|bays?|coasts?)$",
        ],
    },
    "relationship_search": {
        "patterns": [
            r"(?:what|show|list)\s+(?:are\s+)?(?:the\s+)?relationships?(?:\s+involving\s+(.+))?",
            r"(?:trade|rivalry|alliance|feud|war|peace|marriage|religious)\s+(?:between|involving|with)\s+(.+)?",
            r"who\s+(?:trades?|fights?|allies?|is\s+at\s+war)\s+(?:with\s+)?(.+)?",
        ],
    },
    "culture_search": {
        "patterns": [
            r"(?:what|tell|show)\s+(?:me\s+)?(?:about\s+)?(?:the\s+)?cultures?(?:\s+of\s+(.+))?",
            r"culture\s+(?:of|in)\s+(.+)",
            r"who\s+lives?\s+(?:in|at)\s+(.+)",
            r"people\s+(?:of|in)\s+(.+)",
        ],
    },
    "history_query": {
        "patterns": [
            r"(?:what|tell|show)\s+(?:is\s+)?(?:the\s+)?histor(?:y|ies)(?:\s+of\s+(.+))?",
            r"histor(?:y|ies)\s+(?:of|in)\s+(.+)",
            r"what\s+happened\s+(?:in|at)\s+(.+)",
            r"origin\s+(?:of|story)\s+(.+)",
        ],
    },
    "settlement_locate": {
        "patterns": [
            r"where\s+is\s+(.+)",
            r"find\s+(.+?)(?:\s+settlement)?",
            r"locate\s+(.+)",
        ],
    },
    "region_info": {
        "patterns": [
            r"(?:tell|describe|show|what|about)\s+(?:me\s+)?(?:about\s+)?(.+)",
            r"what(?:'s| is) in (.+)",
            r"describe (.+)",
            r"info(?:rmation)? (?:about|on) (.+)",
            r"region\s+(.+)",
        ],
    },
}


# ── Query Result ─────────────────────────────────────────────────────

class QueryResult:
    """A structured query result."""

    def __init__(self, title: str, lines: list[str], found: bool = True):
        self.title = title
        self.lines = lines
        self.found = found

    def render(self, color: bool = True) -> str:
        """Render the result as a formatted string."""
        if not self.found:
            return f"{ANSI_BOLD}Nothing found.{ANSI_RESET}" if color else "Nothing found."
        result = []
        if color:
            result.append(f"{ANSI_BOLD}═══ {self.title} ═══{ANSI_RESET}")
        else:
            result.append(f"=== {self.title} ===")
        result.append("")
        for line in self.lines:
            result.append(line)
        return "\n".join(result)


# ── Query Matching ───────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Normalize text for matching: lowercase, strip punctuation."""
    return re.sub(r'[^\w\s]', '', text).lower().strip()


def _find_region(world: World, name: str):
    """Find a region by its name (fuzzy)."""
    name_lower = _normalize(name)
    best = None
    best_score = 0
    for region in world.regions:
        rn = _normalize(region.name)
        # Exact match
        if rn == name_lower:
            return region
        # Substring match
        if name_lower in rn or rn in name_lower:
            score = len(name_lower) / max(len(rn), len(name_lower))
            if score > best_score:
                best_score = score
                best = region
        # Word match
        for word in name_lower.split():
            if word in rn:
                score = len(word) / len(rn)
                if score > best_score:
                    best_score = score
                    best = region
    return best if best_score > 0.3 else None


def _find_settlement(world: World, name: str):
    """Find a settlement by name (fuzzy)."""
    name_lower = _normalize(name)
    for region in world.regions:
        for s in region.settlements:
            sn = _normalize(s.name)
            if sn == name_lower or name_lower in sn or sn in name_lower:
                return s, region
    return None, None


def _find_feature(world: World, feature_type: str) -> list[dict]:
    """Find features by type keyword."""
    type_map = {
        "mountain": "mountain_range",
        "mountains": "mountain_range",
        "mountain_range": "mountain_range",
        "river": "river",
        "rivers": "river",
        "bay": "bay",
        "bays": "bay",
        "forest": "forest",
        "forests": "forest",
    }
    target = type_map.get(_normalize(feature_type))
    if not world.lore:
        return []
    if target:
        return [f for f in world.lore.features if f["type"] == target]
    return list(world.lore.features)


def _match_query_type(query: str) -> tuple[str, str | None]:
    """Determine query type and extract the target name.

    Returns (type, target) where target may be None.
    """
    query_lower = query.lower().strip()

    # Try each pattern category
    for qtype, config in PATTERNS.items():
        for pat in config["patterns"]:
            m = re.search(pat, query_lower)
            if m:
                target = m.group(1).strip() if m.lastindex and m.group(1) else None
                # Clean up filler words from target
                if target:
                    target = re.sub(r'\b(?:the|a|an|me|about|tell|show|of|in|at|for|its|their)\b', '', target).strip()
                    target = re.sub(r'\s+', ' ', target).strip()
                    if not target:
                        target = None
                return qtype, target

    # Default: try keyword search across all regions
    return "keyword", query


# ── Query Handlers ───────────────────────────────────────────────────

def _handle_overview(world: World, _target=None) -> QueryResult:
    """World overview / summary."""
    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    land = sum(1 for row in world.terrain for t in row
               if t not in ("deep_water", "shallow"))
    water = world.tiles - land

    # Terrain breakdown
    terrain_counts = {}
    for row in world.terrain:
        for t in row:
            terrain_counts[t] = terrain_counts.get(t, 0) + 1

    lines = []
    lines.append(f"  Seed: {world.seed}")
    lines.append(f"  Size: {world.width}×{world.height} ({world.tiles:,} tiles)")
    lines.append(f"  Land: {land:,} tiles ({land / world.tiles * 100:.0f}%)")
    lines.append(f"  Water: {water:,} tiles ({water / world.tiles * 100:.0f}%)")
    lines.append(f"  Regions: {len(world.regions)}")
    lines.append(f"  Settlements: {sum(len(r.settlements) for r in world.regions)}")
    lines.append(f"  Population: {total_pop:,} souls")
    lines.append("")

    # Terrain breakdown
    lines.append(f"{ANSI_BOLD}Terrain:{ANSI_RESET}" if True else "Terrain:")
    for t_key in ["deep_water", "shallow", "sand", "grass", "forest", "hills", "mountains", "snow", "river"]:
        count = terrain_counts.get(t_key, 0)
        if count > 0:
            pct = count / world.tiles * 100
            desc = TERRAIN.get(t_key, {}).get("desc", t_key)
            char = TERRAIN.get(t_key, {}).get("char", "?")
            color = TERRAIN.get(t_key, {}).get("color", 255)
            lines.append(f"  {_color(color)}{char}{ANSI_RESET}  {desc}: {count:,} ({pct:.0f}%)")

    # Regions summary
    lines.append("")
    lines.append(f"{ANSI_BOLD}Regions:{ANSI_RESET}" if True else "Regions:")
    for region in world.regions:
        pop = sum(s.population for s in region.settlements)
        lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET} ({region.biome}) — "
                      f"{len(region.settlements)} settlements, {pop:,} souls")

    return QueryResult(f"wyrd #{world.seed} — Overview", lines)


def _handle_region_info(world: World, target: str | None) -> QueryResult:
    """Detailed info about a specific region."""
    if not target:
        # List all regions
        lines = []
        for i, region in enumerate(world.regions):
            pop = sum(s.population for s in region.settlements)
            settle_list = ", ".join(f"{s.name} ({s.kind})" for s in region.settlements)
            lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}  ({region.biome})")
            lines.append(f"    Settlements: {settle_list}")
            lines.append(f"    Population: {pop:,}")
            if world.lore and region.name in world.lore.cultures:
                lines.append(f"    Culture: {world.lore.cultures[region.name]}")
            if world.lore and region.name in world.lore.histories:
                lines.append(f"    History: {world.lore.histories[region.name]}")
            if i < len(world.regions) - 1:
                lines.append("")
        return QueryResult(f"wyrd #{world.seed} — All Regions", lines)

    region = _find_region(world, target)
    if not region:
        # Try finding by keyword instead
        matching = [r for r in world.regions if _normalize(target) in _normalize(r.name)]
        if matching:
            region = matching[0]
        else:
            return QueryResult("", [f"No region found matching '{target}'."], found=False)

    lines = []
    pop = sum(s.population for s in region.settlements)
    lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}  ({region.biome})")
    lines.append(f"  Settlements: {len(region.settlements)} | Population: {pop:,}")

    if world.lore:
        if region.name in world.lore.cultures:
            lines.append(f"  Culture: {ANSI_ITALIC}{world.lore.cultures[region.name]}{ANSI_RESET}")
        if region.name in world.lore.culture_descriptions:
            for desc in world.lore.culture_descriptions[region.name]:
                lines.append(f"    {ANSI_DIM}{desc}{ANSI_RESET}")
        if region.name in world.lore.histories:
            lines.append(f"  History: {world.lore.histories[region.name]}")
        if region.name in world.lore.region_descriptions:
            lines.append(f"  {ANSI_DIM}{world.lore.region_descriptions[region.name]}{ANSI_RESET}")

    lines.append("")
    lines.append(f"{ANSI_BOLD}Settlements:{ANSI_RESET}")
    for s in region.settlements:
        lines.append(f"  {s.char} {ANSI_BOLD}{s.name}{ANSI_RESET} ({s.kind}, pop {s.population:,})")

    # Features in this region
    if world.lore:
        region_features = [f for f in world.lore.features if f.get("region") == region.name]
        if region_features:
            lines.append("")
            lines.append(f"{ANSI_BOLD}Geographical Features:{ANSI_RESET}")
            for feat in region_features:
                lines.append(f"  {feat['name']} — {feat['desc']}")

    return QueryResult(f"{region.name}", lines)


def _handle_settlement_locate(world: World, target: str | None) -> QueryResult:
    """Find information about a settlement."""
    if not target:
        return QueryResult("", ["Which settlement? Try 'where is Fairhaven' or 'find Goldcrest'."], found=False)

    s, region = _find_settlement(world, target)
    if not s:
        return QueryResult("", [f"No settlement found matching '{target}'."], found=False)

    t = world.terrain[s.y][s.x]
    terrain_desc = TERRAIN.get(t, {}).get("desc", t)

    lines = []
    lines.append(f"  {ANSI_BOLD}{s.name}{ANSI_RESET}  ({s.kind}, pop {s.population:,})")
    lines.append(f"  Location: ({s.x}, {s.y}) in {ANSI_BOLD}{region.name}{ANSI_RESET} ({region.biome})")
    lines.append(f"  Terrain: {terrain_desc}")
    lines.append(f"  Elevation: {world.elevation[s.y][s.x]:.3f}")
    lines.append(f"  Moisture: {world.moisture[s.y][s.x]:.3f}")

    # Relationships involving this settlement
    if world.lore:
        s_rels = [
            r for r in world.lore.relationships
            if r["source"] == s.name or r["target"] == s.name
        ]
        if s_rels:
            lines.append(f"  {ANSI_BOLD}Relationships:{ANSI_RESET}")
            for rel in s_rels[:5]:
                lines.append(f"    {rel['description']}")

    return QueryResult(s.name, lines)


def _handle_feature_search(world: World, target: str | None) -> QueryResult:
    """Find geographical features."""
    if not world.lore or not world.lore.features:
        return QueryResult("", ["No features found in this world."], found=False)

    if target:
        features = _find_feature(world, target)
    else:
        features = list(world.lore.features)

    if not features:
        return QueryResult("", [f"No features of type '{target}' found."], found=False)

    lines = []
    grouped = {}
    for feat in features:
        ftype = feat["type"]
        if ftype not in grouped:
            grouped[ftype] = []
        grouped[ftype].append(feat)

    for ftype, feat_list in grouped.items():
        icon_map = {"mountain_range": "▲", "river": "≈", "bay": "~", "forest": "*"}
        icon = icon_map.get(ftype, "·")
        color_map = {"mountain_range": 130, "river": 45, "bay": 33, "forest": 22}
        fcolor = color_map.get(ftype, 255)
        lines.append(f"  {_color(fcolor)}{icon}{ANSI_RESET}  {ftype.replace('_', ' ').title()}s — {len(feat_list)}")
        for feat in feat_list:
            lines.append(f"    {ANSI_BOLD}{feat['name']}{ANSI_RESET} — {feat['desc']}")

    return QueryResult(f"Features ({len(features)} total)", lines)


def _handle_settlements_in_region(world: World, target: str | None) -> QueryResult:
    """List settlements in a region."""
    if not target:
        return QueryResult("", ["Which region? Try 'what settlements are in Greendale'."], found=False)

    region = _find_region(world, target)
    if not region:
        return QueryResult("", [f"No region found matching '{target}'."], found=False)

    total_pop = sum(s.population for s in region.settlements)
    lines = []
    for s in region.settlements:
        lines.append(
            f"  {s.char} {ANSI_BOLD}{s.name}{ANSI_RESET}  ({s.kind}, pop {s.population:,})  "
            f"({s.x}, {s.y})"
        )
    lines.append("")
    lines.append(f"  Total: {len(region.settlements)} settlements, {total_pop:,} souls")

    return QueryResult(f"Settlements of {region.name}", lines)


def _handle_relationship_search(world: World, target: str | None) -> QueryResult:
    """Find relationships involving a settlement or all relationships."""
    if not world.lore or not world.lore.relationships:
        return QueryResult("", ["No relationships defined for this world."], found=False)

    lines = []
    if target:
        s, region = _find_settlement(world, target)
        if s:
            rels = [
                r for r in world.lore.relationships
                if r["source"] == s.name or r["target"] == s.name
            ]
            if not rels:
                return QueryResult("", [f"No relationships found involving '{s.name}'."], found=False)
            for rel in rels:
                lines.append(f"  {rel['description']}")
            return QueryResult(f"Relationships involving {s.name}", lines)
        else:
            return QueryResult("", [f"No settlement found matching '{target}'."], found=False)

    # Show all relationships by type
    by_type = {}
    for rel in world.lore.relationships:
        rt = rel["type"]
        if rt not in by_type:
            by_type[rt] = []
        by_type[rt].append(rel)

    for rtype, rels in by_type.items():
        icon_map = {"trade": "⇄", "rivalry": "⚔", "alliance": "⚝", "feud": "✗",
                     "vassalage": "→", "marriage_tie": "♡", "religious": "†", "cultural": "♫"}
        color_map = {"trade": 28, "rivalry": 196, "alliance": 33, "feud": 160,
                      "vassalage": 130, "marriage_tie": 205, "religious": 99, "cultural": 213}
        icon = icon_map.get(rtype, "·")
        color = color_map.get(rtype, 255)
        lines.append(f"  {_color(color)}{icon}{ANSI_RESET}  {rtype.title()} — {len(rels)}")
        for rel in rels[:4]:
            lines.append(f"    {rel['description']}")
        if len(rels) > 4:
            lines.append(f"    ... and {len(rels) - 4} more")
        lines.append("")

    return QueryResult(f"Relationships ({len(world.lore.relationships)} total)", lines)


def _handle_culture_search(world: World, target: str | None) -> QueryResult:
    """Find culture information."""
    if not world.lore or not world.lore.cultures:
        return QueryResult("", ["No culture data for this world."], found=False)

    lines = []
    if target:
        region = _find_region(world, target)
        if region and region.name in world.lore.cultures:
            lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}")
            lines.append(f"  Culture: {world.lore.cultures[region.name]}")
            if region.name in world.lore.culture_descriptions:
                for desc in world.lore.culture_descriptions[region.name]:
                    lines.append(f"    {desc}")
            return QueryResult(f"Culture of {region.name}", lines)
        return QueryResult("", [f"No culture data found for '{target}'."], found=False)

    # List all cultures
    for region in world.regions:
        if region.name in world.lore.cultures:
            lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}")
            lines.append(f"    Culture: {world.lore.cultures[region.name]}")
    return QueryResult(f"Cultures of wyrd #{world.seed}", lines)


def _handle_history_query(world: World, target: str | None) -> QueryResult:
    """Find history information."""
    if not world.lore or not world.lore.histories:
        return QueryResult("", ["No history recorded for this world."], found=False)

    lines = []
    if target:
        region = _find_region(world, target)
        if region and region.name in world.lore.histories:
            lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}")
            lines.append(f"  {world.lore.histories[region.name]}")
            return QueryResult(f"History of {region.name}", lines)
        return QueryResult("", [f"No history found for '{target}'."], found=False)

    for region in world.regions:
        if region.name in world.lore.histories:
            lines.append(f"  {ANSI_BOLD}{region.name}{ANSI_RESET}")
            lines.append(f"    {world.lore.histories[region.name]}")
    return QueryResult(f"Histories of wyrd #{world.seed}", lines)


def _handle_terrain_query(world: World, target: str | None) -> QueryResult:
    """Query terrain/biome info."""
    lines = []

    if target and any(w in _normalize(target) for w in ["biome", "biomes"]):
        # List biomes
        biome_counts = {}
        for region in world.regions:
            biome_counts[region.biome] = biome_counts.get(region.biome, 0) + 1
        lines.append(f"  Biomes in this world:")
        biome_colors = {"temperate": 28, "arid": 172, "tundra": 250, "tropical": 35}
        for biome, count in sorted(biome_counts.items()):
            color = biome_colors.get(biome, 255)
            lines.append(f"    {_color(color)}■{ANSI_RESET}  {biome.title()}: {count} region{'s' if count > 1 else ''}")
        return QueryResult(f"Biomes of wyrd #{world.seed}", lines)

    # Terrain distribution
    terrain_counts = {}
    for row in world.terrain:
        for t in row:
            terrain_counts[t] = terrain_counts.get(t, 0) + 1

    lines.append(f"  Terrain distribution:")
    for t_key in ["deep_water", "shallow", "sand", "grass", "forest", "hills", "mountains", "snow", "river"]:
        count = terrain_counts.get(t_key, 0)
        if count > 0:
            pct = count / world.tiles * 100
            desc = TERRAIN.get(t_key, {}).get("desc", t_key)
            char = TERRAIN.get(t_key, {}).get("char", "?")
            color = TERRAIN.get(t_key, {}).get("color", 255)
            bar_len = int(pct / 2)
            bar = "█" * bar_len
            lines.append(f"  {_color(color)}{char}{ANSI_RESET}  {desc}: {pct:5.1f}%  {bar}")

    return QueryResult(f"Terrain of wyrd #{world.seed}", lines)


def _handle_population_query(world: World, target: str | None) -> QueryResult:
    """Population statistics."""
    total_pop = sum(s.population for r in world.regions for s in r.settlements)
    all_settlements = sorted(
        [(s, r) for r in world.regions for s in r.settlements],
        key=lambda x: -x[0].population,
    )

    lines = []
    lines.append(f"  Total population: {total_pop:,} souls")
    lines.append(f"  Number of settlements: {len(all_settlements)}")
    lines.append("")

    if all_settlements:
        lines.append(f"  {ANSI_BOLD}Largest settlements:{ANSI_RESET}")
        for s, region in all_settlements[:5]:
            lines.append(f"    {ANSI_BOLD}{s.name}{ANSI_RESET} ({s.kind}) — {s.population:,} in {region.name}")
        lines.append("")
        lines.append(f"  {ANSI_BOLD}Smallest settlements:{ANSI_RESET}")
        for s, region in all_settlements[-3:]:
            lines.append(f"    {ANSI_BOLD}{s.name}{ANSI_RESET} ({s.kind}) — {s.population:,} in {region.name}")

    return QueryResult(f"Population of wyrd #{world.seed}", lines)


def _handle_keyword(world: World, query: str) -> QueryResult:
    """Fallback: keyword search across all world text."""
    query_lower = _normalize(query)
    if not query_lower:
        return QueryResult("", ["Please provide a query."], found=False)

    hits = []

    # Search region names
    for region in world.regions:
        if query_lower in _normalize(region.name):
            hits.append(("Region", region.name, f"{region.name} ({region.biome})"))

    # Search settlement names
    for region in world.regions:
        for s in region.settlements:
            if query_lower in _normalize(s.name):
                hits.append(("Settlement", s.name, f"{s.name} ({s.kind}) in {region.name}"))

    # Search lore data
    if world.lore:
        for rname, culture in world.lore.cultures.items():
            if query_lower in _normalize(culture):
                hits.append(("Culture", culture, f"{culture} — culture of {rname}"))
        for feat in world.lore.features:
            if query_lower in _normalize(feat["name"]):
                hits.append(("Feature", feat["name"], f"{feat['name']} ({feat['type']})"))
        for rname, history in world.lore.histories.items():
            if query_lower in _normalize(history):
                hits.append(("History", rname, f"History of {rname}"))
        for rel in world.lore.relationships:
            if query_lower in _normalize(rel["description"]):
                # Truncate long descriptions
                desc = rel["description"][:80] + ("..." if len(rel["description"]) > 80 else "")
                hits.append(("Relationship", desc, f"{desc}"))

    if not hits:
        return QueryResult("", [f"Nothing found matching '{query}'."], found=False)

    lines = []
    grouped = {}
    for category, name, desc in hits:
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(desc)

    for category, items in grouped.items():
        lines.append(f"  {ANSI_BOLD}{category}s:{ANSI_RESET}" if True else f"  {category}s:")
        for item in items[:8]:
            lines.append(f"    • {item}")
        if len(items) > 8:
            lines.append(f"    ... and {len(items) - 8} more")

    return QueryResult(f"Search results for '{query}'", lines)


# ── Main Query Dispatcher ────────────────────────────────────────────

def query_world(world: World, query: str) -> QueryResult:
    """Process a natural-language query against a world.

    Args:
        world: A generated World object.
        query: Natural-language query string.

    Returns:
        A QueryResult with formatted output.
    """
    if not query or not query.strip():
        return _handle_overview(world)

    qtype, target = _match_query_type(query)

    handlers = {
        "overview": _handle_overview,
        "region_info": _handle_region_info,
        "settlement_locate": _handle_settlement_locate,
        "feature_search": _handle_feature_search,
        "settlements_in_region": _handle_settlements_in_region,
        "relationship_search": _handle_relationship_search,
        "culture_search": _handle_culture_search,
        "history_query": _handle_history_query,
        "terrain_query": _handle_terrain_query,
        "population_query": _handle_population_query,
    }

    handler = handlers.get(qtype)
    if handler:
        return handler(world, target)

    return _handle_keyword(world, query)
