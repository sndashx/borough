"""Religion / faith / ritual system.

Temple is a building. NPCs have faith (0..100). Rituals happen on calendar triggers:
  - BURIAL_RITUAL: on death of a town member
  - WEDDING_RITUAL: on marriage
  - HARVEST_RITUAL: day 280 each year
  - SOLSTICE_RITUAL: summer + winter solstice
  - BLESSING_RITUAL: player can request a blessing for +faith

Faith affects:
  - morale (-faith → unhappy, may emigrate? not in this build — no migrations)
  - town stability
  - crisis resistance (faithful are calmer)
"""
from __future__ import annotations
import random as _random
from enum import Enum
from typing import Dict, List, Optional


class RitualType(str, Enum):
    BURIAL = "burial"
    WEDDING = "wedding"
    HARVEST = "harvest"
    SOLSTICE = "solstice"
    BLESSING = "blessing"
    PENANCE = "penance"


# Calendar triggers: (day_of_year, ritual_type) or (None, "on_event")
CALENDAR_RITUALS = {
    80: RitualType.SOLSTICE,    # spring
    172: RitualType.SOLSTICE,   # summer
    280: RitualType.HARVEST,    # autumn harvest
    355: RitualType.SOLSTICE,   # winter
}


class Ritual:
    """A performed ritual."""
    def __init__(self, type: RitualType, year: int, day: int, officiant_id: Optional[str],
                 participants: List[str], outcome: str = "ok"):
        self.type = type
        self.year = year
        self.day = day
        self.officiant_id = officiant_id
        self.participants = participants
        self.outcome = outcome

    def to_dict(self) -> dict:
        return {
            "type": self.type.value, "year": self.year, "day": self.day,
            "officiant_id": self.officiant_id, "participants": list(self.participants),
            "outcome": self.outcome,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Ritual":
        return cls(
            type=RitualType(d["type"]), year=d["year"], day=d["day"],
            officiant_id=d.get("officiant_id"), participants=d.get("participants", []),
            outcome=d.get("outcome", "ok"),
        )


class ReligionState:
    """Per-world faith ledger + ritual history."""

    def __init__(self):
        self.faith: Dict[str, int] = {}     # npc_id -> 0..100
        self.temple_leader: Optional[str] = None
        self.rituals: List[Ritual] = []
        self.tithe_pool: int = 0            # accumulated donations

    def get_faith(self, npc_id: str) -> int:
        return self.faith.get(npc_id, 50)   # default neutral

    def adjust_faith(self, npc_id: str, delta: int) -> None:
        cur = self.get_faith(npc_id)
        self.faith[npc_id] = max(0, min(100, cur + delta))

    def mean_faith(self, npc_ids: List[str]) -> float:
        if not npc_ids:
            return 50.0
        return sum(self.get_faith(nid) for nid in npc_ids) / len(npc_ids)

    def tick_calendar(self, year: int, day_of_year: int, npcs, rng) -> List[Ritual]:
        """Check for calendar rituals (solstice, harvest). Returns performed rituals."""
        new_rituals = []
        if day_of_year in CALENDAR_RITUALS:
            rtype = CALENDAR_RITUALS[day_of_year]
            participants = [n.id for n in npcs if n.is_alive][:8]
            officiant = self.temple_leader or (participants[0] if participants else None)
            r = Ritual(rtype, year, day_of_year, officiant, participants)
            self.rituals.append(r)
            new_rituals.append(r)
            # Faith buff
            for nid in participants:
                self.adjust_faith(nid, 3)
            self.tithe_pool += len(participants)
        return new_rituals

    def perform_ritual(self, type: RitualType, year: int, day: int,
                       officiant_id: Optional[str], participants: List[str]) -> Ritual:
        r = Ritual(type, year, day, officiant_id, participants)
        self.rituals.append(r)
        if type == RitualType.BURIAL:
            # Burial comforts mourners
            for nid in participants:
                self.adjust_faith(nid, 2)
        elif type == RitualType.WEDDING:
            for nid in participants:
                self.adjust_faith(nid, 5)
        elif type == RitualType.BLESSING:
            for nid in participants:
                self.adjust_faith(nid, 8)
        elif type == RitualType.PENANCE:
            for nid in participants:
                self.adjust_faith(nid, -3)
        return r

    def to_dict(self) -> dict:
        return {
            "faith": dict(self.faith), "temple_leader": self.temple_leader,
            "tithe_pool": self.tithe_pool,
            "rituals": [r.to_dict() for r in self.rituals],
        }

    def from_dict(self, d: dict) -> None:
        self.faith = dict(d.get("faith", {}))
        self.temple_leader = d.get("temple_leader")
        self.tithe_pool = d.get("tithe_pool", 0)
        self.rituals = [Ritual.from_dict(rd) for rd in d.get("rituals", [])]