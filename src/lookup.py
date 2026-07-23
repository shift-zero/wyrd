"""
wyrd — Lookup Engine (Phase 20: Living Gazetteer).

Quick cross-entity search: `wyrd lookup <name>` searches across all
data types and returns the best match.

Usage:
    wyrd lookup "Ebonheart" --seed 42
    wyrd lookup "Riverwood"
"""

import re
from difflib import SequenceMatcher as SM
from .world import World, ADVENTURE_ZONE_TYPES


def _score(query: str, name: str) -> float:
    """Score a match between query and name (0.0 - 1.0)."""
    q = query.lower().strip()
    n = name.lower().strip()

    # Exact match = 1.0
    if q == n:
        return 1.0

    # Name starts with query = high score
    if n.startswith(q):
        return 0.9

    # Query words found in name
    q_words = set(q.split())
    n_words = set(n.split())
    if q_words and n_words:
        overlap = q_words & n_words
        if overlap:
            return 0.7 + (0.2 * len(overlap) / len(q_words))

    # Sequence similarity
    ratio = SM(None, q, n).ratio()
    if ratio > 0.4:
        return ratio

    # Partial match (query is substring of name)
    if q in n:
        return 0.5

    return 0.0


def _badge(entity_type: str) -> str:
    badges = {
        "settlement": "S",
        "character": "C",
        "faction": "F",
        "creature": "B",
        "zone": "Z",
        "deity": "D",
        "region": "R",
    }
    return badges.get(entity_type, "?")


def lookup(world: World, query: str, max_results: int = 8) -> list[dict]:
    """Search all entity types for matching names. Returns scored results."""

    query = query.strip()
    if not query:
        return []

    results = []

    # 1. Settlements
    for region in world.regions:
        for s in region.settlements:
            score = _score(query, s.name)
            if score > 0.3:
                results.append({
                    "type": "settlement",
                    "name": s.name,
                    "score": score,
                    "detail": f"{s.kind.title()} in {region.name} — Pop {s.population:,}",
                })

    # 2. Regions
    for r in world.regions:
        score = _score(query, r.name)
        if score > 0.3:
            settlements = sum(1 for s in r.settlements)
            results.append({
                "type": "region",
                "name": r.name,
                "score": score,
                "detail": f"{r.biome.title()} region — {settlements} settlement(s)",
            })

    # 3. Characters
    if world.narrative and world.narrative.characters:
        for c in world.narrative.characters:
            for name_field in [c.full_name, c.name, c.surname]:
                score = _score(query, name_field)
                if score > 0.3:
                    results.append({
                        "type": "character",
                        "name": c.full_name,
                        "score": score,
                        "detail": f"{c.occupation.title()} from {c.home_settlement} — {c.status}",
                    })
                    break

    # 4. Factions
    if world.factions:
        for f in world.factions:
            score = _score(query, f.name)
            if score > 0.3:
                results.append({
                    "type": "faction",
                    "name": f.name,
                    "score": score,
                    "detail": f"{f.faction_type.replace('_', ' ').title()} — Power {f.power_score}",
                })

    # 5. Creatures
    if world.bestiary:
        for c in world.bestiary:
            score = _score(query, c.name)
            if score > 0.3:
                results.append({
                    "type": "creature",
                    "name": c.name,
                    "score": score,
                    "detail": f"Tier {c.tier} {c.creature_type.replace('_', ' ').title()} — {c.habitat}",
                })

    # 6. Adventure zones
    if world.adventure_zones:
        for z in world.adventure_zones:
            score = _score(query, z.name)
            if score > 0.3:
                zt = ADVENTURE_ZONE_TYPES.get(z.zone_type, {})
                results.append({
                    "type": "zone",
                    "name": z.name,
                    "score": score,
                    "detail": f"{z.zone_type.title()} in {z.region} — {zt.get('desc', '')}",
                })

    # 7. Deities
    if world.pantheon and world.pantheon.deities:
        for d in world.pantheon.deities:
            score = _score(query, d.name)
            if score > 0.3:
                results.append({
                    "type": "deity",
                    "name": d.name,
                    "score": score,
                    "detail": f"{d.title or 'Deity'} — {', '.join(d.domains) if hasattr(d, 'domains') and d.domains else ''}",
                })

    # Sort by score descending, then alphabetically
    results.sort(key=lambda r: (-r["score"], r["name"]))
    return results[:max_results]
