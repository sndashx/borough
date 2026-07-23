"""Chronicle — auto-generated narrative log of notable events.
Filters for salience. This is what the spectator mode reads.
Player-character salience is separate and earned.
"""
from __future__ import annotations
from typing import Optional

from .world import World
from .npc import NPC


class Chronicle:
    """Wraps the world's chronicle list. The town is its own chronicler.

    The town's own events are auto-recorded. Player-character events
    only land here if they clear the salience bar — i.e. the town
    decided to remember them.
    """

    def __init__(self, world: World):
        self.world = world

    def record(self, year: int, type_: str, summary: str, *, notable: bool = True,
               involved_npc_ids: Optional[list[str]] = None) -> None:
        entry = {
            "year": year,
            "type": type_,
            "summary": summary,
            "notable": notable,
            "involved": involved_npc_ids or [],
        }
        self.world.chronicle.append(entry)
        # Sprint 7: feed the same event into the ghost ledger so the dead watch
        if self.world.ghost is not None:
            self.world.ghost.append_chronicle(
                year, type_, summary, notable, involved_npc_ids,
            )

    def record_player_event(self, year: int, type_: str, summary: str,
                            involved_npc_ids: list[str], salience: float) -> bool:
        """Player events are gated by salience. If town doesn't care, it's not recorded.
        Salience rules (rough):
          - Any murder, public crime, witnessed death: 1.0 (always recorded)
          - Marriage into notable family: 0.7
          - Inheritance claim: 0.6
          - Public debt: 0.4
          - Private act with no witnesses: 0.1
        """
        if salience < 0.3:
            return False
        self.record(year, type_, summary, notable=True, involved_npc_ids=involved_npc_ids)
        return True

    def query(self, year_min: int = 0, year_max: Optional[int] = None,
              type_: Optional[str] = None, npc_id: Optional[str] = None) -> list[dict]:
        year_max = year_max if year_max is not None else 10**9
        out = []
        for e in self.world.chronicle:
            if e["year"] < year_min or e["year"] > year_max:
                continue
            if type_ and e["type"] != type_:
                continue
            if npc_id and npc_id not in e.get("involved", []):
                continue
            out.append(e)
        return out

    def town_says_about(self, npc_id: str) -> list[dict]:
        """All chronicle entries that mention this NPC."""
        return self.query(npc_id=npc_id)
