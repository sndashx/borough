"""Family registry. Tracks blood lines, marriages, feuds, and tombstones.

This is the social-graph layer. Marriages, feuds, and ancestor lines all
pass through here. Designed to be queried by the ghost ledger and the
player scene system.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class FeudState(str, Enum):
    """How two families currently relate."""
    NEUTRAL = "neutral"
    GRUDGE = "grudge"
    FEUD = "feud"
    BLOOD = "blood_feud"
    TRUCE = "truce"


@dataclass
class FamilyLine:
    """A single bloodline branch tracked through generations."""
    id: str
    root_id: str
    parent_line_id: Optional[str] = None
    child_line_ids: list[str] = field(default_factory=list)


@dataclass
class Tombstone:
    """A dead NPC's last mark. Where their memory lives."""
    npc_id: str
    name: str
    family_name: str
    death_year: int
    cause: str
    epitaph: str = ""
    remembered_by: int = 0
    line_id: Optional[str] = None


@dataclass
class FamilyRegistry:
    lines: dict[str, FamilyLine] = field(default_factory=dict)
    tombstone_by_npc: dict[str, Tombstone] = field(default_factory=dict)
    feud: dict[frozenset, FeudState] = field(default_factory=dict)
    _gen_counter: dict[str, int] = field(default_factory=dict)
    _parent_map: dict[str, tuple] = field(default_factory=dict)

    def ancestor_ids(self, npc_id, npc_mother_id, npc_father_id):
        """Walk up the family tree to find all direct ancestors.
        Returns a set of npc_ids that this person CANNOT marry.
        For now we rely on caller-supplied mother/father; the registry
        also stores a parent map below for full tree walks.
        """
        forbidden = {npc_id}
        if npc_mother_id:
            forbidden.add(npc_mother_id)
        if npc_father_id:
            forbidden.add(npc_father_id)
        return forbidden

    def register_parents(self, npc_id, mother_id, father_id):
        """Store parent links so can_marry can walk the full tree."""
        self._parent_map[npc_id] = (mother_id, father_id)

    def full_ancestor_ids(self, npc_id):
        """Walk the registered parent tree to collect all ancestors."""
        if npc_id not in self._parent_map:
            return {npc_id}
        seen = {npc_id}
        stack = [npc_id]
        while stack:
            cur = stack.pop()
            mom, dad = self._parent_map.get(cur, (None, None))
            for p in (mom, dad):
                if p and p not in seen:
                    seen.add(p)
                    stack.append(p)
        return seen

    def can_marry(self, a_mother, a_father, b_mother, b_father, a_id, b_id):
        a_ancestors = self.ancestor_ids(a_id, a_mother, a_father)
        b_ancestors = self.ancestor_ids(b_id, b_mother, b_father)
        # Also walk the registered parent map for full tree descent.
        a_full = self.full_ancestor_ids(a_id)
        b_full = self.full_ancestor_ids(b_id)
        shared = (a_ancestors | a_full) & (b_ancestors | b_full)
        if shared:
            return False, f"line_of_descent:{len(shared)}"
        if a_id == b_id:
            return False, "self"
        return True, ""

    def name_for_newborn(self, family_name):
        n = self._gen_counter.get(family_name, 0) + 1
        self._gen_counter[family_name] = n
        infixes = ["the Younger", "the Elder", "the Middle"]
        if n <= 1:
            return ""
        return f" {infixes[(n - 2) % 3]}"

    def _pair(self, a_family, b_family):
        return frozenset({a_family, b_family})

    def feud_state(self, a_family, b_family):
        if a_family == b_family:
            return FeudState.NEUTRAL
        return self.feud.get(self._pair(a_family, b_family), FeudState.NEUTRAL)

    def escalate(self, a_family, b_family, severity):
        if a_family == b_family:
            return FeudState.NEUTRAL
        key = self._pair(a_family, b_family)
        current = self.feud.get(key, FeudState.NEUTRAL)
        if severity >= 3:
            self.feud[key] = FeudState.BLOOD
        elif severity == 2 and current in (FeudState.NEUTRAL, FeudState.GRUDGE, FeudState.TRUCE):
            self.feud[key] = FeudState.FEUD
        elif severity == 1 and current in (FeudState.NEUTRAL, FeudState.TRUCE):
            self.feud[key] = FeudState.GRUDGE
        return self.feud[key]

    def truce(self, a_family, b_family):
        if a_family == b_family:
            return FeudState.NEUTRAL
        key = self._pair(a_family, b_family)
        current = self.feud.get(key, FeudState.NEUTRAL)
        if current == FeudState.BLOOD:
            self.feud[key] = FeudState.FEUD
        elif current == FeudState.FEUD:
            self.feud[key] = FeudState.GRUDGE
        elif current == FeudState.GRUDGE:
            self.feud[key] = FeudState.TRUCE
        else:
            self.feud[key] = FeudState.NEUTRAL
        return self.feud[key]

    def bury(self, npc_id, name, family_name, death_year, cause, line_id=None):
        t = Tombstone(
            npc_id=npc_id, name=name, family_name=family_name,
            death_year=death_year, cause=cause, line_id=line_id,
        )
        self.tombstone_by_npc[npc_id] = t
        return t

    def forget(self, npc_id):
        t = self.tombstone_by_npc.get(npc_id)
        if t:
            t.remembered_by = 0

    def remember(self, npc_id):
        t = self.tombstone_by_npc.get(npc_id)
        if t:
            t.remembered_by += 1
