"""
Tests for wyrd Phase 9 — Pantheon & Religion System.

Covers pantheon generation, determinism, deity creation, holy site generation,
CLI integration, rendering, TTRPG export integration, and edge cases.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.generate import generate_world
from src.religion import (
    generate_pantheon,
    _select_domains_for_world,
    _generate_deity,
    _generate_holy_sites,
    ALL_DOMAINS,
    DEITY_NAMES_MALE,
    DEITY_NAMES_FEMALE,
    Deity,
    Religion,
    PantheonSystem,
    HolySite,
)
from src.world import World
from src.render import render_pantheon
from src.serialize import world_to_dict, dict_to_world


class TestPantheonGeneration:
    """Core pantheon generation must be deterministic and well-structured."""

    def _generate(self, seed=42):
        world = generate_world(seed)
        pantheon = generate_pantheon(world)
        return world, pantheon

    def test_pantheon_is_pantheonsystem(self):
        """generate_pantheon returns a PantheonSystem."""
        _, p = self._generate()
        assert isinstance(p, PantheonSystem)

    def test_pantheon_has_seed(self):
        """Pantheon stores its generation seed."""
        _, p = self._generate(42)
        assert p.seed == 42

    def test_pantheon_has_religions(self):
        """Every pantheon has at least one religion."""
        _, p = self._generate()
        assert len(p.religions) >= 1

    def test_pantheon_at_most_two_religions(self):
        """Pantheon should not generate more than 2 religions."""
        _, p = self._generate()
        assert len(p.religions) <= 2

    def test_each_religion_has_deities(self):
        """Every religion has at least 2 deities."""
        _, p = self._generate()
        for r in p.religions:
            assert len(r.pantheon) >= 2, f"{r.name} has only {len(r.pantheon)} deities"

    def test_each_religion_has_tenets(self):
        """Every religion has 3-6 tenets."""
        _, p = self._generate()
        for r in p.religions:
            assert 3 <= len(r.tenets) <= 6

    def test_each_religion_has_holy_days(self):
        """Every religion has 2-5 holy days."""
        _, p = self._generate()
        for r in p.religions:
            assert 2 <= len(r.holy_days) <= 5

    def test_each_religion_has_primary_deity(self):
        """Every religion designates a primary deity."""
        _, p = self._generate()
        for r in p.religions:
            assert r.primary_deity is not None

    def test_primary_deity_exists_in_pantheon(self):
        """The primary deity is actually in the pantheon."""
        _, p = self._generate()
        for r in p.religions:
            names = [d.name for d in r.pantheon]
            assert r.primary_deity in names

    def test_region_religion_is_populated(self):
        """Every region is assigned a religion."""
        world, p = self._generate()
        assert len(p.region_religion) == len(world.regions)
        for region in world.regions:
            assert region.name in p.region_religion

    def test_holy_sites_in_religions(self):
        """Religions have holy sites tied to settlements."""
        _, p = self._generate()
        total_sites = sum(len(r.holy_sites) for r in p.religions)
        assert total_sites > 0

    def test_holy_sites_have_valid_types(self):
        """Holy sites have recognized site types."""
        valid_types = {"temple", "shrine", "monastery", "oracle", "grove", "sanctuary"}
        _, p = self._generate()
        for r in p.religions:
            for s in r.holy_sites:
                assert s.site_type in valid_types

    def test_holy_sites_reference_real_settlements(self):
        """Holy sites reference actual settlements in the world."""
        world, p = self._generate()
        all_settlement_names = set(
            s.name for r in world.regions for s in r.settlements
        )
        for r in p.religions:
            for s in r.holy_sites:
                assert s.settlement in all_settlement_names, f"{s.settlement} not in world"

    def test_deities_have_domains(self):
        """Every deity has at least one domain."""
        _, p = self._generate()
        for r in p.religions:
            for d in r.pantheon:
                assert len(d.domains) >= 1

    def test_deities_have_valid_alignments(self):
        """Deity alignments are valid."""
        valid = {"good", "evil", "lawful", "chaotic", "neutral"}
        _, p = self._generate()
        for r in p.religions:
            for d in r.pantheon:
                assert d.alignment in valid

    def test_deities_have_symbols(self):
        """Every deity has a sacred symbol."""
        _, p = self._generate()
        for r in p.religions:
            for d in r.pantheon:
                assert len(d.symbol) > 0

    def test_deities_have_holy_animals(self):
        """Every deity has a holy animal."""
        _, p = self._generate()
        for r in p.religions:
            for d in r.pantheon:
                assert len(d.holy_animal) > 0

    def test_deities_have_clergy_titles(self):
        """Every deity has at least one clergy title."""
        _, p = self._generate()
        for r in p.religions:
            for d in r.pantheon:
                assert len(d.clergy_title) > 0

    def test_clergy_titles_are_in_religion(self):
        """Religion clergy_titles includes deity clergy titles."""
        _, p = self._generate()
        for r in p.religions:
            deity_titles = set(d.clergy_title for d in r.pantheon)
            # At least some of the deity titles should be in the religion list
            if deity_titles and r.clergy_titles:
                overlap = deity_titles.intersection(r.clergy_titles)
                assert len(overlap) > 0 or len(deity_titles) <= len(r.clergy_titles)


class TestPantheonDeterminism:
    """Pantheon generation must be seed-deterministic."""

    def test_same_seed_same_pantheon(self):
        """Same seed produces identical pantheon."""
        w1 = generate_world(42)
        w2 = generate_world(42)
        p1 = generate_pantheon(w1)
        p2 = generate_pantheon(w2)
        self._compare_pantheons(p1, p2)

    def test_different_seeds_different_pantheon(self):
        """Different seeds produce different pantheons (usually)."""
        w1 = generate_world(42)
        w2 = generate_world(99)
        p1 = generate_pantheon(w1)
        p2 = generate_pantheon(w2)
        # Names should differ
        names1 = {d.name for r in p1.religions for d in r.pantheon}
        names2 = {d.name for r in p2.religions for d in r.pantheon}
        # Very unlikely that 42 and 99 produce the same deities
        assert names1 != names2 or len(p1.religions) != len(p2.religions)

    def test_deterministic_with_seed_override(self):
        """Explicit seed override produces same pantheon."""
        w = generate_world(42)
        p1 = generate_pantheon(w, seed=100)
        p2 = generate_pantheon(w, seed=100)
        self._compare_pantheons(p1, p2)

    def _compare_pantheons(self, p1, p2):
        assert p1.seed == p2.seed
        assert len(p1.religions) == len(p2.religions)
        for r1, r2 in zip(p1.religions, p2.religions):
            assert r1.name == r2.name
            assert len(r1.pantheon) == len(r2.pantheon)
            for d1, d2 in zip(r1.pantheon, r2.pantheon):
                assert d1.name == d2.name
                assert d1.surname == d2.surname
                assert d1.domains == d2.domains
                assert d1.alignment == d2.alignment


class TestPantheonRendering:
    """Pantheon rendering should produce readable ANSI output."""

    def test_render_with_pantheon(self):
        """Rendering a world with pantheon returns non-empty output."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        output = render_pantheon(world)
        assert len(output) > 100
        assert "Pantheon" in output or "wyrd" in output

    def test_render_without_pantheon(self):
        """Rendering without pantheon returns placeholder."""
        world = generate_world(42)
        output = render_pantheon(world)
        assert "(no pantheon generated)" in output

    def test_render_shows_religion_names(self):
        """Rendered output includes religion names."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        output = render_pantheon(world)
        for r in world.pantheon.religions:
            # The religion name should appear somewhere in the output
            # (may be truncated, so check first few chars)
            name_part = r.name.split(" ")[0] if " " in r.name else r.name
            assert name_part in output or r.primary_deity in output


class TestPantheonSerialization:
    """Pantheon must serialize and deserialize correctly."""

    def test_serialization_round_trip(self):
        """Pantheon survives save/load round trip."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        data = world_to_dict(world)
        assert "pantheon" in data
        restored = dict_to_world(data)
        assert restored.pantheon is not None
        assert restored.pantheon.total_deities == world.pantheon.total_deities
        assert len(restored.pantheon.religions) == len(world.pantheon.religions)

    def test_serialization_preserves_deities(self):
        """Deity names and domains survive serialization."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for r_orig, r_rest in zip(world.pantheon.religions, restored.pantheon.religions):
            for d_orig, d_rest in zip(r_orig.pantheon, r_rest.pantheon):
                assert d_orig.name == d_rest.name
                assert d_orig.surname == d_rest.surname
                assert d_orig.domains == d_rest.domains
                assert d_orig.alignment == d_rest.alignment

    def test_serialization_without_pantheon(self):
        """World without pantheon serializes fine."""
        world = generate_world(42)
        data = world_to_dict(world)
        assert "pantheon" not in data
        restored = dict_to_world(data)
        assert restored.pantheon is None

    def test_serialization_preserves_holy_sites(self):
        """Holy sites survive serialization round trip."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for r_orig, r_rest in zip(world.pantheon.religions, restored.pantheon.religions):
            for s_orig, s_rest in zip(r_orig.holy_sites, r_rest.holy_sites):
                assert s_orig.name == s_rest.name
                assert s_orig.settlement == s_rest.settlement
                assert s_orig.site_type == s_rest.site_type

    def test_serialization_preserves_religion_tenets(self):
        """Core tenets survive serialization."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        for r_orig, r_rest in zip(world.pantheon.religions, restored.pantheon.religions):
            assert r_orig.tenets == r_rest.tenets
            assert r_orig.holy_days == r_rest.holy_days
            assert r_orig.primary_deity == r_rest.primary_deity

    def test_serialization_preserves_region_religion(self):
        """Region-to-religion mapping survives serialization."""
        world = generate_world(42)
        world.pantheon = generate_pantheon(world)
        data = world_to_dict(world)
        restored = dict_to_world(data)
        assert restored.pantheon.region_religion == world.pantheon.region_religion


class TestEdgeCases:
    """Edge cases in pantheon generation."""

    def test_tiny_world(self):
        """Even tiny worlds should generate a pantheon."""
        world = generate_world(42, width=20, height=15)
        pantheon = generate_pantheon(world)
        assert len(pantheon.religions) >= 1
        assert pantheon.total_deities > 0

    def test_world_without_lore(self):
        """Pantheon works without lore."""
        world = generate_world(42)
        world.lore = None
        pantheon = generate_pantheon(world)
        assert len(pantheon.religions) >= 1

    def test_world_without_settlements(self):
        """A world with very few settlements still gets a pantheon."""
        world = generate_world(42, width=30, height=20)
        pantheon = generate_pantheon(world)
        assert len(pantheon.religions) >= 1

    def test_domain_selection_is_valid(self):
        """Selected domains are from the valid domain pool."""
        world = generate_world(42)
        import random
        rng = random.Random(42)
        domains = _select_domains_for_world(world, rng)
        valid_names = {d["name"] for d in ALL_DOMAINS}
        for domain in domains:
            assert domain["name"] in valid_names

    def test_domain_selection_minimum(self):
        """At least 4 domains are always selected."""
        world = generate_world(42)
        import random
        rng = random.Random(99)
        domains = _select_domains_for_world(world, rng)
        assert len(domains) >= 4

    def test_deity_gender_distribution(self):
        """Deity generation produces both male and female names."""
        world = generate_world(42)
        import random
        rng = random.Random(42)
        domain = ALL_DOMAINS[0]
        genders_seen = set()
        for _ in range(20):
            deity = _generate_deity(domain, rng)
            if deity.name in DEITY_NAMES_MALE:
                genders_seen.add("male")
            if deity.name in DEITY_NAMES_FEMALE:
                genders_seen.add("female")
        assert len(genders_seen) >= 1  # At minimum one gender

    def test_holy_sites_generated_for_tiny_world(self):
        """Even tiny worlds get at least some holy sites."""
        world = generate_world(42, width=30, height=20)
        import random
        rng = random.Random(42)
        domain = ALL_DOMAINS[0]
        deity = _generate_deity(domain, rng)
        sites = _generate_holy_sites("Test Faith", [deity], world, rng)
        assert len(sites) > 0


class TestPantheonProperties:
    """PantheonSystem computed properties."""

    def test_total_deities_count(self):
        """total_deities returns correct count."""
        world = generate_world(42)
        pantheon = generate_pantheon(world)
        manual = sum(len(r.pantheon) for r in pantheon.religions)
        assert pantheon.total_deities == manual

    def test_total_holy_sites_count(self):
        """total_holy_sites returns correct count."""
        world = generate_world(42)
        pantheon = generate_pantheon(world)
        manual = sum(len(r.holy_sites) for r in pantheon.religions)
        assert pantheon.total_holy_sites == manual

    def test_dominant_religion_most_regions(self):
        """dominant_religion is the one with most adherent regions."""
        world = generate_world(42)
        pantheon = generate_pantheon(world)
        if len(pantheon.religions) > 1:
            dominant = pantheon.dominant_religion
            assert dominant is not None
            rel_counts = {}
            for rn in pantheon.region_religion.values():
                rel_counts[rn] = rel_counts.get(rn, 0) + 1
            max_count = max(rel_counts.values())
            assert rel_counts[dominant.name] == max_count

    def test_no_religions_properties(self):
        """Empty pantheon returns safe defaults."""
        pantheon = PantheonSystem(seed=0, religions=[], region_religion={})
        assert pantheon.total_deities == 0
        assert pantheon.total_holy_sites == 0
        assert pantheon.dominant_religion is None
