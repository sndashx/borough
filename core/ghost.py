"""Ghost causal ledger — the dead who still matter.

This is what makes the town the protagonist. When a notable NPC dies,
they don't fully leave. They become a potential ancestor-ghost whose
vote influences which scenes the player is offered and what the town's
preface is for the player's life.

Two gates determine whether a ghost can write into a player's preface:
1. Threshold gate — at least N living NPCs must currently remember them.
2. Ancestor vote — only ancestor-ghosts (lineage-traceable) get to
   influence the next-of-kin life; the rest are just rumor.

The ledger hooks into Chronicle.record so every notable event can
potentially form a ghost's persistent memory.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from .family import Tombstone


# A dead NPC's continuing influence on the town.
@dataclass
class Ghost:
    npc_id: str
    name: str
    family_name: str
    death_year: int
    cause: str
    remembered_by: int = 0
    remembered_by_ids: set[str] = field(default_factory=set)
    # Threshold below which the town has forgotten them. Default 2.
    threshold: int = 2
    # Memory of the events that defined their life
    chronicle: list[dict] = field(default_factory=list)


@dataclass
class GhostCausalLedger:
    """Tracks which dead NPCs still matter to the town and to the player.

    Methods:
    - register_death: called when an NPC dies. Threshold default 2.
    - remember / forget: bumps a ghost's remember-counter.
    - preface_for_player: assembles an ancestor-walk if the player has
      ghosts that clear the threshold gate AND are real ancestors.
    - has_remembrance: returns True if at least `n` living NPCs remember
      a given dead NPC.
    """
    ghosts: dict[str, Ghost] = field(default_factory=dict)
    # Anchor player ancestry: npc_id -> [ancestor_npc_ids]
    _ancestors_of: dict[str, set[str]] = field(default_factory=dict)
    # Player family-name -> [ancestor_npc_ids by family]
    _family_ancestors: dict[str, list[str]] = field(default_factory=dict)
    # Default threshold; configurable per-ghost
    default_threshold: int = 2

    def register_death(self, npc_id, name, family_name, death_year, cause,
                       threshold: Optional[int] = None) -> Ghost:
        g = Ghost(
            npc_id=npc_id, name=name, family_name=family_name,
            death_year=death_year, cause=cause,
            threshold=threshold if threshold is not None else self.default_threshold,
        )
        self.ghosts[npc_id] = g
        # Append to family ancestor pool
        self._family_ancestors.setdefault(family_name, []).append(npc_id)
        return g

    def remember(self, npc_id, by_npc_id):
        """A living NPC now recalls this dead person."""
        g = self.ghosts.get(npc_id)
        if not g:
            return
        if by_npc_id in g.remembered_by_ids:
            return
        g.remembered_by_ids.add(by_npc_id)
        g.remembered_by = len(g.remembered_by_ids)

    def forget(self, npc_id, by_npc_id):
        g = self.ghosts.get(npc_id)
        if not g:
            return
        if by_npc_id in g.remembered_by_ids:
            g.remembered_by_ids.discard(by_npc_id)
            g.remembered_by = len(g.remembered_by_ids)

    def has_remembrance(self, npc_id, n: int = 2) -> bool:
        """True iff at least n living NPCs currently remember this dead NPC."""
        g = self.ghosts.get(npc_id)
        return g is not None and g.remembered_by >= n

    def remembers(self, dead_npc_id, living_npc_id) -> bool:
        g = self.ghosts.get(dead_npc_id)
        return g is not None and living_npc_id in g.remembered_by_ids

    def record_event(self, dead_npc_id, event):
        """Append a chronicle event to a ghost's personal memory."""
        g = self.ghosts.get(dead_npc_id)
        if g is not None:
            g.chronicle.append(event)

    def register_ancestry(self, player_npc_id, ancestor_npc_ids):
        """Tell the ledger that `player_npc_id` is descended from the given NPCs.
        Used to filter the ancestor-ghost preface.
        """
        existing = self._ancestors_of.get(player_npc_id, set())
        existing.update(ancestor_npc_ids)
        self._ancestors_of[player_npc_id] = existing

    def ancestors_of(self, player_npc_id) -> set[str]:
        return set(self._ancestors_of.get(player_npc_id, set()))

    def family_ancestors(self, family_name) -> list[str]:
        return list(self._family_ancestors.get(family_name, []))

    def ancestor_ghosts_for(self, player_npc_id, family_name=None,
                            threshold: Optional[int] = None) -> list[Ghost]:
        """The dead ancestors that clear the threshold gate for this player.

        threshold defaults to the ghost's individual threshold.
        A ghost qualifies if:
          - they are a registered ancestor of player_npc_id, OR
          - family_name is set and they belong to that family
          - AND remembered_by >= threshold (their own, or the override)
        """
        direct = self.ancestors_of(player_npc_id)
        family_pool = set(self.family_ancestors(family_name or ""))
        candidates = direct | family_pool
        out = []
        for dead_id in candidates:
            g = self.ghosts.get(dead_id)
            if not g:
                continue
            t = threshold if threshold is not None else g.threshold
            if g.remembered_by >= t:
                out.append(g)
        # Sort: most remembered first
        out.sort(key=lambda g: (-g.remembered_by, -g.death_year))
        return out

    def preface_for_player(self, player_npc_id, family_name=None) -> list[str]:
        """Assemble the ancestor-ghost preface for a player's birth scene.

        Returns a list of one-line strings. Empty list if no ancestor clears
        the threshold gate — meaning the town is indifferent to this life.
        """
        ghosts = self.ancestor_ghosts_for(player_npc_id, family_name)
        lines = []
        for g in ghosts:
            decade = (g.death_year // 10) * 10
            line = (
                f"{g.name} of the {g.family_name}s died in the {decade}s "
                f"({g.cause.replace('_', ' ')}). {g.remembered_by} still speak of them."
            )
            lines.append(line)
        return lines

    # ----- Hook for chronicle integration -----

    def append_chronicle(self, year, type_, summary, notable, involved_npc_ids):
        """When the world records a notable event, also feed it to any ghosts
        involved. The dead watch from the other side.
        """
        for nid in involved_npc_ids or []:
            g = self.ghosts.get(nid)
            if g is not None:
                g.chronicle.append({
                    "year": year, "type": type_, "summary": summary, "notable": notable,
                })
