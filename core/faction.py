"""Faction system. Town-level groups: Craft Guild, Temple, Militia, plus ad-hoc.

Factions have:
  - members (npc_ids)
  - leader (npc_id, may be None)
  - treasury (loose coin, just for narrative weight)
  - loyalty (0..100, per member via opinion)
  - tension with other factions (0..100, may escalate to feuds)

Three builtin factions: GUILD (craftsfolk), TEMPLE (faithful), MILITIA (defenders).
"""
from __future__ import annotations
import random as _random
from enum import Enum
from typing import Dict, List, Optional


class FactionType(str, Enum):
    GUILD = "guild"        # craftsmen
    TEMPLE = "temple"      # religious
    MILITIA = "militia"    # defenders
    BAND = "band"          # ad-hoc criminal or outcast group
    HOUSE = "house"        # noble family


class Faction:
    """A persistent group within the town."""

    def __init__(self, id: str, name: str, type: FactionType,
                 members: Optional[List[str]] = None,
                 leader: Optional[str] = None,
                 treasury: int = 0,
                 tension: Optional[Dict[str, int]] = None):
        self.id = id
        self.name = name
        self.type = type
        self.members: List[str] = list(members or [])
        self.leader: Optional[str] = leader
        self.treasury: int = treasury
        self.tension: Dict[str, int] = dict(tension or {})  # faction_id -> 0..100
        self.founded_year: int = 0

    def add_member(self, npc_id: str) -> None:
        if npc_id not in self.members:
            self.members.append(npc_id)

    def remove_member(self, npc_id: str) -> None:
        if npc_id in self.members:
            self.members.remove(npc_id)
        if self.leader == npc_id:
            self.leader = self.members[0] if self.members else None

    def tension_with(self, other_id: str) -> int:
        return self.tension.get(other_id, 0)

    def escalate(self, other_id: str, amount: int = 5) -> None:
        self.tension[other_id] = min(100, self.tension.get(other_id, 0) + amount)

    def cool(self, other_id: str, amount: int = 2) -> None:
        cur = self.tension.get(other_id, 0)
        self.tension[other_id] = max(0, cur - amount)
        if self.tension[other_id] == 0 and other_id in self.tension:
            del self.tension[other_id]

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "type": self.type.value,
            "members": list(self.members), "leader": self.leader,
            "treasury": self.treasury, "tension": dict(self.tension),
            "founded_year": self.founded_year,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Faction":
        f = cls(
            id=d["id"], name=d["name"], type=FactionType(d["type"]),
            members=d.get("members"), leader=d.get("leader"),
            treasury=d.get("treasury", 0), tension=d.get("tension"),
        )
        f.founded_year = d.get("founded_year", 0)
        return f


class FactionRegistry:
    """All factions in the world."""

    def __init__(self):
        self.factions: Dict[str, Faction] = {}

    def add(self, faction: Faction) -> None:
        self.factions[faction.id] = faction

    def get(self, id: str) -> Optional[Faction]:
        return self.factions.get(id)

    def of_type(self, type: FactionType) -> List[Faction]:
        return [f for f in self.factions.values() if f.type == type]

    def of_npc(self, npc_id: str) -> List[Faction]:
        return [f for f in self.factions.values() if npc_id in f.members]

    def seed_builtin(self, world) -> None:
        """Create GUILD, TEMPLE, MILITIA from NPCs that fit the role."""
        if "guild" in self.factions:
            return
        current_year = world.year
        from .npc import NPC
        from .building import BuildingType
        # GUILD: any NPC with a craft skill
        crafters = [n for n in world.npcs.values()
                    if n.is_alive
                    and (n.knowledge.skills.get("smithing", 0) >= 5
                         or n.knowledge.skills.get("milling", 0) >= 5)]
        if crafters:
            self.add(Faction(
                id="guild", name="Craftsmen's Guild", type=FactionType.GUILD,
                members=[c.id for c in crafters[:8]],
                leader=crafters[0].id,
            ))
        # TEMPLE: NPCs in a CHURCH building
        temple_folk = [n for n in world.npcs.values()
                       if n.is_alive and n.status.household_id
                       and world.buildings.get(n.status.household_id)
                       and world.buildings[n.status.household_id].type == BuildingType.CHURCH]
        if temple_folk:
            self.add(Faction(
                id="temple", name="Temple of the Borough", type=FactionType.TEMPLE,
                members=[t.id for t in temple_folk[:6]],
                leader=temple_folk[0].id,
            ))
        # MILITIA: any healthy adult not in temple
        militia = [n for n in world.npcs.values()
                   if n.is_alive
                   and 18 <= (current_year - n.birth_year) <= 50
                   and n not in temple_folk]
        if militia:
            self.add(Faction(
                id="militia", name="Town Militia", type=FactionType.MILITIA,
                members=[m.id for m in militia[:10]],
                leader=militia[0].id,
            ))

    def tick_year(self, year: int) -> list:
        """Auto-cools tension. Returns list of (faction_id, other_id, old, new) events."""
        events = []
        for f in self.factions.values():
            for other_id in list(f.tension.keys()):
                old = f.tension[other_id]
                f.cool(other_id, 1)
                if old > 50 and f.tension[other_id] <= 50:
                    events.append((f.id, other_id, old, f.tension[other_id]))
        return events

    def to_dict(self) -> dict:
        return {"factions": {fid: f.to_dict() for fid, f in self.factions.items()}}

    def from_dict(self, d: dict) -> None:
        self.factions = {fid: Faction.from_dict(fd)
                        for fid, fd in d.get("factions", {}).items()}