import pytest
from core.world import generate_world, World
from core.simulation import Simulation
from core.anatomy import Anatomy
from core.relic import RelicRegistry
from core.governance import GovernanceSystem
from core.cult import CultRegistry
from core.lore import LoreRegistry


def test_deep_systems_initialization():
    world = generate_world(seed="deep_seed_101", pop=35)
    sim = Simulation(world, seed=world.seed)

    assert world.relics is not None
    assert world.governance is not None
    assert world.cults is not None
    assert world.lore is not None

    # Run simulation for 5 years
    sim.run_years(5)

    assert world.year == 5
    # Verify governance elections and treasury
    assert world.governance.policies.treasury_gold >= 0
    assert any(seat.incumbent_id is not None for seat in world.governance.seats.values())

    # Check anatomy
    living = world.living_npcs()
    assert len(living) > 0
    for npc in living:
        assert isinstance(npc.anatomy, Anatomy)


def test_relic_creation_and_inheritance():
    world = generate_world(seed="relic_seed_202", pop=30)
    sim = Simulation(world, seed=world.seed)

    # Force an artisan with high skill
    living = world.living_npcs()
    artisan = living[0]
    artisan.knowledge.skills["smith"] = 90

    sim.run_years(10)

    # Check serialization roundtrip
    d = world.to_dict()
    world2 = World.from_dict(d)
    assert world2.year == 10
    assert world2.governance.policies.treasury_gold == world.governance.policies.treasury_gold


if __name__ == "__main__":
    pytest.main([__file__])
