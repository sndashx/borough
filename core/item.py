"""Item schema. 1:1 tracking per the spec — every item is its own entity."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# Counter-based ID for performance. Realistic uniqueness not required for sim.
_item_counter = [0]


def _next_item_id() -> str:
    _item_counter[0] += 1
    return f"i_{_item_counter[0]}"


class ItemType(str, Enum):
    GRAIN = "grain"
    FLOUR = "flour"
    BREAD = "bread"
    COIN = "coin"
    TOOL = "tool"
    CLOTH = "cloth"
    WEAPON = "weapon"
    FURNITURE = "furniture"
    MEAT = "meat"
    WOOD = "wood"
    STONE = "stone"
    IRON_ORE = "iron_ore"
    INGOT = "ingot"
    STEEL_BROADSWORD = "steel_broadsword"
    HERB = "herb"
    POTION = "potion"
    SCROLL = "scroll"
    JEWELRY = "jewelry"
    HOPS = "hops"
    BEER = "beer"
    WINE = "wine"
    CIDER = "cider"
    CHEESE = "cheese"
    ARROW = "arrow"
    ARMOR = "armor"
    PELT = "pelt"
    BARREL = "barrel"
    BOOK = "book"
    LEATHER = "leather"


@dataclass
class Item:
    id: str = field(default_factory=_next_item_id)
    type: ItemType = ItemType.GRAIN
    weight: float = 1.0
    quality: int = 50  # 0..100
    owner_npc_id: Optional[str] = None
    building_id: Optional[str] = None
    tile_x: int = 0
    tile_y: int = 0
    history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "weight": self.weight,
            "quality": self.quality,
            "owner_npc_id": self.owner_npc_id,
            "building_id": self.building_id,
            "tile_x": self.tile_x,
            "tile_y": self.tile_y,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Item":
        return cls(
            id=d["id"],
            type=ItemType(d["type"]),
            weight=d["weight"],
            quality=d["quality"],
            owner_npc_id=d.get("owner_npc_id"),
            building_id=d.get("building_id"),
            tile_x=d.get("tile_x", 0),
            tile_y=d.get("tile_y", 0),
            history=d.get("history", []),
        )
