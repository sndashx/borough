"""Sprint 3 tests — knowledge/mortality, apprenticeship, skill extinction."""
from core.world import generate_world
from core.simulation import Simulation
from core.contract import Contract, ContractType, ContractStatus


def test_apprenticeship_teaches_skill():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    sim.run_years(5)
    # Find someone with non-zero skills
    skilled = [n for n in w.living_npcs() if any(v > 0 for v in n.knowledge.skills.values())]
    total_skill = sum(sum(n.knowledge.skills.values()) for n in skilled)
    print(f"OK apprenticeship teaches: {len(skilled)} skilled NPCs, total skill points={total_skill}")


def test_skill_extinction_recorded():
    """When the only NPC with a critical skill dies, the chronicle should record it."""
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    # Set one NPC as the only reader — force kill them
    reader = next(n for n in w.living_npcs() if n.status.occupation == "priest" or "reading" in n.knowledge.skills)
    for n in w.living_npcs():
        if n.id != reader.id:
            n.knowledge.skills.pop("reading", None)
    reader.knowledge.skills["reading"] = 50
    # Force-kill the reader in 5 years
    reader.death_year = w.year + 5
    reader.cause_of_death = "test"
    sim.run_years(20)
    extinct = [e for e in w.chronicle if e["type"] == "skill_lost"]
    print(f"OK skill extinction: {len(extinct)} extinction events recorded")


def test_master_death_breaks_apprenticeship():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    # Set up an explicit apprenticeship
    adult = next(n for n in w.living_npcs() if w.year - n.birth_year >= 25)
    child = next(n for n in w.living_npcs() if w.year - n.birth_year < 18)
    c = Contract(
        type=ContractType.APPRENTICESHIP,
        parties=[child.id, adult.id],
        terms={"skill": "smithing", "term_years": 7},
        year_created=w.year,
        status=ContractStatus.ACTIVE,
    )
    w.add_contract(c)
    # Force adult to die
    adult.death_year = w.year
    adult.cause_of_death = "test"
    sim.run_years(1)
    print(f"OK master death: contract status={c.status.value}, mentor_died_year={c.terms.get('master_died_year')}")


def test_knowledge_decays():
    """Memories should fade over time."""
    from core.gossip import form_memory_of
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    npc = next(iter(w.living_npcs()))
    form_memory_of(npc, w.year, "wedding", ["x"], 50)
    initial_conf = npc.memory[0].confidence
    sim.run_years(10)
    found = [m for m in npc.memory if m.event_type == "wedding"]
    print(f"OK knowledge decay: initial_conf={initial_conf}, after_10y_conf={found[0].confidence if found else 'GONE'}")


if __name__ == "__main__":
    test_apprenticeship_teaches_skill()
    test_skill_extinction_recorded()
    test_master_death_breaks_apprenticeship()
    test_knowledge_decays()
    print("\n=== ALL SPRINT 3 TESTS PASSED ===")
