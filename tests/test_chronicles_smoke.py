"""Quick smoke test for chronicles engine."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.chronicles import generate_chronicles, Chronicles, Era

# Generate a world
world = generate_world(42)

# Generate chronicles
chronicles = generate_chronicles(world, world.narrative)

print(f"World age: {chronicles.world_age}")
print(f"Number of eras: {chronicles.num_eras}")
print()

for i, era in enumerate(chronicles.eras):
    print(f"{'─' * 60}")
    print(f"Era {i+1}: {era.name} ({era.era_type})")
    print(f"  Period: year {era.start_year} → year {era.end_year} ({era.duration} years)")
    print(f"  Description: {era.description[:120]}...")
    if era.world_modifiers:
        for mod in era.world_modifiers:
            print(f"  [Modifier] {mod}")
    if era.events:
        print(f"  Events ({len(era.events)}):")
        for ev in era.events[:3]:
            print(f"    • [{ev['year']}] {ev['name']}")
            print(f"      {ev['description'][:100]}...")
    print()

print(f"{'═' * 60}")
print(f"Seed determinism test...")
world2 = generate_world(42)
c2 = generate_chronicles(world2, world2.narrative)
assert len(chronicles.eras) == len(c2.eras), "Era count mismatch"
for e1, e2 in zip(chronicles.eras, c2.eras):
    assert e1.name == e2.name, f"Era name mismatch: {e1.name} vs {e2.name}"
    assert len(e1.events) == len(e2.events), f"Event count mismatch in {e1.name}"
print("✅ Seed determinism verified!")

world3 = generate_world(99)
c3 = generate_chronicles(world3, world3.narrative)
assert chronicles.eras[0].name != c3.eras[0].name, "Different seeds should produce different chronicles"
print("✅ Different seeds produce different chronicles!")

print("\n✅ All smoke tests passed!")
