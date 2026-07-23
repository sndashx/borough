"""Gossip propagation. Knowledge spreads through conversations.
This is how facts become town-knowledge — and how a player's deeds become
the town's memory of them (or don't)."""
from __future__ import annotations
from typing import Iterable, Optional
import random as _random

from .npc import NPC, Memory


def propagate_gossip(npcs: Iterable[NPC], year: int, rng: Optional[_random.Random] = None) -> int:
    """For each co-located pair of NPCs, exchange a memory with some probability.
    Returns the number of facts propagated. Cheap O(N^2) at 30-100 NPCs.
    """
    rng = rng or _random
    npc_list = list(npcs)
    if len(npc_list) < 2:
        return 0
    propagated = 0
    for i, a in enumerate(npc_list):
        if not a.is_alive:
            continue
        for b in npc_list[i + 1:]:
            if not b.is_alive:
                continue
            # Co-location: same household or adjacent
            if a.status.household_id and a.status.household_id == b.status.household_id:
                if _share_memory(a, b, year, rng):
                    propagated += 1
    return propagated


def _share_memory(a: NPC, b: NPC, year: int, rng: _random.Random) -> bool:
    """One-directional: a tells b something."""
    candidates = [m for m in a.memory if m.confidence > 50 and m.witnessed_directly]
    if not candidates:
        return False
    mem = rng.choice(candidates)
    # Check b doesn't already have high-confidence on this fact
    for existing in b.memory:
        if (existing.event_type == mem.event_type
                and existing.participants == mem.participants
                and existing.confidence > 40):
            return False
    # Distorted rumor propagation (telephone game: valence exaggerates, confidence decays)
    distorted_valence = max(-100, min(100, int(mem.emotional_valence * 1.2) if mem.emotional_valence != 0 else rng.choice([-15, 15])))
    copy = Memory(
        year=year,
        event_type=mem.event_type,
        participants=list(mem.participants),
        emotional_valence=distorted_valence,
        confidence=max(30, mem.confidence - 20),
        witnessed_directly=False,
        source_npc_id=a.id,
    )
    b.memory.append(copy)
    return True


def form_memory_of(npc: NPC, year: int, event_type: str, participants: list[str],
                    valence: int, *, direct: bool = True, source: str | None = None) -> None:
    """An NPC acquires a memory. Used when they witness or are told of an event.
    Per the spec, town-NPC memory is automatic; player-character memory is
    earned separately (the player is a foreign element by default).
    """
    npc.memory.append(Memory(
        year=year,
        event_type=event_type,
        participants=participants,
        emotional_valence=valence,
        confidence=100 if direct else 60,
        witnessed_directly=direct,
        source_npc_id=source,
    ))
    # Cap memory list to prevent unbounded growth
    if len(npc.memory) > 500:
        npc.memory.sort(key=lambda m: m.confidence, reverse=True)
        npc.memory = npc.memory[:400]
