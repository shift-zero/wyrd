"""
wyrd — World serialization (Phase 3: Save/Load).

Save and load worlds as JSON. Seed-deterministic: the seed is always
the canonical representation; JSON serves as cache / interchange format.
"""

import json
import os
from typing import Optional
from .world import World, Region, Settlement, TERRAIN, BIOMES
from .lore import Lore


class WyrdEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles tuples as lists."""

    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)


def world_to_dict(world: World) -> dict:
    """Serialize a World to a JSON-compatible dict."""
    data = {
        "wyrd_version": "0.1.0",
        "seed": world.seed,
        "width": world.width,
        "height": world.height,
        "elevation": world.elevation,
        "moisture": world.moisture,
        "terrain": world.terrain,
        "rivers": world.rivers,
        "regions": [],
    }

    for region in world.regions:
        region_data = {
            "name": region.name,
            "biome": region.biome,
            "settlements": [
                {
                    "name": s.name,
                    "x": s.x,
                    "y": s.y,
                    "population": s.population,
                    "kind": s.kind,
                }
                for s in region.settlements
            ],
        }
        data["regions"].append(region_data)

    # Lore
    if world.lore:
        lore = world.lore
        data["lore"] = {
            "seed": lore.seed,
            "region_descriptions": lore.region_descriptions,
            "cultures": lore.cultures,
            "culture_descriptions": lore.culture_descriptions,
            "features": lore.features,
            "histories": lore.histories,
            "relationships": lore.relationships,
        }

    return data


def dict_to_world(data: dict) -> World:
    """Deserialize a dict back into a World."""
    world = World(
        seed=data["seed"],
        width=data["width"],
        height=data["height"],
        elevation=data["elevation"],
        moisture=data.get("moisture", []),
        terrain=data["terrain"],
        rivers=[tuple(r) if isinstance(r, list) else r for r in data.get("rivers", [])],
    )

    world.regions = []
    for rd in data.get("regions", []):
        region = Region(name=rd["name"], biome=rd.get("biome", "temperate"))
        region.settlements = [
            Settlement(
                name=s["name"],
                x=s["x"],
                y=s["y"],
                population=s["population"],
                kind=s.get("kind", "hamlet"),
            )
            for s in rd.get("settlements", [])
        ]
        world.regions.append(region)

    # Deserialize lore
    lore_data = data.get("lore")
    if lore_data:
        lore = Lore(seed=lore_data["seed"])
        lore.region_descriptions = lore_data.get("region_descriptions", {})
        lore.cultures = lore_data.get("cultures", {})
        lore.culture_descriptions = lore_data.get("culture_descriptions", {})
        lore.features = lore_data.get("features", [])
        lore.histories = lore_data.get("histories", {})
        lore.relationships = lore_data.get("relationships", [])
        world.lore = lore

    return world


def save_world(world: World, path: str) -> str:
    """Save a world to a JSON file. Returns the path."""
    data = world_to_dict(world)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, cls=WyrdEncoder)
    return path


def load_world(path: str) -> World:
    """Load a world from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return dict_to_world(data)
