"""Chronicle viewer + spectator mode.

The town writes its own history. The viewer lets you read it.
The spectator lets you watch any NPC's life without playing them.

This module is the *first-class non-player mode* of the game. You can
spend an entire session just watching the town. Some players will
prefer it. That's the design.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Iterator

from .world import World
from .npc import NPC


@dataclass
class SpectatorView:
    """A read-only view of an NPC's life. Used by the spectator mode."""
    npc_id: str
    birth_year: int
    death_year: Optional[int]
    family_name: str
    first_name: str
    occupation: str
    is_alive: bool
    age_now: int
    summary: str


def npc_summary(world: World, npc_id: str) -> Optional[SpectatorView]:
    n = world.npcs.get(npc_id)
    if not n:
        return None
    age = world.year - n.birth_year
    summary = build_life_summary(world, n)
    return SpectatorView(
        npc_id=n.id,
        birth_year=n.birth_year,
        death_year=n.death_year,
        family_name=n.family_name,
        first_name=n.first_name,
        occupation=n.status.occupation or "unknown",
        is_alive=n.is_alive and not n.death_year,
        age_now=age,
        summary=summary,
    )


def build_life_summary(world: World, n: NPC) -> str:
    """Generate a 2-3 sentence prose summary of an NPC's life.
    The town remembers what the town remembers.
    """
    parts = []
    parts.append(f"{n.first_name} {n.family_name} was born in year {n.birth_year}.")
    if n.mother_id and n.mother_id in world.npcs:
        m = world.npcs[n.mother_id]
        parts.append(f"Their mother was {m.first_name} {m.family_name}.")
    # Marriage
    for c in world.contracts.values():
        if c.type.value == "marriage" and c.status.value == "active" and n.id in c.parties:
            other_id = next(p for p in c.parties if p != n.id)
            if other_id in world.npcs:
                o = world.npcs[other_id]
                parts.append(f"They married {o.first_name} {o.family_name} in year {c.year_created}.")
            break
    # Children
    children = [c for c in world.npcs.values() if c.mother_id == n.id or c.father_id == n.id]
    if children:
        parts.append(f"They had {len(children)} children.")
    # Occupation
    if n.status.occupation:
        parts.append(f"They worked as a {n.status.occupation}.")
    # Death
    if n.death_year:
        parts.append(f"They died in year {n.death_year}.")
    return " ".join(parts)


def list_living_npcs(world: World) -> list[SpectatorView]:
    """All currently living NPCs, with their life summary."""
    out = []
    for n in world.npcs.values():
        if n.is_alive and not n.death_year:
            v = npc_summary(world, n.id)
            if v:
                out.append(v)
    out.sort(key=lambda v: (v.family_name, v.first_name))
    return out


def list_famous_npcs(world: World, min_mentions: int = 2) -> list[tuple[str, int, str]]:
    """NPCs mentioned most often in the chronicle. These are the town's
    remembered figures — the ones who left a mark."""
    counts: dict[str, int] = {}
    for entry in world.chronicle:
        for npc_id in entry.get("involved", []):
            counts[npc_id] = counts.get(npc_id, 0) + 1
    out = []
    for npc_id, count in sorted(counts.items(), key=lambda kv: -kv[1]):
        if count < min_mentions:
            continue
        n = world.npcs.get(npc_id)
        if n:
            label = f"{n.first_name} {n.family_name} ({n.birth_year}-{n.death_year or 'alive'})"
            out.append((npc_id, count, label))
    return out


def list_recent_events(world: World, n: int = 20) -> list[dict]:
    """Last N chronicle entries, most recent first."""
    return list(reversed(world.chronicle[-n:]))


def search_chronicle(world: World, query: str) -> list[dict]:
    """Full-text search across the chronicle. The town's memory is searchable."""
    q = query.lower()
    out = []
    for entry in world.chronicle:
        if q in entry.get("summary", "").lower() or q in entry.get("type", "").lower():
            out.append(entry)
    return out


def town_statistics(world: World) -> dict:
    """Census + economic summary. The town's vital signs."""
    living = [n for n in world.npcs.values() if n.is_alive and not n.death_year]
    dead = [n for n in world.npcs.values() if n.death_year is not None]
    births = len(world.npcs)
    total_contracts = len(world.contracts)
    active_contracts = sum(1 for c in world.contracts.values()
                           if c.status.value == "active")
    total_coins = sum(n.status.coins for n in living)
    total_debt = sum(
        c.terms.get("principal", 0)
        for c in world.contracts.values()
        if c.type.value == "debt" and c.status.value == "active"
    )
    skills_held: dict[str, int] = {}
    for n in living:
        for skill, level in n.knowledge.skills.items():
            if level > 20:
                skills_held[skill] = skills_held.get(skill, 0) + 1
    return {
        "year": world.year,
        "population_living": len(living),
        "population_dead": len(dead),
        "total_births_ever": births,
        "active_contracts": active_contracts,
        "total_contracts_ever": total_contracts,
        "coins_in_circulation": total_coins,
        "active_debt": total_debt,
        "skills_held": skills_held,
        "chronicle_entries": len(world.chronicle),
    }


def render_chronicle_section(world: World, year_start: int, year_end: int,
                             type_filter: Optional[str] = None,
                             max_entries: int = 50) -> str:
    """Render a slice of the chronicle as readable text."""
    entries = [e for e in world.chronicle
               if year_start <= e["year"] <= year_end
               and (type_filter is None or e["type"] == type_filter)]
    entries.sort(key=lambda e: e["year"])
    if len(entries) > max_entries:
        entries = entries[-max_entries:]
    out = [f"=== Chronicle, years {year_start}-{year_end} ({len(entries)} entries) ==="]
    for e in entries:
        marker = "*" if e.get("notable") else " "
        out.append(f"  {marker} Y{e['year']:>4} [{e['type']:<20}] {e['summary']}")
    return "\n".join(out)


def find_player_ghosts(world: World) -> list[dict]:
    """All NPC-chronicle entries that mark remembered players from prior lives.
    These are the ghosts that can preface a new birth scene."""
    return [e for e in world.chronicle if e.get("type") == "ghost"]
