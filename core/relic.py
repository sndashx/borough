"""Masterwork Relics, Artifact Creation, and Family Heirlooms. Engine-agnostic."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .world import World
    from .npc import NPC


@dataclass
class Relic:
    id: str
    name: str
    creator_id: str
    creator_name: str
    year_created: int
    item_type: str                  # "sword", "crown", "goblet", "pendant", "tapestry", "anvil"
    material: str                   # "Steel", "Silver", "Damascus Steel", "Oak", "Gold", "Obsidian"
    engraving_description: str
    renown_value: int               # 100..10000 gold
    current_owner_id: str
    family_id: Optional[str] = None
    history_log: list[str] = field(default_factory=list)

    def record_transfer(self, from_name: str, to_name: str, year: int, reason: str) -> None:
        entry = f"Year {year}: Transferred from {from_name} to {to_name} via {reason}."
        self.history_log.append(entry)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "creator_id": self.creator_id,
            "creator_name": self.creator_name,
            "year_created": self.year_created,
            "item_type": self.item_type,
            "material": self.material,
            "engraving_description": self.engraving_description,
            "renown_value": self.renown_value,
            "current_owner_id": self.current_owner_id,
            "family_id": self.family_id,
            "history_log": self.history_log,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Relic:
        return cls(**d)


class RelicRegistry:
    def __init__(self, world: Optional[World] = None):
        self.world = world
        self.relics: dict[str, Relic] = {}
        self._relic_counter = 0

    def create_relic(self, creator: NPC, item_type: str, material: str, year: int, rng) -> Relic:
        self._relic_counter += 1
        relic_id = f"relic_{self._relic_counter}"
        
        titles = {
            "sword": ["Blade of Unbroken Vows", "Sunforged Longsword", "The Tyrant's Bane"],
            "goblet": ["Chalice of the First Harvest", "Silvered Sorrow Goblet", "Sovereign's Cup"],
            "crown": ["Ironwood Circlet", "Golden Laurel of Borough", "Crown of Ashes"],
            "tapestry": ["Tapestry of the Great Plague", "Weave of Seven Families", "Winter's Legend"],
            "anvil": ["The Eternal Anvil", "Titan's Iron Block", "Sledge of the Ancestors"],
        }
        name_options = titles.get(item_type, ["Masterwork Heirloom", "Relic of Ancient Worth"])
        name = rng.choice(name_options) + f" of House {creator.family_name}"
        
        desc = f"Masterfully forged in Year {year} by {creator.first_name} {creator.family_name}. Depicts the enduring spirit of Borough."
        relic = Relic(
            id=relic_id,
            name=name,
            creator_id=creator.id,
            creator_name=f"{creator.first_name} {creator.family_name}",
            year_created=year,
            item_type=item_type,
            material=material,
            engraving_description=desc,
            renown_value=rng.randint(500, 3000),
            current_owner_id=creator.id,
            family_id=creator.family_name,
            history_log=[f"Year {year}: Crafted by {creator.first_name} {creator.family_name}."]
        )
        self.relics[relic_id] = relic
        return relic

    def inherit_relics_on_death(self, deceased: NPC, heir: NPC, year: int) -> None:
        for relic in self.relics.values():
            if relic.current_owner_id == deceased.id:
                old_owner = f"{deceased.first_name} {deceased.family_name}"
                new_owner = f"{heir.first_name} {heir.family_name}"
                relic.current_owner_id = heir.id
                relic.record_transfer(old_owner, new_owner, year, "Inheritance")

    def to_dict(self) -> dict:
        return {
            "relic_counter": self._relic_counter,
            "relics": {k: v.to_dict() for k, v in self.relics.items()},
        }

    @classmethod
    def from_dict(cls, d: dict, world: Optional[World] = None) -> RelicRegistry:
        reg = cls(world=world)
        reg._relic_counter = d.get("relic_counter", 0)
        for k, v in d.get("relics", {}).items():
            reg.relics[k] = Relic.from_dict(v)
        return reg
