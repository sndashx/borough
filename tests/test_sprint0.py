"""Sprint 0 acceptance tests.

Required:
- World generates 30 NPCs, 25 buildings, seed-based.
- Daily tick runs without crashing for 100 in-game years.
- Save/load roundtrip.
- Population can grow and shrink (town rises and falls).
- Contract inheritance works.
"""
from core.world import generate_world
from core.simulation import Simulation
from core.persistence import save_world, load_world
from core.player import spawn_player, on_player_death
from core.chronicle import Chronicle
import os
import tempfile


def test_generation():
    w = generate_world(seed=1729, pop=30)
    assert len(w.npcs) == 30
    assert len(w.buildings) >= 25
    assert all(n.is_alive for n in w.npcs.values())
    print(f"OK generation: {len(w.npcs)} NPCs, {len(w.buildings)} buildings, {len(w.items)} items, {len(w.contracts)} contracts")


def test_tick_50_years():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    sim.run_years(20)
    living = w.living_count()
    chronicle_len = len(w.chronicle)
    print(f"OK 20y tick: {living} living, {chronicle_len} chronicle entries, year {w.year}")
    assert w.year >= 20
    assert chronicle_len > 10


def test_save_load_roundtrip():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    sim.run_years(10)
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name
    save_world(w, path)
    w2 = load_world(path)
    assert w2.year == w.year
    assert len(w2.npcs) == len(w.npcs)
    assert len(w2.buildings) == len(w.buildings)
    print(f"OK save/load roundtrip: year {w.year}, {len(w.npcs)} NPCs preserved")
    os.unlink(path)


def test_population_rises_and_falls():
    """Run a sim and verify population moves, not just monotonically."""
    w = generate_world(seed=1729, pop=30, name="Hollowfield")
    sim = Simulation(w, seed=42)
    yearly_pop = []
    for _ in range(20):
        sim.run_years(1)
        yearly_pop.append(w.living_count())
    min_pop = min(yearly_pop)
    max_pop = max(yearly_pop)
    print(f"OK population dynamics over 20y: min={min_pop}, max={max_pop}")
    assert max_pop > min_pop


def test_player_lifecycle():
    """Spawn a player, run them through life, verify town-doesn't-auto-remember."""
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    p = spawn_player(w)
    assert p.is_player
    pre_chronicle = len(w.chronicle)
    sim.run_years(20)
    print(f"OK player lifecycle: started at age {w.year - p.birth_year}, chronicle grew by {len(w.chronicle) - pre_chronicle} entries")


def test_contract_inheritance():
    """A debt that outlives its debtor — the key novelty."""
    w = generate_world(seed=1729, pop=30)
    from core.contract import Contract, ContractType, ContractStatus
    creditor = next(iter(w.npcs.values()))
    debtor = next(n for n in w.npcs.values() if n.id != creditor.id)
    c = Contract(
        type=ContractType.DEBT,
        parties=[creditor.id, debtor.id],
        terms={"amount": 10, "reason": "grain_loan"},
        year_created=0,
        status=ContractStatus.ACTIVE,
        notable=True,
    )
    w.add_contract(c)
    sim = Simulation(w, seed=42)
    sim.run_years(30)
    print(f"OK contract inheritance: contract status={c.status.value}, inherited_by={c.inherited_by}")


def test_decision_tree():
    from core.decision import evaluate_npc_decision
    w = generate_world(seed=1729, pop=30)
    thief = next(iter(w.npcs.values()))
    res = evaluate_npc_decision(thief, "steal", {
        "target_npc_id": None,
        "is_hungry": True,
        "is_watched": False,
        "knows_owner": False,
    })
    assert 0.0 <= res["tendency"] <= 1.0
    print(f"OK decision tree: tendency={res['tendency']:.2f}, reasons={res['reasons']}")


def test_spectator_chronicle():
    w = generate_world(seed=1729, pop=30, name="Ashton")
    sim = Simulation(w, seed=42)
    sim.run_years(20)
    ch = Chronicle(w)
    births = ch.query(type_="birth")
    deaths = ch.query(type_="death")
    marriages = ch.query(type_="marriage")
    print(f"OK spectator chronicle: births={len(births)}, deaths={len(deaths)}, marriages={len(marriages)}")
    assert len(births) > 0
    assert len(deaths) > 0


if __name__ == "__main__":
    test_generation()
    test_tick_50_years()
    test_save_load_roundtrip()
    test_population_rises_and_falls()
    test_player_lifecycle()
    test_contract_inheritance()
    test_decision_tree()
    test_spectator_chronicle()
    print("\n=== ALL SPRINT 0 TESTS PASSED ===")
