"""Building schema. Tracks state, contents, ownership, history."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


_building_counter = [0]
def _next_building_id() -> str:
    _building_counter[0] += 1
    return f"b_{_building_counter[0]}"


class BuildingType(str, Enum):
    HOUSE = "house"
    FARM = "farm"
    MILL = "mill"
    SMITHY = "smithy"
    CHURCH = "church"
    TAVERN = "tavern"
    BARN = "barn"
    WELL = "well"
    MARKET = "market"
    GRANARY = "granary"
    APOTHECARY = "apothecary"
    SCRIPTORIUM = "scriptorium"
    GUARDHOUSE = "guardhouse"
    TANNERY = "tannery"
    WORKSHOP = "workshop"
    VINEYARD = "vineyard"


@dataclass
class Building:
    id: str = field(default_factory=_next_building_id)
    type: BuildingType = BuildingType.HOUSE
    name: str = ""
    x: int = 0
    y: int = 0
    footprint: list[tuple[int, int]] = field(default_factory=list)  # tile offsets
    owner_npc_id: Optional[str] = None
    inherited_from_npc_id: Optional[str] = None
    condition: int = 100  # 0..100, decays, repaired
    occupant_npc_ids: list[str] = field(default_factory=list)
    item_ids: list[str] = field(default_factory=list)
    food_count_cache: int = 0  # cached for perf, recomputed on year boundary
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "footprint": self.footprint,
            "owner_npc_id": self.owner_npc_id,
            "inherited_from_npc_id": self.inherited_from_npc_id,
            "condition": self.condition,
            "occupant_npc_ids": self.occupant_npc_ids,
            "item_ids": self.item_ids,
            "food_count_cache": self.food_count_cache,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Building":
        return cls(
            id=d["id"],
            type=BuildingType(d["type"]),
            name=d.get("name", ""),
            x=d.get("x", 0),
            y=d.get("y", 0),
            footprint=[tuple(p) for p in d.get("footprint", [])],
            owner_npc_id=d.get("owner_npc_id"),
            inherited_from_npc_id=d.get("inherited_from_npc_id"),
            condition=d.get("condition", 100),
            occupant_npc_ids=d.get("occupant_npc_ids", []),
            item_ids=d.get("item_ids", []),
            food_count_cache=d.get("food_count_cache", 0),
            history=d.get("history", []),
        )
