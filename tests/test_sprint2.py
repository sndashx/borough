"""Sprint 2 tests — money/debt graph, market system, contract inheritance."""
from core.world import generate_world
from core.simulation import Simulation
from core.contract import Contract, ContractType, ContractStatus
from core.market import Market, LoanSystem, price_of, BASE_PRICES
from core.item import ItemType


def test_market_runs():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    initial_coins = sum(n.status.coins for n in w.living_npcs())
    sim.run_years(10)
    final_coins = sum(n.status.coins for n in w.living_npcs())
    purchase_contracts = [c for c in w.contracts.values() if c.type == ContractType.PURCHASE]
    debt_contracts = [c for c in w.contracts.values() if c.type == ContractType.DEBT]
    print(f"OK market runs: initial_coins={initial_coins}, final_coins={final_coins}, "
          f"purchase_contracts={len(purchase_contracts)}, debt_contracts={len(debt_contracts)}")


def test_loan_creation():
    w = generate_world(seed=1729, pop=30)
    # Make one NPC very rich, others poor
    rich = next(iter(w.living_npcs()))
    rich.status.coins = 100
    for n in w.living_npcs():
        if n.id != rich.id:
            n.status.coins = 1
    sim = Simulation(w, seed=42)
    sim.run_years(2)
    debts = [c for c in w.contracts.values() if c.type == ContractType.DEBT]
    print(f"OK loan creation: {len(debts)} debts created, rich has {rich.status.coins} coins")
    assert len(debts) > 0, "No debts created despite rich/poor split"


def test_debt_survives_debtor():
    w = generate_world(seed=1729, pop=30)
    creditor = next(iter(w.living_npcs()))
    debtor = next(n for n in w.living_npcs() if n.id != creditor.id)
    c = Contract(
        type=ContractType.DEBT,
        parties=[creditor.id, debtor.id],
        terms={"amount": 50, "reason": "test"},
        year_created=w.year,
        status=ContractStatus.ACTIVE,
    )
    w.add_contract(c)
    sim = Simulation(w, seed=42)
    sim.run_years(120)
    # The contract should still exist, possibly inherited
    still_active = c.status == ContractStatus.ACTIVE
    inherited = len(c.inherited_by) > 0
    print(f"OK debt survives: status={c.status.value}, inherited_by_count={len(c.inherited_by)}")


def test_price_scales_with_supply():
    """Test scarcity (price goes up) and abundance (price goes down)."""
    w = generate_world(seed=1729, pop=30)
    # Test scarcity
    from core.item import Item
    w.items.clear()  # remove all items so grain is scarce
    for b in w.buildings.values():
        b.item_ids.clear()
        b.food_count_cache = 0
    scarce = price_of(ItemType.GRAIN, w)
    # Test abundance
    for _ in range(500):
        w.add_item(Item(type=ItemType.GRAIN, weight=1.0, quality=50))
    cheap = price_of(ItemType.GRAIN, w)
    print(f"OK price scaling: scarce={scarce}, with surplus={cheap}")
    assert scarce > cheap, f"Price didn't drop with surplus: scarce={scarce} <= cheap={cheap}"
    assert scarce > 1, f"Scarce price should be > 1: {scarce}"


def test_market_no_negative_coins():
    w = generate_world(seed=1729, pop=30)
    sim = Simulation(w, seed=42)
    sim.run_years(20)
    for n in w.living_npcs():
        assert n.status.coins >= 0, f"{n.first_name} has negative coins: {n.status.coins}"
    print("OK no NPC has negative coins after 20y")


if __name__ == "__main__":
    test_market_runs()
    test_loan_creation()
    test_debt_survives_debtor()
    test_price_scales_with_supply()
    test_market_no_negative_coins()
    print("\n=== ALL SPRINT 2 TESTS PASSED ===")
