"""Town Governance Council, Political Charters, and Elections. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World
    from .npc import NPC


@dataclass
class TownPolicy:
    tax_rate: int = 10                  # 0..50%
    curfew_active: bool = False
    grain_subsidy: bool = True
    witch_inquisition: bool = False
    sanctuary_rights: bool = True
    public_execution_law: bool = False
    treasury_gold: int = 500


@dataclass
class CouncilSeat:
    title: str                         # "Mayor", "High Constable", "Chief Guildmaster", "Grand Prelate"
    incumbent_id: Optional[str] = None
    salary: int = 20
    influence: int = 50


class GovernanceSystem:
    def __init__(self, world: Optional[World] = None):
        self.world = world
        self.policies = TownPolicy()
        self.seats = {
            "Mayor": CouncilSeat(title="Mayor", salary=30, influence=80),
            "High Constable": CouncilSeat(title="High Constable", salary=25, influence=60),
            "Chief Guildmaster": CouncilSeat(title="Chief Guildmaster", salary=20, influence=50),
            "Grand Prelate": CouncilSeat(title="Grand Prelate", salary=20, influence=50),
        }

    def hold_elections_and_council(self, world: World, rng) -> list[str]:
        logs = []
        living_adults = [n for n in world.npcs.values() if n.is_alive and n.lifecycle(world.year).value in ("adult", "elder")]
        if not living_adults:
            return logs

        # 1. Fill vacant seats
        for title, seat in self.seats.items():
            if seat.incumbent_id is None or not world.npcs.get(seat.incumbent_id, None) or not world.npcs[seat.incumbent_id].is_alive:
                # Vote by living adults
                candidates = living_adults[:5]
                winner = rng.choice(candidates)
                seat.incumbent_id = winner.id
                logs.append(f"Year {world.year}: {winner.first_name} {winner.family_name} was elected as {title}.")

        # 2. Council policy vote based on town state & needs
        hungry_count = sum(1 for n in living_adults if n.body.hunger < 40)
        paranoid_count = sum(1 for n in living_adults if n.psychology.paranoia > 50)

        # Grain subsidy vote
        if hungry_count > len(living_adults) * 0.3 and not self.policies.grain_subsidy:
            self.policies.grain_subsidy = True
            self.policies.treasury_gold = max(0, self.policies.treasury_gold - 100)
            logs.append(f"Year {world.year}: Town Council enacted Grain Subsidies due to widespread hunger.")

        # Curfew vote
        if paranoid_count > len(living_adults) * 0.3 and not self.policies.curfew_active:
            self.policies.curfew_active = True
            logs.append(f"Year {world.year}: High Constable enacted a Night Curfew to restore order.")
        elif paranoid_count < len(living_adults) * 0.1 and self.policies.curfew_active:
            self.policies.curfew_active = False
            logs.append(f"Year {world.year}: Town Council lifted the Night Curfew.")

        # Tax collection
        tax_collected = len(living_adults) * self.policies.tax_rate
        self.policies.treasury_gold += tax_collected
        logs.append(f"Year {world.year}: Collected {tax_collected} gold in taxes. Treasury now holds {self.policies.treasury_gold} gold.")

        return logs

    def to_dict(self) -> dict:
        return {
            "policies": self.policies.__dict__,
            "seats": {k: v.__dict__ for k, v in self.seats.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, world: Optional[World] = None) -> GovernanceSystem:
        gov = cls(world=world)
        if "policies" in d:
            gov.policies = TownPolicy(**d["policies"])
        if "seats" in d:
            gov.seats = {k: CouncilSeat(**v) for k, v in d["seats"].items()}
        return gov
