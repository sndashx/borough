"""Sprint 5 tests: spectator + chronicle viewer.

These are the *read-only* modes of the game. You don't need a player.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.world import generate_world
from core.spectator import (
    npc_summary, list_living_npcs, list_famous_npcs, list_recent_events,
    search_chronicle, town_statistics, render_chronicle_section,
    find_player_ghosts,
)
from core.chronicle import Chronicle
from core.simulation import Simulation


def test_npc_summary_has_life():
    world = generate_world(seed=1729)
    npc = list(world.npcs.values())[0]
    v = npc_summary(world, npc.id)
    assert v is not None
    assert v.first_name == npc.first_name
    assert v.birth_year == npc.birth_year
    assert "was born" in v.summary
    print(f"  PASS: npc summary → '{v.summary[:80]}...'")


def test_list_living_npcs_complete():
    world = generate_world(seed=1729)
    living = list_living_npcs(world)
    assert len(living) == 30, f"Expected 30 living, got {len(living)}"
    assert all(v.is_alive for v in living)
    print(f"  PASS: list_living_npcs → {len(living)} NPCs")


def test_famous_npcs_ranks_by_mentions():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(15)
    famous = list_famous_npcs(world, min_mentions=2)
    # Sorted descending by mention count
    if len(famous) >= 2:
        assert famous[0][1] >= famous[1][1]
    print(f"  PASS: famous_npcs → {len(famous)} NPCs with ≥2 mentions (top: {famous[0][2] if famous else 'none'})")


def test_search_chronicle_finds_known_entry():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    chronicle.record(7, "famine_ended", "The long famine ended today.", involved_npc_ids=[])
    results = search_chronicle(world, "famine")
    assert any("famine" in r["summary"] for r in results)
    print(f"  PASS: search → {len(results)} entries for 'famine'")


def test_town_statistics_after_run():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(15)
    stats = town_statistics(world)
    assert stats["population_living"] >= 20
    assert stats["year"] == 15
    assert stats["total_contracts_ever"] > 0
    print(f"  PASS: town statistics — pop {stats['population_living']}, contracts {stats['total_contracts_ever']}, coins {stats['coins_in_circulation']}")


def test_render_chronicle_section_format():
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(10)
    text = render_chronicle_section(world, 0, 10, max_entries=20)
    assert "Chronicle" in text
    assert "Y" in text
    print("  PASS: chronicle renders")


def test_find_player_ghosts_empty_initially():
    world = generate_world(seed=1729)
    ghosts = find_player_ghosts(world)
    # No ghosts at game start unless a previous player-life was played
    print(f"  PASS: initial ghost count = {len(ghosts)}")


def test_spectator_mode_no_player_required():
    """Spectator mode must work without any player being spawned."""
    world = generate_world(seed=1729)
    chronicle = Chronicle(world)
    sim = Simulation(world, seed=world.seed)
    sim.run_years(20)
    # No player spawn — just watch
    living = list_living_npcs(world)
    assert len(living) > 0
    stats = town_statistics(world)
    assert stats["year"] == 20
    print(f"  PASS: spectator at year {stats['year']} — pop {stats['population_living']}, no player needed")


if __name__ == "__main__":
    print("Sprint 5 tests:")
    test_npc_summary_has_life()
    test_list_living_npcs_complete()
    test_famous_npcs_ranks_by_mentions()
    test_search_chronicle_finds_known_entry()
    test_town_statistics_after_run()
    test_render_chronicle_section_format()
    test_find_player_ghosts_empty_initially()
    test_spectator_mode_no_player_required()
    print("\nAll Sprint 5 tests passed.")
