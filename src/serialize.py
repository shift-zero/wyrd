"""
wyrd — World serialization (Phase 3: Save/Load).

Save and load worlds as JSON. Seed-deterministic: the seed is always
the canonical representation; JSON serves as cache / interchange format.
"""

import json
import os
import gzip
from typing import Optional
from .world import World, Region, Settlement, TERRAIN, BIOMES
from .lore import Lore
from .narrative import Narrative, Character, EventChain, Quest
from .chronicles import Chronicles, Era
from .magic import MagicSystem, MagicSchool, MagicTradition


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

    # Narrative
    if world.narrative:
        narr = world.narrative
        data["narrative"] = {
            "seed": narr.seed,
            "current_year": narr.current_year,
            "characters": [
                {
                    "name": c.name,
                    "surname": c.surname,
                    "age": c.age,
                    "gender": c.gender,
                    "occupation": c.occupation,
                    "personality_traits": c.personality_traits,
                    "home_region": c.home_region,
                    "home_settlement": c.home_settlement,
                    "backstory": c.backstory,
                    "status": c.status,
                }
                for c in narr.characters
            ],
            "events": [
                {
                    "name": e.name,
                    "year": e.year,
                    "event_type": e.event_type,
                    "description": e.description,
                    "regions_involved": e.regions_involved,
                    "settlements_involved": e.settlements_involved,
                    "characters_involved": e.characters_involved,
                    "consequences": e.consequences,
                }
                for e in narr.events
            ],
            "quests": [
                {
                    "name": q.name,
                    "quest_type": q.quest_type,
                    "difficulty": q.difficulty,
                    "description": q.description,
                    "giver_character": q.giver_character,
                    "giver_settlement": q.giver_settlement,
                    "target_region": q.target_region,
                    "rewards": q.rewards,
                    "is_active": q.is_active,
                }
                for q in narr.quests
            ],
        }

    # Chronicles
    if world.chronicles:
        chron = world.chronicles
        data["chronicles"] = {
            "seed": chron.seed,
            "world_age": chron.world_age,
            "eras": [
                {
                    "name": era.name,
                    "era_type": era.era_type,
                    "start_year": era.start_year,
                    "end_year": era.end_year,
                    "description": era.description,
                    "events": era.events,
                    "world_modifiers": era.world_modifiers,
                    "is_present": era.is_present,
                }
                for era in chron.eras
            ],
        }

    # Magic System
    if world.magic:
        magic = world.magic
        data["magic"] = {
            "name": magic.name,
            "source": magic.source,
            "description": magic.description,
            "practitioners": magic.practitioners,
            "schools": [
                {
                    "name": s.name,
                    "description": s.description,
                    "spell_examples": s.spell_examples,
                    "alignment": s.alignment,
                }
                for s in magic.schools
            ],
            "traditions": [
                {
                    "name": t.name,
                    "description": t.description,
                    "origin": t.origin,
                    "region": t.region,
                    "practitioners": t.practitioners,
                }
                for t in magic.traditions
            ],
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

    # Deserialize narrative
    narrative_data = data.get("narrative")
    if narrative_data:
        narr = Narrative(seed=narrative_data["seed"])
        narr.current_year = narrative_data.get("current_year", 1000)
        narr.characters = [
            Character(
                name=cd["name"],
                surname=cd.get("surname", ""),
                age=cd.get("age", 0),
                gender=cd.get("gender", "unknown"),
                occupation=cd.get("occupation", "commoner"),
                personality_traits=cd.get("personality_traits", []),
                home_region=cd["home_region"],
                home_settlement=cd["home_settlement"],
                backstory=cd.get("backstory", ""),
                status=cd.get("status", "alive"),
            )
            for cd in narrative_data.get("characters", [])
        ]
        narr.events = [
            EventChain(
                name=ed["name"],
                year=ed.get("year", 0),
                event_type=ed.get("event_type", "unknown"),
                description=ed.get("description", ""),
                regions_involved=ed.get("regions_involved", []),
                settlements_involved=ed.get("settlements_involved", []),
                characters_involved=ed.get("characters_involved", []),
                consequences=ed.get("consequences", []),
            )
            for ed in narrative_data.get("events", [])
        ]
        narr.quests = [
            Quest(
                name=qd["name"],
                quest_type=qd.get("quest_type", "exploration"),
                difficulty=qd.get("difficulty", "moderate"),
                description=qd.get("description", ""),
                giver_character=qd.get("giver_character"),
                giver_settlement=qd.get("giver_settlement", ""),
                target_region=qd.get("target_region", "unknown"),
                rewards=qd.get("rewards", []),
                is_active=qd.get("is_active", True),
            )
            for qd in narrative_data.get("quests", [])
        ]
        world.narrative = narr

    # Deserialize chronicles
    chronicles_data = data.get("chronicles")
    if chronicles_data:
        chronicles = Chronicles(seed=chronicles_data["seed"])
        chronicles.world_age = chronicles_data.get("world_age", 1000)
        chronicles.eras = []
        for ed in chronicles_data.get("eras", []):
            era = Era(
                name=ed["name"],
                era_type=ed.get("era_type", "age_of"),
                start_year=ed.get("start_year", 0),
                end_year=ed.get("end_year", 100),
                description=ed.get("description", ""),
                events=ed.get("events", []),
                world_modifiers=ed.get("world_modifiers", []),
                is_present=ed.get("is_present", False),
            )
            chronicles.eras.append(era)
        world.chronicles = chronicles

    # Deserialize magic system
    magic_data = data.get("magic")
    if magic_data:
        magic = MagicSystem(
            name=magic_data["name"],
            source=magic_data.get("source", "arcane"),
            description=magic_data.get("description", ""),
            practitioners=magic_data.get("practitioners", ""),
            schools=[
                MagicSchool(
                    name=sd["name"],
                    description=sd.get("description", ""),
                    spell_examples=sd.get("spell_examples", []),
                    alignment=sd.get("alignment", "neutral"),
                )
                for sd in magic_data.get("schools", [])
            ],
            traditions=[
                MagicTradition(
                    name=td["name"],
                    description=td.get("description", ""),
                    origin=td.get("origin", "ancient"),
                    region=td.get("region", ""),
                    practitioners=td.get("practitioners", ""),
                )
                for td in magic_data.get("traditions", [])
            ],
        )
        world.magic = magic

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


# ── Simulation Serialization ──────────────────────────────────────────


def sim_state_to_dict(state: 'SimState') -> dict:
    """Serialize a SimState to a JSON-compatible dict."""
    from .sim import SimState, SettlementSnapshot, SimEvent
    return {
        "year": state.year,
        "settlements": {
            name: {
                "name": s.name,
                "region": s.region,
                "x": s.x,
                "y": s.y,
                "population": s.population,
                "kind": s.kind,
                "is_active": s.is_active,
                "founded_year": s.founded_year,
                "prosperity": s.prosperity,
                "food_stores": s.food_stores,
                "health": s.health,
            }
            for name, s in state.settlements.items()
        },
        "events": [
            {
                "year": e.year,
                "event_type": e.event_type,
                "description": e.description,
                "affected_settlements": e.affected_settlements,
                "affected_regions": e.affected_regions,
            }
            for e in state.events
        ],
        "world_modifiers": state.world_modifiers,
        "population_record": state.population_record,
    }


def save_sim_state(result, path: str, compact: bool = False) -> str:
    """Save a SimResult (or SimState) to JSON. Use compact=True for gzip compression."""
    from .sim import SimResult
    if isinstance(result, SimResult):
        # Save the snapshots dict for per-year loading
        snapshots_dict = {}
        for snap in result.snapshots:
            snapshots_dict[snap.year] = sim_state_to_dict(snap)
        
        data = {
            "wyrd_sim_version": "0.1.0",
            "seed": result.seed,
            "num_years": result.num_years,
            "summary": result.summary,
            "events": [
                {
                    "year": e.year,
                    "event_type": e.event_type,
                    "description": e.description,
                    "affected_settlements": e.affected_settlements,
                    "affected_regions": e.affected_regions,
                }
                for e in result.events
            ],
            "initial_state": sim_state_to_dict(result.initial_state),
            "final_state": sim_state_to_dict(result.final_state),
            "snapshots": snapshots_dict,
            "population_record": result.final_state.population_record,
        }
    else:
        data = sim_state_to_dict(result)
    
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json_str = json.dumps(data, indent=2 if not compact else None, ensure_ascii=False)
    if path.endswith('.gz') or compact:
        with gzip.open(path if path.endswith('.gz') else path + ".gz", "wt", encoding="utf-8") as f:
            f.write(json_str)
        return path if path.endswith('.gz') else path + ".gz"
    with open(path, "w") as f:
        f.write(json_str)
    return path


def load_sim_state(path: str) -> Optional[dict]:
    """Load simulation state/metadata from JSON (supports gzip)."""
    try:
        if path.endswith('.gz'):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                return json.load(f)
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
