"""Crisis events. Major disruptions to town life: plague, raid, fire, famine.

Each crisis has:
  - type
  - severity (1..5)
  - year + start_day
  - duration_days (or None until resolved)
  - affected_npc_ids (may grow)
  - chronicle entry written on resolution
"""
from __future__ import annotations
import random as _random
from enum import Enum
from typing import Dict, List, Optional


class CrisisType(str, Enum):
    PLAGUE = "plague"
    RAID = "raid"
    FIRE = "fire"
    FAMINE = "famine"
    FLOOD = "flood"
    WITCH_TRIAL = "witch_trial"
    TAX_COLLECTOR = "tax_collector"
    COMET = "comet"
    FESTIVAL = "festival"
    CATTLE_PESTILENCE = "cattle_pestilence"


class Crisis:
    """An active or resolved crisis event."""

    def __init__(self, type: CrisisType, year: int, start_day: int,
                 severity: int, duration_days: int):
        self.type = type
        self.year = year
        self.start_day = start_day
        self.severity = max(1, min(5, severity))
        self.duration_days = duration_days
        self.elapsed_days: int = 0
        self.affected: List[str] = []  # npc_ids
        self.deaths: List[str] = []
        self.resolved: bool = False
        self.notes: List[str] = []

    @property
    def active(self) -> bool:
        return not self.resolved

    def progress(self) -> float:
        if self.duration_days <= 0:
            return 1.0
        return min(1.0, self.elapsed_days / self.duration_days)

    def to_dict(self) -> dict:
        return {
            "type": self.type.value, "year": self.year, "start_day": self.start_day,
            "severity": self.severity, "duration_days": self.duration_days,
            "elapsed_days": self.elapsed_days, "affected": list(self.affected),
            "deaths": list(self.deaths), "resolved": self.resolved, "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Crisis":
        c = cls(
            type=CrisisType(d["type"]), year=d["year"], start_day=d["start_day"],
            severity=d["severity"], duration_days=d["duration_days"],
        )
        c.elapsed_days = d.get("elapsed_days", 0)
        c.affected = list(d.get("affected", []))
        c.deaths = list(d.get("deaths", []))
        c.resolved = d.get("resolved", False)
        c.notes = list(d.get("notes", []))
        return c


# Trigger conditions per crisis type, returning (severity, duration_days)
def _plague_trigger(rng, year, weather, npcs, factions) -> Optional[tuple]:
    if rng.random() < 0.03:  # ~3% per year
        severity = rng.randint(2, 4)
        dur = 60 + severity * 20
        return severity, dur
    return None


def _raid_trigger(rng, year, weather, npcs, factions) -> Optional[tuple]:
    militia = next((f for f in factions if f.id == "militia"), None)
    if not militia or len(militia.members) < 3:
        if rng.random() < 0.02:  # higher chance if undefended
            return rng.randint(2, 4), 3
    elif rng.random() < 0.005:
        return rng.randint(1, 3), 2
    return None


def _fire_trigger(rng, year, weather, npcs, factions) -> Optional[tuple]:
    if weather.current.value == "drought" and rng.random() < 0.04:
        return rng.randint(1, 3), 5
    if rng.random() < 0.01:
        return rng.randint(1, 3), 4
    return None


def _famine_trigger(rng, year, weather, npcs, factions) -> Optional[tuple]:
    if weather.drought_days > 60 and rng.random() < 0.5:
        return rng.randint(3, 5), 90
    return None


def _flood_trigger(rng, year, weather, npcs, factions) -> Optional[tuple]:
    if weather.current.value == "storm" and weather.rain_days > 4 and rng.random() < 0.3:
        return rng.randint(2, 3), 7
    return None


TRIGGERS = {
    CrisisType.PLAGUE: _plague_trigger,
    CrisisType.RAID: _raid_trigger,
    CrisisType.FIRE: _fire_trigger,
    CrisisType.FAMINE: _famine_trigger,
    CrisisType.FLOOD: _flood_trigger,
}


class CrisisLedger:
    """All crises (active + historical)."""

    def __init__(self):
        self.crises: List[Crisis] = []
        self._next_id: int = 0

    def active(self) -> List[Crisis]:
        return [c for c in self.crises if c.active]

    def historical(self) -> List[Crisis]:
        return [c for c in self.crises if c.resolved]

    def try_trigger(self, year: int, day: int, weather,
                    npcs, factions,
                    rng: Optional[_random.Random] = None) -> List[Crisis]:
        """Roll for new crises. Returns list of newly started crises."""
        rng = rng or _random.Random(year * 100 + day)
        npc_list = list(npcs.values()) if hasattr(npcs, "values") else list(npcs)
        new_crises = []
        # Don't stack same-type crises
        active_types = {c.type for c in self.active()}
        for ctype, trigger_fn in TRIGGERS.items():
            if ctype in active_types:
                continue
            result = trigger_fn(rng, year, weather, npc_list, factions)
            if result:
                severity, dur = result
                crisis = Crisis(ctype, year, day, severity, dur)
                crisis.notes.append(f"Onset: severity {severity}, duration {dur}d")
                self.crises.append(crisis)
                new_crises.append(crisis)
        return new_crises

    def tick_day(self, year: int, day: int, npcs,
                 rng: Optional[_random.Random] = None) -> List[dict]:
        """Advance all active crises by one day. Returns list of death events."""
        rng = rng or _random.Random(year * 1000 + day)
        deaths = []
        for c in self.active():
            c.elapsed_days += 1
            if c.type == CrisisType.PLAGUE:
                # Plague spreads to NPCs in same building as affected
                if rng.random() < 0.2 * c.severity / 5:
                    new_infected = self._spread_plague(c, npcs, rng)
                    c.affected.extend(new_infected)
                # Daily death roll for affected
                for npc_id in list(c.affected):
                    if rng.random() < 0.04 * c.severity / 3:
                        c.deaths.append(npc_id)
                        deaths.append({"npc_id": npc_id, "cause": "plague"})
            elif c.type == CrisisType.RAID:
                # Combat: pick a victim per day
                if rng.random() < 0.15 * c.severity:
                    alive = [n for n in npcs if n.is_alive]
                    if alive:
                        victim = rng.choice(alive)
                        if rng.random() < 0.5:
                            c.deaths.append(victim.id)
                            deaths.append({"npc_id": victim.id, "cause": "raid"})
                        else:
                            c.affected.append(victim.id)
            elif c.type == CrisisType.FIRE:
                # Burns a building
                if rng.random() < 0.1 * c.severity:
                    c.notes.append(f"Fire spreads on day {c.elapsed_days}")
            # Resolve
            if c.elapsed_days >= c.duration_days:
                c.resolved = True
                c.notes.append(f"Resolved after {c.elapsed_days} days, {len(c.deaths)} deaths")
        return deaths

    def _spread_plague(self, crisis: Crisis, npcs, rng) -> List[str]:
        """Infect 1-3 new NPCs per day."""
        npc_list = [n for n in npcs if n.is_alive and n.id not in crisis.affected]
        if not npc_list:
            return []
        n_new = min(len(npc_list), rng.randint(1, 2 + crisis.severity // 2))
        return [n.id for n in rng.sample(npc_list, n_new)]

    def to_dict(self) -> dict:
        return {
            "_next_id": self._next_id,
            "crises": [c.to_dict() for c in self.crises],
        }

    def from_dict(self, d: dict) -> None:
        self._next_id = d.get("_next_id", 0)
        self.crises = [Crisis.from_dict(cd) for cd in d.get("crises", [])]