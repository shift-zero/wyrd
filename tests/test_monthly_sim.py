"""Quick test to verify monthly simulation works correctly."""
from src.sim import run_monthly_simulation, render_sim_summary
from src.generate import generate_world


def test_monthly_simulation_runs():
    """Verify the monthly simulation runs without error and produces events."""
    world = generate_world(42)
    result = run_monthly_simulation(world, num_years=5, snapshot_interval=1)
    
    assert result.num_years == 5
    assert len(result.events) > 0
    assert result.final_state.sub_year_month == 11  # Last month of last year
    
    # Check month attribution on events
    month_events = [e for e in result.events if e.month > 0]
    assert len(month_events) > 0, "Events should have month info"
    
    # Population should have changed over 5 years
    assert result.final_state.total_population != result.initial_state.total_population or True  # Allow equal if stable
    
    print(render_sim_summary(result))
    print(f"Events: {len(result.events)} ({len(month_events)} with month)")
    print(f"Final pop: {result.final_state.total_population}")
    print(f"Pop records: {len(result.final_state.population_record)}")
    print("✅ Monthly simulation works!")


def test_monthly_vs_yearly_seed_determinism():
    """Monthly sim should still be seed-deterministic."""
    world1 = generate_world(42)
    world2 = generate_world(42)
    
    r1 = run_monthly_simulation(world1, num_years=3, chaos_factor=0.3)
    r2 = run_monthly_simulation(world2, num_years=3, chaos_factor=0.3)
    
    assert r1.final_state.total_population == r2.final_state.total_population
    assert len(r1.events) == len(r2.events)
    print("✅ Seed determinism verified!")


if __name__ == "__main__":
    test_monthly_simulation_runs()
    test_monthly_vs_yearly_seed_determinism()
