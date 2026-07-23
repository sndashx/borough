"""Market system — the money/debt graph.
Money is a graph of relationships, not a number.
Every transaction is a contract between NPCs.
"""
from __future__ import annotations
import random
from typing import Optional

from .world import World
from .npc import NPC, Relationship
from .contract import Contract, ContractType, ContractStatus
from .item import Item, ItemType


# Price reference: how many coppers an item is worth at base.
# Real prices fluctuate based on supply/demand.
BASE_PRICES = {
    ItemType.GRAIN: 1,
    ItemType.BREAD: 2,
    ItemType.MEAT: 3,
    ItemType.HERB: 4,
    ItemType.TOOL: 10,
    ItemType.WOOD: 2,
    ItemType.STONE: 2,
    ItemType.CLOTH: 5,
    ItemType.FURNITURE: 15,
    ItemType.COIN: 1,
    ItemType.WEAPON: 50,
}


def price_of(item_type: ItemType, world: World) -> int:
    """Get current price for an item type. Modulated by town scarcity."""
    base = BASE_PRICES.get(item_type, 5)
    # Count items of this type in town storage
    count = sum(1 for it in world.items.values() if it.type == item_type)
    target = max(10, world.living_count() * 2)
    if count > target * 2:
        return max(1, base // 2)  # abundant
    if count < target // 2:
        return base * 2  # scarce
    return base


class Market:
    """Yearly market tick. NPCs trade goods based on needs."""

    def __init__(self, world: World, rng: random.Random):
        self.world = world
        self.rng = rng

    def run(self) -> int:
        """Execute one market round. Returns number of trades."""
        trades = 0
        living = self.world.living_npcs()
        # Each NPC has a chance to trade
        for npc in living:
            if self.rng.random() < 0.3:  # 30% chance to engage in trade
                if self._maybe_sell(npc):
                    trades += 1
                elif self._maybe_buy(npc):
                    trades += 1
        return trades

    def _maybe_sell(self, npc: NPC) -> bool:
        """NPC sells from household storage if they have surplus and are not starving."""
        if npc.body.hunger < 30:
            return False
        if not npc.status.household_id:
            return False
        house = self.world.buildings.get(npc.status.household_id)
        if not house or not house.item_ids:
            return False
        # Find a non-food item to sell
        for iid in list(house.item_ids):
            item = self.world.items.get(iid)
            if not item:
                house.item_ids.remove(iid)
                continue
            if item.type in (ItemType.GRAIN, ItemType.BREAD, ItemType.MEAT, ItemType.HERB):
                continue  # keep food for the household
            # Try to find a buyer
            price = price_of(item.type, self.world)
            buyer = self._find_buyer(npc, item, price)
            if buyer:
                self._execute_sale(npc, buyer, item, price)
                return True
        return False

    def _maybe_buy(self, npc: NPC) -> bool:
        """NPC buys if they have coins and need something."""
        if npc.status.coins < 3:
            return False
        # Decide what they need
        needed = self._what_does_npc_need(npc)
        if not needed:
            return False
        # Find a seller
        seller = self._find_seller(npc, needed)
        if not seller:
            return False
        item = self._find_seller_item(seller, needed)
        if not item:
            return False
        price = price_of(item.type, self.world)
        if npc.status.coins < price:
            return False
        self._execute_sale(seller, npc, item, price)
        return True

    def _what_does_npc_need(self, npc: NPC) -> Optional[ItemType]:
        """Decide what an NPC needs based on their state."""
        if npc.body.hunger < 60:
            return ItemType.GRAIN  # always need food
        if npc.status.occupation in ("smith", "carpenter", "mason"):
            return self.rng.choice([ItemType.TOOL, ItemType.WOOD, ItemType.STONE])
        if npc.status.occupation == "weaver":
            return ItemType.CLOTH
        # Generic
        if self.rng.random() < 0.3:
            return self.rng.choice([ItemType.TOOL, ItemType.WOOD, ItemType.CLOTH])
        return None

    def _find_buyer(self, seller: NPC, item: Item, price: int) -> Optional[NPC]:
        """Find a buyer who has the coins and affinity."""
        living = self.world.living_npcs()
        candidates = [n for n in living
                      if n.id != seller.id
                      and n.status.coins >= price
                      and (n.id not in seller.relationships
                           or seller.relationships[n.id].affinity > -30)]
        if not candidates:
            return None
        # Prefer known associates
        if self.rng.random() < 0.6:
            known = [c for c in candidates if c.id in seller.relationships]
            if known:
                return self.rng.choice(known)
        return self.rng.choice(candidates)

    def _find_seller(self, buyer: NPC, item_type: ItemType) -> Optional[NPC]:
        """Find an NPC selling this type."""
        living = self.world.living_npcs()
        candidates = []
        for n in living:
            if n.id == buyer.id:
                continue
            # Check inventory and household
            has = any(self.world.items.get(iid) and self.world.items[iid].type == item_type
                      for iid in n.status.inventory_item_ids)
            if has:
                candidates.append(n)
                continue
            if n.status.household_id:
                h = self.world.buildings.get(n.status.household_id)
                if h and any(self.world.items.get(iid) and self.world.items[iid].type == item_type
                             for iid in h.item_ids):
                    candidates.append(n)
        if not candidates:
            return None
        if self.rng.random() < 0.6:
            known = [c for c in candidates if c.id in buyer.relationships]
            if known:
                return self.rng.choice(known)
        return self.rng.choice(candidates)

    def _find_seller_item(self, seller: NPC, item_type: ItemType) -> Optional[Item]:
        for iid in seller.status.inventory_item_ids:
            item = self.world.items.get(iid)
            if item and item.type == item_type:
                return item
        if seller.status.household_id:
            h = self.world.buildings.get(seller.status.household_id)
            if h:
                for iid in h.item_ids:
                    item = self.world.items.get(iid)
                    if item and item.type == item_type:
                        return item
        return None

    def _execute_sale(self, seller: NPC, buyer: NPC, item: Item, price: int) -> None:
        """Transfer item and coins, create a sale contract."""
        if price > buyer.status.coins:
            return
        # Transfer
        buyer.status.coins -= price
        seller.status.coins += price
        # Remove from seller's inventory/household
        if item.id in seller.status.inventory_item_ids:
            seller.status.inventory_item_ids.remove(item.id)
        if seller.status.household_id:
            h = self.world.buildings.get(seller.status.household_id)
            if h and item.id in h.item_ids:
                h.item_ids.remove(item.id)
                if item.type in (ItemType.GRAIN, ItemType.BREAD, ItemType.MEAT, ItemType.HERB):
                    h.food_count_cache = max(0, h.food_count_cache - 1)
        # Add to buyer's inventory
        if item.id not in buyer.status.inventory_item_ids:
            buyer.status.inventory_item_ids.append(item.id)
        item.owner_npc_id = buyer.id
        # Contract
        c = Contract(
            type=ContractType.PURCHASE,
            parties=[seller.id, buyer.id],
            witnesses=[],
            year_created=self.world.year,
            terms={"item_type": item.type.value, "price": price},
            status=ContractStatus.FULFILLED,
            notable=False,
        )
        self.world.add_contract(c)
        # Update relationship
        if buyer.id not in seller.relationships:
            seller.relationships[buyer.id] = Relationship()
        if seller.id not in buyer.relationships:
            buyer.relationships[seller.id] = Relationship()
        seller.relationships[buyer.id].affinity = min(100, seller.relationships[buyer.id].affinity + 2)
        buyer.relationships[seller.id].affinity = min(100, buyer.relationships[seller.id].affinity + 1)
        # Chronicle only if notable
        if price > 20:
            self.world.chronicle.append({
                "year": self.world.year,
                "type": "trade",
                "summary": f"{buyer.first_name} {buyer.family_name} bought {item.type.value} from {seller.first_name} {seller.family_name} for {price} coppers.",
                "notable": True,
                "involved": [buyer.id, seller.id],
            })


class LoanSystem:
    """Yearly lending round. NPCs with surplus coins may lend to those in need,
    creating debt contracts that outlive both parties."""

    def __init__(self, world: World, rng: random.Random):
        self.world = world
        self.rng = rng

    def run(self) -> int:
        loans = 0
        rich = [n for n in self.world.living_npcs() if n.status.coins > 20]
        poor = [n for n in self.world.living_npcs() if n.status.coins < 5]
        if not rich or not poor:
            return 0
        for _ in range(min(3, len(rich))):
            creditor = self.rng.choice(rich)
            debtor = self.rng.choice(poor)
            if creditor.id == debtor.id:
                continue
            # Don't lend to people you hate
            if creditor.id in debtor.relationships and debtor.relationships[creditor.id].affinity < -20:
                continue
            amount = min(creditor.status.coins // 2, self.rng.randint(3, 10))
            if amount < 1:
                continue
            self._make_loan(creditor, debtor, amount)
            loans += 1
        return loans

    def _make_loan(self, creditor: NPC, debtor: NPC, amount: int) -> None:
        creditor.status.coins -= amount
        debtor.status.coins += amount
        c = Contract(
            type=ContractType.DEBT,
            parties=[creditor.id, debtor.id],
            witnesses=[],
            year_created=self.world.year,
            terms={"amount": amount, "reason": "loan", "interest": 0.1},
            status=ContractStatus.ACTIVE,
            reputation_stake=15,
            notable=False,
        )
        self.world.add_contract(c)
        if debtor.id not in creditor.relationships:
            creditor.relationships[debtor.id] = Relationship()
        creditor.relationships[debtor.id].trust = max(0, creditor.relationships[debtor.id].trust - 5)
        if creditor.id not in debtor.relationships:
            debtor.relationships[creditor.id] = Relationship()
        debtor.relationships[creditor.id].affinity = min(100, debtor.relationships[creditor.id].affinity + 3)
