"""
wyrd — Political Simulation (Phase 12).

Faction dynamics during year-by-year simulation.
Factions rise/fall in power, wage war, form alliances,
and affect the prosperity of settlements in their territories.

Integrates with sim.py via _simulate_political_tick().
"""

import random
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World
    from .sim import SimState, SimEvent


# ── Faction Simulation State ────────────────────────────────────────

@dataclass
class FactionSnapshot:
    """Simulation-tracked state for a faction."""
    name: str
    faction_type: str
    influence: int = 50      # 0-100
    wealth: int = 50         # 0-100
    military: int = 50       # 0-100
    stability: int = 50      # 0-100
    reputation: str = "neutral"
    is_active: bool = True
    at_war_with: list[str] = field(default_factory=list)
    years_of_peace: int = 0
    war_exhaustion: int = 0  # ticks up during war, decays in peace; affects settlement food
    territory_regions: list[str] = field(default_factory=list)

    @property
    def power_score(self) -> int:
        """Overall power rating combining all stats."""
        return self.influence + self.wealth + self.military + self.stability

    @property
    def power_label(self) -> str:
        """Human-readable power tier."""
        ps = self.power_score
        if ps >= 320:
            return "dominant"
        elif ps >= 240:
            return "major"
        elif ps >= 160:
            return "moderate"
        elif ps >= 80:
            return "minor"
        return "fading"


# ── Political Event Templates ────────────────────────────────────────

POLITICAL_EVENT_TEMPLATES = {
    "faction_war": (
        "War erupts between {faction_a} and {faction_b}! "
        "The {faction_a_type} clashes with the {faction_b_type} over {cause}. "
        "{effect}"
    ),
    "faction_alliance": (
        "{faction_a} and {faction_b} form a {strength} alliance. "
        "{detail}"
    ),
    "faction_power_shift": (
        "{faction} experiences a dramatic shift in power. "
        "{cause} {effect}"
    ),
    "faction_collapse": (
        "{faction} collapses! {cause} "
        "{effect}"
    ),
    "faction_leadership_change": (
        "Leadership of {faction} passes to a new era. "
        "{detail}"
    ),
    "faction_trade_pact": (
        "A trade pact between {faction_a} and {faction_b} "
        "brings prosperity to {region}. {effect}"
    ),
    "faction_vassal_revolt": (
        "{faction_a} rebels against {faction_b}! "
        "Years of {cause} have pushed them to open defiance. "
        "{effect}"
    ),
    "faction_coup": (
        "A coup rocks {faction}! {detail} "
        "{effect}"
    ),
    "faction_peace_treaty": (
        "{faction_a} and {faction_b} sign a formal peace treaty. "
        "{terms} {effect}"
    ),
}

# ── Political Event Causes ───────────────────────────────────────────

WAR_CAUSES = [
    "disputed border territories",
    "an ancient grudge brought to a boil",
    "competition for scarce resources",
    "a diplomatic insult that demands satisfaction",
    "religious differences that cannot be reconciled",
    "a succession crisis that draws in neighbours",
    "broken trade agreements and stolen caravans",
    "a assassination that fingers the rival faction",
]

ALLIANCE_REASONS = [
    "a shared enemy threatens them both",
    "marriage binds their noble houses",
    "mutual economic benefit drives cooperation",
    "a religious bond unites their followers",
    "a natural disaster forces neighbourly aid",
    "a charismatic leader bridges their differences",
]

POWER_SHIFT_CAUSES = [
    "A rich vein of ore is discovered in their territory.",
    "A devastating plague sweeps through their lands.",
    "Their patron deity appears to abandon them.",
    "New trade routes bring unprecedented wealth.",
    "A generation of wise leadership transforms the faction.",
    "A catastrophic military defeat leaves them reeling.",
    "Internal corruption saps their strength from within.",
]

COLLAPSE_CAUSES = [
    "Internal strife tears the faction apart.",
    "A series of military defeats leaves them defenceless.",
    "Economic ruin follows a decade of poor harvests.",
    "The death of their leader triggers a succession war.",
    "A natural disaster destroys their seat of power.",
    "Their vassals revolt and the faction fragments.",
]

COUP_DETAILS = [
    "A charismatic general seizes control in a bloodless takeover.",
    "A secret society within the faction overthrows the leadership.",
    "The merchant class, tired of war taxes, installs a new council.",
    "A religious figure declares themselves the rightful ruler.",
    "The old leader is found dead and a new power fills the void.",
]

PEACE_EFFECTS = [
    "Trade flourishes between their territories.",
    "Cultural exchange enriches both societies.",
    "The borderlands grow prosperous and peaceful.",
    "A golden age of cooperation begins.",
    "Farmers return to fields once scarred by war.",
]

PEACE_TREATY_TERMS = [
    "Both sides agree to a demilitarised border zone.",
    "War reparations are paid in gold and grain over five years.",
    "The treaty cedes disputed border territories to the victor.",
    "A mutual non-aggression pact is signed for a generation.",
    "Prisoners are exchanged and trade routes reopen.",
    "The treaty is sealed with a marriage between noble houses.",
    "Both sides pledge to submit future disputes to neutral arbitration.",
]

WAR_EFFECTS = [
    "Fields are burned and villages raided.",
    "The borderlands become a wasteland.",
    "Thousands flee the conflict zone.",
    "Fortresses are besieged and fall one by one.",
    "Mercenaries grow rich on the blood of both sides.",
    "The war drains both treasuries to the brink.",
]


# ── Political Tick ──────────────────────────────────────────────────

def initialize_faction_state(world: 'World') -> dict[str, FactionSnapshot]:
    """Initialize faction simulation state from a world's faction data."""
    faction_state: dict[str, FactionSnapshot] = {}
    for f in world.factions:
        faction_state[f.name] = FactionSnapshot(
            name=f.name,
            faction_type=f.faction_type,
            influence=f.influence,
            wealth=f.wealth,
            military=f.military,
            stability=f.stability,
            reputation=f.reputation,
            is_active=True,
            territory_regions=list(f.territory),
        )
    return faction_state


def _find_region_settlements(state: 'SimState', region_names: list[str]) -> list[str]:
    """Find settlement names belonging to given regions."""
    result = []
    for s_name, s in state.settlements.items():
        if s.is_active and s.region in region_names:
            result.append(s_name)
    return result


def _faction_war_chance(fs_a: FactionSnapshot, fs_b: FactionSnapshot,
                        world: 'World', rng: random.Random) -> bool:
    """Determine if two factions should go to war this tick."""
    # Check if they have a rivalry/hostility relationship
    if not hasattr(world, 'faction_relationships'):
        return False
    for rel in world.faction_relationships:
        names = {rel.faction_a, rel.faction_b}
        if {fs_a.name, fs_b.name} == names:
            if rel.rel_type in ("rivalry", "hostility"):
                # Hostile factions are more likely to war
                base_chance = 0.04 if rel.rel_type == "hostility" else 0.015
                # If they've been at peace a long time, tension builds
                peace_bonus = min(fs_a.years_of_peace, fs_b.years_of_peace) * 0.002
                return rng.random() < base_chance + peace_bonus
    return False


def _simulate_political_tick(world: 'World', state: 'SimState',
                              rng: random.Random, year: int,
                              chaos_factor: float = 0.1) -> list['SimEvent']:
    """
    Simulate one year of faction politics.
    
    Called from _simulate_tick after settlement processing.
    Mutates state.faction_state in place.
    """
    from .sim import SimEvent
    
    events: list[SimEvent] = []
    
    if not state.faction_state or len(state.faction_state) < 2:
        return events
    
    fs_dict = state.faction_state
    faction_names = list(fs_dict.keys())
    rng.shuffle(faction_names)
    
    # ── 1. Faction Power Drift ─────────────────────────────────────
    for f_name in faction_names:
        fs = fs_dict[f_name]
        if not fs.is_active:
            continue
        
        # Influence drifts toward territory count × 10
        territory_count = len(fs.territory_regions)
        target_influence = min(100, max(10, territory_count * 10 + 20))
        fs.influence += int((target_influence - fs.influence) * 0.05
                            + rng.uniform(-3, 3))
        fs.influence = max(5, min(100, fs.influence))
        
        # Wealth drifts based on faction type
        wealth_biases = {
            "merchant_guild": 2, "mining_consortium": 2, "kingdom": 0,
            "duchy": 0, "noble_house": 1, "thieves_guild": 1,
            "arcane_order": 0, "religious_order": 0, "druidic_circle": -1,
            "mercenary_company": -1, "barbarian_clan": -2, "cult": -1,
        }
        wealth_bias = wealth_biases.get(fs.faction_type, 0)
        fs.wealth += int(rng.uniform(-2, 2) + wealth_bias * 0.5)
        fs.wealth = max(5, min(100, fs.wealth))
        
        # Military drifts based on faction type
        military_biases = {
            "mercenary_company": 2, "barbarian_clan": 2, "kingdom": 1,
            "duchy": 0, "noble_house": -1, "merchant_guild": -2,
            "thieves_guild": 1, "arcane_order": -1, "religious_order": -1,
            "druidic_circle": -1, "cult": 1, "mining_consortium": 0,
        }
        military_bias = military_biases.get(fs.faction_type, 0)
        fs.military += int(rng.uniform(-2, 2) + military_bias * 0.5)
        fs.military = max(5, min(100, fs.military))
        
        # Stability: wars hurt, peace helps
        if fs.at_war_with:
            fs.stability -= int(rng.uniform(1, 4) * chaos_factor)
            fs.years_of_peace = 0
            fs.war_exhaustion += 1
        else:
            fs.stability += int(rng.uniform(0, 2))
            fs.years_of_peace += 1
            fs.war_exhaustion = max(0, fs.war_exhaustion - 1)
        fs.stability = max(5, min(100, fs.stability))
        
        # Wars may end after enough years — formal peace treaties
        if fs.at_war_with and rng.random() < 0.15 * chaos_factor:
            for enemy in list(fs.at_war_with):
                if enemy in fs_dict:
                    enemy_fs = fs_dict[enemy]
                    if rng.random() < 0.4:  # Peace
                        fs.at_war_with.remove(enemy)
                        enemy_fs.at_war_with.remove(fs.name)
                        terms = rng.choice(PEACE_TREATY_TERMS)
                        effect = rng.choice(PEACE_EFFECTS)
                        events.append(SimEvent(
                            year=year,
                            event_type="faction_peace_treaty",
                            description=POLITICAL_EVENT_TEMPLATES[
                                "faction_peace_treaty"
                            ].format(
                                faction_a=fs.name,
                                faction_b=enemy,
                                terms=terms,
                                effect=effect,
                            ),
                            affected_regions=list(set(
                                fs.territory_regions + enemy_fs.territory_regions
                            )),
                        ))
                        # War weariness -> stability recovery
                        fs.stability = min(100, fs.stability + 10)
                        enemy_fs.stability = min(100, enemy_fs.stability + 10)
                        # Reset exhaustion — peace allows recovery
                        fs.war_exhaustion = max(0, fs.war_exhaustion - 3)
                        enemy_fs.war_exhaustion = max(0, enemy_fs.war_exhaustion - 3)
    
    # ── 2. Faction Wars ────────────────────────────────────────────
    for f_name in faction_names:
        fs = fs_dict[f_name]
        if not fs.is_active or fs.at_war_with:
            continue
        
        for other_name in faction_names:
            if other_name <= f_name:
                continue
            fs_other = fs_dict[other_name]
            if not fs_other.is_active:
                continue
            
            if _faction_war_chance(fs, fs_other, world, rng):
                # War breaks out!
                cause = rng.choice(WAR_CAUSES)
                effect = rng.choice(WAR_EFFECTS)
                fs.at_war_with.append(other_name)
                fs_other.at_war_with.append(fs.name)
                
                # Military losses
                mil_loss_a = int(fs.military * rng.uniform(0.05, 0.2))
                mil_loss_b = int(fs_other.military * rng.uniform(0.05, 0.2))
                fs.military = max(5, fs.military - mil_loss_a)
                fs_other.military = max(5, fs_other.military - mil_loss_b)
                
                # Settlement casualties in affected regions
                a_settlements = _find_region_settlements(
                    state, fs.territory_regions)
                b_settlements = _find_region_settlements(
                    state, fs_other.territory_regions)
                affected_settlements = list(set(a_settlements + b_settlements))
                
                # Populate casualties in war zones
                for s_name in affected_settlements[:5]:  # limit impact
                    if s_name in state.settlements:
                        s = state.settlements[s_name]
                        if s.is_active:
                            casualties = max(1, int(s.population * rng.uniform(0.01, 0.06)))
                            s.population = max(1, s.population - casualties)
                            s.prosperity = max(0, s.prosperity - 0.1)
                
                events.append(SimEvent(
                    year=year,
                    event_type="faction_war",
                    description=POLITICAL_EVENT_TEMPLATES["faction_war"].format(
                        faction_a=fs.name,
                        faction_b=other_name,
                        faction_a_type=fs.faction_type.replace("_", " "),
                        faction_b_type=fs_other.faction_type.replace("_", " "),
                        cause=cause,
                        effect=effect,
                    ),
                    affected_settlements=affected_settlements,
                    affected_regions=list(set(
                        fs.territory_regions + fs_other.territory_regions
                    )),
                ))
    
    # ── 3. Alliances (non-rival factions) ──────────────────────────
    for f_name in faction_names:
        fs = fs_dict[f_name]
        if not fs.is_active or len(fs.at_war_with) >= 2:
            continue
        
        for other_name in faction_names:
            if other_name <= f_name:
                continue
            fs_other = fs_dict[other_name]
            if not fs_other.is_active or fs_other.at_war_with:
                continue
            
            # Check they're not already hostile
            is_hostile = False
            if hasattr(world, 'faction_relationships'):
                for rel in world.faction_relationships:
                    names = {rel.faction_a, rel.faction_b}
                    if {f_name, other_name} == names and \
                       rel.rel_type in ("rivalry", "hostility"):
                        is_hostile = True
                        break
            
            if not is_hostile and rng.random() < 0.01 * chaos_factor:
                reason = rng.choice(ALLIANCE_REASONS)
                strength = rng.choice(["loose", "formal", "enduring", "unshakeable"])
                events.append(SimEvent(
                    year=year,
                    event_type="faction_alliance",
                    description=POLITICAL_EVENT_TEMPLATES["faction_alliance"].format(
                        faction_a=fs.name,
                        faction_b=other_name,
                        strength=strength,
                        detail=reason,
                    ),
                    affected_regions=list(set(
                        fs.territory_regions + fs_other.territory_regions
                    )),
                ))
    
    # ── 4. Power Shifts ────────────────────────────────────────────
    for f_name in faction_names:
        fs = fs_dict[f_name]
        if not fs.is_active:
            continue
        
        # Dramatic power shifts (rare, 0.5% per year per faction)
        if rng.random() < 0.005 * chaos_factor:
            cause = rng.choice(POWER_SHIFT_CAUSES)
            shift = int(rng.uniform(10, 30) * (1 if rng.random() < 0.5 else -1))
            fs.influence = max(5, min(100, fs.influence + shift // 3))
            fs.wealth = max(5, min(100, fs.wealth + shift // 3))
            fs.military = max(5, min(100, fs.military + shift // 3))
            effect = "Their power swells across the land." if shift > 0 else "Their influence wanes dramatically."
            
            affected_regions = list(fs.territory_regions)
            a_settlements = _find_region_settlements(state, affected_regions)
            
            events.append(SimEvent(
                year=year,
                event_type="faction_power_shift",
                description=POLITICAL_EVENT_TEMPLATES["faction_power_shift"].format(
                    faction=fs.name,
                    cause=cause,
                    effect=effect,
                ),
                affected_settlements=a_settlements,
                affected_regions=affected_regions,
            ))
        
        # Collapse (very rare, 0.2% per year per faction, only if weak)
        if rng.random() < 0.002 * chaos_factor and fs.power_score < 100:
            cause = rng.choice(COLLAPSE_CAUSES)
            fs.is_active = False
            affected_regions = list(fs.territory_regions)
            a_settlements = _find_region_settlements(state, affected_regions)
            
            # Settlements in collapsed faction's territory suffer
            for s_name in a_settlements[:10]:
                if s_name in state.settlements:
                    s = state.settlements[s_name]
                    if s.is_active:
                        s.prosperity = max(0, s.prosperity - 0.2)
                        s.population = max(1, int(s.population * 0.85))
            
            events.append(SimEvent(
                year=year,
                event_type="faction_collapse",
                description=POLITICAL_EVENT_TEMPLATES["faction_collapse"].format(
                    faction=fs.name,
                    cause=cause,
                    effect="Their territories fall into chaos and their people scatter.",
                ),
                affected_settlements=a_settlements,
                affected_regions=affected_regions,
            ))
    
    # ── 5. Faction → Settlement Effects ────────────────────────────
    for f_name, fs in fs_dict.items():
        if not fs.is_active:
            continue
        
        # Map faction territory to settlements
        settlements_in_territory = _find_region_settlements(
            state, fs.territory_regions)
        
        # Strong faction -> prosperity bonus
        if fs.power_score >= 240:
            bonus = 0.05  # major faction prosperity bonus
        elif fs.power_score >= 160:
            bonus = 0.02  # moderate faction
        else:
            bonus = -0.02 if fs.power_score < 80 else 0  # weak faction penalty
        
        if bonus != 0:
            for s_name in settlements_in_territory:
                if s_name in state.settlements:
                    s = state.settlements[s_name]
                    if s.is_active:
                        s.prosperity = max(0.0, min(1.0, s.prosperity + bonus))
        
        # War exhaustion: prolonged war degrades settlement food and prosperity
        if fs.war_exhaustion > 0 and settlements_in_territory:
            # Exhaustion penalty scales with war_exhaustion (capped at 25)
            exhaustion_malus = min(fs.war_exhaustion * 0.01, 0.25)
            for s_name in settlements_in_territory:
                if s_name in state.settlements:
                    s = state.settlements[s_name]
                    if s.is_active:
                        # Reduce food stores (war consumes resources)
                        food_loss = int(s.food_stores * exhaustion_malus * 0.3)
                        s.food_stores = max(0, s.food_stores - food_loss)
                        # Reduce prosperity (war weariness)
                        s.prosperity = max(0.0, s.prosperity - exhaustion_malus * 0.5)
    
    return events
