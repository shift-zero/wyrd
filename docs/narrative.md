# Narrative Engine

`src/narrative.py` — Phase 4. Characters, events, and quests grounded in the world's geography and cultures.

## Data Model

```python
@dataclass class Character:
    name, surname, age, gender, occupation
    personality_traits, home_region, home_settlement
    backstory, status

@dataclass class EventChain:
    name, year, event_type, description
    regions_involved, settlements_involved
    characters_involved, consequences

@dataclass class Quest:
    name, quest_type, difficulty, description
    giver_character, giver_settlement
    target_region, rewards, is_active

@dataclass class Narrative:
    seed, characters, events, quests, current_year
```

## Character Generation

- 1-3 characters per settlement
- Names from gendered pools with unique-enforcement
- Occupations: ordinary (farmers, smiths) for small pops, noble roles (chieftain, lord) for large pops
- Backstories assembled from template fragments

## Event Types

`conflict`, `discovery`, `natural`, `political`, `cultural` — each with detailed sentence templates.

## Quest Types

`exploration`, `combat`, `diplomacy`, `gathering`, `intrigue` — with difficulty ratings and rewards.

## See also

- [Chronicles Engine](chronicles.md) — uses narrative characters as legendary participants
- [Simulation](simulation.md) — event model extended for sim events
