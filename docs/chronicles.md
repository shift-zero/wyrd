# Chronicles Engine

`src/chronicles.py` — Phase 5. Era-based world history with causal links.

## Data Model

```python
@dataclass class Era:
    name, era_type, start_year, end_year
    description, events: list[dict]
    world_modifiers: list[str]
    is_present: bool

@dataclass class Chronicles:
    seed, eras: list[Era], world_age: int
```

## Era Types (8)

| Type | Duration | Character |
|------|----------|-----------|
| `founding` | 50-150 yrs | First settlements rise |
| `golden_age` | 30-120 | Prosperity and culture |
| `cataclysm` | 1-15 | Disaster strikes |
| `dark_age` | 30-120 | Recovery after fall |
| `age_of` | 30-120 | A theme defines the era |
| `decline` | 30-120 | Resources run dry |
| `rebirth` | 30-120 | Rising from ashes |
| `schism` | 30-120 | Division and conflict |

## Generation

- 4-8 eras spanning 1000 years
- Era type weighted for natural progression (same type less likely to repeat)
- Each era references characters from the Narrative engine as legendary participants
- World modifiers (ruins, fallen empires, contested borders) persist to simulation

## See also

- [Narrative Engine](narrative.md) — character pool for legends
- [Simulation](simulation.md) — sim picks up where chronicles leave off
