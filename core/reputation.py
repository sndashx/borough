"""Reputation system — how the town views the player (and how NPCs view each other).

Two layers:
  - per-NPC opinion of the player (int, -100..+100), decays toward 0 over time
  - town-wide reputation scalar (int, 0..1000), persistent legacy metric

Modifiers come from actions the player takes (kindness, theft, work, murder).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TownReputation:
    """Legacy / overall reputation. Persists past player death."""
    score: int = 0            # 0..1000
    notable_deeds: list = field(default_factory=list)  # list of {year, summary, delta}

    def adjust(self, year: int, delta: int, summary: str) -> None:
        self.score = max(0, min(1000, self.score + delta))
        self.notable_deeds.append({"year": year, "summary": summary, "delta": delta})
        if len(self.notable_deeds) > 50:
            self.notable_deeds = self.notable_deeds[-50:]


@dataclass
class NPCOpinion:
    """How a single NPC views the player. -100 = enemy, +100 = devoted."""
    npc_id: str
    score: int = 0
    last_changed_year: int = 0
    reasons: list = field(default_factory=list)  # list of (year, reason)

    def adjust(self, year: int, delta: int, reason: str) -> None:
        self.score = max(-100, min(100, self.score + delta))
        self.last_changed_year = year
        self.reasons.append((year, reason))
        if len(self.reasons) > 20:
            self.reasons = self.reasons[-20:]

    def decay(self, years: int = 1) -> None:
        """Opinion drifts toward 0 each year (people forget grudges, fickle love)."""
        if self.score > 0:
            self.score = max(0, self.score - 1 * years)
        elif self.score < 0:
            self.score = min(0, self.score + 1 * years)


class ReputationLedger:
    """Container for all reputation state. World owns one."""

    def __init__(self):
        self.town: TownReputation = TownReputation()
        self.opinions: Dict[str, NPCOpinion] = {}  # npc_id -> NPCOpinion

    def get(self, npc_id: str) -> NPCOpinion:
        if npc_id not in self.opinions:
            self.opinions[npc_id] = NPCOpinion(npc_id=npc_id)
        return self.opinions[npc_id]

    def adjust_player(self, npc_id: str, year: int, delta: int, reason: str) -> None:
        self.get(npc_id).adjust(year, delta, reason)

    def adjust_town(self, year: int, delta: int, summary: str) -> None:
        self.town.adjust(year, delta, summary)

    def decay_all(self, years: int = 1) -> None:
        for op in self.opinions.values():
            op.decay(years)

    def town_tier(self) -> str:
        """Coarse-grained tier label for UI/chronicle."""
        s = self.town.score
        if s >= 800:
            return "beloved"
        if s >= 600:
            return "respected"
        if s >= 400:
            return "known"
        if s >= 200:
            return "tolerated"
        if s >= 50:
            return "noticed"
        return "stranger"

    def allies(self, threshold: int = 30) -> list:
        """NPCs who like the player."""
        return [op.npc_id for op in self.opinions.values() if op.score >= threshold]

    def enemies(self, threshold: int = -30) -> list:
        """NPCs who dislike the player."""
        return [op.npc_id for op in self.opinions.values() if op.score <= threshold]

    def to_dict(self) -> dict:
        return {
            "town": {"score": self.town.score,
                     "notable_deeds": list(self.town.notable_deeds)},
            "opinions": {nid: {"npc_id": o.npc_id, "score": o.score,
                               "last_changed_year": o.last_changed_year,
                               "reasons": list(o.reasons)}
                          for nid, o in self.opinions.items()},
        }

    def from_dict(self, d: dict) -> None:
        self.town = TownReputation(
            score=d.get("town", {}).get("score", 0),
            notable_deeds=list(d.get("town", {}).get("notable_deeds", [])),
        )
        self.opinions = {}
        for nid, od in d.get("opinions", {}).items():
            self.opinions[nid] = NPCOpinion(
                npc_id=od["npc_id"],
                score=od.get("score", 0),
                last_changed_year=od.get("last_changed_year", 0),
                reasons=list(od.get("reasons", [])),
            )